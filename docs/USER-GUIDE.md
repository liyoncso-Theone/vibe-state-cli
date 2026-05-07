# vibe-state-cli User Guide

> Complete reference from install to daily use, covering every command flag.
>
> [繁體中文版](zh-TW/USER-GUIDE.md) | [README](../README.md)

---

## Install

```bash
pip install pipx
pipx ensurepath
pipx install vibe-state-cli
```

> After install, **close and reopen your terminal** so the new PATH takes effect.
> `pipx` puts `vibe` in an isolated environment so it never conflicts with project packages.

Verify:

```bash
vibe --version       # or vibe -V
```

---

## Quick start (3 minutes)

```bash
cd my-project
vibe init              # Initialize .vibe/ (auto-detects language, framework, AI tools, installs git hook)
vibe start             # Start session (loads state, auto-syncs new commits, shows summary)
# ... work ...
vibe sync              # End session (appends git activity, runs C.L.E.A.R. checklist)
```

That's it. Three commands cover 90% of usage.

---

## Five commands in detail

### 1. `vibe init`

**What it does**: scans your project, generates `.vibe/`, creates AI tool config files, and installs a git post-commit hook (auto-syncs after every commit).

```bash
vibe init                      # Default English template (or read existing config when --force)
vibe init --lang zh-TW         # Traditional Chinese template
vibe init --force              # Force reinitialize (also reopens closed projects)
vibe init --no-hooks           # Skip git post-commit hook installation
```

**Auto-detects**:

- Language/framework: reads `pyproject.toml`, `package.json`, `Cargo.toml`, etc.
- AI tools: scans `.claude/`, `.cursor/`, `.windsurf/`, etc.
- Git: detects `.git/` (skips hook install if absent)

**`--force` behavior** (fixed in v0.3.4):
- Backs up the existing `.vibe/` to a timestamped directory
- When `--lang` is not specified, **preserves** the existing config's lang (no longer silently reverts to en)
- If the git hook is already installed, skips re-install (idempotent)

**Generated files**:

```text
.vibe/
├── config.toml          # Settings (adapter on/off, compact threshold, lang)
└── state/
    ├── current.md       # Latest progress
    ├── tasks.md         # Task checklist
    ├── architecture.md  # Tech stack
    ├── standards.md     # Coding rules
    ├── experiments.md   # Autoresearch experiment log
    └── archive.md       # Cold storage
```

### 2. `vibe start`

**What it does**: run at the start of each session. **As of v0.3.4, automatically syncs commits behind the cursor** (no need to remember `vibe sync`), loads state, auto-compacts oversized files, prints a summary panel.

```bash
vibe start
```

**Sample output**:

```text
Auto-synced: 5 new commits since last session

┌────────────── vibe start ──────────────┐
│  Progress      [2026-05-07] feat: ...   │
│  Git           3 uncommitted changes    │
│  Open issues   (none)                   │
│  Top tasks                              │
│                  1. Build auth module   │
│                  2. Write tests         │
│  Experiments   5 kept, 2 reverted       │
└──────────────── Session loaded ─────────┘
```

### 3. `vibe sync`

**What it does**: appends git activity to `state/current.md`, advances the sync cursor, detects autoresearch experiment commits, prints the C.L.E.A.R. review checklist.

```bash
vibe sync                              # Daily sync
vibe sync --note "three-tier adapter refactor — token efficiency"   # Add semantic note
vibe sync --compact                    # Sync + compact (archive completed tasks)
vibe sync --close                      # Close project (final sync + compact + retrospective)
vibe sync --no-refresh                 # Skip adapter regeneration (used by git hook)
```

**What is `--note` for?**

Git commit messages typically describe **what** was done, but the **why** — architectural decisions, intent, tradeoffs — usually only lives in conversation history and disappears when the session ends. `--note` writes that semantic layer into `state/current.md`'s Progress Summary section (not the sync block), so future AI sessions see the why, not just the what.

```bash
vibe sync --note "Split adapter into three modes (full/slim/compact) because Cursor cannot read AGENTS.md — must inline rules in .mdc"
```

**C.L.E.A.R. review checklist** (only shown when there are real changes and not in hook mode):

```text
[C] Core Logic   — Is the core logic correct? Edge cases?
[L] Layout       — Structure/naming follows standards.md?
[E] Evidence     — Test output or API response as proof?
[A] Access       — Any hardcoded secrets or permission holes?
[R] Refactor     — Obvious tech debt or performance issues?
```

### 4. `vibe status`

**What it does**: view project state at any time (allowed in any lifecycle state). **As of v0.3.4 it's a health dashboard** showing days since last sync, commits behind, and per-adapter freshness.

```bash
vibe status
```

**Sample output (English UI when `config.vibe.lang = "en"`)**:

