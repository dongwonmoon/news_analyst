FROM postgres:13

# 빌드를 위한 툴과 pgvector 소스 설치
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      git \
      build-essential \
      postgresql-server-dev-13 \
 && git clone --depth 1 https://github.com/pgvector/pgvector.git /usr/src/pgvector \
 && cd /usr/src/pgvector \
 && make && make install \
 && cd / \
 && rm -rf /usr/src/pgvector \
 && apt-get purge -y --auto-remove git build-essential postgresql-server-dev-13 \
 && rm -rf /var/lib/apt/lists/*
