"""遥测数据路由：全部数据来自孪生引擎快照，不再维护独立的随机数状态。"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime, timedelta

from ..database import get_db
from ..models import TelemetryRecordModel
from ..schemas import TelemetryData
from ..simulation.engine import get_engine

router = APIRouter(prefix="/telemetry", tags=["遥测数据"])


@router.get("/latest", response_model=TelemetryData)
async def get_latest_telemetry():
    """变电站当前最新的综合遥测指标快照（与 WebSocket 推流同源）。"""
    snapshot = get_engine().snapshot()
    return TelemetryData(**snapshot["telemetry"], devices=snapshot["devices"])


@router.get("/model")
async def get_model_state():
    """孪生模型运行状态：步数、收敛判据、在运设备、故障边界条件。"""
    snapshot = get_engine().snapshot()
    return snapshot["model"]


@router.get("/history")
async def get_telemetry_history(limit: int = 30, db: AsyncSession = Depends(get_db)):
    """获取历史负荷趋势数据 (用于前端 ECharts 大屏初始化波形)。"""
    result = await db.execute(
        select(TelemetryRecordModel).order_by(desc(TelemetryRecordModel.timestamp)).limit(limit)
    )
    records = result.scalars().all()
    if records:
        records.reverse()
        return [
            {
                "time": r.timestamp.strftime("%H:%M:%S"),
                "total_power": r.total_power,
                "reactive_power": r.reactive_power,
                "frequency": r.frequency,
                "trans1_oil_temp": r.trans1_oil_temp,
                "trans1_hot_spot": getattr(r, "trans1_hot_spot", None),
                "station_load_rate": getattr(r, "station_load_rate", None),
            }
            for r in records
        ]

    # 无历史数据时的兜底序列（保持与物模型初始工况一致，不再是硬编码常数）
    engine = get_engine()
    telemetry = engine.snapshot()["telemetry"]
    now = datetime.now()
    mock_history = []
    for i in range(limit, 0, -1):
        t = now - timedelta(seconds=i * 2)
        mock_history.append(
            {
                "time": t.strftime("%H:%M:%S"),
                "total_power": round(telemetry["total_power"] * (1 + (i % 7 - 3) * 0.002), 2),
                "reactive_power": round(telemetry["reactive_power"] * (1 + (i % 5 - 2) * 0.002), 2),
                "frequency": round(telemetry["frequency"] + (i % 3 - 1) * 0.005, 3),
                "trans1_oil_temp": engine.values["trans-1"]["oil_temp"],
                "trans1_hot_spot": engine.values["trans-1"]["winding_temp"],
                "station_load_rate": telemetry["load_rate"],
            }
        )
    return mock_history
