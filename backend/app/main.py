import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from .config import settings
from .database import engine, init_schema, AsyncSessionLocal
from .domain.point_model import load_point_model
from .models import DeviceModel
from .opcua.server import opcua_server
from .mqtt.client import mqtt_client
from .routers import devices, telemetry, control, alarms, ws, model
from .simulation.engine import get_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("Substation_Backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    pm = load_point_model()
    twin = get_engine()

    # 1. 建表 + 幂等补列（保证改动之前生成的 substation.db 也能平滑升级）
    added_columns = await init_schema()
    logger.info(
        "数据库初始化完成 (SQLite aiosqlite)%s",
        f"，本次补充列: {added_columns}" if added_columns else "，表结构已是最新",
    )

    # 2. 设备台账种子数据 —— 直接来自物模型配置，不再在代码里硬编码
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(DeviceModel))
        if not res.scalars().first():
            for spec in pm.devices.values():
                values = twin.values.get(spec.id, {})
                session.add(
                    DeviceModel(
                        id=spec.id,
                        name=spec.name,
                        model=spec.model,
                        voltage_level=spec.voltage_level,
                        device_type=spec.type,
                        status=values.get("status", "normal"),
                        breaker_state=values.get("breaker_state"),
                        health_score=int(values.get("health_score", 95)),
                        rated_capacity=spec.rated_capacity,
                    )
                )
            await session.commit()
            logger.info("初始电气设备台账已按物模型写入数据库：%d 台设备", len(pm.devices))

    # 3. 启动工业 OPC UA 服务端（地址空间由物模型生成）
    await opcua_server.start()

    # 4. 启动 MQTT 物联网网关客户端：外部控制指令直接驱动孪生引擎
    async def on_mqtt_control(payload: dict):
        device_id = payload.get("device_id")
        action = payload.get("action", "toggle")
        try:
            result = twin.set_breaker(device_id, action=action)
            if result.get("changed"):
                await opcua_server.write_breaker_node(device_id, bool(result["breaker_state"]))
            logger.info("MQTT 遥控指令执行完毕: %s -> %s", device_id, result.get("breaker_state"))
        except Exception as exc:
            logger.warning("MQTT 遥控指令被拒绝 (%s): %s", device_id, exc)

    mqtt_client.on_control_received = on_mqtt_control
    mqtt_client.start()

    # 5. 启动孪生主时钟：步进机理模型并推流/落库/上报
    publisher_task = asyncio.create_task(ws.telemetry_background_publisher())

    logger.info("★ 220kV 变电站数字孪生后端服务已全链路就绪 ★")
    logger.info("  - 孪生模型: IEC 60076-7 一阶热路 + 拓扑潮流，时间压缩 %.0f 倍", pm.time_compression)
    logger.info(f"  - REST API & Swagger UI: http://localhost:8000/docs")
    logger.info(f"  - 物模型自描述: http://localhost:8000/api/model")
    logger.info(f"  - WebSocket 实时通道: ws://localhost:8000/ws/substation")
    logger.info(f"  - OPC UA Server 端口: {settings.OPCUA_ENDPOINT}")
    logger.info(f"  - MQTT 客户端状态: 监听 {settings.MQTT_CONTROL_TOPIC}")

    yield

    # 优雅停机
    publisher_task.cancel()
    await opcua_server.stop()
    mqtt_client.stop()
    await engine.dispose()
    logger.info("后端服务已安全停机")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="支持 FastAPI + OPC UA (IEC 62541) + MQTT (IoT) + WebSocket + SQLite 的变电站数字孪生后端系统；"
                "内置物模型驱动的遥测体系、IEC 60076-7 一阶热路模型与拓扑潮流模型",
    version="2.0.0",
    lifespan=lifespan
)

# 允许跨域 (支持 Vue 3 前端联调)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载路由
app.include_router(devices.router, prefix=settings.API_V1_PREFIX)
app.include_router(telemetry.router, prefix=settings.API_V1_PREFIX)
app.include_router(control.router, prefix=settings.API_V1_PREFIX)
app.include_router(alarms.router, prefix=settings.API_V1_PREFIX)
app.include_router(model.router, prefix=settings.API_V1_PREFIX)
app.include_router(ws.router)

@app.get("/")
async def root():
    return {
        "project": settings.PROJECT_NAME,
        "status": "online",
        "docs_url": "/docs",
        "thing_model_url": f"{settings.API_V1_PREFIX}/model",
        "websocket_url": "/ws/substation",
        "opcua_endpoint": settings.OPCUA_ENDPOINT
    }
