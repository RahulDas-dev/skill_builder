# AG-UI Event Structures Reference

Complete JSON shapes for every AG-UI event. All events serialize to camelCase via `to_dict()`.

## Common Fields (All Events)

```json
{
  "type": "EVENT_TYPE",       // string - EventType enum value
  "timestamp": 1741564800000, // int - Unix ms (auto-generated)
  "rawEvent": { ... }         // any - optional provider-specific data
}

```

---

## Lifecycle Events

### RUN_STARTED

```json
{
  "type": "RUN_STARTED",
  "threadId": "session-abc123",
  "runId": "run-a1b2c3d4e5f6",
  "parentRunId": null,
  "timestamp": 1741564800000
}

```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `threadId` | `string` | Yes | Session/conversation identifier |
| `runId` | `string` | Yes | Unique run identifier |
| `parentRunId` | `string?` | No | Parent run for nested agent calls |
| `input` | `object?` | No | Agent input payload |

### RUN_FINISHED

```json
{
  "type": "RUN_FINISHED",
  "threadId": "session-abc123",
  "runId": "run-a1b2c3d4e5f6",
  "result": null,
  "rawEvent": {
    "usage": { "input_tokens": 150, "output_tokens": 80, "total_tokens": 230 },
    "iterations": 1
  },
  "timestamp": 1741564800500
}

```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `threadId` | `string` | Yes | Session identifier |
| `runId` | `string` | Yes | Run identifier |
| `result` | `any?` | No | Final result data |
| `rawEvent` | `object?` | No | Contains `usage` and `iterations` in this framework |

### RUN_ERROR

```json
{
  "type": "RUN_ERROR",
  "message": "Model throttled: rate limit exceeded",
  "code": "RATE_LIMIT",
  "timestamp": 1741564800100
}

```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `message` | `string` | Yes | Human-readable error |
| `code` | `string?` | No | Machine-readable error code |

### STEP_STARTED / STEP_FINISHED

```json
{
  "type": "STEP_STARTED",
  "stepName": "iteration-0",
  "timestamp": 1741564800050
}

```

```json
{
  "type": "STEP_FINISHED",
  "stepName": "iteration-0",
  "rawEvent": {
    "usage": { "input_tokens": 120, "output_tokens": 60, "total_tokens": 180 }
  },
  "timestamp": 1741564800400
}

```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `stepName` | `string` | Yes | Step identifier (format: `iteration-N`) |
| `rawEvent` | `object?` | No | `STEP_FINISHED` includes token usage here |

> **Note:** The iteration number in `stepName` is 0-indexed. `iteration-0` is the first LLM call, `iteration-1` is the second (after tool execution), etc.

---

## Text Message Events

### TEXT_MESSAGE_START

```json
{
  "type": "TEXT_MESSAGE_START",
  "messageId": "msg-uuid-1234",
  "role": "assistant",
  "timestamp": 1741564800100
}

```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `messageId` | `string` | Yes | Unique message identifier |
| `role` | `string` | Yes | One of: `"developer"`, `"system"`, `"assistant"`, `"user"` |

### TEXT_MESSAGE_CONTENT

```json
{
  "type": "TEXT_MESSAGE_CONTENT",
  "messageId": "msg-uuid-1234",
  "delta": "Hello! I can help you ",
  "timestamp": 1741564800120
}

```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `messageId` | `string` | Yes | Must match the `messageId` from `TEXT_MESSAGE_START` |
| `delta` | `string` | Yes | Incremental text fragment |

### TEXT_MESSAGE_END

```json
{
  "type": "TEXT_MESSAGE_END",
  "messageId": "msg-uuid-1234",
  "timestamp": 1741564800300
}

```

### TEXT_MESSAGE_CHUNK (Convenience)

```json
{
  "type": "TEXT_MESSAGE_CHUNK",
  "messageId": "msg-uuid-1234",
  "role": "assistant",
  "delta": "chunk of text",
  "timestamp": 1741564800150
}

```

> Auto-manages `START` -> `CONTENT` -> `END` lifecycle. Use when you don't need granular control.

---

## Tool Call Events

### TOOL_CALL_START

```json
{
  "type": "TOOL_CALL_START",
  "toolCallId": "tc-abc123",
  "toolCallName": "calculator",
  "parentMessageId": "msg-uuid-1234",
  "timestamp": 1741564800100
}

```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `toolCallId` | `string` | Yes | Unique tool call ID (from LLM response) |
| `toolCallName` | `string` | Yes | Name of the tool being called |
| `parentMessageId` | `string?` | No | Message that triggered this tool call |

### TOOL_CALL_ARGS

```json
{
  "type": "TOOL_CALL_ARGS",
  "toolCallId": "tc-abc123",
  "delta": "{\"operation\": \"add\", ",
  "timestamp": 1741564800120
}

```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `toolCallId` | `string` | Yes | Must match `TOOL_CALL_START` |
| `delta` | `string` | Yes | JSON fragment of tool arguments |

> **Frontend note:** Concatenate all `delta` values to reconstruct the full JSON arguments.

### TOOL_CALL_END

```json
{
  "type": "TOOL_CALL_END",
  "toolCallId": "tc-abc123",
  "timestamp": 1741564800150
}

```

### TOOL_CALL_RESULT

