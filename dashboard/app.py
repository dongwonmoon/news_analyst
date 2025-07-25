import os
from dotenv import load_dotenv

import streamlit as st
import psycopg2
import pandas as pd
from collections import Counter

from wordcloud import WordCloud
import matplotlib.pyplot as plt

load_dotenv()

# --- 페이지 기본 설정 ---
st.set_page_config(
    page_title="실시간 뉴스 트렌드 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --- DB 연결 및 데이터 로딩 (캐싱을 통한 백엔드 최적화) ---
@st.cache_resource
def get_db_connection():
    """환경 변수에서 DB 접속 정보를 가져와 연결합니다."""
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )
    return conn


@st.cache_data(ttl=300)
def load_data():
    """최근 24시간의 분석된 뉴스 데이터를 로드합니다."""
    conn = get_db_connection()
    query = """
        SELECT url, title, news_time, sentiment, sentiment_score, keywords, cluster_id
        FROM analyzed_news
        WHERE news_time >= NOW() - INTERVAL '1 day';
    """
    df = pd.read_sql_query(query, conn)
    df["news_time"] = pd.to_datetime(df["news_time"])
    return df


# --- 데이터 처리 함수 (백엔드 로직) ---
def get_wordcloud_data(df: pd.DataFrame) -> Counter:
    """데이터프레임에서 키워드를 추출하여 빈도를 계산합니다."""
    keywords = df["keywords"].dropna().sum()
    return Counter(keywords)


# --- 대시보드 UI 렌더링 ---
st.title("📊 실시간 뉴스 트렌드 대시보드")
st.markdown("지난 24시간 동안의 뉴스 트렌드를 분석합니다.")

# 데이터 로드
try:
    df = load_data()
    if df.empty:
        st.warning("지난 24시간 동안 분석된 뉴스가 없습니다.")
        st.stop()
except Exception as e:
    st.error(f"데이터베이스 연결 또는 데이터 로딩 중 오류 발생: {e}")
    st.stop()

# --- 1. 메인 브리핑 ---
st.header("📌 메인 브리핑")
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("💬 실시간 이슈 맵")
    word_counts = get_wordcloud_data(df)
    if word_counts:
        wc = WordCloud(
            font_path="font/NanumGothic.ttf",
            background_color="white",
            width=800,
            height=400,
        ).generate_from_frequencies(word_counts)
        fig, ax = plt.subplots()
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        st.pyplot(fig)
    else:
        st.text("키워드 데이터가 부족합니다.")

with col2:
    st.subheader("😊 전체 뉴스 감성 지수")
    sentiment_counts = df["sentiment"].value_counts()
    st.bar_chart(sentiment_counts)

st.subheader("📈 주요 토픽 타임라인")
timeline_df = (
    df.set_index("news_time")
    .groupby([pd.Grouper(freq="H"), "cluster_id"])
    .size()
    .unstack(fill_value=0)
)
st.line_chart(timeline_df)

# --- 2. 이슈 심층 분석 ---
st.header("🔍 이슈 심층 분석")
all_clusters = df["cluster_id"].dropna().unique().astype(int)
selected_cluster = st.selectbox(
    "분석할 토픽(군집 ID)을 선택하세요:", sorted(all_clusters)
)

if selected_cluster:
    cluster_df = df[df["cluster_id"] == selected_cluster]
    st.markdown(f"### 토픽 #{selected_cluster} 상세 정보")
    st.dataframe(
        cluster_df[["title", "news_time", "sentiment"]].sort_values(
            "news_time", ascending=False
        )
    )
