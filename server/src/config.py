import os
from pydantic import Field, model_validator, field_validator
from pydantic_settings import BaseSettings
from typing import Optional, Union, Literal
from src.constraints import DEFAULT_LOG_LEVEL, DEFAULT_POOL_CONN_RETRIES, DEFAULT_POOL_CONN_RETRY_DELAY, DEFAULT_DEV_PORT, DEFAULT_DEV_HOST, DEFAULT_DEV_PROTOCOL
from src.models.constraints import DEFAULT_OPENAI_BASE_URL
from src.exceptions import PublicKeyMissingException


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


class Settings(BaseSettings):
    postgres: PostgresSettings = PostgresSettings()
    logging: LoggingSettings = LoggingSettings()
    server: ServerSettings = ServerSettings()
    openai: OpenAISettings = OpenAISettings()


settings = Settings()
