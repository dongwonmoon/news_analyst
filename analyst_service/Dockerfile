FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    default-jdk \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

# JAVA_HOME 환경 변수 설정
ENV JAVA_HOME /usr/lib/jvm/default-java