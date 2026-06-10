# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.3.8] — 2026-06-10

> Third consecutive break of the 90-day post-v0.3.6 freeze. Each break
> was strategic, not accidental: v0.3.6 added **outbound** (`vibe sync
> --promote`, state → external store), v0.3.7 added **inbound**
> (`[memory]`, external store → AGENTS.md template), v0.3.8 adds
> **observability** (`vibe status --diagnose`, cross-machine health
> probe). The three together complete vibe-state-cli's second-brain
> architecture; after this ship the freeze actually means something
> because there's no remaining structural gap to fill.
>
> The trigger came from a real-world friction: the maintainer's
> `tailscale ssh liyon-srv 'vibe sync'` failed because `vibe` wasn't on
> the non-interactive shell PATH (Linux `~/.local/bin` SSH non-login
> gotcha — same root cause as the Windows codex-cli PATH friction from
> earlier). A symlink fixed the immediate case, but the deeper problem
> ("environment health is invisible across machines") deserved a
> first-class command surface. The flag-not-command shape (`vibe status
> --diagnose`) keeps the 5-command minimum-viable surface, consistent
> with v0.3.6 `--promote` precedent.

### Added

- **`vibe status --diagnose`** — brew-doctor-style deep environment check on top of the existing `vibe status` dashboard. Renders 4 check groups with ✓/⚠/✗ markers + actionable fix hints + a tail summary. Exit 1 on any error; warnings stay exit 0 (brew-doctor convention).
- **Environment group** — vibe binary location + version (via `vibe --version` subprocess), python version (informational), pipx on PATH.
- **Project group** — `.vibe/state/` structure, config.toml readability, `.vibe/.gitignore` entries (compared against `_INTERNAL_GITIGNORE_ENTRIES`), post-commit hook installation status (with `vibe-state-cli:auto-sync` marker check; resolves gitlinks for submodules/worktrees).
- **Adapters group** — each enabled adapter's freshness via the existing `_check_adapter_freshness()` helper. Plus a v0.3.7-specific assertion that AGENTS.md contains `## Persistent Knowledge — QUERY BEFORE RECALL` (catches workspaces still on pre-v0.3.7 template that haven't run `vibe sync` since upgrade).
- **Memory layer group** — `[memory].enabled` state, `basic-memory` CLI on PATH (the reverse of the SSH PATH friction that triggered this release), and a 5-second runtime probe (`basic-memory --version` with timeout) that surfaces cold-start delays as warnings rather than silent hangs.
- **5-second per-check subprocess timeout** (`_DIAGNOSE_TIMEOUT`). The original RFC trigger was BM cold-start ≥30s on Windows; 5s captures warm-cache health while keeping the diagnose pipeline fast. Cold-start scenarios surface as `⚠ timed out` with explicit retry guidance, not hangs.

### Changed

- `vibe status` (no flag) behavior unchanged. `--diagnose` is purely additive.

### Fixed (folded into this commit per adversarial review)

- **AGENTS.md read errors no longer silently disappear**. Adversarial review (2 of 4 reviewers independently) flagged a `try/except OSError: pass` on the AGENTS.md content read at `cmd_status.py:386-387`. The silent-pass would have produced different check counts across machines (one machine readable, another not), violating the cross-machine determinism contract diagnose is supposed to enforce. Replaced with an explicit warning result.

### Strategic context

- This is the **third consecutive break** of the 90-day post-v0.3.6 freeze. The maintainer explicitly accepted the break each time, with each break filling a structural gap in the second-brain architecture (outbound/inbound/observability). Pre-v0.3.6 freeze was decided before that architecture became the strategic direction; the architecture's three gaps had to be filled before the freeze could be honored without leaving a half-built system.
- After v0.3.8 ships: **freeze clock resets to 2026-06-10 → 2026-09-08, and this time it really means it**. Subsequent ships require either a P0 user-filed bug or a `[[cross-team-dispatch-via-rfc]]` cycle that survives adversarial review with strategic justification.
- Per the BM methodology note `[[cli-design-prefer-flag-over-new-command]]` (written by laptop-side Claude during this cycle): `--diagnose` was deliberately implemented as a flag on `vibe status`, not as a new `vibe doctor` command. Inherits the brew/npm/flutter "doctor" lineage but preserves the 5-command minimum-viable surface that the v0.3.6 workflow analysis established. Same principle as v0.3.6 `vibe sync --promote`.