```text
┌────────── vibe status ──────────┐
│  Lifecycle      ACTIVE            │
│  Last sync      30 days ago (48 commits behind) │
│  State health   VERY STALE — run `vibe sync` urgently │
│  Adapter sync                    │
│                 claude    ⚠ stale │
│                 agents_md ⚠ stale │
│  Git            enabled           │
│  Content lang   en                │
│  Tasks          0 pending, 0 done, 0 stale │
└──────────────────────────────────┘
```

**Health classification**:

| Level | Condition |
|------|------|
| FRESH | < 3 days AND < 5 commits |
| STALE | 3-14 days OR 5-30 commits |
| VERY STALE | ≥ 14 days OR > 30 commits |

### 5. `vibe adapt`

**What it does**: manage AI/IDE adapter settings, **and as of v0.3.4 also switches interface language**.

```bash
vibe adapt --list                          # List all adapters (ON/OFF)
vibe adapt --add cursor                    # Enable Cursor adapter
vibe adapt --add claude                    # Enable Claude Code adapter
vibe adapt --sync --confirm                # Regenerate all enabled adapter files
vibe adapt --remove cursor --dry-run       # Preview files to delete
vibe adapt --remove cursor --confirm       # Confirm deletion (auto-backup)
vibe adapt --lang zh-TW                    # Switch interface language to Chinese
vibe adapt --lang en                       # Switch to English
```

**`--lang` vs `vibe init --force --lang`**:

| Operation | Scope | When to use |
|-----------|-------|-------------|
| `vibe adapt --lang` | Updates only `config.toml`'s lang field | You only want to switch UI language |
| `vibe init --force --lang` | Backs up `.vibe/`, regenerates adapters, resets lifecycle | Full reinit |

---

## Smart migration

If your project already has `CLAUDE.md`, `AGENTS.md`, `.cursorrules`, etc., `vibe init` detects and imports your rules:

```text
$ vibe init
Scanning project...

Found 2 existing config file(s):
  - CLAUDE.md
  - .cursorrules
Imported 9 rules into .vibe/state/standards.md
Archived 2 legacy file(s) to .vibe/archive/legacy/
```

**Two-phase safe migration**: copy all to archive → verify → only then delete originals. If a file has no extractable bullet rules (paragraph-form prose only), it's preserved with a warning instead of being archived.

---

## Daily workflows

### Solo dev

```text
Every morning: vibe start         # Auto-syncs last night's commits
  ↓
Work (each commit auto-syncs into state via git hook)
  ↓
Optional: vibe sync --note "..."  # Capture architectural decisions
  ↓
Every evening: vibe sync          # See C.L.E.A.R. review checklist
  ↓
Friday: vibe sync --compact       # Archive completed tasks
  ↓
Project end: vibe sync --close    # Write retrospective, lock state
```

### Multi-agent switching

```text
Morning: Claude Code terminal
  ↓ vibe start → Claude reads CLAUDE.md → sees "Session Start" → reads .vibe/state/
  ↓ work...
  ↓ commit (hook auto-syncs)

Afternoon: Cursor IDE
  ↓ vibe start → Cursor loads .mdc → sees injected ## Last Session → has full context
  ↓ Picks up morning's work seamlessly
```

### With Autoresearch

[Autoresearch](https://github.com/uditgoenka/autoresearch) is an autonomous iteration framework that runs **modify → verify → keep/discard → repeat** on any measurable goal.

**Basic flow**:

```bash
# Step 1: Start autoresearch in Claude Code
/autoresearch
Goal: Improve test coverage to 95%
Scope: src/**/*.py
Metric: pytest --cov --cov-report=term | grep TOTAL | awk '{print $4}'
Direction: higher_is_better
Verify: pytest --cov --cov-fail-under=95

# Step 2: Autoresearch runs the loop automatically
#   → Make atomic change → commit → measure metric
#   → Metric improved → KEEP commit
#   → Metric regressed → REVERT (history preserved)

# Step 3: Record with vibe (the git hook already auto-runs sync, but manual works too)
vibe sync    # Scans git log → detects experiment commits → writes state/experiments.md
vibe start   # Shows summary: 5 kept, 3 reverted
```

**Autoresearch full command list**:

| Command                  | Purpose                                                |
| ------------------------ | ------------------------------------------------------ |
| `/autoresearch`          | Main iteration loop (bounded/unbounded)                |
| `/autoresearch:plan`     | Interactive wizard: Goal, Scope, Metric, Verify        |
| `/autoresearch:debug`    | Scientific bug hunting: hypothesis → test → fix        |
| `/autoresearch:fix`      | Auto-fix loop (one fix per round, auto-revert on fail) |
| `/autoresearch:security` | STRIDE threat model + OWASP Top 10 + red team audit    |
| `/autoresearch:learn`    | Auto-generate/update docs                              |
| `/autoresearch:ship`     | 8-phase universal shipping flow                        |
| `/autoresearch:predict`  | 5-persona expert swarm analysis                        |
| `/autoresearch:reason`   | Adversarial refinement (generate → critique → judge)   |
| `/autoresearch:scenario` | Edge case + derivative scenario exploration            |

**vibe-state-cli detection mechanism**:

`vibe sync` scans git log and matches commit messages against patterns to flag experiment commits:

```text
# Default patterns (case-insensitive)
autoresearch:    experiment:    [autoresearch]    [experiment]    auto-research
```

Revert detection only checks the **prefix** (first word after the pattern):

```text
autoresearch: revert - metric dropped    → [REVERTED] ✓ correct
experiment: fix revert payment issue     → [KEPT]     ✓ correct (revert is in body, not prefix)
```

**Customize patterns** in `.vibe/config.toml`:

```toml
[experiments]
commit_patterns = ["autoresearch:", "experiment:", "[autoresearch]", "[experiment]", "auto-research"]
revert_prefixes = ["revert", "reset", "rollback", "undo"]
```

---

## Git Hook (v0.3.4)

`vibe init` installs `.git/hooks/post-commit` automatically, which runs `vibe sync --no-refresh` after every commit. That means:

- **You don't need to remember manual sync** — state updates after every commit
- **Failures never block your commit** — hook uses `|| true`, errors silently log to `.vibe/state/.hook.log`
- **No working-tree noise** — `--no-refresh` skips adapter regeneration, so you don't get dirty changes right after committing
- **Silent skip in READY state** — first commit after `vibe init --force` won't spam the log (lifecycle hasn't reached ACTIVE yet)

