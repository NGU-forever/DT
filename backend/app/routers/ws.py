"""WebSocket 实时推流：驱动孪生引擎步进，并广播 / 落库 / 上报。

**单一写入者原则**：只有本模块的推流循环向数据库写遥测与事件，
REST 路由只负责修改引擎状态。这样避免了"路由写一次、推流又写一次"的重复记录，
也让整个时序列是同一个时间步进的产物，天然对齐。
"""

import json
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..database import AsyncSessionLocal
from ..models import TelemetryRecordModel, AlarmRecordModel, OperationLogModel
from ..domain.point_model import load_point_model
from ..simulation.engine import get_engine
from ..opcua.server import opcua_server
from ..mqtt.client import mqtt_client

logger = logging.getLogger("Substation_WS")

router = APIRouter(tags=["WebSocket 实时推流"])


class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"客户端已接入 WebSocket，当前连接数: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"客户端断开 WebSocket，剩余连接数: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
        payload = json.dumps(message, ensure_ascii=False)
        disconnected = set()
        for conn in self.active_connections:
            try:
                await conn.send_text(payload)
            except Exception:
                disconnected.add(conn)
        for dead in disconnected:
            self.active_connections.discard(dead)


manager = ConnectionManager()


@router.websocket("/ws/substation")
async def websocket_substation_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # 握手：下发当前完整孪生快照（遥测 + 设备 + 模型元信息）
        snapshot = get_engine().snapshot()
        snapshot["type"] = "INITIAL_SNAPSHOT"
        await websocket.send_text(json.dumps(snapshot, ensure_ascii=False))

        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except Exception:
                continue
            action = msg.get("action")
            if action == "PING":
                await websocket.send_text(json.dumps({"type": "PONG", "timestamp": datetime.now().isoformat()}))
            elif action == "GET_SNAPSHOT":
                await websocket.send_text(json.dumps(get_engine().snapshot(), ensure_ascii=False))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket 异常断开: {e}")
        manager.disconnect(websocket)


async def telemetry_background_publisher():
    """孪生主时钟：步进引擎 -> 广播 -> 事件落库 -> OPC UA 同步 -> MQTT 上报 -> 时序落库。"""
    pm = load_point_model()
    engine = get_engine()
    step_seconds = pm.step_seconds
    persist_every = pm.db_persist_every_steps
    counter = 0
    logger.info(
        "★ 孪生主时钟已启动：步长 %.1fs，时间压缩 %.0f 倍，时序落库每 %d 步一次",
        step_seconds, pm.time_compression, persist_every,
    )

    while True:
        try:
            await asyncio.sleep(step_seconds)

            # 1. 推进机理模型（潮流 -> 热路 -> 保护 -> 告警）
            snapshot = engine.step()

            # 2. 广播给所有前端数字孪生看板
            await manager.broadcast(snapshot)

            # 3. 事件落库 + MQTT 告警上报
            await _persist_events(engine.drain_events())

            # 4. 同步 OPC UA 地址空间节点值
            await opcua_server.sync_snapshot(snapshot)

            # 5. MQTT 遥测上报
            mqtt_client.publish_telemetry(
                {
                    "type": "TELEMETRY_UPDATE",
                    "timestamp": snapshot["timestamp"],
                    "telemetry": snapshot["telemetry"],
                }
            )

            # 6. 时序落库（按步数抽样，避免高频 IO）
            counter += 1
            if counter >= persist_every:
                counter = 0
                await _persist_telemetry(snapshot)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"推流任务异常: {e}")
            await asyncio.sleep(2)


async def _persist_events(events: List[Dict[str, Any]]) -> None:
    """把引擎产生的告警与操作票写入数据库，并把告警上报 MQTT。"""
    if not events:
        return
    async with AsyncSessionLocal() as session:
        try:
            for event in events:
                if event.get("kind") == "ALARM":
                    alarm = event["alarm"]
                    session.add(
                        AlarmRecordModel(
                            id=alarm["id"],
                            timestamp=datetime.utcnow(),
                            device_id=alarm["device_id"],
                            device_name=alarm["device_name"],
                            level=alarm["level"],
                            message=alarm["text"],
                            handled=False,
                        )
                    )
                    mqtt_client.publish_alarm(
                        {
                            "type": "ALARM",
                            "level": alarm["level"],
                            "device_id": alarm["device_id"],
                            "message": alarm["text"],
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                elif event.get("kind") == "OPERATION_LOG":
                    session.add(
                        OperationLogModel(
                            log_type=event.get("log_type", "系统"),
                            content=event.get("content", ""),
                            operator=event.get("operator", "SYSTEM"),
                            timestamp=datetime.utcnow(),
                        )
                    )
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"事件落库失败: {e}")


async def _persist_telemetry(snapshot: Dict[str, Any]) -> None:
    """时序落库：只存模型算出来的量，保证历史曲线与实时曲线同源。"""
    telemetry = snapshot["telemetry"]
    devices = snapshot["devices"]
    trans1 = devices.get("trans-1", {})
    trans2 = devices.get("trans-2", {})
    gis201 = devices.get("gis-201", {})
    async with AsyncSessionLocal() as session:
        try:
            session.add(
                TelemetryRecordModel(
                    timestamp=datetime.utcnow(),
                    total_power=telemetry["total_power"],
                    reactive_power=telemetry["reactive_power"],
                    frequency=telemetry["frequency"],
                    voltage_a=telemetry["voltage_a"],
                    voltage_b=telemetry["voltage_b"],
                    voltage_c=telemetry["voltage_c"],
                    current_a=telemetry["current_a"],
                    trans1_oil_temp=trans1.get("oil_temp"),
                    trans1_winding_temp=trans1.get("winding_temp"),
                    trans1_hot_spot=trans1.get("winding_temp"),
                    trans2_oil_temp=trans2.get("oil_temp"),
                    trans2_hot_spot=trans2.get("winding_temp"),
                    gis201_current=gis201.get("current"),
                    gis201_sf6_pressure=gis201.get("sf6_pressure"),
                    station_load_rate=telemetry["load_rate"],
                    shed_mva=telemetry.get("shed_mva", 0.0),
                )
            )
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"时序落库失败: {e}")
