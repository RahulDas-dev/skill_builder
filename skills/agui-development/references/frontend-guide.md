# AG-UI Frontend Integration Guide

Patterns for consuming AG-UI streaming events in React/TypeScript frontends.

## Official AG-UI Frontend Packages

```bash
pnpm install @ag-ui/core     # BASE: all event types, enums, interfaces (use this for type inference)
pnpm install @ag-ui/client   # SSE consumer, agent runner (depends on @ag-ui/core)
pnpm install @ag-ui/react    # React hooks (useAgentStream, useAgentState)
pnpm install @ag-ui/encoder  # SSE encoding/decoding utilities

```

> **In this repo:** `@ag-ui/core` is already installed in both frontends. Always import types from `@ag-ui/core` — it is the canonical type source. `@ag-ui/client` re-exports the authoritative package for type inference and IDE autocompletion.

| Package | Role | Docs |
| --- | --- | --- |
| `@ag-ui/core` | Base types — event interfaces, `EventType` enum, `BaseEvent`, message types | https://www.npmjs.com/package/@ag-ui/core |
| `@ag-ui/client` | SSE client / agent runner | https://www.npmjs.com/package/@ag-ui/client |
| `@ag-ui/react` | React hooks | https://www.npmjs.com/package/@ag-ui/react |
| `@ag-ui/encoder` | SSE encoding/decoding | https://www.npmjs.com/package/@ag-ui/encoder |
| AG-UI Protocol Spec | — | https://docs.ag-ui.com |
| AG-UI GitHub | — | https://github.com/ag-ui-protocol/ag-ui |

---

## TypeScript Event Types

Import all event types and enums from `@ag-ui/core`:

```typescript
import type {
  BaseEvent,
  RunStartedEvent,
  RunFinishedEvent,
  RunErrorEvent,
  TextMessageStartEvent,
  TextMessageContentEvent,
  TextMessageEndEvent,
  ToolCallStartEvent,
  ToolCallArgsEvent,
  ToolCallEndEvent,
  ToolCallResultEvent,
  StateSnapshotEvent,
  StateDeltaEvent,
  CustomEvent,
} from "@ag-ui/core";
import { EventType } from "@ag-ui/core";

// EventType enum matches Python's EventType exactly:
// EventType.RUN_STARTED, EventType.TEXT_MESSAGE_CONTENT, etc.

```

---

## SSE Consumption (Vanilla)

### Using EventSource

```javascript
const eventSource = new EventSource("/api/agent/stream?message=Hello");

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch (data.type) {
    case "RUN_STARTED":
      console.log(`Run started: ${data.runId}`);
      break;

    case "TEXT_MESSAGE_START":
      // New message - initialize accumulator
      break;

    case "TEXT_MESSAGE_CONTENT":
      // Append delta to current message
      appendText(data.messageId, data.delta);
      break;

    case "TEXT_MESSAGE_END":
      // Message complete - finalize rendering
      break;

    case "TOOL_CALL_START":
      showToolIndicator(data.toolCallName);
      break;

    case "TOOL_CALL_RESULT":
      updateToolResult(data.toolCallId, data.content, data.isError);
      break;

    case "RUN_FINISHED":
      eventSource.close();
      break;

    case "RUN_ERROR":
      showError(data.message);
      eventSource.close();
      break;
  }
};

```

### Using fetch + ReadableStream (Better Control)

```typescript
async function streamAgent(message: string) {
  const response = await fetch("/api/agent/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop()!; // Keep incomplete line in buffer

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const event = JSON.parse(line.slice(6));
        handleEvent(event);
      }
    }
  }
}

```

---

## React Patterns

### Message Accumulator Hook