### Tests

- 12 new tests, **285 total passing** (was 273 in v0.3.7, +12 new). `TestV038StatusDiagnose` covers: status-without-diagnose regression guard, all 4 group headers render, exit codes (1 on error / 0 on only warnings), environment reports python version, project warns on missing .gitignore entries, project warns when no .git, adapters flag missing Persistent Knowledge section, memory layer disabled = ok, memory layer warns on unknown target, memory layer errors when basic-memory CLI missing, runtime probe timeout = warn (cold-start case), only-warnings = exit 0.

### Adversarial review note

- 4 reviewers + 1 synth ran before commit. Verdict: **SHIP-WITH-FOLLOWUP** (confidence 0.82). Two reviewers (Correctness + Cross-machine Determinism) both flagged the same P1 (silent except on AGENTS.md read). Synth bundled it into this commit per the v0.3.6 / v0.3.7 pre-commit fix pattern. Four P2 follow-ups recorded in `.vibe/state/tasks.md` for v0.3.9 consideration. Two P3 items refuted (errors-first ordering and empty-group header suppression — both rejected because the existing design choices were intentional and tests assert them).

### Backlog notes

- `.vibe/state/tasks.md` carries v0.3.8 P2 follow-ups (silent-except pattern in 2 remaining places, MCP probe fidelity) + v0.3.7 P2 items (over-broad MCP-accessible wording, silent config-load swallow) + v0.3.6 carryover (hook marker auto-replace, sync activity-log skip after hook cursor advance). All deferred under the new freeze starting 2026-06-10.

### Cross-AI coordination note

- v0.3.8 was designed via a two-session loop: laptop-side Claude ran an independent design-alignment workflow (4 reviewers + synth) after the maintainer asked "OSS 應該也要修嗎?" upon hitting the SSH PATH friction. That workflow's output was simplified per the maintainer's "diagnose就好，不要複雜化" signal (rejecting --doctor alias, --json output, -d short flag, --no-emoji, AGENTS.md version markers, governance-workspace special handling, parallel check execution, --timeout flag — none of which made it into v0.3.8). The portable principle (flag > new command) was captured in BM as methodology, not as a project-specific RFC, so future OSS work on any CLI can recall it directly.

---

## [0.3.7] — 2026-06-10

> Strategic break of the 90-day v0.3.6 post-ship freeze. The maintainer
> needed multi-agent Basic Memory integration to work across laptop and
> server NOW; deferring 87 more days didn't serve the dogfood loop.
> Freeze clock resets from this ship date.
>
> v0.3.7 grew out of a [[cross-team-dispatch-via-rfc]] cycle: a separate
> Claude session (laptop side) wrote `docs/v0.3.6-rfc-agents-md-bm-aware.md`
> after a SessionStart-hook post-mortem surfaced an architectural insight
> — vibe-state-cli's AGENTS.md template is already the cross-agent
> equivalent of a SessionStart hook (pure markdown, every agent that
> reads AGENTS.md follows). The RFC proposed making the template
> persistent-knowledge-aware. This release adopts that RFC with
> adjustments documented in `docs/v0.3.6-rfc-agents-md-bm-aware-RESPONSE.md`.

### Added

