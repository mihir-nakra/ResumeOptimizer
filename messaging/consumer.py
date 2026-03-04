"""
Kafka consumer for receiving messages between agents.
"""
import json
import logging
from typing import Callable

from api.config import settings

logger = logging.getLogger(__name__)


class AgentConsumer:
    """Kafka consumer for agent messages. Degrades gracefully when Kafka is unavailable."""

    def __init__(self, topics: list[str], group_id: str) -> None:
        self._consumer = None
        try:
            from kafka import KafkaConsumer

            self._consumer = KafkaConsumer(
                *topics,
                bootstrap_servers=settings.kafka_bootstrap_servers,
                group_id=group_id,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            )
            logger.info("Kafka consumer connected for topics %s", topics)
        except Exception as exc:
            logger.warning(
                "Kafka consumer could not connect (%s). Consuming disabled.",
                exc,
            )

    @property
    def is_connected(self) -> bool:
        return self._consumer is not None

    async def consume(self, handler: Callable) -> None:
        if self._consumer is None:
            logger.warning("Kafka consumer not available. Cannot consume messages.")
            return
        for message in self._consumer:
            await handler(message.topic, message.value)

    def close(self) -> None:
        if self._consumer is not None:
            self._consumer.close()
            logger.info("Kafka consumer closed")
