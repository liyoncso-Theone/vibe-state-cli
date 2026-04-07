# vibe-state-cli 創作歷程與決策紀錄

> 本文件記錄了 vibe-state-cli 從構想到成品的完整歷程，包含每一個重大決策的「為什麼」。

---

## 第一章：起源 — 一個 Prompt 模板的進化

### 痛點

2026 年初，AI Coding 已經是日常。但開發者面臨一個核心矛盾：

**AI 很強大，但每次對話結束就失憶。**

- 你在 Claude Code 上花了兩小時跟 AI 討論架構，關掉終端，明天重開 — AI 什麼都不記得。
- 你在 Cursor 寫了一半的功能，切到 Claude Code 做 debug — 另一個 AI 不知道你剛剛做了什麼。
- 專案做了三個月，AI 的「記憶」散落在 CLAUDE.md、.cursor/rules/、AGENTS.md 各處，互不相通。

### 第一版：Memory Bank 手動模板

最初的解法是一套 Markdown 模板 — 「多代理人協作大腦 (Memory Bank)」：

- `memory-bank/current-state.md` — 當前進度
- `memory-bank/task.md` — 任務清單
- `memory-bank/implementation_plan.md` — 架構計畫
- `.claude/CLAUDE.md` — AI 行為規則

運作方式：每天開工時，把這些文件貼給 AI，讓它「恢復記憶」。

**問題**：全是手動操作。要複製貼上、要記得更新、要自己維護。而且只能用在 Claude Code 上。

### 關鍵轉折：從模板到工具

當我們問出這個問題：「能不能把這套流程做成一個 CLI 工具，讓任何 AI 都能用？」

vibe-state-cli 就此誕生。

---

## 第二章：架構設計 — 四輪嚴格審查

### 第一輪：市場研究（4 路 Agent 並行）

我們派出四個 AI Agent 同時研究：
- Agent 1：競品分析（Aider、Cursor Rules、CLAUDE.md、MCP 生態）
- Agent 2：技術架構設計
- Agent 3：開源策略（打包、社區、i18n）
- Agent 4：MCP 協議與工具鏈驗證

**關鍵發現**：
- AGENTS.md 已成為 Linux Foundation 標準，被 60,000+ repo 採用
- 各工具的設定檔格式**完全不同**（Cursor 用 .mdc YAML、Windsurf 用 trigger enum、Cline 用 paths array）
- 沒有任何工具做「跨 session 狀態管理 + 跨工具同步」

### 第二輪：規格驗證（去除幻覺）

這是最關鍵的一步。我們發現第一輪的部分結論是**AI 幻覺**：

| 幻覺 | 真實 |
|------|------|
| Claude Code 讀取 AGENTS.md | 不讀，需要 `@AGENTS.md` 匯入 |
| 生成 `.cursorrules` | 已棄用，現為 `.cursor/rules/*.mdc` |
| 各工具 frontmatter 可通用 | 完全不同，不可互換 |
| MCP 協議版本 v1.27 | 那是 SDK 版本，協議版本是 2025-11-25 |

**教訓**：AI 研究結果必須交叉驗證。我們用 WebSearch 逐一確認了 8 個 AI/IDE 的真實規格。

### 第三輪：三路架構審查

派出三個獨立審查團隊：

**工作流邏輯審查**發現：
- VIBE.md 被宣稱為「SSOT」但沒有更新機制 → 改名為「Constitution」
- `vibe sync` 說「從 git 更新語意進度」但 git 只給檔案清單，不可能 → 改為「純 git 附加」
- 指令可以亂序執行 → 加入嚴格狀態機

**產品策略審查**質疑：
- 8 個 adapter 維護成本是否可持續？
- 用戶真的會在 8 個工具間切換嗎？
- 原生工具（Claude auto-memory）是否已經解決問題？

**技術可行性審查**發現：
- `vibe adapt --remove` 會刪除用戶手動編輯的內容 → 加入快照比對 + 備份 + dry-run
- Markdown regex 解析不可靠 → 改用 AST（markdown-it-py）
- config.toml 損壞會 crash → 加入 try/except + 友善錯誤

### 第四輪：八維度綜合審查

在程式碼寫完後，我們做了最嚴格的一輪：

