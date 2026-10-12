"""站内简化潮流模型：由开关状态决定供电范围，由功率导出电流。

原 Demo 的问题：全站电流 ``current_a`` 是一个从不更新的常量 472.4 A，
``total_power`` 独立做随机游走，与断路器分合闸毫无关系。
于是界面上会出现"201 已分闸"与"全站负荷 182MW"同时成立的物理矛盾。

本模块建立三条硬约束（也是单元测试的断言来源）：

1. **功率守恒**：站内实际供电负荷 = Σ 各主变承担的负荷；
2. **电流由功率导出**：I = S / (√3 · U)，任何支路电流都不是独立随机数；
3. **失电即零流**：未带电的母线与支路电流恒为 0，且全站功率为 0。

潮流分配策略（简化但自洽）：
- 带电源的母线经闭合的主变向低压侧供电；
- 站负荷需求按**容量比例**分配给所有"高压侧带电"的主变（因此一台主变退出时，
  其负荷会转移给其余主变并造成过载——这是真实电网的行为）；
- 母联断路器只输送两侧的不平衡功率。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

SQRT3 = math.sqrt(3.0)


@dataclass
class FlowResult:
    """一次潮流求解的结果快照。"""

    served_mva: float = 0.0
    shed_mva: float = 0.0
    total_power_mw: float = 0.0
    reactive_power_mvar: float = 0.0
    apparent_power_mva: float = 0.0
    station_load_rate: float = 0.0
    transformer_mva: Dict[str, float] = field(default_factory=dict)
    branch_currents: Dict[str, float] = field(default_factory=dict)
    energized_buses: List[str] = field(default_factory=list)
    in_service_transformers: List[str] = field(default_factory=list)
    de_energized: bool = False
    notes: List[str] = field(default_factory=list)

    def current_of(self, device_id: str) -> float:
        return float(self.branch_currents.get(device_id, 0.0))


class StationPowerFlow:
    """220kV 变电站简化潮流求解器。"""

    def __init__(self, point_model, switch_state: Optional[Dict[str, bool]] = None):
        self.pm = point_model
        self.u_hv = float(point_model.station["voltage_hv_kv"])
        self.u_mv = float(point_model.station["voltage_mv_kv"])
        self.power_factor = float(point_model.station["power_factor"])
        self.transformers = point_model.devices_of_type("transformer")
        # 由外部传入当前开关位置；未传入时按物模型初始位置
        self.switch_state: Dict[str, bool] = switch_state or {
            d.id: bool(d.initial_breaker_state()) for d in point_model.switches()
        }

    # ---- 电气量换算 ----
    def hv_current_a(self, mva: float) -> float:
        """高压侧三相视在功率 -> 线电流 (A)。"""
        if mva <= 0:
            return 0.0
        return mva / (SQRT3 * self.u_hv) * 1000.0

    def mv_current_a(self, mva: float) -> float:
        """中压侧(110kV)三相视在功率 -> 线电流 (A)。"""
        if mva <= 0:
            return 0.0
        return mva / (SQRT3 * self.u_mv) * 1000.0

    # ---- 带电范围搜索 ----
    def _resolve_energized_buses(self) -> Set[str]:
        """从电源点出发，经闭合开关与主变（高压侧->低压侧）传播带电范围。"""
        pm = self.pm
        energized: Set[str] = set()

        # 1. 电源点注入
        for source_id in pm.grid_sources():
            if not pm.has_device(source_id):
                continue
            spec = pm.device(source_id)
            if self.switch_state.get(source_id, False):
                target = spec.topology.get("to")
                if target:
                    energized.add(target)

        # 2. 迭代传播：闭合的母联开关 + 主变高低压侧耦合
        changed = True
        while changed:
            changed = False
            for spec in pm.switches():
                closed = self.switch_state.get(spec.id, False)
                if not closed:
                    continue
                if spec.topology.get("role") != "bus_tie":
                    continue
                a, b = spec.topology.get("from"), spec.topology.get("to")
                if a in energized and b not in energized:
                    energized.add(b)
                    changed = True
                elif b in energized and a not in energized:
                    energized.add(a)
                    changed = True
            for spec in self.transformers:
                hv_bus = spec.topology.get("hv_bus")
                lv_bus = spec.topology.get("lv_bus")
                # 主变按高压侧->低压侧单向传播（避免经低压侧反送电造成虚假带电）
                if hv_bus in energized and lv_bus and lv_bus not in energized:
                    energized.add(lv_bus)
                    changed = True
        return energized

    # ---- 主求解 ----
    def solve(self, demand_mva: float, mv_demand_multiplier: float = 1.0) -> FlowResult:
        """给定站负荷需求，求解潮流。

        :param demand_mva: 站负荷需求（视在功率 MVA，含 110kV 出线与 35kV 负荷）
        :param mv_demand_multiplier: 110kV 出线负荷倍率，用于模拟出线过载
        """
        pm = self.pm
        result = FlowResult()
        energized = self._resolve_energized_buses()
        result.energized_buses = sorted(energized)

        # 1. 参与供电的主变：高压侧必须带电
        in_service = [t for t in self.transformers if t.topology.get("hv_bus") in energized]
        result.in_service_transformers = [t.id for t in in_service]

        if not in_service:
            result.de_energized = True
            result.notes.append("全站失压：无带电源的变压器在运")
            for spec in pm.switches():
                result.branch_currents[spec.id] = 0.0
            for t in self.transformers:
                result.transformer_mva[t.id] = 0.0
            return result

        # 2. 负荷需求分解为「110kV 出线负荷」与「35kV 及其它负荷」
        #    出线负荷是否在供，取决于出线断路器位置与该侧母线是否带电
        mv_nominal = self._mv_nominal_share()
        mv_in_service = False
        for spec in pm.switches():
            if spec.topology.get("role") == "outgoing":
                mv_in_service = bool(self.switch_state.get(spec.id, False)) and spec.topology.get("from") in energized
        mv_served = demand_mva * mv_nominal * float(mv_demand_multiplier) if mv_in_service else 0.0
        other_load = demand_mva * (1.0 - mv_nominal)
        served_mva = other_load + mv_served
        result.served_mva = round(served_mva, 3)
        # 甩负荷 = 需求中有多少没被供上（出线停电时的份额）
        result.shed_mva = round(max(demand_mva - served_mva, 0.0), 3)

        # 3. 按容量比例分配主变负荷（容量相同即均分；一台退出则负荷转移）
        total_capacity = sum(float(t.physics.get("rated_capacity_mva", 1.0)) for t in in_service)
        for t in self.transformers:
            if t not in in_service:
                result.transformer_mva[t.id] = 0.0
                continue
            share = float(t.physics.get("rated_capacity_mva", 1.0)) / total_capacity
            result.transformer_mva[t.id] = round(served_mva * share, 3)

        # 4. 全站电气量
        result.apparent_power_mva = round(served_mva, 3)
        result.total_power_mw = round(served_mva * self.power_factor, 2)
        result.reactive_power_mvar = round(served_mva * math.sqrt(max(1.0 - self.power_factor**2, 0.0)), 2)
        result.station_load_rate = round(served_mva / total_capacity * 100.0, 1) if total_capacity else 0.0

        # 5. 支路电流
        for t in self.transformers:
            result.branch_currents[t.id] = round(self.hv_current_a(result.transformer_mva[t.id]), 1) if result.transformer_mva[t.id] else 0.0

        source_buses = {
            pm.device(pid).topology.get("to")
            for pid in pm.grid_sources()
            if pm.has_device(pid) and self.switch_state.get(pid, False)
        }

        for spec in pm.switches():
            if spec.id in result.branch_currents:
                continue
            role = spec.topology.get("role")
            closed = self.switch_state.get(spec.id, False)
            current = 0.0
            if closed and role == "incoming":
                # 进线断路器承担本站由该电源点获取的全部功率
                current = self.hv_current_a(served_mva)
            elif closed and role == "bus_tie":
                # 母联只输送"非电源侧"主变所需的转移功率
                a, b = spec.topology.get("from"), spec.topology.get("to")
                far_bus = a if b in source_buses else b
                transferred = sum(
                    result.transformer_mva.get(t.id, 0.0)
                    for t in in_service
                    if t.topology.get("hv_bus") == far_bus
                )
                current = self.hv_current_a(transferred)
            elif closed and role == "outgoing":
                current = self.mv_current_a(mv_served)
            result.branch_currents[spec.id] = round(current, 1)
        return result

    def _mv_nominal_share(self) -> float:
        """110kV 出线在总负荷中的额定份额。"""
        for spec in self.pm.switches():
            if spec.topology.get("role") == "outgoing":
                return float(spec.topology.get("load_share", 0.0))
        return 0.0
