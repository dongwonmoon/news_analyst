import os
import yaml
from dotenv import load_dotenv


def load_config():
    # 서비스 루트 디렉토리 (analyst_service)
    service_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 프로젝트 루트 디렉토리 (news_analyst)
    project_root = os.path.dirname(service_root)

    # 프로젝트 루트의 .env 파일 로드
    dotenv_path = os.path.join(project_root, ".env")
    load_dotenv(dotenv_path=dotenv_path)

    # ENV 변수를 .env 파일에서 읽어옴
    env = os.getenv("ENV", "dev")

    # 설정 파일 경로 계산
    config_path = os.path.join(service_root, f"config/config.{env}.yaml")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # --- 데이터베이스 설정 ---
    # 'database' 키가 config에 없을 경우를 대비
    if "database" not in config:
        config["database"] = {}
    db_keys = ["host", "port", "db", "user", "password"]
    for key in db_keys:
        env_var = f"POSTGRES_{key.upper()}"
        if os.getenv(env_var):
            config["database"][key] = os.getenv(env_var)

    # --- Kafka 설정 ---
    kafka_bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
    if kafka_bootstrap_servers:
        config["kafka"]["bootstrap_servers"] = kafka_bootstrap_servers

    return config


config = load_config()
