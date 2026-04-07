# Skill: memory-audit (大腦記憶與 codebase 狀態校準)

🎯 觸發時機

**手動觸發**：當使用者下達「執行 memory-audit」或表示「狀態脫節」、「你搞混了」時。

**自動觸發**：當以下任一情境發生時，你【必須】主動執行此 skill，無需人類下令：
* 人類執行了 git revert、git reset 或在 IDE 中 discard changes 後告知你。
* 你連續兩次以上嘗試修改一個檔案卻發現它的內容與你記憶中的不同。
* 你嘗試引用一個函式、API 或模組，但執行時報錯說它不存在。

🔍 前置條件 (Prerequisites)
* 確認專案已初始化 git（.git 目錄存在）。
* 確認 memory-bank/ 目錄存在。

📋 嚴格執行步驟

1. **取得真實狀態 (Ground Truth from Git)**：
   - 執行 `git status` 確認工作目錄的真實狀態。
   - 執行 `git log --oneline -10` 確認最近 10 筆 commit 紀錄。
   - 執行 `git diff --stat` 確認未提交的變更。
   - 若有需要，讀取關鍵檔案的實際內容以確認模組是否存在。

2. **讀取大腦記憶**：讀取 memory-bank/current-state.md 與 memory-bank/task.md。

3. **交叉比對 (Diff & Audit)**：
   - 尋找「記憶中標記為已完成，但 git 中不存在對應 commit 或程式碼」的幻覺進度。
   - 尋找「git 中有 commit 或程式碼，但記憶中沒有紀錄」的遺漏進度。
   - 尋找「記憶中引用的函式/模組/API，但實際檔案中不存在」的幻覺依賴。

4. **強制校準 (Override — 現實優先)**：
   - 以 git 狀態為絕對真理 (Single Source of Truth)。
   - 強制覆寫修正 current-state.md，刪除幻覺進度，補上真實進度。
   - 將被誤標為完成的任務在 task.md 中退回為 [ ]（未完成）。

⚠️ 約束條件 (Constraints)
* 校準過程中嚴禁依賴 AI 自身記憶，一切以 git 指令的回傳結果為準。
* 嚴禁刪除 task.md 中的任何任務，只能修改完成狀態標記。
* 校準完成後必須重新讀取修正後的 memory-bank 檔案，確保後續對話基於正確狀態。

📤 預期輸出 (Expected Output)
🔬 Memory Audit 校準報告
═══════════════════════
▸ 發現幻覺進度：[N] 項
  - [具體列出每項幻覺內容與修正動作]
▸ 發現遺漏進度：[N] 項
  - [具體列出每項遺漏內容與補錄動作]
▸ 任務狀態修正：[N] 項任務從 [x] 退回 [ ]
▸ 結論：記憶體已與 codebase 實際狀態強制對齊完畢。
═══════════════════════
