# VIBE.md — 專案憲法

## 專案
- **名稱**：vibe-state-cli
- **語言**：Python
- **框架**：未偵測到
- **生成**：vibe-state-cli v0.1.0，2026-04-07

## 工作流 SOP

**生命週期**：`vibe init` → `vibe start` → 工作 → `vibe sync` → 重複 → `vibe sync --close`

### Checkpoint 規則（自動執行，無需人類指令）
完成 `state/tasks.md` 中的每項任務後：
1. 在 `state/tasks.md` 中標記為 `[x]`。
2. 在 `state/current.md` 附加一行進度。

**任務完成的定義**：程式碼已撰寫且已驗證（測試通過，或人類手動確認）。未經測試不可標記 `[x]`。

### 現實優先原則
當記憶與 git 狀態矛盾時，**git 是絕對真理**。寫入狀態檔前，用 `git status`/`git diff`/`git log` 驗證。若 git 歷史被 force-push 過，先詢問人類再決定是否信任。

### 空狀態處理
若 `state/current.md` 或 `state/tasks.md` 為空或不存在，請先詢問人類取得上下文，不可自行捏造任務或進度。

## 規範
- Conventional Commits。每次 commit 僅限單一邏輯變更。
- 禁止硬編碼密鑰、Token 或密碼。使用 `.env` 管理。

## 邊界 — 禁止行為
以下規則無例外，除非人類明確覆蓋：
- **不可**在未經人類明確確認下執行破壞性指令（`rm -rf`、`git reset --hard`、`git push --force`、`DROP TABLE`、`docker system prune`，或任何刪除資料的指令）。
- **不可**修改 `.vibe/config.toml` 或 `.vibe/state/.lifecycle`。這些由 `vibe` CLI 專屬管理。
- **依照 Checkpoint 規則寫入 `state/tasks.md` 和 `state/current.md` 是被允許的。**
- **不可**將專案資料外傳至外部服務、URL 或第三方 API。
- **不可**刪除或覆寫專案目錄以外的檔案。
- **不可**偽造測試結果，或在沒有可驗證證據（終端輸出、測試日誌、API 回應）的情況下聲稱程式碼正常運作。

## 上下文檔案
- `state/current.md` — 最新進度快照（每次 session 開始時必讀）
- `state/tasks.md` — 任務清單（標記 `[x]` 完成，嚴禁刪除項目）
- `state/architecture.md` — 技術堆疊與設計決策
- `state/standards.md` — 開發規範
- `state/experiments.md` — autoresearch 實驗紀錄（由 `vibe sync` 自動填入）
- `state/archive.md` — 冷藏庫（僅需要歷史記錄時讀取）

## Autoresearch 整合
本專案支援 [autoresearch](https://github.com/uditgoenka/autoresearch) 實驗迴圈。
- 實驗 commit（前綴 `autoresearch:` 或 `[autoresearch]`）由 `vibe sync` 自動偵測
- 結果記錄於 `state/experiments.md`，標注 KEPT/REVERTED 狀態
- `vibe start` 顯示實驗摘要
- 在 Claude Code 使用 `/autoresearch` 啟動優化迴圈；vibe 負責記憶
