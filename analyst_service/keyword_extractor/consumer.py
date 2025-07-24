import traceback
import logging
from krwordrank.word import KRWordRank
from common.config import config
from common.base_consumer import BaseConsumer

logger = logging.getLogger(__name__)


class KeywordExtractorConsumer(BaseConsumer):
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

    def extract_keywords(self, texts, top_n=5):
        """주어진 텍스트에서 상위 N개의 키워드를 추출합니다."""
        wordrank_extractor = KRWordRank(min_count=2, max_length=10, verbose=False)
        beta = 0.85
        max_iter = 10

        keywords, rank, graph = wordrank_extractor.extract(texts, beta, max_iter)
        sorted_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)
        return [word for word, score in sorted_keywords[:top_n]]

    def process_message(self, article: dict) -> dict:
        content = article.get("content", "")
        if not content:
            logger.warning("내용이 없는 기사, 건너뜁니다.")
            return None

        # 핵심 로직: 키워드 추출
        keywords = self.extract_keywords([content])

        # 원본 데이터에 추출된 키워드 추가
        article["keywords"] = keywords

        return article


if __name__ == "__main__":
    """
    sentiment에서 받아서 keyword 컬럼 추가.
    """
    consumer = KeywordExtractorConsumer(
        input_topic_key="topic_with_sentiment",
        output_topic_key="topic_with_keywords",
        service_config_key="keyword_extractor",
    )
    consumer.run()
