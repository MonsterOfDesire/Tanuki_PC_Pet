param(
    [string]$PythonExe = $env:TANUKI_PYTHON,
    [string]$OutputRoot = $env:TANUKI_BUILD_ROOT,
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$outerRoot = Split-Path -Parent $repoRoot
$outerSitePackages = Join-Path $outerRoot ".venv\Lib\site-packages"
$isNestedWorkspace =
    (Test-Path -LiteralPath (Join-Path $outerRoot "run_lab_2.bat")) -and
    (Test-Path -LiteralPath $outerSitePackages)
$workspaceRoot = if ($isNestedWorkspace) { $outerRoot } else { $repoRoot }

if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $OutputRoot = $workspaceRoot
}
$OutputRoot = [IO.Path]::GetFullPath($OutputRoot)

if ([string]::IsNullOrWhiteSpace($PythonExe)) {
    $pythonCandidates = @(
        (Join-Path $repoRoot ".venv\Scripts\python.exe"),
        (Join-Path $workspaceRoot ".venv\Scripts\python.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python310\python.exe")
    ) | Select-Object -Unique
    $PythonExe = $pythonCandidates |
        Where-Object { Test-Path -LiteralPath $_ } |
        Select-Object -First 1
}

$scriptPath = Join-Path $repoRoot "lab_2.py"
$iconPath = Join-Path $repoRoot "luna.ico"
$assetsDir = Join-Path $repoRoot "assets_cropped"
$itemsDir = Join-Path $repoRoot "items"
$heartPath = Join-Path $repoRoot "heart.png"
$starPath = Join-Path $repoRoot "star.png"
$thinkPath = Join-Path $repoRoot "think.png"
$distDir = Join-Path $OutputRoot "dist"
$workDir = Join-Path $OutputRoot "build\lab_2"
$buildName = "TanukiPet"

if ([string]::IsNullOrWhiteSpace($PythonExe) -or -not (Test-Path -LiteralPath $PythonExe)) {
    throw "Missing Python interpreter. Set -PythonExe or TANUKI_PYTHON."
}

$requiredPaths = @(
    @{ Label = "script"; Path = $scriptPath },
    @{ Label = "icon"; Path = $iconPath },
    @{ Label = "assets directory"; Path = $assetsDir },
    @{ Label = "item icons directory"; Path = $itemsDir },
    @{ Label = "heart image"; Path = $heartPath },
    @{ Label = "star image"; Path = $starPath },
    @{ Label = "thought icon"; Path = $thinkPath }
)
foreach ($required in $requiredPaths) {
    if (-not (Test-Path -LiteralPath $required.Path)) {
        throw "Missing $($required.Label): $($required.Path)"
    }
}

$sitePackageCandidates = @(
    (Join-Path $repoRoot ".venv\Lib\site-packages"),
    (Join-Path $workspaceRoot ".venv\Lib\site-packages")
) | Select-Object -Unique
$pythonPathEntries = @($repoRoot)
$pythonPathEntries += $sitePackageCandidates | Where-Object { Test-Path -LiteralPath $_ }
if (-not [string]::IsNullOrWhiteSpace($env:PYTHONPATH)) {
    $pythonPathEntries += $env:PYTHONPATH
}
$env:PYTHONPATH = $pythonPathEntries -join [IO.Path]::PathSeparator

Write-Host "Using Python: $PythonExe"
Write-Host "Repository root: $repoRoot"
Write-Host "Output root: $OutputRoot"
Write-Host "Script file: $scriptPath"
Write-Host "Work dir: $workDir"
Write-Host "Dist dir: $distDir"
Write-Host ""

& $PythonExe -c "import PyInstaller, PyQt6, pynput" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "Build dependencies are unavailable. Install requirements-build.txt with the selected Python environment."
}
if ($CheckOnly) {
    Write-Host "Build dependencies and packaged resources are available."
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
