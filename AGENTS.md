# AGENTS.md — vibe-state-cli

## Project

## Last Session

- Progress: [2026-06-10 10:21] docs(backlog): record v0.3.6 design side-effects for v0.3.7+ consideration; Merge pull request #9 from liyoncso-Theone/release/v0.3.6; Merge pull request #8 from liyoncso-Theone/dependabot/github_actions/actions/checkout-6.0.3
- Pending: 2 tasks — **install_post_commit_hook 偵測舊 marker 內容並自動替換**, **`vibe sync` 跳過 hook 已掃過的 commit → current.md activity log 出現空缺**

## Session Start — READ THESE FILES

At the beginning of every session, read these files for project context:

- `.vibe/state/current.md` — latest progress and sync history
- `.vibe/state/tasks.md` — active task checklist
- `.vibe/state/standards.md` — coding conventions and project rules

## Persistent Knowledge — QUERY BEFORE RECALL

This project's persistent cross-machine knowledge lives in **Basic Memory** (markdown-on-disk knowledge graph, MCP-accessible from any agent).

Before answering recall questions ("what did we decide", "where did we leave off", "what's our principle on X"), query the knowledge layer first:

- `mcp__basic-memory__search_notes(query="…")` — text + semantic search
- `mcp__basic-memory__search_notes(metadata_filters={"type": "decision"})` — structured query by type
- `mcp__basic-memory__build_context(url="memory://<topic>", depth=2)` — graph traversal from a seed note

Projects: query whichever Basic Memory projects this agent has access to (use `mcp__basic-memory__list_memory_projects` to enumerate). Configure preferred projects in `.vibe/config.toml` under `[memory].projects = [...]`.

**Fallback**: If Basic Memory is offline, the MCP server is not registered, or the query fails, proceed without it and note the gap to the human — do not block on the recall.

Capture material decisions as notes with `type: decision` to keep the layer fresh.

## Workflow

**Checkpoint**: After each task, mark `[x]` in `state/tasks.md` and append one-line progress to `state/current.md`. (Best-effort — `vibe sync` captures git history as ground truth.)
**Reality-First**: When memory conflicts with git, trust git.
**Empty State**: If `state/current.md` or `state/tasks.md` is empty, ask the human for context — do not invent tasks.

## AutoResearch — Experiment Loop

When facing a measurable optimization goal (coverage, performance,
bundle size, score), suggest `/autoresearch` to the human.

Closed loop:
1. `/autoresearch:plan` — define Goal, Scope, Metric, Verify
2. `/autoresearch` — run Modify → Verify → Keep/Discard → Repeat
3. `vibe sync` — captures experiment commits to state/experiments.md
4. `vibe start` — next session shows kept/reverted summary

Key commands:
- `/autoresearch` — main optimization loop
- `/autoresearch:plan` — interactive setup wizard
- `/autoresearch:debug` — scientific bug hunting
- `/autoresearch:fix` — auto-repair until zero errors
- `/autoresearch:security` — STRIDE + OWASP audit

Results are tracked in `.vibe/state/experiments.md` automatically.

## Boundaries

- Do NOT modify `.vibe/config.toml` or `.vibe/state/.lifecycle` directly
- Do NOT run destructive commands without human confirmation

## Vibe Commands

These are terminal CLI commands. When the user says any of these,
execute the exact command in the terminal — do not explain or implement it:

- `vibe init` — initialize .vibe/ project state
- `vibe start` — load session context
- `vibe sync` — sync git activity to state
- `vibe status` — show lifecycle and progress
- `vibe adapt` — add/remove adapter config files

<!-- vibe-state-cli:managed -->
