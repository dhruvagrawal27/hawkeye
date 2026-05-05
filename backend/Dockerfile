FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl libpq-dev git && \
    rm -rf /var/lib/apt/lists/*

# Install pip deps
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir hatchling && \
    pip install --no-cache-dir -e ".[dev]" || true && \
    pip install --no-cache-dir \
        fastapi uvicorn[standard] pydantic pydantic-settings \
        sqlalchemy alembic asyncpg psycopg2-binary \
        redis[hiredis] confluent-kafka neo4j \
        lightgbm shap numpy pandas pyarrow \
        langchain langchain-anthropic langchain-community anthropic \
        python-jose[cryptography] httpx tenacity structlog \
        prometheus-client minio mlflow sentry-sdk[fastapi] \
        python-multipart websockets pytest pytest-asyncio \
        pytest-cov ruff mypy

COPY . .

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
