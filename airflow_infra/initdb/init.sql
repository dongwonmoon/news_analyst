CREATE TABLE IF NOT EXISTS naver_news (
    id SERIAL PRIMARY KEY,
    url TEXT UNIQUE,
    title TEXT NOT NULL,
    time TIMESTAMP,
    summary TEXT,
    content TEXT,
    section_id INT
);

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
    topic_id INT -- Topic ID ?
);