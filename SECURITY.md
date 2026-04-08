# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in vibe-state-cli, please report it responsibly:

1. **Do NOT** open a public GitHub issue for security vulnerabilities
2. Email: [security@vibe-state-cli.dev] (or use GitHub's private vulnerability reporting)
3. Include: steps to reproduce, affected version, potential impact

We will respond within 48 hours and provide a fix timeline.

## Security Design

vibe-state-cli generates configuration files that AI coding agents read as instructions. This creates a unique attack surface:

### What we protect against

- **Prompt injection via project metadata**: User-controlled strings (project name, languages, frameworks) are sanitized — control characters stripped before entering templates.
- **Path traversal**: `state.py` validates all filenames stay within `.vibe/state/`. Writes use atomic temp-file + rename.
- **Destructive adapter operations**: `vibe adapt --remove` defaults to dry-run, requires `--confirm`. Backups are created before deletion.
- **Config corruption**: Malformed `config.toml` halts execution with user-friendly error. Pydantic validates all fields.
- **YAML frontmatter injection**: Adapter-specific validators check required fields after every `emit()`.

### What we instruct AI agents to follow

The generated `AGENTS.md` includes explicit boundary rules:

- Do not execute destructive commands without human confirmation
- Do not modify `.vibe/config.toml` or `.vibe/state/.lifecycle`

### Known limitations

- **AI compliance is not enforced**: AGENTS.md boundaries are instructions, not enforcement. An AI model may choose to ignore them.
- **File-level access**: Generated adapter files (CLAUDE.md, .cursor/rules/) are readable by anyone with project access. Do not put secrets in `.vibe/` files.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.3.x   | Yes       |
| 0.2.x   | No        |
| 0.1.x   | No        |