```typescript
import { useState, useCallback } from "react";

interface StreamMessage {
  id: string;
  role: string;
  content: string;
  isComplete: boolean;
}

interface ToolCall {
  id: string;
  name: string;
  args: string;
  result?: string;
  isError?: boolean;
  isComplete: boolean;
}

function useAgentStream() {
  const [messages, setMessages] = useState<StreamMessage[]>([]);
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [reasoning, setReasoning] = useState<string>("");

  const handleEvent = useCallback((event: any) => {
    switch (event.type) {
      case "RUN_STARTED":
        setIsRunning(true);
        break;

      case "TEXT_MESSAGE_START":
        setMessages((prev) => [
          ...prev,
          { id: event.messageId, role: event.role, content: "", isComplete: false },
        ]);
        break;

      case "TEXT_MESSAGE_CONTENT":
        setMessages((prev) =>
          prev.map((m) =>
            m.id === event.messageId ? { ...m, content: m.content + event.delta } : m
          )
        );
        break;

      case "TEXT_MESSAGE_END":
        setMessages((prev) =>
          prev.map((m) =>
            m.id === event.messageId ? { ...m, isComplete: true } : m
          )
        );
        break;

      case "TOOL_CALL_START":
        setToolCalls((prev) => [
          ...prev,
          { id: event.toolCallId, name: event.toolCallName, args: "", isComplete: false },
        ]);
        break;

      case "TOOL_CALL_ARGS":
        setToolCalls((prev) =>
          prev.map((tc) =>
            tc.id === event.toolCallId ? { ...tc, args: tc.args + event.delta } : tc
          )
        );
        break;

      case "TOOL_CALL_END":
        setToolCalls((prev) =>
          prev.map((tc) =>
            tc.id === event.toolCallId ? { ...tc, isComplete: true } : tc
          )
        );
        break;

      case "TOOL_CALL_RESULT":
        setToolCalls((prev) =>
          prev.map((tc) =>
            tc.id === event.toolCallId
              ? { ...tc, result: event.content, isError: event.isError }
              : tc
          )
        );
        break;

      case "REASONING_MESSAGE_CONTENT":
        setReasoning((prev) => prev + event.delta);
        break;

      case "RUN_FINISHED":
        setIsRunning(false);
        break;

      case "RUN_ERROR":
        setIsRunning(false);
        console.error("Agent error:", event.message);
        break;
    }
  }, []);

  return { messages, toolCalls, reasoning, isRunning, handleEvent };
}

```

### Chat Component

```typescript
function AgentChat() {
  const { messages, toolCalls, reasoning, isRunning, handleEvent } = useAgentStream();

  const sendMessage = async (text: string) => {
    const response = await fetch("/api/agent/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });

    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop()!;
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          handleEvent(JSON.parse(line.slice(6)));
        }
      }
    }
  };

  return (
    <div>
      {reasoning && <CollapsibleThinking text="{reasoning}"/>}
      {messages.map((m) => (
        <MessageBubble content="{m.content}" key="{m.id}" role="{m.role}" streaming="{!m.isComplete}"/>
      ))}
      {toolCalls.map((tc) => (
        <ToolCallCard args="{tc.args}" key="{tc.id}" name="{tc.name}" result="{tc.result}"/>
      ))}
      <ChatInput disabled="{isRunning}" onSend="{sendMessage}"/>
    </div>
  );
}

```

---

## State Management with AG-UI

### Applying State Snapshots

```typescript
case "STATE_SNAPSHOT":
  // Replace entire state
  setState(event.snapshot);
  break;

```

### Applying State Deltas (JSON Patch)

```typescript
import { applyPatch } from "fast-json-patch";

case "STATE_DELTA":
  // Apply RFC 6902 JSON Patch operations
  setState(prev => applyPatch(prev, event.delta).newDocument);
  break;

```

**Install:** `pnpm install fast-json-patch`

## Key Frontend Considerations

1. **Event ordering is guaranteed** — events arrive in emission order via SSE
2. `messageId` **correlation** — always match START/CONTENT/END by `messageId`
3. `toolCallId` **correlation** — match TOOL_CALL_START through TOOL_CALL_RESULT by `toolCallId`
4. `delta` **is incremental** — concatenate deltas, don't replace
5. `isError` **on TOOL_CALL_RESULT** — render tool failures differently
6. `RUN_FINISHED` **signals completion** — close EventSource, stop loading indicators
7. `STEP_FINISHED.rawEvent.usage` — extract token counts for cost display
8. **Reasoning events are optional** — not all models/providers emit them
9. **Timestamps are Unix milliseconds** — use `new Date(event.timestamp)` to convert