# A2UI Backend (Agent) Guide — Constructing Messages Natively

How an agent backend builds and validates A2UI messages **by hand** (plain dicts, no `a2ui-agent-sdk` pipeline), and how to transport them. `a2ui-core` is referenced only for schema validation, not as a message-construction framework.

## Constructing Messages

Plain dicts matching the v0.9.1 envelope — see `references/message-structures.md` for the full field reference:

```python
from __future__ import annotations

A2UI_VERSION = "v0.9.1"  # keep this in sync with whatever schema version you validate against


def build_create_surface(surface_id: str, catalog_id: str, *, theme: dict | None = None) -> dict:
    return {
        "version": A2UI_VERSION,
        "createSurface": {
            "surfaceId": surface_id,
            "catalogId": catalog_id,
            "theme": theme,
            "sendDataModel": True,
        },
    }


def build_update_components(surface_id: str, components: list[dict]) -> dict:
    return {
        "version": A2UI_VERSION,
        "updateComponents": {
            "surfaceId": surface_id,
            "components": components,
        },
    }


def build_update_data_model(surface_id: str, path: str, value: object) -> dict:
    return {
        "version": A2UI_VERSION,
        "updateDataModel": {
            "surfaceId": surface_id,
            "path": path,
            "value": value,
        },
    }


def build_delete_surface(surface_id: str) -> dict:
    return {"version": A2UI_VERSION, "deleteSurface": {"surfaceId": surface_id}}
```

Example usage — a simple profile card surface:

```python
surface_id = "user_profile_card"
messages = [
    build_create_surface(
        surface_id,
        catalog_id="https://a2ui.org/specification/v0_9_1/catalogs/basic/catalog.json",
    ),
    build_update_components(
        surface_id,
        components=[
            {"id": "root", "component": "Column", "children": ["user_name", "user_title"]},
            {"id": "user_name", "component": "Text", "text": {"path": "/user/name"}},
            {"id": "user_title", "component": "Text", "text": {"literalString": "Software Engineer"}},
        ],
    ),
    build_update_data_model(surface_id, path="/user/name", value="Alice"),
]
```

## Validating Before You Send

Don't trust a hand-built dict blindly — validate it against the official JSON Schema before emitting it. Fetch (and vendor, so you're not hitting the network per-request) the schema files from the canonical spec directory:

```python
import json
import jsonschema

# Vendor these once from github.com/a2ui-project/a2ui/specification/v0_9_1/json/
# rather than fetching them at request time.
with open("vendor/a2ui/v0_9_1/message_schema.json") as f:
    MESSAGE_SCHEMA = json.load(f)


def validate_message(message: dict) -> None:
    jsonschema.validate(instance=message, schema=MESSAGE_SCHEMA)
```

`a2ui-core` (PyPI) bundles equivalent pydantic models and schema data built on the same `jsonschema`/`pydantic`/`referencing` stack — reach for it if you'd rather not vendor the schema file yourself, but treat it as *"the schema, conveniently packaged,"* not as a message-building framework. Verify its exact model names against your installed version before relying on them; this guide intentionally doesn't assume a specific import path since that surface is smaller and changes faster than the wire format itself.

## Transport

A2UI is transport-agnostic by design — the spec documents A2A, AG-UI, MCP, WebSockets, and REST as valid carriers. The standalone case (no other protocol involved) is below; for combining this with an AG-UI event stream instead, see `references/agui-relationship.md` — that's the one place this skill covers that combination, so it isn't repeated here.

### Direct SSE

```python
import json
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()


async def a2ui_event_generator(surface_id: str):
    for message in messages:  # from "Constructing Messages" above
        validate_message(message)
        yield f"data: {json.dumps(message)}\n\n"


@app.post("/api/a2ui/stream")
async def stream_a2ui(surface_id: str) -> StreamingResponse:
    return StreamingResponse(a2ui_event_generator(surface_id), media_type="text/event-stream")
```

## Reading Bidirectional Writes Back

Since `TextField`/`CheckBox`/`ChoicePicker` write to the client's local data model without a mandated round-trip message (see `frontend-guide.md`), your agent needs its own mechanism to learn about those writes — a follow-up tool call, a webhook, or whatever state-reporting channel your transport already provides. A2UI itself only defines the UI/data-model format, not how an agent observes client-side state changes.
