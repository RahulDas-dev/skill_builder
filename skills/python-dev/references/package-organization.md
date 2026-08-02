# Python Package Organization & Import Conventions

## Standard Project Layout


```

myproject/
├── src/
│   └── mypackage/
│       ├── __init__.py
│       ├── main.py
│       ├── api/
│       │   ├── __init__.py
│       │   └── routes.py
│       ├── models/
│       │   ├── __init__.py
│       │   └── user.py
│       └── utils/
│           ├── __init__.py
│           └── helpers.py
├── tests/
│   ├── conftest.py
│   ├── test_api.py
│   └── test_models.py
├── pyproject.toml
├── README.md
└── .gitignore

```

## Import Conventions

```python
# Import order: stdlib -> third-party -> local (ruff/isort enforced)
import os
import sys
from pathlib import Path          # stdlib

import requests
from fastapi import FastAPI       # third-party

from mypackage.models import User # local
from mypackage.utils import fmt   # local

# X Wildcard imports - never use
from os.path import *             # hides what's actually imported

```

## `__init__.py` — Package Exports

```python
# mypackage/__init__.py
"""mypackage - brief description."""

__version__ = "1.0.0"

# Re-export public API at package level
from mypackage.models import User, Post
from mypackage.utils import format_name

__all__ = ("User", "Post", "format_name")

```

## Path Operations: always use pathlib

```python
from pathlib import Path

# pathlib
config_file = Path(__file__).parent / "config.json"
data_dir = Path.home() / ".myapp" / "data"
data_dir.mkdir(parents=True, exist_ok=True)

# X os.path - verbose and error-prone
import os
config_file = os.path.join(os.path.dirname(__file__), "config.json")

```

## TYPE_CHECKING Guard — Avoid Circular Imports

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mypackage.models import User  # only imported when type-checking, not at runtime

def create_session(user: "User") -> Session:
    ...

```

## pyproject.toml — Minimal Setup

```toml
[project]
name = "mypackage"
version = "1.0.0"
requires-python = ">=3.13"
dependencies = []

[tool.hatch.build.targets.wheel]
packages = ["src/mypackage"]

[tool.ruff]
line-length = 120
target-version = "py313"

```

> See `ruff-config.md` for full ruff configuration.
