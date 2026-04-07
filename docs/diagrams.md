# vibe-state-cli 架構圖集

> 使用 Mermaid 語法。可在 GitHub、Notion、Obsidian、mkdocs-material 直接渲染。

---

## 圖 1：核心架構 — .vibe/ 目錄與 Adapter 衍生

```mermaid
graph TB
    subgraph ".vibe/ 目錄（專案內）"
        VIBE["VIBE.md<br/>憲法"]
        CONFIG["config.toml<br/>設定"]
        subgraph "state/（SSOT）"
            CURRENT["current.md<br/>進度快照"]
            TASKS["tasks.md<br/>任務清單"]
            ARCH["architecture.md<br/>技術堆疊"]
            STD["standards.md<br/>編碼規範"]
            EXP["experiments.md<br/>實驗紀錄"]
            ARCHIVE["archive.md<br/>冷藏庫"]
        end
    end

    VIBE --> DERIVE
    CONFIG --> DERIVE
    STD --> DERIVE
    ARCH --> DERIVE

    DERIVE["adapter emit()"]

    DERIVE --> AGENTS["AGENTS.md<br/>通用標準"]
    DERIVE --> CLAUDE["CLAUDE.md<br/>+ .claude/rules/"]
    DERIVE --> GEMINI["GEMINI.md<br/>Antigravity"]
    DERIVE --> CURSOR[".cursor/rules/*.mdc"]
    DERIVE --> COPILOT[".github/copilot-instructions.md"]
    DERIVE --> WINDSURF[".windsurf/rules/*.md"]
    DERIVE --> CLINE[".clinerules/*.md"]
    DERIVE --> ROO[".roo/rules/*.md"]

    style VIBE fill:#f9d71c,stroke:#333,color:#000
    style DERIVE fill:#4ecdc4,stroke:#333,color:#000
    style CURRENT fill:#a8e6cf,stroke:#333,color:#000
    style TASKS fill:#a8e6cf,stroke:#333,color:#000
    style EXP fill:#ffd3b6,stroke:#333,color:#000
```

---

## 圖 2：生命週期狀態機

```mermaid
stateDiagram-v2
    [*] --> UNINIT
    UNINIT --> READY : vibe init
    READY --> ACTIVE : vibe start
    ACTIVE --> ACTIVE : vibe sync
    ACTIVE --> ACTIVE : vibe start
    ACTIVE --> CLOSED : vibe sync --close
    CLOSED --> READY : vibe init --force

    state ACTIVE {
        [*] --> Working
        Working --> Syncing : vibe sync
        Syncing --> Working
        Working --> Compacting : vibe sync --compact
        Compacting --> Working
    }

    note right of READY : vibe status 在任何狀態都可用
    note right of CLOSED : vibe adapt 在 READY/ACTIVE 可用
```

---

## 圖 3：每日工作流

```mermaid
sequenceDiagram
    participant Dev as 開發者
    participant CLI as vibe CLI
    participant State as .vibe/state/
    participant Git as Git Repo
    participant AI as AI 助手

    Note over Dev,AI: ☀️ 每日開工
    Dev->>CLI: vibe start
    CLI->>State: 讀取 current.md + tasks.md
    CLI->>Git: git status（校驗）
    CLI-->>Dev: Rich 摘要面板

    Note over Dev,AI: ⚙️ 工作中
    Dev->>AI: 開始工作
    AI->>State: 標記 tasks.md [x]
    AI->>State: 附加 current.md 進度
    Note right of AI: Checkpoint Rule<br/>（自動執行）

    Note over Dev,AI: 🌙 每日收工
    Dev->>CLI: vibe sync
    CLI->>Git: git log + git diff
    CLI->>State: 附加 Sync 區塊到 current.md
    CLI->>State: 偵測 autoresearch → experiments.md
    CLI-->>Dev: C.L.E.A.R. 審查清單
```

---

## 圖 4：多 Agent 切換流程

```mermaid
flowchart LR
    subgraph "Morning — Claude Code"
        CC[Claude Code CLI]
        CC -->|讀取| CM[CLAUDE.md]
        CM -->|"@AGENTS.md"| AG[AGENTS.md]
        CC -->|"Session Start 指令"| STATE1[".vibe/state/*"]
        CC -->|工作中 checkpoint| STATE1
    end

    STATE1 -.->|"vibe sync<br/>（附加 git 狀態）"| STATE2

    subgraph "Afternoon — Cursor"
        CU[Cursor IDE]
        CU -->|自動載入| MDC[".cursor/rules/*.mdc"]
        MDC -->|"Session Start 指令"| STATE2[".vibe/state/*"]
        CU -->|也讀取| AG2[AGENTS.md]
    end

    STATE2 -.->|"vibe sync"| STATE3[".vibe/state/*"]

    subgraph "Evening — Windsurf"
        WS[Windsurf]
        WS -->|自動載入| WR[".windsurf/rules/*.md"]
        WR -->|"Session Start 指令"| STATE3
    end

    style STATE1 fill:#a8e6cf,stroke:#333,color:#000
    style STATE2 fill:#a8e6cf,stroke:#333,color:#000
    style STATE3 fill:#a8e6cf,stroke:#333,color:#000
```

