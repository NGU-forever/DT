"""物模型 (Thing Model) 加载与访问层。

设计目标：把"设备类型 -> 测点模板 -> 实例绑定"从代码里搬到配置里。
- 新增一台设备、增删一个测点、调整一个告警阈值，只改 ``device_model.json``，不改代码；
- OPC UA 地址空间、REST 台账、遥测推流、告警判定全部由同一份物模型驱动，
  从而保证"配置即接口"，不会出现三处定义互相不一致的情况。

电力语义：测点即"四遥"中的遥测(YC)/遥信(YX)，
本模块同时给出每个测点的单位、精度与告警阈值（高限/低限）。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

CONFIG_PATH = Path(__file__).with_name("device_model.json")


def resolve_config_path() -> Path:
    """物模型配置路径。

    默认取本模块同目录下的 device_model.json（与工作目录无关）；
    如需多站/多套配置，可用环境变量 THING_MODEL_PATH 覆盖。
    """
    try:
        from ..config import settings

        override = getattr(settings, "THING_MODEL_PATH", None)
    except Exception:  # 配置层不可用时退回默认路径
        override = None
    if override:
        candidate = Path(override)
        if candidate.exists():
            return candidate
    return CONFIG_PATH

# 告警等级排序，用于取最严重等级
_LEVEL_ORDER = {"normal": 0, "info": 1, "warning": 2, "danger": 3}


@dataclass(frozen=True)
class Measurement:
    """单个测点（遥测/遥信）的定义。"""

    key: str
    label: str
    unit: str = ""
    precision: int = 2
    alarm: Dict[str, Any] = field(default_factory=dict)

    @property
    def direction(self) -> str:
        """告警方向：high 表示越高越危险，low 表示越低越危险。"""
        return str(self.alarm.get("direction", "high"))

    def threshold(self, level: str) -> Optional[float]:
        value = self.alarm.get(level)
        return None if value is None else float(value)

    def evaluate(self, value: Any) -> str:
        """按阈值判定单个测点的告警等级，返回 normal/warning/danger。"""
        if value is None or not isinstance(value, (int, float)) or isinstance(value, bool):
            return "normal"
        danger = self.threshold("danger")
        warning = self.threshold("warning")
        if self.direction == "low":
            if danger is not None and value <= danger:
                return "danger"
            if warning is not None and value <= warning:
                return "warning"
        else:
            if danger is not None and value >= danger:
                return "danger"
            if warning is not None and value >= warning:
                return "warning"
        return "normal"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "unit": self.unit,
            "precision": self.precision,
            "alarm": dict(self.alarm),
        }


@dataclass(frozen=True)
class DeviceSpec:
    """设备实例定义（一台具体的一次设备）。"""

    id: str
    type: str
    name: str
    model: Optional[str]
    voltage_level: Optional[str]
    rated_capacity: Optional[str]
    topology: Dict[str, Any]
    physics: Dict[str, Any]
    initial: Dict[str, Any]
    opcua_folder: str

    def is_switch(self) -> bool:
        """是否为可遥控分合闸的开关类设备。"""
        return "breaker_state" in self.initial

    def initial_breaker_state(self) -> Optional[bool]:
        return self.initial.get("breaker_state")


@dataclass(frozen=True)
class DeviceType:
    """设备类型模板：一类设备的测点集合、OPC UA 映射与物理参数。"""

    name: str
    label: str
    measurements: Dict[str, Measurement]
    opcua: List[Dict[str, Any]]
    physics: Dict[str, Any]

    def measurement(self, key: str) -> Optional[Measurement]:
        return self.measurements.get(key)


class PointModel:
    """物模型门面：对上层屏蔽 JSON 结构。"""

    def __init__(self, raw: Dict[str, Any]):
        self.raw = raw
        self.station: Dict[str, Any] = raw["station"]
        self._types: Dict[str, DeviceType] = {}
        for type_name, tdef in raw["device_types"].items():
            measurements = {
                m["key"]: Measurement(
                    key=m["key"],
                    label=m.get("label", m["key"]),
                    unit=m.get("unit", ""),
                    precision=int(m.get("precision", 2)),
                    alarm=dict(m.get("alarm", {})),
                )
                for m in tdef.get("measurements", [])
            }
            self._types[type_name] = DeviceType(
                name=type_name,
                label=tdef.get("label", type_name),
                measurements=measurements,
                opcua=list(tdef.get("opcua", [])),
                physics=dict(tdef.get("physics", {})),
            )

        self._devices: Dict[str, DeviceSpec] = {}
        for d in raw["devices"]:
            folder = d.get("opcua_folder") or self._default_opcua_folder(d)
            # 设备自身 physics 覆盖类型模板 physics
            merged_physics = dict(self._types[d["type"]].physics)
            merged_physics.update(d.get("physics", {}))
            self._devices[d["id"]] = DeviceSpec(
                id=d["id"],
                type=d["type"],
                name=d["name"],
                model=d.get("model"),
                voltage_level=d.get("voltage_level"),
                rated_capacity=d.get("rated_capacity"),
                topology=dict(d.get("topology", {})),
                physics=merged_physics,
                initial=dict(d.get("initial", {})),
                opcua_folder=folder,
            )

    @staticmethod
    def _default_opcua_folder(device: Dict[str, Any]) -> str:
        """未显式配置 opcua_folder 时按约定生成：transformer -> Transformer_1。"""
        kind = "Transformer" if device.get("type") == "transformer" else "GIS_Breaker"
        return f"{kind}_{str(device['id']).split('-')[-1]}"

    # ---- 基础访问 ----
    @property
    def devices(self) -> Dict[str, DeviceSpec]:
        return self._devices

    @property
    def device_types(self) -> Dict[str, DeviceType]:
        return self._types

    def device(self, device_id: str) -> DeviceSpec:
        return self._devices[device_id]

    def has_device(self, device_id: str) -> bool:
        return device_id in self._devices

    def device_type(self, device_id: str) -> DeviceType:
        return self._types[self._devices[device_id].type]

    def measurements_for(self, device_id: str) -> Dict[str, Measurement]:
        return self.device_type(device_id).measurements

    def devices_of_type(self, type_name: str) -> List[DeviceSpec]:
        return [d for d in self._devices.values() if d.type == type_name]

    def switches(self) -> List[DeviceSpec]:
        return [d for d in self._devices.values() if d.is_switch()]

    def grid_sources(self) -> List[str]:
        return list(self.station.get("grid_sources", []))

    # ---- 仿真参数 ----
    @property
    def step_seconds(self) -> float:
        return float(self.station.get("simulation", {}).get("step_seconds", 1.5))

    @property
    def time_compression(self) -> float:
        """时间压缩倍数：真实物理时间常数 / 该倍数 = 模型内仿真时间常数。

        Demo 需要在几十秒内观察到热过程，而真实变压器顶层油温时间常数约 2.5 小时，
        因此显式声明压缩倍数，避免"看起来不真实又没有说明"。
        """
        return float(self.station.get("simulation", {}).get("time_compression", 300.0))

    @property
    def db_persist_every_steps(self) -> int:
        return int(self.station.get("simulation", {}).get("db_persist_every_steps", 10))

    def real_seconds_to_model(self, real_seconds: float) -> float:
        return real_seconds / self.time_compression

    # ---- 告警判定 ----
    def evaluate_device(self, device_id: str, values: Dict[str, Any]) -> Dict[str, Any]:
        """按物模型阈值评估单台设备的所有测点，返回综合告警等级与越限明细。"""
        items = []
        worst = "normal"
        for key, measurement in self.measurements_for(device_id).items():
            if key not in values:
                continue
            level = measurement.evaluate(values[key])
            if level != "normal":
                items.append(
                    {
                        "key": key,
                        "label": measurement.label,
                        "unit": measurement.unit,
                        "value": values[key],
                        "level": level,
                        "threshold": measurement.threshold(level),
                        "direction": measurement.direction,
                    }
                )
            if _LEVEL_ORDER[level] > _LEVEL_ORDER[worst]:
                worst = level
        return {"level": worst, "items": items}

    # ---- OPC UA 地址空间 ----
    def opcua_layout(self) -> List[Dict[str, Any]]:
        """生成扁平化的 OPC UA 地址空间布局，供服务端构建节点树。

        返回项形如：
        {"device_id": "gis-201", "folder": "GIS_Breaker_201",
         "node": "BreakerPosition", "variant": "Boolean", "writable": True,
         "initial": True, "measurement_key": "breaker_state"}
        """
        layout: List[Dict[str, Any]] = []
        for spec in self._devices.values():
            for item in self.device_type(spec.id).opcua:
                key = item["key"]
                layout.append(
                    {
                        "device_id": spec.id,
                        "folder": spec.opcua_folder,
                        "node": item["node"],
                        "variant": item.get("variant", "Float"),
                        "writable": bool(item.get("writable", False)),
                        "measurement_key": key,
                        "initial": self._opcua_initial(spec, key),
                    }
                )
        return layout

    def _opcua_initial(self, spec: DeviceSpec, key: str) -> Any:
        value = spec.initial.get(key)
        if value is not None:
            return value
        # 遥信量与开关状态同源
        if key == "breaker_state":
            return bool(spec.initial_breaker_state())
        measurement = self.device_type(spec.id).measurement(key)
        return 0.0 if measurement else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """物模型自描述，供 /api/model 接口对外暴露（前端可据此动态渲染测点）。"""
        return {
            "schema_version": self.raw.get("schema_version"),
            "station": self.station,
            "device_types": {
                name: {
                    "label": t.label,
                    "measurements": [m.to_dict() for m in t.measurements.values()],
                    "opcua": t.opcua,
                    "physics": t.physics,
                }
                for name, t in self._types.items()
            },
            "devices": [
                {
                    "id": d.id,
                    "type": d.type,
                    "name": d.name,
                    "model": d.model,
                    "voltage_level": d.voltage_level,
                    "rated_capacity": d.rated_capacity,
                    "topology": d.topology,
                    "opcua_folder": d.opcua_folder,
                    "physics": d.physics,
                    "measurements": [m.to_dict() for m in self.measurements_for(d.id).values()],
                }
                for d in self._devices.values()
            ],
        }


@lru_cache(maxsize=1)
def load_point_model() -> PointModel:
    """加载并缓存物模型（进程内单例）。"""
    with resolve_config_path().open("r", encoding="utf-8") as fp:
        raw = json.load(fp)
    return PointModel(raw)


def reload_point_model() -> PointModel:
    """清缓存后重新加载，便于测试与热更新。"""
    load_point_model.cache_clear()
    return load_point_model()
