# Publishing & Security Guide

## Before First Publish

### 1. PyPI Account Security
- [ ] Enable 2FA on pypi.org (mandatory)
- [ ] Set up **Trusted Publishers** (OIDC — no static API tokens): https://docs.pypi.org/trusted-publishers/
- [ ] Register defensive package names: `vibestate`, `vibe_state`, `vibe-state`

### 2. GitHub Repository Security
- [ ] Enable branch protection on `main` (require PR reviews, no direct push)
- [ ] Pin ALL GitHub Actions to commit SHA (already done in ci.yml)
- [ ] Enable Dependabot for dependency updates
- [ ] Enable secret scanning
- [ ] Restrict `GITHUB_TOKEN` permissions (already done: `contents: read`)

### 3. Signing
- [ ] Consider Sigstore signing for releases: https://docs.pypi.org/attestations/

## Publishing a Release

```bash
# 1. Update version in src/vibe_state/__init__.py and CHANGELOG.md
# 2. Commit + tag
git tag v0.1.0
git push origin v0.1.0

# 3. Build
python -m build

# 4. Upload (prefer Trusted Publishers over twine)
# If using twine:
twine upload dist/* --skip-existing
```

## Incident Response

If the PyPI account is compromised:
1. Immediately contact PyPI support: https://pypi.org/security/
2. Yank all compromised versions: `pip install --no-cache-dir vibe-state-cli==<safe_version>`
3. Post a GitHub Security Advisory
4. Notify users via README banner

## Threat Model

| Threat | Mitigation |
|--------|-----------|
| PyPI account takeover | 2FA + Trusted Publishers (no static tokens) |
| Malicious PR | Branch protection + required reviews |
| GitHub Actions injection | Pinned to commit SHA + minimal permissions |
| Dependency vulnerability | Dependabot + `pip-audit` in CI |
| Typosquatting | Register defensive names |
