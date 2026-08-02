# Services Patterns

## Overview

Each service is a **package** under `services/`. It owns a slice of business logic, persists data via SQLAlchemy, and exposes itself as a **singleton** through `get_<name>()` / `set_<name>()` functions. Route handlers and other services always call `get_*()` — they never instantiate services directly.

---

## Package Structure

```
services/
├── base_db_service.py         ← shared async SQLAlchemy base (engine + session factory)
└── <service_name>/            ← one package per service: session/, config/, app_manager/
    ├── __init__.py            ← module docstring + re-exports public API
    ├── main.py                ← service class + get_<name>() + set_<name>()
    └── schema.py              ← Pydantic / dataclass domain models this service owns
```

---

## `base_db_service.py` — Shared Async SQLAlchemy Base

All DB-backed services extend `BaseDBService`. It manages the engine, session factory, and teardown.

```python
# services/base_db_service.py
import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from <package>.db import Base

logger = logging.getLogger(__name__)


def to_uuid(value: str | uuid.UUID) -> uuid.UUID:
    """Coerce string → UUID."""
    return value if isinstance(value, uuid.UUID) else uuid.UUID(value)


class BaseDBService:
    def __init__(
        self,
        db_url: str,
        echo: bool = False,
        engine_args: dict[str, Any] | None = None,
    ) -> None:
        self._db_url = db_url
        self._echo = echo
        self._engine_args = engine_args or {}
        self._engine: AsyncEngine | None = None
        self._session_maker: async_sessionmaker[AsyncSession] | None = None

    async def initialize(self) -> None:
        """Create engine, session factory, and run table migrations."""
        self._engine = create_async_engine(self._db_url, echo=self._echo, **self._engine_args)
        self._session_maker = async_sessionmaker(self._engine, expire_on_commit=False)
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)  # idempotent

    @property
    def is_connected(self) -> bool:
        return self._engine is not None and self._session_maker is not None

    @asynccontextmanager
    async def _get_db_session(self) -> AsyncIterator[AsyncSession]:
        """Context manager that yields a session and handles rollback + close."""
        if self._session_maker is None:
            raise RuntimeError("Service not initialized. Call initialize() first.")
        session = self._session_maker()
        try:
            yield session
        except Exception:
            await session.rollback()
        finally:
            await session.close()

    async def close(self) -> None:
        """Dispose engine and clear references."""
        if not self._engine:
            return
        try:
            await self._engine.dispose(close=True)
        except asyncio.CancelledError:
            self._engine.sync_engine.dispose()  # fallback on cancellation
        finally:
            self._engine = None
            self._session_maker = None
            logger.info("Database disconnected")
```

---

## `main.py` — Service Class + Singleton Functions

### Service class

```python
# services/session/main.py
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from <package>.db import SessionOrm
from <package>.services.base_db_service import BaseDBService, to_uuid
from .schema import GetSessionConfig, ListSessionsResponse, Session

logger = logging.getLogger(__name__)


class SessionService(BaseDBService):
    """PostgreSQL-backed session persistence service."""

    async def create_session(
        self,
        *,                          # ← keyword-only args on all public methods
        app_name: str,
        user_id: str,
        session_id: str | None = None,
        state: dict[str, Any] | None = None,
        history: list[dict[str, Any]] | None = None,
    ) -> Session:
        session_uuid = to_uuid(session_id) if session_id else uuid.uuid4()
        orm = SessionOrm(
            app_name=app_name,
            user_id=user_id,
            id=session_uuid,
            state=state or {},
            history=history or [],
        )
        async with self._get_db_session() as db:
            db.add(orm)
            await db.commit()
            await db.refresh(orm)
        return self._to_session(orm)

    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: GetSessionConfig | None = None,
    ) -> Session | None:
        async with self._get_db_session() as db:
            stmt = select(SessionOrm).where(
                SessionOrm.app_name == app_name,
                SessionOrm.user_id == user_id,
                SessionOrm.id == to_uuid(session_id),
            )
            result = await db.execute(stmt)
            orm = result.scalar_one_or_none()
            if orm is None:
                return None
            session = self._to_session(orm)
            return self._apply_config(session, config) if config else session

    async def update_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        state_delta: dict[str, Any] | None = None,
        history_append: list[dict[str, Any]] | None = None,
    ) -> Session | None:
        async with self._get_db_session() as db:
            stmt = select(SessionOrm).where(
                SessionOrm.app_name == app_name,
                SessionOrm.user_id == user_id,
                SessionOrm.id == to_uuid(session_id),
            )
            result = await db.execute(stmt)
            orm = result.scalar_one_or_none()
            if orm is None:
                return None

            if state_delta:
                current = dict(orm.state) if orm.state else {}
                current.update(state_delta)
                orm.state = current
                flag_modified(orm, "state")         # ← required for JSONB mutations

            if history_append:
                current_h = list(orm.history) if orm.history else []
                current_h.extend(history_append)
                orm.history = current_h
                flag_modified(orm, "history")

            orm.updated_at = datetime.now(UTC)
            await db.commit()
            await db.refresh(orm)
            return self._to_session(orm)

    async def delete_session(self, *, app_name: str, user_id: str, session_id: str) -> bool:
        async with self._get_db_session() as db:
            stmt = select(SessionOrm).where(
                SessionOrm.app_name == app_name,
                SessionOrm.user_id == user_id,
                SessionOrm.id == to_uuid(session_id),
            )
            result = await db.execute(stmt)
            orm = result.scalar_one_or_none()
            if orm is None:
                return False
            await db.delete(orm)
            await db.commit()
            return True

    # ── Private helpers ───────────────────────────────────────────────────────
    def _to_session(self, orm: SessionOrm) -> Session:
        """Convert ORM row → domain model."""
        return Session(
            id=str(orm.id),
            app_name=orm.app_name,
            user_id=orm.user_id,
            state=orm.state or {},
            history=orm.history or [],
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    def _apply_config(self, session: Session, config: GetSessionConfig) -> Session:
        history = session.history
        if config.after_timestamp:
            history = [m for m in history if m.get("timestamp", 0) > config.after_timestamp]
        if config.num_recent_messages:
            history = history[-config.num_recent_messages:]
        session.history = history
        return session
```

