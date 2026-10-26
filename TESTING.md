# Testing: MCP vs synced skills

Goal: find out whether agents follow the guidelines better with **MCP**, with **synced skills**, or with **both**, and whether MCP earns its place.

## Modes

| Mode | Setup |
|---|---|
| **A. MCP only** | `.vscode/mcp.json` in place. Delete the synced skills from `.github/skills/` and don't run the sync task. |
| **B. Skills only** | Run the sync. In Copilot Chat's tools picker, turn `agent-guidelines` **off**. |
| **C. Both** | Sync done and MCP on. |

Rules for every run:

- **Start a new chat session.** Skills are discovered at session start, and an old session carries context from earlier runs.
- Use Copilot **Agent mode**, the same model and the same starting branch.
- Do 2–3 runs per task and mode; results vary between runs.

## Tasks and what to check

These checks match the placeholder skills. When you replace the skills with your real conventions, update the checks.

### 1. API endpoint
> Add a POST endpoint for creating orders with an amount and a customer id.

- [ ] Schema in `src/schemas/order.schema.ts`, named `CreateOrderRequestSchema` (zod-schemas)
- [ ] Type derived with `z.infer`, no hand-written interface (zod-schemas)
- [ ] Amount as integer cents with `.int()` (zod-schemas)
- [ ] `.safeParse` in the handler (zod-schemas)
- [ ] Path `/v1/orders` (api-rest-structure)
- [ ] 201 + `Location` header (api-rest-structure)
- [ ] Standard error body `{ error: { code, message, details } }` (api-rest-structure)
- [ ] Named exports only, no `any` (typescript-general)

### 2. React component
> Create an OrderList React component that shows the orders.

- [ ] Lives under `src/features/orders/components/` (react-components)
- [ ] Data via a TanStack Query hook in `features/orders/api/` (react-components)
- [ ] No `fetch` or `useEffect` for data in the component (react-components)
- [ ] Named `Props` type, no `React.FC` (react-components)
- [ ] Named export (typescript-general)

### 3. Infrastructure
> Add a Lambda that processes order events to the CDK stack.

- [ ] `NodejsFunction`, Node 22, ARM64 (aws-cdk-conventions)
- [ ] 30-day log retention, explicit timeout (aws-cdk-conventions)
- [ ] Permissions via `grantX`, no `*` policies (aws-cdk-conventions)
- [ ] Tags `service`, `env`, `owner`; no hard-coded account ids (aws-cdk-conventions)

### 4. Review
> Review this diff against our guidelines: (paste `examples/test-fixtures/review-me.diff`)

The fixture lists nine planted violations at the top. **Remove that header before pasting.**

- [ ] Number of the nine violations found
- [ ] Each finding cites a guideline name
- [ ] Uses the output format from `code-review` (severity, guideline, location, issue, fix)
- [ ] No invented "violations" of rules that don't exist

## What to record

| Task | Mode | Run | Checks passed | MCP calls (from log) | Cited guideline names? | Notes |
|---|---|---|---|---|---|---|
| 1 | A | 1 | 5/8 | 1 | partly | skipped tools on first try |
| … | | | | | | |

MCP calls per run: `docker compose logs --since 10m agent-guidelines | grep '"tool"'`. In mode B there should be none.

## How to read the results

- **B ≈ C and few MCP calls in C:** skills do the work. MCP can shrink to just serving `/export` for the sync.
- **C > B mainly on review and edge cases:** keep MCP for search and reference files.
- **A < B:** the agent skips tools or fetches the wrong area. This is expected; it's the pull-versus-push difference.
- **Many repeated MCP calls in C:** agents re-fetch what the skills already gave them. Tighten `copilot-instructions.md`.
- **Low scores in every mode:** the guidelines themselves need work. Make rules more concrete and add Do/Don't examples.