```json
{
  "type": "TOOL_CALL_RESULT",
  "messageId": "result-uuid-5678",
  "toolCallId": "tc-abc123",
  "content": "Result: 42",
  "isError": false,
  "role": "tool",
  "timestamp": 1741564800200
}

```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `messageId` | `string` | Yes | Unique result message ID |
| `toolCallId` | `string` | Yes | ID of the tool call this result answers |
| `content` | `string` | Yes | Tool execution result (always string) |
| `isError` | `boolean` | No | `true` if tool execution failed (default: `false`) |
| `role` | `string?` | No | Always `"tool"` when present |

### TOOL_CALL_CHUNK (Convenience)

```json
{
  "type": "TOOL_CALL_CHUNK",
  "toolCallId": "tc-abc123",
  "toolCallName": "calculator",
  "delta": "{\"a\": 5}",
  "timestamp": 1741564800130
}

```

---

## Reasoning Events

### REASONING_START / REASONING_END

```json
{ "type": "REASONING_START", "messageId": "reasoning-uuid", "timestamp": 1741564800050 }
{ "type": "REASONING_END", "messageId": "reasoning-uuid", "timestamp": 1741564800090 }

```

### REASONING_MESSAGE_START / CONTENT / END

```json
{ "type": "REASONING_MESSAGE_START", "messageId": "rm-uuid", "role": "assistant", "timestamp": ... }
{ "type": "REASONING_MESSAGE_CONTENT", "messageId": "rm-uuid", "delta": "Let me think...", "timestamp": ... }
{ "type": "REASONING_MESSAGE_END", "messageId": "rm-uuid", "timestamp": ... }

```

### REASONING_ENCRYPTED_VALUE

```json
{
  "type": "REASONING_ENCRYPTED_VALUE",
  "subtype": "message",
  "entityId": "entity-uuid",
  "encryptedValue": "base64-encrypted-cot-data...",
  "timestamp": 1741564800070
}

```

| Field | Type | Values | Description |
| --- | --- | --- | --- |
| `subtype` | `string` | `"tool-call"` or `"message"` | What the encrypted value represents |
| `entityId` | `string` | — | ID of the entity this belongs to |
| `encryptedValue` | `string` | — | Encrypted chain-of-thought content |

---

## State Events

### STATE_SNAPSHOT

```json
{
  "type": "STATE_SNAPSHOT",
  "snapshot": { "user_name": "Alice", "preferences": { "theme": "dark" } },
  "timestamp": 1741564800200
}

```

### STATE_DELTA (JSON Patch RFC 6902)

```json
{
  "type": "STATE_DELTA",
  "delta": [
    { "op": "replace", "path": "/preferences/theme", "value": "light" },
    { "op": "add", "path": "/last_query", "value": "weather" }
  ],
  "timestamp": 1741564800250
}

```

### MESSAGES_SNAPSHOT

```json
{
  "type": "MESSAGES_SNAPSHOT",
  "messages": [
    { "role": "user", "content": "Hello" },
    { "role": "assistant", "content": "Hi there!" }
  ],
  "timestamp": 1741564800300
}

```

---

## Activity Events

### ACTIVITY_SNAPSHOT

```json
{
  "type": "ACTIVITY_SNAPSHOT",
  "messageId": "activity-uuid",
  "activityType": "searching",
  "content": "Searching knowledge base...",
  "replace": true,
  "timestamp": 1741564800150
}

```

| Field | Type | Description |
| --- | --- | --- |
| `replace` | `boolean` | If `true`, replaces previous activity with same `messageId` |

### ACTIVITY_DELTA

```json
{
  "type": "ACTIVITY_DELTA",
  "messageId": "activity-uuid",
  "activityType": "searching",
  "patch": [{ "op": "replace", "path": "/progress", "value": 75 }],
  "timestamp": 1741564800180
}

```

---

## Special Events

### RAW

```json
{
  "type": "RAW",
  "event": { "provider": "bedrock", "raw_response": { ... } },
  "source": "bedrock-converse",
  "timestamp": 1741564800100
}

```

### CUSTOM

```json
{
  "type": "CUSTOM",
  "name": "cost_update",
  "value": { "total_cost_usd": 0.0023 },
  "timestamp": 1741564800200
}

```

---

## Serialization Rules

1. **Python → JSON:** All fields serialize to camelCase (`tool_call_id` → `toolCallId`)
2. **Timestamps:** Unix milliseconds (`int(time.time() * 1000)`)
3. **Optional fields:** Omitted from output when `None` (not serialized as `null`)
4. **isError:** Only included when `true`
5. **to_dict():** Every event has a `to_dict()` method for JSON serialization

### Python Dataclass $\rightarrow$ JSON Mapping

| Python Field | JSON Key |
| --- | --- |
| `thread_id` | `threadId` |
| `run_id` | `runId` |
| `parent_run_id` | `parentRunId` |
| `message_id` | `messageId` |
| `tool_call_id` | `toolCallId` |
| `tool_call_name` | `toolCallName` |
| `parent_message_id` | `parentMessageId` |
| `step_name` | `stepName` |
| `is_error` | `isError` |
| `raw_event` | `rawEvent` |
| `activity_type` | `activityType` |
| `encrypted_value` | `encryptedValue` |
| `entity_id` | `entityId` |