### Singleton functions — bottom of `main.py`

```python
# ── Singleton ─────────────────────────────────────────────────────────────────
_session_service: SessionService | None = None


def set_session_service(service: SessionService) -> None:
    """Register the singleton. Called only from startops/setup_db.py."""
    global _session_service  # noqa: PLW0603
    _session_service = service


def get_session_service() -> SessionService:
    """Retrieve the singleton. Used everywhere else."""
    if _session_service is None:
        raise RuntimeError("SessionService not initialized. App lifespan may not have started.")
    return _session_service
```

**Rules:**
- `set_*()` called **only** from `startops/setup_*.py`
- `get_*()` used by routes (`Depends(get_session_service)`), other services, apps
- The module-level `_var` is `None` at import time — set at startup, never earlier
- All public service methods use **keyword-only args** (`*` separator) — prevents positional mistakes

---

## `schema.py` — Domain Models

Use `@dataclass` for simple value objects (no validation needed). Use `BaseModel` when Pydantic validation or serialization is needed.

```python
# services/session/schema.py
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


def _validate_uuid(session_id: str | uuid.UUID) -> str:
    if isinstance(session_id, uuid.UUID):
        return str(session_id)
    try:
        uuid.UUID(session_id)
    except ValueError as e:
        raise ValueError(f"Session ID must be a valid UUID, got: {session_id}") from e
    return session_id


@dataclass
class Session:
    """Domain model for a session — returned by SessionService methods."""

    id: str
    app_name: str
    user_id: str
    state: dict[str, Any] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        self.id = _validate_uuid(self.id)


@dataclass
class GetSessionConfig:
    """Options for filtering history on get_session()."""

    num_recent_messages: int | None = None
    after_timestamp: float | None = None


@dataclass
class ListSessionsResponse:
    """Wrapper returned by list_sessions()."""

    sessions: list[Session] = field(default_factory=list)
```

---

## `__init__.py` — Public API with Module Docstring

```python
# services/session/__init__.py
"""Session management — persistent per-session state and conversation history.

Supports PostgreSQL (asyncpg) and SQLite (aiosqlite) via async SQLAlchemy.
Sessions are scoped by (app_name, user_id, session_id).

Usage:
    from <package>.services.session import get_session_service

    service = get_session_service()
    session = await service.create_session(app_name="my_app", user_id="u1")
"""

from .main import SessionService, get_session_service, set_session_service
from .schema import GetSessionConfig, ListSessionsResponse, Session

__all__ = [
    "GetSessionConfig",
    "ListSessionsResponse",
    "Session",
    "SessionService",
    "get_session_service",
    "set_session_service",
]
```

---

## Non-DB Service: AppManager

Not all services extend `BaseDBService`. The `AppManager` is a pure in-memory cache.

```python
# services/app_manager/main.py
class AppManager:
    """Eagerly builds and caches all active apps at startup."""

    def __init__(self) -> None:
        self._apps: dict[str, BaseApp] = {}

    async def initialize(self) -> None:
        """Build all active apps from config and cache them."""
        config_service = get_config_service()
        app_configs = await config_service.list_appconfigs(active_only=True)
        for app_config in app_configs:
            app = await AppBuilder.build(app_config)  # @classmethod, no instantiation
            self._apps[app_config.tenant_name] = app
        logger.info("App manager initialized: apps=%d", len(self._apps))

    def get_app(self, app_name: str) -> BaseApp:
        """Synchronous lookup — fast path during request handling."""
        if app_name not in self._apps:
            raise ValueError(f"App not found: {app_name}")
        return self._apps[app_name]

    async def cleanup(self) -> None:
        for name, app in self._apps.items():
            try:
                await app.close()
            except Exception:
                logger.exception("Failed to close app: %s", name)
        self._apps.clear()


# Singleton
_app_manager: AppManager | None = None


def set_app_manager(manager: AppManager) -> None:
    global _app_manager  # noqa: PLW0603
    _app_manager = manager


def get_app_manager() -> AppManager:
    if _app_manager is None:
        raise RuntimeError("AppManager not initialized.")
    return _app_manager
```

---

## Rules

1. **Always keyword-only args** on service methods — use `*` separator
2. **Always `flag_modified(orm, "col")`** after in-place JSONB mutation
3. **`_to_domain()`** private helper converts ORM → domain model — never expose ORM outside service
4. **`schema.py` types are the public contract** — routes import from `schema.py`, never from `db/`
5. **`set_*()` is startops-only** — never call from routes, tests override via dependency injection
6. **`get_*()` raises `RuntimeError`** if called before initialization — fail loudly, not silently
7. **`@dataclass` for simple value objects** in `schema.py`; `BaseModel` only when Pydantic validation is needed