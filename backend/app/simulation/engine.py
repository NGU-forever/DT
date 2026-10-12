"""数字孪生仿真引擎：把潮流模型、热路模型、保护逻辑与告警判定串成一次时间步进。

与原实现的关键区别：

- 原来 ``ws.py`` 直接对 ``total_power`` 做随机游走、对油温写死初值，
  设备状态与全站遥测互相独立；
- 现在每一步都走 **拓扑 -> 潮流 -> 电流 -> 热路 -> 健康度 -> 告警** 的因果链，
  因此"分闸"必然会改变电流、负荷率、温度与健康度，而不再是一个孤立的内存字段。

故障注入也改为**改变边界条件**而不是改数字：
- 主变过热  = 冷却器全停（冷却可用率降到 0.5），由热模型自行把油温推到 91℃ 以上；
- SF6 泄漏  = 气压按泄漏速率衰减，跌破闭锁值自动告警并禁止合闸；
- 出线过载  = 出线负荷激增，越过保护定值后由保护逻辑延时跳闸，潮流随之重算。
"""

from __future__ import annotations

import logging
import math
import random
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..domain.point_model import PointModel, load_point_model
from .powerflow import FlowResult, StationPowerFlow
from .thermal import ThermalState, TransformerThermalModel

logger = logging.getLogger("Substation_Engine")

FAULT_TRANS_OVERHEAT = "trans_overheat"
FAULT_SF6_LEAK = "sf6_leak"
FAULT_OVERLOAD_TRIP = "overload_trip"
FAULT_TYPES = (FAULT_TRANS_OVERHEAT, FAULT_SF6_LEAK, FAULT_OVERLOAD_TRIP)

# 冷却器全停事故工况下的冷却能力可用率（由物模型热参数反推：稳态油温将收敛到 ~91.5℃）
COOLING_LOSS_RATIO = 0.5
# SF6 泄漏速率（MPa / 步），约 25 秒跌破 0.45MPa 闭锁值
SF6_LEAK_RATE_MPA_PER_STEP = 0.008
# 出线过载故障的负荷倍率，越过保护定值后延时跳闸
OVERLOAD_DEMAND_MULTIPLIER = 2.2

# 热状态"收敛"判据：油温单步变化小于该值即认为已进入稳态（K / 步）
CONVERGE_RATE_C_PER_STEP = 0.05

# 告警等级排序，用于在多测点同时越限时选取最严重者作为告警主体
_LEVEL_RANK = {"normal": 0, "info": 1, "warning": 2, "danger": 3}


