# Tanuki PC Pet

[![Windows CI](https://github.com/MonsterOfDesire/Tanuki_PC_Pet/actions/workflows/windows-ci.yml/badge.svg)](https://github.com/MonsterOfDesire/Tanuki_PC_Pet/actions/workflows/windows-ci.yml)
[![macOS Limited CI](https://github.com/MonsterOfDesire/Tanuki_PC_Pet/actions/workflows/macos-ci.yml/badge.svg)](https://github.com/MonsterOfDesire/Tanuki_PC_Pet/actions/workflows/macos-ci.yml)

Tanuki PC Pet 是以 Python 3.10 與 PyQt6 開發的桌面寵物。Windows 版支援視窗停棲等完整功能；macOS 功能受限版保留角色與 Activity 核心玩法，但停用 Windows 專屬視窗偵測與獨立更新器。

目前介面語系支援繁體中文、简体中文、日本語與 English；可在「狀態設定 → 語言與更新」切換。資訊中心、側邊啟動列、角色顯示名稱、事件、成就與更新狀態均已接入 resource catalog。

[玩家下載與更新](#玩家下載與更新) · [開發者執行與維護](#開發者執行與維護) · [目錄導覽](#目錄導覽) · [授權與素材](#授權與素材)

## 玩家下載與更新

只想使用桌寵，請前往 [GitHub Releases](https://github.com/MonsterOfDesire/Tanuki_PC_Pet/releases)，選擇要使用的版本，再從 **Assets** 下載對應平台的套件。beta 版本會標示為 Pre-release。

**打包版不需要另外安裝 Python，也不需要下載或執行原始碼。** GitHub 自動提供的 `Source code (zip)`／`Source code (tar.gz)` 是開發用原始碼，不是可直接啟動的桌寵套件。

### 選擇下載檔案

下表的 `<版本>` 請對照所選 Release，例如 `0.11.0-beta`。

| 使用環境 | 應下載的檔案 | 啟動方式 |
|---|---|---|
| Windows 10／11，x64 | `TanukiPet-<版本>-windows-x64.zip` | 完整解壓縮後執行 `TanukiPet.exe` |
| macOS 13+，Apple Silicon（M 系列） | `TanukiPet-<版本>-macos-arm64.zip` | 解壓縮後開啟 `TanukiPet.app` |
| macOS 13+，Intel | `TanukiPet-<版本>-macos-x64.zip` | 解壓縮後開啟 `TanukiPet.app` |

- Windows：請完整解壓縮到獨立資料夾；`TanukiPet.exe` 必須與套件內的 `_internal` 等檔案／資料夾一起保留，不能只搬走 EXE，亦不要直接在 ZIP 內執行。
- macOS：請依晶片選擇 arm64 或 x64。`.app` 本身是包含資源的應用程式套件，不要拆開搬動內部檔案。平台限制、首次啟動與測試注意事項見 [macOS 功能受限版說明](docs/MACOS_LIMITED_VERSION.md)。
- 下載頁若提供 `SHA256SUMS.txt`，可用它核對檔案雜湊；它不是啟動程式。`tanuki-update.json` 與 SPDX SBOM 也不需手動執行。

### 更新既有版本

- Windows：從 Release 下載並執行 `TanukiUpdater.exe`，依畫面選取或確認舊版所在資料夾。更新器會在需要時要求正常關閉桌寵，驗證更新包並保留設定，不需要先解除安裝或刪除舊版；它不是首次安裝用的完整主程式。詳見 [更新器與更新包說明](docs/UPDATE_PACKAGE_SPEC.md)。
- macOS：先正常關閉桌寵，下載相同架構的新版 ZIP，再用解壓縮後的 `TanukiPet.app` 替換舊版。設定存於使用者的 `~/Library/Application Support/Tanuki_PC_Pet/`，不要刪除該資料目錄；macOS 不使用 `TanukiUpdater.exe`。

主程式啟動時不會自動連線檢查 GitHub；需要時可在狀態設定中手動檢查，或直接查看 Releases。各版變更可查閱 [版本說明](release_notes/)。

## 開發者執行與維護

本節適用於執行原始碼、修改程式或自行建置套件的開發者；一般玩家不需要完成以下操作。開發環境使用 Python 3.10，所有指令都從本 repository 根目錄（含 `README.md` 與 `lab_2.py` 的資料夾）執行。

### 從原始碼啟動

Windows PowerShell：建立虛擬環境並安裝 runtime 依賴。

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe lab_2.py
```

macOS：使用 Python 3.10 建立虛擬環境，安裝 `requirements-macos-build.txt`（含 macOS 平台及打包依賴），以 `.venv/bin/python lab_2.py` 啟動；完整環境與建置步驟見 [macOS 說明](docs/MACOS_LIMITED_VERSION.md#建置)。

### 測試

全套測試包含打包及素材相關檢查，Windows 請先安裝 build 依賴：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

需要在沒有螢幕輸出的環境執行 Qt 測試時，請在測試前設定：

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
```

此設定只用於離屏測試，不應用於玩家的正常桌面啟動。macOS 測試使用 `.venv/bin/python -m unittest discover -s tests`，離屏環境變數可設為 `QT_QPA_PLATFORM=offscreen`。

### 素材 Manifest

`assets_cropped` 內的 `manifest_edit.xlsx` 是素材維護來源，JSON 由轉換器驗證或產生。先執行乾跑：

```powershell
.\.venv\Scripts\python.exe .\tools\manifest_xlsx_to_json.py --assets-dir .\assets_cropped
```

確認結果後才加上 `--write`。`tools\manifest_xlsx_to_json.py` 是正式命令列入口，轉換與驗證規則只實作於 `tanuki_core.manifest_xlsx_converter`；不要直接手動改寫產生的 JSON。

所有可用 context 的情境、互動對象、實際效果與接線狀態集中記錄於 [docs/MANIFEST_CONTEXT_CATALOG.md](docs/MANIFEST_CONTEXT_CATALOG.md)。

### Windows 可攜打包

安裝 build 依賴後，先檢查環境與封裝素材，再執行 PyInstaller：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\build_lab_2.ps1 -CheckOnly
.\build_lab_2.ps1
```

一般 clone 預設輸出到 repository 的 `build\` 與 `dist\`：

- `dist\TanukiPet\`：可攜主程式
- `dist\TanukiUpdater.exe`：獨立更新器

可用 `-PythonExe` 或 `TANUKI_PYTHON` 指定 Python；可用 `-OutputRoot` 或 `TANUKI_BUILD_ROOT` 指定輸出根目錄：

```powershell
.\build_lab_2.ps1 -PythonExe C:\Python310\python.exe -OutputRoot C:\TanukiBuild
```

完整提交、tag、敏感資料檢查與發布步驟請參閱 [RELEASE_WORKFLOW.md](RELEASE_WORKFLOW.md)。
獨立更新器、更新包檔名、manifest、SHA-256 與 staging／rollback 安全規格請參閱 [docs/UPDATE_PACKAGE_SPEC.md](docs/UPDATE_PACKAGE_SPEC.md)。
維護者的特殊巢狀工作區說明位於 [docs/LOCAL_WORKSPACE.md](docs/LOCAL_WORKSPACE.md)，一般 clone 不需要依賴該目錄結構。

### macOS 建置與驗證

macOS 套件須在對應架構的 Mac 上建置；使用 `build_macos.sh` 與 `TanukiPet-macOS.spec`，輸出 `.app` 與架構別 ZIP。沒有 Mac 開發機時，可利用 repository 的 macOS CI 取得 arm64／x64 成品，再交由測試者確認真實桌面操作。保留／停用能力、建置方式與人工測試清單見 [macOS 功能受限版說明](docs/MACOS_LIMITED_VERSION.md)。

## 目錄導覽

此 repository 是桌寵主程式與開發配套，不是玩家安裝資料夾。以下依用途列出主要檔案與目錄：

| 位置 | 用途 |
|---|---|
| [`lab_2.py`](lab_2.py)、[`tanuki_core/`](tanuki_core/) | 主程式入口，以及角色行為、Activity、介面、存檔和平台能力等核心模組 |
| [`tanuki_updater.py`](tanuki_updater.py) | Windows 獨立更新器入口 |
| [`assets_cropped/`](assets_cropped/) | 角色動畫、一般／變身形態的 manifest 工作簿及產生的 JSON |
| [`items/`](items/) | 飲食與道具互動素材 |
| [`UI/`](UI/) | 介面底圖、圖示、語系、獎盃及介面概念圖；概念圖不一定是正式採用的介面 |
| [`tests/`](tests/) | 純規則、runtime 接線、介面與打包契約的回歸測試 |
| [`tools/`](tools/) | manifest 轉換、驗證、封裝與其他維護工具 |
| [`docs/`](docs/) | 技術規格、相容性、平台限制、素材 context 目錄與來源調查 |
| [`release_notes/`](release_notes/) | 各版本發布說明 |
| [`packaging/`](packaging/)、[`TanukiPet-macOS.spec`](TanukiPet-macOS.spec) | 平台封裝設定與 macOS 應用程式規格 |
| [`build_lab_2.ps1`](build_lab_2.ps1)、[`build_lab_2.bat`](build_lab_2.bat)、[`build_macos.sh`](build_macos.sh) | Windows／macOS 建置入口 |
| [`requirements.txt`](requirements.txt)、[`requirements-build.txt`](requirements-build.txt)、[`requirements-macos-build.txt`](requirements-macos-build.txt) | runtime、Windows 開發／打包及 macOS 開發／打包依賴 |
| [`config.example.json`](config.example.json) | 設定檔範例，不是玩家的實際存檔 |
| [`.github/`](.github/)、[`.githooks/`](.githooks/) | CI、社群表單與本機提交安全守衛 |
| [`archive/legacy_versions/`](archive/legacy_versions/)、[`RELEASE_UPDATE_0.3.0_to_current.md`](RELEASE_UPDATE_0.3.0_to_current.md) | 舊版程式與歷史更新紀錄，不是目前的啟動入口 |
| [`RELEASE_WORKFLOW.md`](RELEASE_WORKFLOW.md) | 維護者提交、建置、簽章與發布流程 |

`build/` 與 `dist/` 是建置時產生的本機輸出，與上表的原始碼／維護資料不同；一般玩家應使用 Releases 中的打包成品。

## 授權與素材

原創程式碼與專案文件依 [MIT License](LICENSE) 授權。角色圖像、動畫、道具圖示與其他視覺素材不包含在 MIT 授權範圍內，相關權利仍屬各自權利人；本 repository 不授予重新使用或散布這些素材的權利。詳見 [ASSET_NOTICE.md](ASSET_NOTICE.md)。

來源、作者層次、調查範圍與尚未取得的許可集中記錄於 [素材來源調查](docs/asset_provenance/README.md)。這些文件是有日期與範圍的研究紀錄，不是素材授權證明。
