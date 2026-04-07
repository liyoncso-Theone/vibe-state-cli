# Task List

## 待辦事項

> 格式：- [ ] [任務描述]（完成後標記為 [x]，嚴禁刪除任何項目）
> 擱置任務標記為 [~]，由 vibe compact 自動處理

### Phase 0：專案骨架

- [ ] 初始化 git repo + .gitignore
- [ ] 建立 pyproject.toml（hatchling + uv，entry point: vibe）
- [ ] 建立 src/vibe_state/ 套件結構（cli.py、core/、adapters/、templates/、config.py、safety.py）
- [ ] 建立 tests/ 目錄與 pytest 設定
- [ ] 建立 README.md（英文，含 quickstart）
- [ ] 設定 GitHub Actions CI（ruff + mypy + pytest，Linux + Windows + macOS）

### Phase 1：核心 CLI

- [ ] 實作 ScanResult dataclass + scanner.py（偵測鏈：lockfile → .gitignore → 副檔名 → 互動選擇）
- [ ] 實作 lifecycle.py — 狀態機（.lifecycle 讀寫 + 轉換檢查 + 報錯）
- [ ] 實作 config.py — config.toml Schema（Pydantic）+ 載入 + 版本遷移
- [ ] 實作 Jinja2 模板系統（VIBE.md + state/*.md + skills/*.md）
- [ ] 實作 `vibe init` — 掃描 + 生成 .vibe/ + 互動選擇 adapter + 按需 emit + lifecycle→READY
- [ ] 實作 git_ops.py — 封裝 git status/diff/log + .sync-cursor 追蹤
- [ ] 實作 state.py — .vibe/state/ 檔案讀寫驗證
- [ ] 實作 `vibe start` — 載入 state/ + git 校驗 + auto-compact + Rich 摘要 + lifecycle→ACTIVE
- [ ] 實作 compactor.py — markdown-it-py AST 解析 + 歸檔 [x] + 擱置 [~]（>stale_task_days）
- [ ] 實作 `vibe compact` — 執行 compactor + 回報行數對比
- [ ] 實作 `vibe sync` — git 附加模式 + .sync-cursor 更新 + C.L.E.A.R. 空白模板
- [ ] 實作 `vibe close` — 最終 sync + compact + 回顧模板生成 + lifecycle→CLOSED
- [ ] 實作 `vibe reopen` — lifecycle CLOSED→ACTIVE + 移除結案標記
- [ ] 實作 `vibe status` — 任何狀態可用，Rich 格式輸出

### Phase 2：全量 Adapter 系統

- [ ] 實作 AdapterBase ABC（detect/emit/clean/validate + REQUIRED_FIELDS）
- [ ] 實作 safety.py — 快照比對 + 備份 + dry-run 安全機制
- [ ] 實作 registry.py — 自動發現 + 按需執行啟用的 adapter
- [ ] 實作 `vibe adapt` 指令（--add/--remove/--list/--sync/--confirm/--dry-run）
- [ ] 實作 AGENTS.md adapter（純 Markdown，≤32KiB 驗證）
- [ ] 實作 Claude Code adapter（CLAUDE.md + .claude/rules/*.md + 含 @AGENTS.md 去重邏輯）
- [ ] 實作 Cursor adapter（.cursor/rules/*.mdc，驗證 alwaysApply/globs/description）
- [ ] 實作 Copilot adapter（.github/copilot-instructions.md + instructions/，驗證 applyTo）
- [ ] 實作 Windsurf adapter（.windsurf/rules/*.md，驗證 trigger enum）
- [ ] 實作 Cline adapter（.clinerules/*.md，驗證 paths list）
- [ ] 實作 Roo Code adapter（.roo/rules/*.md，純 Markdown）

### Phase 3：品質與發布

- [ ] 撰寫單元測試（scanner、compactor、lifecycle、git_ops、state、config、safety）
- [ ] 撰寫 adapter 測試（每個 adapter 的 emit + validate + 錯誤 context 測試）
- [ ] 撰寫 CLI 整合測試（CliRunner，含狀態機轉換測試）
- [ ] 跨平台 CI（Linux + Windows + macOS）
- [ ] 撰寫 mkdocs-material 文件站（英文 + zh-TW quickstart）
- [ ] i18n：`vibe init --lang zh-TW`
- [ ] 發布至 PyPI（pipx install vibe-state-cli）

### Phase 4：進階功能

- [ ] MCP Server（`vibe serve`）— FastMCP，Resources: state/*，Tools: sync/compact/status
- [ ] VS Code 擴充套件 — sidebar 顯示 VIBE 狀態
- [ ] 自訂模板覆寫（.vibe/custom_templates/）
