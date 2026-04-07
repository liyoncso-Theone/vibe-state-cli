# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.1.0] — 2026-04-07

### Added

- **5 CLI commands**: `init`, `start`, `sync`, `status`, `adapt`
- **8 built-in adapters**: AGENTS.md, Claude Code, Antigravity/Gemini, Cursor, Copilot, Windsurf, Cline, Roo Code
- **Strict lifecycle state machine**: UNINIT → READY → ACTIVE → CLOSED, with `init --force` for recovery
- **Smart migration**: detects existing CLAUDE.md, AGENTS.md, .cursorrules — imports rules into .vibe/state/standards.md without overwriting originals
- **Autoresearch integration**: auto-detect experiment commits in git log, record to `state/experiments.md`, configurable patterns
- **i18n**: English and Traditional Chinese (zh-TW) templates
- **Safety mechanisms**:
  - Atomic file writes (temp + os.replace)
  - Exponential backoff file locking (fails safe, never forces entry)
  - Path traversal prevention
  - Adapter snapshot + backup (3 copies) + dry-run default for --remove
  - Input sanitization
  - Frontmatter validation per adapter
  - Config corruption halts execution (no silent defaults)
  - Supply chain fingerprint warning on cloned .vibe/
- **Token efficiency**:
  - Slim mode for adapters when AGENTS.md co-enabled
  - AST-based Markdown compaction (markdown-it-py, respects code fences)
  - Section-aware trimming (never breaks document structure)
  - Skip empty sync blocks (0 commits + 0 diff)
- **VIBE.md Constitution**:
  - Checkpoint Rule with task completion definition
  - Reality-First Principle with force-push caveat
  - Explicit Boundary framework (prohibited actions)
  - Session Start directive in all adapter outputs
- **207 automated tests**, 100% coverage

### Architecture Decisions

- VIBE.md is "Constitution" (behavioral rules, rarely modified), not SSOT
- `state/` directory is the true SSOT (mutable project state)
- `vibe sync` uses pure git append (no LLM dependency, vendor-neutral)
- Adapters derive from `VIBE.md + state/ + config.toml` combined
- CLI modularized into `commands/` subpackage (cmd_init, cmd_start, etc.)
- `markdown-it-py` AST used for section-boundary-aware compaction

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
