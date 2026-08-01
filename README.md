# Tanuki PC Pet

[![Windows CI](https://github.com/MonsterOfDesire/Tanuki_PC_Pet/actions/workflows/windows-ci.yml/badge.svg)](https://github.com/MonsterOfDesire/Tanuki_PC_Pet/actions/workflows/windows-ci.yml)

Tanuki PC Pet 是以 Python 3.10 與 PyQt6 開發的 Windows 桌面寵物。角色會在桌面與視窗邊緣移動，並依心情、關係、道具與家庭事件呈現不同互動。

## 系統需求

- Windows 10 或 Windows 11
- Python 3.10

## 安裝與啟動

在 repository 根目錄建立虛擬環境並安裝 runtime 依賴：

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe lab_2.py
```

## 測試

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

需要在沒有螢幕輸出的環境執行 Qt 測試時，可先設定：

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
```

## 素材 Manifest

`assets_cropped` 內的 `manifest_edit.xlsx` 是素材維護來源，JSON 由轉換器驗證或產生。先執行乾跑：

```powershell
.\.venv\Scripts\python.exe .\tools\manifest_xlsx_to_json.py --assets-dir .\assets_cropped
```

確認結果後才加上 `--write`。`tools\manifest_xlsx_to_json.py` 是正式命令列入口，轉換與驗證規則只實作於 `tanuki_core.manifest_xlsx_converter`；不要直接手動改寫產生的 JSON。

所有可用 context 的情境、互動對象、實際效果與接線狀態集中記錄於 [docs/MANIFEST_CONTEXT_CATALOG.md](docs/MANIFEST_CONTEXT_CATALOG.md)。

## 可攜打包

安裝 build 依賴後，先檢查環境與封裝素材，再執行 PyInstaller：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\build_lab_2.ps1 -CheckOnly
.\build_lab_2.ps1
```

一般 clone 預設輸出到 repository 的 `build\` 與 `dist\`。

可用 `-PythonExe` 或 `TANUKI_PYTHON` 指定 Python；可用 `-OutputRoot` 或 `TANUKI_BUILD_ROOT` 指定輸出根目錄：

```powershell
.\build_lab_2.ps1 -PythonExe C:\Python310\python.exe -OutputRoot C:\TanukiBuild
```

完整提交、tag、敏感資料檢查與發布步驟請參閱 [RELEASE_WORKFLOW.md](RELEASE_WORKFLOW.md)。
維護者的特殊巢狀工作區說明位於 [docs/LOCAL_WORKSPACE.md](docs/LOCAL_WORKSPACE.md)，一般 clone 不需要依賴該目錄結構。

## 授權與素材

原創程式碼與專案文件依 [MIT License](LICENSE) 授權。角色圖像、動畫、道具圖示與其他視覺素材不包含在 MIT 授權範圍內，相關權利仍屬各自權利人；本 repository 不授予重新使用或散布這些素材的權利。詳見 [ASSET_NOTICE.md](ASSET_NOTICE.md)。
