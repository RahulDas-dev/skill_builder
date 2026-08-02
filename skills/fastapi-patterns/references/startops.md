# Startops Patterns

## Overview

`startops/` contains every startup and shutdown step as **discrete, single-responsibility files**. Each file does exactly one thing. This makes startup order explicit, failures easy to isolate, and individual steps testable in isolation.

---

## Directory Layout

```
startops/
├── __init__.py              ← flat re-export of every public function
├── set_env.py               ← SYNC: load .config file → os.environ
├── set_loggers.py           ← SYNC: configure logging levels, handlers, formatters
├── set_timezone.py          ← SYNC: set process TZ from config
├── set_warnings.py          ← SYNC: configure Python warnings filters
├── setup_db.py              ← ASYNC: create DB services → call set_*() singletons
├── setup_<manager>.py       ← ASYNC: build in-memory cache → call set_*() singleton
├── setup_<service>.py       ← ASYNC: verify external service (MCP, etc.) — fail fast
└── shutdown_setup.py        ← graceful_shutdown() + emergency_cleanup() + atexit handler
```

**Naming rule:**
- `set_*.py` — **synchronous**, no I/O, no await
- `setup_*.py` — **async**, does I/O (DB connection, HTTP check, etc.)

---

## `__init__.py` — Flat Re-export

```python
# startops/__init__.py
from .set_env        import setup_environment
from .set_loggers    import setup_loggers
from .set_timezone   import setup_timezone
from .set_warnings   import setup_warnings
from .setup_db       import close_db, setup_db_service
from .setup_<mgr>   import close_<mgr>, setup_<mgr>
from .setup_<svc>   import setup_<svc>_connection
from .shutdown_setup import graceful_shutdown, setup_signal_handlers

__all__ = (
    "close_db",
    "graceful_shutdown",
    "setup_<mgr>",
    "setup_db_service",
    "setup_environment",
    "setup_loggers",
    "setup_signal_handlers",
    "setup_timezone",
    "setup_warnings",
)
```

---

## Synchronous `set_*.py` Files

### `set_env.py` — Load `.config` file

```python
# startops/set_env.py
from dotenv import load_dotenv


def setup_environment() -> None:
    """Load .config file into os.environ before anything reads config."""
    load_dotenv()
```

### `set_timezone.py` — Apply timezone to process

```python
# startops/set_timezone.py
import os
import time
from <package>.configs import app_conf

def setup_timezone() -> None:
    tz = app_conf.TIMEZONE.strip()
    if tz:
        os.environ["TZ"] = tz
    else:
        os.environ.pop("TZ", None)   # use system default
    if hasattr(time, "tzset"):
        time.tzset()                 # apply to process (Unix only)
```

### `set_warnings.py` — Filter Python warnings

```python
# startops/set_warnings.py
import warnings


def setup_warnings() -> None:
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
    warnings.filterwarnings("default", category=UserWarning)
    warnings.filterwarnings("default", category=ResourceWarning)
```

### `set_loggers.py` — Configure logging

```python
# startops/set_loggers.py
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from <package>.configs import app_conf

def setup_loggers(service_name: str = "application") -> None:
    log_level = getattr(logging, app_conf.LOG_LEVEL.upper(), logging.INFO)
    handlers: list[logging.Handler] = [logging.StreamHandler()]

    if app_conf.LOG_DIR:
        log_dir = Path(app_conf.LOG_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y_%m_%d-%H-%M-%S")
        handlers.append(
            RotatingFileHandler(
                filename=log_dir / f"{service_name}_{timestamp}.log",
                maxBytes=app_conf.LOG_FILE_MAX_SIZE * 1024 * 1024,
                backupCount=app_conf.LOG_FILE_BACKUP_COUNT,
            )
        )

    logging.basicConfig(
        level=log_level,
        format=app_conf.LOG_FORMAT,
        datefmt=app_conf.LOG_DATEFORMAT,
        force=True,        # override any prior config
        handlers=handlers,
    )
    # Quiet noisy third-party loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
```

---

## Async `setup_*.py` Files

### `setup_db.py` — Instantiate DB services + register singletons

