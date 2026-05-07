# vibe-state-cli 使用者指南（繁體中文）

> 從安裝到日常使用的完整教學。包含所有指令的詳細選項。
>
> [English version](../USER-GUIDE.md) | [README](README.md)

---

## 安裝

```bash
pip install pipx
pipx ensurepath
pipx install vibe-state-cli
```

> 安裝完**請關掉終端、重新打開**，新的 PATH 才會生效。
> `pipx` 把 `vibe` 裝在隔離環境，不會污染你的專案套件。

確認版本：

```bash
vibe --version       # 或 vibe -V
```

---

## 快速開始（3 分鐘）

```bash
cd my-project
vibe init              # 初始化 .vibe/（自動偵測語言、框架、AI 工具、裝 git hook）
vibe start             # 開工（載入狀態、自動 sync 落後 commits、顯示摘要）
# ... 開始工作 ...
vibe sync              # 收工（附加 git 狀態、C.L.E.A.R. 審查）
```

就這樣。三個指令涵蓋 90% 的使用場景。

---

## 五個指令詳解

### 1. `vibe init`

**做什麼**：掃描專案，生成 `.vibe/` 目錄、AI 工具的原生設定檔，並安裝 git post-commit hook（每次 commit 自動 sync）。

```bash
vibe init                      # 預設英文模板，沒指定 --lang 時讀現有 config（force）
vibe init --lang zh-TW         # 繁體中文模板
vibe init --force              # 強制重新初始化（也用於重開已結案專案）
vibe init --no-hooks           # 跳過 git post-commit hook 安裝
```

**自動偵測**：

- 語言/框架：讀取 `pyproject.toml`、`package.json`、`Cargo.toml` 等
- AI 工具：掃描 `.claude/`、`.cursor/`、`.windsurf/` 等目錄
- Git：偵測 `.git/` 是否存在（沒 git 就跳過 hook 安裝）

**`--force` 行為**（v0.3.4 修正）：
- 自動 backup 既有 `.vibe/` 到時間戳目錄
- 沒指定 `--lang` 時，**保留**既有 config 的 lang 設定（不再悄悄重置成 en）
- 如果 git hook 已安裝，跳過不重複裝

**生成的檔案**：

```text
.vibe/
├── config.toml          # 設定（adapter 開關、compact 閾值、lang）
└── state/
    ├── current.md       # 當前進度
    ├── tasks.md         # 任務清單
    ├── architecture.md  # 技術堆疊
    ├── standards.md     # 編碼規範
    ├── experiments.md   # autoresearch 實驗紀錄
    └── archive.md       # 冷藏庫
```

### 2. `vibe start`

**做什麼**：每日開工時執行。**v0.3.4 起會自動 sync 落後的 git commits**（不需要再記得手動 `vibe sync`），載入狀態、自動壓縮過長檔案、顯示摘要面板。

```bash
vibe start
```

**輸出範例**：

```text
Auto-synced: 5 new commits since last session

┌────────────── vibe start ──────────────┐
│  Progress      [2026-05-07] feat: ...   │
│  Git           3 uncommitted changes    │
│  Open issues   (none)                   │
│  Top tasks                              │
│                  1. Build auth module   │
│                  2. Write tests         │
│  Experiments   5 kept, 2 reverted       │
└──────────────── Session loaded ─────────┘
```

### 3. `vibe sync`

**做什麼**：附加 git 活動到 `state/current.md`，更新 sync cursor，偵測 autoresearch 實驗 commit，輸出 C.L.E.A.R. 審查清單。

```bash
vibe sync                              # 日常同步
vibe sync --note "三層 adapter 重構，理由是 token 效率"   # 加語意進度註記
vibe sync --compact                    # 同步 + 壓縮（歸檔已完成任務）
vibe sync --close                      # 結案（最終同步 + 壓縮 + 回顧報告）
vibe sync --no-refresh                 # 跳過 adapter 重新生成（git hook 用，避免 working tree 噪音）
```

**`--note` 是什麼？**

