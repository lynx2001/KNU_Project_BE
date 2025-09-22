FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# ★ mysqlclient 빌드에 필요한 도구/헤더
# default-libmysqlclient-dev 가 리포에 없을 때는 libmariadb-dev 로 교체
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    default-libmysqlclient-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# (대체안)
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential \
#     pkg-config \
#     libmariadb-dev \
#     ca-certificates \
#     && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# 툴체인 먼저 최신화 → 요구사항 설치
RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install -v -r requirements.txt

COPY . .
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