- **`vibe sync` regenerates AGENTS.md with a `## Persistent Knowledge — QUERY BEFORE RECALL` section** — placed between `## Session Start` and `## Workflow`. Tells every agent that reads AGENTS.md (Claude, Codex, Gemini/Antigravity, Cursor via v0.3.6 shim, ...) to query the configured knowledge layer before answering recall questions ("what did we decide", "where did we leave off"). The mechanism is vendor-neutral; the default content targets Basic Memory.
- **New `[memory]` config section in `.vibe/config.toml`** — symmetric to v0.3.6's `[promotion]`:
  - `enabled` (default `true`) — flip to `false` to skip the section entirely
  - `target` (default `"basic-memory"`) — string; `"obsidian"`, `"logseq"`, etc. fall back to a vendor-agnostic stub instead of leaking BM specifics
  - `projects` (default `[]`) — empty list renders a generic "query whichever projects you find" instruction; non-empty list renders explicit project bullets
- **Cold-start performance caveat in the template** — explicitly tells agents that the first Basic Memory query may take 30+ seconds on Windows (the exact symptom that motivated the RFC), to cap per-query timeouts at ~5 seconds, and to treat slow queries as unavailable rather than waiting.
- **Concrete fallback baseline** — when Basic Memory is offline / MCP not registered / query times out, the template now names `.vibe/state/*.md` as the explicit baseline (not "proceed without it"), specifies a one-line warning shape (`⚠ Basic Memory unavailable — using .vibe/state only`), and prohibits retry loops + blocking.

### Changed

- **Default-on for `[memory]` while `[promotion]` stays default-off — explicit design choice, documented here**. The asymmetry is intentional: `[promotion]` is **outbound** (vibe writes to an external store on user-initiated action — sensible to require opt-in), while `[memory]` is **inbound read guidance** (the template tells agents to pull from a store on session start — sensible to assume default for vibe-managed multi-agent setups, where a knowledge layer is the whole point of using the tool). Users without a persistent memory layer flip `[memory].enabled = false`; the section disappears, no agent ever sees the BM tool names. This asymmetry was flagged by adversarial review (4 reviewers, 2 voted BLOCK on default-on), accepted as conscious owner choice, and preserved with the safety nets above.

### Strategic context

- **vibe-state-cli philosophy**: AGENTS.md is the cross-agent baseline; tool-specific configs are opt-in. v0.3.7 applies that philosophy to the persistent-knowledge layer — every workspace becomes BM-aware for every agent with one template change. Higher leverage than any Claude-specific SessionStart hook fix.
- **90-day freeze**: v0.3.6 shipped 2026-06-07 with a stated 90-day post-ship freeze. v0.3.7 breaks that freeze deliberately for urgent multi-agent integration. Freeze clock resets from v0.3.7's ship date (2026-06-10 → 2026-09-08).

### Tests

- 10 new tests, **283 total passing** (was 273 in v0.3.6, +10 new). `TestMemorySectionInjection` covers: default-config rendering, explicit projects rendering, OSS safety net (default never leaks owner project names), `enabled=false` complete skip, unknown-target vendor-agnostic stub, offline fallback prose (baseline named, retry/block prohibited, cold-start performance warned), freshness marker preservation, idempotent regeneration, mode restriction (full only — slim/compact skip), section position between `Session Start` and `Workflow`.

### Adversarial review note

- 4 reviewers + 1 synth ran before commit. Verdict: **SHIP-WITH-FOLLOWUP** (confidence 0.82). Two reviewers voted BLOCK; synth refuted both with grounded reasoning (the `_write_file` "user-content destruction" claim conflated AGENTS.md with state files — AGENTS.md is fully managed by design since v0.3.0; the default-on objection was the explicit owner choice already accepted upstream). Two P1 follow-ups (fallback prose, asymmetry documentation) were folded into this commit; two P2 follow-ups (over-broad "MCP-accessible from any agent" wording, silent config-load swallow) are recorded in `.vibe/state/tasks.md` for v0.3.8 consideration.

### Backlog notes

- `.vibe/state/tasks.md` carries the v0.3.7 P2 follow-ups + v0.3.6's two existing backlog items (`install_post_commit_hook` marker auto-replace, `vibe sync` activity-log skip after hook cursor advance). All deferred under the new 90-day freeze starting 2026-06-10.

