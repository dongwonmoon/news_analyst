# News Analyst Project

## 1. 프로젝트 개요

본 프로젝트는 실시간으로 뉴스를 수집하고 자연어 처리(NLP) 기술을 통해 분석하여, 주요 트렌드와 이슈를 시각적으로 제공하는 데이터 파이프라인 시스템입니다. Kafka를 이용한 비동기 메시지 큐잉, Airflow를 이용한 워크플로우 오케스트레이션, 그리고 Streamlit을 이용한 대시보드를 통해 전체 과정을 자동화하고 사용자에게 인사이트를 제공합니다.

## 2. 시스템 아키텍처

```
+----------------+      +-------+      +----------------------+      +-------+      +-------------------+      +-------+      +----------------+
|                |----->|       |----->|                      |----->|       |----->|                   |----->|       |----->|                |
|  News Scraper  |      | Kafka |      | Sentiment Analyzer   |      | Kafka |      | Keyword Extractor |      | Kafka |      |  Topic Modeler |
|                |----->| topic |----->| (Consumer)           |----->| topic |----->| (Consumer)        |----->| topic |----->|  (Consumer)    |
|                |      | _raw  |      |                      |      | _with |      |                   |      | _with |      |                |
+----------------+      +-------+      +----------------------+      |_sentim|      +-------------------+      |_keywor|      +-------+--------+
                                                                     | ent   |                                  | ds    |             |
                                                                     +-------+                                  +-------+             |
                                                                                                                                     |
                                                                                                                                     v
                                                                                                                             +----------------+
                                                                                                                             |                |
                                                                                                                             |  PostgreSQL    |
                                                                                                                             | (analyzed_news)|
                                                                                                                             |                |
                                                                                                                             +-------+--------+
                                                                                                                                     ^
                                                                                                                                     |
+--------------------------+      +------------------------+                                                                         |
|                          |----->|                        |                                                                         |
|  Airflow                 |      |  PostgreSQL            |-------------------------------------------------------------------------+
| (news_clustering_dag)    |----->|  (Airflow Backend)     |
|                          |      |                        |
+--------------------------+      +------------------------+
```

**데이터 흐름:**

1.  **뉴스 수집:** 외부 스크레이퍼가 뉴스를 수집하여 Kafka의 `topic_raw` 토픽으로 전송합니다.
2.  **감성 분석:** `Sentiment Analyzer` 서비스가 `topic_raw` 토픽의 뉴스를 소비(consume)하여 감성 분석을 수행하고, 결과를 `sentiment`와 `sentiment_score` 필드에 추가하여 `topic_with_sentiment` 토픽으로 발행(produce)합니다.
3.  **키워드 추출:** `Keyword Extractor` 서비스가 `topic_with_sentiment` 토픽의 뉴스를 소비하여 키워드를 추출하고, `keywords` 필드를 추가하여 `topic_with_keywords` 토픽으로 발행합니다.
4.  **임베딩 및 저장:** `Topic Modeler` 서비스가 `topic_with_keywords` 토픽의 뉴스를 소비하여 기사 내용에 대한 벡터 임베딩(vector embedding)을 생성합니다. 최종적으로 분석된 모든 데이터(감성, 키워드, 임베딩 등)를 PostgreSQL의 `analyzed_news` 테이블에 저장/업데이트합니다.
5.  **뉴스 군집화:** Airflow의 `news_embedding_clustering` DAG가 30분마다 스케줄링되어 실행됩니다.
    *   DB에서 최근 24시간 동안 군집화되지 않은 뉴스를 가져옵니다.
    *   HDBSCAN 알고리즘을 사용하여 뉴스들을 클러스터링하고, 기존 클러스터와 비교하여 일관된 `cluster_id`를 부여합니다.
    *   군집화 결과를 다시 `analyzed_news` 테이블에 업데이트합니다.
6.  **시각화:** Streamlit으로 구현된 `Dashboard`가 PostgreSQL DB에 직접 연결하여, 최근 24시간의 분석 결과를 차트와 워드클라우드 형태로 시각화하여 보여줍니다.

## 3. 주요 구성 요소

### 3.1. Analyst Service

