---
name: agui-development
description: AG-UI protocol event structures, types, and integration guide for streaming agent responses. Use when implementing streaming UI, consuming AG-UI events from a backend agent, understanding event flow, building SSE endpoints that emit AG-UI events, handling tool call events, rendering reasoning/thinking events, or debugging event flow/ordering. Do NOT use for generic SSE endpoints that don't carry AG-UI events, or for MCP (tool-calling) or A2A (agent-to-agent) protocol integration — AG-UI is the agent-to-user layer only.
license: Personal use only — not for redistribution.
---

# AG-UI Protocol Events Reference

Quick-reference for the AG-UI (Agent-User Interaction) protocol streaming events.

## When to Use This Skill

* Building a frontend that consumes streaming agent responses
* Implementing a backend endpoint that serves AG-UI events
* Debugging event ordering or missing events in streaming flows
* Understanding the event lifecycle for tool calls, text messages, or reasoning

## Dependencies

| Package | Role | Required |
| --- | --- | --- |
| `ag-ui-protocol` (PyPI) | Python event classes (Pydantic v2) — backend emission | Yes, for a Python backend |
| `pydantic>=2.11.2` | Required by `ag-ui-protocol` for model validation/serialization | Yes (transitive) |
| `@ag-ui/core` (npm) | TypeScript event types/enums — canonical type source for frontend | Yes, for a TS/JS frontend |
| `@ag-ui/client` | SSE consumer / agent runner, depends on `@ag-ui/core` | Recommended |
| `@ag-ui/react` | React hooks (`useAgentStream`, `useAgentState`) | Optional |
| `sse-starlette` | Alternative FastAPI SSE response wrapper (see backend-guide.md) | Optional |
| `fast-json-patch` (npm) | Applying `STATE_DELTA`/`ACTIVITY_DELTA` RFC 6902 patches on the frontend | Optional |

See "Verified against" below for exact versions this skill was checked against.

## Official References

| Resource | Link |
| :--- | :--- |
| **AG-UI Protocol (GitHub)** | https://github.com/ag-ui-protocol/ag-ui |
| **AG-UI Documentation** | https://docs.ag-ui.com |
| **AG-UI Python SDK** | https://pypi.org/project/ag-ui-protocol |
| **AG-UI Core Types (TS)** | https://www.npmjs.com/package/@ag-ui/core |
| **AG-UI TypeScript SDK** | https://www.npmjs.com/package/@ag-ui/client |

**Verified against:** `ag-ui-protocol` (Python) v0.1.19 — latest on PyPI as of 2026-08-02, released 2026-06-02, `requires-python >=3.9`, `pydantic>=2.11.2` — and `@ag-ui/core` (TS) v0.0.57, latest on npm as of 2026-08-02. (Newer GitHub releases exist but are for adjacent framework-integration packages — CrewAI, Mastra, Strands, .NET clients — not the core protocol packages this skill documents.)

**Note on "protocol version":** AG-UI has no independently versioned spec — the repo's own contributor docs state "each package has independent versioning." The event names/fields are defined by whatever the reference SDKs currently implement, so the package versions above *are* the closest thing to a protocol version. Both are pre-1.0 — field names and event shapes can still change between minor releases; re-check `sdks/python/ag_ui/core/events.py` and `types.py` in the GitHub repo if something here looks stale.

---

## Event Categories (28 Total)

### 1. Lifecycle Events (5)

Control the run boundary. `RUN_STARTED`/`RUN_FINISHED`/`RUN_ERROR` bound the whole agent run; `STEP_STARTED`/`STEP_FINISHED` bound each inner iteration (e.g. one LLM call). The spec doesn't mandate a specific "layer" emits each — this is the typical nesting shown in the flow diagrams below, not a protocol rule.

| Event | Key Fields | Typical Emitter | When |
| :--- | :--- | :--- | :--- |
| `RUN_STARTED` | `threadId`, `runId` | Agent | First event of `agent.stream()` |
| `RUN_FINISHED` | `threadId`, `runId`, `result`, `outcome?` | Agent | Last event on success |
| `RUN_ERROR` | `message`, `code` | Agent/LLM | On unrecoverable error |
| `STEP_STARTED` | `stepName` | LLM | Before each LLM API call |
| `STEP_FINISHED` | `stepName`, `rawEvent.usage` | LLM | After each LLM API call (contains token usage) |

### 2. Text Message Events (4)

Streaming text content from the assistant.

| Event | Key Fields | Description |
| :--- | :--- | :--- |
| `TEXT_MESSAGE_START` | `messageId`, `role`, `name?` | Opens a new text message |
| `TEXT_MESSAGE_CONTENT` | `messageId`, `delta` | Incremental text chunk |
| `TEXT_MESSAGE_END` | `messageId` | Closes the text message |
| `TEXT_MESSAGE_CHUNK` | `messageId?`, `role?`, `delta?` | Convenience: auto-expands to Start→Content→End |

