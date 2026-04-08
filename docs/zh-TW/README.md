# vibe-state-cli

[English](../../README.md) | [繁體中文](README.md)

**你的 AI 每次開 session 都失憶。這個工具修好它。**

## 它做什麼

在你的專案裡建一個 `.vibe/` 目錄，當作所有 AI 工具的**共享大腦**。你在 Claude Code 做的事，切到 Cursor 或 Gemini 時，AI 直接知道。

五個指令：

```bash
vibe init      # 掃描專案，建立 .vibe/，偵測你在用哪些 AI 工具
vibe start     # 開工：載入狀態，刷新設定檔，AI 自動看到最新進度
vibe sync      # 收工：從 git 抓今天的變更，更新所有 AI 的設定檔
vibe status    # 隨時看目前狀態
vibe adapt     # 新增或移除 AI 工具的設定檔
```

## 為什麼需要它

- AI 每次開對話就**失憶**。你昨天花兩小時解釋的架構，今天要重來一遍。
- 你用多個工具，但它們**各自為政**。Claude 不知道你在 Cursor 做了什麼。
- 每個工具的設定檔格式不同（CLAUDE.md、.cursorrules、GEMINI.md），你的規則**散落各處，互相重複，吃 token**。

vibe-state-cli 把記憶統一到 `.vibe/state/`，把規則統一到 `AGENTS.md`，然後自動幫每個工具生成它能讀的設定檔。

## 不做什麼

- **不取代你的現有設定。** 有 CLAUDE.md？vibe 匯入你的規則再幫你歸檔原檔到 `.vibe/archive/legacy/`。
- **不需要 API key。** 完全離線，沒有遙測。
- **不綁架你。** `.vibe/` 裡面全是 Markdown，隨時可讀可改可刪。
- **不碰你的 git。** 只讀 git status，不會 commit 或 push。

## 安裝

```bash
pipx install vibe-state-cli
```

> 為什麼用 `pipx` 不用 `pip`？因為這是 CLI 工具，不是函式庫。`pipx` 自動建隔離環境，不會跟你的專案依賴打架。

## 舊專案遷移

已經有 AI 設定檔？`vibe init` 自動處理：

1. 偵測你的 CLAUDE.md、.cursorrules、AGENTS.md 等
2. 抽取規則到 `.vibe/state/standards.md`
3. 原檔搬到 `.vibe/archive/legacy/`（不刪，可追溯）
4. 生成全新的標準格式設定檔

如果你的規則不是用 `- bullet` 格式寫的，vibe 會警告你並**保留原檔不動**，讓你手動處理。

## 跨工具同步怎麼運作

```text
你用 Claude 工作 → checkpoint 寫入 .vibe/state/
     ↓
vibe sync → 抓 git log + 壓縮摘要 → 注入 AGENTS.md、.cursor/rules/ 等所有設定檔
     ↓
切到 Gemini/Cursor → 自動載入設定檔 → 看到 Claude 的進度
```

核心原理：`vibe sync` 和 `vibe start` 每次都把**壓縮後的狀態摘要**寫進各工具的設定檔。工具自動載入自己的設定檔，就看到最新狀態。

**Git 是唯一可靠的記錄。** AI 的 checkpoint（更新 tasks.md）是 best-effort，遵從率約 40-60%。`vibe sync` 從 git log 抓的是確定性的。

## 支援哪些工具

| 工具 | vibe 生成什麼 | 同步深度 |
| ---- | ------------ | ------- |
| Claude Code | `CLAUDE.md` + `.claude/rules/` + 5 個 slash command | **完整** |
| Cursor | `.cursor/rules/vibe-standards.mdc`（含內嵌規則） | **完整**（compact） |
| Windsurf | `.windsurf/rules/vibe-standards.md` | **完整**（compact） |
| Cline | `.clinerules/01-vibe-standards.md` | **完整**（compact） |
| Roo Code | `.roo/rules/01-vibe-standards.md` | **完整**（compact） |
| Antigravity/Gemini | `GEMINI.md`（含 fallback body） | **完整** |
| GitHub Copilot | `.github/copilot-instructions.md` | **摘要**（無法讀檔） |
| AGENTS.md | `AGENTS.md`（跨工具標準） | 依工具而定 |

**同步深度**：

- **完整**：工具收到規則 + 狀態摘要，部分工具能進一步讀 `.vibe/state/` 完整檔案
- **compact**：規則和 standards 直接內嵌在設定檔裡（不依賴 AI 去讀其他檔案）
- **摘要**：只收到壓縮的 5 行摘要（Copilot 的能力限制，非 vibe 的問題）

## 安全

- 設定檔移除預設 **dry-run**，要 `--confirm` 才會真的刪
- 遷移是 **two-phase**：全部複製 → 驗證 → 才刪除原檔
- 檔案寫入是原子的（temp + rename），Windows 有 retry 防防毒鎖檔
- Symlink 和 NTFS Junction 穿越阻擋
- config.toml 損壞直接報錯停住，不會偷偷用預設值
- Advisory lock 保護併發寫入（CI 環境）

## 授權

MIT — 隨便用，不用付錢。
