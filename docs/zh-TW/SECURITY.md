# 安全政策

## 回報漏洞

如果你發現 vibe-state-cli 的安全漏洞，請負責任地回報：

1. **不要**為安全漏洞開公開的 GitHub Issue
2. 請發信至 [security@vibe-state-cli.dev] 或使用 GitHub 的私密漏洞回報功能
3. 請包含：重現步驟、受影響版本、潛在影響

我們會在 48 小時內回覆並提供修復時程。

## 安全設計

vibe-state-cli 生成的設定檔會被 AI 編碼助手讀取為指令。這形成了獨特的攻擊面：

### 我們防護的項目

- **透過專案中繼資料注入 Prompt**：使用者可控字串（專案名稱、語言、框架）在進入模板前會過濾控制字元。
- **路徑穿越**：`state.py` 驗證所有檔名都在 `.vibe/state/` 內。寫入使用原子的 temp + rename 模式。
- **破壞性 adapter 操作**：`vibe adapt --remove` 預設為 dry-run，需要 `--confirm`。刪除前會建立備份。
- **設定檔損壞**：格式錯誤的 `config.toml` 會直接停住。Pydantic 驗證所有欄位。
- **YAML frontmatter 注入**：每個 adapter 在 `emit()` 後自動執行驗證檢查。

### 我們指示 AI 遵循的規則

生成的 `AGENTS.md` 包含明確的邊界規則：

- 未經人類確認不得執行破壞性指令
- 不得修改 `.vibe/config.toml` 或 `.vibe/state/.lifecycle`

### 已知限制

- **AI 合規不是強制的**：AGENTS.md 的邊界規則是指令，不是強制執行。AI 模型可能選擇忽略它們。
- **檔案層級存取**：生成的 adapter 檔案（CLAUDE.md、.cursor/rules/）對任何有專案存取權的人都是可讀的。不要在 `.vibe/` 中放置機密資訊。

## 支援版本

| 版本 | 支援狀態 |
|------|---------|
| 0.3.x | 是 |
| 0.2.x | 否 |
| 0.1.x | 否 |
