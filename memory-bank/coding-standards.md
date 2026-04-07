# Coding Standards

> 本檔案採分類索引結構。新增規範時歸入對應分類，勿在底部直接追加。

## 目錄

1. [命名規範](#1-命名規範)
2. [檔案結構](#2-檔案結構)
3. [版控規範](#3-版控規範)
4. [錯誤處理](#4-錯誤處理)
5. [安全性](#5-安全性)
6. [跨平台](#6-跨平台)
7. [Markdown 解析](#7-markdown-解析)
8. [Adapter 規範](#8-adapter-規範)
9. [專案特定規範](#9-專案特定規範)

---

## 1. 命名規範

- 變數與函式使用 snake_case
- 類別使用 PascalCase
- 常數使用 UPPER_SNAKE_CASE
- CLI 指令名稱使用 kebab-case（如有需要）

## 2. 檔案結構

- 採用 src layout（src/vibe_state/）
- 模板檔案存放於 src/vibe_state/templates/
- 測試檔案存放於 tests/

## 3. 版控規範

- 嚴格遵守 Conventional Commits 標準
- 採用 Micro-commits 策略（單次 Commit 僅限單一邏輯變更）

## 4. 錯誤處理

- 狀態機無效轉換：直接報錯，不靜默跳過
- adapter validate 失敗：印警告，不靜默通過
- git 不存在：自動停用 git 功能 + 警告，不崩潰

## 5. 安全性

- 禁止硬編碼任何密鑰、Token 或密碼
- 環境變數統一使用 .env 檔案管理
- subprocess 禁止使用 `shell=True`，一律傳引數列表
- `vibe adapt --remove` 預設 dry-run，需 `--confirm` 才執行

## 6. 跨平台

- **路徑**：全面使用 `pathlib.Path`，禁止字串拼接路徑
- **Git 偵測**：`shutil.which("git")`，找不到則 `config.git.enabled = false`
- **編碼**：所有檔案讀寫指定 `encoding="utf-8"`
- **換行**：寫入時使用 `newline="\n"`（Unix 風格），Git autocrlf 處理平台差異

## 7. Markdown 解析

- **禁止使用 regex 解析 Markdown 結構**（checkbox、heading、list 等）
- 使用 `markdown-it-py` 解析為 AST，遍歷節點操作
- regex 僅限用於非結構性的簡單文字匹配

## 8. Adapter 規範

- 每個 adapter 必須定義 `REQUIRED_FIELDS: set[str]`
- `emit()` 後必須自動呼叫 `validate()` 檢查 frontmatter
- `emit()` 時同步存一份到 `.vibe/snapshots/<tool>/`
- `clean()` 前必須備份到 `.vibe/backups/<tool>/<timestamp>/`

## 9. 專案特定規範

- 所有生成的 Markdown 模板須保持可讀性，避免過度嵌套
- CLI 輸出使用 Rich 美化，確保無 Rich 環境下仍可正常運作
- VIBE.md 是「憲法」不是「SSOT」— state/ 才是 SSOT
