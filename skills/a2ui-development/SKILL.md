---
name: a2ui-development
description: Google's A2UI (Agent-to-UI) protocol — declarative agent-generated UI, message envelopes, component catalogs, and data binding. Use when an agent needs to render rich interactive UI (not just text) declaratively across web/mobile/desktop, when parsing or emitting createSurface/updateComponents/updateDataModel/deleteSurface messages, when building a native A2UI renderer or emitter from the wire spec, or when validating a payload against the official A2UI schema. Do NOT use for agent event/streaming lifecycle concerns (run/step/tool-call/reasoning events) — this skill covers only the UI-rendering payload format, not the transport or event stream carrying it.
license: Personal use only — not for redistribution.
---

# A2UI Protocol Development Guide

Reference for Google's A2UI (Agent-to-UI) protocol — a declarative wire format that lets an agent describe rich, interactive UI as structured JSON instead of executable code or raw HTML.

## When to Use This Skill

* Implementing an agent backend that needs to render forms, cards, lists, or other rich widgets — not just chat text
* Building a native A2UI renderer (web, mobile, or desktop) that consumes `createSurface`/`updateComponents`/`updateDataModel` messages
* Parsing or emitting A2UI messages by hand, without adopting a full ready-made renderer SDK
* Validating a hand-built A2UI payload against the official schema
* Debugging surface/component/data-model synchronization issues

## Dependencies

A2UI has many ready-made renderer/solution packages across languages. **This skill deliberately does not teach any of them as "the way" to implement A2UI** — the goal is understanding the wire format well enough to emit/consume it natively. The packages below are useful only as a schema/type *reference to validate against*:

| Package | Ecosystem | Role | Use it for |
| --- | --- | --- | --- |
| `a2ui-core` (PyPI) | Python | Deps: `pydantic`, `jsonschema`, `referencing` only — no agent-framework lock-in | Validating a hand-built payload dict against the official JSON Schema |
| `@a2ui/web_core` (npm) | JS/TS | Official core lib; deps `zod`, `zod-to-json-schema` | Runtime validation of messages you constructed yourself |
| `@a2ui-sdk/types` (npm) | TS | Zero runtime deps, types only | Compile-time type-checking only, no runtime cost |

**Intentionally out of scope** (full ready-made solutions, not covered here): `a2ui-agent-sdk` (PyPI — pulls in `google-adk`, `google-genai`, `a2a-sdk`), `@a2ui/react`, `@a2ui/lit`, `@a2ui/angular`, `@copilotkit/a2ui-renderer`, `a2ui-vue`, `a2ui-shadcn`, and similar. Reach for these only if you've decided you *don't* need to understand the wire format — this skill assumes you do.

**Canonical source of truth**, no package required: `github.com/a2ui-project/a2ui/specification/{version}/json/` and `.../catalogs/basic/` — the actual versioned JSON Schema and catalog files, fetchable directly.

## Official References

| Resource | Link |
| :--- | :--- |
| **A2UI Spec Site** | https://a2ui.org |
| **A2UI GitHub Repo** | https://github.com/a2ui-project/a2ui |
| **What is A2UI?** | https://a2ui.org/introduction/what-is-a2ui/ |
| **Message Reference** | https://a2ui.org/reference/messages/ |
| **Data Binding Concepts** | https://a2ui.org/concepts/data-binding/ |
| **Component Gallery** | https://a2ui.org/reference/components/ |

### Version Status

| Version | Status per a2ui.org | Notes |
| --- | --- | --- |
| v0.8 | Legacy | Different envelope shape — see Gotchas in `references/message-structures.md` |
| v0.9 | Stable | First version of the current `{"version": ..., "<messageType>": {...}}` envelope |
| v0.9.1 | **Current production** (per a2ui.org, spec dated 2025-11-20) | This skill documents v0.9.1 as the baseline |
| v1.0 | Candidate on a2ui.org | The GitHub repo's `specification/v1_0/` directory (with its own `evolution_guide.md`) appears further along than the public docs site reflects — **check both sources before committing to a version** in a real project |

## Message Types

Every A2UI message is a JSON envelope with a `version` field plus exactly one of these keys:

| Message | Direction | Key Fields | Purpose |
| :--- | :--- | :--- | :--- |
| `createSurface` | Agent → Client | `surfaceId`, `catalogId`, `theme?`, `sendDataModel?` | Initialize a new UI surface |
| `updateComponents` | Agent → Client | `surfaceId`, `components[]` (flat, ID-referenced) | Add or modify component definitions on a surface |
| `updateDataModel` | Agent → Client | `surfaceId`, `path?` (RFC 6901, defaults to `/`), `value?` | Insert or replace data-model values (drives reactive UI updates) |
| `deleteSurface` | Agent → Client | `surfaceId` | Remove a surface entirely |

> Client capability negotiation (which catalogs a client can render) happens via transport metadata — a `supportedCatalogIds` array — not as an A2UI message itself.

## Message Flow

### Typical surface lifecycle

```text
createSurface (surfaceId, catalogId)
└── updateComponents (surfaceId, components: [...])
    └── updateDataModel (surfaceId, path: "/", value: {...})
        └── updateDataModel (surfaceId, path: "/user/name", value: "Alice")  (×N, incremental)
deleteSurface (surfaceId)
```

### Interactive form round-trip

```text
Agent: createSurface -> updateComponents (TextField bound to /form/name)
Client: user types "Alice" -> client-side write to /form/name (no message to agent required)
Agent: (reads the updated data model back via whatever channel this project already uses)
Agent: updateDataModel (path: "/form/status", value: "submitted")
```

## Relationship to AG-UI

A2UI and AG-UI are separate protocols, explicitly designed to be used together *or* independently — neither requires the other. AG-UI covers the agent event/run lifecycle (text streaming, tool calls, reasoning, state sync); A2UI covers UI rendering (surfaces, components, data binding). **A2UI works fully standalone** over plain SSE/WebSockets/REST with zero AG-UI involvement. The two can also be combined — e.g. carrying an A2UI message as the payload of an AG-UI `CUSTOM` event — if a project already streams AG-UI and also wants rich UI. Full detail, including which approach to pick and a worked example of combining them, is in `references/agui-relationship.md`.

## Detailed Guides

* **Message Structures Reference** — full JSON shapes, component/catalog model, data-binding syntax, version differences → `references/message-structures.md`
* **Frontend (Client) Guide** — building a native renderer: flat-list-to-tree, JSON Pointer resolution, reactive updates → `references/frontend-guide.md`
* **Backend (Agent) Guide** — constructing and validating messages natively, transport options → `references/backend-guide.md`
* **AG-UI Relationship** — standalone vs. combined use, and a worked A2UI-over-AG-UI example → `references/agui-relationship.md`
