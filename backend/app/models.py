from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from .database import Base

class DeviceModel(Base):
    """变电站一次电气设备台账"""
    __tablename__ = "devices"

    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    model = Column(String(100))
    voltage_level = Column(String(50))
    device_type = Column(String(50)) # transformer, gis, breaker, busbar
    status = Column(String(20), default="normal") # normal, warning, danger
    breaker_state = Column(Boolean, nullable=True) # True=合闸, False=分闸
    health_score = Column(Integer, default=95)
    rated_capacity = Column(String(50))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TelemetryRecordModel(Base):
    """全站时序遥测历史数据 (时序落库)"""
    __tablename__ = "telemetry_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    total_power = Column(Float)       # 有功功率 (MW)
    reactive_power = Column(Float)    # 无功功率 (Mvar)
    frequency = Column(Float)         # 频率 (Hz)
    voltage_a = Column(Float)         # A相电压 (kV)
    voltage_b = Column(Float)         # B相电压 (kV)
    voltage_c = Column(Float)         # C相电压 (kV)
    current_a = Column(Float)         # A相电流 (A)
    trans1_oil_temp = Column(Float)   # 1#主变油温 (℃)
    trans1_winding_temp = Column(Float)
    trans1_hot_spot = Column(Float)      # 1#主变绕组热点温度 (℃)
    trans2_oil_temp = Column(Float)      # 2#主变油温 (℃)
    trans2_hot_spot = Column(Float)      # 2#主变绕组热点温度 (℃)
    gis201_current = Column(Float)       # 201 进线电流 (A)
    gis201_sf6_pressure = Column(Float)
    station_load_rate = Column(Float)    # 全站综合负载率 (%)
    shed_mva = Column(Float)             # 甩负荷 (MVA)

class AlarmRecordModel(Base):
    """告警事件记录表"""
    __tablename__ = "alarm_records"

    id = Column(String(50), primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    device_id = Column(String(50), index=True)
    device_name = Column(String(100))
    level = Column(String(20)) # danger, warning, info
    message = Column(String(255))
    handled = Column(Boolean, default=False)

class OperationLogModel(Base):
    """倒闸与运维操作审计日志表"""
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    log_type = Column(String(50)) # 遥控指令, 故障复归, 巡检, 保护动作
    content = Column(String(255))
    operator = Column(String(50), default="SCADA_SYSTEM")