1. **核心架構** — skills/ 檔案從未被引用（475 token 浪費）→ 合併進 VIBE.md
2. **程式碼嚴謹** — adapter 共用邏輯複製 6 次 → 抽取到 `_build_common_body()`
3. **上下文汙染** — 信號比僅 35%（256 行中只有 91 行有用）→ 精簡到 92 行
4. **Token 節約** — "Never hardcode secrets" 重複 6 次 → 智慧去重
5. **安全性** — project name 可注入 markdown heading → `_sanitize()` 過濾
6. **效能** — `vibe start` 永遠顯示初始化日期 → 改讀最後 Sync 區塊
7. **可維護性** — 無 CONTRIBUTING.md、無 --debug flag
8. **用戶旅程** — 新用戶第一次用的摩擦點

---

## 第三章：關鍵決策日誌

### 決策 1：5 個指令，不是 8 個

原設計有 8 個指令。我們問：「對一個人類來說，他需要記住 8 個指令嗎？」

答案是不需要。`compact` 收進 `sync --compact`，`close` 收進 `sync --close`，`reopen` 改為 `init --force`。

**最終**：`init`、`start`、`sync`、`status`、`adapt` — 五個就夠了。

### 決策 2：VIBE.md 不是 SSOT

最初設計 VIBE.md 為「唯一事實來源」。審查發現這是悖論 — VIBE.md 生成後從不更新，宣稱 SSOT 是空話。

改為：VIBE.md 是「憲法」（行為準則，極少修改），`state/` 才是真正的 SSOT。

### 決策 3：純 git 附加，不依賴 LLM

`vibe sync` 原設計要「呼叫 LLM 產生語意進度摘要」。審查發現這打破了「廠商中立」承諾 — 你需要 API key。

改為：只附加 git status 的結構化資料。語意解讀由 AI 在 `vibe start` 時自行理解。

### 決策 4：按需 adapter，不是全量生成

原設計一視同仁生成所有 AI 工具的設定檔。使用者問：「我只用 Claude，為什麼要生成 Cursor 的 .mdc？」

改為三層策略：自動偵測 → 互動選擇 → `vibe adapt` 事後增減。

### 決策 5：slim 模式去重

當 AGENTS.md + Cursor adapter 同時啟用，兩邊載入相同內容浪費 token。

改為：AGENTS.md 放完整內容，Cursor .mdc 只放 frontmatter + "See AGENTS.md" + Session Start 指令。

### 決策 6：隱形大腦問題

`.vibe/state/` 是共享大腦，但沒有任何 AI 工具自動讀取它。

修復：每個 adapter 輸出都包含「Session Start — READ THESE FILES」指令，明確引導 AI 讀取 `state/current.md` 和 `state/tasks.md`。

### 決策 7：Autoresearch 整合

不另做專案，不 fork。vibe-state-cli 做「記憶層」，autoresearch 做「進化引擎」。`vibe sync` 自動偵測 autoresearch 的 commit pattern，記錄到 `state/experiments.md`。

### 決策 8：安全邊界框架

VIBE.md 不只告訴 AI「要做什麼」，更明確定義「不可以做什麼」：
- 不可執行破壞性指令
- 不可修改 .vibe/config.toml
- 不可偽造測試結果
- 不可外傳資料

---

## 第四章：技術亮點

### 原子寫入
`state.py` 使用 `tempfile.mkstemp()` + `os.replace()` 確保寫入是原子的。斷電或 crash 不會損壞狀態檔。

### 路徑穿越防護
`_validate_filename()` 確認所有檔案路徑在 `state/` 目錄內。理論上的 `../../.bashrc` 攻擊被阻擋。

### 輸入消毒
`_sanitize()` 過濾 `\n`、`\r`、`#`、`"`、`'`、`` ` `` — 防止 markdown heading 注入和 YAML frontmatter 破壞。

### 智慧去重
`_build_common_body(slim=True)` 在 AGENTS.md 同時啟用時自動切換精簡模式，避免 token 浪費。

### Frontmatter 驗證
每個 adapter 定義 `REQUIRED_FIELDS`，`emit()` 後自動 `validate()` 確認輸出格式正確。

---

## 第五章：數據

| 指標 | 數值 |
|------|------|
| CLI 指令數 | 5 |
| 內建 adapter | 8（覆蓋所有主流 AI/IDE） |
| 狀態檔 | 7（含 experiments.md） |
| 自動化測試 | 68 |
| 場景測試 | 10（全部通過） |
| 支援語言 | 2（en、zh-TW） |
| 精簡後 token 數 | ~684（vs 初版 ~1,820，降 62%） |
| 安全審查輪次 | 4 輪 |
| 發現並修復的 bug | 17 項 |
