# macOS 功能受限版

Tanuki PC Pet 的 macOS 版本沿用同一套角色、Activity、manifest、存檔與 UI 程式碼，但把 Windows 專屬能力集中關閉。首版最低目標為 macOS 13，分別提供 Apple Silicon (`arm64`) 與 Intel (`x64`) 安裝包。

## 保留功能

- 角色顯示、地面移動、點擊、長按拖曳及召喚／隱藏。
- 心情、關係、照護、睡眠、變身、競賽、合奏與供品互動。
- 沙盒與黃金傳說模式；新安裝預設為沙盒。
- 資訊中心、家庭摘要、事件日誌、狀態設定、獎盃蒐集櫃及四種介面語言。
- macOS 使用者資料儲存在 `~/Library/Application Support/Tanuki_PC_Pet/config.json`。
- 主程式可檢查 GitHub Release 是否有新版，但 macOS 首版只提供手動下載更新。

## 暫停功能

- 不讀取其他應用程式的視窗位置，因此沒有視窗頂端停棲、視窗表面降落或視窗間飛行。
- 不啟動 `pynput` 全域滑鼠監聽器；只保留 Qt 視窗自身可收到的游標與點擊事件。
- 不提供 `TanukiUpdater.exe` 或背景自動替換；下載新的 `.app` 後由使用者手動替換。
- 首批 GitHub Actions 產物採 ad-hoc 簽章，未做 Apple Developer ID 簽章或 Apple notarization，Gatekeeper 仍可能要求使用者確認來源。

## 建置

在對應架構的 Mac 上執行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-macos-build.txt
TANUKI_PYTHON=.venv/bin/python bash ./build_macos.sh
```

輸出：

- `dist/TanukiPet.app`
- `dist/TanukiPet-<version>-macos-arm64.zip` 或 `dist/TanukiPet-<version>-macos-x64.zip`

`.icns` 由 `luna.ico` 在建置時重現產生；產物不含 Windows 更新器。

## 無 Mac 開發機時的驗證

`.github/workflows/macos-ci.yml` 在 `macos-15`（Apple Silicon）與 `macos-15-intel`（Intel）執行完整測試、manifest 驗證、PyInstaller 建置、ad-hoc 簽章驗證與三秒啟動 smoke test。Actions artifact 可交由 Mac 測試者進行下列人工驗證：

1. 第一次啟動、四語切換、資訊中心顯示與重新叫出。
2. 點擊、原地長按拖曳、跨螢幕拖曳與召喚／隱藏。
3. 1x／8x 下的睡眠、照護、變身、競賽、合奏及供品互動。
4. 關閉後重新啟動，確認設定、位置、事件與成就仍存在。
5. 確認角色只在 macOS 可用工作區地面活動，不嘗試停在其他應用程式視窗上。

CI 能證明程式可建置、啟動與通過自動測試，但不能取代真實桌面、多螢幕、Dock 位置、Mission Control 與 Gatekeeper 的人工驗證。

## Release 內容

建議跨平台首版使用 `v0.9.0-beta`，同一個 Release 放置本版 Windows 套件、`TanukiUpdater.exe`、Windows 更新 manifest，以及兩個 macOS ZIP。macOS ZIP 不重複包入 Windows 內容；Release 頁則同時提供各平台下載選項。
