# vibe-state-cli

[English](README.md) | [繁體中文](docs/zh-TW/README.md)

**Your AI forgets everything the moment you close the terminal. This tool fixes that.**

## What it does

Creates a `.vibe/` directory in your project that acts as a **shared brain** across all your AI coding tools. What you did in Claude Code, Cursor or Gemini picks up seamlessly.

Five commands:

```bash
vibe init      # Scan project, create .vibe/, detect your AI tools
vibe start     # Begin session: load state, refresh config files, AI sees latest progress
vibe sync      # End session: capture git changes, update all AI config files
vibe status    # Check project state anytime
vibe adapt     # Add or remove AI tool adapters
```

## Why you need it

- AI **forgets** every session. You spent two hours explaining your architecture yesterday — today you start over.
- You use multiple tools but they **don't talk to each other**. Claude doesn't know what you did in Cursor.
- Each tool has a different config format (CLAUDE.md, .cursorrules, GEMINI.md). Your rules are **scattered, duplicated, eating tokens**.

vibe-state-cli unifies memory into `.vibe/state/`, rules into `AGENTS.md`, then auto-generates each tool's native config file.

## What it does NOT do

- **Does not replace your existing setup.** Got a CLAUDE.md? vibe imports your rules and archives the original to `.vibe/archive/legacy/`.
- **Does not require an API key.** Runs 100% offline. No telemetry.
- **Does not lock you in.** `.vibe/` is plain Markdown. Read, edit, or delete anytime.
- **Does not touch your git.** Only reads git status — never commits or pushes.

## Install

```bash
pipx install vibe-state-cli
```

## Migrating existing projects

Already have AI config files? `vibe init` handles it:

1. Detects your CLAUDE.md, .cursorrules, AGENTS.md, etc.
2. Extracts rules into `.vibe/state/standards.md`
3. Archives originals to `.vibe/archive/legacy/` (not deleted — fully traceable)
4. Generates fresh, standardized config files

If your rules aren't in `- bullet` format, vibe warns you and **preserves originals untouched** for manual migration.

## How cross-tool sync works

```text
Work with Claude → checkpoint writes to .vibe/state/
     ↓
vibe sync → captures git log + compresses summary → injects into all config files
     ↓
Switch to Gemini/Cursor → auto-loads config → sees Claude's progress
```

Core mechanism: `vibe sync` and `vibe start` write a **compressed state summary** into every tool's config file. Each tool auto-loads its own config — no extra steps.

**Git is the only reliable record.** AI checkpoints (updating tasks.md) are best-effort with ~40-60% compliance. `vibe sync` captures git log deterministically.

## Supported tools

| Tool | What vibe generates | Sync depth |
| ---- | ------------------- | ---------- |
| Claude Code | `CLAUDE.md` + `.claude/rules/` + 5 slash commands | **Full** |
| Cursor | `.cursor/rules/vibe-standards.mdc` (inline rules) | **Full** (compact) |
| Windsurf | `.windsurf/rules/vibe-standards.md` | **Full** (compact) |
| Cline | `.clinerules/01-vibe-standards.md` | **Full** (compact) |
| Roo Code | `.roo/rules/01-vibe-standards.md` | **Full** (compact) |
| Antigravity/Gemini | `GEMINI.md` (with fallback body) | **Full** |
| GitHub Copilot | `.github/copilot-instructions.md` | **Summary only** |
| AGENTS.md | `AGENTS.md` (cross-tool standard) | Varies by tool |

**Sync depth**:

- **Full**: Tool receives rules + state summary. Some can read full `.vibe/state/` files.
- **Compact**: Rules and standards inlined directly in config (no dependency on AI reading other files).
- **Summary only**: Receives compressed 5-line digest only (Copilot limitation, not vibe's).

## Safety

- Adapter removal defaults to **dry-run** — requires `--confirm` to execute
- Migration is **two-phase**: copy all → verify → then delete originals
- File writes are atomic (temp + rename) with Windows retry for antivirus locks
- Symlink and NTFS Junction traversal blocked
- Corrupt config.toml halts with error — no silent defaults
- Advisory lock protects concurrent writes (CI environments)

## License

MIT
