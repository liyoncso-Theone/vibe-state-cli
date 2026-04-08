# vibe-state-cli

[English](../../README.md) | [繁體中文](README.md)

**讓你的 AI 助手不再失憶。**

## vibe-state-cli 做什麼

在你的專案裡建一個 `.vibe/` 資料夾，當作你和所有 AI 工具之間的**共享大腦**。不管你用 Claude Code、Cursor 還是 Copilot，它們都讀同一份狀態 — 你的進度、任務、架構決策、編碼規範。

五個指令，就這樣：

```bash
vibe init      # 掃描專案，建立 .vibe/，偵測你在用哪些 AI 工具
vibe start     # 載入昨天的進度，檢查 git，告訴你今天該做什麼
vibe sync      # 把今天的 git 變更存起來，跑 C.L.E.A.R. 自我審查
vibe status    # 看一下專案目前的狀態（隨時可用）
vibe adapt     # 新增或移除 AI 工具的設定檔
```

## vibe-state-cli 想解決什麼問題

AI 寫程式很強，但每次關掉對話就全忘了。你花時間解釋過的專案背景、寫好的規範、做到一半的進度，下次開對話又要重來一遍。更慘的是，如果你同時用好幾個 AI 工具，每一個都活在自己的孤島裡 — Claude 不知道你在 Cursor 做了什麼，Copilot 不知道你跟 Gemini 討論過什麼。

vibe-state-cli 把所有 AI 工具的記憶統一到同一個地方。

另外，它會防止你的 AI 上下文越積越肥。當 `current.md` 和 `tasks.md` 的歷史紀錄越來越多，內建的壓縮器會用 **Markdown AST 語法樹解析**，安全地移除舊的段落，保證不會切斷程式碼區塊或破壞文件結構。

## vibe-state-cli 不做什麼

- **不取代你現有的設定。** 如果你已經有 `CLAUDE.md`、`.cursorrules` 或 `AGENTS.md`，vibe 會匯入你的規則，但不會動你的原始檔案。它是加法，不是減法。
- **不需要 API key。** 完全離線運作。不傳任何資料出去，沒有遙測。
- **不綁架你。** `.vibe/` 裡面全是純 Markdown，你隨時可以讀、改、刪。沒有專有格式。
- **不改變你跟 AI 的互動方式。** 你還是用原本的方式跟 Claude、Cursor、Copilot 對話。vibe 只是確保每次開 session 時，AI 手上都有正確的上下文。
- **不會幫你 commit 或 push。** 它只讀取 git 狀態，不碰你的程式碼庫。

## 安裝

```bash
pipx install vibe-state-cli
```

> 為什麼用 `pipx` 不用 `pip`？因為這是 CLI 工具，不是函式庫。`pipx` 會自動建隔離環境，不會跟你的專案依賴打架。如果還沒裝 pipx：`pip install pipx`

## 智慧遷移

已經有 AI 設定檔了？vibe 會自動偵測：

```text
$ vibe init
Scanning project...

Found 2 existing config file(s):
  - CLAUDE.md
  - .cursorrules
Imported 9 rules into .vibe/state/standards.md

The following legacy config files have been imported into .vibe/
and are no longer needed:
  - CLAUDE.md
  - .cursorrules
```

你的規則完整保留。你的檔案不會被覆蓋。什麼時候要清理，由你決定。

## 支援哪些 AI 工具？

| 工具 | vibe 會幫你生成 | 怎麼偵測 |
| ---- | --------------- | -------- |
| Claude Code | `.claude/rules/vibe-standards.md` + `.claude/skills/vibe-*/SKILL.md` | 有 `.claude/` 資料夾 |
| Cursor | `.cursor/rules/vibe-standards.mdc` | 有 `.cursor/` 資料夾 |
| GitHub Copilot | `.github/copilot-instructions.md` | 有 copilot 設定檔 |
| Windsurf | `.windsurf/rules/vibe-standards.md` | 有 `.windsurf/` 資料夾 |
| Cline | `.clinerules/01-vibe-standards.md` | 有 `.clinerules/` 資料夾 |
| Roo Code | `.roo/rules/01-vibe-standards.md` | 有 `.roo/` 資料夾 |
| Antigravity / Gemini | `GEMINI.md` | 有 `GEMINI.md` 或 `.gemini/` |
| AGENTS.md（通用標準） | `AGENTS.md` | 預設生成 |

只生成有在用的工具的設定，不會多生垃圾。多個 adapter 同時啟用時，自動去除重複內容節省 Token。

**所有 adapter 內建 Vibe Commands**：生成的每一份設定檔都包含「Vibe Commands」區塊，告訴 AI「當使用者說 `vibe sync`，直接在終端執行，不要解釋」。不需要任何外掛就能跨工具通用。

**Claude Code 額外加分**：Claude adapter 會自動生成 [Agent Skills](https://agentskills.io/)（`/vibe-init`、`/vibe-start`、`/vibe-sync`、`/vibe-status`、`/vibe-adapt`），在 Claude Code、Cline 等支援開放 skill 標準的工具裡可以直接當 slash command 用。

## 搭配 Autoresearch 自動進化

支援 [autoresearch](https://github.com/uditgoenka/autoresearch) — 自主迭代框架，對任何可量化的目標執行 **修改 → 驗證 → 保留/捨棄 → 重複** 循環（測試覆蓋率、效能、Lighthouse 分數、安全漏洞數等）。

**怎麼搭配：**

1. 在 AI 工具裡跑 autoresearch（例如 Claude Code 裡打 `/autoresearch`）
2. Autoresearch 自動做原子修改、commit、跑 metric、決定保留或回滾
3. 跑 `vibe sync` 時，自動掃 git 歷史中的實驗 commit，記錄到 `state/experiments.md`
4. `vibe start` 顯示摘要：「5 kept, 2 reverted」

**偵測的 commit pattern**（可在 `.vibe/config.toml` 自訂）：

```text
autoresearch:    experiment:    [autoresearch]    [experiment]    auto-research
```

**回滾偵測**：只有 `revert`、`reset`、`rollback` 等關鍵字出現在訊息**前綴**時才判定為 REVERTED（例如 `autoresearch: revert - metric dropped`），不會把 `experiment: fix revert payment issue` 誤判為回滾。

**自訂 pattern**（`.vibe/config.toml`）：

```toml
[experiments]
commit_patterns = ["autoresearch:", "experiment:", "[autoresearch]", "[experiment]", "auto-research"]
revert_prefixes = ["revert", "reset", "rollback", "undo"]
```

## 安全機制

- 刪除 adapter 預設 **dry-run** — 確認才會動手
- 每次生成都存快照，要覆蓋時會先警告你有沒有手動改過
- 刪除前自動備份（保留最近 3 份）
- 設定檔損壞時直接停住，不會偷偷用預設值跑（防止誤刪資料）
- 寫入是原子操作（temp + rename），搭配指數退避鎖防止併發衝突

## 授權

MIT — 隨便用，不用付錢。
