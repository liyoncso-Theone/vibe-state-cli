# 任務清單

> 完成後標記 `[x]`，嚴禁刪除。超過 30 天未動標記 `[~]`。

## 待辦（freeze 期間 hold；v0.3.7+ 候選）

- [ ] **install_post_commit_hook 偵測舊 marker 內容並自動替換**
  - 背景：v0.3.5 改了 hook script（同步 → 背景 `(... &)`），但 `install_post_commit_hook` 看到既有 marker 就 return "already"，舊用戶升級拿不到新 hook。v0.3.6 沒處理。
  - 結構性影響：未來任何 hook script 變更都會被同一道牆擋住。
  - 修法：偵測 marker 區塊內容，若不含 `&)` 視為過期 → 刪舊區塊重灌。
  - 規模：~20 行 + 1 個測試。
  - 為何延後：實際受影響 user base ≈ 0–1 人；90 天 freeze 內不動。
  - 建單日：2026-05-08

- [ ] **`vibe sync` 跳過 hook 已掃過的 commit → current.md activity log 出現空缺**
  - 背景：v0.3.6 為了修「兩檔無限循環」bug，把 post-commit hook 改成「只移 `.sync-cursor`、不寫 `current.md`」。
  - 副作用：使用者親手跑 `vibe sync` 時，`.sync-cursor` 已被 hook 偷偷推到最新 HEAD → sync 判定「沒新 commit」→ `current.md` activity log 跳過那一段。
  - 影響：AI 仍可看 git log（ground truth），人類可讀的 activity log 出現空缺。**功能不壞，可讀性損失。**
  - 觀察到的情境：v0.3.6 merge 後，自己跑 `vibe sync` 看不到 v0.3.6 那串 commit 被寫入 `current.md`。
  - 可能修法：(a) hook 改成寫精簡單行記號到 `current.md` 末尾（重新引入循環風險）；或 (b) `vibe sync` 顯式版本加 `--force` 旗標、繞過 cursor 直接 dump 區間活動。
  - 為何延後：90 天 freeze；user base = 1（owner 自己）；不影響 AI 上下文。等 freeze 結束評估 (a) vs (b)。
  - 建單日：2026-06-07
