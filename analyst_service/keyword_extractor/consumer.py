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
        # 불용어 리스트 추가
        self.stopwords = set([
            '있다', '말했다', '있습니다', '없다', '위해', '대한', '그리고', '하지만', '그러나',
            '따르면', '등', '통해', '오전', '오후', '지난', '올해', '내년', '최근',
            '가장', '많이', '더', '큰', '수', '것', '그', '이', '저', '것으로',
            '보인다', '밝혔다', '전했다', '이어', '대해', '바로', '때문', '같은', '함께',
            '기자', '뉴스', '사진', '헤럴드경제', '연합뉴스', '뉴시스', '뉴스1', '노컷뉴스',
            '파이낸셜뉴스', '아시아경제', '머니투데이', '이데일리', '조선일보', '중앙일보',
            '동아일보', '한겨레', '경향신문', '한국일보', '서울신문', '세계일보', '국민일보'
        ])
        logger.info("KeywordExtractorConsumer is initialized.")

    def extract_keywords(self, texts, top_n=5):
        """주어진 텍스트에서 상위 N개의 키워드를 추출하고 불용어를 제거합니다."""
        wordrank_extractor = KRWordRank(min_count=2, max_length=10, verbose=False)
        beta = 0.85
        max_iter = 10

        keywords, rank, graph = wordrank_extractor.extract(texts, beta, max_iter)
        
        # 불용어 제거 및 정렬
        filtered_keywords = {
            word: score for word, score in keywords.items() if word not in self.stopwords
        }
        
        sorted_keywords = sorted(filtered_keywords.items(), key=lambda x: x[1], reverse=True)
        return [word for word, score in sorted_keywords[:top_n]]

    def process_message(self, article: dict) -> dict:
        logger.info(f"Received message: {article.get('id')}")
        content = article.get("content", "")
        if not content:
            logger.warning("내용이 없는 기사, 건너뜁니다.")
            return None

        # 핵심 로직: 키워드 추출
        keywords = self.extract_keywords([content])
        logger.info(f"Extracted keywords: {keywords}")

        # 원본 데이터에 추출된 키워드 추가
        article["keywords"] = keywords
        logger.info(f"Sending message with keywords: {article.get('id')}")

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
