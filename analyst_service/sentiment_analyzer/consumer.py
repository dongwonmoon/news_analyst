import traceback
from transformers import pipeline
import logging
from common.config import config
from common.base_consumer import BaseConsumer

logger = logging.getLogger(__name__)


class SentimentAnalyzerConsumer(BaseConsumer):
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
        # 모델 로드
        model_name = self.service_config["model_name"]
        logger.info(f"감성 분석 모델({model_name})을 로드합니다.")
        self.sentiment_pipeline = pipeline(
            "sentiment-analysis", model=model_name, device=-1
        )
        logger.info("감성 분석 모델 로드 완료.")

    def process_message(self, article: dict) -> dict:
        logger.info(f"Received message: {article.get('id')}")
        content = article.get("content", "")
        if not content:
            logger.warning("내용이 없는 기사, 건너뜁니다.")
            return None

        # 감성 분석
        result = self.sentiment_pipeline(content[:512])[0]
        logger.info(f"Sentiment analysis result: {result}")

        # 피처 추가
        article["sentiment"] = "positive" if result["score"] > 0.5 else "negative"
        article["sentiment_score"] = result["score"]
        logger.info(f"Sending message with sentiment: {article.get('id')}")

        return article


if __name__ == "__main__":
    """
    sentiment에서 받아서 keyword 컬럼 추가.
    """
    consumer = SentimentAnalyzerConsumer(
        input_topic_key="topic_raw",
        output_topic_key="topic_with_sentiment",
        service_config_key="sentiment_analyzer",
    )
    consumer.run()
