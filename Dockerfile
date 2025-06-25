# 베이스 이미지
FROM python:3.13-slim

# 환경 변수
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 작업 디렉토리
WORKDIR /app

# requirements.txt 복사
COPY requirements.txt .

# 라이브러리 설치
RUN pip install --no-cache-dir -r requirements.txt

# 나머지 소스 코드 복사
COPY . .

# 실행 명령어
CMD ["python", "main.py"]