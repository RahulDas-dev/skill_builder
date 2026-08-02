---
name: python-dev
description: Pythonic idioms, PEP 8 standards, type hints, and best practices for building robust, efficient, and maintainable Python applications. Use when designing packages, implementing type hints, or establishing coding standards.
---

# Python Development Patterns

## When to Activate

* Writing/reviewing/refactoring Python code
* Designing Python packages/modules
* Implementing type hints or logging
* Establishing or enforcing coding standards

## Package Manager: uv (NOT pip)

```bash
uv sync                 # Install dependencies
uv run <command>        # Run commands
uv add <package>        # Add package
uv add <package> --dev  # Dev dependency

```

## Mandatory After Every Code Change

```bash
uv run ruff format -v .      # Format code
uv run ruff check -v .       # Check for issues
uv run ruff check -v . --fix # Auto-fix issues
uv run pyclean -v .          # Clean cache

```

## Type Hints (Python 3.10+)

Use modern syntax — NOT legacy `typing` module:

```python
# Modern
def process(name: str | None) -> bool:             # not Optional[str]
def handle(items: list[str]) -> dict[str, int]:    # not List, Dict
def convert(value: str | int | float) -> str:     # not Union[...]
def get_coords() -> tuple[int, int]:               # not Tuple[int, int]

# Only import these from typing when needed:
from typing import Any, Literal, Protocol, TypeVar, TYPE_CHECKING

```

## Logging (NOT print)

```python
import logging
logger = logging.getLogger(__name__)  # module-level, always __name__

# % formatting - lazy evaluation (G004 rule)
logger.info("User %s processed %d items", name, count)
logger.exception("Failed: %s", op)    # inside except block - includes traceback

# X f-strings in log calls - always evaluated even if level is suppressed
logger.info(f"User {name}")           # G004 violation

```

> See `references/logging.md` for full logging patterns, `extra={}` structured logging, and configuration.

## Core Patterns

```python
# EAFP - use exceptions, not pre-checks
try:
    return dictionary[key]
except KeyError:
    return default_value

# Specific exception handling - never bare except
try:
    parsed = json.loads(data)
except json.JSONDecodeError as e:
    raise ValueError(f"Failed to parse data") from e  # chain exceptions

# Context managers for all resources
with open(path) as f:
    return f.read()

```

> See `references/patterns.md` for error handling hierarchy, context manager classes, and decorator patterns.

## Anti-Patterns to Avoid

```python
# X Mutable default argument
def append_to(item, items=[]): ...
# Use None sentinel
def append_to(item, items=None):
    if items is None: items = []

# X type() comparison
if type(obj) == list: ...
# isinstance
if isinstance(obj, list): ...

# X None comparison with ==
if value == None: ...
# identity check
if value is None: ...

# X Bare except
try: risky()
except: pass
# Specific exception
try: risky()
except SpecificError as e: logger.exception("Failed: %s", e)

```

## Quick Reference: Python Idioms

| Idiom | Use For |
| --- | --- |
| **EAFP** | Dictionary access, attribute lookup |
| **`with` statement** | Files, DB connections, locks |
| **List comprehensions** | Simple in-memory transforms |
| **Generators / `yield`** | Large data sets, lazy evaluation |
| **`dataclass`** | Data containers with auto `__init__` / `__repr__` |
| **`NamedTuple`** | Immutable records with field names |
| **`__slots__`** | High-volume objects needing memory efficiency |
| **`pathlib.Path`** | All path operations (not `os.path`) |
| **`enumerate`** | Index + element loops (not manual counter) |

## Line Length & Environment

* **Line length:** 120 characters
* **Indent:** 4 spaces
* **Python version:** 3.13+

## References

| File | Contents |
| --- | --- |
| `references/logging.md` | Full logging guide — levels, structured logging, configuration |
| `references/patterns.md` | Error handling, context managers, decorators |
| `references/data-structures.md` | Dataclasses, NamedTuples, comprehensions, generators |
| `references/package-organization.md` | Package layout, import conventions, performance tips |
| `references/ruff-config.md` | Full pyproject.toml ruff setup |

