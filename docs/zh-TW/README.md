# vibe-state-cli

**廠商中立的 AI-人類協作狀態管理 CLI 工具。**

讓任何 AI 模型 — Claude、GPT、Gemini 或本地模型 — 透過讀取一個 `.vibe/` 目錄，瞬間與你的專案上下文同步。

## 安裝

```bash
pipx install vibe-state-cli
```

## 快速開始

```bash
cd my-project

vibe init                # 初始化 .vibe/（自動偵測語言、框架、AI 工具）
vibe start               # 每日開工 — 載入狀態、git 校驗、自動壓縮
vibe sync                # 每日收工 — 附加 git 狀態、C.L.E.A.R. 審查
vibe sync --compact      # 歸檔已完成任務、壓縮狀態檔
vibe sync --close        # 專案結案 — 最終同步 + 回顧報告
vibe status              # 查看專案狀態（隨時可用）
vibe adapt --list        # 查看已啟用的 AI 工具 adapter
```

## 五個指令

| 指令 | 時機 | 功能 |
|------|------|------|
| `vibe init` | 一次 | 掃描專案、生成 `.vibe/`、偵測 AI 工具、產出 adapter 檔案 |
| `vibe start` | 每天 | 載入狀態、git 校驗、需要時自動壓縮、Rich 摘要 |
| `vibe sync` | 每天 | 附加 git 狀態、C.L.E.A.R. 審查 |
| `vibe status` | 隨時 | 顯示 lifecycle、任務數、檔案大小 |
| `vibe adapt` | 按需 | `--add`/`--remove`/`--list`/`--sync` adapter 檔案 |

### 旗標

- `vibe init --lang zh-TW` — 繁體中文模板
- `vibe init --force` — 重新初始化或重開已結案專案
- `vibe sync --compact` — 同步後壓縮記憶
- `vibe sync --close` — 專案結案
- `vibe adapt --remove cursor --dry-run` — 預覽刪除
- `vibe adapt --remove cursor --confirm` — 刪除並備份

## 支援的 AI 工具

| 工具 | 生成的設定檔 | 自動偵測 |
|------|-------------|---------|
| AGENTS.md | `AGENTS.md` | `AGENTS.md` 已存在 |
| Claude Code | `CLAUDE.md` + `.claude/rules/` | `.claude/` 目錄 |
| Antigravity / Gemini | `GEMINI.md` | `GEMINI.md` 或 `.gemini/` |
| Cursor | `.cursor/rules/*.mdc` | `.cursor/` 目錄 |
| GitHub Copilot | `.github/copilot-instructions.md` | 既有 copilot 設定 |
| Windsurf | `.windsurf/rules/*.md` | `.windsurf/` 目錄 |
| Cline | `.clinerules/*.md` | `.clinerules/` 目錄 |
| Roo Code | `.roo/rules/*.md` | `.roo/` 目錄 |

只有偵測到的工具才會生成設定檔。不會產生多餘檔案。

## 安全機制

- `vibe adapt --remove` 預設 **dry-run** — 需要 `--confirm` 才執行
- 每次生成都保存快照用於差異偵測
- 刪除前自動備份（保留最近 3 份）
- 使用者手動修改的檔案會觸發覆寫警告

## Autoresearch 整合

支援 [autoresearch](https://github.com/uditgoenka/autoresearch) 自動優化迴圈。`vibe sync` 自動偵測實驗 commit 並記錄到 `state/experiments.md`。

## 授權

MIT
