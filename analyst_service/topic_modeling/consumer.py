import logging
from sentence_transformers import SentenceTransformer
from common.base_consumer import BaseConsumer
from airflow.providers.postgres.hooks.postgres import PostgresHook

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingGenerator(BaseConsumer):
    """
    Kafka에서 메시지를 받아 임베딩을 생성하고, PostgreSQL의 analyzed_news 테이블에 저장하는 컨슈머.
    """

    def __init__(
        self,
        input_topic_key: str,
        output_topic_key: str = None,
        service_config_key: str = None,
    ):
        # 이 컨슈머는 다음 토픽으로 메시지를 보내지 않으므로, produce_topic은 None으로 설정
        super().__init__(
            input_topic_key=input_topic_key,
            output_topic_key=output_topic_key,
            service_config_key=service_config_key,
        )
        # 한국어 특화 SBERT 모델 로드
        self.model = SentenceTransformer("jhgan/ko-sroberta-multitask", device="cpu")
        self.pg_hook = PostgresHook(postgres_conn_id="postgres_default")
        logger.info("EmbeddingGenerator 초기화 완료.")

    def process_message(self, message: dict) -> None:
        """
        메시지를 처리하여 임베딩을 생성하고 DB에 저장합니다.
        BaseConsumer의 추상 메소드를 구현합니다.
        """
        try:
            content_to_embed = message.get("content", "")
            if not content_to_embed:
                logger.warning("메시지에 content가 없어 임베딩을 생성할 수 없습니다.")
                return

            # 문장 임베딩 생성
            embedding = self.model.encode(
                content_to_embed, convert_to_tensor=False
            ).tolist()

            # DB에 저장할 데이터 준비
            record = {
                "url": message.get("url"),
                "section_id": message.get("section_id"),
                "title": message.get("title"),
                "summary": message.get("summary"),
                "content": message.get("content"),
                "news_time": message.get("time"),
                "sentiment": message.get("sentiment", {}).get("label"),
                "sentiment_score": message.get("sentiment", {}).get("score"),
                "keywords": message.get("keywords"),
                "embedding": embedding,
            }

            self.save_to_db(record)

        except Exception as e:
            logger.error(f"메시지 처리 중 오류 발생: {e}\n메시지: {message}")

        # 이 서비스는 다음 카프카 토픽으로 데이터를 보내지 않으므로 None을 반환
        return None

    def save_to_db(self, record: dict):
        """준비된 레코드를 analyzed_news 테이블에 삽입/업데이트합니다."""
        sql = """
            INSERT INTO analyzed_news (
                url, section_id, title, summary, content, news_time,
                sentiment, sentiment_score, keywords, embedding
            ) VALUES (
                %(url)s, %(section_id)s, %(title)s, %(summary)s, %(content)s, %(news_time)s,
                %(sentiment)s, %(sentiment_score)s, %(keywords)s, %(embedding)s
            )
            ON CONFLICT (url) DO UPDATE SET
                section_id = EXCLUDED.section_id,
                title = EXCLUDED.title,
                summary = EXCLUDED.summary,
                content = EXCLUDED.content,
                news_time = EXCLUDED.news_time,
                sentiment = EXCLUDED.sentiment,
                sentiment_score = EXCLUDED.sentiment_score,
                keywords = EXCLUDED.keywords,
                embedding = EXCLUDED.embedding;
        """
        try:
            conn = self.pg_hook.get_conn()
            with conn.cursor() as cursor:
                cursor.execute(sql, record)
            conn.commit()
            logger.info(f"뉴스 저장/업데이트 성공: {record['url']}")
        except Exception as e:
            logger.error(f"DB 저장 중 오류 발생: {e}")


if __name__ == "__main__":
    consumer = EmbeddingGenerator(
        input_topic_key="topic_with_keywords",
        output_topic_key=None,
        service_config_key="topic_modeler",
    )
    consumer.run()
