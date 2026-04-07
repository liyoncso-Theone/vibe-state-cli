# Current State

## 最後更新

2026-04-07 — CLI 精簡為 5 個指令，全部測試通過

## 當前進度摘要

完成 Phase 0~3。CLI 從 8 個指令精簡為 5 個（init/start/sync/status/adapt）。compact 收入 sync --compact，close 收入 sync --close，reopen 改為 init --force。63 個測試全部通過。舊設計文件已廢棄刪除。

## 已完成模組

- Phase 0：git、pyproject.toml、套件結構、tests、README、CI、LICENSE
- Phase 1：scanner、lifecycle、config、Jinja2 模板、git_ops、state、compactor
- Phase 1 CLI：5 指令（init/start/sync/status/adapt）+ sync --compact/--close 子功能
- Phase 2：7 adapter（AGENTS.md/Claude/Cursor/Copilot/Windsurf/Cline/Roo）+ safety
- Phase 3：63 測試、i18n（zh-TW）、LICENSE、沙盒測試、bug 修復（5 項）
- 精簡重構：8 指令 → 5 指令

## 未解決問題

- Cursor 是否原生支援 AGENTS.md 仍未確認
