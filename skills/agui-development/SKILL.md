---
name: agui-development
description: AG-UI protocol event structures, types, and integration guide for streaming agent responses. Use when: implementing streaming UI, consuming AG-UI events from backend agent, understanding event flow, building SSE endpoints, handling tool call events, rendering reasoning/thinking events, debugging event flow.
---

# AG-UI Protocol Events Reference

Quick-reference for the AG-UI (Agent-User Interaction) protocol streaming events.

## When to Use This Skill

* Building a frontend that consumes streaming agent responses
* Implementing a backend endpoint that serves AG-UI events
* Debugging event ordering or missing events in streaming flows
* Understanding the event lifecycle for tool calls, text messages, or reasoning

## Official References

| Resource | Link |
| :--- | :--- |
| **AG-UI Protocol (GitHub)** | https://github.com/ag-ui-protocol/ag-ui |
| **AG-UI Documentation** | https://docs.ag-ui.com |
| **AG-UI Python SDK** | https://pypi.org/project/ag-ui-protocol |
| **AG-UI Core Types (TS)** | https://www.npmjs.com/package/@ag-ui/core |
| **AG-UI TypeScript SDK** | https://www.npmjs.com/package/@ag-ui/client |

---

## Event Categories (28 Total)

### 1. Lifecycle Events (5)

Control the run boundary. Agent layer emits `RUN_*`; LLM layer emits `STEP_*`.

| Event | Key Fields | Emitted By | When |
| :--- | :--- | :--- | :--- |
| `RUN_STARTED` | `threadId`, `runId` | Agent | First event of `agent.stream()` |
| `RUN_FINISHED` | `threadId`, `runId`, `result` | Agent | Last event on success |
| `RUN_ERROR` | `message`, `code` | Agent/LLM | On unrecoverable error |
| `STEP_STARTED` | `stepName` | LLM | Before each LLM API call |
| `STEP_FINISHED` | `stepName`, `rawEvent.usage` | LLM | After each LLM API call (contains token usage) |

### 2. Text Message Events (4)

Streaming text content from the assistant.

| Event | Key Fields | Description |
| :--- | :--- | :--- |
| `TEXT_MESSAGE_START` | `messageId`, `role` | Opens a new text message |
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
| `TOOL_CALL_CHUNK` | `toolCallId?`, `toolCallName?`, `delta?` | Convenience: auto-expands to Start→Args→End |
| `TOOL_CALL_RESULT` | `messageId`, `toolCallId`, `content`, `isError` | Tool execution result |

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
    ├── TOOL_CALL_RESULT (content, isError)
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
