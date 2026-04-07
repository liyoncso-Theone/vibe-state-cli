# 更新日誌

本專案的所有重要變更都會記錄在這份文件中。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/)。

---

## [0.1.0] — 2026-04-07

### 新增
- **5 個 CLI 指令**：`init`、`start`、`sync`、`status`、`adapt`
- **8 個內建 adapter**：AGENTS.md、Claude Code、Antigravity/Gemini、Cursor、Copilot、Windsurf、Cline、Roo Code
- **嚴格生命週期狀態機**：UNINIT → READY → ACTIVE → CLOSED，`init --force` 可復原
- **Autoresearch 整合**：自動偵測 git log 中的實驗 commit，記錄到 `state/experiments.md`
- **i18n**：英文與繁體中文模板
- **安全機制**：
  - 原子寫入（temp + os.replace）
  - 檔案鎖定（防止並發存取）
  - 路徑穿越防護
  - Adapter 快照 + 備份（3 份）+ 預設 dry-run
  - 輸入消毒（過濾 \n、#、"、'、`）
  - 各 adapter 的 frontmatter 驗證
  - config 欄位驗證（Pydantic）
  - UTF-8 錯誤友善處理
- **Token 效率**：
  - Slim 模式（AGENTS.md 共存時自動去重）
  - 安全規則智慧去重
  - 記憶壓縮：歸檔 [x]、擱置 [~]、裁切 current.md >300 行、archive.md 上限 500 行
  - 無變更時跳過空 sync 區塊
- **VIBE.md 憲法**：
  - Checkpoint 規則（含任務完成定義）
  - 現實優先原則（含 force-push 警告）
  - 空狀態處理指令
  - 明確的邊界框架（禁止行為，無例外條款）
  - Autoresearch 整合區塊
  - 所有 adapter 輸出包含 Session Start 指令
- **68 個自動化測試** + 10 個場景測試（全部通過）

### 架構決策
- VIBE.md 是「憲法」（行為準則，極少修改），不是 SSOT
- `state/` 目錄是真正的 SSOT（可變的專案狀態）
- `vibe sync` 使用純 git 附加（不依賴 LLM，廠商中立）
- Adapter 從 `VIBE.md + state/ + config.toml` 組合衍生
- `_build_common_body(slim=True)` 消除跨檔案 token 重複
