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

## Quick start (2 minutes)

### 1. Install (one time, global, never again)

Open any terminal and run:

```bash
pip install pipx
pipx ensurepath
pipx install vibe-state-cli
```

Then **close the terminal and reopen it**.

> **What is pipx?** It's like `pip install` but for CLI tools. It puts `vibe` in an isolated environment so it never conflicts with your project's packages. You only need to do this once — `vibe` will be available everywhere on your computer.
>
> **Important:** After `pipx ensurepath`, you must restart **all open terminals and your IDE**. The new PATH only takes effect in freshly opened windows.

### 2. Initialize your project (one time per project)

```bash
cd your-project
vibe init --lang zh-TW       # or: vibe init (for English)
```

This scans your project, creates `.vibe/`, and generates config files for your AI tools. If you already have CLAUDE.md or .cursorrules, vibe imports your rules and archives the originals safely.

**This is the only time you need to type in a terminal.**

### 3. Daily use — just talk to your AI

From now on, everything happens through your AI chat. No terminal needed.

| What you want | Say this to your AI |
| ------------- | ------------------- |
| Start your day | "vibe start" |
| Save progress | "vibe sync" |
| Check status | "vibe status" |

Your AI reads the config file that vibe generated, sees these are terminal commands, and runs them for you.

> **What if it says "command not found"?** Don't worry. The AI will fall back to reading your `.vibe/state/` files directly — it still gets all your context. This is by design.

## How it works under the hood

Every AI tool has a config file it reads automatically — CLAUDE.md for Claude, `.cursor/rules/*.mdc` for Cursor, GEMINI.md for Gemini, and so on.

When you say "vibe sync", the tool:

1. Pulls your latest git commits
2. Compresses them into a 5-line summary
3. Writes that summary into **every** AI tool's config file

Next time any AI starts, it loads its own config and sees your latest progress. No magic, no plugins, no API calls.

**Git is the only reliable record.** AI sometimes forgets to update tasks.md — that's OK. `vibe sync` captures git log, which never lies.

## AutoResearch — the experiment loop

vibe pairs naturally with [autoresearch](https://github.com/uditgoenka/autoresearch), an autonomous optimization framework.

vibe is the **memory layer**. autoresearch is the **evolution layer**. Together:

```text
/autoresearch:plan  → define what to optimize (coverage, speed, score)
/autoresearch       → AI runs experiments automatically
vibe sync           → captures which experiments worked
vibe start          → next session, AI learns from past experiments
```

## Supported tools

| Tool | What the AI sees |
| ---- | ---------------- |
| Claude Code | Full state + 5 slash commands (`/vibe-start`, etc.) |
| Cursor | Standards + state summary (inline in rules file) |
| Windsurf | Standards + state summary (inline) |
| Cline | Standards + state summary (inline) |
| Roo Code | Standards + state summary (inline) |
| Antigravity/Gemini | Full state (with fallback for older versions) |
| GitHub Copilot | Summary only (Copilot can't browse project files) |

## What it does NOT do

- **No API calls.** Runs 100% offline. No telemetry, no network.
- **No git writes.** Only reads git status — never commits or pushes.
- **No lock-in.** `.vibe/` is plain Markdown. Delete it anytime.
- **No workflow changes.** You still talk to AI the same way. vibe just makes sure it remembers.

## Updating

```bash
pipx upgrade vibe-state-cli
```

## Safety

- Adapter removal is **dry-run by default** — nothing deleted without `--confirm`
- Migration is **two-phase**: copy all → verify → then delete originals
- File writes are **atomic** with retry for antivirus locks (Windows)
- Symlink and NTFS Junction traversal **blocked**
- Corrupt config **halts with error** — no silent defaults
- Checkpoint honestly marked as **best-effort (~40-60%)**

## License

MIT
