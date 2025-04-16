# server/src/config.py
from pydantic import Field, model_validator, field_validator
from pydantic_settings import BaseSettings
from typing import Optional, Union, Literal
from src.constraints import DEFAULT_LOG_LEVEL, DEFAULT_POOL_CONN_RETRIES, DEFAULT_POOL_CONN_RETRY_DELAY, DEFAULT_DEV_PORT, DEFAULT_DEV_HOST, DEFAULT_DEV_PROTOCOL
from src.models.constraints import DEFAULT_OPENAI_BASE_URL


# Database connection parameters
class PostgresSettings(BaseSettings):
    host: str = Field("postgres", env="POSTGRES_HOST")
    port: int = Field(5432, env="POSTGRES_PORT")
    user: str = Field("postgres", env="POSTGRES_USER")
    password: str = Field("postgres", env="POSTGRES_PASSWORD")
    dbname: str = Field("postgres", env="POSTGRES_DB")
    pool_conn_retries: int = DEFAULT_POOL_CONN_RETRIES
    pool_conn_retry_delay: int = DEFAULT_POOL_CONN_RETRY_DELAY
    minconn: int = Field(2, env="POOL_MINCONN")
    maxconn: int = Field(20, env="POOL_MAXCONN")
        
    @property
    def dsn(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}"


class LoggingSettings(BaseSettings):
    log_level: str = Field(DEFAULT_LOG_LEVEL, env="LOG_LEVEL")
    
    @model_validator(mode="after")
    def validate_log_level(self):
        valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        if self.log_level not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of {valid_levels}")
        return self


class ServerSettings(BaseSettings):
    protocol: Literal["http", "https"] = DEFAULT_DEV_PROTOCOL
    host: str = Field(DEFAULT_DEV_HOST, min_length=1)
    port: str = DEFAULT_DEV_PORT
    public_api_key: str = Field(None, env="PUBLIC_API_KEY")

    @property
    def url(self) -> str:
        return self.protocol + "://" + self.host + ":" + self.port

    @field_validator("port", mode="after")
    @classmethod
    def validate_port(cls, value: str) -> str:
        try:
            port_int = int(value)
        except ValueError:
            raise ValueError('Port must be an integer represented as a string.')

        if not (0 <= port_int <= 65535):
            raise ValueError('Port must be between 0 and 65535.')

        return value

class OpenAISettings(BaseSettings):
    base_url: str = Field(DEFAULT_OPENAI_BASE_URL, env="OPENAI_BASE_URL")


class Settings(BaseSettings):
    postgres: PostgresSettings = PostgresSettings()
    logging: LoggingSettings = LoggingSettings()
    server: ServerSettings = ServerSettings()
    openai: OpenAISettings = OpenAISettings()


settings = Settings()
