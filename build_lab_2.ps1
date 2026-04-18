$ErrorActionPreference = "Stop"

$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $appDir

$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$scriptPath = Join-Path $appDir "lab_2.py"
$iconPath = Join-Path $appDir "luna.ico"
$assetsDir = Join-Path $appDir "assets_cropped"
$heartPath = Join-Path $appDir "heart.png"
$starPath = Join-Path $appDir "star.png"
$distDir = Join-Path $projectRoot "dist"
$workDir = Join-Path $projectRoot "build\lab_2"
$buildName = "TanukiPet"

if (-not (Test-Path $pythonExe)) {
    throw "Missing interpreter: $pythonExe"
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
if (-not (Test-Path $heartPath)) {
    throw "Missing heart image: $heartPath"
}
if (-not (Test-Path $starPath)) {
    throw "Missing star image: $starPath"
}

Write-Host "Using Python: $pythonExe"
Write-Host "Script file: $scriptPath"
Write-Host "Icon file: $iconPath"
Write-Host "Assets dir: $assetsDir"
Write-Host "Heart image: $heartPath"
Write-Host "Star image: $starPath"
Write-Host "Work dir: $workDir"
Write-Host "Dist dir: $distDir"
Write-Host ""

& $pythonExe -m PyInstaller `
  --noconfirm `
  --onedir `
  --windowed `
  --name $buildName `
  --icon $iconPath `
  --add-data "${assetsDir};assets_cropped" `
  --add-data "${heartPath};." `
  --add-data "${starPath};." `
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
