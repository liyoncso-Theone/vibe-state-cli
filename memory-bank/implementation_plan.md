# Implementation Plan

## 當前架構快照

### 商業目標

- 打造廠商中立 (Model-Agnostic) 的 AI-人類協作狀態管理 CLI 工具
- 讓任何 AI 模型讀取 `.vibe/` 目錄即可進入同步心流
- 以開源專案形式發布（MIT License），目標成為 Vibe Driven Development (VDD) 標準工具
- 與 AGENTS.md（Linux Foundation / AAIF 標準）相容
- 8 個 AI/IDE adapter 全量內建，開箱即用

### 核心概念釐清

- **VIBE.md = 憲法（Constitution）**：唯讀行為準則（coding philosophy、SOP 流程、AI 指令），初始化後極少修改
- **state/ = SSOT（單一事實來源）**：可變的專案狀態（進度、任務、架構、規範）
- **adapter 衍生來源**：VIBE.md（行為）+ state/（狀態）+ config.toml（設定）→ 組合產出各工具原生設定檔

### 系統架構設計

- **CLI 入口**：8 大指令 — `vibe init`、`vibe start`、`vibe sync`、`vibe compact`、`vibe close`、`vibe reopen`、`vibe status`、`vibe adapt`
- **`.vibe/` 目錄**：VIBE.md（憲法）、skills/（技能庫）、state/（SSOT）、config.toml（設定）、snapshots/（adapter 快照）、backups/（adapter 備份）
- **嚴格狀態機**：`.vibe/state/.lifecycle` 追蹤狀態，無效轉換報錯
- **Git 整合**：唯讀（status/diff/log），`vibe sync --commit` 為 opt-in，非 git 專案可停用

### 嚴格狀態機

```text
UNINIT ──[init]──► READY ──[start]──► ACTIVE
                                        │
                       ┌─[sync]───► ACTIVE
                       ├─[compact]─► ACTIVE
                       └─[close]──► CLOSED ──[reopen]──► ACTIVE

vibe status：任何狀態可用
vibe adapt：READY 或 ACTIVE 可用
無效轉換：直接報錯
```

### `vibe sync` 語意（純 git 附加，不依賴 LLM）

1. `git log --oneline <last-sync>..HEAD` → commit 列表
2. `git diff --stat <last-sync>..HEAD` → 變更檔案
3. **附加**結構化區塊到 `state/current.md`（非覆寫，保留 AI checkpoint）
4. HEAD hash 存入 `state/.sync-cursor`
5. C.L.E.A.R. → 輸出空白模板供填寫
6. 非 git 專案：跳過 git 操作 + 提示手動更新

### Adapter 安全機制

- **快照比對**：`emit()` 時存份到 `.vibe/snapshots/<tool>/`
- **備份**：`--remove` 前備份到 `.vibe/backups/<tool>/<timestamp>/`，保留 3 份
- **預設 dry-run**：`--remove` 需 `--confirm` 才執行
- **frontmatter 驗證**：每個 adapter 定義 `REQUIRED_FIELDS`，emit 後自動 validate

### Adapter 按需生成策略（三層）

1. `vibe init` 自動偵測已有 AI/IDE 痕跡
2. 無痕跡時互動式多選（AGENTS.md 預設勾選）
3. `vibe adapt --add/--remove/--list/--sync` 事後增減

跨檔案去重：Claude + AGENTS.md 同時啟用時，CLAUDE.md 用 `@AGENTS.md` 匯入通用部分。單獨啟用任一 adapter 時自包含完整內容。

### Adapter 目標工具規格（已驗證）

| # | Adapter | 輸出 | Frontmatter | 驗證欄位 |
| --- | --- | --- | --- | --- |
| 1 | AGENTS.md | `AGENTS.md` | 無 | ≤32KiB |
| 2 | Claude Code | `CLAUDE.md` + `.claude/rules/*.md` + `.claude/settings.json` | `paths` | list |
| 3 | Cursor | `.cursor/rules/*.mdc` | `alwaysApply`, `description`, `globs` | bool |
| 4 | Copilot | `.github/copilot-instructions.md` + `.github/instructions/*.instructions.md` | `applyTo`, `excludeAgent` | glob |
| 5 | Windsurf | `.windsurf/rules/*.md` | `trigger`, `description`, `globs` | enum |
| 6 | Cline | `.clinerules/*.md` | `paths` | list |
| 7 | Roo Code | `.roo/rules/*.md` | 無 | 純 Markdown |
| 8 | Codex CLI | 同 #1（AGENTS.md 共用） | 無 | ≤32KiB |

### 技術堆疊

