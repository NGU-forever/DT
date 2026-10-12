"""物模型自描述接口。

把 device_model.json 原样对外暴露，前端据此即可动态渲染任意设备的测点面板——
新增设备不需要改动任何前端代码，也不需要后端再加接口。
"""

from fastapi import APIRouter
from typing import Any, Dict

from ..domain.point_model import load_point_model

router = APIRouter(prefix="/model", tags=["物模型"])


@router.get("")
async def get_thing_model() -> Dict[str, Any]:
    """返回完整物模型：设备类型、测点模板、告警阈值、物理参数与拓扑绑定。"""
    return load_point_model().to_dict()
