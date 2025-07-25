import traceback
from transformers import pipeline
import logging
from common.config import config
from common.base_consumer import BaseConsumer

logger = logging.getLogger(__name__)


import numpy as np


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

    def analyze_sentiment_in_chunks(
        self, text: str, chunk_size: int = 500, overlap: int = 50
    ) -> dict:
        """긴 텍스트를 조각내어 감성 분석을 실행하고, 평균 점수를 반환합니다."""

        # 텍스트가 chunk_size보다 작거나 같으면 바로 분석
        if len(text) <= chunk_size:
            return self.sentiment_pipeline(text)[0]

        # 텍스트를 조각(chunk)으로 나눔
        chunks = []
        for i in range(0, len(text), chunk_size - overlap):
            chunks.append(text[i : i + chunk_size])

        # 각 조각에 대해 감성 분석 실행
        results = self.sentiment_pipeline(chunks)

        # 점수 평균 계산
        # positive를 1, negative를 -1로 변환하여 평균 계산
        scores = []
        for res in results:
            if res["score"] >= 0.5:
                scores.append(res["score"])
            else:
                scores.append(
                    1 - res["score"]
                )  # 부정 점수는 1에서 빼서 긍정 점수로 변환

        avg_score = np.mean(scores)
        final_label = "positive" if avg_score >= 0.5 else "negative"

        return {"label": final_label, "score": avg_score}

    def process_message(self, article: dict) -> dict:
        logger.info(f"Received message: {article.get('id')}")
        content = article.get("content", "")
        if not content:
            logger.warning("내용이 없는 기사, 건너뜁니다.")
            return None

        # 감성 분석
        result = self.analyze_sentiment_in_chunks(content)
        logger.info(f"Sentiment analysis result: {result}")

        # 피처 추가
        article["sentiment"] = result["label"]
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
