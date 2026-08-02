# A2UI Frontend (Client) Guide — Building a Native Renderer

How to consume A2UI messages and render a surface **from the wire format directly**, without adopting a ready-made renderer package (`@a2ui/react`, `@a2ui/lit`, etc.). Use `@a2ui/web_core` or `@a2ui-sdk/types` only to type-check/validate what you build here — not as the renderer itself.

## Overview

A native client needs, per surface:

1. A `components` map (`id -> component definition`), built incrementally from `updateComponents` messages
2. A `dataModel` object, built incrementally from `updateDataModel` messages
3. A way to walk the map from a root ID into an actual render tree
4. A JSON Pointer resolver to turn `{"path": "..."}` bindings into live values
5. A re-render trigger when a bound path (or an ancestor of it) changes

## Core Data Structures

```typescript
interface ComponentDef {
  id: string;
  component: string; // "Text", "Button", "Column", ...
  children?: string[];
  child?: string;
  [prop: string]: unknown; // type-specific properties
}

interface SurfaceState {
  surfaceId: string;
  catalogId: string;
  components: Map<string, ComponentDef>;
  dataModel: Record<string, unknown>;
}

function createSurfaceState(surfaceId: string, catalogId: string): SurfaceState {
  return { surfaceId, catalogId, components: new Map(), dataModel: {} };
}
```

## Handling Incoming Messages

```typescript
function applyMessage(surfaces: Map<string, SurfaceState>, msg: Record<string, any>): void {
  if (msg.createSurface) {
    const { surfaceId, catalogId } = msg.createSurface;
    surfaces.set(surfaceId, createSurfaceState(surfaceId, catalogId));
  } else if (msg.updateComponents) {
    const { surfaceId, components } = msg.updateComponents;
    const surface = surfaces.get(surfaceId);
    if (!surface) return;
    for (const comp of components) {
      surface.components.set(comp.id, comp);
    }
  } else if (msg.updateDataModel) {
    const { surfaceId, path, value } = msg.updateDataModel;
    const surface = surfaces.get(surfaceId);
    if (!surface) return;
    setAtPointer(surface.dataModel, path ?? "/", value);
  } else if (msg.deleteSurface) {
    surfaces.delete(msg.deleteSurface.surfaceId);
  }
}
```

## Algorithm: Flat List → Render Tree

Components arrive flat and reference each other by ID via `children`/`child` — there is no nested payload to walk directly. Reconstruct the tree by resolving IDs starting from an entry point.

> **Note on the root ID:** the message spec doesn't carry an explicit `"root"` field in `createSurface`/`updateComponents` for v0.9+ (v0.8's `beginRendering` did have one). In practice, examples use a component literally IDed `"root"` by convention. Confirm this with whatever agent framework is emitting your surfaces — don't assume it's guaranteed by the wire format alone.

```typescript
function buildTree(surface: SurfaceState, rootId: string = "root"): RenderNode | null {
  const def = surface.components.get(rootId);
  if (!def) return null;

  const childIds = def.children ?? (def.child ? [def.child] : []);
  return {
    id: def.id,
    component: def.component,
    props: def, // type-specific fields live directly on def
    children: childIds
      .map((childId) => buildTree(surface, childId))
      .filter((n): n is RenderNode => n !== null),
  };
}

interface RenderNode {
  id: string;
  component: string;
  props: ComponentDef;
  children: RenderNode[];
}
```

Map each `component` string to your own framework's widget (a `switch` on `node.component`, or a lookup table) — this is the one place you touch your UI framework directly; everything above is framework-agnostic.

## Resolving Data Bindings (JSON Pointer, RFC 6901)

```typescript
function resolvePointer(data: unknown, pointer: string): unknown {
  if (pointer === "" || pointer === "/") return data;
  const parts = pointer.split("/").slice(1).map((p) => p.replace(/~1/g, "/").replace(/~0/g, "~"));
  let current: any = data;
  for (const part of parts) {
    if (current == null) return undefined;
    current = current[part];
  }
  return current;
}

function setAtPointer(data: Record<string, unknown>, pointer: string, value: unknown): void {
  if (pointer === "" || pointer === "/") {
    Object.keys(data).forEach((k) => delete data[k]);
    Object.assign(data, value);
    return;
  }
  const parts = pointer.split("/").slice(1).map((p) => p.replace(/~1/g, "/").replace(/~0/g, "~"));
  let current: any = data;
  for (let i = 0; i < parts.length - 1; i++) {
    if (current[parts[i]] == null) current[parts[i]] = {};
    current = current[parts[i]];
  }
  current[parts[parts.length - 1]] = value;
}

function resolveValue(binding: { literalString?: unknown; path?: string } | undefined, dataModel: unknown): unknown {
  if (!binding) return undefined;
  if ("path" in binding && binding.path) return resolvePointer(dataModel, binding.path);
  return binding.literalString;
}
```

## Handling `updateDataModel` Deltas Reactively

A component only needs to re-render when a path it's bound to (or an ancestor of that path) changed:

```typescript
function pathAffects(changedPath: string, boundPath: string): boolean {
  return boundPath === changedPath || boundPath.startsWith(changedPath + "/") || changedPath.startsWith(boundPath + "/");
}
```

Apply this check against every bound path in your currently-rendered tree when an `updateDataModel` message arrives, and only re-render the affected components — not the whole surface.

## List Templates

`{"children": {"path": "/products", "componentId": "product-card"}}` means: for each item in the array at `/products`, render one instance of the `product-card` template, with paths inside that instance scoped to the item:

```typescript
function renderListTemplate(surface: SurfaceState, arrayPath: string, templateComponentId: string): RenderNode[] {
  const items = (resolvePointer(surface.dataModel, arrayPath) as unknown[]) ?? [];
  return items.map((_, i) => {
    const scopedRoot = buildTree(surface, templateComponentId);
    return scopeNodePaths(scopedRoot, `${arrayPath}/${i}`);
  }).filter((n): n is RenderNode => n !== null);
}
```

(`scopeNodePaths` — prefix every relative bound `path` in the subtree with the item's index path; omitted here for brevity, but it's a straightforward tree walk over the same `RenderNode` structure `buildTree` produces.)

## Bidirectional Input

`TextField`/`CheckBox`/`ChoicePicker` write to the local data model immediately on user interaction — no round trip to the agent is required by the protocol itself:

```typescript
function onTextFieldChange(surface: SurfaceState, boundPath: string, newValue: string): void {
  setAtPointer(surface.dataModel, boundPath, newValue);
  // A2UI itself doesn't define how the agent learns about this write — report it
  // over whatever transport this project already uses (see backend-guide.md).
}
```

## Validating Against the Official Types

Use `@a2ui/web_core` (runtime, via its `zod` schemas) or `@a2ui-sdk/types` (compile-time only) to confirm your hand-built `ComponentDef`/message shapes match the spec — don't adopt either package's own renderer or runtime; import only the type/schema exports.
