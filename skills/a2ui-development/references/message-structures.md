# A2UI Message Structures Reference (v0.9.1)

Full JSON shapes for every A2UI message, the component model, and the data-binding syntax. All examples are v0.9.1 unless marked otherwise.

## Envelope

Every message shares this envelope shape — a `version` string plus exactly one message key:

```json
{
  "version": "v0.9.1",
  "createSurface": { }
}
```

---

## createSurface

Initializes a new UI surface.

```json
{
  "version": "v0.9.1",
  "createSurface": {
    "surfaceId": "user_profile_card",
    "catalogId": "https://a2ui.org/specification/v0_9_1/catalogs/basic/catalog.json",
    "theme": { "primaryColor": "#00BFFF" },
    "sendDataModel": true
  }
}
```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `surfaceId` | `string` | Yes | Unique identifier for this UI surface |
| `catalogId` | `string` | Yes | URL of the component catalog this surface's components come from |
| `theme` | `object?` | No | Renderer-specific theme hints |
| `sendDataModel` | `boolean?` | No | If true, client should expect a full data model on next `updateDataModel` |

## updateComponents

Adds or modifies component definitions on a surface — the components themselves are transmitted as a **flat list**, not a nested tree.

```json
{
  "version": "v0.9.1",
  "updateComponents": {
    "surfaceId": "user_profile_card",
    "components": [
      { "id": "root", "component": "Column", "children": ["user_name", "user_title"] },
      { "id": "user_name", "component": "Text", "text": { "path": "/user/name" } },
      { "id": "user_title", "component": "Text", "text": { "literalString": "Software Engineer" } }
    ]
  }
}
```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `surfaceId` | `string` | Yes | Surface these components belong to |
| `components` | `array` | Yes | Flat list of component objects (see below) |

### Component object shape

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | Yes | Unique ID within the surface — the adjacency-list key |
| `component` | `string` | Yes | Component type name from the catalog (e.g. `"Text"`, `"Button"`) |
| `children` / `child` | `string[]` / `string` | No | ID references to child components — this is how the tree is expressed, not nesting |
| *(type-specific)* | varies | No | Remaining properties depend on `component` — see the Basic catalog below |

> **Parent-child relationships are ID references, not nesting.** A client must build a `Map<id, component>` and resolve `children` recursively starting from a designated root ID — see `frontend-guide.md` for the algorithm.

## updateDataModel

Inserts or replaces values in the surface's data model. Bound components re-render automatically when their `path` changes.

```json
{
  "version": "v0.9.1",
  "updateDataModel": {
    "surfaceId": "user_profile_card",
    "path": "/user/name",
    "value": "Alice"
  }
}
```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `surfaceId` | `string` | Yes | Surface whose data model is being updated |
| `path` | `string?` | No — defaults to `/` (replace whole model) | RFC 6901 JSON Pointer to the value being set |
| `value` | `any?` | No | New value at `path` |

## deleteSurface

```json
{
  "version": "v0.9.1",
  "deleteSurface": { "surfaceId": "user_profile_card" }
}
```

---

## Basic Component Catalog

The catalog referenced by `catalogId` in `createSurface`. This is the "Basic" catalog — the standard starting set:

| Component | Purpose |
| --- | --- |
| `Text` | Display text, supports Markdown |
| `Image` | Render an image from a URL |
| `Icon` | System-provided icon |
| `Row` | Horizontal layout container |
| `Column` | Vertical layout container |
| `Button` | Clickable action trigger |
| `TextField` | User text input (bidirectional) |
| `CheckBox` | Boolean toggle with label (bidirectional) |
| `ChoicePicker` | Single/multiple option selection (bidirectional) |
| `Card` | Card-styled container |
| `List` | Scrollable list of components |
| `Divider` | Visual separator |
| `Modal` | Overlay dialog |
| `Tabs` | Tabbed interface |

A client declares which catalogs it can render via a `supportedCatalogIds` array at the transport level (not an A2UI message).

---

## Data Binding

A2UI separates **UI structure** (components) from **application state** (a JSON data model). Components reference the data model via **JSON Pointer paths (RFC 6901)** — never inline computed values.

### Value types

```json
{ "text": { "literalString": "Welcome" } }
```

```json
{ "text": { "path": "/user/name" } }
```

| Value type | Behavior |
| --- | --- |
| `literalString` (and `literalNumber`/`literalBoolean`) | Fixed value, never changes |
| `path` | Reactive — re-renders when the data model at that path changes |

### List templates

Arrays render multiple component instances from one template, with paths scoped relative to each item:

```json
{ "children": { "path": "/products", "componentId": "product-card" } }
```

Inside the `product-card` template, a bound path like `/name` resolves per-item: `/products/0/name`, `/products/1/name`, etc.

### Bidirectional input

`TextField`, `CheckBox`, and `ChoicePicker` write back to the data model on user interaction — e.g. typing "Alice" into a `TextField` bound to `/form/name` sets `/form/name` to `"Alice"` client-side, with no message back to the agent required unless the agent needs to observe it (see `backend-guide.md` for how an agent reads state back).

---

## Gotchas: Version Differences

**v0.8 used a materially different envelope** — no top-level `version` field, and different message names entirely:

```json
{
  "surfaceId": "user_profile_card",
  "root": "root",
  "catalogId": "https://a2ui.org/specification/v0_8/catalogs/basic/catalog.json"
}
```

v0.8's `beginRendering` (not `createSurface`), `surfaceUpdate` (not `updateComponents`), and `dataModelUpdate` (not `updateDataModel`) also nest component data differently — e.g. v0.8's `surfaceUpdate.components[].component` is `{"<ComponentType>": {props}}` (type name as a wrapper key) instead of v0.9+'s flat `"component": "<ComponentType>"` string field. **Mixing v0.8 examples found online with v0.9+ code will silently produce malformed messages** — always check which version a code sample targets before copying it.

**a2ui.org vs the GitHub repo can disagree on "current" version.** As of this writing, a2ui.org calls v0.9.1 "current production" and v1.0 "candidate", but the GitHub repo's `specification/v1_0/` directory (with its own migration `evolution_guide.md`) suggests v1.0 is further along in-repo. Check both before pinning a version in a real project.