```python
# startops/setup_db.py
import logging
from <package>.configs import app_conf
from <package>.services.config  import AppConfigService, set_config_service, get_config_service
from <package>.services.session import SessionService, set_session_service, get_session_service

logger = logging.getLogger(__name__)


async def setup_db_service() -> None:
    """Initialize both DB services and register them as singletons."""
    try:
        session_svc = SessionService(
            db_url=app_conf.database_url,
            echo=app_conf.SQLALCHEMY_ECHO,
            engine_args=app_conf.connection_args,
        )
        await session_svc.initialize()
        set_session_service(session_svc)                         # ← register singleton
        logger.info("Session service initialized: %s", app_conf.database_url)

        config_svc = AppConfigService(
            db_url=app_conf.database_url,
            echo=app_conf.SQLALCHEMY_ECHO,
            engine_args=app_conf.connection_args,
        )
        await config_svc.initialize()
        set_config_service(config_svc)                           # ← register singleton
        logger.info("Config service initialized")

    except Exception:
        logger.exception("Failed to initialize database services")
        raise                                                     # ← always re-raise startup failures


async def close_db() -> None:
    """Close all DB connections during shutdown."""
    try:
        await get_session_service().close()
        logger.info("Session service closed")
    except Exception:
        logger.exception("Failed to close session service")      # ← never re-raise in shutdown

    try:
        await get_config_service().close()
        logger.info("Config service closed")
    except Exception:
        logger.exception("Failed to close config service")
```

### `setup_<manager>.py` — Build in-memory cache + register singleton

```python
# startops/setup_agent_manager.py
import logging
from <package>.services.app_manager import AppManager, get_app_manager, set_app_manager

logger = logging.getLogger(__name__)


async def setup_agent_manager() -> None:
    """Build all active apps and register the AppManager singleton.

    Note: requires setup_db_service() to have completed first.
    """
    try:
        manager = AppManager()
        await manager.initialize()       # reads from DB via get_config_service()
        set_app_manager(manager)
        logger.info("App manager initialized")
    except Exception:
        logger.exception("Failed to initialize app manager")
        raise


async def close_agent_manager() -> None:
    try:
        await get_app_manager().cleanup()
        logger.info("App manager closed")
    except RuntimeError:
        logger.debug("App manager not initialized, skipping cleanup")
    except Exception:
        logger.exception("Failed to close app manager")
```

### `setup_<service>.py` — Verify external service (fail fast)

```python
# startops/setup_mcp_servers.py
import logging
from <package>.configs import app_conf
from <package>.common.mcp_connector import MCPConnectionVerifier, McpObject

logger = logging.getLogger(__name__)


async def setup_mcp_connection(
    connection_timeout: float = 10.0,
    max_retries: int = 3,
) -> bool:
    """Verify external MCP server is reachable before serving requests."""
    mcp_details = [McpObject(server_name="txn_resolver_mcp", server_url=str(app_conf.EXTERNAL_SERVICE_URL))]
    verifier = MCPConnectionVerifier(mcpdetails=mcp_details, timeout=connection_timeout, max_retries=max_retries)
    results = await verifier.verify_connection()
    success = all(r.success for r in results)
    if not success:
        logger.error("MCP server connection failed: %s", [r.error for r in results if not r.success])
    return success
```

---

## `shutdown_setup.py` — Graceful Shutdown + Emergency Cleanup

