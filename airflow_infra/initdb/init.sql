CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS naver_news (
    id SERIAL PRIMARY KEY,
    url TEXT UNIQUE,
    title TEXT NOT NULL,
    time TIMESTAMP,
    summary TEXT,
    content TEXT,
    section_id INT
);

-- 최종 분석 데이터를 저장할 테이블 생성
CREATE TABLE IF NOT EXISTS analyzed_news (
    url VARCHAR(255) PRIMARY KEY,
    section_id INT,
    title TEXT,
    summary TEXT,
    content TEXT,
    news_time TIMESTAMP,
    sentiment VARCHAR(50),
    sentiment_score FLOAT,
    keywords TEXT[],
    embedding VECTOR(768),
    cluster_id INT
);

CREATE INDEX IF NOT EXISTS analyzed_news_embedding_idx ON analyzed_news USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE SEQUENCE IF NOT EXISTS cluster_id_seq START 1;