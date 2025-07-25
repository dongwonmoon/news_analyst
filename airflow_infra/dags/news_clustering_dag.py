import pendulum
from airflow.decorators import dag, task
from airflow.providers.postgres.hooks.postgres import PostgresHook
import numpy as np
from sklearn.cluster import HDBSCAN
from collections import defaultdict
import logging

# 로깅 설정
logger = logging.getLogger(__name__)


@dag(
    dag_id="news_embedding_clustering",
    start_date=pendulum.datetime(2025, 7, 25, tz="Asia/Seoul"),
    schedule="*/30 * * * *",  # 30분마다 실행
    catchup=False,
    tags=["embedding", "clustering", "news"],
    doc_md="뉴스 임베딩을 주기적으로 군집화하고, 과거 ID와 연결하여 일관성을 유지합니다.",
)
def news_embedding_clustering_dag():

    @task
    def get_target_articles() -> dict:
        """DB에서 군집화 대상 기사와 ID 매핑을 위한 최신 기사 정보를 가져옵니다."""
        hook = PostgresHook(postgres_conn_id="postgres_default")

        # 1. 군집화 대상: 최근 24시간 내 cluster_id가 없는 기사
        unclustered_sql = """
            SELECT url, embedding FROM analyzed_news
            WHERE cluster_id IS NULL AND news_time >= NOW() - INTERVAL '1 day';
        """
        unclustered_records = hook.get_records(unclustered_sql)
        unclustered_articles = [
            {"url": r[0], "embedding": r[1]} for r in unclustered_records
        ]

        # 2. ID 매핑 기준: 최근 2시간 내에 이미 ID가 할당된 기사
        recent_clustered_sql = """
            SELECT url, cluster_id FROM analyzed_news
            WHERE cluster_id IS NOT NULL AND news_time >= NOW() - INTERVAL '2 hour';
        """
        recent_records = hook.get_records(recent_clustered_sql)
        recent_cluster_map = {r[0]: r[1] for r in recent_records}

        logger.info(f"군집화 대상 신규 기사: {len(unclustered_articles)}건")
        logger.info(f"ID 매핑 기준 기사: {len(recent_cluster_map)}건")

        return {"unclustered": unclustered_articles, "recent_map": recent_cluster_map}

    @task
    def perform_temporary_clustering(unclustered_articles: list[dict]) -> list[dict]:
        """가져온 기사에 대해 HDBSCAN을 실행하여 임시 클러스터 ID를 부여합니다."""
        import json

        if not unclustered_articles or len(unclustered_articles) < 3:
            logger.info("군집화할 기사가 부족하여 태스크를 건너뜁니다.")
            return []

        embeddings = np.array(
            [json.loads(article["embedding"]) for article in unclustered_articles],
            dtype=float,
        )
        clusterer = HDBSCAN(
            min_cluster_size=3, metric="cosine", allow_single_cluster=True
        )
        temp_labels = clusterer.fit_predict(embeddings)

        results = []
        for i, article in enumerate(unclustered_articles):
            if temp_labels[i] != -1:  # 노이즈(-1)가 아닌 경우에만 처리
                results.append(
                    {"url": article["url"], "temp_cluster_id": int(temp_labels[i])}
                )

        logger.info(
            f"총 {len(unclustered_articles)}개 기사를 {len(set(temp_labels))}개의 임시 군집으로 분류."
        )
        return results

    @task
    def map_and_assign_permanent_ids(
        temp_clusters: list[dict], recent_map: dict
    ) -> list[dict]:
        """임시 클러스터 ID를 기존의 영구 클러스터 ID에 매핑합니다."""
        if not temp_clusters:
            return []

        hook = PostgresHook(postgres_conn_id="postgres_default")

        # 임시 ID별로 기사(url) 목록 만들기
        temp_id_to_urls = defaultdict(list)
        for item in temp_clusters:
            temp_id_to_urls[item["temp_cluster_id"]].append(item["url"])

        permanent_id_map = {}  # {temp_id: permanent_id}

        for temp_id, urls in temp_id_to_urls.items():
            overlap_counts = defaultdict(int)
            for url in urls:
                if url in recent_map:
                    permanent_id = recent_map[url]
                    overlap_counts[permanent_id] += 1

            # 가장 많이 겹치는 기존 영구 ID를 찾음
            if overlap_counts:
                # Jaccard 유사도 또는 간단한 임계값(예: 30% 이상 겹치면)으로 판단 가능
                # 여기서는 가장 많이 겹치는 ID를 그대로 사용
                best_match_id = max(overlap_counts, key=overlap_counts.get)
                permanent_id_map[temp_id] = best_match_id
                logger.info(
                    f"임시 ID {temp_id} -> 기존 영구 ID {best_match_id}에 연결."
                )
            else:
                # 겹치는 ID가 없으면 새로운 사건으로 판단, 새 ID 발급
                new_id_record = hook.get_first("SELECT nextval('cluster_id_seq')")
                permanent_id_map[temp_id] = new_id_record[0]
                logger.info(
                    f"임시 ID {temp_id} -> 새로운 영구 ID {permanent_id_map[temp_id]} 발급."
                )

        # 최종 결과 생성: {url: permanent_cluster_id}
        results = []
        for item in temp_clusters:
            permanent_id = permanent_id_map[item["temp_cluster_id"]]
            results.append({"url": item["url"], "cluster_id": permanent_id})

        return results

    @task
    def update_permanent_cluster_ids(permanent_clusters: list[dict]):
        """결정된 영구 클러스터 ID를 DB에 업데이트합니다."""
        if not permanent_clusters:
            logger.info("업데이트할 군집 ID가 없습니다.")
            return

        hook = PostgresHook(postgres_conn_id="postgres_default")
        sql = """
        UPDATE analyzed_news 
        SET cluster_id = %(cluster_id)s 
        WHERE url = %(url)s
        """
        hook.run(
            sql,
            handler=lambda cur: cur.executemany(sql, permanent_clusters),
        )
        logger.info(
            f"총 {len(permanent_clusters)}개 기사의 영구 클러스터 ID를 업데이트했습니다."
        )

    # 태스크 실행 순서 정의
    targets = get_target_articles()
    temp_clustered_results = perform_temporary_clustering(targets["unclustered"])
    permanent_clustered_results = map_and_assign_permanent_ids(
        temp_clustered_results, targets["recent_map"]
    )
    update_permanent_cluster_ids(permanent_clustered_results)


news_embedding_clustering_dag()
