# Release 工作流程建議

這份文件是給目前 `tanuki_core/` 多模組架構使用的發布流程建議。

目的有兩個：

- 讓我們之後更容易比對「這次版本到底改了什麼」
- 讓 release 說明不再依賴人工回憶或單一大型檔案的差異

## 一、建議保留的備份方式

現在已經不適合每次都額外備份一整份大型單檔 Python。

之後比較穩的做法是：

### 1. 以 Git tag 當版本基準

每次準備發版時，建立一個 tag，例如：

- `v0.3.0`
- `v0.4.0`
- `v0.4.1`

這樣之後要比較版本差異時，就不需要依賴手動備份檔名，而是直接用 tag 對 tag。

### 2. 舊版大型里程碑保留在 `archive/`

像 `0.3.0.py` 這種有代表性的舊版，仍然可以保留在：

- `archive/legacy_versions/`

但建議只保留少數重要里程碑，不要每次小更新都額外存一份完整 Python。

### 3. 發版時保留一份 release note

每次版本釋出時，建議至少新增一份：

- `release_notes/`
  - `v0.4.0.md`
  - `v0.4.1.md`

這樣之後回頭看時，比對的不只是程式碼，還有當時對外怎麼描述更新內容。

## 二、之後如何比對前後變化

從現在開始，release 說明建議不要再用「只比對單一主檔行數」的方式，而是改成三層來看。

### 1. 功能層

先問自己這次對玩家有感的東西是什麼：

- 新功能
- 行為改動
- 明顯 bug 修正
- UI 或操作上的改善

這一層是 release 公告最重要的內容。

### 2. 工程層

再整理這次底層做了哪些工程化處理：

- 新模組
- 設定保存
- 打包修正
- debug / validation 工具
- 效能或穩定度改善

這一層可以寫在「技術更新」或「開發備註」。

### 3. 結構層

最後才是專案結構上的整理：

- 檔案搬移
- 模組拆分
- `tanuki_core/` 新增內容
- 虛擬環境、build、dist、archive 的整理

這一層通常適合寫在內部 release note，或比較長版的更新說明。

## 三、每次發版前的實際流程

### 1. 開發完成後先確認可執行

- 用 PyCharm 執行：
  - `tanuki_app/lab_2.py`
- 或用：
  - `run_lab_2.bat`

### 2. 整理這次改動

建議至少看這幾個 Git 指令：

```powershell
git -C G:\TanukiProject\tanuki_app status
git -C G:\TanukiProject\tanuki_app diff --stat
git -C G:\TanukiProject\tanuki_app log --oneline --decorate -n 15
```

如果要直接比前一版 tag 和目前差異：

```powershell
git -C G:\TanukiProject\tanuki_app diff --stat v0.4.1-beta..HEAD
git -C G:\TanukiProject\tanuki_app log --oneline v0.4.1-beta..HEAD
```

這兩組資訊通常就足夠寫出初版 release note。

### 3. 撰寫 release note

我建議固定寫成三段：

1. 玩家有感更新
2. 穩定性 / 體驗修正
3. 架構 / 開發工具整理

這樣就算之後模組再拆更多，公告仍然好讀。

### 4. 提交原始碼

```powershell
git -C G:\TanukiProject\tanuki_app status
git -C G:\TanukiProject\tanuki_app add -- <explicit-paths>
git -C G:\TanukiProject\tanuki_app diff --cached --name-only
python G:\TanukiProject\tanuki_app\tools\check_staged_secrets.py
git -C G:\TanukiProject\tanuki_app diff --cached
git -C G:\TanukiProject\tanuki_app commit -m "..."
```

不得使用無條件的 `git add .`。每次只 stage 本次 commit 負責的明確路徑，安全檢查只輸出檔名與命中規則，不輸出匹配內容。

首次設定此 repo 時，啟用並確認版本化 hook：

```powershell
git -C G:\TanukiProject\tanuki_app config core.hooksPath .githooks
git -C G:\TanukiProject\tanuki_app config --get core.hooksPath
```

### 5. 建立版本 tag

例如：

```powershell
git -C G:\TanukiProject\tanuki_app tag v0.5.0-beta
```

只有在 commit、tag、測試與 staged 安全檢查都確認完成，並取得明確同意後，才執行 `git push` 與 `git push origin <tag>`。

### 6. 打包

先檢查 Python、PyInstaller 與必要素材：

```powershell
& G:\TanukiProject\tanuki_app\build_lab_2.ps1 -CheckOnly
```

執行：

- `build_lab_2.bat`

腳本會優先使用 `TANUKI_PYTHON` 或 `-PythonExe` 指定的直譯器，否則依序尋找 G 槽 `.venv` 與本機 Python 3.10。封裝內容包括 `assets_cropped/`、`items/`、`heart.png`、`star.png` 與 `think.png`。

目前打包結果輸出到：

- `G:\TanukiProject\dist\TanukiPet`

### 7. 簽章與發布

建議流程：

1. 對 exe 簽章
2. 壓縮發布資料夾
3. 上傳到 GitHub Release
4. 把對應版本的 release note 一起貼上

## 四、我會建議的日常習慣

### 1. 每次做大功能時，順手記一行

例如先寫在 commit message 或暫存筆記裡：

- 新增視窗停留
- 修正 drag 動畫
- 加入時間流速

這樣之後整理 release note 會輕鬆很多。

### 2. 少做「整份 Python 備份」，多做「有意義的版本標記」

多模組架構之後，真正重要的是：

- 哪些模組新增
- 哪些行為改了
- 哪些工具被加入

這些內容 Git 比手動備份更適合管理。

### 3. 重要跨版本時，再做一次人工總整理

像從 `0.3.0` 走到目前這種大型變化，人工寫一份總結文件還是很值得。

但之後日常版本不需要每次都回到「存一份完整 Python 當備份」。

## 五、簡單結論

從現在開始，最穩的方式是：

- 重要歷史版本留在 `archive/`
- 日常版本靠 Git commit + tag
- 發版時額外留一份 release note
- 寫公告時分成「玩家更新 / 穩定性修正 / 架構整理」三層

這樣就算專案已經從單檔變成多模組，我們之後一樣能很清楚地知道每一版到底改了什麼。
