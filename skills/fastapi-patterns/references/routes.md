# Routes Patterns

## Overview

Every route domain is a **package** under `routes/`. The package has exactly four files, each with a single job. The `routes/__init__.py` aggregates everything into one `api_router` mounted under `/api/v1`.

---

## Package Structure

```
routes/
├── __init__.py            ← aggregates ALL sub-routers into api_router (no logic)
└── <domain>/              ← one package per domain: chat, sessions, config, health
    ├── __init__.py        ← exports only `router`
    ├── views.py           ← APIRouter definition + all @router.* handlers
    ├── models.py          ← Request & Response Pydantic models for this domain
    └── runner.py          ← (optional) re-exports of singletons views.py depends on
```

---

## `routes/__init__.py` — Router Aggregator

No logic here. Just collect and expose `api_router`.

```python
# routes/__init__.py
from fastapi.routing import APIRouter
from <package>.routes import chat, config, health, sessions

api_router = APIRouter()
api_router.include_router(config.router)
api_router.include_router(sessions.router)
api_router.include_router(chat.router)
api_router.include_router(health.router)
```

Mounted in `app.py` under `/api/v1`:

```python
def add_routers(app: FastAPI) -> None:
    from <package>.routes import api_router  # ruff: noqa: PLC0415
    app.include_router(router=api_router, prefix="/api/v1")
```

---

## `routes/<domain>/__init__.py` — Export Only `router`

```python
# routes/sessions/__init__.py
from <package>.routes.sessions.views import router
__all__ = ["router"]
```

---

## `views.py` — Router + Handlers

### Define `router` at the top

Prefix and tags always go on the `APIRouter`, never in `include_router()`.

```python
# routes/sessions/views.py
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from <package>.services.session import Session, SessionService, get_session_service
from .models import CreateSessionRequest

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/users/{app_name}/{user_id}/sessions",
    tags=["sessions"],
)
```

### GET — retrieve a resource

```python
@router.get("/{session_id}", response_model_exclude_none=True)
async def get_session(
    app_name: str,
    user_id: str,
    session_id: str,
    session_service: Annotated[SessionService, Depends(get_session_service)],
) -> Session:
    logger.info("Session id: %s | User Id: %s | Retrieving session", session_id, user_id)
    session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
    if not session:
        logger.warning("Session id: %s | User Id: %s | Session not found", session_id, user_id)
        raise HTTPException(status_code=404, detail="Session not found")
    logger.info("Session id: %s | User Id: %s | Session retrieved", session_id, user_id)
    return session
```

### GET — list resources

```python
@router.get("", response_model_exclude_none=True)
async def list_sessions(
    app_name: str,
    user_id: str,
    session_service: Annotated[SessionService, Depends(get_session_service)],
) -> list[Session]:
    logger.info("User Id: %s | Listing sessions", user_id)
    result = await session_service.list_sessions(app_name=app_name, user_id=user_id)
    logger.info("User Id: %s | Found %d sessions", user_id, len(result.sessions))
    return list(result.sessions)
```

### POST — create (status 201)

```python
@router.post("", status_code=status.HTTP_201_CREATED, response_model_exclude_none=True)
async def create_session(
    app_name: str,
    user_id: str,
    req: CreateSessionRequest,
    session_service: Annotated[SessionService, Depends(get_session_service)],
) -> Session:
    logger.info("User Id: %s | Creating session", user_id)
    session = await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        state=req.state,
        session_id=req.session_id,
    )
    logger.info("Session id: %s | User Id: %s | Session created", session.id, user_id)
    return session
```

### PATCH — partial update with `exclude_unset`

```python
@router.patch("/{app_id}")
async def update_app(
    app_id: str,
    req: UpdateAppRequest,
    app_service: Annotated[AppConfigService, Depends(get_config_service)],
) -> AppConfig:
    logger.info("Updating app: id=%s", app_id)
    updates = req.model_dump(exclude_unset=True)  # ← only fields the client sent
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No updates provided")
    updated = await app_service.update_app(app_id, **updates)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")
    return updated
```

### DELETE — no response body (status 204)

```python
@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    app_name: str,
    user_id: str,
    session_id: str,
    session_service: Annotated[SessionService, Depends(get_session_service)],
) -> None:
    logger.info("Session id: %s | User Id: %s | Deleting session", session_id, user_id)
    await session_service.delete_session(app_name=app_name, user_id=user_id, session_id=session_id)
    logger.info("Session id: %s | User Id: %s | Session deleted", session_id, user_id)
```

### Helper functions inside views.py

Private helpers that support multiple handlers go inside `views.py`, prefixed with `_`:

```python
def _resolution_models_to_dicts(resolutions: list | None) -> list[dict]:
    """Convert resolution request models to storable dicts."""
    if not resolutions:
        return []
    return [r.model_dump() for r in resolutions]
```

---

## `models.py` — Request & Response Models

### Request models always use `alias_generators.to_camel`

```python
# routes/sessions/models.py
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, alias_generators


class CreateSessionRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,  # camelCase in JSON ↔ snake_case in Python
        populate_by_name=True,  # accept both formats
    )
    session_id: str | None = Field(
        default=None,
        description="Session UUID. Auto-generated if omitted.",
    )
    state: dict[str, Any] | None = Field(
        default=None,
        description="Initial session state.",
    )
```

### PATCH request — all fields optional

```python
class UpdateAppRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
    )
    display_name: str | None = Field(default=None, min_length=1, max_length=256)
    description: str | None = Field(default=None)
    is_active: bool | None = Field(default=None)
    metadata: dict[str, Any] | None = Field(default=None)
```

### Nested CREATE request