Git commit message 通常只說「做了什麼」，但「為什麼這樣做」、「架構決策的理由」常常只留在對話裡，session 結束就消失。`--note` 把這層語意寫進 `state/current.md` 的「進度摘要」區（不是 sync block），讓未來的 AI 能看到 why 不只是 what。

```bash
vibe sync --note "把 adapter 拆成三層 mode：full/slim/compact，因為 Cursor 不會讀 AGENTS.md，必須在 .mdc 裡內嵌規則"
```

**C.L.E.A.R. 審查清單**（僅在有實際變更且非 hook 模式時顯示）：

```text
[C] Core Logic   — 核心邏輯正確嗎？邊界條件？
[L] Layout       — 結構/命名符合 standards.md？
[E] Evidence     — 有測試輸出或 API 回應作為證據？
[A] Access       — 有硬編碼密鑰或權限漏洞？
[R] Refactor     — 明顯的技術債或效能問題？
```

### 4. `vibe status`

**做什麼**：隨時查看專案狀態（任何 lifecycle 狀態都可用）。**v0.3.4 起變成健康儀表板**，顯示距上次 sync 多久、落後幾個 commit、每個 adapter 是否新鮮。

```bash
vibe status
```

**輸出範例（中文介面，當 `config.vibe.lang = "zh-TW"`）**：

```text
┌────────── vibe status ──────────┐
│  生命週期      ACTIVE             │
│  上次同步      30 天前（落後 48 commits） │
│  狀態健康度    嚴重過期 — 建議立即執行 vibe sync │
│  Adapter 同步                    │
│                claude    ⚠ 過期   │
│                agents_md ⚠ 過期   │
│  Git           已啟用             │
│  內容語言      zh-TW              │
│  任務          0 待辦, 0 完成, 0 過期 │
└──────────────────────────────────┘
```

**健康度分級**：

| 等級 | 條件 |
|------|------|
| 新鮮 | < 3 天 且 < 5 commits |
| 過期 | 3-14 天 或 5-30 commits |
| 嚴重過期 | ≥ 14 天 或 > 30 commits |

### 5. `vibe adapt`

**做什麼**：管理 AI/IDE adapter 設定，**v0.3.4 起也用來切換介面語言**。

```bash
vibe adapt --list                          # 查看所有 adapter（ON/OFF）
vibe adapt --add cursor                    # 啟用 Cursor adapter
vibe adapt --add claude                    # 啟用 Claude Code adapter
vibe adapt --sync --confirm                # 重新生成所有已啟用 adapter 的檔案
vibe adapt --remove cursor --dry-run       # 預覽將刪除的檔案
vibe adapt --remove cursor --confirm       # 確認刪除（自動備份）
vibe adapt --lang zh-TW                    # 切換介面語言到中文
vibe adapt --lang en                       # 切換到英文
```

**`--lang` vs `vibe init --force --lang`** 的差別：

| 操作 | 影響範圍 | 適用場景 |
|------|---------|---------|
| `vibe adapt --lang` | 只改 config.toml 的 lang 欄位 | 只想切介面語言 |
| `vibe init --force --lang` | backup 既有 .vibe/、重生 adapter、重置 lifecycle | 完整重啟 |

---

## 智慧遷移

如果你的專案已經有 `CLAUDE.md`、`AGENTS.md`、`.cursorrules` 等 AI 設定檔，`vibe init` 會自動偵測並匯入你的規則：

```text
$ vibe init
Scanning project...

Found 2 existing config file(s):
  - CLAUDE.md
  - .cursorrules
Imported 9 rules into .vibe/state/standards.md
Archived 2 legacy file(s) to .vibe/archive/legacy/
```

**Two-phase 安全遷移**：先全部複製到 archive → 驗證 → 才刪除原檔。如果某個檔案抽不到 bullet rules（純段落式說明），會單獨保留警告，不歸檔。

---

## 日常工作流

### 單人開發

```text
每天早上：vibe start          # 自動 sync 昨晚的 commits
  ↓
工作（每次 commit 後 git hook 自動 sync 進 state）
  ↓
偶爾留下架構決策：vibe sync --note "..."
  ↓
每天收工：vibe sync           # 看 C.L.E.A.R. 審查清單
  ↓
每週五：vibe sync --compact   # 歸檔已完成任務
  ↓
專案結束：vibe sync --close   # 寫回顧報告，鎖定狀態
```

