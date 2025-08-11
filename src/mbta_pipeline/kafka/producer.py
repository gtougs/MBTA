"""Kafka producer wrapper for MBTA pipeline."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional
from dataclasses import dataclass

from confluent_kafka import Producer

from ..config.settings import settings
from ..utils.logging import get_logger


def _to_json_serializable(obj: Any) -> Any:
    from datetime import datetime, date
    if isinstance(obj, dict):
        return {k: _to_json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_json_serializable(v) for v in obj]
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return obj


@dataclass
class KafkaProducerWrapper:
    logger_name: str = "KafkaProducer"
    acks: str = "all"
    linger_ms: int = 10
    retries: int = 3

    def __post_init__(self) -> None:
        self.logger = get_logger(self.logger_name)
        conf = {
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "compression.type": "lz4",
            "linger.ms": self.linger_ms,
            "enable.idempotence": True,
            "acks": self.acks,
        }
        self._producer = Producer(conf)

    def _delivery_report(self, err, msg) -> None:
        if err is not None:
            self.logger.error("Kafka delivery failed", error=str(err), topic=msg.topic(), key=str(msg.key()))
        else:
            self.logger.debug("Kafka delivered", topic=msg.topic(), partition=msg.partition(), offset=msg.offset())

    def produce_json(self, topic: str, key: Optional[str], value: Dict[str, Any]) -> None:
        payload = json.dumps(_to_json_serializable(value)).encode("utf-8")
        key_bytes = key.encode("utf-8") if key is not None else None
        attempt = 0
        while True:
            try:
                self._producer.produce(topic=topic, key=key_bytes, value=payload, on_delivery=self._delivery_report)
                self._producer.poll(0)
                break
            except BufferError:
                # Queue full, wait and retry
                attempt += 1
                if attempt > self.retries:
                    raise
                time.sleep(0.05 * attempt)

    def flush(self, timeout: float = 5.0) -> None:
        self._producer.flush(timeout)


