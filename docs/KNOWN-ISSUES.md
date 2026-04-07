# Known Issues (v0.1.0-beta)

## 1. Overzealous content filtering in adapter output

**File**: `src/vibe_state/adapters/base.py`

`_is_suspicious_instruction()` uses a keyword blacklist (`rm -rf`, `http://`, `system(`, etc.) that silently drops matching lines from `standards.md` before writing adapter files. This means legitimate rules like:

- `- Never use rm -rf in scripts`
- `- Internal API endpoint: http://10.0.0.1`

...get silently removed, which is counterproductive — the AI never sees the safety rule.

**Planned fix for v0.2.0**: Replace blacklist with context-aware filtering (e.g., only flag lines that are *imperative instructions to execute*, not *descriptions of what to avoid*).

## 2. Over-sanitization of project metadata

**File**: `src/vibe_state/adapters/base.py`

`_sanitize()` strips `#`, `"`, `'`, `` ` `` from all user-controlled strings. This breaks:

- Language names: `C#` → `C`, `F#` → `F`
- Project names with quotes: `AI "Oasis" API` → `AI Oasis API`

**Planned fix for v0.2.0**: Only escape characters that are dangerous in the specific output context (YAML frontmatter vs Markdown body), not blanket-strip everything.
