# vibe-state-cli

[English](../../README.md) | [繁體中文](README.md)

**你的 AI 每次關掉對話就什麼都忘了。這個工具解決這件事。**

## 問題在哪

你花兩小時跟 Claude 解釋專案架構。關掉終端。明天 Claude 完全不記得你說過什麼。

你在 Cursor 修好一個 bug，切到 Claude Code 做更大的重構。Claude 不知道你剛才在 Cursor 做了什麼。

你的 coding standards 散落在 CLAUDE.md、.cursorrules、AGENTS.md — 三份檔案講一樣的事，每一份都在吃 token。

## vibe-state-cli 做什麼

讓所有 AI 工具共用**同一個大腦**。

在你的專案裡放一個 `.vibe/` 目錄，存你的進度、任務、規範。換工具時，新的 AI 直接從上一個 AI 停下的地方接手。

```bash
vibe init      # 掃描專案，偵測你在用哪些 AI 工具，建立 .vibe/
vibe start     # 開工 — AI 自動看到你的最新進度
vibe sync      # 收工 — 把今天的 git 變更存起來
vibe status    # 隨時看目前狀態
vibe adapt     # 新增或移除 AI 工具支援
```

## 原理

每個 AI 工具都有一個它會自動讀的設定檔 — Claude 讀 CLAUDE.md，Cursor 讀 `.cursor/rules/*.mdc`，Gemini 讀 GEMINI.md。

`vibe sync` 和 `vibe start` 把**壓縮後的狀態摘要**直接寫進每個工具的設定檔。AI 讀自己的設定檔 → 看到你的最新進度。不需要外掛、不需要 API。

```text
你用 Claude 工作 → Claude 把進度寫進 .vibe/state/
     ↓
vibe sync → 抓 git log → 壓縮成 5 行摘要 → 寫進所有設定檔
     ↓
切到 Cursor → Cursor 載入 .mdc → 看到 Claude 剛才做了什麼
```

**Git 是唯一可靠的紀錄。** AI 的 checkpoint（更新 tasks.md）有時候會漏。但 `vibe sync` 從 git log 抓的不會錯。

## 舊專案遷移

已經有 CLAUDE.md、.cursorrules 或 AGENTS.md？直接跑 `vibe init`。

它會抽取你的規則、把原檔歸檔到 `.vibe/archive/legacy/`（不會刪除），然後生成乾淨的新設定檔。

如果你的規則不是用 `- bullet` 格式寫的，vibe 會警告你並**保留原檔不動**。

## AutoResearch — 實驗迴圈

vibe 跟 [autoresearch](https://github.com/uditgoenka/autoresearch) 天然搭配。autoresearch 是自主優化框架。

vibe 是**記憶層**，autoresearch 是**進化層**。兩者形成閉環：

```text
/autoresearch:plan  → 定義要優化什麼（覆蓋率、速度、分數）
/autoresearch       → AI 跑實驗：修改 → 測試 → 保留或回滾
vibe sync           → 自動記錄哪些實驗成功了
vibe start          → 下次開工看到「5 kept, 2 reverted」
                      → AI 從過去的實驗中學習
```

所有 adapter 輸出都已經告訴 AI 有 autoresearch 可用 — 遇到可量化的目標時，AI 會主動建議 `/autoresearch`。

## 每個工具拿到什麼

| 工具 | vibe 生成什麼 | AI 看到什麼 |
| ---- | ------------ | ---------- |
| Claude Code | `CLAUDE.md` + rules + 5 個 slash command | 透過 @import 取得完整 state |
| Cursor | `.cursor/rules/vibe-standards.mdc` | Standards + 摘要內嵌 |
| Windsurf | `.windsurf/rules/vibe-standards.md` | Standards + 摘要內嵌 |
| Cline | `.clinerules/01-vibe-standards.md` | Standards + 摘要內嵌 |
| Roo Code | `.roo/rules/01-vibe-standards.md` | Standards + 摘要內嵌 |
| Antigravity/Gemini | `GEMINI.md` | 完整（舊版有 fallback） |
| GitHub Copilot | `.github/copilot-instructions.md` | 僅摘要（Copilot 無法讀檔） |
| AGENTS.md | `AGENTS.md` | 完整 — 跨工具標準 |

## 不做什麼

- **不呼叫任何 API。** 完全離線，沒有遙測。
- **不碰你的 git。** 只讀取，不會 commit 或 push。
- **不綁架你。** `.vibe/` 是純 Markdown，隨時刪掉就好。
- **不改變你的工作方式。** 你還是用原本的方式跟 AI 對話。vibe 只是確保 AI 記得。

## 安裝

```bash
pipx install vibe-state-cli
```

## 安全

- 設定檔移除預設 **dry-run**，要 `--confirm` 才會真的刪
- 遷移是 **two-phase**：全部複製 → 驗證 → 才刪除原檔
- 檔案寫入是**原子的**，Windows 有 retry 防防毒鎖檔
- Symlink 和 NTFS Junction 穿越**阻擋**
- config.toml 損壞**直接報錯停住**，不會偷偷用預設值
- Advisory lock 保護**併發寫入**（CI 環境）
- Checkpoint 誠實標示為 **best-effort（~40-60%）**

## 授權

MIT
