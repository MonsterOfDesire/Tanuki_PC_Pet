param(
    [string]$PythonExe = $env:TANUKI_PYTHON,
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"

$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $appDir

$sitePackages = Join-Path $projectRoot ".venv\Lib\site-packages"
if ([string]::IsNullOrWhiteSpace($PythonExe)) {
    $pythonCandidates = @(
        (Join-Path $projectRoot ".venv\Scripts\python.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python310\python.exe")
    )
    $PythonExe = $pythonCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}

$scriptPath = Join-Path $appDir "lab_2.py"
$iconPath = Join-Path $appDir "luna.ico"
$assetsDir = Join-Path $appDir "assets_cropped"
$itemsDir = Join-Path $appDir "items"
$heartPath = Join-Path $appDir "heart.png"
$starPath = Join-Path $appDir "star.png"
$thinkPath = Join-Path $appDir "think.png"
$distDir = Join-Path $projectRoot "dist"
$workDir = Join-Path $projectRoot "build\lab_2"
$buildName = "TanukiPet"

if ([string]::IsNullOrWhiteSpace($PythonExe) -or -not (Test-Path -LiteralPath $PythonExe)) {
    throw "Missing Python interpreter. Set -PythonExe or TANUKI_PYTHON."
}
if (-not (Test-Path $scriptPath)) {
    throw "Missing script: $scriptPath"
}
if (-not (Test-Path $iconPath)) {
    throw "Missing icon: $iconPath"
}
if (-not (Test-Path $assetsDir)) {
    throw "Missing assets directory: $assetsDir"
}
if (-not (Test-Path $itemsDir)) {
    throw "Missing item icons directory: $itemsDir"
}
if (-not (Test-Path $heartPath)) {
    throw "Missing heart image: $heartPath"
}
if (-not (Test-Path $starPath)) {
    throw "Missing star image: $starPath"
}
if (-not (Test-Path $thinkPath)) {
    throw "Missing thought icon: $thinkPath"
}

$pythonPathEntries = @($appDir)
if (Test-Path -LiteralPath $sitePackages) {
    $pythonPathEntries += $sitePackages
}
if (-not [string]::IsNullOrWhiteSpace($env:PYTHONPATH)) {
    $pythonPathEntries += $env:PYTHONPATH
}
$env:PYTHONPATH = $pythonPathEntries -join [IO.Path]::PathSeparator

Write-Host "Using Python: $PythonExe"
Write-Host "Script file: $scriptPath"
Write-Host "Icon file: $iconPath"
Write-Host "Assets dir: $assetsDir"
Write-Host "Item icons: $itemsDir"
Write-Host "Heart image: $heartPath"
Write-Host "Star image: $starPath"
Write-Host "Thought icon: $thinkPath"
Write-Host "Work dir: $workDir"
Write-Host "Dist dir: $distDir"
Write-Host ""

& $PythonExe -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller is not available to the selected Python environment."
}
if ($CheckOnly) {
    Write-Host "Build prerequisites and packaged resources are available."
    exit 0
}

& $PythonExe -m PyInstaller `
  --noconfirm `
  --onedir `
  --windowed `
  --name $buildName `
  --icon $iconPath `
  --add-data "${assetsDir};assets_cropped" `
  --add-data "${itemsDir};items" `
  --add-data "${heartPath};." `
  --add-data "${starPath};." `
  --add-data "${thinkPath};." `
  --collect-all pynput `
  --clean `
  --specpath $workDir `
  --workpath $workDir `
  --distpath $distDir `
  $scriptPath

if ($LASTEXITCODE -ne 0) {
    throw "Build failed with code $LASTEXITCODE."
}

$buildDir = Join-Path $distDir $buildName
Write-Host ""
Write-Host "Build complete."
Write-Host "Output: $buildDir"
Write-Host "Packaged name: $buildName"
