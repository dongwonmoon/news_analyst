import pendulum
import json
from airflow.decorators import dag, task
from airflow.providers.apache.kafka.hooks.produce import KafkaProducerHook
from airflow.providers.postgres.hooks.postgres import PostgresHook

KAFKA_TOPIC = "news.raw"


# Airflow DAG
@dag(
    dag_id="news_scraping_and_send_to_kafka",
    start_date=pendulum.datetime(2025, 7, 24, tz="Asia/Seoul"),
    schedule="*/10 * * * *",
    catchup=False,
    tags=["scraping", "news", "kafka"],
    doc_md="10분마다 네이버 뉴스를 스크래핑하여 PostgreSQL에 저장하고 Kafka로 전송합니다.",
)
def news_scraping_and_send_to_kafka_dag():

    @task
    def get_all_article_urls() -> list[dict]:
        from src.crawling import get_urls_from_section

        all_articles = []  # list[dict]: [{"url": str, "section_id": int}]

        # 100: 정치, 101: 경제, 102: 사회, 103: 생활/문화, 104: 세계, 105: IT/과학
        for section_id in range(100, 106):
            urls = get_urls_from_section(section_id)
            for url in urls:
                all_articles.append({"url": url, "section_id": section_id})

        # 중복 url 제거
        # 방어적. 대부분 X
        unique_articles = list({item["url"] for item in all_articles})
        print(f"Found {len(unique_articles)} unique URLs from Naver.")

        return [
            article for article in all_articles if article["url"] in unique_articles
        ]

    @task
    def filter_new_urls(articles: list[dict]) -> list[dict]:
        """
        DB에 없는 새로운 URL만 필터링합니다.
        """
        if not articles:
            return []

        all_urls = [article["url"] for article in articles]
        # Airflow Postgres Connection 사용
        hook = PostgresHook(postgres_conn_id="postgres_default")
        # 존재하는 URL 조회
        sql = "SELECT url FROM naver_news WHERE url = ANY(%s)"
        existing_urls_tuples = hook.get_records(sql, parameters=(all_urls,))
        existing_urls = {row[0] for row in existing_urls_tuples}
        # 존재하는 URL 제거
        new_articles = [
            article for article in articles if article["url"] not in existing_urls
        ]
        print(
            f"Total URLs: {len(articles)}, Existing URLs: {len(existing_urls)}, New URLs to scrape: {len(new_articles)}"
        )
        return new_articles

    @task
    def scrape_save_and_send(article: dict):
        """
        하나의 기사를 스크래핑하고, DB에 저장한 뒤 Kafka로 전송합니다.
        """
        from src.crawling import get_news_content

        url = article["url"]
        section_id = article["section_id"]

        # 1. 스크래핑
        news_data = get_news_content(url)
        if not news_data or not news_data.get("title"):
            print(f"Failed to scrape or no title for URL: {url}")
            return

        news_data["section_id"] = section_id

        # 2. DB에 저장
        hook = PostgresHook(postgres_conn_id="postgres_default")
        sql = """
            INSERT INTO naver_news (url, title, time, summary, content, section_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (url) DO NOTHING
        """
        hook.run(
            sql,
            parameters=(
                news_data["url"],
                news_data["title"],
                news_data["time"],
                news_data["summary"],
                news_data["content"],
                news_data["section_id"],
            ),
        )

        # 3. Kafka로 전송
        hook = KafkaProducerHook(kafka_config_id="kafka_default")
        producer = hook.get_producer()
        producer.produce(
            topic=KAFKA_TOPIC,
            value=json.dumps(news_data),
            key=news_data["url"].encode("utf-8"),
        )
        producer.flush()
        print(f"Sent article to Kafka: {news_data['url']}")

    # 태스트 정의
    all_articles = get_all_article_urls()
    new_articles = filter_new_urls(all_articles)

    # expand를 사용하여 분산 실행
    scrape_save_and_send.expand(article=new_articles)


news_scraping_and_send_to_kafka_dag()
