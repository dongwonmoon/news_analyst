FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y fonts-nanum*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health
CMD ["streamlit", "run", "app.py"]