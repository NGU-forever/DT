"""OPC UA 服务端（IEC 62541）。

地址空间**完全由物模型配置生成**：``device_model.json`` 里每台设备的 ``opcua`` 段
决定它暴露哪些节点、什么数据类型、是否可写。新增设备或测点时，
这里一行代码都不需要改。
"""

import logging
from typing import Any, Dict, Tuple

from asyncua import Server, ua

from ..config import settings
from ..domain.point_model import load_point_model

logger = logging.getLogger("Substation_OPCUA")

_VARIANT_TYPES = {
    "Float": ua.VariantType.Float,
    "Double": ua.VariantType.Double,
    "Boolean": ua.VariantType.Boolean,
    "Int32": ua.VariantType.Int32,
    "String": ua.VariantType.String,
}


class SubstationOPCUAServer:
    """220kV 变电站工业级 OPC UA 仿真与通信服务端。"""

    def __init__(self):
        self.server = Server()
        self.endpoint = settings.OPCUA_ENDPOINT
        self.idx = 0
        self.nodes: Dict[Tuple[str, str], Any] = {}
        self.node_variants: Dict[Tuple[str, str], Any] = {}
        self.is_running = False

    async def init(self):
        pm = load_point_model()
        await self.server.init()
        self.server.set_endpoint(self.endpoint)
        self.server.set_server_name(settings.OPCUA_SERVER_NAME)

        # 注册自定义命名空间
        self.idx = await self.server.register_namespace(settings.OPCUA_NAMESPACE_URI)

        # 建立地址空间层级：Objects -> Substation_220kV -> 各设备文件夹 -> 测点节点
        objects = self.server.nodes.objects
        substation_folder = await objects.add_folder(self.idx, "Substation_220kV")

        folders: Dict[str, Any] = {}
        for item in pm.opcua_layout():
            folder_name = item["folder"]
            if folder_name not in folders:
                folders[folder_name] = await substation_folder.add_folder(self.idx, folder_name)

            variant_type = _VARIANT_TYPES.get(item["variant"], ua.VariantType.Float)
            initial = self._coerce(item["initial"], variant_type)
            node = await folders[folder_name].add_variable(self.idx, item["node"], initial, variant_type)
            if item["writable"]:
                await node.set_writable()

            key = (item["device_id"], item["measurement_key"])
            self.nodes[key] = node
            self.node_variants[key] = variant_type

        logger.info(
            "OPC UA 地址空间由物模型生成完成：%d 个节点 / %d 个设备文件夹，命名空间 %s",
            len(self.nodes), len(folders), settings.OPCUA_NAMESPACE_URI,
        )

    @staticmethod
    def _coerce(value: Any, variant_type) -> Any:
        """把 JSON 配置值转换成与 OPC UA 节点数据类型一致的 Python 值。"""
        if value is None:
            value = 0.0
        if variant_type == ua.VariantType.Boolean:
            return bool(value)
        if variant_type == ua.VariantType.Int32:
            return int(value)
        if variant_type == ua.VariantType.String:
            return str(value)
        return float(value)

    async def start(self):
        try:
            await self.init()
            await self.server.start()
            self.is_running = True
            logger.info(f"OPC UA 服务端已成功启动并在 {self.endpoint} 监听")
        except Exception as e:
            # 端口被占用或权限受限时降级为"仅 REST/WS 可用"，不影响孪生主链路
            logger.warning(f"OPC UA 服务端启动提示 (端口可能受限): {e}")

    async def stop(self):
        if self.is_running:
            await self.server.stop()
            self.is_running = False
            logger.info("OPC UA 服务端已安全停止")

    async def sync_snapshot(self, snapshot: Dict[str, Any]) -> None:
        """把孪生快照按物模型映射写入 OPC UA 节点，实现"数字侧 -> 工业侧"同步。"""
        if not self.is_running:
            return
        for device_id, values in snapshot.get("devices", {}).items():
            for key, value in values.items():
                node = self.nodes.get((device_id, key))
                if node is None or value is None:
                    continue
                try:
                    await node.write_value(
                        self._coerce(value, self.node_variants[(device_id, key)]),
                        self.node_variants[(device_id, key)],
                    )
                except Exception as e:
                    logger.debug("OPC UA 节点写入失败 %s.%s: %s", device_id, key, e)

    async def write_breaker_node(self, device_id: str, state: bool) -> None:
        """外部遥控直接写入断路器位置可写节点。"""
        if not self.is_running:
            return
        node = self.nodes.get((device_id, "breaker_state"))
        if node is None:
            return
        try:
            await node.write_value(bool(state), ua.VariantType.Boolean)
            logger.info(f"OPC UA 写入成功: {device_id} BreakerPosition = {state}")
        except Exception as e:
            logger.error(f"OPC UA 写入断路器节点失败: {e}")

    def node_listing(self) -> Dict[str, Any]:
        """对外暴露当前地址空间清单，便于运维核对。"""
        return {
            "endpoint": self.endpoint,
            "running": self.is_running,
            "namespace": settings.OPCUA_NAMESPACE_URI,
            "nodes": [
                {"device_id": d, "measurement": k, "variant": str(v).split(".")[-1]}
                for (d, k), v in self.node_variants.items()
            ],
        }


opcua_server = SubstationOPCUAServer()
