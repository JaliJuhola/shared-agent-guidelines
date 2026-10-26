---
name: zod-schemas
description: Where Zod schemas live, how they are named, and how types are derived from them. Use when adding validation, parsing input, or defining request/response/message types.
metadata:
  area: zod
  applies_to: "**/*.schema.ts, src/schemas/**, src/api/**"
  tags: "validation, schema, types, boundary, parsing"
---
<!-- EXAMPLE CONTENT: replace with your team's actual conventions -->
# Zod schemas

## Rules
- Schemas live in `src/schemas/<domain>.schema.ts`, named `<Entity>Schema`.
- Derive types: `export type Order = z.infer<typeof OrderSchema>`. Never hand-write a type a schema defines.
- Parse only at boundaries (HTTP input, queue messages, env, third-party responses). Inside the domain, trust the types.
- Handlers use `.safeParse` and map failures with `toValidationError()`; `.parse` only in startup code (env).
- Separate request and response schemas: `CreateOrderRequestSchema`, `OrderResponseSchema`.

## Pitfalls
- `z.number()` accepts floats: money is integer cents with `.int()`.

More examples: [references/examples.md](references/examples.md)
