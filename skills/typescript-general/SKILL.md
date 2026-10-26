---
name: typescript-general
description: Baseline TypeScript rules for all .ts/.tsx code - typing, errors, exports and imports. Use whenever writing or changing TypeScript.
metadata:
  area: typescript
  applies_to: "**/*.ts, **/*.tsx"
  tags: "types, errors, imports, exports"
---
<!-- EXAMPLE CONTENT: replace with your team's actual conventions -->
# TypeScript general

## Rules
- No `any`. Use `unknown` and narrow, or parse with a Zod schema at boundaries (see `zod-schemas`).
- Prefer `type` aliases; use `interface` only when declaration merging is needed.
- Named exports only; no default exports.
- Throw subclasses of `AppError` from `@team/errors`, never strings or plain `Error`.
- Use `import type` for type-only imports.

## Do
```ts
export type OrderId = string & { readonly __brand: "OrderId" };
export function parseOrderId(raw: unknown): OrderId { /* validate */ }
```

## Don't
```ts
export default function handler(event: any) { throw "bad input"; }
```

## Pitfalls
- Default exports break barrel re-exports and auto-import naming.