---

## 圖 5：Adapter 去重策略

```mermaid
flowchart TD
    INIT["vibe init 偵測到<br/>claude + cursor + agents_md"]

    INIT --> AGENTS_FULL["AGENTS.md<br/>📄 完整內容<br/>（standards + security + session start）"]

    INIT --> CLAUDE_IMPORT["CLAUDE.md<br/>📄 @AGENTS.md 匯入<br/>+ Claude 專屬指令"]

    INIT --> CURSOR_SLIM[".cursor/rules/vibe-standards.mdc<br/>📄 slim 模式<br/>frontmatter + 'See AGENTS.md'<br/>+ Session Start 指令"]

    AGENTS_FULL -.->|"Token: ~350"| TOKEN1["完整 body"]
    CLAUDE_IMPORT -.->|"Token: ~80"| TOKEN2["只有 @import + 專屬"]
    CURSOR_SLIM -.->|"Token: ~120"| TOKEN3["frontmatter + 指令"]

    style AGENTS_FULL fill:#4ecdc4,stroke:#333,color:#000
    style CLAUDE_IMPORT fill:#ffd93d,stroke:#333,color:#000
    style CURSOR_SLIM fill:#ffd93d,stroke:#333,color:#000
```

---

## 圖 6：Autoresearch 整合

```mermaid
sequenceDiagram
    participant AR as /autoresearch
    participant Git as Git
    participant CLI as vibe CLI
    participant State as state/experiments.md

    Note over AR,State: 自動優化迴圈
    loop 每次迭代
        AR->>AR: 提出假設
        AR->>Git: 修改 code + git commit<br/>"autoresearch: try lr=0.01"
        AR->>AR: 執行 verify command
        alt metric 提升
            AR->>Git: keep（保留 commit）
        else metric 下降
            AR->>Git: git reset（回滾）
        end
    end

    Note over CLI,State: 迴圈結束後
    CLI->>Git: vibe sync<br/>掃描 git log
    Git-->>CLI: 發現 autoresearch commits
    CLI->>State: 記錄 KEPT/REVERTED
    CLI-->>CLI: "Experiments: 5 kept, 3 reverted"

    Note over CLI,State: 下次開工
    CLI->>State: vibe start<br/>讀取 experiments.md
    CLI-->>CLI: 摘要面板顯示實驗結果
```

---

## 圖 7：安全防護層

```mermaid
flowchart TB
    INPUT["使用者輸入 / 專案中繼資料"]

    INPUT --> SANITIZE["_sanitize()<br/>過濾 \\n # \" ' \`"]
    SANITIZE --> TEMPLATE["Jinja2 模板渲染"]
    TEMPLATE --> VALIDATE["adapter.validate()<br/>檢查 frontmatter"]
    VALIDATE --> WRITE["原子寫入<br/>temp + os.replace()"]
    WRITE --> SNAPSHOT["save_snapshot()<br/>快照存檔"]

    subgraph "刪除防護"
        REMOVE["vibe adapt --remove"]
        REMOVE --> DRYRUN{"--dry-run?"}
        DRYRUN -->|是| PREVIEW["預覽不執行"]
        DRYRUN -->|否| CONFIRM{"--confirm?"}
        CONFIRM -->|否| WARN["顯示警告<br/>偵測用戶修改"]
        CONFIRM -->|是| BACKUP["create_backup()<br/>保留 3 份"]
        BACKUP --> DELETE["刪除檔案"]
    end

    subgraph "狀態防護"
        LIFECYCLE[".lifecycle 狀態機"]
        LIFECYCLE --> CHECK["每個指令先驗轉換"]
        CHECK -->|無效| ERROR["報錯 + 列出合法指令"]
        CHECK -->|有效| EXECUTE["執行"]
        PATHVAL["_validate_filename()"] --> PATHCHECK{"在 state/ 內?"}
        PATHCHECK -->|否| REJECT["拒絕（路徑穿越）"]
        PATHCHECK -->|是| PROCEED["允許"]
    end

    style SANITIZE fill:#ff6b6b,stroke:#333,color:#fff
    style VALIDATE fill:#ff6b6b,stroke:#333,color:#fff
    style BACKUP fill:#4ecdc4,stroke:#333,color:#000
    style LIFECYCLE fill:#ffd93d,stroke:#333,color:#000
```
