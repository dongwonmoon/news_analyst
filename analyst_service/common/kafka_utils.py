from kafka import KafkaProducer, KafkaConsumer
import json
from common.config import load_config


def get_kafka_producer():
    """Kafka Producer 인스턴스를 생성하여 반환합니다."""
    config = load_config()
    bootstrap_servers = config["kafka"]["bootstrap_servers"]
    print(f"producer bootstrap_servers: {bootstrap_servers}")
    return KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
        acks="all",
        retries=3,
    )


def get_kafka_consumer(topic: str, group_id: str):
    """특정 토픽과 그룹 ID에 대한 Kafka Consumer 인스턴스를 생성하여 반환합니다."""
    config = load_config()
    bootstrap_servers = config["kafka"]["bootstrap_servers"]
    print(f"consumer bootstrap_servers: {bootstrap_servers}")
    return KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        group_id=group_id,
        auto_offset_reset="earliest",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        # consumer_timeout_ms=1000,
        max_poll_records=500,
    )


if __name__ == "__main__":
    from kafka import TopicPartition
    import time

    # 예시: Producer 사용
    # producer = get_kafka_producer()
    # producer.send("news.raw", {"key": "value"})
    # producer.flush()

    # 예시: Consumer 사용
    topic = "news.raw"
    partition = 0
    consumer = get_kafka_consumer(topic, "test_group")

    partitions = consumer.partitions_for_topic(topic)
    tps = [TopicPartition(topic, p) for p in partitions]

    beginning_offsets = consumer.beginning_offsets(tps)
    end_offsets = consumer.end_offsets(tps)

    total_messages = sum(end_offsets[tp] - beginning_offsets[tp] for tp in tps)
    print(f"토픽 전체 메시지 수: {total_messages}")

    for message in consumer:
        print(message.value)
        time.sleep(1)
