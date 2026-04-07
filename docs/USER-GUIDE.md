# vibe-state-cli 使用者指南

> 從安裝到日常使用的完整教學。

---

## 安裝

```bash
pipx install vibe-state-cli
```

> `pipx` 會自動建隔離環境。如果還沒裝：`pip install pipx`

---

## 快速開始（3 分鐘）

```bash
cd my-project
vibe init              # 初始化 .vibe/（自動偵測語言、框架、AI 工具）
vibe start             # 開工（載入狀態、驗證 git、顯示摘要）
# ... 開始工作 ...
vibe sync              # 收工（附加 git 狀態、C.L.E.A.R. 審查）
```

就這樣。三個指令涵蓋 90% 的使用場景。

---

## 五個指令詳解

### 1. `vibe init`

**做什麼**：掃描專案，生成 `.vibe/` 目錄和 AI 工具的原生設定檔。

```bash
vibe init                    # 英文模板
vibe init --lang zh-TW       # 繁體中文模板
vibe init --force             # 強制重新初始化（也可用於重開已結案專案）
```

**自動偵測**：

- 語言/框架：讀取 `pyproject.toml`、`package.json`、`Cargo.toml` 等
- AI 工具：掃描 `.claude/`、`.cursor/`、`.windsurf/` 等目錄
- Git：偵測 `.git/` 是否存在

**生成的檔案**：

```text
.vibe/
├── VIBE.md              # 憲法（AI 行為準則 + 工作流 SOP）
├── config.toml          # 設定（adapter 開關、compact 閾值等）
└── state/
    ├── current.md       # 當前進度
    ├── tasks.md         # 任務清單
    ├── architecture.md  # 技術堆疊
    ├── standards.md     # 編碼規範
    ├── experiments.md   # autoresearch 實驗紀錄
    └── archive.md       # 冷藏庫
```

### 2. `vibe start`

**做什麼**：每日開工時執行。載入狀態、驗證 git、自動壓縮過長檔案、顯示 Rich 格式的摘要面板。

```bash
vibe start
```

**輸出範例**：

```text
┌────────────── vibe start ──────────────┐
│  Progress      Sync [2026-04-07] ...   │
│  Git           3 uncommitted changes   │
│  Open issues   (none)                  │
│  Top tasks                             │
│                  1. Build auth module   │
│                  2. Write tests         │
│  Experiments   5 kept, 2 reverted      │
└──────────────── Session loaded ────────┘
```

### 3. `vibe sync`

**做什麼**：附加 git 狀態到 `state/current.md`，偵測 autoresearch 實驗 commit，輸出 C.L.E.A.R. 審查清單。

```bash
vibe sync                # 日常同步
vibe sync --compact      # 同步 + 壓縮（歸檔已完成任務）
vibe sync --close        # 結案（最終同步 + 壓縮 + 回顧報告）
```

**C.L.E.A.R. 審查清單**（僅有實際變更時顯示）：

```text
[C] Core Logic   — 核心邏輯正確嗎？邊界條件？
[L] Layout       — 結構/命名符合 standards.md？
[E] Evidence     — 有測試輸出或 API 回應作為證據？
[A] Access       — 有硬編碼密鑰或權限漏洞？
[R] Refactor     — 明顯的技術債或效能問題？
```

### 4. `vibe status`

**做什麼**：隨時查看專案狀態（任何 lifecycle 狀態都可用）。

```bash
vibe status
```

### 5. `vibe adapt`

**做什麼**：管理 AI/IDE adapter 設定檔。

```bash
vibe adapt --list                          # 查看所有 adapter（ON/OFF）
vibe adapt --add cursor                    # 啟用 Cursor adapter
vibe adapt --add claude                    # 啟用 Claude Code adapter
vibe adapt --sync                          # 重新生成所有已啟用 adapter 的檔案
vibe adapt --remove cursor --dry-run       # 預覽將刪除的檔案
vibe adapt --remove cursor --confirm       # 確認刪除（自動備份）
```

---

## 日常工作流

### 單人開發

```text
每天早上：vibe start
  ↓
工作（AI 自動 checkpoint — 標記 [x] + 更新 current.md）
  ↓
每天收工：vibe sync
  ↓
每週五：vibe sync --compact
  ↓
專案結束：vibe sync --close
```

### 多 Agent 切換

```text
Morning: Claude Code terminal
  ↓ vibe start → AI 讀取 CLAUDE.md → 看到 "Session Start" → 讀 .vibe/state/
  ↓ 工作...
  ↓ vibe sync

Afternoon: Cursor IDE
  ↓ vibe start → Cursor 載入 .mdc → 看到 "Session Start" → 讀 .vibe/state/
  ↓ 無縫銜接 morning 的進度
```

### 搭配 Autoresearch

```bash
# 在 Claude Code 中：
/autoresearch
Goal: Improve test coverage to 95%
Scope: src/**/*.py
Verify: pytest --cov --cov-fail-under=95

# Autoresearch 自動跑迴圈（改 code → commit → test → keep/revert）
# 完成後：
vibe sync    # 自動偵測 experiment commits → 記錄到 state/experiments.md
vibe start   # 顯示實驗摘要：5 kept, 3 reverted
```

---

## 支援的 AI 工具

| 工具 | Adapter 名稱 | 自動偵測標誌 |
| ---- | ------------ | ------------ |
| AGENTS.md（通用標準） | `agents_md` | `AGENTS.md` 已存在 |
| Claude Code | `claude` | `.claude/` 或 `CLAUDE.md` |
| Google Antigravity / Gemini CLI | `antigravity` | `GEMINI.md` 或 `.gemini/` |
| Cursor | `cursor` | `.cursor/` 或 `.cursorrules` |
| GitHub Copilot (VS Code) | `copilot` | `.github/copilot-instructions.md` |
| Windsurf | `windsurf` | `.windsurf/` 或 `.windsurfrules` |
| Cline | `cline` | `.clinerules/` |
| Roo Code | `roo` | `.roo/` |

**Token 節約**：當 AGENTS.md + 其他 adapter 同時啟用時，其他 adapter 自動切換 slim 模式（只放 frontmatter + 指向 AGENTS.md），避免重複內容浪費 token。

---

## FAQ

### .vibe/ 應該 commit 到 git 嗎？

**是的**。`.vibe/` 是專案的共享大腦，團隊成員都應該看到。但 `.vibe/backups/` 和 `.vibe/snapshots/` 已在 `.gitignore` 中排除。

### 不用 git 可以嗎？

可以。`vibe init` 會自動偵測，非 git 專案的 sync 會跳過 git 操作。

### 可以同時用 Claude Code 和 Cursor 嗎？

可以。`vibe adapt --add claude` + `vibe adapt --add cursor` + `vibe adapt --sync`。兩邊各自載入自己的設定檔，共享 `.vibe/state/`。

### experiments.md 是什麼？

是 autoresearch 實驗的自動記錄。`vibe sync` 會偵測 git log 中帶有 `autoresearch:` 或 `[autoresearch]` 前綴的 commit，記錄為 KEPT 或 REVERTED。
