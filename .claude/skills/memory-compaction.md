# Skill: memory-compaction (大腦記憶體瘦身)

🎯 觸發時機
當使用者下達「執行 memory-compaction」，或每日開工時偵測到任何單一 memory-bank 檔案超過 150 行時自動觸發。

🔍 前置條件 (Prerequisites)
* 確認 memory-bank/ 目錄存在且包含 task.md、current-state.md、archive.md。

📋 嚴格執行步驟

1. **任務歸檔**：將 memory-bank/task.md 中所有已標記為完成（[x]）的任務，完整剪下並貼上至 memory-bank/archive.md 中，加上歸檔日期標題（格式：## [YYYY-MM-DD] 歸檔）。
2. **狀態精簡**：精簡 memory-bank/current-state.md 的歷史流水帳，只保留「當前狀態快照」。
3. **行數檢查**：檢查所有 memory-bank 檔案的行數，回報精簡前後的對比。

⚠️ 約束條件 (Constraints)
* 精簡時【嚴禁】刪除以下三類資訊：
  - 未解決的 Bug
  - 已決定的架構設計決策
  - 已知的環境限制與相依性
* 歸檔至 archive.md 時，必須加上日期標題，以便未來考古。

📤 預期輸出 (Expected Output)
🧹 Memory Compaction 完成
───────────────────────
task.md：[N] 項已完成任務歸檔至 archive.md
current-state.md：[精簡前行數] → [精簡後行數] 行
coding-standards.md：[行數] 行（未動/已整理）
implementation_plan.md：[行數] 行（未動/已整理）
───────────────────────
