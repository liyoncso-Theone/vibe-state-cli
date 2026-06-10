# 開發規範

## 命名
- 變數/函式：snake_case，類別：PascalCase，常數：UPPER_SNAKE_CASE

## 版控
- Conventional Commits。每次 commit 僅限單一邏輯變更。

## 安全性
- 禁止硬編碼密鑰。使用 .env 管理。

---

## Release Ritual — 完整流程含結尾清理

> **為什麼這條獨立成節**：v0.3.5 / v0.3.6 / v0.3.7 三次 ship，三次都把
> 收尾 commit 落在 merge 完的 dead branch 上、靠 cherry-pick dance 補救。
> 根因不是技術問題、是 ritual **沒寫到結尾**。完整紀錄見
> [docs/release-history.md](../../docs/release-history.md)。

### 完整 9 步流程（每次 ship 必走，最後一步不可省）

```
1. 在 main 上 git pull，確保是 origin/main 最新
2. git checkout -b release/vX.Y
3. 開發 + 測試 + 跑 adversarial review workflow
4. commit + push 到 origin
5. 開 PR → CI 全綠 → merge 到 main
6. 切回 main、git pull、創建 GitHub Release（target=main）
7. 等 publish.yml 自動跑 → 驗證 PyPI 上架
8. 兩台機器 pipx upgrade → 各 workspace vibe sync
9. ★ 收尾清理 — 不做就會踩 dead-branch 坑：
   git branch -D release/vX.Y     # 砍本地 dead branch（origin 留著）
   （這一步把工作樹從 dead branch 強制移開，下次新工作只能從 main 起跑）
```

### Anti-pattern 警告

**不要把 cherry-pick dance 當「正常 recovery」**。如果你發現自己又在 dead branch 上 commit 了，**那是 ritual 沒走完到 Step 9 的徵兆**，不是該被優雅化的常規操作。立刻：

1. 把那個 commit 搬到 main（cherry-pick 或重做）
2. **補做 Step 9** —— 把 dead branch 砍掉
3. 在 `.vibe/state/tasks.md` 記一筆「ritual 又沒走完」當 trigger，下次更專注

### 既有 origin dead branch 留著的原因

`origin/release/vX.Y` 留在 GitHub 不砍 —— 對應 PR 歷史好查、磁碟成本近 0。
但**本地一定砍**，因為本地分支的存在就是引誘下次落上去的物理機制。

### 如果 release 後需要立即 hot-fix（不是大改）

開新分支 `fix/<short-desc>`（不要叫 release/vX.Y.Z）→ PR → merge → tag patch
release → cleanup。不重用任何 release 分支名。
