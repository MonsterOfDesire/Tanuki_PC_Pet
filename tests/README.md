# Test Suite Layout

測試維持扁平 discovery，但以 suite catalog 分類，方便快速判斷哪一層回歸：

- `assets`: 素材選擇、載入、store/cache
- `config`: config schema、apply/save scheduler、store
- `dashboard`: dashboard/controller/presenter/shell/shutdown
- `pet`: pet host、physics、logic、social/care、overlay
- `runtime`: `SimulationClock` 與時間倍率
- `windowing`: perch/flight/window tracker/surface/windowing coordinator
- `tooling`: lightweight checks 等開發工具

## Qt Test Boundary

- 純規則測試不得 import PyQt；例如 autosave 是否取得儲存目標由 `test_config_rules.py` 驗證。
- `QTimer` 整合測試繼承 `QtApplicationTestCase`，由 `tests/qt_test_support.py` 建立並持有 offscreen `QApplication`。
- 測試 fallback 只在實際 import PyQt6 失敗時啟用，不得以 `PyQt6` 是否已存在於 `sys.modules` 判斷安裝狀態。
- Qt 測試結束時必須停止仍 active 的 timer，避免事件洩漏到下一個案例。

## Shared Food Three-Layer Suite

`shared_food` 另外依依賴程度分成三層，定義在 `tests/suite_catalog.py`：

| Layer | 內容 | 適用時機 |
|---|---|---|
| `logic` | Partner eligibility、outcome resolver、能力 preflight | 修改距離、權重或結果規則時快速回歸 |
| `runtime` | scene coordinator、offer routing/release、stage、道具生命週期 | 修改 runtime handler 或場景流程時 |
| `assets` | AssetManager/audit、xlsx converter、真實 shared_food manifest/context | 修改 profile、候選或素材資料時 |

PowerShell 執行方式：

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python.exe .\tools\run_shared_food_tests.py --layer logic
.\.venv\Scripts\python.exe .\tools\run_shared_food_tests.py --layer runtime
.\.venv\Scripts\python.exe .\tools\run_shared_food_tests.py --layer assets
```

完整 shared_food 回歸使用 `--layer all`。第三層直接讀取工作區的 `assets_cropped`，會確認四位參與角色 xlsx/json 一致、36 個食物／角色／能力 context 需求無缺漏，以及六個雙向路由都支援三種 outcome。

命名慣例：

- 檔名保持 `test_<module_or_boundary>.py`
- façade / controller / presenter / rules 等後綴應直接反映現在的模組邊界
- 新增測試時，請同步更新 `tests/suite_catalog.py`
- shared_food 測試新增或移動時，也要同步更新 `SHARED_FOOD_TEST_LAYERS`
