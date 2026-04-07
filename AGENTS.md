# AGENTS.md — vibe-state-cli

## Project

- 變數/函式：snake_case，類別：PascalCase，常數：UPPER_SNAKE_CASE
- Conventional Commits。每次 commit 僅限單一邏輯變更。
- 禁止硬編碼密鑰。使用 .env 管理。

## Security

- Never hardcode secrets, tokens, or passwords
- Use .env files for environment variables

## Session Start — READ THESE FILES

At the beginning of every session, read these files for project context:

- `.vibe/state/current.md` — latest progress and sync history
- `.vibe/state/tasks.md` — active task checklist
- `.vibe/VIBE.md` — project constitution and workflow SOP

## Boundaries

- Do NOT modify `.vibe/config.toml` or `.vibe/state/.lifecycle` directly
- Do NOT run destructive commands without human confirmation

<!-- vibe-state-cli:integrity:ca8e0e99326a -->