| 類別 | 技術 | 版本 |
| --- | --- | --- |
| 語言 | Python | ≥3.10 |
| CLI 框架 | Typer | latest |
| 終端美化 | Rich | latest |
| 模板引擎 | Jinja2 | latest |
| Markdown 解析 | markdown-it-py | latest |
| 建置系統 | hatchling | latest |
| 套件管理 | uv | latest |
| 部署 | PyPI + pipx | - |
| MCP（P4） | mcp Python SDK | ≥1.27.0 |
| 文件 | mkdocs-material | - |
| CI/CD | GitHub Actions | - |
| Linter | ruff | - |
| 型別檢查 | mypy | - |
| 測試 | pytest | - |

### Python 套件結構

```text
src/vibe_state/
├── __init__.py
├── cli.py                  # Typer app（含 vibe adapt/reopen）
├── core/
│   ├── scanner.py          # ScanResult dataclass + 偵測鏈
│   ├── compactor.py        # markdown-it-py AST 解析 + 歸檔
│   ├── git_ops.py          # Git 唯讀操作 + .sync-cursor
│   ├── state.py            # .vibe/state/ 讀寫驗證
│   └── lifecycle.py        # 狀態機（.lifecycle 讀寫 + 轉換檢查）
├── adapters/
│   ├── base.py             # AdapterBase ABC（detect/emit/clean/validate）
│   ├── registry.py         # 自動發現 + 按需執行
│   ├── claude.py           # → CLAUDE.md + .claude/rules/*.md
│   ├── cursor.py           # → .cursor/rules/*.mdc
│   ├── copilot.py          # → .github/copilot-instructions.md
│   ├── windsurf.py         # → .windsurf/rules/*.md
│   ├── cline.py            # → .clinerules/*.md
│   ├── roo.py              # → .roo/rules/*.md
│   └── agents_md.py        # → AGENTS.md
├── templates/              # Jinja2 模板
│   ├── vibe.md.j2
│   ├── state/*.md.j2
│   ├── skills/*.md.j2
│   └── adapters/           # 各工具專用模板
├── config.py               # config.toml Schema + 載入 + 遷移
└── safety.py               # 快照/備份/dry-run 安全機制
```

### config.toml Schema

```toml
[vibe]
version = 1
lang = "en"               # "en" | "zh-TW"

[state]
compact_threshold = 150
stale_task_days = 30       # [~] 擱置標記閾值

[adapters]
enabled = ["agents_md"]
auto_detect = true

[git]
enabled = true
auto_commit = false
```

### 環境限制與相依性

- 跨平台（Windows、macOS、Linux）：全面使用 pathlib.Path
- Git 可選：`shutil.which("git")` 偵測，找不到則 `git.enabled = false`
- 編碼：所有讀寫 `encoding="utf-8"` + `newline="\n"`
- subprocess：不用 `shell=True`，傳引數列表
- AGENTS.md（AAIF 標準）：Claude Code 不原生讀取，需 `@AGENTS.md` 匯入（僅兩者同時啟用時）
- 各工具 frontmatter schema 完全不同，各自生成 + validate
- MCP 協議版本 `2025-11-25`，Python SDK v1.27.0+

---

## 架構決策歷史

### [2026-04-07] 架構全面校正：三大致命缺陷修復

決策：(1) VIBE.md 從 SSOT 降級為 Constitution；(2) vibe sync 改為純 git 附加不依賴 LLM；(3) adapt --remove 加入三層安全機制。
原因：三路獨立審查發現 SSOT 悖論（VIBE.md 無更新機制）、sync 語意不可能（git 無法產生語意進度）、remove 毀滅性操作無防護。

### [2026-04-07] 嚴格狀態機 + vibe reopen

決策：加入 .lifecycle 狀態追蹤（UNINIT→READY→ACTIVE→CLOSED），無效轉換報錯。新增 vibe reopen 指令。
原因：審查發現指令可亂序執行（sync before start），需防護。結案後需支援熱修復重開。

### [2026-04-07] task.md 擱置機制 [~]

決策：>30 天未動的 [ ] 任務自動標記 [~]（擱置），compact 時移至 archive 擱置區。
原因：「不刪除任何任務」原則導致 task.md 無限增長，compaction 只處理 [x] 不夠。

### [2026-04-07] Markdown 解析改用 AST

決策：棄用 regex，改用 markdown-it-py 解析 task.md 為 AST。
原因：regex 無法正確處理巢狀任務、多行描述、code block。

### [2026-04-07] 使用者決策：全量 adapter

決策：8 個 adapter 全部內建，不採用 plugin 機制。
原因：使用者選擇開箱即用優先於維護成本。每個 adapter 加入 frontmatter validate 降低風險。

### [2026-04-07] Adapter 按需生成 + 條件式去重

決策：三層按需策略（偵測→選擇→adapt 增減）。Claude + AGENTS.md 同時啟用時用 @AGENTS.md 匯入去重。
原因：避免生成使用者不需要的檔案。

### [2026-04-07] 技術堆疊定案

決策：hatchling + uv + Typer + Rich + Jinja2 + markdown-it-py + MIT License
原因：2026 Python 生態事實標準。markdown-it-py 新增以取代 regex 解析。
