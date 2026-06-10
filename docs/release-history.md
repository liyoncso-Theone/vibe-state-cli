# Release History — vibe-state-cli

> Institutional memory for the v0.3.5 → v0.3.6 → v0.3.7 release cycle.
>
> This document exists because the local `release/v0.3.5`, `release/v0.3.6`, and
> `release/v0.3.7` branches are about to be deleted. Their commits are preserved
> on `main` via merge commits, but several side-effects are not — orphaned
> post-merge commits, the actual development process for each release, the
> first complete cross-team-dispatch-via-RFC loop, and a recurring anti-pattern
> the maintainer kept stepping into. Capturing those here keeps the audit trail
> intact once the branches are gone.
>
> Sources: `CHANGELOG.md`, `docs/v0.3.6-roadmap-RFC.md`,
> `docs/v0.3.6-rfc-agents-md-bm-aware.md`,
> `docs/v0.3.6-rfc-agents-md-bm-aware-RESPONSE.md`, `.vibe/state/tasks.md`,
> and `git log` on each release branch.

---

## [0.3.5] — 2026-05-07

### Scope

Hot-fix release addressing two production bugs (Windows cp950 encoding,
hook-generated `.hook.log` noise) plus four defensive patches discovered during
pre-ship self-review.

### Timeline

