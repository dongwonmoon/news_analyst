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

    # --- 모델 경로를 절대 경로로 변환 (컨테이너 호환) ---
    # config.yaml에 정의된 경로는 topic_modeling 디렉토리 기준 상대 경로임
    # 예: "models/bertopic_model"
    relative_model_path = config["kafka"]["services"]["topic_modeler"]["model_path"]
    # service_root를 기준으로 절대 경로 생성
    absolute_model_path = os.path.join(
        service_root, "topic_modeling", relative_model_path
    )
    config["kafka"]["services"]["topic_modeler"]["model_path"] = absolute_model_path

    # --- 데이터베이스 설정 ---
    # 'database' 키가 config에 없을 경우를 대비
    if "database" not in config:
        config["database"] = {}
    db_keys = ["host", "port", "dbname", "user", "password"]
    for key in db_keys:
        env_var = f"DB_{key.upper()}"
        if os.getenv(env_var):
            config["database"][key] = os.getenv(env_var)

    # --- Kafka 설정 ---
    kafka_bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
    if kafka_bootstrap_servers:
        config["kafka"]["bootstrap_servers"] = kafka_bootstrap_servers

    return config


config = load_config()
