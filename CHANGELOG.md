# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.3.0] — 2026-04-08

### Added

- **Three-mode adapter output**: `full` (AGENTS.md), `slim` (Claude/Gemini with @import), `compact` (Cursor/Windsurf/Cline/Roo/Copilot — inline standards, no file-read instructions)
- **Cross-tool state sync**: `vibe sync` and `vibe start` inject compressed state summary into ALL adapter config files. Switch tools → AI sees latest progress
- **Claude Code Agent Skills**: 5 slash commands (`/vibe-init` through `/vibe-adapt`) following [Agent Skills open standard](https://agentskills.io/)
- **Vibe Commands in every adapter**: All tools instructed to execute `vibe` CLI commands in terminal
- **Symlink + NTFS Junction defense**: `_validate_filename` blocks symlink/junction traversal in state directory
- **Advisory lock**: `append_to_state_file` uses cross-platform advisory lock (fcntl/msvcrt) for CI concurrency safety
- **Windows retry**: `_atomic_write` retries on `PermissionError` (antivirus lock scenario)
- **Two-phase migration**: copy all → verify → unlink. Partial failure preserves originals
- **Zero-rules warning**: When legacy files have content but no extractable bullet rules, warn and preserve originals
- **`constants.py`**: Single source of truth for experiment patterns (eliminates lazy imports)
- **`ConfigParseError`**: Core layer raises exception, CLI layer catches and exits (library code no longer calls `SystemExit`)

### Changed

- **VIBE.md eliminated**: Workflow rules merged into AGENTS.md. One less file, one less token hop
- **Bootstrap-not-embed**: Adapter files point to `state/` instead of copying content (Tier 2 compact mode inlines top 10 standards as exception)
- **Summary is pure data**: No "read file X" hints — Tier 2 tools get everything inline, Tier 1 tools use @import
- **Checkpoint marked best-effort**: All docs and adapter output honestly state AI compliance is ~40-60%, git log is ground truth
- **Copilot marked "Summary only"**: README support table shows sync depth per tool
- **Antigravity fallback body**: GEMINI.md includes compact body for Gemini CLI < 1.20.3
- **Skip-if-unchanged**: Adapter writes compare content before writing, avoiding git noise

### Removed

- VIBE.md template, supply chain fingerprint, snapshot system, suspicious instruction detection, dead config fields (`auto_commit`, `auto_detect`, `package_managers`)

### Fixed

- Windows cp950 encoding in git_ops.py
- Heading matching in summary.py now tolerates `###` and extra whitespace
- Code fence detection supports `~~~` syntax
- Lock file race condition (no longer deleted after release)

---

## [0.2.0] — 2026-04-07

### Added

- **Smart migration**: `vibe init` detects existing CLAUDE.md, AGENTS.md, .cursorrules, .windsurfrules — imports rules into `.vibe/state/standards.md` without overwriting originals
- **User file protection**: adapters skip generating files that already belong to the user (e.g., existing CLAUDE.md)
- **Traditional Chinese documentation**: full zh-TW README and USER-GUIDE

### Fixed

- First-sync `diff_stat` now correctly diffs from root commit (was showing only uncommitted changes)
- Three defensive programming fixes from red team audit (lock safety, config halt, atomic writes)
- Correct cursor adapter output filename (`vibe-standards.mdc`, not `vibe.mdc`)
- AGENTS.md markdown formatting (proper blank lines between headings and lists)
- Standardized `pipx` across all documentation (was inconsistently using `pip`)

### Changed

- README rewritten with clear "what it does / what it tries to do / what it doesn't do" structure
- Documentation reorganized and fully synced between EN and zh-TW
- Internal docs moved to gitignored `docs/internal/`

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
