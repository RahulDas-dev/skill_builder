# Config Singleton Pattern

## Overview

Configuration is split into focused `BaseSettings` subclasses — one file per concern — then merged into a single class via multiple inheritance. That class is instantiated **once** at module import time in `__init__.py` and exported as a module-level singleton.

---

## Directory Layout

```
configs/
├── __init__.py          # Single instantiation point → exports app_conf singleton
├── deployment_conf.py   # HOST, PORT, ENV, DEBUG, TIMEZONE, CORS, APP_NAME
├── db_conf.py           # DB connection fields + @property helpers (database_url, driver, etc.)
├── feature_conf.py      # Feature flags + external service URLs
├── log_conf.py          # LOG_LEVEL, LOG_FORMAT, LOG_DIR, rotation settings
└── <name>_conf.py       # Add one file per new concern — never add to an existing file
```

---

## Pattern: One `BaseSettings` Subclass Per Concern

Each file defines **one class** that owns its slice of config. Use `Field()` with `description=` on every field.

```python
# configs/deployment_conf.py
from enum import Enum
from pydantic import Field, PositiveInt
from pydantic_settings import BaseSettings


class Environment(str, Enum):
    PRODUCTION = "PRODUCTION"
    STAGING = "STAGING"
    DEVELOPMENT = "DEVELOPMENT"


class DeploymentConfig(BaseSettings):
    APP_NAME: str = Field()
    APP_DESCRIPTION: str = Field(default="A FastAPI microservice")
    APP_VERSION: str = Field(default="0.0.1")
    DEBUG: bool = Field(default=False)
    DEPLOYMENT_ENV: Environment = Field(default=Environment.DEVELOPMENT)
    HOST: str = Field(default="127.0.0.1")
    PORT: PositiveInt = Field(default=5000)
    TIMEZONE: str = Field(default="UTC")
    ALLOW_ORIGINS: str = Field(default="*")
```

```python
# configs/db_conf.py
from typing import Literal
from pydantic import Field, NonNegativeInt, PositiveInt, SecretStr
from pydantic_settings import BaseSettings
from sqlalchemy import URL
from sqlalchemy.util import immutabledict


class DatabaseConfig(BaseSettings):
    DB_HOST: str = Field()
    DB_PORT: PositiveInt = Field()
    DB_USERNAME: str = Field()
    DB_PASSWORD: SecretStr = Field()  # ← always SecretStr for passwords
    DB_DATABASE: str = Field()
    DB_TYPE: Literal["postgres", "sqlite", "mysql"] = Field(default="postgres")
    DB_SCHEMA: str = Field(default="public")

    # SQLAlchemy pool settings
    SQLALCHEMY_POOL_SIZE: NonNegativeInt = Field(default=30)
    SQLALCHEMY_MAX_OVERFLOW: NonNegativeInt = Field(default=10)
    SQLALCHEMY_POOL_RECYCLE: NonNegativeInt = Field(default=3600)
    SQLALCHEMY_POOL_PRE_PING: bool = Field(default=True)
    SQLALCHEMY_ECHO: bool = Field(default=False)
    SQLALCHEMY_POOL_TIMEOUT: NonNegativeInt = Field(default=30)

    # Derived helpers — always @property, never stored fields
    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self.DB_TYPE.lower()

    @property
    def is_postgres(self) -> bool:
        return "postgres" in self.DB_TYPE.lower()

    @property
    def driver(self) -> str:
        if self.is_postgres:
            return "postgresql+asyncpg"
        if self.is_sqlite:
            return "sqlite+aiosqlite"
        if self.DB_TYPE.lower() == "mysql":
            return "mysql+aiomysql"
        raise NotImplementedError(f"Unsupported DB type: {self.DB_TYPE}")

    @property
    def connection_args(self) -> dict:
        """Pool kwargs forwarded to create_async_engine()."""
        if self.is_postgres:
            args = {
                "pool_size": self.SQLALCHEMY_POOL_SIZE,
                "max_overflow": self.SQLALCHEMY_MAX_OVERFLOW,
                "pool_recycle": self.SQLALCHEMY_POOL_RECYCLE,
                "pool_pre_ping": self.SQLALCHEMY_POOL_PRE_PING,
                "pool_timeout": self.SQLALCHEMY_POOL_TIMEOUT,
            }
            if self.DB_SCHEMA != "public":
                args["server_settings"] = {"search_path": self.DB_SCHEMA}
            return args
        return {}

    @property
    def database_url(self) -> str:
        """Full SQLAlchemy async connection URL string."""
        return URL(
            drivername=self.driver,
            username=None if self.is_sqlite else self.DB_USERNAME,
            password=None if self.is_sqlite else self.DB_PASSWORD.get_secret_value(),
            host=None if self.is_sqlite else self.DB_HOST,
            port=None if self.is_sqlite else self.DB_PORT,
            database=self.DB_DATABASE,
        ).render_as_string(hide_password=False)
```