```python
class CreateTransactionRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=256)
    description: str | None = Field(default=None)
    url: str | None = Field(default=None, max_length=512)
    request_method: str = Field(default="POST")
    timeout_ms: int = Field(default=30000, ge=1000, le=300000)
    requires_confirm: bool = Field(default=False)
    metadata: dict[str, Any] | None = Field(default=None)
    fields: list[CreateTxnFieldRequest] | None = Field(default=None)
```

### `schema.py` (service) vs `models.py` (route)

| | `schema.py` | `models.py` |
|---|---|---|
| **Location** | `services/<name>/schema.py` | `routes/<domain>/models.py` |
| **Contains** | Domain objects the service **owns** (e.g. `Session`, `ListSessionsResponse`) | HTTP request / response shapes for one route domain |
| **Used by** | Service methods, other services, route handlers | Route handlers only |
| **Type** | `@dataclass` or `BaseModel` | `BaseModel` always |

---

## `runner.py` — Dependency Re-exports

Only re-export what `views.py` needs. Zero logic.

```python
# routes/chat/runner.py
"""Runner re-exports — singletons needed by chat route handlers."""
from <package>.apps.base import BaseApp
from <package>.services.app_manager import AppManager, get_app_manager, set_app_manager

__all__ = ["AppManager", "BaseApp", "get_app_manager", "set_app_manager"]
```

---

## SSE Streaming

```python
# routes/chat/views.py
import logging
from typing import Annotated, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from <package>.common.utilis import Aclosing
from <package>.services.app_manager import Event, RunConfig
from <package>.services.session import SessionService, get_session_service
from .models import RunAgentRequest
from .runner import get_app_manager

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/apps/{app_name}/users/{user_id}/sessions/{session_id}",
    tags=["chat"],
)


@router.post("/run_sse")
async def run_agent_sse(
    app_name: str,
    user_id: str,
    session_id: str,
    req: RunAgentRequest,
    session_service: Annotated[SessionService, Depends(get_session_service)],
) -> StreamingResponse:
    session = await session_service.get_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        event_count = 0
        try:
            runner = get_app_manager().get_app(app_name)
            run_config = RunConfig(streaming_mode="events" if req.streaming else "none")

            async with Aclosing(
                runner.run_async(
                    user_id=user_id,
                    session_id=session_id,
                    new_message=req.new_message,
                    state_delta=req.state_delta,
                    run_config=run_config,
                    invocation_id=req.invocation_id,
                )
            ) as agen:
                async for event in agen:
                    event_count += 1
                    yield f"data: {event.model_dump_json(exclude_none=True, by_alias=True)}\n\n"

            yield "data: [DONE]\n\n"
            logger.info("Session id: %s | SSE completed, events=%d", session_id, event_count)

        except Exception as e:
            logger.exception("Session id: %s | SSE stream error, events=%d", session_id, event_count)
            error = str(e).replace('"', "'").replace("\n", " ")
            yield f'data: {{"error": "{error}", "eventCount": {event_count}}}\n\n'
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )
```

**SSE rules:**
- Always wrap the async generator with `Aclosing` — guarantees cleanup on client disconnect
- Each event: `f"data: {json}\n\n"` — two newlines terminate the SSE frame
- Always end the stream with `yield "data: [DONE]\n\n"`
- Catch exceptions **inside** the generator and yield an error event — never let the generator raise
- Set `X-Accel-Buffering: no` to disable nginx/proxy buffering

---

## Dependency Injection

Always use `Annotated[Type, Depends(getter)]`. Define a type alias for reuse.

```python
from typing import Annotated
from fastapi import Depends

SessionServiceDep = Annotated[SessionService, Depends(get_session_service)]
ConfigServiceDep = Annotated[AppConfigService, Depends(get_config_service)]


@router.get("/{session_id}")
async def get_session(session_id: str, svc: SessionServiceDep) -> Session: ...
```

---

## Error Handling

```python
from fastapi import HTTPException, status

# 404 — resource not found
if not resource:
    logger.warning("Resource id: %s | Not found", resource_id)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

# 400 — bad input (use from None to suppress chain)
raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bad request") from None

# 400 — no fields in PATCH
updates = req.model_dump(exclude_unset=True)
if not updates:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No updates provided")

# 500 — unexpected (preserve chain with from e)
except Exception as e:
    logger.exception("Session id: %s | Operation failed", session_id)
    raise HTTPException(status_code=500, detail=str(e)) from e
```

---

## Logging Rules

Every log line must include request-scoped identifiers. Use `%s` style always.

```python
logger.info("Session id: %s | User Id: %s | Starting agent run", session_id, user_id)
logger.info("Session id: %s | User Id: %s | Completed, events=%d", session_id, user_id, count)
logger.warning("Session id: %s | User Id: %s | Session not found", session_id, user_id)
logger.exception("Session id: %s | User Id: %s | Run failed", session_id, user_id)  # inside except
```

- **Never** f-strings in log calls — lazy `%s` only
- **Never** emojis in log messages
- Use `logger.exception()` inside `except` blocks — captures the traceback automatically
- Use `logger.warning()` for expected misses (404s), `logger.exception()` for unexpected errors

---

## Status Code Reference

| Scenario | Decorator | Notes |
|---|---|---|
| Successful GET / LIST | _(default 200)_ | No `status_code=` needed |
| Successful POST | `status_code=status.HTTP_201_CREATED` | Resource created |
| Successful DELETE | `status_code=status.HTTP_204_NO_CONTENT` | Return type must be `-> None` |
| Not found | `HTTPException(404)` | |
| Bad input | `HTTPException(400)` | Use `from None` for validation errors |
| Unexpected error | `HTTPException(500)` | Use `from e` to preserve traceback |