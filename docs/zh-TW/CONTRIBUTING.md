# 貢獻指南

感謝你對 vibe-state-cli 的關注！

## 開發環境設定

```bash
git clone https://github.com/vibe-state-cli/vibe-state-cli.git
cd vibe-state-cli
make install              # 使用 uv sync + pre-commit install
```

需要 [uv](https://docs.astral.sh/uv/)（`pip install uv` 或 `curl -LsSf https://astral.sh/uv/install.sh | sh`）。

## 執行測試

```bash
make lint                 # uv run ruff check
make test                 # uv run pytest
make cov                  # uv run pytest --cov
make typecheck            # uv run mypy
make build                # uv build
```

## 依賴管理

依賴透過 `uv.lock` 鎖定（已 commit 到 git）。保證每位貢獻者拿到完全相同的版本。

```bash
# 在 pyproject.toml 新增依賴後：
make lock                 # 重新生成 uv.lock
```

## 專案結構

```
src/vibe_state/
├── cli.py            # 5 個 Typer 指令
├── config.py         # config.toml Schema（Pydantic）
├── safety.py         # 快照、備份、dry-run
├── core/
│   ├── scanner.py    # 語言/框架/工具偵測
│   ├── lifecycle.py  # 狀態機（UNINIT→READY→ACTIVE→CLOSED）
│   ├── git_ops.py    # Git 唯讀操作 + autoresearch 偵測
│   ├── state.py      # 原子寫入 + 檔案鎖定
│   ├── compactor.py  # 任務歸檔 + 狀態壓縮
│   └── templates.py  # Jinja2 渲染 + i18n
├── adapters/         # 8 個內建 adapter
│   ├── base.py       # AdapterBase ABC + _build_common_body()
│   ├── registry.py   # 透過 @register_adapter 自動發現
│   └── *.py          # 每個 adapter 一個檔案
└── templates/        # Jinja2 模板（en + zh-TW）
```

## 新增 Adapter

1. 建立 `src/vibe_state/adapters/your_tool.py`
2. 繼承 `AdapterBase`，實作 `detect()`、`emit()`、`clean()`
3. 加上 `@register_adapter` 裝飾器
4. 在 `registry.py:_load_all_adapters()` 加入 import
5. 在 `scanner.py:TOOL_SIGNATURES` 加入偵測簽章
6. 在 `tests/test_adapters.py` 加入測試
7. 更新 `README.md` 支援工具表

## Commit 規範

- 遵循 [Conventional Commits](https://www.conventionalcommits.org/)
- 每次 commit 僅限單一邏輯變更
- 前綴：`feat:`、`fix:`、`docs:`、`refactor:`、`test:`、`chore:`

## 程式碼規範

- Python 3.10+，全面使用 type annotations
- `pathlib.Path` 處理所有路徑（不用字串拼接）
- `encoding="utf-8"` + `newline="\n"` 用於所有檔案 I/O
- subprocess 禁止 `shell=True`
- ruff 檢查 lint，mypy 檢查型別
