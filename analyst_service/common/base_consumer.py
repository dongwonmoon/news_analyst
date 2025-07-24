import traceback
from abc import ABC, abstractmethod
import logging
from common.kafka_utils import get_kafka_consumer, get_kafka_producer
from common.config import config

logger = logging.getLogger(__name__)


class BaseConsumer(ABC):
    def __init__(
        self,
        input_topic_key: str,
        output_topic_key: str = None,
        service_config_key: str = None,
    ):
        self.input_topic = config["kafka"][input_topic_key]
        self.output_topic = (
            config["kafka"][output_topic_key] if output_topic_key else None
        )
        self.service_config = (
            config["kafka"]["services"][service_config_key]
            if service_config_key
            else None
        )
        self.group_id = (
            self.service_config["group_id"]
            if self.service_config and "group_id" in self.service_config
            else None
        )

        if not self.group_id:
            raise ValueError(
                f"group_id is not defined for service_config_key: {service_config_key}"
            )
        self.consumer = get_kafka_consumer(self.input_topic, self.group_id)
        self.producer = get_kafka_producer()

        logger.info(f"'{self.input_topic}' 토픽 구독 시작")
        if self.output_topic:
            logger.info(f" -> '{self.output_topic}'으로 발행")

    @abstractmethod
    def process_message(self, message_value: dict) -> dict:
        """각 서비스의 핵심 로직을 구현하는 추상 메서드"""
        pass

    def run(self):
        self.consumer.subscribe([self.input_topic])
        while True:
            try:
                # poll()을 사용하여 메시지 배치 처리
                messages = self.consumer.poll(timeout_ms=1000, max_records=500)
                if not messages:
                    continue

                for tp, consumer_records in messages.items():
                    for message in consumer_records:
                        try:
                            processed_data = self.process_message(message.value)
                            if self.output_topic and processed_data:
                                self.producer.send(
                                    self.output_topic, value=processed_data
                                )
                                logger.info(
                                    f"Offset {message.offset}: 메시지 처리 및 '{self.output_topic}'으로 전송 완료"
                                )
                            elif not self.output_topic:
                                logger.info(
                                    f"Offset {message.offset}: 메시지 처리 완료 (최종 단계)"
                                )

                        except Exception as e:
                            logger.error(
                                f"Offset {message.offset} 메시지 처리 중 오류 발생: {e}"
                            )
                            traceback.print_exc()

            except Exception as e:
                logger.error(f"Kafka 소비 중 오류: {e}")
                traceback.print_exc()
            finally:
                self.producer.flush()
