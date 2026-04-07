# Skill: agent-handoff (每日收工/階段存檔)

🎯 觸發時機
當使用者下達「執行 agent-handoff」時觸發。

🔍 前置條件 (Prerequisites)
* 確認 memory-bank/ 目錄存在且包含 current-state.md 與 task.md。

📋 嚴格執行步驟

1. **Git 狀態確認**：先執行 git status 與 git diff --stat，確認 codebase 的真實狀態。
2. **狀態覆寫**：根據 git 的真實狀態（而非你的記憶），將當前開發進度完整寫入 memory-bank/current-state.md（覆寫為最新快照，非追加流水帳）。
3. **任務同步**：確認 task.md 中所有已完成的項目皆標記為 [x]。嚴禁刪除任何任務以保留完整軌跡。
4. **C.L.E.A.R. 五維度審查**：輸出以下格式的報告：

🔍 C.L.E.A.R. 審查報告
═══════════════════════
[C] Core Logic（核心邏輯）
    本次變更的核心邏輯是否正確？有無邊界條件未處理？
    → [具體評估結果]

[L] Layout（程式碼結構）
    檔案結構、命名、模組拆分是否符合 coding-standards.md？
    → [具體評估結果]

[E] Evidence（測試證據）
    是否有終端機日誌、API 回傳值或測試結果作為佐證？
    → [具體評估結果，附上證據來源]

[A] Access（安全與權限）
    是否有硬編碼密鑰、暴露的端點或權限漏洞？
    → [具體評估結果]

[R] Refactor（重構建議）
    有無明顯的技術債或可改善的效能瓶頸？
    → [具體建議，或「目前無需重構」]
═══════════════════════

⚠️ 約束條件 (Constraints)
* 嚴禁刪除 task.md 中的任何任務（含已完成項），僅可標記狀態。
* C.L.E.A.R. 每個維度必須給出具體評估，禁止寫「無問題」等空泛結論。
* 狀態覆寫必須基於 git 真實狀態，禁止僅憑 AI 記憶寫入。

📤 預期輸出 (Expected Output)
* 確認訊息：「Agent Handoff 完成。current-state.md 與 task.md 已同步。」
* 隨後輸出完整的 C.L.E.A.R. 審查報告。