---

## [0.3.6] — 2026-05-08

> Hardening + standards alignment release. v0.3.5's freshly-shipped auto-sync
> hook exposed one real bug (the two-file infinite loop), the Linux Foundation
> formally anchored AGENTS.md (2025-12), Google announced Gemini CLI sunset
> on 2026-06-18, and dogfood usage matured the tool past Alpha. Six items,
> all driven by external signals or own-eyes evidence — no speculative
> additions. After this ships, a 90-day code freeze begins.

### Fixed

- **Post-commit hook no longer creates an infinite `git status` loop** — v0.3.5's hook ran `vibe sync --no-refresh`, which both advanced the cursor AND appended to `current.md`. Both files were tracked, so every commit produced two "modified" entries, and committing them re-fired the hook. v0.3.6 splits sync into two paths: `perform_cursor_update()` (hook mode — cursor only) and `perform_git_sync()` (explicit user invocation — full append). `current.md` is now reserved for human-initiated `vibe sync` and `vibe start`. The behavior was caught dogfooding within hours of v0.3.5's release.

- **`.sync-cursor` and `.lifecycle` are now untracked runtime state** — both files were git-tracked but mutated on every commit, which is the actual root cause of the loop above. v0.3.6 adds them to `.vibe/.gitignore` and a one-shot `ensure_state_files_untracked()` migration runs on `vibe init --force` and `vibe start`. File contents stay on disk; only the index entry is removed. Mirrors the Unix convention (and Claude Code's session model) of "machine-driven state stays untracked."

### Changed

- **AGENTS.md is now the canonical source of truth (pivot)** — when AGENTS.md is co-enabled, the Cursor / Windsurf / Cline / Roo / Copilot adapters emit a one-line `See AGENTS.md` shim instead of inlining standards. Standalone fallback (when AGENTS.md is not enabled) still inlines for backwards compatibility. Reflects the Linux Foundation Agentic AI Foundation standard (announced 2025-12; 60,000+ repos adopted as of v0.3.6 ship). Single source of truth, less drift, less code per adapter.

- **Antigravity adapter writes both `.agents/skills/` (new) and `GEMINI.md` (deprecated)** — Google announced Gemini CLI sunset on 2026-06-18, replaced by Antigravity CLI (`agy`), which reads `AGENTS.md` and `.agents/skills/`. v0.3.6 writes the new layout (forward-compatible) while keeping `GEMINI.md` with a deprecation banner pointing transition users at the new structure. A future release will remove `GEMINI.md` output entirely.

- **Status: Alpha → Beta** — `pyproject.toml` classifier bumped from `Development Status :: 3 - Alpha` to `4 - Beta`. The "Alpha" label is no longer truthful — vibe has been production-stable across 11+ dogfood projects for 60+ days with zero user-filed bugs. Not "5 - Production/Stable" — that's a post-1.0 commitment we explicitly defer.

### Added

- **`vibe sync --promote "title"`** — opt-in flag that ships the latest sync block from `current.md` to an external knowledge store via a vendor-neutral subprocess shim. Default backend: `basic-memory` CLI (https://docs.basicmemory.com/). Architecture is extensible — `target` in `[promotion]` config can become `obsidian`, `logseq`, `raw-file`, etc. with one shim per target. Flag is a flag, not a new command, deliberately: 5-command surface stays at minimum-viable, and `enabled = false` (default) means zero behavior change for users who don't opt in. Editor pre-fills the latest sync block; user trims/edits to the rationale they want preserved cross-project; vibe pipes to the backend's CLI.

### Removed

- **Unused `mcp` optional dependency** — `pyproject.toml`'s `[project.optional-dependencies].mcp = ["mcp>=1.27.0"]` advertised functionality that does not exist (`grep -rn 'mcp\|fastmcp\|ModelContextProtocol' src/` returns zero hits). Dead-code cleanup; honest pyproject. MCP integration remains deferred until a clear cross-tool pattern emerges; no users have inquired as of v0.3.6.

### Tests

- 14 new tests, 263 total passing. `TestV036PostCommitHookLoopFix` proves the hook path no longer touches `current.md` and the explicit path still does. `TestV036UntrackMigration` covers the `git rm --cached` migration on both `vibe init --force` and `vibe start` (and verifies idempotency + content preservation on disk). `TestV036SyncPromote` covers disabled-by-default, title-required, unknown-target, missing-CLI, and a full mocked happy-path through `basic-memory`. Adapter tests gained the `test_shims_to_agents_md_when_co_enabled` regression net for all five compact-mode adapters.

### Notes

- After ship: **90-day code freeze**. No `src/` commits unless a P0 user-filed bug surfaces. Observation period to separate real demand signal from internal restlessness. RFC `docs/v0.3.6-roadmap-RFC.md` documents the strategic context and the rejected anti-patterns (no `basic_memory` adapter, no auto-pull on `vibe start`, no 10th adapter, no MCP server yet).

---

## [0.3.5] — 2026-05-07

> Two real-world bugs surfaced within hours of v0.3.4 going live, plus a
> defensive pass that closed four more quiet bug surfaces (big-repo
> latency, submodules/worktrees, upgrade UX, write failures). Everything
> ships together as one solid release.

### Fixed

- **`UnicodeEncodeError` on Windows cp950/cp936/cp932 consoles** — `vibe status` (and any other Rich-rendered output) crashed with `UnicodeEncodeError: 'cp950' codec can't encode character '✓'` on Windows CMD, PowerShell 5, and CJK-default Windows installs. The `✓ ⚠ ✗` markers and Unicode box-drawing characters that Rich emits cannot be encoded by legacy code pages. Fixed by reconfiguring `sys.stdout` and `sys.stderr` to UTF-8 at CLI entry — users no longer need to set `PYTHONIOENCODING=utf-8` themselves. Reported in production by an external team within hours of the v0.3.4 release.

- **`.vibe/state/.hook.log` showed up untracked in `git status`** — the post-commit hook installed by `vibe init` writes its sync output to `.vibe/state/.hook.log`, but `.vibe/.gitignore` only listed `backups/`. Every commit therefore created an untracked file that lingered in `git status`. Reported by the ProBrain team. Fixed by:
  - Extracting `.gitignore` management into `ensure_internal_gitignore()` helper that idempotently appends missing entries (`backups/`, `state/*.lock`, `state/.hook.log`) without overwriting user additions.
  - `vibe init --force` *and* `vibe start` now run this helper, so existing projects upgrading to v0.3.5 automatically gain coverage for the newly-introduced runtime files — no `--force` re-init required.

- **Post-commit hook now runs in the background** — on big repos `vibe sync --no-refresh` can take several seconds (git log + diff stat over many commits), and the original hook ran it synchronously, so the commit prompt felt frozen. The installed hook now uses the POSIX `(... &)` background-subshell pattern: the commit returns immediately, sync completes asynchronously, and output still streams to `.vibe/state/.hook.log`. Works under git-bash on Windows.

- **Submodules and linked worktrees can now install the hook** — when `.git` is a *file* (gitlink) pointing to `<parent>/.git/modules/<sub>` (submodule) or `<main>/.git/worktrees/<name>` (linked worktree), the previous installer treated it as "no git" and silently skipped hook installation. Added `_resolve_git_dir()` that follows the `gitdir:` pointer and lands the hook in the correct per-checkout hooks directory. Broken gitlinks (target missing) still fail closed as `no_git` rather than raising.

- **`vibe init` no longer crashes on rare write failures** — read-only filesystems, antivirus-locked files, or disk-full conditions used to surface as a Python traceback. Both `install_post_commit_hook()` and `ensure_internal_gitignore()` calls are now wrapped: on `OSError` we print a yellow warning and continue, so init still produces a working `.vibe/` and the user gets actionable feedback instead of a stack trace.

### Hardened

- `ensure_internal_gitignore()` no longer leaves a stray leading newline when the existing `.gitignore` is empty or whitespace-only.

### Tests

- 19 new tests, 249 total passing. `TestCliEncoding` covers the UTF-8 forcing logic with mocked cp950 streams; integration tests verify the `init` wiring for fresh and pre-existing `.gitignore` files; `TestEnsureInternalGitignore` adds 7 unit-level tests covering all helper branches; `TestStartUpgradesGitignore` covers the auto-upgrade path on `vibe start`; `TestHookSubmoduleAndWorktree` covers gitlink resolution and the background-execution shape of the hook script; `TestInitGracefulFailures` covers both wrapped failure paths via mocked `OSError`.

---

## [0.3.4] — 2026-05-07

> Closes the cross-session continuity gap: state used to silently fall behind
> git unless you remembered to run `vibe sync`. Now the existing five commands
> carry that load themselves — no new commands.

### Added

- **`vibe status` health dashboard** — surfaces last-sync age, commits behind, per-adapter sync state, and a FRESH/STALE/VERY-STALE classification. Output is i18n-aware (en + zh-TW; auto-selects from `config.vibe.lang`)
- **`vibe start` auto-sync** — pulls new commits since the last cursor before loading state, so a fresh session always reflects current git. No more "I forgot to sync"
- **`vibe sync --note "..."`** — appends a dated semantic note inside the Progress Summary section (recognizes both English `Progress Summary` and zh-TW `進度摘要` headings). Captures the *why* that commit messages alone don't preserve
- **`vibe sync --no-refresh`** — skips adapter rewrites; used by the new git post-commit hook to avoid working-tree noise after each commit
- **`vibe init` installs git post-commit hook by default** — every commit auto-syncs state into `current.md` via `vibe sync --no-refresh`. `--no-hooks` opts out. Hook failures log silently to `.vibe/state/.hook.log` and never block your commit
- **`VIBE_SKIP_HOOK_INSTALL` env var** — honored by `vibe init` so test suites and CI can suppress the hook side-effect
- **`vibe adapt --lang <en|zh-TW>`** — lightweight interface-language switch. Updates `.vibe/config.toml` only; existing state files keep their original language, adapter files don't regenerate. The right tool when you just want to flip `vibe status` between English and Chinese without re-running `init --force`

### Changed

- `perform_git_sync` extracted to `_helpers.py` as a `SyncResult`-returning helper. Both `vibe sync` and `vibe start` now share the same git → state pipeline
- Adapter freshness detection examines all managed files (not just the first), so adapters writing multiple files (e.g. claude → CLAUDE.md + `.claude/rules/*.md` + skills) report fresh as long as any managed file carries the current summary marker

### Fixed

- `vibe init --force` no longer silently reverts a zh-TW project back to English. The new `--lang` resolution is: explicit flag > existing config on `--force` > default `en`
- `vibe sync --no-refresh` no longer prints the C.L.E.A.R. review checklist. The hook redirects sync output to `.vibe/state/.hook.log`; the checklist is for humans, so leaking it into a log file (and hitting cp950 encoding mojibake on Windows along the way) was pure noise
- `vibe sync --no-refresh` silently skips when lifecycle isn't ACTIVE. After `vibe init --force`, lifecycle is READY until the user runs `vibe start`; the post-commit hook used to spam `.hook.log` with "Cannot run 'vibe sync' in READY state" errors on every commit. Plain `vibe sync` (no flag) still errors loudly to preserve the manual UX

### Tests

- 22 new tests, 230 total passing. New `tests/conftest.py` autouse fixture sets `VIBE_SKIP_HOOK_INSTALL=1` so `subprocess.run git commit` inside tests stays deterministic; hook-behavior tests delete the env var in their own scope

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
