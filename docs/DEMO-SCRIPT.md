# Demo 錄製腳本

> 用 [asciinema](https://asciinema.org/) 或 [VHS](https://github.com/charmbracelet/vhs) 錄製。
> 預計時長：GIF 約 30 秒，完整 demo 約 2 分鐘。

---

## GIF 動畫腳本（30 秒）

**目標**：展示 `init → start → sync` 三個核心指令。

```bash
# 準備（錄製前先跑好，不入鏡）
mkdir ~/demo-app && cd ~/demo-app
git init
echo '{"name":"my-app","dependencies":{"react":"^19"}}' > package.json
echo "console.log('hello')" > index.js
git add -A && git commit -m "feat: initial app"

# === 開始錄製 ===

# 1. Init（5 秒）
vibe init
# 停頓 2 秒讓觀眾看輸出

# 2. Start（5 秒）
vibe start
# 停頓 2 秒

# 3. Sync（5 秒）
vibe sync
# 停頓 2 秒

# 4. Status（5 秒）
vibe status
# 停頓 3 秒

# === 結束錄製 ===
```

**VHS 腳本**（如果用 [VHS](https://github.com/charmbracelet/vhs)）：

```
# demo.tape
Output demo.gif
Set Theme "Catppuccin Mocha"
Set FontSize 16
Set Width 900
Set Height 500

Type "vibe init"
Enter
Sleep 3s

Type "vibe start"
Enter
Sleep 3s

Type "vibe sync"
Enter
Sleep 3s

Type "vibe status"
Enter
Sleep 4s
```

---

## 2 分鐘完整 Demo 腳本

**場景**：一個 React 開發者使用 vibe-state-cli 管理 AI 協作狀態。

### Part 1：初始化（30 秒）

```bash
# 旁白：「讓我們看看 vibe-state-cli 如何運作。」
cd my-react-app
ls    # 展示這是一個真實的 React 專案

# 旁白：「一個指令初始化。」
vibe init
# 展示輸出：偵測到 Node.js + React，生成 AGENTS.md

# 旁白：「它自動偵測了語言和框架。」
```

### Part 2：日常工作（30 秒）

```bash
# 旁白：「每天開工就跑 vibe start。」
vibe start
# 展示 Rich 面板：進度、git 狀態、待辦任務

# 旁白：「現在用任何 AI — Claude、Cursor、Copilot — 開始工作。」
# （切到 IDE 畫面，展示 AI 在讀取 .vibe/state/）

# 做一些修改、commit
echo "export const Button = () => <button>Click</button>" > Button.jsx
git add -A && git commit -m "feat: add Button component"
```

### Part 3：同步（20 秒）

```bash
# 旁白：「收工時，一個 sync 把狀態寫入。」
vibe sync
# 展示：1 commit 附加到 current.md + C.L.E.A.R. 審查清單

# 旁白：「明天換另一個 AI 工具，它也能讀到這些進度。」
```

### Part 4：多工具切換（20 秒）

```bash
# 旁白：「假設我現在要加入 Cursor 支援。」
vibe adapt --add cursor
vibe adapt --sync
# 展示：.cursor/rules/vibe-standards.mdc 被生成

vibe adapt --list
# 展示：agents_md ON、cursor ON

# 旁白：「Cursor 和 Claude 共享同一個大腦。」
```

### Part 5：Autoresearch 整合（20 秒）

```bash
# 旁白：「如果你用 autoresearch 做自動優化...」
# （展示幾個 autoresearch commit）
git log --oneline -5
# 輸出包含 "autoresearch: try ..." 的 commit

vibe sync
# 展示：「Experiments: 3 kept, 1 reverted」

vibe start
# 展示：Rich 面板中的 Experiments 行

# 旁白：「vibe 自動記錄每次實驗的結果。」
```

### Outro（10 秒）

```bash
# 旁白：「vibe-state-cli — 持久記憶、無幻覺、多 Agent 切換、自我進化。」
# 展示 GitHub star 頁面
```

---

## 社群媒體文案模板

### Twitter/X（280 字）

```
🔥 剛開源 vibe-state-cli — 讓任何 AI 工具共享同一個大腦

痛點：AI 每次對話結束就失憶
解法：.vibe/ 目錄 = 跨工具的持久記憶

✅ 5 個指令搞定一切
✅ 支援 8 個 AI/IDE（Claude、Cursor、Copilot、Windsurf...）
✅ 自動偵測 autoresearch 實驗
✅ 嚴格安全邊界

pip install vibe-state-cli

#VibeCoding #AICoding #OpenSource
```

### LinkedIn / 技術部落格（開頭段）

```
2026 年，AI Coding 已是日常。但有一個問題始終沒被解決：

每次你關掉 Claude Code，明天重開 — 它什麼都不記得。
你在 Cursor 寫了一半，切到 Copilot — 另一個 AI 不知道你的進度。

我花了一天，從零設計了 vibe-state-cli — 一個讓任何 AI 模型共享同一個大腦的 CLI 工具。

這個過程經歷了 4 輪嚴格審查，發現並修復了 17 個 bug（包含 AI 幻覺的假設）...
```
