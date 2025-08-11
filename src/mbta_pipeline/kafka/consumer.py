"""Kafka consumer wrapper for MBTA pipeline."""

from __future__ import annotations

import json
from typing import Callable, Optional

from confluent_kafka import Consumer, KafkaError

from ..config.settings import settings
from ..utils.logging import get_logger


class KafkaConsumerWrapper:
    def __init__(self, group_id: str, logger_name: str = "KafkaConsumer") -> None:
        self.logger = get_logger(logger_name)
        conf = {
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
        self._consumer = Consumer(conf)

    def subscribe(self, topics: list[str]) -> None:
        self._consumer.subscribe(topics)

    def poll_json(self, timeout: float = 1.0) -> Optional[dict]:
        msg = self._consumer.poll(timeout)
        if msg is None:
            return None
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                return None
            self.logger.error("Kafka consume error", error=str(msg.error()), topic=msg.topic())
            return None
        try:
            return json.loads(msg.value())
        except Exception as e:
            self.logger.error("Failed to decode Kafka message", error=str(e))
            return None

    def commit(self) -> None:
        self._consumer.commit(asynchronous=True)

    def close(self) -> None:
        self._consumer.close()


