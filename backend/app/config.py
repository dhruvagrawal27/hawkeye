"""Application configuration — all values come from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # General
    environment: str = "development"
    log_level: str = "INFO"
    public_base_url: str = "https://hawkeye.nineagents.in"

    # Postgres
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "hawkeye"
    postgres_user: str = "hawkeye"
    postgres_password: str = "changeme_postgres"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: str = "changeme_redis"

    @property
    def redis_url(self) -> str:
        return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"

    # Kafka
    kafka_bootstrap_servers: str = "kafka:29092"
    kafka_topic: str = "hawkeye.events"
    kafka_group_id: str = "hawkeye-consumer"

    # Neo4j
    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "changeme_neo4j"

    # MinIO
    minio_endpoint: str = "minio:9000"
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "changeme_minio"
    minio_bucket: str = "hawkeye-artifacts"

    # Keycloak
    keycloak_url: str = "http://keycloak:8080"
    keycloak_realm: str = "hawkeye"
    keycloak_client_id: str = "hawkeye-backend"
    keycloak_client_secret: str = "changeme_keycloak_secret"

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"

    # Groq fallback
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"

    # MLflow
    mlflow_tracking_uri: str = "http://mlflow:5000"
    mlflow_experiment: str = "hawkeye-scoring"

    # Scoring
    model_m1_path: str = "/app/artifacts/lgb_model_m1_full.txt"
    model_m2_path: str = "/app/artifacts/lgb_model_m2_full.txt"
    feature_config_path: str = "/app/artifacts/feature_config.json"
    feature_stats_path: str = "/app/artifacts/feature_stats.json"
    shap_background_rows: int = 200
    score_trigger_every_n_events: int = 10
    score_trigger_every_n_seconds: int = 60
    alert_dedup_window_seconds: int = 3600

    # Replay
    replay_events_path: str = "/app/data/synthetic_events.jsonl"
    replay_default_rate: int = 50
    replay_max_rate: int = 5000

    # Observability
    sentry_dsn: str = ""
    grafana_admin_password: str = "changeme_grafana"


@lru_cache
def get_settings() -> Settings:
    return Settings()
