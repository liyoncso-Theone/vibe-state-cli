# Skill: project-close (專案結案)

🎯 觸發時機
當使用者下達「執行 project-close」，確認專案已完成或需要正式結案時觸發。

🔍 前置條件 (Prerequisites)
* 確認 memory-bank/ 目錄存在且完整。
* 確認 task.md 中無未完成的關鍵任務（若有，先提醒人類確認是否放棄）。

📋 嚴格執行步驟

1. **最終 Handoff**：執行一次完整的 agent-handoff（含 C.L.E.A.R. 審查）。
2. **最終 Compaction**：執行一次完整的 memory-compaction。
3. **專案回顧摘要**：產出以下格式的回顧報告，寫入 memory-bank/project-retrospective.md：

# 專案回顧摘要
生成日期：[YYYY-MM-DD]

## 專案成果
- [列出主要交付物與達成的商業目標]

## 關鍵技術決策
- [列出開發過程中做出的重大架構/技術選擇及其原因]

## 遺留事項
- [未完成的功能、已知 Bug、技術債]

## 經驗教訓
- [值得帶到下個專案的最佳實踐或踩過的坑]

4. **狀態標記**：在 current-state.md 頂部加入「⛔ 本專案已於 [YYYY-MM-DD] 結案。」

⚠️ 約束條件 (Constraints)
* 結案前必須讓人類確認遺留事項是否可接受。
* 結案後 memory-bank 檔案保留不刪除，供未來參考。

📤 預期輸出 (Expected Output)
* 輸出完整的專案回顧摘要。
* 確認訊息：「專案已正式結案。memory-bank 已歸檔保留。」