class TwinEngine:
    """站级数字孪生引擎（进程内单例，由路由与推流任务共享）。"""

    def __init__(self, point_model: Optional[PointModel] = None):
        self.pm = point_model or load_point_model()
        self.reset(initial=True)

    # ------------------------------------------------------------------ 复位
    def reset(self, initial: bool = False) -> Dict[str, Any]:
        """回到物模型定义的初始工况。"""
        pm = self.pm
        self.step_index = 0
        self.values: Dict[str, Dict[str, Any]] = {}
        self.switch_state: Dict[str, bool] = {}
        self.health: Dict[str, int] = {}
        self.status: Dict[str, str] = {}
        self.cooling_ratio: Dict[str, float] = {}
        self.thermal_models: Dict[str, TransformerThermalModel] = {}
        self.thermal_state: Dict[str, ThermalState] = {}
        self._prev_oil: Dict[str, float] = {}
        self.active_faults: Dict[str, Dict[str, Any]] = {}
        self.mv_demand_multiplier = 1.0
        self.protection_counters: Dict[str, int] = {}
        self._last_signature: Dict[str, Optional[str]] = {}

        demand = pm.station.get("demand", {})
        self.demand_base_mva = float(demand.get("base_mva", 365.3))
        self.demand_band_mva = float(demand.get("band_mva", 2.4))
        self.demand_mva = self.demand_base_mva

        ambient = float(pm.station.get("ambient_temp_c", 24.8))
        compression = pm.time_compression

        for spec in pm.devices.values():
            vals = dict(spec.initial)
            vals.setdefault("voltage", float(pm.station.get("voltage_hv_kv" if spec.type == "transformer" else "voltage_hv_kv", 224.5)))
            self.values[spec.id] = vals
            if spec.is_switch():
                self.switch_state[spec.id] = bool(spec.initial_breaker_state())
                self.protection_counters[spec.id] = 0
            if spec.type == "transformer":
                self.cooling_ratio[spec.id] = float(spec.initial.get("cooler_ratio", 1.0))
                model = TransformerThermalModel(spec.physics, ambient, compression)
                self.thermal_models[spec.id] = model
                self.thermal_state[spec.id] = model.initial_state(
                    vals.get("oil_temp", ambient), vals.get("winding_temp", ambient)
                )
                self._prev_oil[spec.id] = self.thermal_state[spec.id].oil_temp
            self.health[spec.id] = int(vals.get("health_score", 95))
            self.status[spec.id] = "normal"

        # 未显式配置健康分的设备按健康度模型给出初值
        for spec in pm.devices.values():
            self.health[spec.id] = self._health_score(spec.id, self.values[spec.id])

        self.alarms: List[Dict[str, Any]] = []
        if not initial:
            self.alarms = []
        self.events: List[Dict[str, Any]] = []
        self.last_flow = StationPowerFlow(pm, self.switch_state).solve(self.demand_mva)
        self._apply_flow(self.last_flow)
        self._evaluate_all(emit_alarms=False)
        return self.snapshot()

    # ------------------------------------------------------------------ 步进
    def step(self, dt_seconds: Optional[float] = None) -> Dict[str, Any]:
        """推进一个仿真步，返回自洽的完整快照。"""
        pm = self.pm
        dt = float(dt_seconds if dt_seconds is not None else pm.step_seconds)
        self.step_index += 1
        self.events = []

        # 1. 负荷需求微幅波动（唯一的随机源，且只作用于"需求"这一外部边界条件）
        self.demand_mva = self.demand_base_mva + (random.random() - 0.5) * 2.0 * self.demand_band_mva

        # 2. 故障边界条件演化
        self._advance_faults(dt)

        # 3. 潮流：开关状态 -> 供电范围 -> 功率分配 -> 支路电流
        flow = StationPowerFlow(pm, self.switch_state).solve(self.demand_mva, self.mv_demand_multiplier)
        self.last_flow = flow
        self._apply_flow(flow)

        # 4. 热路：负载率 -> 油温 / 绕组热点温度
        self._advance_thermal(dt, flow)

        # 5. 保护逻辑：越限 -> 延时 -> 跳闸（跳闸后回到第 3 步的因果链，下个周期生效）
        self._check_protection(flow)

        # 6. 健康度与告警判定（阈值全部来自物模型）
        self._evaluate_all(emit_alarms=True)
        return self.snapshot()

    # ------------------------------------------------------- 潮流结果写回设备
    def _apply_flow(self, flow: FlowResult) -> None:
        pm = self.pm
        for spec in pm.devices.values():
            vals = self.values[spec.id]
            if spec.type == "transformer":
                mva = flow.transformer_mva.get(spec.id, 0.0)
                rated = float(spec.physics.get("rated_capacity_mva", 240.0))
                vals["current"] = round(flow.current_of(spec.id), 1)
                vals["load_rate"] = round(mva / rated * 100.0, 1) if rated else 0.0
                vals["voltage"] = round(float(pm.station["voltage_hv_kv"]), 1)
            else:
                vals["current"] = round(flow.current_of(spec.id), 1)
                if spec.id in self.switch_state:
                    vals["breaker_state"] = bool(self.switch_state[spec.id])
                if spec.voltage_level == "110kV":
                    vals["voltage"] = round(float(pm.station["voltage_mv_kv"]), 1)
                else:
                    vals["voltage"] = round(float(pm.station["voltage_hv_kv"]), 1)

    # --------------------------------------------------------------- 热路步进
    def _advance_thermal(self, dt: float, flow: FlowResult) -> None:
        for spec in self.pm.devices_of_type("transformer"):
            model = self.thermal_models[spec.id]
            vals = self.values[spec.id]
            rated = float(spec.physics.get("rated_capacity_mva", 240.0))
            load_factor = flow.transformer_mva.get(spec.id, 0.0) / rated if rated else 0.0
            cool = self.cooling_ratio.get(spec.id, 1.0)
            self._prev_oil[spec.id] = self.thermal_state[spec.id].oil_temp
            state = model.step(self.thermal_state[spec.id], load_factor, cool, dt)
            self.thermal_state[spec.id] = state
            vals["oil_temp"] = round(state.oil_temp, 1)
            vals["winding_temp"] = round(state.hot_spot_temp, 1)
            vals["cooler_ratio"] = round(cool, 2)
            banks = int(spec.physics.get("cooling_banks", 6))
            running = int(round(banks * cool))
            vals["cooler_banks_running"] = running
            vals["cooler_status"] = (
                f"自动运行 ({running}组投运)" if running > 0 else "冷却器全停 (事故工况)"
            )

    # --------------------------------------------------------------- 故障演化
    def _advance_faults(self, dt: float) -> None:
        leak = self.active_faults.get(FAULT_SF6_LEAK)
        if leak:
            device_id = leak["device_id"]
            vals = self.values[device_id]
            current = float(vals.get("sf6_pressure", 0.0))
            vals["sf6_pressure"] = round(max(current - SF6_LEAK_RATE_MPA_PER_STEP, 0.0), 3)
            vals["sf6_moisture"] = round(float(vals.get("sf6_moisture", 40.0)) + 1.2, 1)

        overheat = self.active_faults.get(FAULT_TRANS_OVERHEAT)
        if overheat:
            # 冷却器全停：冷却能力可用率下调，温度由热模型自行推导
            self.cooling_ratio[overheat["device_id"]] = COOLING_LOSS_RATIO

        trip = self.active_faults.get(FAULT_OVERLOAD_TRIP)
        self.mv_demand_multiplier = OVERLOAD_DEMAND_MULTIPLIER if trip else 1.0

    # --------------------------------------------------------------- 保护逻辑
    def _check_protection(self, flow: FlowResult) -> None:
        for spec in self.pm.switches():
            pickup = spec.physics.get("protection_pickup_a")
            if pickup is None:
                continue
            if not self.switch_state.get(spec.id, False):
                self.protection_counters[spec.id] = 0
                continue
            current = flow.current_of(spec.id)
            if current > float(pickup):
                self.protection_counters[spec.id] = self.protection_counters.get(spec.id, 0) + 1
                need = int(spec.physics.get("protection_delay_steps", 3))
                if self.protection_counters[spec.id] >= need:
                    self._trip_breaker(spec.id, current, float(pickup))
            else:
                self.protection_counters[spec.id] = 0

    def _trip_breaker(self, device_id: str, current: float, pickup: float) -> None:
        if not self.switch_state.get(device_id, False):
            return
        self.switch_state[device_id] = False
        self.protection_counters[device_id] = 0
        spec = self.pm.device(device_id)
        self.values[device_id]["breaker_state"] = False
        mva = self.last_flow.served_mva
        text = (
            f"【保护动作】{spec.name} 越限跳闸：实测 {current:.0f}A 超过过流保护定值 {pickup:.0f}A，"
            f"经 {spec.physics.get('protection_delay_steps', 3)} 个采样周期确认后出口跳闸"
        )
        self._raise_alarm(device_id, "danger", text)
        self.events.append(
            {
                "kind": "OPERATION_LOG",
                "log_type": "保护动作",
                "content": f"{spec.name} 过流保护动作跳闸（{current:.0f}A / 定值 {pickup:.0f}A），已甩负荷",
                "operator": "PROTECTION_RELAY",
            }
        )
        logger.warning("保护动作跳闸: %s @ %.1fA", device_id, current)

    # ----------------------------------------------------------- 健康度与告警
    def _health_score(self, device_id: str, values: Dict[str, Any]) -> int:
        """由模型量计算的健康度评分（不再写死）。"""
        score = 100.0

        def num(key: str) -> Optional[float]:
            v = values.get(key)
            return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None

        oil = num("oil_temp")
        if oil is not None:
            score -= max(oil - 75.0, 0.0) * 1.2
        hot = num("winding_temp")
        if hot is not None:
            score -= max(hot - 95.0, 0.0) * 0.8
        load_rate = num("load_rate")
        if load_rate is not None:
            score -= max(load_rate - 90.0, 0.0) * 0.3
        pd = num("pd_level")
        if pd is not None:
            score -= pd * 0.08
        vib = num("vibration")
        if vib is not None:
            score -= vib * 2.0
        sf6 = num("sf6_pressure")
        if sf6 is not None and sf6 > 0:
            score -= max(0.55 - sf6, 0.0) * 120.0
        wear = num("contact_wear")
        if wear is not None:
            score -= wear * 0.5
        moisture = num("sf6_moisture")
        if moisture is not None:
            score -= max(moisture - 50.0, 0.0) * 0.02
        actions = num("action_count")
        if actions is not None:
            score -= actions * 0.02
        return int(max(0.0, min(100.0, round(score))))

    def _evaluate_all(self, emit_alarms: bool) -> None:
        pm = self.pm
        for spec in pm.devices.values():
            values = self.values[spec.id]
            health = self._health_score(spec.id, values)
            values["health_score"] = health
            self.health[spec.id] = health

            report = pm.evaluate_device(spec.id, values)
            level = report["level"]
            values["status"] = level
            self.status[spec.id] = level

            if not report["items"]:
                self._last_signature[spec.id] = None
                continue
            # 取最严重的越限测点；同级时按键名排序，保证告警文本稳定不抖动
            worst = max(report["items"], key=lambda i: (_LEVEL_RANK[i["level"]], i["key"]))
            signature = f"{level}:{worst['key']}"
            # 边沿触发：仅当"等级或越限测点"发生变化时才产生新告警，避免稳态下每步刷屏
            if emit_alarms and self._last_signature.get(spec.id) != signature:
                self._raise_alarm(spec.id, level, self._format_alarm_text(spec, worst))
            self._last_signature[spec.id] = signature

    @staticmethod
    def _format_alarm_text(spec, item: Dict[str, Any]) -> str:
        direction = "低于" if item["direction"] == "low" else "超过"
        label = "危险" if item["level"] == "danger" else "预警"
        return (
            f"【{label}】{spec.name} {item['label']} {item['value']}{item['unit']} "
            f"{direction}{item['level']}阈值 {item['threshold']}{item['unit']}"
        )

    def _raise_alarm(self, device_id: str, level: str, text: str) -> None:
        spec = self.pm.device(device_id)
        alarm = {
            "id": f"alm-{device_id}-{uuid.uuid4().hex[:10]}",
            "time": datetime.now().strftime("%H:%M:%S"),
            "device_id": device_id,
            "device_name": spec.name,
            "level": level,
            "text": text,
            "handled": False,
        }
        self.alarms.insert(0, alarm)
        del self.alarms[60:]
        self.events.append({"kind": "ALARM", "alarm": alarm})
        logger.info("生成告警: %s %s", device_id, text)

    # ------------------------------------------------------------- 遥控与故障
    def set_breaker(self, device_id: str, closed: Optional[bool] = None, action: str = "toggle") -> Dict[str, Any]:
        """倒闸遥控。返回执行结果；带 SF6 气压闭锁与防误校验。"""
        pm = self.pm
        if not pm.has_device(device_id):
            raise KeyError(f"设备不存在: {device_id}")
        spec = pm.device(device_id)
        if not spec.is_switch():
            raise ValueError(f"设备不支持分合闸操作: {device_id}")

        current_state = bool(self.switch_state.get(device_id, False))
        if closed is None:
            new_state = (not current_state) if action == "toggle" else (str(action).lower() == "close")
        else:
            new_state = bool(closed)

        # 防误：SF6 气压低于闭锁值时禁止合闸。
        # 注意此校验必须在"位置未变化"的短路返回之前，否则对已合闸开关的重复合闸指令会绕过闭锁。
        if new_state:
            pressure = float(self.values[device_id].get("sf6_pressure", 1.0))
            lockout = float(spec.physics.get("sf6_lockout_pressure_mpa", 0.45))
            if pressure < lockout:
                text = (
                    f"【操作闭锁】{spec.name} SF6 气压 {pressure:.3f}MPa 低于闭锁值 {lockout:.3f}MPa，"
                    f"拒绝合闸操作"
                )
                self._raise_alarm(device_id, "danger", text)
                raise PermissionError(text)

        if new_state == current_state:
            return {"success": True, "changed": False, "device_id": device_id, "breaker_state": current_state,
                    "message": "开关已在目标位置，未重复操作"}

        self.switch_state[device_id] = new_state
        values = self.values[device_id]
        values["breaker_state"] = new_state
        wear = float(values.get("contact_wear", 0.0)) + 0.15
        values["contact_wear"] = round(wear, 2)
        values["action_count"] = int(values.get("action_count", 0)) + 1

        action_text = "合闸 (CLOSED)" if new_state else "分闸 (OPEN)"
        self.events.append(
            {
                "kind": "OPERATION_LOG",
                "log_type": "遥控指令",
                "content": f"下发遥控指令：[{spec.name}] 执行 {action_text}",
                "operator": "WEB_DIGITAL_TWIN",
            }
        )
        # 立刻重算潮流，使接口返回值就已经是操作后的自洽状态
        flow = StationPowerFlow(pm, self.switch_state).solve(self.demand_mva, self.mv_demand_multiplier)
        self.last_flow = flow
        self._apply_flow(flow)
        return {
            "success": True,
            "changed": True,
            "device_id": device_id,
            "breaker_state": new_state,
            "action_text": action_text,
            "station_mva_after": flow.served_mva,
            "de_energized": flow.de_energized,
            "message": f"断路器已切换为 {action_text}，潮流已按新拓扑重算",
        }

    def inject_fault(self, fault_type: str) -> Dict[str, Any]:
        """故障注入：改变模型边界条件，由模型自行演化出后果。"""
        if fault_type not in FAULT_TYPES:
            raise ValueError(f"未知故障类型: {fault_type}")

        if fault_type == FAULT_TRANS_OVERHEAT:
            device_id = "trans-1"
            self.active_faults[FAULT_TRANS_OVERHEAT] = {"device_id": device_id, "kind": "cooling_loss"}
            self.cooling_ratio[device_id] = COOLING_LOSS_RATIO
            model = self.thermal_models[device_id]
            load_factor = self.values[device_id].get("load_rate", 76.1) / 100.0
            oil_ss, hot_grad = model.steady_state(load_factor, COOLING_LOSS_RATIO)
            msg = (
                f"1# 主变冷却器全停（冷却能力降至 {COOLING_LOSS_RATIO:.0%}）。"
                f"按 IEC 60076-7 一阶热路模型推演，顶层油温将收敛至 {oil_ss:.1f}℃，"
                f"绕组热点温度约 {oil_ss + hot_grad:.1f}℃，预计越限 85℃ 后触发告警。"
            )
        elif fault_type == FAULT_SF6_LEAK:
            device_id = "gis-201"
            self.active_faults[FAULT_SF6_LEAK] = {"device_id": device_id, "kind": "gas_leak"}
            msg = (
                f"220kV GIS 201 气室发生 SF6 泄漏，气压以 {SF6_LEAK_RATE_MPA_PER_STEP:.3f}MPa/周期 衰减，"
                f"跌破 0.45MPa 闭锁值后自动告警并禁止合闸。"
            )
        else:
            device_id = "gis-101"
            self.active_faults[FAULT_OVERLOAD_TRIP] = {"device_id": device_id, "kind": "overload"}
            self.mv_demand_multiplier = OVERLOAD_DEMAND_MULTIPLIER
            spec = self.pm.device(device_id)
            pickup = float(spec.physics.get("protection_pickup_a", 1000.0))
            msg = (
                f"110kV 出线负荷激增至 {OVERLOAD_DEMAND_MULTIPLIER:.1f} 倍，"
                f"电流预计越过过流保护定值 {pickup:.0f}A，保护将延时出口跳闸。"
            )

        self._raise_alarm(device_id, "danger", f"【故障注入】{msg}")
        self.events.append(
            {
                "kind": "OPERATION_LOG",
                "log_type": "故障注入",
                "content": msg,
                "operator": "FAULT_SIMULATOR",
            }
        )
        return {"success": True, "fault_type": fault_type, "device_id": device_id, "message": msg}

    def clear_fault(self) -> Dict[str, Any]:
        """全站事故复归：恢复边界条件、恢复开关位置并重新计算热稳态。"""
        self.active_faults.clear()
        self.mv_demand_multiplier = 1.0
        self.protection_counters = {spec.id: 0 for spec in self.pm.switches()}
        for spec in self.pm.devices.values():
            self.cooling_ratio[spec.id] = 1.0 if spec.type == "transformer" else self.cooling_ratio.get(spec.id, 1.0)
            if spec.is_switch():
                self.switch_state[spec.id] = bool(spec.initial_breaker_state())
                self.values[spec.id]["breaker_state"] = bool(spec.initial_breaker_state())
            if spec.type == "transformer":
                self.cooling_ratio[spec.id] = 1.0
                self.thermal_state[spec.id] = self.thermal_models[spec.id].initial_state(
                    spec.initial.get("oil_temp", 55.0), spec.initial.get("winding_temp", 65.0)
                )
        for spec in self.pm.devices.values():
            for key, value in spec.initial.items():
                if key in ("cooler_banks_running",):
                    continue
                self.values[spec.id][key] = value
        self.demand_mva = self.demand_base_mva
        flow = StationPowerFlow(self.pm, self.switch_state).solve(self.demand_mva)
        self.last_flow = flow
        self._apply_flow(flow)
        self._last_signature = {}
        self._evaluate_all(emit_alarms=False)
        self.events.append(
            {
                "kind": "OPERATION_LOG",
                "log_type": "故障复归",
                "content": "全站事故信号已复归，边界条件与拓扑恢复额定工况",
                "operator": "CONTROL_CENTER",
            }
        )
        return {"success": True, "message": "全站状态已成功复归", "served_mva": flow.served_mva}

    def drain_events(self) -> List[Dict[str, Any]]:
        """取出并清空待持久化/上报的事件（告警、操作票）。"""
        events, self.events = self.events, []
        return events

    # ------------------------------------------------------------------ 快照
    def snapshot(self) -> Dict[str, Any]:
        flow = self.last_flow
        pm = self.pm
        converged = self._thermal_converged()

        # 频率与电压随负荷联动（不再是与负荷无关的随机数）
        load_delta = (flow.station_load_rate - 76.0) / 100.0
        frequency = round(50.0 + (random.random() - 0.5) * 0.02 - load_delta * 0.25, 3)
        u_hv = round(float(pm.station["voltage_hv_kv"]) * (1.0 - load_delta * 0.02), 1)
        u_mv = round(float(pm.station["voltage_mv_kv"]) * (1.0 - load_delta * 0.02), 1)
        # 站级三相电流取进线总电流，三相间保留微小不平衡
        incoming = 0.0
        for spec in pm.switches():
            if spec.topology.get("role") == "incoming" and self.switch_state.get(spec.id, False):
                incoming = flow.current_of(spec.id)
        if not incoming:
            incoming = sum(flow.transformer_mva.values()) / (math.sqrt(3) * u_hv) * 1000.0 if u_hv else 0.0

        telemetry = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "total_power": flow.total_power_mw,
            "reactive_power": flow.reactive_power_mvar,
            "apparent_power": flow.apparent_power_mva,
            "power_factor": float(pm.station["power_factor"]),
            "load_rate": flow.station_load_rate,
            "frequency": frequency,
            "voltage_a": u_hv,
            "voltage_b": round(u_hv - 0.3, 1),
            "voltage_c": round(u_hv + 0.3, 1),
            "current_a": round(incoming, 1),
            "current_b": round(incoming * 0.997, 1),
            "current_c": round(incoming * 1.004, 1),
            "shed_mva": flow.shed_mva,
            "energized_buses": flow.energized_buses,
        }

        model_meta = {
            "step": self.step_index,
            "time_compression": pm.time_compression,
            "step_seconds": pm.step_seconds,
            "converged": converged,
            "de_energized": flow.de_energized,
            "in_service_transformers": flow.in_service_transformers,
            "notes": flow.notes,
            "active_faults": sorted(self.active_faults.keys()),
            "thermal_steady_state": {
                tid: {
                    "oil_temp_steady": round(self._steady_oil(tid), 2),
                    "converged": abs(
                        self.thermal_state[tid].oil_temp - self._prev_oil.get(tid, self.thermal_state[tid].oil_temp)
                    ) <= CONVERGE_RATE_C_PER_STEP,
                }
                for tid in self.thermal_models
            },
        }

        devices = {}
        for spec in pm.devices.values():
            merged = {
                "id": spec.id,
                "name": spec.name,
                "model": spec.model,
                "voltage_level": spec.voltage_level,
                "device_type": spec.type,
                "rated_capacity": spec.rated_capacity,
            }
            merged.update(self.values[spec.id])
            devices[spec.id] = merged

        return {
            "type": "TELEMETRY_UPDATE",
            "timestamp": telemetry["timestamp"],
            "telemetry": telemetry,
            "devices": devices,
            "model": model_meta,
            "active_faults": sorted(self.active_faults.keys()),
        }

    def _steady_oil(self, transformer_id: str) -> float:
        """按当前潮流与冷却能力计算该主变的顶层油温稳态值（用于对比与收敛判断）。"""
        spec = self.pm.device(transformer_id)
        rated = float(spec.physics.get("rated_capacity_mva", 240.0))
        load_factor = self.last_flow.transformer_mva.get(transformer_id, 0.0) / rated if rated else 0.0
        return self.thermal_models[transformer_id].steady_state(
            load_factor, self.cooling_ratio.get(transformer_id, 1.0)
        )[0]

    def _thermal_converged(self) -> bool:
        """热状态收敛判据：油温单步变化率趋近于零。

        不用"与瞬时稳态值的距离"，因为负荷需求本身有微幅波动，
        瞬时稳态值会跟着抖，那样判据会一直闪烁。用"变化率"才是工程上
        判断是否进入稳态的正确做法。
        """
        for tid, state in self.thermal_state.items():
            prev = self._prev_oil.get(tid)
            if prev is None:
                continue
            if abs(state.oil_temp - prev) > CONVERGE_RATE_C_PER_STEP:
                return False
        return True

    # ---------------------------------------------------------------- 只读视图
    def device_status_list(self) -> List[Dict[str, Any]]:
        return list(self.snapshot()["devices"].values())

    def device_status(self, device_id: str) -> Dict[str, Any]:
        return self.snapshot()["devices"][device_id]


# 进程内单例：路由、推流任务、OPC UA 同步共用同一份孪生状态
engine = TwinEngine()


def get_engine() -> TwinEngine:
    return engine
