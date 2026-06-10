# 任務清單

> 完成後標記 `[x]`，嚴禁刪除。超過 30 天未動標記 `[~]`。

## 待辦（freeze 期間 hold；v0.3.8+ 候選）

> v0.3.7 ship 後 freeze 從 2026-06-10 重新起算 → 2026-09-08 解除

### v0.3.7 adversarial review P2 follow-ups

- [ ] **`_build_basic_memory_section` template wording 太絕對**
  - 現況：「MCP-accessible from any agent」過度承諾。Cursor / Cline / Codex 使用者透過 v0.3.6 shim 讀 AGENTS.md 時不一定有 BM MCP 連著。
  - 修法：改成「MCP-accessible from agents with the `basic-memory` MCP server registered」。
  - 規模：~2 行 prose 變動 + 1 個 assertion 補強。
  - 為何延後：fallback prose 已涵蓋失敗模式，這條是 cosmetic precision。
  - 來源：v0.3.7 adversarial review reviewer 3 + synthesizer P2
  - 建單日：2026-06-10

- [ ] **`_build_memory_section` config 載入 silent except**
  - 現況：`except Exception: return []` 默默吞掉所有 config 載入錯誤，operator 看不到「BM 預設啟用但 config 壞了」vs「BM 真的關掉」的差別。
  - 修法：加 `logger.debug(f"memory section skipped: {e}")` 進 except 內，行為不變。
  - 規模：1 行。
  - 為何延後：debug-only 改善，無功能差異。
  - 來源：v0.3.7 adversarial review reviewer 1 + synthesizer P2
  - 建單日：2026-06-10

### v0.3.8 adversarial review P2 follow-ups

- [ ] **silent except pattern 還有 2 處未修**
  - 現況：v0.3.8 修了 AGENTS.md 那條（cmd_status.py:386-387 之前 silent `except OSError: pass`），但 `.vibe/.gitignore`（280-290）和 post-commit hook（307-317）有同個 pattern。
  - 影響：較小（這兩個比 AGENTS.md 更少 cross-machine readable/unreadable 差異），但保留同個 silent degradation 風險。
  - 修法：抽 `_safe_read_text(path) -> tuple[str | None, OSError | None]` helper，三處共用，OSError 一致變 warn。
  - 為何延後：v0.3.8 只 fold 一個 P1 入 commit，剩兩條同 pattern 統一 refactor 比較乾淨。
  - 來源：v0.3.8 adversarial review reviewer 1 + synthesizer P2
  - 建單日：2026-06-10

- [ ] **MCP runtime probe 不真的測 daemon**
  - 現況：`vibe status --diagnose` 用 `basic-memory --version` 當 probe。它只測 CLI binary 能 spawn，不真的查 daemon／資料庫。
  - 風險：daemon 死但 CLI 還在 → diagnose ✓ false positive。
  - 修法：等確認 basic-memory CLI surface 穩定後，改用 `basic-memory project list` 或 `basic-memory status` 之類真的 touch daemon 的指令。timeout 可能要從 5s 拉到 10s 或更高。
  - 為何延後：(a) basic-memory CLI shape 我不熟，亂猜 subcommand 會踩 false negative；(b) 等實作 v0.3.9 時併入「per-target probe shape」抽象。
  - 來源：v0.3.8 adversarial review reviewer 2 + synthesizer P2
  - 建單日：2026-06-10

### 從 v0.3.6 帶過來的待辦

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