```python
# configs/log_conf.py
from pydantic import Field, PositiveInt
from pydantic_settings import BaseSettings


class LoggingConfig(BaseSettings):
    LOG_LEVEL: str = Field(default="INFO")
    LOG_DIR: str | None = Field(default=None)
    LOG_FILE_MAX_SIZE: PositiveInt = Field(default=20)  # MB
    LOG_FILE_BACKUP_COUNT: PositiveInt = Field(default=5)
    LOG_FORMAT: str = Field(
        default="%(asctime)s.%(msecs)03d %(levelname)s [%(threadName)s] [%(filename)s:%(lineno)d] - %(message)s"
    )
    LOG_DATEFORMAT: str | None = Field(default=None)
```

```python
# configs/feature_conf.py
from pydantic import AnyHttpUrl, Field, PositiveInt
from pydantic_settings import BaseSettings


class FeatureConfig(BaseSettings):
    ALLOW_RECOMMENDATIONS: bool = Field(default=False)
    RECOMMENDATION_DAYS_WINDOW: PositiveInt = Field(default=30)
    EXTERNAL_SERVICE_URL: AnyHttpUrl = Field(default_factory=lambda: AnyHttpUrl("http://localhost:8000"))
```

---

## Pattern: Merge via Multiple Inheritance + `SettingsConfigDict`

The main config class merges all concerns. It adds **no new fields** — only `model_config`.

```python
# configs/app_conf.py
from pydantic_settings import SettingsConfigDict
from .deployment_conf import DeploymentConfig
from .db_conf import DatabaseConfig
from .feature_conf import FeatureConfig
from .log_conf import LoggingConfig


class AppConfig(DeploymentConfig, LoggingConfig, DatabaseConfig, FeatureConfig):
    """Single merged config — reads from .config file (not .env)."""

    model_config = SettingsConfigDict(
        frozen=True,  # immutable after init — prevents accidental mutation
        env_file=".config",  # project uses .config, not .env
        env_file_encoding="utf-8",
        extra="ignore",  # silently ignore unknown env vars
    )
```

---

## Pattern: Single Instantiation in `__init__.py`

```python
# configs/__init__.py
from .app_conf import AppConfig

app_conf = AppConfig()  # ← ONE instantiation, at import time

__all__ = ("AppConfig", "app_conf")
```

**Rules:**
- `app_conf` is the **only** instance that ever exists
- Import it as `from <package>.configs import app_conf`
- Never call `AppConfig()` anywhere else in the codebase
- `model_config = SettingsConfigDict(frozen=True, ...)` makes it immutable — trying to set an attribute raises `ValidationError`

---

## How to Add a New Config Concern

1. Create `configs/<concern>_conf.py` with a new `BaseSettings` subclass
2. Add it to the multiple-inheritance list in `app_conf.py`
3. Re-export from `__init__.py` if external modules need the subclass type

```python
# configs/redis_conf.py   ← new file
class RedisConfig(BaseSettings):
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: PositiveInt = Field(default=6379)
    REDIS_DB: int = Field(default=0)


# configs/app_conf.py     ← add to merge class
class AppConfig(DeploymentConfig, LoggingConfig, DatabaseConfig, FeatureConfig, RedisConfig): ...
```

---

## Usage Throughout the Codebase

```python
# Any module that needs config
from <package>.configs import app_conf

# Access fields directly
db_url  = app_conf.database_url        # @property — builds connection string
origins = app_conf.ALLOW_ORIGINS.split(",")
port    = app_conf.PORT
level   = app_conf.LOG_LEVEL.upper()
```

**Never** import individual config subclasses (`DatabaseConfig`, etc.) outside `configs/`. Only `app_conf` and `AppConfig` are the public API.