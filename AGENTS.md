# AGENTS.md — vibe-state-cli

## Project

## Last Session

- Progress: [2026-05-07 03:51] feat: v0.3.3 — beginner-friendly README rewrite; feat: v0.3.2 — AutoResearch closed-loop integration + human-friendly README; chore: bump to v0.3.1 (includes README English fix)
- Experiments: 1 kept, 0 reverted

## Session Start — READ THESE FILES

At the beginning of every session, read these files for project context:

- `.vibe/state/current.md` — latest progress and sync history
- `.vibe/state/tasks.md` — active task checklist
- `.vibe/state/standards.md` — coding conventions and project rules

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
