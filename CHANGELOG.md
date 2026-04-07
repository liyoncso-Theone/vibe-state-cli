# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.1.0] — 2026-04-07

### Added
- **5 CLI commands**: `init`, `start`, `sync`, `status`, `adapt`
- **8 built-in adapters**: AGENTS.md, Claude Code, Antigravity/Gemini, Cursor, Copilot, Windsurf, Cline, Roo Code
- **Strict lifecycle state machine**: UNINIT → READY → ACTIVE → CLOSED, with `init --force` for recovery
- **Autoresearch integration**: auto-detect experiment commits in git log, record to `state/experiments.md`
- **i18n**: English and Traditional Chinese (zh-TW) templates
- **Safety mechanisms**:
  - Atomic file writes (temp + os.replace)
  - File locking for concurrent access
  - Path traversal prevention
  - Adapter snapshot + backup (3 copies) + dry-run default for --remove
  - Input sanitization (_sanitize: strips \n, #, ", ', `)
  - Frontmatter validation per adapter
  - Config field validation (Pydantic, ge/le constraints)
  - UTF-8 error graceful handling
- **Token efficiency**:
  - Slim mode for adapters when AGENTS.md co-enabled (avoids duplication)
  - Smart dedup for security rules (skip if standards already include them)
  - Compaction: archive [x] tasks, shelve [~] stale tasks, trim current.md >300 lines, cap archive.md at 500 lines
  - Skip empty sync blocks (0 commits + 0 diff)
- **VIBE.md Constitution**:
  - Checkpoint Rule with task completion definition
  - Reality-First Principle with force-push caveat
  - Empty State Handling instruction
  - Explicit Boundary framework (prohibited actions with no-exception clause)
  - Autoresearch integration section
  - Session Start directive in all adapter outputs
- **68 automated tests** + 10 scenario tests (all passing)

### Architecture Decisions
- VIBE.md is "Constitution" (behavioral rules, rarely modified), not SSOT
- `state/` directory is the true SSOT (mutable project state)
- `vibe sync` uses pure git append (no LLM dependency, vendor-neutral)
- Adapters derive from `VIBE.md + state/ + config.toml` combined
- `_build_common_body(slim=True)` eliminates cross-file token duplication
- `markdown-it-py` declared for future AST parsing (currently line-based)

### Supported Platforms
- Claude Code CLI + VS Code extension
- Google Antigravity IDE + Gemini CLI
- Cursor
- GitHub Copilot (VS Code + GitHub.com)
- Windsurf (Codeium)
- Cline
- Roo Code
- OpenAI Codex CLI (via AGENTS.md)
- Any tool that reads AGENTS.md (Zed, Warp, Aider, Devin, etc.)
