import json
import logging
import asyncio
from typing import Callable, Optional
import paho.mqtt.client as mqtt
from ..config import settings

logger = logging.getLogger("Substation_MQTT")

class SubstationMQTTClient:
    """
    变电站 MQTT 物联网数据传输客户端
    实现边缘网关遥测上报与遥控指令订阅分发
    """
    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self.is_connected = False
        self.on_control_received: Optional[Callable] = None

    def init_client(self):
        try:
            # 兼容 paho-mqtt 2.x 与 1.x
            self.client = mqtt.Client(
                client_id=settings.MQTT_CLIENT_ID,
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2
            )
        except Exception:
            self.client = mqtt.Client(client_id=settings.MQTT_CLIENT_ID)

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self.is_connected = True
            logger.info(f"MQTT Broker 连接成功: {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}")
            # 订阅控制主题
            client.subscribe(settings.MQTT_CONTROL_TOPIC)
            logger.info(f"已订阅控制主题: {settings.MQTT_CONTROL_TOPIC}")
        else:
            self.is_connected = False
            logger.warning(f"MQTT Broker 连接返回码: {rc}")

    def _on_disconnect(self, client, userdata, disconnect_flags_or_rc, properties=None):
        self.is_connected = False
        logger.info("MQTT Broker 连接已断开，等待自动重连")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            logger.info(f"收到 MQTT 控制消息 [{msg.topic}]: {payload}")
            if self.on_control_received and asyncio.iscoroutinefunction(self.on_control_received):
                asyncio.create_task(self.on_control_received(payload))
        except Exception as e:
            logger.error(f"处理 MQTT 消息异常: {e}")

    def start(self):
        self.init_client()
        try:
            # 异步非阻塞连接与后台事件循环
            self.client.connect_async(settings.MQTT_BROKER_HOST, settings.MQTT_BROKER_PORT, 60)
            self.client.loop_start()
            logger.info("MQTT 客户端后台轮询已启动")
        except Exception as e:
            logger.warning(f"MQTT Broker 暂未启动或无法连接 (将在后台持续探测): {e}")

    def stop(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.is_connected = False
            logger.info("MQTT 客户端已停止")

    def publish_telemetry(self, telemetry_data: dict):
        """发布实时遥测数据报文"""
        if self.client and self.is_connected:
            try:
                payload_str = json.dumps(telemetry_data, ensure_ascii=False)
                self.client.publish(settings.MQTT_TELEMETRY_TOPIC, payload_str, qos=0)
            except Exception as e:
                logger.error(f"MQTT 遥测上报失败: {e}")

    def publish_alarm(self, alarm_data: dict):
        """发布告警事件报文"""
        if self.client and self.is_connected:
            try:
                payload_str = json.dumps(alarm_data, ensure_ascii=False)
                self.client.publish(settings.MQTT_ALARM_TOPIC, payload_str, qos=1)
            except Exception as e:
                logger.error(f"MQTT 告警上报失败: {e}")

mqtt_client = SubstationMQTTClient()