### 3. Tool Call Events (5)

Tool invocation lifecycle.

| Event | Key Fields | Description |
| :--- | :--- | :--- |
| `TOOL_CALL_START` | `toolCallId`, `toolCallName`, `parentMessageId?` | Tool invocation begins |
| `TOOL_CALL_ARGS` | `toolCallId`, `delta` | Streamed argument JSON fragment |
| `TOOL_CALL_END` | `toolCallId` | Tool invocation request complete |
| `TOOL_CALL_CHUNK` | `toolCallId?`, `toolCallName?`, `parentMessageId?`, `delta?` | Convenience: auto-expands to Start→Args→End |
| `TOOL_CALL_RESULT` | `messageId`, `toolCallId`, `content`, `role?` | Tool execution result — **no `isError` field**; failure is reported via `ToolMessage.error` on the message, not this event |

### 4. Reasoning Events (7)

Chain-of-thought / thinking visibility.

| Event | Key Fields | Description |
| :--- | :--- | :--- |
| `REASONING_START` | `messageId` | Reasoning phase begins |
| `REASONING_MESSAGE_START` | `messageId`, `role` | Individual reasoning message starts |
| `REASONING_MESSAGE_CONTENT` | `messageId`, `delta` | Reasoning text chunk |
| `REASONING_MESSAGE_END` | `messageId` | Individual reasoning message ends |
| `REASONING_MESSAGE_CHUNK` | `messageId?`, `delta?` | Convenience auto-expand |
| `REASONING_END` | `messageId` | Reasoning phase ends |
| `REASONING_ENCRYPTED_VALUE` | `subtype`, `entityId`, `encryptedValue` | Encrypted CoT (e.g. OpenAI o-series) |

### 5. State Events (3)

Synchronize agent state with the UI.

| Event | Key Fields | Description |
| :--- | :--- | :--- |
| `STATE_SNAPSHOT` | `snapshot` | Full state object |
| `STATE_DELTA` | `delta` | JSON Patch (RFC 6902) operations |
| `MESSAGES_SNAPSHOT` | `messages` | Full conversation snapshot |

### 6. Activity Events (2)

Progress indicators for long-running operations.

| Event | Key Fields | Description |
| :--- | :--- | :--- |
| `ACTIVITY_SNAPSHOT` | `messageId`, `activityType`, `content`, `replace` | Full activity state |
| `ACTIVITY_DELTA` | `messageId`, `activityType`, `patch` | JSON Patch update |

### 7. Special Events (2)

| Event | Key Fields | Description |
| :--- | :--- | :--- |
| `RAW` | `event`, `source?` | Pass-through from external systems |
| `CUSTOM` | `name`, `value` | Application-specific events |

---

## Event Flow Diagrams

### Simple Text Response

```text
RUN_STARTED
└── STEP_STARTED (iteration-0)
    ├── TEXT_MESSAGE_START
    ├── TEXT_MESSAGE_CONTENT (×N chunks)
    ├── TEXT_MESSAGE_END
    └── STEP_FINISHED (iteration-0, usage in rawEvent)
RUN_FINISHED

```

### Tool Call + Response

```text
RUN_STARTED
└── STEP_STARTED (iteration-0)
    ├── TOOL_CALL_START (toolCallId, toolCallName)
    ├── TOOL_CALL_ARGS (delta: JSON fragments ×N)
    ├── TOOL_CALL_END
    ├── TOOL_CALL_RESULT (content)
    └── STEP_FINISHED (iteration-0)
└── STEP_STARTED (iteration-1)
    ├── TEXT_MESSAGE_START
    ├── TEXT_MESSAGE_CONTENT (×N)
    ├── TEXT_MESSAGE_END
    └── STEP_FINISHED (iteration-1)
RUN_FINISHED

```

### With Reasoning/Thinking

```text
RUN_STARTED
└── STEP_STARTED (iteration-0)
    ├── REASONING_START
    ├── REASONING_MESSAGE_START
    ├── REASONING_MESSAGE_CONTENT (×N)
    ├── REASONING_MESSAGE_END
    ├── REASONING_END
    ├── TEXT_MESSAGE_START
    ├── TEXT_MESSAGE_CONTENT (×N)
    ├── TEXT_MESSAGE_END
    └── STEP_FINISHED (iteration-0)
RUN_FINISHED

```

---

## Detailed Guides

* **Event Structures Reference** — JSON shapes, field types, serialization rules → `references/event-structures.md`
* **Frontend Integration Guide** — React/TypeScript patterns, SSE consumption, state management → `references/frontend-guide.md`
* **Backend Integration Guide** — Python emission patterns, SSE endpoints, custom events → `references/backend-guide.md`
