# 更新日誌

本專案的所有重要變更都會記錄在這份文件中。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/)。

---

## [0.3.0] — 2026-04-08

### 新增

- **三層 adapter 輸出**：full（AGENTS.md）、slim（Claude/Gemini @import）、compact（Cursor/Windsurf/Cline/Roo/Copilot — 內嵌規則，不叫 AI 讀檔）
- **跨工具狀態同步**：`vibe sync` 和 `vibe start` 自動把壓縮摘要注入所有 adapter 設定檔
- **Claude Code Skills**：5 個 slash command（`/vibe-init` 到 `/vibe-adapt`）
- **Symlink/Junction 防護**：阻擋 symlink 和 Windows NTFS Junction 穿越
- **Advisory Lock**：跨平台 advisory lock 保護 CI 併發寫入
- **Windows retry**：防毒鎖檔時 `os.replace` 自動重試
- **Two-phase 遷移**：全部複製 → 驗證 → 才刪除原檔
- **0 rules 警告**：偵測到舊檔但無法抽取規則時，保留原檔不動
- **`constants.py`**：單一來源的預設 patterns（消除 lazy import）
- **`ConfigParseError`**：core 層拋例外，CLI 層捕捉退出

### 變更

- **移除 VIBE.md**：行為規則合併進 AGENTS.md
- **Bootstrap-not-embed**：adapter 指向 state/，compact 模式內嵌前 10 條 standards
- **Summary 是純資料**：不含「讀檔案 X」指令
- **Checkpoint 標示 best-effort**：AI 遵從率 ~40-60%，git log 才是 ground truth
- **Copilot 標示「摘要」**：支援表格誠實標示同步深度
- **Antigravity fallback**：GEMINI.md 含 compact body 給舊版 Gemini CLI
- **Skip-if-unchanged**：設定檔沒變就不寫，避免 git noise

### 移除

- VIBE.md 模板、供應鏈指紋、快照系統、可疑指令偵測、死欄位

### 修正

- Windows cp950 編碼修正
- Heading 匹配容忍 `###` 和多餘空白
- Code fence 支援 `~~~` 語法
- Lock file 不再刪除（防 race condition）

---

## [0.2.0] — 2026-04-07

### 新增

- **智慧遷移**：偵測既有 CLAUDE.md、AGENTS.md、.cursorrules，匯入規則不覆蓋原檔
- **使用者檔案保護**：adapter 跳過使用者已有的同名檔案
- **繁體中文文件**：完整 zh-TW README 和 USER-GUIDE

### 修正

- 首次 sync 的 diff_stat 從根 commit 計算
- 紅隊審查的三個防禦性修正
- Cursor adapter 輸出檔名修正（`vibe-standards.mdc`）
- AGENTS.md markdown 格式修正
- 全文件統一使用 `pipx`

---

## [0.1.0] — 2026-04-07

### 新增

- **5 個 CLI 指令**：`init`、`start`、`sync`、`status`、`adapt`
- **8 個內建 adapter**：AGENTS.md、Claude Code、Antigravity/Gemini、Cursor、Copilot、Windsurf、Cline、Roo Code
- **嚴格生命週期狀態機**：UNINIT → READY → ACTIVE → CLOSED
- **Autoresearch 整合**：自動偵測實驗 commit
- **i18n**：英文與繁體中文模板
- **安全機制**：原子寫入、路徑穿越防護、frontmatter 驗證、config 損壞停止
- **Token 效率**：Slim 模式、AST 壓縮、section 邊界裁切
- **自動化測試**，100% 覆蓋率

### 架構決策

- `state/` 目錄是 SSOT
- `vibe sync` 使用純 git 附加（廠商中立）
- CLI 模組化為 `commands/` 子套件
- `markdown-it-py` AST 壓縮
