# 1. 베이스 이미지 선택
FROM python:3.10-slim

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. 폰트 설치 (워드클라우드 한글 깨짐 방지)
RUN apt-get update && apt-get install -y fonts-nanum*
RUN fc-cache -fv # 폰트 캐시 업데이트

# 4. 필요한 라이브러리 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. 애플리케이션 코드 복사
COPY . .
COPY font/ /app/font/

# 6. Streamlit 실행 포트 노출
EXPOSE 8501

# 7. 애플리케이션 실행
# HEALTHCHECK: Streamlit 기본 healthcheck 엔드포인트 사용
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health
# CMD: Streamlit 실행
CMD ["streamlit", "run", "app.py"]