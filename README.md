# agent-centralized-guidelines

PoC: shared engineering guidelines for AI agents, kept in one repo.

## What we're testing

Guidelines live here as skills (`skills/<name>/SKILL.md`) and reach agents in two ways:

- **Sync:** `sync/sync_skills.py` copies the skills into a repo before each session or task, and agents load them automatically.
- **MCP:** an MCP server serves the same files for search and lookups during a task.

The question is which works better: sync only, MCP only, or both. See [TESTING.md](TESTING.md).

## Use in a repository

1. Start the server:
   ```bash
   git clone <this repo> ~/agent-centralized-guidelines
   cd ~/agent-centralized-guidelines && docker compose up -d --build
   ```
2. Copy `examples/consumer-repo/.vscode/` into your repo:
   - `mcp.json` connects Copilot to the server.
   - `tasks.json` syncs the skills into `.github/skills` whenever the folder opens.
3. Add the entries from `examples/consumer-repo/gitignore-snippet.txt` to your `.gitignore`.

To sync manually: `SKILLS_DIR=.github/skills python3 ~/agent-centralized-guidelines/sync/sync_skills.py`

## Instruct agents

Add to `.github/copilot-instructions.md` (or `AGENTS.md`):

```markdown
Team conventions are available as skills in `.github/skills` and from the
`agent-guidelines` MCP server. They override general best practices.
- Use the matching skills when writing or reviewing code.
- If no skill covers the task, call `get_guidelines_for_files` or `search_guidelines`.
- Cite the guideline name (e.g. `zod-schemas`) when applying or reviewing a rule.
```

In multi-agent setups, sync once at the start of a run, before spawning agents. See `examples/orchestrator/run_task.py`.
