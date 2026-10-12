"""告警与审计日志路由。

告警有两个来源，这里做合并去重后统一对外：
1. 引擎内存中的**当前会话实时告警**（由物模型阈值边沿触发产生，毫秒级可见）；
2. 已由推流任务落库的**历史告警**（重启后依然可查）。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, update
from typing import List

from ..database import get_db
from ..models import AlarmRecordModel, OperationLogModel
from ..schemas import AlarmItem, OperationLogItem
from ..simulation.engine import get_engine

router = APIRouter(prefix="", tags=["告警与审计日志"])

# 数据库与引擎都为空时的初始演示告警
SEED_ALARMS = [
    {
        "id": "alm-seed-1",
        "time": "18:15:20",
        "device_id": "trans-1",
        "device_name": "1# 主变压器",
        "level": "warning",
        "text": "B相绕组温度微幅上升，触发智能风冷3组补强循环",
        "handled": False
    },
    {
        "id": "alm-seed-2",
        "time": "17:40:12",
        "device_id": "gis-201",
        "device_name": "220kV GIS 201 断路器",
        "level": "info",
        "text": "储能电机自动完成储能充压，机构压力正常",
        "handled": True
    },
]


@router.get("/alarms", response_model=List[AlarmItem])
async def list_alarms(limit: int = 20, db: AsyncSession = Depends(get_db)):
    """获取变电站告警流水列表（引擎实时告警 + 数据库历史告警，按 id 去重）。"""
    engine = get_engine()
    merged: List[AlarmItem] = []
    seen = set()

    for alarm in engine.alarms:
        if alarm["id"] in seen:
            continue
        seen.add(alarm["id"])
        merged.append(
            AlarmItem(
                id=alarm["id"],
                time=alarm["time"],
                device_id=alarm["device_id"],
                device_name=alarm["device_name"],
                level=alarm["level"],
                text=alarm["text"],
                handled=alarm["handled"],
            )
        )

    result = await db.execute(
        select(AlarmRecordModel).order_by(desc(AlarmRecordModel.timestamp)).limit(limit)
    )
    for record in result.scalars().all():
        if record.id in seen:
            continue
        seen.add(record.id)
        merged.append(
            AlarmItem(
                id=record.id,
                time=record.timestamp.strftime("%H:%M:%S"),
                device_id=record.device_id,
                device_name=record.device_name,
                level=record.level,
                text=record.message,
                handled=record.handled,
            )
        )

    if merged:
        return merged[:limit]
    return [AlarmItem(**a) for a in SEED_ALARMS]


@router.post("/alarms/{alarm_id}/ack")
async def acknowledge_alarm(alarm_id: str, db: AsyncSession = Depends(get_db)):
    """确认/响应告警（同时更新引擎内存与数据库）。"""
    handled = False
    for alarm in get_engine().alarms:
        if alarm["id"] == alarm_id:
            alarm["handled"] = True
            handled = True

    result = await db.execute(
        update(AlarmRecordModel)
        .where(AlarmRecordModel.id == alarm_id)
        .values(handled=True)
    )
    await db.commit()
    if result.rowcount:
        handled = True

    if handled:
        return {"success": True, "message": "告警已确认"}
    raise HTTPException(status_code=404, detail="未找到指定告警")


@router.get("/logs", response_model=List[OperationLogItem])
async def list_operation_logs(limit: int = 20, db: AsyncSession = Depends(get_db)):
    """获取变电运维操作记录流水。"""
    result = await db.execute(
        select(OperationLogModel).order_by(desc(OperationLogModel.timestamp)).limit(limit)
    )
    logs = result.scalars().all()
    if logs:
        return [
            OperationLogItem(
                id=l.id,
                time=l.timestamp.strftime("%H:%M:%S"),
                type=l.log_type,
                content=l.content,
            )
            for l in logs
        ]
    return [
        OperationLogItem(id=1, time="18:00:00", type="巡检", content="红外测温机器人完成 #1 主变例行巡检，未见异常热点"),
        OperationLogItem(id=2, time="16:30:15", type="遥信", content="220kV I母接地刀闸 2017 在分闸位状态确认"),
    ]
