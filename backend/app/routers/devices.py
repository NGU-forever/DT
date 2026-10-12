"""设备台账与实时状态路由。

静态台账来自**物模型配置**，动态状态来自**孪生引擎**，
两者在引擎快照中已经合并，路由层只做转发与 404 判定，不再持有任何状态。
"""

from fastapi import APIRouter, HTTPException
from typing import List

from ..simulation.engine import get_engine
from ..schemas import DeviceDetail

router = APIRouter(prefix="/devices", tags=["设备台账与状态"])


@router.get("", response_model=List[DeviceDetail])
async def list_devices():
    """获取变电站所有一次设备列表及最新孪生状态。"""
    return list(get_engine().snapshot()["devices"].values())


@router.get("/{device_id}", response_model=DeviceDetail)
async def get_device(device_id: str):
    """根据 ID 获取指定设备的详细测点。"""
    engine = get_engine()
    if not engine.pm.has_device(device_id):
        raise HTTPException(status_code=404, detail="设备未找到")
    return engine.device_status(device_id)
