# vibe-state-cli

[English](README.md) | [繁體中文](docs/zh-TW/README.md)

**Model-agnostic AI-human collaboration state management CLI.**

Let any AI model — Claude, GPT, Gemini, or local models — instantly sync with your project's context by reading a single `.vibe/` directory.

## Why vibe?

| Problem | How vibe solves it |
|---------|-------------------|
| AI loses memory every session | `.vibe/state/` persists across sessions and tools |
| Switching AI tools = starting over | 8 adapters generate each tool's native config from one source |
| CLAUDE.md grows forever, wastes tokens | `vibe sync --compact` auto-archives, keeps state lean (~684 tokens) |
| Manual copy-paste of context prompts | `vibe init` scans your project and generates everything |
| No structured handoff between sessions | `vibe sync` appends git state + C.L.E.A.R. review checklist |

Works **100% offline**. No API keys, no telemetry, no network calls.

## Install

```bash
pipx install vibe-state-cli
```

## Quick Start

```bash
cd my-project

vibe init                # Initialize .vibe/ (auto-detects language, framework, AI tools)
vibe start               # Daily start — load state, git check, auto-compact
vibe sync                # Daily close — append git status, C.L.E.A.R. review
vibe sync --compact      # Archive completed tasks, compress state files
vibe sync --close        # End project — final sync + retrospective
vibe status              # Check project state (anytime)
vibe adapt --list        # See which AI tool adapters are enabled
```

## 5 Commands

| Command | When | What it does |
|---------|------|-------------|
| `vibe init` | Once | Scan project, generate `.vibe/`, detect AI tools, emit adapter files |
| `vibe start` | Daily | Load state, validate vs git, auto-compact if needed, Rich summary |
| `vibe sync` | Daily | Append git status to state, C.L.E.A.R. checklist |
| `vibe status` | Anytime | Show lifecycle, tasks, file sizes |
| `vibe adapt` | As needed | `--add`/`--remove`/`--list`/`--sync` adapter files |

### Flags

- `vibe init --lang zh-TW` — Traditional Chinese templates
- `vibe init --force` — Reinitialize or reopen a closed project
- `vibe sync --compact` — Run memory compaction after sync
- `vibe sync --close` — Close project with retrospective
- `vibe adapt --remove cursor --dry-run` — Preview before deleting
- `vibe adapt --remove cursor --confirm` — Delete with backup

## Supported AI Tools

| Tool | Generated Config | Auto-detected by |
|------|-----------------|------------------|
| AGENTS.md | `AGENTS.md` | `AGENTS.md` exists |
| Claude Code | `CLAUDE.md` + `.claude/rules/` | `.claude/` directory |
| Cursor | `.cursor/rules/*.mdc` | `.cursor/` directory |
| GitHub Copilot | `.github/copilot-instructions.md` | existing copilot config |
| Windsurf | `.windsurf/rules/*.md` | `.windsurf/` directory |
| Cline | `.clinerules/*.md` | `.clinerules/` directory |
| Roo Code | `.roo/rules/*.md` | `.roo/` directory |

Only detected tools get adapter files generated. No bloat.

## Safety

- `vibe adapt --remove` defaults to **dry-run** — requires `--confirm` to delete
- Snapshots saved on every emit for diff detection
- Backups kept (last 3) before any deletion
- User-modified files trigger warnings before overwrite

## License

MIT
