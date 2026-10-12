import os
from pathlib import Path

from pydantic import BaseModel

# 工程根目录（backend/app/config.py -> backend/app -> backend -> DT/）
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = PROJECT_ROOT / "substation.db"


class Settings(BaseModel):
    PROJECT_NAME: str = "220kV 智能变电站数字孪生 IIoT 后端"
    API_V1_PREFIX: str = "/api"

    # 数据库配置 (异步 SQLite)
    # 必须用**绝对路径**：SQLite 的相对路径是相对进程工作目录的，
    # 用 "./substation.db" 会导致从不同目录启动时各自生成一个库，
    # 出现"历史曲线和告警突然查不到"的假故障。可用环境变量覆盖。
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", f"sqlite+aiosqlite:///{DEFAULT_DB_PATH}"
    )

    # 物模型配置路径（同样锚定到工程内，避免受工作目录影响）
    THING_MODEL_PATH: str = os.getenv(
        "THING_MODEL_PATH", str(PROJECT_ROOT / "backend" / "app" / "domain" / "device_model.json")
    )

    # OPC UA Server 配置
    OPCUA_ENDPOINT: str = "opc.tcp://0.0.0.0:4840/freeopcua/server/"
    OPCUA_SERVER_NAME: str = "Substation220kV_OPCUA_Server"
    OPCUA_NAMESPACE_URI: str = "http://substation220kv.digitaltwin.org"

    # MQTT 配置 (支持外部 Broker 如 Mosquitto / EMQX，或本地模拟)
    MQTT_BROKER_HOST: str = os.getenv("MQTT_BROKER_HOST", "127.0.0.1")
    MQTT_BROKER_PORT: int = int(os.getenv("MQTT_BROKER_PORT", "1883"))
    MQTT_CLIENT_ID: str = "Substation_FastAPI_Gateway"
    MQTT_TELEMETRY_TOPIC: str = "substation/220kv/telemetry"
    MQTT_CONTROL_TOPIC: str = "substation/220kv/control"
    MQTT_ALARM_TOPIC: str = "substation/220kv/alarms"

    # 遥测推流频率 (秒)
    TELEMETRY_INTERVAL: float = 1.0


settings = Settings()
