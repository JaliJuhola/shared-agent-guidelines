# Error format

```json
{ "error": { "code": "ORDER_NOT_FOUND", "message": "Order 123 not found", "details": {} } }
```

- `code`: SCREAMING_SNAKE_CASE, stable, documented in the OpenAPI spec.
- `message`: human readable, no stack traces or internal ids.
- `details`: optional; for validation errors, `{ "fields": { "<path>": "<reason>" } }`.
