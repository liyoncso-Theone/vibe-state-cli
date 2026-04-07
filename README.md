# vibe-state-cli

[English](README.md) | [繁體中文](docs/zh-TW/README.md)

**Stop losing your AI's memory every time you close the terminal.**

## What vibe-state-cli does

It creates a `.vibe/` directory in your project that acts as a **shared brain** between you and any AI coding tool. When you switch from Claude Code to Cursor to Copilot, they all read from the same state — your progress, your tasks, your architecture decisions, your coding standards.

Five commands. That's it:

```bash
vibe init      # Scan your project, set up .vibe/, detect your AI tools
vibe start     # Load yesterday's context, check git, show what to work on
vibe sync      # Save today's progress from git, review with C.L.E.A.R. checklist
vibe status    # Quick look at project state (works anytime)
vibe adapt     # Add or remove AI tool adapters
```

## What vibe-state-cli is trying to solve

AI coding assistants are powerful but forgetful. Every session starts from zero. You waste time re-explaining your project, your conventions, your progress. And if you use more than one tool, each one lives in its own silo — Claude doesn't know what you did in Cursor, Copilot doesn't know what you told Gemini.

vibe-state-cli fixes this by giving every AI tool a single source of truth to read from.

It also prevents your AI context from growing out of control. As `current.md` and `tasks.md` accumulate history, the built-in compactor uses **Markdown AST parsing** to safely remove old sections without ever breaking code blocks or document structure.

## What vibe-state-cli does NOT do

- **Does not replace your existing setup.** If you already have a `CLAUDE.md`, `.cursorrules`, or `AGENTS.md`, vibe imports your rules and leaves your files alone. It's additive, not destructive.
- **Does not require an API key.** Everything runs 100% offline. No telemetry, no network calls.
- **Does not lock you in.** The `.vibe/` directory is plain Markdown files. You can read, edit, or delete them anytime. No proprietary format.
- **Does not change how you work with AI.** You still talk to Claude, Cursor, Copilot the same way. vibe just makes sure they all start each session with the right context.
- **Does not auto-commit or push code.** It only reads git status. Your repository is yours.

## Install

```bash
pipx install vibe-state-cli
```

> Why `pipx`? Because this is a CLI tool, not a library. `pipx` installs it in an isolated environment so it never conflicts with your project dependencies.

## Smart Migration

Already have AI config files? vibe detects them automatically:

```text
$ vibe init
Scanning project...

Found 2 existing config file(s):
  - CLAUDE.md
  - .cursorrules
Imported 9 rules into .vibe/state/standards.md

The following legacy config files have been imported into .vibe/
and are no longer needed:
  - CLAUDE.md
  - .cursorrules
```

Your rules are preserved. Your files are not overwritten. You decide when to clean up.

## Supported AI Tools

| Tool | What vibe generates | How it's detected |
| ---- | ------------------- | ------------------- |
| Claude Code | `.claude/rules/vibe-standards.md` | `.claude/` directory |
| Cursor | `.cursor/rules/vibe-standards.mdc` | `.cursor/` directory |
| GitHub Copilot | `.github/copilot-instructions.md` | existing copilot config |
| Windsurf | `.windsurf/rules/vibe-standards.md` | `.windsurf/` directory |
| Cline | `.clinerules/01-vibe-standards.md` | `.clinerules/` directory |
| Roo Code | `.roo/rules/01-vibe-standards.md` | `.roo/` directory |
| Antigravity / Gemini | `GEMINI.md` | `GEMINI.md` or `.gemini/` |
| AGENTS.md (universal) | `AGENTS.md` | always generated |

Only detected tools get adapter files. When multiple adapters are active, duplicate content is automatically eliminated to save tokens.

## Autoresearch Integration

Works with [autoresearch](https://github.com/uditgoenka/autoresearch) experiment loops. `vibe sync` detects experiment commits in your git history and records which ones were kept vs reverted in `state/experiments.md`. Patterns are configurable in `.vibe/config.toml`.

## Safety

- Adapter removal defaults to **dry-run** — nothing gets deleted until you confirm
- Every generated file gets a snapshot; vibe warns you before overwriting your manual edits
- Backups are kept (last 3) before any deletion
- Corrupt config halts execution instead of silently using defaults
- File writes are atomic (temp + rename) with exponential backoff locking

## License

MIT