```python
# startops/shutdown_setup.py
# ruff: noqa: PLC0415
import asyncio
import atexit
import contextlib
import logging

logger = logging.getLogger(__name__)
_cleanup_registered = False


async def graceful_shutdown() -> None:
    """Normal shutdown — called from lifespan finally block.

    Closes services in reverse startup order:
    1. App manager (closes all runners)
    2. DB services (closes connections)
    """
    from .setup_agent_manager import close_agent_manager
    from .setup_db import close_db

    logger.info("Application shutting down...")
    await close_agent_manager()
    await close_db()
    logger.info("Shutdown complete")


def emergency_cleanup() -> None:
    """Last-resort cleanup registered with atexit.

    Runs synchronously when the process exits unexpectedly (e.g. unhandled exception).
    Creates a new event loop since atexit handlers cannot be async.
    """
    logger.warning("Emergency cleanup triggered")
    loop = None
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        for getter, label in [
            ("aider.services.app_manager.get_app_manager", "app manager"),
            ("aider.services.config.get_config_service", "config service"),
            ("aider.services.session.get_session_service", "session service"),
        ]:
            module, fn = getter.rsplit(".", 1)
            try:
                import importlib

                get_fn = getattr(importlib.import_module(module), fn)
                svc = get_fn()
                if hasattr(svc, "cleanup"):
                    loop.run_until_complete(svc.cleanup())
                elif hasattr(svc, "close") and getattr(svc, "is_connected", True):
                    loop.run_until_complete(svc.close())
                logger.info("Emergency cleanup: %s closed", label)
            except RuntimeError:
                logger.debug("Emergency cleanup: %s not initialized, skipping", label)
            except Exception:
                logger.exception("Emergency cleanup: failed to close %s", label)

    except Exception:
        logger.exception("Emergency cleanup failed")
    finally:
        if loop:
            with contextlib.suppress(Exception):
                loop.close()


def setup_signal_handlers() -> None:
    """Register atexit handler once as a safety net.

    The preferred shutdown path is through the FastAPI lifespan finally block.
    This is only a fallback for unexpected termination.
    """
    global _cleanup_registered  # noqa: PLW0603
    if not _cleanup_registered:
        atexit.register(emergency_cleanup)
        _cleanup_registered = True
        logger.debug("Emergency cleanup registered with atexit")
```

---

## `app.py` — Startup Orchestration

Synchronous steps run in `add_startup_ops()` (called at module import), async steps run inside `lifespan()`.

```python
# app.py
# ruff: noqa: PLC0415
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from <package>.configs import app_conf

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Async startup/shutdown — strict ordering enforced."""
    from <package>.startops import (
        graceful_shutdown,
        setup_db_service,
        setup_agent_manager,
        setup_mcp_connection,
    )

    await setup_db_service()          # 1. DB first — all services depend on it

    await setup_agent_manager()       # 2. In-memory cache — depends on DB config service

    if not await setup_mcp_connection():
        raise RuntimeError("MCP server unavailable — refusing to start")   # 3. Fail fast

    yield                             # ← app is live and serving requests

    await graceful_shutdown()         # 4. Reverse order: runners → DB connections


def add_startup_ops(_app: FastAPI) -> None:
    """Synchronous setup — runs before lifespan, at module import time."""
    from <package>.startops import (
        setup_environment,
        setup_loggers,
        setup_timezone,
        setup_warnings,
        setup_signal_handlers,
    )
    setup_environment()               # load .config → os.environ first
    setup_timezone()
    setup_warnings()
    setup_loggers("<service_name>")
    setup_signal_handlers()           # register atexit emergency cleanup


def setup_application() -> FastAPI:
    app = FastAPI(
        title=app_conf.APP_NAME,
        description=app_conf.APP_DESCRIPTION,
        version=app_conf.APP_VERSION,
        lifespan=lifespan,
    )
    add_startup_ops(app)
    add_middlewares(app)
    add_routers(app)
    return app
```

---

## Rules

1. **`set_*.py` = synchronous only** — no `await`, no I/O, no DB calls
2. **`setup_*.py` = async only** — always `async def`, always uses `await`
3. **Always `raise` on startup failure** — never swallow exceptions in `setup_*()` functions
4. **Never `raise` in shutdown** — log the exception, continue closing remaining resources
5. **Startup order is strict**: `env → loggers/tz/warnings → DB → managers → external services`
6. **Shutdown is reverse order**: `managers → DB` — always close dependents before dependencies
7. **Inline imports in `startops/` and `app.py`** are intentional — suppressed with `# ruff: noqa: PLC0415`
8. **`graceful_shutdown()` is called from lifespan** — `emergency_cleanup()` is only for atexit (unexpected exit)
9. **`setup_signal_handlers()` registers atexit once** — idempotent, guarded by `_cleanup_registered`
10. **One setup function per file** — each `setup_*.py` owns one concern and nothing else