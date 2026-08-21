# 獨立更新器與更新包（schema 1）

本專案使用獨立的 `TanukiUpdater.exe` 更新可攜版。主程式啟動時不會存取 GitHub；使用者需要更新時，從 GitHub Release 下載更新器並執行即可，不必解除安裝或手動刪除舊版。

## GitHub Release 資產

每個可更新的 Release 必須同時包含：

- `TanukiUpdater.exe`
- `TanukiPet-<version>-windows-x64.zip`
- `tanuki-update.json`

ZIP 根目錄是新版 `TanukiPet` onedir 內容，必須直接包含 `TanukiPet.exe`，不可再包一層資料夾。manifest 格式如下：

```json
{
  "schema_version": 1,
  "version": "0.8.0-beta",
  "executable_name": "TanukiPet.exe",
  "package": {
    "name": "TanukiPet-0.8.0-beta-windows-x64.zip",
    "url": "https://github.com/MonsterOfDesire/Tanuki_PC_Pet/releases/download/v0.8.0-beta/TanukiPet-0.8.0-beta-windows-x64.zip",
    "sha256": "64-character-lowercase-sha256",
    "size": 12345678
  }
}
```

## 使用者流程

1. 使用者下載並執行 `TanukiUpdater.exe`。
2. 更新器讀取 `%LOCALAPPDATA%\Tanuki_PC_Pet\installation.json`；可攜主程式第一次執行時會自動登記自身位置、版本與介面語言。從尚未支援登記的舊版第一次升級時，更新器會先檢查自己所在資料夾，仍找不到才請使用者選取一次含 `TanukiPet.exe` 的資料夾。
3. 更新器當下才查詢 GitHub Releases。beta 版會納入 prerelease，穩定版只接受穩定 Release。
4. 主程式只有在同一 Release 同時找到 `TanukiUpdater.exe`、manifest 與精確版本 ZIP 時，才顯示可直接下載的更新器；資產不完整時仍可開啟 Release 頁面檢查，但不宣稱可自動更新。
5. 若有新版，使用者確認後才下載同一 Release 的 manifest 與 ZIP。manifest 記錄的 ZIP 名稱、URL 與大小必須和 GitHub Release 資產一致。
6. 下載與套用期間顯示原生進度視窗；若主程式仍在執行，更新器要求使用者正常關閉並等待，不會強制終止行程。
7. 成功後啟動新版；不需要解除安裝。更新器會清除舊的 runtime 副本與已下載 ZIP，安裝旁只保留最近一份 backup。

若更新器被放在主程式資料夾內，它會先複製到 `%LOCALAPPDATA%\Tanuki_PC_Pet\updater-runtime` 再執行替換，避免執行中的更新器鎖住目標資料夾。

## 驗證、替換與回復

1. ZIP 先下載成 `.partial`，大小及 SHA-256 都符合 manifest 後才改為正式檔名。
2. 解壓到安裝資料夾旁、同一磁碟區的空白 staging；拒絕絕對路徑、`..`、磁碟機路徑及 symbolic link。
3. staging 根目錄必須存在 manifest 指定的 `TanukiPet.exe`。
4. 舊版 `config.json` 會複製到 staging，因此語言、角色位置、家庭狀態及成就等現有設定不會因更新消失。
5. 舊版資料夾先重新命名為隱藏 backup，staging 才替換到原安裝位置。
6. 任一步驟失敗時，更新器把 backup 改回原安裝位置；成功後保留本次 backup 並移除更舊版本，方便人工復原且不會長期累積。

更新器只接受含 `TanukiPet.exe` 的明確安裝資料夾，拒絕磁碟根目錄與使用者家目錄，避免把廣泛路徑當作替換目標。

## 建置

先執行完整打包；腳本會同時產生 onedir 主程式與 onefile 更新器：

```powershell
.\build_lab_2.ps1 -CheckOnly
.\build_lab_2.ps1
```

打包後可先執行不連網、不讀取玩家安裝紀錄的成品自我檢查；它會在系統暫存目錄建立舊版副本，驗證替換、`config.json` 保留、失敗 rollback 與新版重新啟動後自動清除：

```powershell
.\dist\TanukiUpdater.exe --self-check
```

接著建立版本 ZIP 與 manifest：

```powershell
python .\tools\build_update_package.py `
  --source-dir .\dist\TanukiPet `
  --version 0.8.0-beta `
  --output-dir .\dist\release `
  --package-url https://github.com/MonsterOfDesire/Tanuki_PC_Pet/releases/download/v0.8.0-beta/TanukiPet-0.8.0-beta-windows-x64.zip
```

上傳前必須先完成 EXE 簽章，再產生 ZIP 與 manifest。三個資產必須一同上傳，而且 Release tag、manifest 版本與 `tanuki_core/app_version.py` 必須一致。
