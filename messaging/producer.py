"""
Kafka producer for sending messages between agents.
"""
import json
import logging
from typing import Any

from api.config import settings

logger = logging.getLogger(__name__)


class AgentProducer:
    """Kafka producer for agent messages. Degrades gracefully when Kafka is unavailable."""

    def __init__(self) -> None:
        self._producer = None
        try:
            from kafka import KafkaProducer

            self._producer = KafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                request_timeout_ms=5000,
                max_block_ms=5000,
            )
            logger.info("Kafka producer connected to %s", settings.kafka_bootstrap_servers)
        except Exception as exc:
            logger.warning(
                "Kafka producer could not connect (%s). "
                "Messages will be logged but not published.",
                exc,
            )

    @property
    def is_connected(self) -> bool:
        return self._producer is not None

    async def send_message(self, topic: str, message: dict[str, Any]) -> None:
        if self._producer is None:
            logger.warning(
                "Kafka unavailable. Would have published to '%s': %s",
                topic,
                json.dumps(message)[:200],
            )
            return
        try:
            self._producer.send(topic, value=message)
            self._producer.flush()
            logger.info("Published message to topic '%s'", topic)
        except Exception as exc:
            logger.error("Failed to publish to '%s': %s", topic, exc)

    def close(self) -> None:
        if self._producer is not None:
            self._producer.close()
            logger.info("Kafka producer closed")
