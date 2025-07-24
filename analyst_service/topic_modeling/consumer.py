import traceback
import os
import logging
from bertopic import BERTopic
from common.config import config
from common.base_consumer import BaseConsumer

logger = logging.getLogger(__name__)


class TopicModelingConsumer(BaseConsumer):
    def __init__(
        self,
        input_topic_key: str,
        output_topic_key: str = None,
        service_config_key: str = None,
    ):
        super().__init__(
            input_topic_key=input_topic_key,
            output_topic_key=output_topic_key,
            service_config_key=service_config_key,
        )
        # BERTopic 모델 로드
        model_path = self.service_config["model_path"]
        if os.path.exists(model_path):
            logger.info(f"저장된 BERTopic 모델({model_path})을 로드합니다.")
            self.topic_model = BERTopic.load(model_path)
            logger.info("BERTopic 모델 로드 완료.")
        else:
            logger.error(f"오류: 학습된 모델을 찾을 수 없습니다. 경로: {model_path}")
            exit()  # 학습된 모델이 없으면 실행을 중단합니다.

    def process_message(self, article: dict) -> dict:
        content = article.get("content", "")
        if not content:
            return None

        # 토픽 예측
        topics, _ = self.topic_model.transform([content])
        topic_id = topics[0]
        topic_keyword_tuples = self.topic_model.get_topic(topic_id)
        topic_keywords = (
            [word for word, score in topic_keyword_tuples]
            if topic_keyword_tuples
            else []
        )

        # 최종 피처 추가
        article["topic_id"] = topic_id
        article["topic_keywords"] = topic_keywords

        return article


if __name__ == "__main__":
    consumer = TopicModelingConsumer(
        input_topic_key="topic_with_keywords",
        output_topic_key="topic_processed",
        service_config_key="topic_modeler",
    )
    consumer.run()
