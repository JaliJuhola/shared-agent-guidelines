---
name: react-components
description: React component structure, data fetching and styling rules for the frontends. Use when creating or changing React components, hooks or feature folders.
metadata:
  area: react
  applies_to: "**/*.tsx, src/components/**"
  tags: "frontend, components, hooks, data-fetching"
---
<!-- EXAMPLE CONTENT: replace with your team's actual conventions -->
# React components

## Rules
- Feature folders: `src/features/<feature>/{components,hooks,api}`; shared UI only in `src/components/ui`.
- Data fetching only via TanStack Query hooks in `features/<feature>/api`; never `fetch` inside components.
- Function components with a named `Props` type; no `React.FC`.
- Use `@team/ui` design-system components before writing custom ones.

## Pitfalls
- Fetching in `useEffect` bypasses the query cache and error boundary (caused duplicate requests before).