### 多 Agent 切換

```text
Morning: Claude Code terminal
  ↓ vibe start → AI 讀取 CLAUDE.md → 看到 "Session Start" → 讀 .vibe/state/
  ↓ 工作...
  ↓ commit（hook 自動 sync）

Afternoon: Cursor IDE
  ↓ vibe start → Cursor 載入 .mdc → 看到注入的 ## Last Session → 立刻知道進度
  ↓ 無縫銜接 morning 的工作
```

### 搭配 Autoresearch

[Autoresearch](https://github.com/uditgoenka/autoresearch) 是自主迭代框架，對任何可量化的目標自動跑 **修改 → 驗證 → 保留/捨棄 → 重複** 循環。

**基本流程**：

```bash
# Step 1: 在 Claude Code 中啟動 autoresearch
/autoresearch
Goal: Improve test coverage to 95%
Scope: src/**/*.py
Metric: pytest --cov --cov-report=term | grep TOTAL | awk '{print $4}'
Direction: higher_is_better
Verify: pytest --cov --cov-fail-under=95

# Step 2: Autoresearch 自動跑迴圈
#   → 每次做一個原子修改 → commit → 跑 metric
#   → metric 改善 → KEEP（保留 commit）
#   → metric 退步 → REVERT（回滾，但歷史保留）

# Step 3: 完成後用 vibe 記錄（其實 git hook 已自動跑，但手動也行）
vibe sync    # 掃描 git log → 偵測實驗 commit → 寫入 state/experiments.md
vibe start   # 顯示摘要：5 kept, 3 reverted
```

**Autoresearch 完整指令**：

| 指令                     | 用途                                                    |
| ------------------------ | ------------------------------------------------------- |
| `/autoresearch`          | 主要迭代迴圈（有界/無界）                               |
| `/autoresearch:plan`     | 互動式嚮導：設定 Goal、Scope、Metric、Direction、Verify |
| `/autoresearch:debug`    | 科學除錯法：假設 → 驗證 → 修正                          |
| `/autoresearch:fix`      | 自動修錯迴圈（每輪修一個，失敗自動回滾）                |
| `/autoresearch:security` | STRIDE 威脅模型 + OWASP Top 10 + 紅隊審計               |
| `/autoresearch:learn`    | 自動生成/更新文件                                       |
| `/autoresearch:ship`     | 8 階段通用上線流程                                      |
| `/autoresearch:predict`  | 5 人格專家群體分析                                      |
| `/autoresearch:reason`   | 對抗式精煉（生成 → 批判 → 綜合 → 裁決）                 |
| `/autoresearch:scenario` | 邊界案例 + 衍生情境探索                                 |

**vibe-state-cli 的偵測機制**：

`vibe sync` 掃描 git log，根據 commit message 的 pattern 判定是否為實驗 commit：

```text
# 預設偵測的 pattern（不分大小寫）
autoresearch:    experiment:    [autoresearch]    [experiment]    auto-research
```

回滾偵測只看訊息**前綴**第一個詞是否為 `revert`、`reset`、`rollback`、`undo`：

```text
autoresearch: revert - metric dropped    → [REVERTED] ✓ 正確
experiment: fix revert payment issue     → [KEPT]     ✓ 正確（revert 在 body 不在前綴）
```

**自訂 pattern**（`.vibe/config.toml`）：

```toml
[experiments]
commit_patterns = ["autoresearch:", "experiment:", "[autoresearch]", "[experiment]", "auto-research"]
revert_prefixes = ["revert", "reset", "rollback", "undo"]
```

---

## Git Hook（v0.3.4）

`vibe init` 會自動安裝 `.git/hooks/post-commit`，每次 commit 自動跑 `vibe sync --no-refresh`。意思是：

- **你不用記得手動跑 sync** — commit 完 state 就自動更新
- **失敗不會擋你 commit** — hook 用 `|| true`，錯誤靜默 log 到 `.vibe/state/.hook.log`
- **不污染 working tree** — `--no-refresh` 不重生 adapter 檔案，避免 commit 後又有 dirty changes
- **READY 狀態下 silent skip** — `vibe init --force` 後第一次 commit 不會炸 log（lifecycle 還沒推到 ACTIVE）

不想要 hook？

```bash
vibe init --no-hooks                    # init 時跳過
# 或裝完想移除：手動刪 .git/hooks/post-commit 的 vibe 區塊（介於兩個 marker 之間）
```

---

## 支援的 AI 工具

| 工具                            | Adapter 名稱  | 自動偵測標誌                           |
| ------------------------------- | ------------- | -------------------------------------- |
| AGENTS.md（通用標準）           | `agents_md`   | `AGENTS.md` 已存在                     |
| Claude Code                     | `claude`      | `.claude/` 或 `CLAUDE.md`（含 skills） |
| Google Antigravity / Gemini CLI | `antigravity` | `GEMINI.md` 或 `.gemini/`              |
| Cursor                          | `cursor`      | `.cursor/` 或 `.cursorrules`           |
| GitHub Copilot (VS Code)        | `copilot`     | `.github/copilot-instructions.md`      |
| Windsurf                        | `windsurf`    | `.windsurf/` 或 `.windsurfrules`       |
| Cline                           | `cline`       | `.clinerules/`                         |
| Roo Code                        | `roo`         | `.roo/`                                |

**Token 節約**：當 AGENTS.md + 其他 adapter 同時啟用時，其他 adapter 自動切換 slim 模式（只放 frontmatter + 指向 AGENTS.md），避免重複內容浪費 token。

**Vibe Commands**：所有 adapter 生成的設定檔都包含「Vibe Commands」區塊，告訴 AI 工具：「當使用者說 `vibe sync`，直接在終端執行該命令，不要解釋或實作它。」這個機制不需要外掛，跨所有 AI 工具通用。

**Claude Code Skills**：Claude adapter 額外生成 `.claude/skills/vibe-*/SKILL.md`，讓 `/vibe-init`、`/vibe-start`、`/vibe-sync`、`/vibe-status`、`/vibe-adapt` 可以直接當 slash command 使用。此格式遵循 [Agent Skills 開放標準](https://agentskills.io/)。

---

## 環境變數

| 變數 | 用途 |
|------|------|
| `VIBE_SKIP_HOOK_INSTALL` | 設為 `1` 跳過 `vibe init` 的 hook 安裝（測試/CI 用） |

---

## FAQ

### `.vibe/` 應該 commit 到 git 嗎？

**是的**。`.vibe/` 是專案的共享大腦，團隊成員都應該看到。`.vibe/backups/` 跟 `.vibe/state/.hook.log`、`.vibe/state/*.lock` 已在 `.gitignore` 中排除。

### 不用 git 可以嗎？

可以。`vibe init` 會自動偵測，非 git 專案的 sync 會跳過 git 操作，hook 也不會安裝。

### 可以同時用 Claude Code 和 Cursor 嗎？

可以。`vibe adapt --add claude` + `vibe adapt --add cursor` + `vibe adapt --sync`。兩邊各自載入自己的設定檔，共享 `.vibe/state/`。

### `vibe status` 顯示「過期」怎麼辦？

`vibe sync` 把當下落後的 commits 寫入 state，或更簡單：直接 `vibe start`，它會自動 sync。

### `experiments.md` 是什麼？

Autoresearch 實驗的自動記錄。`vibe sync` 偵測 git log 中帶有 `autoresearch:` 或 `[autoresearch]` 前綴的 commit，記錄為 KEPT 或 REVERTED。

### 在 IDE 裡打 `vibe sync` AI 不理我？

所有 adapter 生成的設定檔都包含「Vibe Commands」指令，告訴 AI 直接執行終端命令。如果 AI 還是不理解，說「請在終端執行 `vibe sync`」。如果你用 Claude Code 或 Cline，可以直接打 `/vibe-sync`（slash command）。
