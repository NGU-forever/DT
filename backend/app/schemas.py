from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

# 设备信息
class DeviceBase(BaseModel):
    id: str
    name: str
    model: Optional[str] = None
    voltage_level: Optional[str] = None
    device_type: Optional[str] = None
    status: str = "normal"
    breaker_state: Optional[bool] = None
    health_score: int = 95
    rated_capacity: Optional[str] = None

class DeviceDetail(DeviceBase):
    """设备实时测点。字段与物模型 device_model.json 中的测量点一一对应。"""

    oil_temp: Optional[float] = None            # 顶层油温 ℃
    winding_temp: Optional[float] = None        # 绕组热点温度 ℃
    current: Optional[float] = None             # 电流 A
    voltage: Optional[float] = None             # 运行电压 kV
    load_rate: Optional[float] = None           # 负载率 %
    sf6_pressure: Optional[float] = None        # SF6 气压 MPa
    sf6_moisture: Optional[float] = None        # SF6 微水 ppm
    pd_level: Optional[float] = None            # 局部放电 pC
    vibration: Optional[float] = None           # 振动 mm/s
    gas_h2: Optional[float] = None              # 油中溶解 H2 ppm
    contact_wear: Optional[float] = None        # 电寿命磨损 %
    action_count: Optional[int] = None          # 动作次数
    cooler_ratio: Optional[float] = None        # 冷却器可用率 0~1
    cooler_banks_running: Optional[int] = None  # 运行的冷却器组数
    cooler_status: Optional[str] = None         # 冷却器运行状态描述

# 实时全站遥测数据包 (WebSocket & MQTT 推流格式)
class TelemetryData(BaseModel):
    timestamp: str
    total_power: float
    reactive_power: float
    apparent_power: float
    power_factor: float
    load_rate: float
    frequency: float
    voltage_a: float
    voltage_b: float
    voltage_c: float
    current_a: float
    current_b: float
    current_c: float
    shed_mva: float = 0.0                       # 甩负荷 MVA
    energized_buses: List[str] = Field(default_factory=list)
    devices: Dict[str, Any] = Field(default_factory=dict)

# 孪生模型运行元信息 (推流载荷中的 model 段)
class TwinModelMeta(BaseModel):
    step: int = 0
    time_compression: float = 1.0
    step_seconds: float = 1.5
    converged: bool = False
    de_energized: bool = False
    in_service_transformers: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    active_faults: List[str] = Field(default_factory=list)
    thermal_steady_state: Dict[str, Any] = Field(default_factory=dict)

# 倒闸遥控指令请求
class BreakerControlRequest(BaseModel):
    device_id: str = Field(..., description="目标断路器ID，如 gis-201, gis-101")
    action: str = Field(..., description="'open' 分闸 或 'close' 合闸 或 'toggle' 取反")
    operator: str = "WEB_DIGITAL_TWIN"

# 故障模拟请求
class FaultInjectRequest(BaseModel):
    fault_type: str = Field(..., description="'trans_overheat', 'sf6_leak', 'overload_trip'")

# 告警条目
class AlarmItem(BaseModel):
    id: str
    time: str
    device_id: str
    device_name: str
    level: str
    text: str
    handled: bool

# 操作日志
class OperationLogItem(BaseModel):
    id: int
    time: str
    type: str
    content: str
