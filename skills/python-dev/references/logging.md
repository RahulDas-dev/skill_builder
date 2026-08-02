# Python Logging Guide

## Setup

```python
import logging

# Module-level logger - always use __name__
logger = logging.getLogger(__name__)

```

## Log Levels

| Level | When to use |
| --- | --- |
| **DEBUG** | Detailed diagnostic info (disabled in production) |
| **INFO** | Confirming things work as expected |
| **WARNING** | Something unexpected but recoverable |
| **ERROR** | Failure that prevented an operation |
| **CRITICAL** | Application-level failure |

## Message Formatting (G004 rule)

```python
# % formatting - lazy: string only built if level is enabled
logger.info("User %s processed %d items in %.2fs", name, count, elapsed)
logger.debug("Request payload: %s", payload)
logger.warning("Retry %d/%d for %s", attempt, max_retries, operation)

# X f-strings - eager: always evaluated, even if DEBUG is suppressed
logger.info(f"User {name} processed {count} items")  # G004 violation

```

## Exception Logging (TRY400 / TRY401 rules)

```python
# logger.exception() - includes full traceback automatically
try:
    result = process_data(data)
except Exception:
    logger.exception("Failed to process data_id=%s", data_id)
    raise

# logger.error() with exc_info=True - same as exception(), explicit
try:
    result = process_data(data)
except Exception:
    logger.error("Failed to process data_id=%s", data_id, exc_info=True)
    raise

# X TRY401 - don't pass exception object to logger.exception()
try:
    process()
except Exception as e:
    logger.exception("Failed: %s", e)  # redundant - traceback already contains e

# X TRY400 - don't use logger.error() without exc_info inside except
try:
    process()
except Exception as e:
    logger.error("Failed: %s", e)      # loses traceback - use logger.exception()

```

## Structured Logging with extra

```python
# Add structured context fields to any log record
logger.info(
    "Request completed: status=%s latency_ms=%d",
    status,
    latency_ms,
    extra={"session_id": session_id, "user_id": user_id},
)

# In exception handlers
try:
    call_api(endpoint)
except Exception:
    logger.exception(
        "API call failed: endpoint=%s",
        endpoint,
        extra={"provider": provider, "model": model_id},
    )
    raise

```

## Conditional Debug Logging (expensive payloads)

```python
# Guard expensive serialization behind level check
if logger.isEnabledFor(logging.DEBUG):
    logger.debug("Full response: %s", json.dumps(response, indent=2))

```

## Logger Configuration (app entry point only)

```python
# Configure once at entry point (main.py / __main__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

# Library code: NEVER call basicConfig or add handlers
# Library code: only get a logger and call log methods

```

## Quick Reference

```python
logger.debug("Cache miss: key=%s", key)
logger.info("Agent started: session=%s model=%s", session_id, model)
logger.warning("Token limit approaching: used=%d max=%d", used, max_tokens)
logger.error("Tool execution failed: tool=%s", tool_name, exc_info=True)
logger.exception("Unhandled error in generate()")  # inside except block only

```

