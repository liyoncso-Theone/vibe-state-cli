# AGENTS.md — vibe-state-cli

## Project

- Languages: Python

- Variables/functions: snake_case, Classes: PascalCase, Constants: UPPER_SNAKE_CASE
- Conventional Commits. One logical change per commit.
- Never hardcode secrets. Use .env files.
- DO NOT GIVE ME HIGH LEVEL SHIT. IF I ASK FOR A FIX OR EXPLANATION, I WANT ACTUAL CODE OR DETAILED EXPLANATION.
- Always communicate in Traditional Chinese (繁體中文).
- Suggest solutions that I didnt think about. Treat me as an expert.
- Value good arguments over authorities; consider new technologies.
- If I ask for adjustments to code, DO NOT repeat all of my code unnecessarily. Give just a couple of lines before/after any changes.
- **Version Control**：嚴格遵守 Conventional Commits 標準。採用 Micro-commits 策略（單次 Commit 僅限單一邏輯變更）。
- **Zero Trust**：未提供測試證據（真實終端機日誌或 API 回傳值）前，禁止部署核心邏輯。高風險操作須人類放行。
- **[進場讀取]**：接到「每日開工」指令時，強制讀取 memory-bank/ 下的核心檔案，並輸出狀態驗證摘要供人類確認。
- **[即時 Checkpoint — 自動執行，無需人類指令]**：每完成 task.md 中的一個任務項，你【必須】立即自行更新 task.md（標記 [x]）與 current-state.md（追加進度）。這是防止對話中斷導致進度遺失的關鍵機制，不需等到收工，也不需要人類提醒。若你忘記執行此步驟，視為違反憲法。
- **[鏡像同步]**：你內部的檔案狀態，必須與 memory-bank/ 保持同步。
- **[現實優先原則]**：當你對 codebase 的記憶與 git 實際狀態產生矛盾時，以 git（git status、git diff、git log）為絕對真理。禁止依賴自身記憶覆寫 current-state.md，必須先用 git 驗證。
- coding-standards.md 採分類索引結構，每日開工只讀目錄索引，需要時再載入特定章節。
- implementation_plan.md 頂部為「當前架構快照」（必讀），底部為「架構決策歷史」（按需讀取）。
- archive.md 為冷藏庫，日常不讀取，僅考古時載入。
- **[自動瘦身 — 無需人類指令]**：每日開工讀取 memory-bank 時，若偵測到任何單一檔案超過 150 行，你【必須】立即自動執行 memory-compaction skill 的完整流程，執行完畢後回報結果。不需等待人類下令。
- **[自動發現機制 Auto-Discovery]**：當使用者下達「執行 [技能名稱]」或提出特定任務需求時，你【必須】先掃描 .claude/skills/ 目錄，尋找是否有對應的 [技能名稱].md 檔案。
- **[動態載入與執行]**：若找到對應檔案，請靜默讀取其內容，並嚴格遵循該檔案內定義的執行順序、約束條件與輸出格式來完成任務。
- **[未知技能回報]**：若使用者呼叫了不存在的技能，請回報「在 skills 目錄中找不到該技能」，並詢問是否需要協助建立新的技能樣板。

## Session Start — READ THESE FILES
At the beginning of every session, read these files for project context:
- `.vibe/state/current.md` — latest progress and sync history
- `.vibe/state/tasks.md` — active task checklist
- `.vibe/VIBE.md` — project constitution and workflow SOP

## Boundaries
- Do NOT modify `.vibe/config.toml` or `.vibe/state/.lifecycle` directly
- Do NOT run destructive commands without human confirmation

<!-- vibe-state-cli:integrity:c7ae38e6c496 -->
