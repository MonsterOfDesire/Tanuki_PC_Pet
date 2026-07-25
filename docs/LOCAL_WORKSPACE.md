# Maintainer local workspace

這份文件只描述目前維護者使用的巢狀 Windows 工作區。一般 clone、CI 與其他開發者不應依賴這些絕對路徑。

## 目前目錄

- 工作區：`G:\TanukiProject`
- Git repository：`G:\TanukiProject\tanuki_app`
- 外層啟動器：`G:\TanukiProject\run_lab_2.bat`
- Python：`C:\Users\HreoK\AppData\Local\Programs\Python\Python310\python.exe`
- 共用 site-packages：`G:\TanukiProject\.venv\Lib\site-packages`

`build_lab_2.ps1` 會偵測這個巢狀配置，並將 build／dist 放在外層工作區。一般 clone 則使用 repository 內的 `.venv`、`build` 與 `dist`。

## 維護者命令

```powershell
$env:PYTHONPATH = "G:\TanukiProject\tanuki_app;G:\TanukiProject\.venv\Lib\site-packages"
& "C:\Users\HreoK\AppData\Local\Programs\Python\Python310\python.exe" -m unittest discover -s "G:\TanukiProject\tanuki_app\tests"
```

正式程式與唯一發布 repository 始終是 `G:\TanukiProject\tanuki_app`。除非明確進行救援參考，不使用其他磁碟的舊工作區。
