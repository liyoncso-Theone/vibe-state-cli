# vibe-state-cli

[English](../../README.md) | [繁體中文](README.md)

**讓你的 AI 助手不再失憶。**

不管你用的是 Claude、Cursor、Copilot 還是其他工具，每次關掉對話，AI 就什麼都忘了。`vibe-state-cli` 幫你在專案裡建一個 `.vibe/` 資料夾當作共享大腦 — 任何 AI 工具打開就能接上之前的進度。

## 為什麼需要 vibe-state-cli？

| 你一定遇過這些問題 | vibe-state-cli 怎麼幫你 |
|---|---|
| 跟 AI 討論了兩小時的架構，關掉終端就全忘了 | `.vibe/state/` 把進度存在專案裡，換 session 也不會斷 |
| 早上用 Claude Code，下午切 Cursor，兩邊互不認識 | 8 種工具的設定檔自動生成，共用同一份狀態 |
| CLAUDE.md 越寫越肥，AI 開始胡說八道 | `vibe sync --compact` 自動歸檔舊任務，Token 控制在安全水位 |
| 每次開新對話都要手動貼一大堆背景資料 | `vibe init` 一鍵掃描你的專案，全部幫你生好 |
| 昨天做到哪了？AI 不記得，你也忘了 | `vibe sync` 自動把 git 紀錄寫進狀態檔，明天一開就能接著做 |

完全離線，不需要 API key，不傳任何資料出去。

## 安裝

```bash
pip install vibe-state-cli
```

## 三分鐘上手

```bash
cd my-project

vibe init                # 初始化（自動偵測你的語言、框架、用哪些 AI 工具）
vibe start               # 開工（載入昨天的進度，順便幫你整理過長的檔案）
vibe sync                # 收工（把今天的 git 變更存進去，列出審查清單）
```

就這樣。日常只需要這三個指令。

## 全部指令一覽

| 指令 | 什麼時候用 | 做什麼 |
|------|-----------|--------|
| `vibe init` | 專案開始時跑一次 | 掃描專案，建立 `.vibe/`，偵測你在用哪些 AI 工具並生成對應設定 |
| `vibe start` | 每天開工 | 讀取狀態、比對 git、太長的自動壓縮，最後秀出今天的待辦摘要 |
| `vibe sync` | 每天收工 | 把 git commit 紀錄附加到狀態檔，跑 C.L.E.A.R. 自我審查 |
| `vibe status` | 想看就看 | 秀出專案目前的狀態：進度、任務數、檔案大小 |
| `vibe adapt` | 需要時 | 管理 AI 工具的設定檔：新增、移除、同步、預覽 |

### 常用參數

```bash
vibe init --lang zh-TW       # 用繁體中文模板
vibe init --force             # 重新初始化（也可以拿來重開已結案的專案）
vibe sync --compact           # 收工時順便壓縮舊資料
vibe sync --close             # 專案做完了，產出回顧報告並結案
vibe adapt --add cursor       # 加入 Cursor 的設定檔
vibe adapt --remove cursor    # 預覽會刪什麼（預設不會真的刪）
vibe adapt --list             # 看哪些工具已啟用
```

## 支援哪些 AI 工具？

| 工具 | 會幫你生成 | 怎麼偵測 |
|------|-----------|---------|
| AGENTS.md（通用標準） | `AGENTS.md` | 專案裡已有 `AGENTS.md` |
| Claude Code | `CLAUDE.md` + `.claude/rules/` | 有 `.claude/` 資料夾 |
| Antigravity / Gemini | `GEMINI.md` | 有 `GEMINI.md` 或 `.gemini/` |
| Cursor | `.cursor/rules/*.mdc` | 有 `.cursor/` 資料夾 |
| GitHub Copilot | `.github/copilot-instructions.md` | 有 copilot 設定檔 |
| Windsurf | `.windsurf/rules/*.md` | 有 `.windsurf/` 資料夾 |
| Cline | `.clinerules/*.md` | 有 `.clinerules/` 資料夾 |
| Roo Code | `.roo/rules/*.md` | 有 `.roo/` 資料夾 |

只會幫你生有在用的工具的設定，不會多生垃圾檔案。兩個以上工具同時啟用時，會自動去除重複內容節省 Token。

## 安全機制

- 刪除設定檔前會先秀預覽，確認才會動手（還會自動備份最近 3 份）
- 每次生成檔案都存快照，下次要覆蓋時會偵測你有沒有手動改過
- Clone 別人的專案如果裡面有 `.vibe/`，`vibe start` 會跳警告提醒你檢查
- 狀態檔不能拿來注入惡意指令（有掃描機制）

## 搭配 Autoresearch 自動進化

如果你有用 [autoresearch](https://github.com/uditgoenka/autoresearch) 做自動優化實驗，`vibe sync` 會自動偵測實驗性的 git commit，幫你分類哪些成功保留、哪些已經回滾，紀錄在 `state/experiments.md`。

下次 `vibe start` 開工時，面板直接告訴你：「昨晚跑了 50 輪實驗，12 個保留、38 個回滾。」

## 授權

MIT — 隨便用，不用付錢。
