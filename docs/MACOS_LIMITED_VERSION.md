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

## 平台視窗互動

- macOS 的角色視窗依目前 GIF 畫面的 alpha 建立原生輸入遮罩，透明 `QWidget` 區域由視窗系統直接穿透；Qt 事件層仍保留可見像素檢查，避免透明周邊觸發點擊或拖曳。
- macOS 角色 overlay 使用 AppKit non-activating panel；點擊角色本體可互動，但不應啟用整個應用程式或把已開啟的狸貓資訊中心帶到最上層。
- 角色與收合控制列加入所有 macOS Spaces，完整資訊中心仍只留在使用者開啟它的目前 Space。macOS 不建立 Windows 邊緣 hover `SensorZone`，收合後改保留可點擊的窄控制列入口。
- 程式會監聽螢幕新增、移除、可用區域及解析度變更，重新選擇最左側控制列螢幕，並把安全狀態的地面角色校正到目前實際工作區地板；忙碌、拖曳、墜落或 Activity 中的角色會延後校正。
- macOS 的資訊中心、分離頁面、飲食餐盤、家庭摘要與事件／關係工具視窗使用系統原生標題列及 traffic-light 關閉／最小化按鈕。原本的釘選功能仍保留在內容列中。
- Windows 不啟用 alpha 視窗遮罩、non-activating panel、all-Spaces 或 macOS 收合政策，繼續使用既有角色命中行為、工具視窗層級、自繪關閉／最小化控制列及邊緣感應區；只有實際增減螢幕時會共用拓撲安全重算。

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
2. 點擊角色可見像素、確認透明周邊不會觸發、原地長按拖曳、跨螢幕拖曳與召喚／隱藏。
3. 1x／8x 下的睡眠、照護、變身、競賽、合奏及供品互動。
4. 關閉後重新啟動，確認設定、位置、事件與成就仍存在。
5. 確認角色只在 macOS 可用工作區地面活動，不嘗試停在其他應用程式視窗上。
6. 資訊中心保持開啟但不置頂時點擊角色，確認資訊中心不會自動浮到最上層；再由功能列主動叫出時仍能正常聚焦。
7. 確認資訊中心、分離頁面與飲食餐盤使用 macOS 原生 traffic-light 控制，釘選功能仍可正常切換。
8. 在程式啟動前後分別連接左側副螢幕，確認收合控制列都移到目前最左側螢幕，沒有巨大灰綠感應區。
9. 在內建螢幕多個 Spaces 間切換，確認角色與收合入口持續可見，且角色能在高低不同的兩個螢幕間回到正確地板。

CI 能證明程式可建置、啟動與通過自動測試，但不能取代真實桌面、多螢幕、Dock 位置、Mission Control 與 Gatekeeper 的人工驗證。

## Release 內容

建議跨平台首版使用 `v0.9.0-beta`，同一個 Release 放置本版 Windows 套件、`TanukiUpdater.exe`、Windows 更新 manifest，以及兩個 macOS ZIP。macOS ZIP 不重複包入 Windows 內容；Release 頁則同時提供各平台下載選項。
