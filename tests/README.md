# Test Suite Layout

測試維持扁平 discovery，但以 suite catalog 分類，方便快速判斷哪一層回歸：

- `assets`: 素材選擇、載入、store/cache
- `config`: config schema、apply/save scheduler、store
- `dashboard`: dashboard/controller/presenter/shell/shutdown
- `pet`: pet host、physics、logic、social/care、overlay
- `runtime`: `SimulationClock` 與時間倍率
- `windowing`: perch/flight/window tracker/surface/windowing coordinator
- `tooling`: lightweight checks 等開發工具

命名慣例：

- 檔名保持 `test_<module_or_boundary>.py`
- façade / controller / presenter / rules 等後綴應直接反映現在的模組邊界
- 新增測試時，請同步更新 `tests/suite_catalog.py`
