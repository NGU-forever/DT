"""倒闸遥控与故障仿真路由。

本层只做三件事：校验入参 -> 调用孪生引擎改变边界条件 -> 同步工业侧（OPC UA / MQTT）。
业务后果（潮流重算、温度演化、保护动作、告警与操作票）全部由引擎按物理模型产生，
路由不再直接给温度"赋值"，也不再自己拼装状态。
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime

from ..simulation.engine import get_engine
from ..opcua.server import opcua_server
from ..mqtt.client import mqtt_client
from ..schemas import BreakerControlRequest, FaultInjectRequest

router = APIRouter(prefix="/control", tags=["倒闸遥控与故障仿真"])


@router.post("/breaker")
async def control_breaker(req: BreakerControlRequest):
    """下发断路器遥控分合闸指令，并同步写入 OPC UA 可写节点与 MQTT 控制总线。"""
    engine = get_engine()
    try:
        result = engine.set_breaker(req.device_id, action=req.action)
    except KeyError:
        raise HTTPException(status_code=404, detail="目标断路器不存在")
    except ValueError:
        raise HTTPException(status_code=400, detail="该设备不支持断路器分合闸操作")
    except PermissionError as exc:
        # SF6 气压低于闭锁值：拒绝合闸，属于防误操作保护
        raise HTTPException(status_code=409, detail=str(exc))

    if result.get("changed"):
        await opcua_server.write_breaker_node(req.device_id, bool(result["breaker_state"]))
        mqtt_client.publish_telemetry(
            {
                "event": "BREAKER_CHANGED",
                "device_id": req.device_id,
                "state": result["breaker_state"],
                "operator": req.operator,
                "timestamp": datetime.now().isoformat(),
            }
        )
    result["message"] = f"{result['message']}，OPC UA 与 MQTT 已同步。"
    return result


@router.post("/fault/inject")
async def inject_fault(req: FaultInjectRequest):
    """注入典型故障：改变模型边界条件，由机理模型演化出后果。"""
    engine = get_engine()
    try:
        return engine.inject_fault(req.fault_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/fault/reset")
async def reset_fault():
    """全站事故一键复归。"""
    return get_engine().clear_fault()