뉴스 분석의 핵심 로직을 담당하는 마이크로서비스들로 구성됩니다. 각 서비스는 독립적인 Kafka 컨슈머로 동작합니다.

*   **`sentiment_analyzer`**: `transformers` 라이브러리를 사용하여 기사 내용의 긍정/부정을 분석합니다.
*   **`keyword_extractor`**: `krwordrank` 라이브러리를 사용하여 기사의 핵심 키워드를 추출합니다.
*   **`topic_modeling`**: `sentence-transformers` 라이브러리(`ko-sroberta-multitask` 모델)를 사용하여 기사 내용을 다차원 벡터로 변환(임베딩)하고, 최종 분석 결과를 DB에 저장합니다.

### 3.2. Airflow Infrastructure

데이터 파이프라인의 워크플로우를 관리하고 스케줄링합니다.

*   **`news_embedding_clustering` DAG**: 30분 주기로 실행되며, `analyzed_news` 테이블의 데이터를 기반으로 뉴스 군집화를 수행합니다. 이 과정을 통해 유사한 주제의 뉴스들을 그룹화하여 '토픽'을 형성합니다.

### 3.3. Dashboard

`Streamlit`으로 제작된 사용자 인터페이스로, 분석 결과를 시각적으로 탐색할 수 있는 기능을 제공합니다.

*   **실시간 이슈 맵**: 주요 키워드를 워드클라우드로 시각화합니다.
*   **전체 뉴스 감성 지수**: 전체 뉴스의 긍정/부정 비율을 막대 차트로 보여줍니다.
*   **주요 토픽 타임라인**: 시간대별 주요 토픽(군집)의 뉴스 양을 꺾은선 그래프로 보여줍니다.
*   **이슈 심층 분석**: 특정 토픽(군집 ID)을 선택하여 해당 토픽에 속한 기사 목록을 확인할 수 있습니다.

### 3.4. 기술 스택

*   **Workflow Orchestration**: Apache Airflow
*   **Message Queue**: Apache Kafka
*   **Database**: PostgreSQL
*   **Backend**: Python, Kafka-Python
*   **NLP / Machine Learning**:
    *   `transformers`
    *   `sentence-transformers`
    *   `krwordrank`
    *   `scikit-learn` (HDBSCAN)
*   **Dashboard**: Streamlit
*   **Infrastructure**: Docker, Docker Compose

## 4. 실행 방법

### 4.1. 사전 요구사항

*   Docker
*   Docker Compose

### 4.2. 실행

1.  프로젝트 루트 디렉토리에서 `.env.example` 파일을 `.env` 파일로 복사하고, 필요에 따라 내부 환경 변수(DB 접속 정보, Kafka IP 등)를 수정합니다.

    ```bash
    cp .env.example .env
    ```

2.  아래 명령어를 사용하여 모든 서비스를 실행합니다.

    ```bash
    docker-compose up --build -d
    ```

### 4.3. 서비스 접근

*   **Airflow Webserver**: `http://localhost:8080`
*   **Dashboard**: `http://localhost:8501`
*   **PostgreSQL**: `localhost:5432`
*   **Kafka**: `localhost:29092`

## 5. 프로젝트 구조

```
.
├── analyst_service/      # 뉴스 분석을 위한 Kafka 컨슈머 서비스
│   ├── common/           # Kafka 컨슈머, 설정 등 공통 모듈
│   ├── keyword_extractor/ # 키워드 추출 컨슈머
│   ├── sentiment_analyzer/ # 감성 분석 컨슈머
│   └── topic_modeling/   # 토픽 모델링(임베딩) 및 DB 저장 컨슈머
├── airflow_infra/        # Airflow 실행을 위한 인프라 및 DAG
│   ├── dags/             # Airflow DAG 파일
│   │   └── news_clustering_dag.py
│   └── initdb/           # DB 초기화를 위한 SQL 스크립트
├── dashboard/            # Streamlit 대시보드 애플리케이션
│   └── app.py
├── docker-compose.yaml   # 전체 서비스 정의 및 실행을 위한 Docker Compose 파일
├── Dockerfile            # 각 서비스 빌드를 위한 Dockerfile
└── README.md             # 프로젝트 설명서
```