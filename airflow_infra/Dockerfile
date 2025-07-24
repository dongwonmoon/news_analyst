FROM apache/airflow:3.0.3

USER root
RUN apt-get update && apt-get install -y gcc

USER airflow
RUN pip install --no-cache-dir \
    apache-airflow-providers-apache-kafka