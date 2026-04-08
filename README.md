# vibe-state-cli

[English](README.md) | [繁體中文](docs/zh-TW/README.md)

**Your AI forgets everything the moment you close the terminal. This tool fixes that.**

## The problem

You spend two hours explaining your project architecture to Claude. You close the terminal. Tomorrow, Claude has no idea what you talked about.

You fix a bug in Cursor, then switch to Claude Code for a bigger refactor. Claude doesn't know what you just did in Cursor.

Your coding standards are scattered across CLAUDE.md, .cursorrules, and AGENTS.md — three files saying the same thing, all eating tokens.

## What vibe-state-cli does

It gives all your AI tools **one shared brain**.

A `.vibe/` directory in your project holds your progress, tasks, and standards. When you switch tools, the new AI picks up exactly where the last one left off.

```bash
vibe init      # Scan project, detect your AI tools, set up .vibe/
vibe start     # Begin session — AI sees your latest progress
vibe sync      # End session — save today's work from git
vibe status    # Check state anytime
vibe adapt     # Add or remove AI tool support
```

## How it actually works

Every AI tool has a config file it reads automatically — CLAUDE.md for Claude, `.cursor/rules/*.mdc` for Cursor, GEMINI.md for Gemini, and so on.

`vibe sync` and `vibe start` write a **compressed state summary** directly into each tool's config file. The AI reads its own config → sees your latest progress. No magic, no plugins, no API calls.

```text
You work with Claude → Claude writes checkpoints to .vibe/state/
     ↓
vibe sync → captures git log → compresses into 5-line summary → writes into all config files
     ↓
Switch to Cursor → Cursor loads its .mdc → sees what Claude did
```

**Git is the ground truth.** AI checkpoints (updating tasks.md) are best-effort — sometimes the AI forgets. But `vibe sync` pulls from git log, which never lies.

## Migrating an existing project

Already have CLAUDE.md, .cursorrules, or AGENTS.md? Just run `vibe init`.

It extracts your rules, archives the originals to `.vibe/archive/legacy/` (nothing is deleted), and generates clean new config files.

If your rules aren't in `- bullet` format, vibe warns you and **leaves your files untouched**.

## AutoResearch — the experiment loop

vibe pairs naturally with [autoresearch](https://github.com/uditgoenka/autoresearch), an autonomous optimization framework.

vibe is the **memory layer**. autoresearch is the **evolution layer**. Together they form a closed loop:

```text
/autoresearch:plan  → define what to optimize (coverage, speed, score)
/autoresearch       → AI runs experiments: modify → test → keep or revert
vibe sync           → auto-captures which experiments worked
vibe start          → next session shows "5 kept, 2 reverted"
                      → AI learns from past experiments
```

Every adapter output already tells the AI about autoresearch — when it sees a measurable goal, it knows to suggest `/autoresearch`.

## What each tool gets

| Tool | What vibe generates | What the AI sees |
| ---- | ------------------- | ---------------- |
| Claude Code | `CLAUDE.md` + rules + 5 slash commands | Full state via @import |
| Cursor | `.cursor/rules/vibe-standards.mdc` | Standards + summary inline |
| Windsurf | `.windsurf/rules/vibe-standards.md` | Standards + summary inline |
| Cline | `.clinerules/01-vibe-standards.md` | Standards + summary inline |
| Roo Code | `.roo/rules/01-vibe-standards.md` | Standards + summary inline |
| Antigravity/Gemini | `GEMINI.md` | Full (with fallback for older versions) |
| GitHub Copilot | `.github/copilot-instructions.md` | Summary only (Copilot can't read files) |
| AGENTS.md | `AGENTS.md` | Full — the cross-tool standard |

## What it does NOT do

- **Does not call any API.** Runs 100% offline. No telemetry.
- **Does not touch your git.** Only reads — never commits or pushes.
- **Does not lock you in.** `.vibe/` is plain Markdown. Delete it anytime.
- **Does not replace your workflow.** You still talk to AI the same way. vibe just makes sure it remembers.

## Install

```bash
pipx install vibe-state-cli
```

## Safety

- Adapter removal is **dry-run by default** — nothing deleted without `--confirm`
- Migration is **two-phase**: copy all → verify → then delete originals
- File writes are **atomic** with Windows retry for antivirus locks
- Symlink and NTFS Junction traversal **blocked**
- Corrupt config **halts with error** — no silent defaults
- Advisory lock for **concurrent writes** (CI environments)
- Checkpoint compliance is honestly marked as **best-effort (~40-60%)**

## License

MIT
