# vibe-state-cli

[English](../../README.md) | [繁體中文](README.md)

**你的 AI 每次關掉對話就什麼都忘了。這個工具解決這件事。**

## 問題在哪

你花兩小時跟 Claude 解釋專案架構。關掉終端。明天 Claude 完全不記得你說過什麼。

你在 Cursor 修好一個 bug，切到 Claude Code 做更大的重構。Claude 不知道你剛才在 Cursor 做了什麼。

你的 coding standards 散落在 CLAUDE.md、.cursorrules、AGENTS.md — 三份檔案講一樣的事，每一份都在吃 token。

## vibe-state-cli 做什麼

讓所有 AI 工具共用**同一個大腦**。

在你的專案裡放一個 `.vibe/` 目錄，存你的進度、任務、規範。換工具時，新的 AI 直接從上一個停下的地方接手。

## 快速開始（2 分鐘）

### 1. 安裝（全電腦一次，之後不用管）

打開任何終端，跑這三行：

```bash
pip install pipx
pipx ensurepath
pipx install vibe-state-cli
```

然後**關掉終端，重新開一個**。

> **pipx 是什麼？** 跟 `pip install` 類似，但專門給 CLI 工具用。它把 `vibe` 裝在隔離環境裡，不會跟你專案的套件打架。全電腦只要裝一次，之後在任何資料夾都能用 `vibe`。
>
> **重要：** 跑完 `pipx ensurepath` 之後，要**重啟所有開著的終端和 IDE**。新的 PATH 只在重新打開的視窗裡生效。

### 2. 初始化專案（每個專案一次）

```bash
cd your-project
vibe init --lang zh-TW       # 或：vibe init（英文版）
```

它會掃描你的專案、建立 `.vibe/`、幫每個 AI 工具生成設定檔。如果你已經有 CLAUDE.md 或 .cursorrules，vibe 會匯入你的規則，原檔安全歸檔。

**這是唯一需要打字在終端的時刻。**

### 3. 日常使用 — 跟 AI 說就好

從現在開始，所有操作都透過 AI 對話。不需要開終端。

| 你想做什麼 | 跟 AI 說 |
| ---------- | -------- |
| 開工 | 「vibe start」 |
| 存進度 | 「vibe sync」 |
| 看狀態 | 「vibe status」 |

AI 看到 vibe 生成的設定檔，知道這些是終端指令，會幫你執行。

> **如果 AI 說「command not found」怎麼辦？** 不用擔心。AI 會自動改成直接讀你的 `.vibe/state/` 檔案，一樣能拿到所有上下文。這是設計好的。

## 原理

每個 AI 工具都有一個它會自動讀的設定檔 — Claude 讀 CLAUDE.md，Cursor 讀 `.cursor/rules/*.mdc`，Gemini 讀 GEMINI.md。

當你說「vibe sync」，工具會：

1. 抓你最新的 git commits
2. 壓縮成 5 行摘要
3. 把摘要寫進**每一個** AI 工具的設定檔

下次任何 AI 啟動時，它載入自己的設定檔，就能看到你的最新進度。不需要外掛、不需要 API。

**Git 是唯一可靠的紀錄。** AI 有時候會忘記更新 tasks.md — 沒關係。`vibe sync` 從 git log 抓的不會錯。

## AutoResearch — 實驗迴圈

vibe 跟 [autoresearch](https://github.com/uditgoenka/autoresearch) 天然搭配。autoresearch 是自主優化框架。

vibe 是**記憶層**，autoresearch 是**進化層**。兩者一起用：

```text
/autoresearch:plan  → 定義要優化什麼（覆蓋率、速度、分數）
/autoresearch       → AI 自動跑實驗
vibe sync           → 自動記錄哪些實驗成功
vibe start          → 下次開工，AI 從過去的實驗中學習
```

## 支援哪些工具

| 工具 | AI 看到什麼 |
| ---- | ---------- |
| Claude Code | 完整狀態 + 5 個快捷指令（`/vibe-start` 等） |
| Cursor | 規範 + 狀態摘要（內嵌在 rules 裡） |
| Windsurf | 規範 + 狀態摘要（內嵌） |
| Cline | 規範 + 狀態摘要（內嵌） |
| Roo Code | 規範 + 狀態摘要（內嵌） |
| Antigravity/Gemini | 完整狀態（舊版有 fallback） |
| GitHub Copilot | 僅摘要（Copilot 無法瀏覽專案檔案） |

## 不做什麼

- **不呼叫任何 API。** 完全離線，沒有遙測，沒有網路。
- **不碰你的 git。** 只讀取，不會 commit 或 push。
- **不綁架你。** `.vibe/` 是純 Markdown，隨時刪掉就好。
- **不改變你的工作方式。** 你還是用原本的方式跟 AI 對話。vibe 只是確保 AI 記得。

## 更新

```bash
pipx upgrade vibe-state-cli
```

## 安全

- 設定檔移除預設 **dry-run**，要 `--confirm` 才會真的刪
- 遷移是 **two-phase**：全部複製 → 驗證 → 才刪除原檔
- 檔案寫入是**原子的**，Windows 有 retry 防防毒鎖檔
- Symlink 和 NTFS Junction 穿越**阻擋**
- config.toml 損壞**直接報錯停住**，不會偷偷用預設值
- Checkpoint 誠實標示為 **best-effort（~40-60%）**

## 授權

MIT
