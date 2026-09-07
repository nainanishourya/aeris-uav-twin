"""MQTT Gateway and Ingestion Client for AERIS.

Connects to Eclipse Mosquitto or any standard MQTT 3.1.1/5.0 broker.
Features an intelligent in-memory queue fallback so the entire system
runs seamlessly even when a local Mosquitto daemon is not installed.
"""

import json
import logging
import threading
from typing import Dict, Any, Callable, List, Optional
import paho.mqtt.client as mqtt

from aeris.config.settings import settings

logger = logging.getLogger("aeris.mqtt")

class AerisMQTTGateway:
    """Manages telemetry publish and subscribe pipelines over MQTT with in-memory fallback."""

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None, uav_id: Optional[str] = None):
        self.host = host or settings.mqtt_broker_host
        self.port = port or settings.mqtt_broker_port
        self.uav_id = uav_id or settings.mqtt_uav_id
        
        self.client: Optional[mqtt.Client] = None
        self.is_connected: bool = False
        self._callbacks: Dict[str, List[Callable[[str, Dict[str, Any]], None]]] = {}
        self._fallback_mode: bool = False
        self._lock = threading.Lock()

    def start(self):
        """Attempts connection to external MQTT broker, switches to fallback if unreachable."""
        try:
            # Paho MQTT v2 compatibility
            try:
                self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"aeris-gateway-{self.uav_id}")
            except (AttributeError, TypeError):
                self.client = mqtt.Client(client_id=f"aeris-gateway-{self.uav_id}")

            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.on_disconnect = self._on_disconnect

            logger.info(f"Connecting to MQTT broker at {self.host}:{self.port}...")
            self.client.connect_async(self.host, self.port, keepalive=settings.mqtt_keepalive)
            self.client.loop_start()
        except Exception as e:
            logger.warning(f"Could not connect to external MQTT broker ({e}). Enabling internal in-memory telemetry broker.")
            self._fallback_mode = True
            self.is_connected = False

    def stop(self):
        """Disconnect and stop client loop."""
        if self.client and not self._fallback_mode:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except Exception:
                pass
        self.is_connected = False

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            logger.info(f"Connected successfully to MQTT Broker at {self.host}:{self.port}")
            self.is_connected = True
            self._fallback_mode = False
            # Subscribe to all aeris topics for this UAV
            client.subscribe(f"aeris/uav/{self.uav_id}/#")
        else:
            logger.warning(f"MQTT Broker connection returned code {rc}. Using fallback dispatch.")
            self._fallback_mode = True

    def _on_disconnect(self, client, userdata, rc, properties=None):
        self.is_connected = False
        logger.info("MQTT Client disconnected.")

    def _on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode("utf-8"))
            self._dispatch_to_subscribers(topic, payload)
        except Exception as e:
            logger.error(f"Error decoding MQTT message on {msg.topic}: {e}")

    def _dispatch_to_subscribers(self, topic: str, payload: Dict[str, Any]):
        """Dispatches payload to internal registered callbacks."""
        with self._lock:
            # Check exact match or wildcard match
            for reg_topic, handlers in self._callbacks.items():
                if reg_topic == topic or reg_topic.endswith("/#") and topic.startswith(reg_topic[:-2]):
                    for h in handlers:
                        try:
                            h(topic, payload)
                        except Exception as ex:
                            logger.error(f"Error in subscriber handler for {topic}: {ex}")

    def subscribe(self, topic: str, handler: Callable[[str, Dict[str, Any]], None]):
        """Register a subscriber callback for a topic."""
        with self._lock:
            if topic not in self._callbacks:
                self._callbacks[topic] = []
            self._callbacks[topic].append(handler)

        if self.client and self.is_connected:
            self.client.subscribe(topic)

    def publish(self, topic: str, payload: Dict[str, Any]) -> bool:
        """Publishes JSON payload to topic over MQTT or internal dispatcher."""
        payload_str = json.dumps(payload)
        published_mqtt = False

        if self.client and self.is_connected and not self._fallback_mode:
            try:
                res = self.client.publish(topic, payload_str, qos=1)
                published_mqtt = (res.rc == mqtt.MQTT_ERR_SUCCESS)
            except Exception as e:
                logger.error(f"MQTT publish failed: {e}")
                self._fallback_mode = True

        # In all cases, also dispatch internally to guarantee local dashboard & DB receive the message
        self._dispatch_to_subscribers(topic, payload)
        return True

    def publish_telemetry(self, data: Dict[str, Any]):
        return self.publish(settings.topic_telemetry, data)

    def publish_health(self, data: Dict[str, Any]):
        return self.publish(settings.topic_health, data)

    def publish_alert(self, data: Dict[str, Any]):
        return self.publish(settings.topic_alerts, data)

    def publish_diagnostics(self, data: Dict[str, Any]):
        return self.publish(settings.topic_diagnostics, data)

# Global singleton gateway
mqtt_gateway = AerisMQTTGateway()
