# A2UI ↔ AG-UI: How They Relate

A2UI and AG-UI are two separate protocols that solve different problems and are explicitly designed to be used together — or entirely independently. This file is the single place this skill covers that relationship; `frontend-guide.md` and `backend-guide.md` intentionally don't repeat it.

## Are They the Same Protocol?

No.

| | AG-UI | A2UI |
| --- | --- | --- |
| Solves | Agent run/event lifecycle: `RUN_STARTED`, text streaming, tool calls, reasoning, state sync | Declarative UI rendering: surfaces, components, data binding |
| Unit of communication | An event (`RUN_STARTED`, `TEXT_MESSAGE_CONTENT`, `STATE_DELTA`, ...) | A message (`createSurface`, `updateComponents`, `updateDataModel`, `deleteSurface`) |
| Answers | "What is the agent doing right now?" | "What should the screen look like right now?" |

Neither subsumes the other. AG-UI has no concept of a UI component; A2UI has no concept of a tool call or reasoning trace.

## Can A2UI Be Used Standalone, Without AG-UI?

**Yes.** A2UI's wire format has no dependency on AG-UI at all — it's plain JSON envelopes (see `message-structures.md`) that travel over whatever transport you choose: raw SSE, a plain WebSocket, REST, MCP, or A2A. If your agent only needs to render UI and has no other streaming/event needs, you never have to touch AG-UI — see `backend-guide.md`'s "Direct SSE" example, which is a complete, self-contained A2UI implementation with zero AG-UI involvement.

## When Would You Combine Them?

If your agent *already* streams AG-UI events (chat text, tool calls, reasoning) and you *also* want to render rich widgets — a form, a card, a picklist — in that same conversation, you don't need a second channel. Carry the A2UI envelope as the payload of an AG-UI event you're already emitting.

### Concrete example: A2UI riding inside an AG-UI `CUSTOM` event

Backend (Python) — reuse the message builders from `backend-guide.md`, wrap one as an AG-UI event instead of sending it over raw SSE directly:

```python
from ag_ui.core import CustomEvent  # from the agui-development skill's backend guide

surface_message = build_create_surface(
    "user_profile_card",
    catalog_id="https://a2ui.org/specification/v0_9_1/catalogs/basic/catalog.json",
)

agui_wrapper = CustomEvent(name="a2ui_message", value=surface_message)
# emit agui_wrapper exactly like any other AG-UI event (model_dump(by_alias=True), SSE frame, etc.)
```

Frontend (TypeScript) — in your AG-UI event switch, route `CUSTOM` events named `a2ui_message` into the A2UI message handler from `frontend-guide.md`:

```typescript
case "CUSTOM":
  if (event.name === "a2ui_message") {
    applyMessage(surfaces, event.value); // applyMessage is from frontend-guide.md
  }
  break;
```

That's the entire integration surface — A2UI doesn't need to know AG-UI exists, and AG-UI doesn't need to know what's inside a `CUSTOM` event's `value`.

## How Their Own Maintainers Position This

Google's A2UI announcement lists **AG-UI/CopilotKit as a partner with "day-zero compatibility"** — this is the source for treating the two as intentionally complementary rather than competing. Beyond that general framing, there is no vendor-published, field-level "A2UI-over-AG-UI extension spec" this skill has independently verified — unlike A2A, which the A2UI repo documents explicitly under `specification/v1_0/extensions/a2a/docs/a2ui_extension_specification.md`. Treat the `CUSTOM`-event-wrapping pattern above as a spec-consistent, sensible default — not a copy of an official mapping document, because none was found to copy from.
