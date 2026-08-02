# AG-UI Backend Integration Guide

Patterns for emitting AG-UI events from a Python backend using the `ag-ui-protocol` SDK.

## Installing the SDK

```bash
uv add ag-ui-protocol
# or
pip install ag-ui-protocol

```

## Importing Event Classes

```python
from ag_ui.core import (
    # Enums & Base
    EventType, BaseEvent,
    # Lifecycle
    RunStartedEvent, RunFinishedEvent, RunErrorEvent,
    StepStartedEvent, StepFinishedEvent,
    # Text
    TextMessageStartEvent, TextMessageContentEvent, TextMessageEndEvent,
    # Tools
    ToolCallStartEvent, ToolCallArgsEvent, ToolCallEndEvent, ToolCallResultEvent,
    # Reasoning
    ReasoningStartEvent, ReasoningMessageStartEvent,
    ReasoningMessageContentEvent, ReasoningMessageEndEvent,
    # State
    StateSnapshotEvent, StateDeltaEvent, MessagesSnapshotEvent,
    # Activity
    ActivitySnapshotEvent, ActivityDeltaEvent,
    # Special
    RawEvent, CustomEvent,
)

```

## Event Lifecycle

A well-formed AG-UI stream follows this order:

```text
RUN_STARTED
  STEP_STARTED
    TEXT_MESSAGE_START -> TEXT_MESSAGE_CONTENT (*N) -> TEXT_MESSAGE_END
    TOOL_CALL_START -> TOOL_CALL_ARGS -> TOOL_CALL_END -> TOOL_CALL_RESULT
    REASONING_START -> REASONING_MESSAGE_* -> REASONING_END
  STEP_FINISHED
RUN_FINISHED  (or RUN_ERROR on failure)

```

## SSE Endpoint Patterns

### FastAPI + StreamingResponse

```python
import json
import uuid
import time
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from ag_ui.core import (
    RunStartedEvent, RunFinishedEvent,
    TextMessageStartEvent, TextMessageContentEvent, TextMessageEndEvent,
    StepStartedEvent, StepFinishedEvent,
)

app = FastAPI()

class ChatRequest(BaseModel):
    message: str
    thread_id: str = ""
    run_id: str = ""

def _ts() -> int:
    return int(time.time() * 1000)

async def event_generator(req: ChatRequest):
    thread_id = req.thread_id or str(uuid.uuid4())
    run_id = req.run_id or str(uuid.uuid4())
    msg_id = str(uuid.uuid4())

    def emit(event: BaseEvent) -> str:
        return f"data: {json.dumps(event.model_dump())}\n\n"

    yield emit(RunStartedEvent(thread_id=thread_id, run_id=run_id, timestamp=_ts()))
    yield emit(StepStartedEvent(step_name="generate", timestamp=_ts()))
    yield emit(TextMessageStartEvent(message_id=msg_id, role="assistant", timestamp=_ts()))

    # --- Replace this block with your LLM streaming call ---------------------
    full_response = "Hello! How can I help you today?"
    for chunk in full_response.split():
        yield emit(TextMessageContentEvent(message_id=msg_id, delta=chunk + " ", timestamp=_ts()))
    # ------------------------------------------------------------------------

    yield emit(TextMessageEndEvent(message_id=msg_id, timestamp=_ts()))
    yield emit(StepFinishedEvent(step_name="generate", timestamp=_ts()))
    yield emit(RunFinishedEvent(thread_id=thread_id, run_id=run_id, timestamp=_ts()))

@app.post("/api/agent/stream")
async def stream_agent(request: ChatRequest):
    return StreamingResponse(
        event_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

```

### Starlette SSE with EventSourceResponse

```python
from sse_starlette.sse import EventSourceResponse

@app.post("/api/agent/stream")
async def stream_agent(request: ChatRequest):
    async def generate():
        async for chunk in event_generator(request):
            # EventSourceResponse wraps each yield as a data frame automatically
            yield {"data": chunk.removeprefix("data: ").strip()}

    return EventSourceResponse(generate())

```

Install: `uv add sse-starlette`

## Emitting Custom Events

### Activity Indicators

```python
# Show progress to frontend
yield ActivitySnapshotEvent(
    message_id="search-1",
    activity_type="searching",
    content="Searching knowledge base...",
    replace=True,
)

# Incremental update
yield ActivityDeltaEvent(
    message_id="search-1",
    activity_type="searching",
    patch=[{"op": "replace", "path": "/progress", "value": 75}],
)

```

### State Synchronization

```python
# Send full state snapshot
yield StateSnapshotEvent(snapshot={"user": "Alice", "cart": []})

# Incremental update (JSON Patch RFC 6902)
yield StateDeltaEvent(delta=[
    {"op": "add", "path": "/cart/-", "value": {"item": "Widget", "qty": 1}},
])

```

### Custom Application Events

```python
yield CustomEvent(name="cost_update", value={"total_cost_usd": 0.0042})
yield CustomEvent(name="source_citation", value={"url": "...", "title": "..."})

```

## Serialization

Use `model_dump()` (Pydantic v2) or `to_dict()` for serialization:

```python
event = ToolCallStartEvent(tool_call_id="tc-1", tool_call_name="calculator")
print(json.dumps(event.model_dump()))
# {"type": "TOOL_CALL_START", "toolCallId": "tc-1", "toolCallName": "calculator", "timestamp": ...}

```

## Key Backend Considerations

1. **Event ordering matters** — always yield START before CONTENT before END
2. `model_dump()` handles serialization — never manually construct event JSON
3. Every run needs a unique `run_id` — generate with `uuid.uuid4()` if not provided by client
4. Always Close with `RUN_FINISHED` or `RUN_ERROR` — client need a terminal oevent to stop listening
5. Timestamps are miliseconds since epoch —  use `int(time.time()*1000)`
6. set `X-Accel-Buffereing: no` — prevents nginx from buffereings SSE responses 
