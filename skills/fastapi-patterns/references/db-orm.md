# DB ORM Patterns

## Overview

`db/` contains **only** SQLAlchemy ORM model definitions. Zero business logic, zero queries, zero service calls. It is a pure schema layer. All queries live in `services/`.

---

## Directory Layout

```
db/
├── __init__.py    # Re-exports every ORM class — the public API for the db layer
├── base.py        # DeclarativeBase — one class, nothing else
├── config.py      # ORM models for config-domain tables (Apps, Agents, Transactions, Fields)
└── state.py       # ORM models for runtime-state tables (Sessions, AppState, UserState)
```

Split files by **domain concern**, not by table count. If a new domain grows large, add a new file (e.g., `billing.py`, `audit.py`).

---

## `base.py` — One Class Only

```python
# db/base.py
"""SQLAlchemy declarative base."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
```

Never add anything else to `base.py`. All ORM classes import `Base` from here.

---

## `__init__.py` — Re-export Every ORM Class

```python
# db/__init__.py
from .base import Base
from .config import (
    AgentConfigOrm,
    AgentGuardrailConfigOrm,
    AgentSystemPromptConfigOrm,
    AppConfigOrm,
    TransactionConfigOrm,
    TxnFieldConfigOrm,
)
from .state import AppStateOrm, SessionOrm, UserStateOrm

__all__ = (
    "AgentConfigOrm",
    "AgentGuardrailConfigOrm",
    "AgentSystemPromptConfigOrm",
    "AppConfigOrm",
    "AppStateOrm",
    "Base",
    "SessionOrm",
    "TransactionConfigOrm",
    "TxnFieldConfigOrm",
    "UserStateOrm",
)
```

---

## ORM Model Anatomy

Every model follows the same structure. Internalize this pattern:

```python
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ExampleOrm(Base):
    """One-line description of what this table stores."""

    __tablename__ = "examples"  # ← always snake_case plural

    # ── Primary Key ───────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Row UUID",
    )

    # ── Required String Fields ────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Unique identifier slug",
    )

    # ── Optional / Nullable Fields ────────────────────────────────────────────
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Human-readable description",
    )

    # ── Booleans ──────────────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Soft-delete flag",
    )

    # ── JSONB — flexible payloads (PostgreSQL only) ───────────────────────────
    # Rename the ORM attribute to avoid clashing with Python `metadata`
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",  # ← actual DB column name stays "metadata"
        JSONB,
        nullable=True,
        comment="Arbitrary extra data",
    )
    config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),  # ← DB sets this, not Python
        comment="Row creation time (UTC)",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),  # ← auto-updated on every UPDATE
        comment="Row last modified time (UTC)",
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    children: Mapped[list["ChildOrm"]] = relationship(
        "ChildOrm",
        back_populates="parent",
        cascade="all, delete-orphan",  # ← children deleted when parent deleted
        doc="Child rows owned by this row",
    )

    # ── Table-Level Constraints & Indexes ─────────────────────────────────────
    __table_args__ = (
        Index("ix_examples_name", "name", unique=True),
        Index("ix_examples_is_active", "is_active"),
        Index("ix_examples_created_at", "created_at"),
        {"comment": "Stores example entities"},
    )
```

---

## Foreign Keys

```python
class ChildOrm(Base):
    __tablename__ = "children"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # FK — always use ondelete="CASCADE" for owned children
    parent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("examples.id", ondelete="CASCADE"),
        nullable=False,
        comment="FK → examples.id",
    )

    # Back-reference to parent
    parent: Mapped["ExampleOrm"] = relationship(
        "ExampleOrm",
        back_populates="children",
    )
```

---

## JSONB Usage Rules

Use `JSONB` for:
- Polymorphic/flexible config blobs (e.g., resolution strategies, agent config)
- Lists of primitives (`list[str]`, `list[dict]`)
- Arbitrary metadata / extension points

```python
# List of dicts — resolution strategies stored as JSONB
resolution: Mapped[list[dict[str, Any]] | None] = mapped_column(
    JSONB,
    nullable=True,
    comment="Ordered list of resolution strategies",
)

# List of strings — dependency names
depends_on: Mapped[list[str] | None] = mapped_column(
    JSONB,
    nullable=True,
    comment="Field names this field depends on",
)

# Any scalar — JSONB can hold int, float, str, bool, null
default_value: Mapped[Any | None] = mapped_column(
    JSONB,
    nullable=True,
)
```

**Important:** After mutating a JSONB column in-place (e.g., `dict.update()`), you **must** call `flag_modified(orm_obj, "column_name")` so SQLAlchemy detects the change:

```python
from sqlalchemy.orm.attributes import flag_modified

current = dict(session_orm.state) if session_orm.state else {}
current.update(state_delta)
session_orm.state = current
flag_modified(session_orm, "state")  # ← required for JSONB mutations
```

---

## `metadata_` vs `metadata` Naming Conflict

SQLAlchemy's `DeclarativeBase` uses `metadata` as a class-level attribute. To avoid the collision, name the ORM attribute `metadata_` but map it to the actual DB column `"metadata"`:

```python
metadata_: Mapped[dict[str, Any] | None] = mapped_column(
    "metadata",  # ← DB column name
    JSONB,
    nullable=True,
)
```

---

## Composite Indexes & Unique Constraints

```python
__table_args__ = (
    # Unique composite — enforce uniqueness across two columns
    Index("ix_agents_app_name", "app_id", "name", unique=True),
    # Simple index — speed up common filters
    Index("ix_agents_is_active", "is_active"),
    Index("ix_agents_tenant_name", "tenant_name"),
    # Check constraint — enforce domain rules at DB level
    CheckConstraint("build_type IN ('Agentic', 'Non-Agentic')", name="ck_apps_build_type"),
    CheckConstraint("tenant_name NOT LIKE '% %'", name="ck_apps_tenant_name_no_spaces"),
    # Table comment — always include
    {"comment": "Stores agent configurations"},
)
```

---

## State Tables (Runtime vs Config)

Split ORM files by domain: config tables (long-lived, admin-managed) vs state tables (runtime, per-user/session).

```python
# db/state.py — runtime state tables


class SessionOrm(Base):
    """Per-session conversation state and history."""

    __tablename__ = "sessions"

    # Composite primary key — scoped by app + user + session
    app_name: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    state: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    history: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_sessions_app_user", "app_name", "user_id"),
        Index("ix_sessions_updated_at", "updated_at"),
    )


class AppStateOrm(Base):
    """App-wide shared state (single row per app)."""

    __tablename__ = "app_state"
    app_name: Mapped[str] = mapped_column(String(128), primary_key=True)
    state: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UserStateOrm(Base):
    """Per-user persistent state (single row per app+user)."""

    __tablename__ = "user_state"
    app_name: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    state: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

---

## Rules

1. **No queries in `db/`** — `db/` is schema only. All SQLAlchemy `select()`, `insert()`, etc. live in `services/*/main.py`
2. **Always `comment=`** on every column — documents the schema in the DB itself
3. **Always `server_default=func.now()`** for timestamps — the DB sets them, not Python
4. **Always `onupdate=func.now()`** on `updated_at`
5. **Always `cascade="all, delete-orphan"`** on parent→children relationships
6. **Always include `{"comment": "..."}` dict** in `__table_args__`
7. **Use `Mapped[T]` + `mapped_column()`** — never the legacy `Column()` style
8. **`metadata_` for JSONB columns** named `metadata` — avoids SQLAlchemy base class collision
9. **Call `flag_modified()`** after in-place JSONB mutation in service methods