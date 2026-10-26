---
name: my-skill-name          # lowercase, digits, hyphens; MUST equal the directory name
description: What this covers and WHEN to use it. Agents decide whether to load the skill from this line alone (max 1024 chars).
metadata:
  area: typescript           # groups skills; becomes an enum value in get_guidelines
  applies_to: "src/**/*.ts"  # comma-separated globs for get_guidelines_for_files ("" = none)
  tags: "optional, search, words"
---
# Title

## Rules
- Short, imperative, checkable. One rule per bullet.

## Do
```ts
// smallest example showing the pattern
```

## Don't
```ts
// the mistake people (and models) actually make
```

## Pitfalls
- Non-obvious failure modes and what happens if ignored.

## Reference implementation
- repo-name: path/to/canonical/file.ts

Longer material goes in `references/*.md` and is linked from here, e.g. [references/examples.md](references/examples.md).
