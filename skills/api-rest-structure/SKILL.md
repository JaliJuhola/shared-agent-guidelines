---
name: api-rest-structure
description: REST endpoint design - URLs, status codes, error format and pagination. Use when adding or changing HTTP endpoints or OpenAPI specs.
metadata:
  area: api
  applies_to: "src/api/**, src/routes/**, **/openapi.yaml"
  tags: "rest, http, endpoints, errors, pagination"
---
<!-- EXAMPLE CONTENT: replace with your team's actual conventions -->
# REST API structure

## Rules
- Plural kebab-case nouns, version in path: `/v1/order-items/{id}`.
- One error shape everywhere: see [references/error-format.md](references/error-format.md).
- Cursor pagination: `?limit=&cursor=`; responses include `nextCursor` (null at end).
- 201 + `Location` on create, 204 on delete, 422 for valid JSON that breaks business rules.
- Every handler validates input with a Zod schema (`zod-schemas`).