| Event | When |
| --- | --- |
| Branch created (from v0.3.4 merge `f36def9`) | 2026-05-07 |
| First real commit (`34149aa` cp950 fix) | 2026-05-07 23:16:50 |
| Merged to `main` (`8b6da10` PR #7) | 2026-05-07 23:59:43 |
| PyPI published | 2026-05-07 |

### Commits

**Merge commit on main:** `8b6da10` — *Merge pull request #7 from
liyoncso-Theone/release/v0.3.5*

**Commits on branch that landed on main:**

| SHA | Subject |
| --- | --- |
| `34149aa` | fix: cp950 UnicodeEncodeError + .hook.log untracked noise (v0.3.5) |
| `e4a1055` | test: harden ensure_internal_gitignore against edge cases |
| `da09ac4` | fix: 4 defensive patches — submodule/worktree, big-repo hook, upgrade UX, graceful init |

**Orphan / cherry-picked commits:** none. Clean linear history on the release
branch; nothing left stranded.

### Scope summary

v0.3.5 ships two real-world bugs caught in production within hours of v0.3.4
going live, plus four defensive patches discovered during pre-ship self-review.

- **Bug 1 — Windows cp950 crash.** `vibe status` raised
  `UnicodeEncodeError: 'cp950' codec` on Windows CMD, PowerShell 5, and
  CJK-default Windows installs, because Rich's Unicode box-drawing and
  `✓ ⚠ ✗` markers cannot be encoded by legacy code pages. Fixed by forcing
  UTF-8 on `sys.stdout` / `sys.stderr` at CLI entry, so users no longer have
  to set `PYTHONIOENCODING=utf-8` themselves.
- **Bug 2 — `.hook.log` untracked-after-every-commit (reported by ProBrain).**
  The post-commit hook wrote to `.vibe/state/.hook.log`, but `.vibe/.gitignore`
  only listed `backups/`. Fixed by extracting gitignore management into an
  idempotent `ensure_internal_gitignore()` helper that runs on both
  `vibe init --force` and `vibe start`, giving upgraders automatic coverage
  for the new runtime file without re-running `init --force`.
- **Four defensive patches** bundled as `da09ac4`:
  1. Post-commit hook backgrounded via POSIX `(... &)` so commits don't freeze
     on big repos.
  2. `_resolve_git_dir()` follows `gitdir:` pointers so the hook installs in
     submodules and linked worktrees instead of silently skipping.
  3. `vibe start` self-heals `.gitignore` for existing projects.
  4. `OSError` guards on `install_post_commit_hook()` and
     `ensure_internal_gitignore()` so init degrades gracefully on read-only
     filesystems, AV-locked files, or disk-full conditions.

19 new tests; 249 total passing. No RFC — this was a pure bug-fix release
driven by external signals and owner self-review.

### Process notes (honest)

v0.3.5 marks the first time the **"ship-then-find-bugs"** pattern triggered at
scale. v0.3.4 shipped around 14:00 UTC+8 on 2026-05-07; within hours the
ProBrain team reported `.hook.log` noise, and the owner's own Windows machine
surfaced the cp950 crash on `vibe status`.

Initially scoped as two one-off fixes, the release widened during the pre-ship
review pass when the owner found four additional edge cases that would have
quietly damaged new-user impressions (big-repo hook lag, submodule silently
skipped, upgrade UX friction, init crash on disk-full). The decision to bundle
all six rather than ship incrementally was deliberate: these were critical gaps
in the core workflow, not new features.

This is the first explicit instance of **"no bugs before ship"** acting as a
gating criterion — the release was held until the self-review pass was
complete. That informal practice became the formalized adversarial review
protocol in v0.3.6.

The `.hook.log` bug also had a secondary dimension: ProBrain noted that the
original `if not exists: create` guard prevented upgrades from picking up new
gitignore entries. The fix (helper + unconditional call) solved both the
"untracked after commit" symptom AND the "existing projects can't upgrade"
upgrade-path problem. This **dual-solution pattern** became a template for
v0.3.6's split-path fix (hook-only cursor move vs full user-initiated sync).

### Lessons (release-specific)

1. **External signals win internal momentum.** Both cp950 and `.hook.log` were
   production-reported, not speculative. v0.3.5 established the "ship fast,
   patch fast" cadence with external feedback as the primary trigger.
2. **Defensive pass before ship is mandatory.** The four "quiet bad impression"
   patches existed because the owner ran a self-review pass *before*
   publishing. Later releases formalized this as adversarial review.
3. **Gitignore management is infrastructure, not a detail.** Extracting
   `ensure_internal_gitignore()` unlocked both the immediate fix and the
   upgrade path. "Git-tracked runtime files are an anti-pattern" was validated
   here and became architectural dogma (and the direct cause of the v0.3.6
   `.sync-cursor` / `.lifecycle` untrack migration).
4. **Hooks must degrade gracefully.** Backgrounding the hook and wrapping init
   in `OSError` guards proved that "best effort" is the right posture for
   side-effects — failures should warn, never block.
5. **Git-edge cases (submodules, worktrees) are real constraints.**
   `_resolve_git_dir()` proved "assume `.git` is always a directory" is naive
   in real repos.
6. **The pre-ship review pass was born here.** Owner held the release until
   four extra defensive patches existed. This is the seed of v0.3.6's
   4-reviewer + synthesizer adversarial protocol.

---

## [0.3.6] — 2026-05-08

### Scope

Hardening release: killed the post-commit-hook infinite loop, pivoted to
AGENTS.md-canonical adapter pattern, sunsetted GEMINI.md, added
`vibe sync --promote` flag, and bumped status from Alpha to Beta with a
declared 90-day post-ship freeze.

### Timeline

| Event | When |
| --- | --- |
| Branch created (after v0.3.5 ship) | early May 2026 |
| First real commit (`ce1f990`) | 2026-06-07 19:57:55 |
| Merged to `main` (`c3c9009` PR #9) | 2026-06-07 23:21:18 |
| PyPI published | 2026-06-07 |

Note: CHANGELOG date is `2026-05-08`; actual merge timestamp is `2026-06-07`.
The CHANGELOG date is symbolic (continuity with v0.3.5); the git timestamps
are ground truth.

### Commits

**Merge commit on main:** `c3c9009` — *Merge pull request #9 from
liyoncso-Theone/release/v0.3.6*

**Commits on branch that landed on main:**

| SHA | Subject |
| --- | --- |
| `ce1f990` | feat: v0.3.6 — kill commit loop, AGENTS.md pivot, --promote flag, Beta |

**Orphan / post-merge-on-dead-branch commits (will be lost when branch is deleted):**

| SHA | Subject | Status |
| --- | --- | --- |
| `0177410` | feat: add new skills for vibe commands and initialize scheduled tasks lock | Lost — committed to `release/v0.3.6` *after* the merge to main; never cherry-picked. |
| `15da63d` | chore: dogfood v0.3.6 on self — adapter regen + state file migration | Lost — same pattern. |

These two commits exist only on the release branch and represent dogfood work
(applying v0.3.6 to vibe-state-cli's own `.vibe/`). They were committed on
2026-06-07 between 23:27 and 23:49 — *after* the merge commit `c3c9009` at
23:21. They were never cherry-picked to main. **This is the "dead-branch
trap" documented in the cross-cutting patterns section below.**

### Scope summary

v0.3.6 addressed the **critical post-commit-hook infinite loop** discovered
during v0.3.5 dogfooding: `.sync-cursor` and `.lifecycle` were git-tracked but
mutated on every commit, causing two files to appear in `git status`
indefinitely. The fix split sync behavior into two paths:

- `perform_cursor_update()` — hook mode, cursor only, never touches
  `current.md`.
- `perform_git_sync()` — explicit user invocation, full append.

`current.md` is now reserved for human-initiated `vibe sync` / `vibe start`,
and `.sync-cursor` / `.lifecycle` were migrated to untracked runtime state via
a one-shot `ensure_state_files_untracked()` migration on
`vibe init --force` and `vibe start`.

Other scope items:

- **AGENTS.md became the canonical adapter target.** Five compact-mode
  adapters (Cursor, Windsurf, Cline, Roo, Copilot) emit a one-line
  `See AGENTS.md` shim when AGENTS.md is co-enabled, instead of inlining
  standards. Standalone fallback still inlines for backward compatibility.
  Reflects the Linux Foundation Agentic AI Foundation standard announced
  2025-12 (60,000+ repos adopted as of v0.3.6 ship).
- **Antigravity adapter writes the new `.agents/skills/` layout** while
  keeping `GEMINI.md` with a deprecation banner, ahead of Google's
  2026-06-18 Gemini CLI sunset.
- **`vibe sync --promote "title"`** — opt-in flag (not a new command) that
  ships the latest sync block to an external knowledge store via a
  vendor-neutral subprocess shim. Default backend: `basic-memory` CLI;
  `target` in `[promotion]` config can become `obsidian`, `logseq`, etc.
- **Status: Alpha → Beta.** `pyproject.toml` classifier bumped to reflect 60+
  days of stable production use across 11+ dogfood projects with zero
  user-filed bugs.
- **Removed unused `mcp` optional dependency** — `pyproject.toml`
  advertised functionality that did not exist anywhere in `src/`. Honest
  pyproject.

14 new tests; 263 total passing.

### Process notes (honest)

v0.3.6 was the first **RFC-driven release** (`docs/v0.3.6-roadmap-RFC.md`,
filed by owner with comprehensive adversarial triage). All six scope items had
external motivators: hook bug (own-eyes evidence), MCP dead code (grep
cleanup), AGENTS.md pivot (Linux Foundation standard), Gemini CLI sunset
(Google deprecation deadline), `--promote` flag (owner's Basic Memory workflow,
but extensible), and Alpha→Beta (truth-in-advertising).

The release underwent **4-reviewer adversarial review before commit**
(confidence 0.92, verdict SHIP). The RFC itself explicitly documented rejected
anti-patterns (no `basic_memory` adapter, no auto-pull on `vibe start`, no
10th adapter, no MCP server yet) to save future contributors the cost of
rediscovering the same dead ends. The rationale was treated as part of the
deliverable, not as throwaway debate.

**Dead-branch trap (first occurrence):** After the merge, the maintainer
committed `0177410` and `15da63d` directly to `release/v0.3.6` as
"convenience" dogfood work (adapter regeneration on self, state file
migration). They were never cherry-picked to main. The release branch was
mentally "done" once the PR closed, but psychologically still "live" because
it hadn't been deleted — so committing there for follow-up work felt natural
even though it was wrong.

**90-day freeze declared, broken on day 3.** v0.3.6's stated freeze ran
through 2026-09-08. v0.3.7 broke it on 2026-06-10 (86 days early) with
explicit written justification (multi-agent urgency — SessionStart hook
timeout on Windows). The freeze clock was then reset from v0.3.7's ship date.
This proved the freeze was a real tool, not theater: it could be broken with
rationale, but had to be reset, not just ignored.

### Lessons (release-specific)

1. **Post-merge release-branch commits are an anti-pattern.** `0177410` and
   `15da63d` exist on `release/v0.3.6` but never reached main, creating
   orphaned state. Correct ritual: tag the merge, delete the branch, and
   commit any follow-up dogfood directly to main. This lesson hardened by
   v0.3.7 (but the pattern recurred — see cross-cutting section).
2. **RFC-driven scope with adversarial triage works.** All six items passed
   the filter *"driver is external signal or own-eyes bug, not owner
   restlessness."* Explicitly-rejected anti-patterns provided a reusable
   decision audit trail.
3. **The 90-day freeze is a real tool.** Being deliberately breakable (with
   rationale) and requiring a clock reset (not silent extension) made it a
   genuine constraint rather than cargo cult.
4. **AGENTS.md-canonical pivot reduced maintenance surface.** Five adapters
   collapsed to one-line shims. The shim pattern ("emit `See AGENTS.md` when
   co-enabled, inline standalone") became the template for future vendor
   decisions.
5. **Vendor deprecation deadlines force ship dates.** Gemini CLI sunset
   (2026-06-18) and Linux Foundation AGENTS.md adoption (2025-12) anchored
   the entire timeline. Clear external signals beat internal priority
   debates.

---

## [0.3.7] — 2026-06-10

### Scope

Extended AGENTS.md with a multi-agent Basic-Memory-aware persistent knowledge
section, using a vendor-neutral `[memory]` config (default-on for inbound read
guidance, offsetting v0.3.6's opt-in `[promotion]` outbound writes).

### Timeline

| Event | When |
| --- | --- |
| Branch created (~3 days after v0.3.6 merge) | 2026-06-07 |
| First commit on branch (`657d46d` backlog doc) | 2026-06-07 23:52:02 |
| Feature commit (`bebd2e4`) | 2026-06-10 18:34:11 |
| Merged to `main` (`59f2fe2` PR #10) | 2026-06-10 19:14:08 |
| PyPI published | 2026-06-10 (inferred) |

### Commits

**Merge commit on main:** `59f2fe2` — *Merge pull request #10 from
liyoncso-Theone/release/v0.3.7*

**Commits on branch that landed on main:**

| SHA | Subject |
| --- | --- |
| `657d46d` | docs(backlog): record v0.3.6 design side-effects for v0.3.7+ consideration |
| `bebd2e4` | feat: v0.3.7 — AGENTS.md BM-aware Session Start Protocol |
| `59d1113` | chore: complete v0.3.6 .gitignore migration on dogfood repo + sync regen |

**Orphan / cherry-picked commits:** none recorded at the time of writing.
However: see cross-cutting section — the *pattern* of committing to
`release/v0.3.7` after merge is the same trap as v0.3.6, and is explicitly
called out as ongoing risk.

### Scope summary

v0.3.7 delivered multi-agent persistent knowledge integration by extending
**AGENTS.md** — the cross-agent baseline used since v0.3.0.

Motivated by a laptop-side Claude session's RFC
(`docs/v0.3.6-rfc-agents-md-bm-aware.md`, filed 2026-06-10 after a
SessionStart-hook post-mortem): vibe-state-cli's AGENTS.md template is already
the cross-agent equivalent of a SessionStart hook, so making it
knowledge-aware reaches all agents (Claude, Codex, Antigravity, Cursor, ...)
in one change — higher leverage than any Claude-specific hook fix.

What shipped:

- **`vibe sync` regenerates AGENTS.md with a `## Persistent Knowledge — QUERY
  BEFORE RECALL` section**, placed between `## Session Start` and
  `## Workflow`. Tells every agent that reads AGENTS.md to query the
  configured knowledge layer before answering recall questions
  ("what did we decide", "where did we leave off").
- **New `[memory]` config section** in `.vibe/config.toml`, symmetric to
  v0.3.6's `[promotion]`:
  - `enabled` (default `true`) — flip to `false` to skip the section entirely.
  - `target` (default `"basic-memory"`) — `"obsidian"`, `"logseq"`, etc. fall
    back to a vendor-agnostic stub instead of leaking BM specifics.
  - `projects` (default `[]`) — empty list renders a generic "query whichever
    projects you find" instruction; non-empty list renders explicit project
    bullets. RFC originally proposed `["personal", "methodology"]`; adjusted
    to `[]` so pip-installed non-owner users don't see owner-private project
    names in their auto-generated AGENTS.md.
- **Cold-start performance caveat** in the template — tells agents the first
  BM query may take 30+ seconds on Windows (the exact symptom that motivated
  the RFC), caps per-query timeouts at ~5 seconds, and treats slow as
  unavailable.
- **Concrete fallback baseline** — when BM is offline / MCP not registered /
  query times out, the template names `.vibe/state/*.md` as the explicit
  baseline (*not* "proceed without it"), specifies the warning shape
  `⚠ Basic Memory unavailable — using .vibe/state only`, and prohibits retry
  loops and blocking.

10 new tests; 283 total passing.

### Process notes (honest)

**Strategic break of the 90-day freeze.** v0.3.6 declared a freeze through
2026-09-08. v0.3.7 broke it on day 3 because the owner needed multi-agent BM
integration for active dogfood work. The break was made deliberately, with
written rationale, and the freeze clock was reset to start from v0.3.7's
ship date (now → 2026-09-08 from 2026-06-10).

**First complete `[[cross-team-dispatch-via-rfc]]` loop.** This repo's first
two-document closure of a cross-session dispatch:

1. **Laptop-side Claude** wrote `docs/v0.3.6-rfc-agents-md-bm-aware.md`
   directly into the target repo's `docs/` after a SessionStart-hook
   debugging session. Made no code changes. Handed the decision to the owner.
2. **Main-dev session** (this machine) processed the RFC, chose Plan A with
   adjustments, ran 4-reviewer + synth adversarial review (verdict
   SHIP-WITH-FOLLOWUP, confidence 0.82), and committed.
3. Main-dev session then wrote
   `docs/v0.3.6-rfc-agents-md-bm-aware-RESPONSE.md` next to the original RFC
   to close the dispatch loop.

Both documents now form the audit trail; future contributors can reconstruct
the decision chain without session access. The pattern is portable and now
documented as a methodology.

**Two BLOCK verdicts refuted.** Adversarial reviewers 3 and 4 voted BLOCK.
Synthesizer refuted both with grounded reasoning:

- *"`_write_file` destroys user content"* — conflated AGENTS.md with state
  files. AGENTS.md has been fully managed by design since v0.3.0; not a
  regression.
- *"Default-on is unsafe"* — explicit owner choice from Plan A in the RFC.
  Safety nets: fallback prose, `[memory].enabled = false` opt-out,
  `projects = []` OSS-safe default.

Both concerns were recorded as v0.3.8 P2 backlog (over-broad MCP wording,
silent config-load exception). **BLOCK was treated as a trigger to add safety
nets, not as veto.**

**Implementation discovered the RFC underestimate.** The RFC predicted ~15
lines of template string. Actual implementation: `MemorySection` config
class + `_build_memory_section` + `_build_basic_memory_section` helpers + 10
new tests, roughly 150 lines. RFC didn't account for vendor-neutral `target`
dispatch and OSS-safe empty-projects rendering. Worth noting for future RFC
sizing.

**Backlog carries forward.** v0.3.7 P2 items (over-broad MCP wording, silent
config-load exception) + v0.3.6's two still-open items
(`install_post_commit_hook` marker auto-replace, `vibe sync` activity-log gap
after hook cursor advance) all recorded in `.vibe/state/tasks.md` for v0.3.8+.

### Lessons (release-specific)

1. **Cross-team dispatch-via-RFC is a viable methodology.** Laptop session
   writes RFC into target repo's `docs/`, makes no code changes, hands
   decision to owner. Main-dev session reviews, decides, executes, writes
   RESPONSE document. No real-time coordination required; audit trail is
   permanent. Requirement: both files must ship side-by-side, and the
   RESPONSE must accompany the ship (no closure signal = loop stays open).
2. **Adversarial review on conscious design choices.** Two reviewers voting
   BLOCK did not halt ship. Their concerns triggered concrete safety nets
   (fallback prose, OSS default `projects = []`, performance caveat). The
   design choice itself (default-on for `[memory]`) was upheld as the
   owner's explicit decision. Documented in CHANGELOG so future readers
   know this was deliberate, not accidental.
3. **Philosophy asymmetry is powerful.** `[promotion]` defaults off (outbound
   writes are user-initiated); `[memory]` defaults on (inbound read guidance
   on session start). Same config schema, opposite defaults, justified by
   usage pattern. Violates "least surprise" in isolation, but enables the
   cross-agent assumption: if you're using vibe-state-cli for multi-agent
   collaboration, you want a knowledge layer visible to all agents by
   default. Documented so it can be re-evaluated, not re-debated.
4. **Cold-start performance as a release driver.** The 30s+ Windows cold-start
   wasn't fixed (out of scope); it was *named* in the template so every agent
   reading AGENTS.md adapts (cap at 5s, treat slow as unavailable). Sometimes
   the bug is in the integration assumption, not in your code.
5. **Freeze breaks need reset clocks.** v0.3.6's freeze was broken deliberately
   and the clock was reset (90 days from v0.3.7 ship, not from v0.3.6 ship).
   A freeze without a reset clock becomes easier to break next time. Reset
   discipline preserves the constraint.

---

## Patterns Across Releases

This section captures the cross-cutting truths that no single release section
fully expresses.

### Recurring anti-patterns

#### 1. Commits on post-merge dead release branches, never cherry-picked to main

**Occurred in:** v0.3.6, and the pattern repeated on v0.3.7's branch with
in-flight commits that may not all reach main.

**Concrete evidence on v0.3.6:**

```
c3c9009  Merge pull request #9 from liyoncso-Theone/release/v0.3.6   23:21
0177410  feat: add new skills for vibe commands ...                  23:27   ← orphan
15da63d  chore: dogfood v0.3.6 on self — adapter regen ...           23:49   ← orphan
```

`0177410` and `15da63d` were committed to `release/v0.3.6` **after** the
merge to main. They were never cherry-picked. When the branch is deleted,
those commits vanish.

**Root cause:** The release ritual was incomplete. Once the merge PR closed,
the branch was *mentally* done, so subsequent dogfood work (adapter
regeneration, state file migration on self) got committed there as
convenience. The branch wasn't deleted, so it stayed psychologically *live*.

**Why it kept happening:** This became a "recovery dance" — a routine that
felt like a normal recovery path because nothing in the ritual stopped it.
The maintainer's own framing was honest: *"I keep stepping in the same hole;
my own normalized recovery dance is the misleading guide that lets me keep
stepping in it."*

**Eventual fix:** This document is the salvage operation. The branches will
be deleted once this institutional memory is committed. Going forward, the
fix is **not** "be more careful" — it is to **delete the release branch
immediately after merge**, so the option to commit there structurally does
not exist. AGENTS.md's release ritual section should encode this.

#### 2. Incomplete release ritual — branches linger after merge

**Occurred in:** v0.3.5, v0.3.6, v0.3.7.

**Root cause:** No explicit post-merge step was defined. The merge landed on
main, the maintainer moved on, and the branch sat in an ambiguous state for
days. That ambiguity is what enabled anti-pattern #1.

**Eventual fix:** Process change pending. Two valid options:

1. **Delete the release branch immediately after merge.** Simpler. Removes
   the option to commit there.
2. **Keep the branch but mark it frozen** — README banner + pre-commit hook
   that blocks new commits. Preserves history at branch tip but enforces
   read-only.

Option 1 is preferred. These branches will be deleted once this document
ships.

### Methodology evolution

#### Adversarial review before commit

**First appeared in:** v0.3.6.

**Shape:** Before any release commit, 4 independent reviewers + 1 synthesizer
run in parallel. Verdict framework: **SHIP** (go), **SHIP-WITH-FOLLOWUP**
(go + backlog items), **BLOCK** (don't ship). BLOCK is a trigger to add
safety nets and document, not an automatic veto. Disagreement is captured in
the CHANGELOG with confidence scores and resolution rationale.

**Used in:** v0.3.6 (SHIP, 0.92), v0.3.7 (SHIP-WITH-FOLLOWUP, 0.82, two BLOCK
votes refuted with reasoning).

#### Cross-team dispatch-via-RFC

**First appeared in:** v0.3.7.

**Shape:**

1. One Claude session (the *sending* session, often on a different machine)
   writes a full RFC directly into the target repo's `docs/` folder. Makes
   no code changes. Modifies no existing files.
2. Target repo's maintainer (the *receiving* session, often the
   owner/main-dev environment) receives the RFC naturally when they next
   open the project. Adopts, adjusts, or rejects.
3. **Mandatory:** when adopting, the maintainer writes a `*-RESPONSE.md`
   document next to the original RFC to close the dispatch loop.
4. Both RFC + RESPONSE form the permanent audit trail.

**Established artifacts:** `docs/v0.3.6-rfc-agents-md-bm-aware.md` (RFC) +
`docs/v0.3.6-rfc-agents-md-bm-aware-RESPONSE.md` (response). Pattern is now
portable for multi-AI workflows.

#### 90-day post-ship code freeze

**First appeared in:** v0.3.6.

**Shape:** After a release ships, zero `src/` commits for 90 days unless a P0
user-filed bug surfaces.

- **Hard-stop signals** (any one extends freeze indefinitely): Claude Code
  ships first-party cross-tool memory sync; another 30 days of zero
  user-filed bugs; a contributor proposes a 10th adapter.
- **Soft-stop signals** (any two extend freeze): PyPI downloads plateau below
  250/month; maintainer hasn't committed in 60 days while still using daily;
  maintainer reaches for an external knowledge store instead of
  `vibe sync --note`.

**Reset rule:** When deliberately broken (as v0.3.7 broke v0.3.6's freeze on
day 3 for multi-agent urgency), the clock resets from the new release's ship
date, not continued from the previous one. Breaking without resetting invites
decision fatigue on when to break again.

#### Opinionated default vs vendor-neutral mechanism

**First appeared in:** v0.3.6 (`[promotion]`), refined in v0.3.7 (`[memory]`).

**Shape:** Feature uses a vendor-neutral subprocess / config architecture
that can accommodate multiple backends (`obsidian`, `logseq`, raw-file,
etc.), but the **default** target is chosen based on the maintainer's actual
use case (`basic-memory` CLI). Users without that backend disable the feature
or swap config target.

**Asymmetry rule:** *Outbound* writes (like `[promotion]`) default OFF —
user-initiated actions deserve opt-in. *Inbound* read guidance (like
`[memory]`) defaults ON — assumed for vibe-managed multi-agent setups,
where a knowledge layer is the whole point of the tool. Documented in
CHANGELOG so the asymmetry is conscious, not accidental.

### Meta-lessons

1. **Incomplete rituals become normalized workarounds.** The maintainer
   stepped into the dead-branch trap three times (v0.3.5, v0.3.6, v0.3.7)
   because no explicit post-merge ritual was defined. The absence created a
   vacuum that the maintainer's own convenience filled. The fix is not "be
   more careful" — it is **write the ritual down and enforce it
   structurally** (auto-delete branch on merge, or fail-closed hook on
   frozen branches).
2. **Adversarial review catches real issues even on small releases.** In
   v0.3.7, four reviewers independently flagged that the original RFC's
   "proceed without it" fallback was dangerous given the 30s cold-start
   that motivated the RFC. Two voted BLOCK. The synth refuted the BLOCK
   verdicts as unsound — but the P1 follow-ups (fallback prose, asymmetry
   documentation) made the ship safer. Adversarial review should be
   standard before every release, not optional.
3. **Cross-team dispatch via RFC closes loops that would otherwise stay
   open.** The laptop session's architectural insight (AGENTS.md is already
   the cross-agent hook) + the main-dev session's adjustments (OSS safety
   net, fallback prose) + the audit trail (RFC + RESPONSE) created
   institutional memory that neither session could have produced alone. The
   pattern works because both parties write into the same repo; the RFC is
   a commit-free handoff.
4. **The 90-day freeze is a forcing function for distinguishing real demand
   from internal restlessness.** v0.3.6 shipped with a freeze; v0.3.7 broke
   it after 3 days because the multi-agent integration need was genuinely
   urgent. The freeze didn't prevent v0.3.7 — it forced the explicit
   question: *"do I actually need to ship this now, or am I bored?"* Owner
   answered "actually need" and reset the clock. This discipline prevents
   feature creep during observation periods.
5. **Vendor-neutral mechanism + opinionated default is the scalable
   compromise.** Hardcoding `basic-memory` would alienate users with other
   setups. Pure mechanism with no default would force users to configure
   from zero. The hybrid (`target = "basic-memory"` by default, swap via
   config) lets the maintainer's preferences guide UX while leaving escape
   hatches. The honesty about which is default and which is mechanism lives
   in CHANGELOG.
6. **Deferred items deserve explicit backlogs with rationale.** v0.3.6's
   RFC section on rejected anti-patterns and v0.3.7's `tasks.md` both
   record *what was considered and rejected* (no `basic_memory` adapter, no
   auto-pull on `vibe start`, no 10th adapter, no MCP server yet) **with
   reasoning**. This saves the next contributor from rediscovering the same
   dead ends. The rationale is as valuable as the decision itself.

---

## What this means for future releases

The dead-branch trap is the single most important pattern to fix
structurally, because it is the one anti-pattern that recurred across all
three releases and is the one this document exists to salvage from.

**Concrete next steps** — to be added to `AGENTS.md`'s release ritual:

1. **Delete the release branch immediately after merge.** No exceptions.
   Dogfood work, adapter regen, state migration, all of it gets committed
   directly to `main` as fresh commits — not back to a dead branch.
2. **Treat the merge commit as the freeze boundary.** Once `main` carries
   the merge, the release is shipped. Any `release/*` branch that lingers
   past that point is a smell, not a workspace.
3. **The post-merge ritual is part of "shipped".** A release is not
   "shipped" until: (a) merged to main, (b) tagged on main, (c) PyPI
   published, **(d) release branch deleted**, (e) freeze clock started.
   Missing (d) is what caused this whole document to exist.
4. **Keep adversarial review mandatory before every release commit.** It
   has paid for itself twice (v0.3.6, v0.3.7). The cost (~30 min of
   parallel reviewer runs) is dwarfed by the cost of shipping unresolved
   safety gaps.
5. **Keep cross-team dispatch-via-RFC as the multi-session methodology.**
   Both files (RFC + RESPONSE) must ship together. No closure document,
   no closed loop.
6. **Keep the 90-day freeze, with reset clocks on breaks.** Breaking is
   allowed; silent extension is not.

Once these are encoded in `AGENTS.md`, the recovery dance becomes
structurally impossible — not just "discouraged."