Don't want the hook?

```bash
vibe init --no-hooks                    # Skip during init
# Or after install: manually delete the vibe block in .git/hooks/post-commit
# (between the two markers)
```

---

## Supported AI tools

| Tool                            | Adapter name  | Auto-detect signal                     |
| ------------------------------- | ------------- | -------------------------------------- |
| AGENTS.md (universal standard)  | `agents_md`   | `AGENTS.md` exists                     |
| Claude Code                     | `claude`      | `.claude/` or `CLAUDE.md` (with skills) |
| Google Antigravity / Gemini CLI | `antigravity` | `GEMINI.md` or `.gemini/`              |
| Cursor                          | `cursor`      | `.cursor/` or `.cursorrules`           |
| GitHub Copilot (VS Code)        | `copilot`     | `.github/copilot-instructions.md`      |
| Windsurf                        | `windsurf`    | `.windsurf/` or `.windsurfrules`       |
| Cline                           | `cline`       | `.clinerules/`                         |
| Roo Code                        | `roo`         | `.roo/`                                |

**Token savings**: when AGENTS.md + other adapters are co-enabled, the others switch to slim mode (frontmatter + pointer to AGENTS.md only) to avoid duplicate content.

**Vibe Commands**: every adapter's config file includes a "Vibe Commands" block instructing the AI: "When the user says `vibe sync`, run that command in the terminal — don't explain or reimplement it." Works across all AI tools without plugins.

**Claude Code Skills**: the claude adapter additionally generates `.claude/skills/vibe-*/SKILL.md`, making `/vibe-init`, `/vibe-start`, `/vibe-sync`, `/vibe-status`, `/vibe-adapt` directly usable as slash commands. This format follows the [Agent Skills open standard](https://agentskills.io/).

---

## Environment variables

| Variable | Purpose |
|----------|---------|
| `VIBE_SKIP_HOOK_INSTALL` | Set to `1` to skip `vibe init`'s hook install (used by test suites and CI) |

---

## FAQ

### Should `.vibe/` be committed to git?

**Yes**. `.vibe/` is the project's shared brain, meant for the team to see. `.vibe/backups/`, `.vibe/state/.hook.log`, and `.vibe/state/*.lock` are excluded by `.gitignore`.

### Can I use this without git?

Yes. `vibe init` auto-detects; non-git projects skip git operations and the hook isn't installed.

### Can I use Claude Code and Cursor at the same time?

Yes. `vibe adapt --add claude` + `vibe adapt --add cursor` + `vibe adapt --sync`. Each tool loads its own config, and they share `.vibe/state/`.

### `vibe status` says STALE — what do I do?

`vibe sync` writes the missing commits to state. Or simpler: just `vibe start`, which auto-syncs.

### What is `experiments.md`?

Autoresearch experiments auto-recorded. `vibe sync` detects commits prefixed with `autoresearch:` or `[autoresearch]` and logs them as KEPT or REVERTED.

### The AI doesn't respond when I type `vibe sync` in the IDE?

Every adapter config includes a "Vibe Commands" instruction telling the AI to execute terminal commands directly. If the AI still doesn't get it, say "Please run `vibe sync` in the terminal." With Claude Code or Cline you can also type `/vibe-sync` (slash command).
