# 更新日誌

本專案的所有重要變更都會記錄在這份文件中。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/)。

---

## [0.1.0] — 2026-04-07

### 新增

- **5 個 CLI 指令**：`init`、`start`、`sync`、`status`、`adapt`
- **8 個內建 adapter**：AGENTS.md、Claude Code、Antigravity/Gemini、Cursor、Copilot、Windsurf、Cline、Roo Code
- **嚴格生命週期狀態機**：UNINIT → READY → ACTIVE → CLOSED，`init --force` 可復原
- **智慧遷移**：偵測既有的 CLAUDE.md、AGENTS.md、.cursorrules，匯入規則到 .vibe/state/standards.md，不覆蓋原檔
- **Autoresearch 整合**：自動偵測 git log 中的實驗 commit，記錄到 `state/experiments.md`，pattern 可自訂
- **i18n**：英文與繁體中文模板
- **安全機制**：
  - 原子寫入（temp + os.replace）
  - 指數退避檔案鎖（失敗時安全停止，不強行闖入）
  - 路徑穿越防護
  - Adapter 快照 + 備份（3 份）+ 預設 dry-run
  - 輸入消毒
  - 各 adapter 的 frontmatter 驗證
  - config 損壞時停止執行（不偷偷用預設值）
  - 供應鏈指紋警告（偵測 clone 來的 .vibe/）
- **Token 效率**：
  - Slim 模式（AGENTS.md 共存時自動去重）
  - AST 語義壓縮（markdown-it-py，不切斷 code fence）
  - 依 section 邊界裁切（不破壞文件結構）
  - 無變更時跳過空 sync 區塊
- **VIBE.md 憲法**：
  - Checkpoint 規則（含任務完成定義）
  - 現實優先原則（含 force-push 警告）
  - 明確的邊界框架（禁止行為）
  - 所有 adapter 輸出包含 Session Start 指令
- **207 個自動化測試**，100% 覆蓋率

### 架構決策

- VIBE.md 是「憲法」（行為準則，極少修改），不是 SSOT
- `state/` 目錄是真正的 SSOT（可變的專案狀態）
- `vibe sync` 使用純 git 附加（不依賴 LLM，廠商中立）
- Adapter 從 `VIBE.md + state/ + config.toml` 組合衍生
- CLI 模組化為 `commands/` 子套件（cmd_init、cmd_start 等）
- `markdown-it-py` AST 用於 section 邊界感知壓縮

### 支援平台

- Claude Code CLI + VS Code 擴充
- Google Antigravity IDE + Gemini CLI
- Cursor
- GitHub Copilot（VS Code + GitHub.com）
- Windsurf（Codeium）
- Cline
- Roo Code
- OpenAI Codex CLI（透過 AGENTS.md）
- 任何支援 AGENTS.md 的工具（Zed、Warp、Aider、Devin 等）
