# 任務清單

> 完成後標記 `[x]`，嚴禁刪除。超過 30 天未動標記 `[~]`。

## 待辦（v0.3.6 候選）

- [ ] **install_post_commit_hook 偵測舊 marker 內容並自動替換**
  - 背景：v0.3.5 改了 hook script（同步 → 背景 `(... &)`），但 `install_post_commit_hook` 看到既有 marker 就 return "already"，舊用戶升級拿不到新 hook。
  - 結構性影響：未來任何 hook script 變更都會被同一道牆擋住。
  - 修法：偵測 marker 區塊內容，若不含 `&)` 視為過期 → 刪舊區塊重灌。
  - 規模：~20 行 + 1 個測試。
  - 為何延後：v0.3.5 剛 ship、實際受影響 user base ≈ 0–1 人、連發 v0.3.6 看起來像沒打磨好。等實際抱怨或下次要動 hook 時一起處理。
  - 建單日：2026-05-08
