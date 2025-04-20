import os
from pydantic import Field, model_validator, field_validator
from pydantic_settings import BaseSettings
from typing import Optional, Union, Literal
from src.constraints import DEFAULT_LOG_LEVEL, DEFAULT_POOL_CONN_RETRIES, DEFAULT_POOL_CONN_RETRY_DELAY, DEFAULT_DEV_PORT, DEFAULT_DEV_HOST, DEFAULT_DEV_PROTOCOL, DEFAULT_FRONTEND_LANGUAGE, DEFAULT_POSTGRES_HOST, DEFAULT_POSTGRES_PORT, DEFAULT_POSTGRES_DB, DEFAULT_POSTGRES_USER, DEFAULT_POSTGRES_PASSWORD, DEFAULT_POOL_MINCONN, DEFAULT_POOL_MAXCONN, DEFAULT_REDIS_PASSWORD, DEFAULT_REDIS_USER, DEFAULT_REDIS_USER_PASSWORD, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT, DEFAULT_REDIS_POOL_SIZE, DEFAULT_REDIS_DB, DEFAULT_REDIS_EX
from src.models.constraints import DEFAULT_OPENAI_BASE_URL
from src.exceptions import PublicKeyMissingException
from src.types import Language


# Database connection parameters
class PostgresSettings(BaseSettings):
    host: str = Field(DEFAULT_POSTGRES_HOST, env="POSTGRES_HOST")
    port: int = Field(DEFAULT_POSTGRES_PORT, env="POSTGRES_PORT")
    user: str = Field(DEFAULT_POSTGRES_USER, env="POSTGRES_USER")
    password: str = Field(DEFAULT_POSTGRES_PASSWORD, env="POSTGRES_PASSWORD")
    dbname: str = Field(DEFAULT_POSTGRES_DB, env="POSTGRES_DB")
    pool_conn_retries: int = DEFAULT_POOL_CONN_RETRIES
    pool_conn_retry_delay: int = DEFAULT_POOL_CONN_RETRY_DELAY
    minconn: int = Field(DEFAULT_POOL_MINCONN, env="POOL_MINCONN")
    maxconn: int = Field(DEFAULT_POOL_MAXCONN, env="POOL_MAXCONN")
        
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

    def set_public_api_key(self, public_pem: str) -> None:
        if not public_pem:
            raise ValueError("Attempted setting empty public key")
        self.public_api_key = public_pem
        os.environ["PUBLIC_API_KEY"] = public_pem

    def get_public_api_key(self) -> str:
        public_pem = self.public_api_key
        env_public_pem = os.getenv("PUBLIC_API_KEY", None)
        if not env_public_pem and not public_pem:
            raise PublicKeyMissingException()
        if not env_public_pem:
            os.environ["PUBLIC_API_KEY"] = public_pem
            return public_pem
        if not public_pem:
            self.public_api_key = env_public_pem
            return env_public_pem
        if public_pem != env_public_pem:
            self.public_api_key = env_public_pem
            return env_public_pem
        return public_pem

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


class FrontendSettings(BaseSettings):
    default_language: Language = Field(DEFAULT_FRONTEND_LANGUAGE, env="DEFAULT_FRONTEND_LANGUAGE")


class RedisSettings(BaseSettings):
    host: str = Field(DEFAULT_REDIS_HOST, env="REDIS_HOST")
    port: int = Field(DEFAULT_REDIS_PORT, env="REDIS_PORT")
    password: str = Field(DEFAULT_REDIS_PASSWORD, env="REDIS_PASSWORD")
    user: str = Field(DEFAULT_REDIS_USER, env="REDIS_USER")
    user_password: str = Field(DEFAULT_REDIS_USER_PASSWORD, env="REDIS_USER_PASSWORD")
    pool_size: int = Field(DEFAULT_REDIS_POOL_SIZE, env="REDIS_POOL_SIZE")
    db: int = Field(DEFAULT_REDIS_DB, env="REDIS_DB")
    ex: int = DEFAULT_REDIS_EX

    @property
    def url(self) -> str:
        return f"redis://@{self.host}:{self.port}/{self.db}"


class Settings(BaseSettings):
    postgres: PostgresSettings = PostgresSettings()
    logging: LoggingSettings = LoggingSettings()
    server: ServerSettings = ServerSettings()
    openai: OpenAISettings = OpenAISettings()
    frontend: FrontendSettings = FrontendSettings()
    redis: RedisSettings = RedisSettings()


settings = Settings()
