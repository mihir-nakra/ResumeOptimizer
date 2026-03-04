"""
Application configuration using pydantic-settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_env: str = "development"

    # LLM API Keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # AWS Configuration
    aws_region: str = "us-east-1"

    # Kafka Configuration
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_resume_parsed: str = "resume.parsed"
    kafka_topic_ats_optimized: str = "resume.ats_optimized"
    kafka_topic_suggestions: str = "resume.suggestions"
    kafka_topic_interviews: str = "interview.questions"


    # OpenTelemetry Configuration
    otel_service_name: str = "resume-optimizer"
    otel_exporter_prometheus_port: int = 8001

    # Agent Configuration
    max_retries: int = 3
    timeout_seconds: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
