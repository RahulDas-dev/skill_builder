"""configs/main_conf.py — merges per-concern settings via multiple inheritance.

Pair with configs/__init__.py:
    from .main_conf import AppConfig
    app_conf = AppConfig()          # single instantiation point
    __all__ = ("AppConfig", "app_conf")
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class DeploymentConfig(BaseSettings):
    environment: str = "local"


class LoggingConfig(BaseSettings):
    log_level: str = "INFO"


class DatabaseConfig(BaseSettings):
    database_url: str


class AppConfig(DeploymentConfig, LoggingConfig, DatabaseConfig):
    model_config = SettingsConfigDict(env_file=".env", frozen=True, extra="ignore")
