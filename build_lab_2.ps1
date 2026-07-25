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
$uiDir = Join-Path $repoRoot "UI"
$uiFamilyIconsDir = Join-Path $uiDir "family_icon"
$uiDietPath = Join-Path $uiDir "diet.png"
$uiDietCharacterPath = Join-Path $uiDir "diet_char.gif"
$uiRelationPath = Join-Path $uiDir "relation_summon.gif"
$uiRelationCharacterPath = Join-Path $uiDir "relation_summon_char.gif"
$uiEventPath = Join-Path $uiDir "event_note.jpg"
$uiEventCharacterPath = Join-Path $uiDir "event_note_char.gif"
$uiFamilyPath = Join-Path $uiDir "family_status_abstract.png"
$uiFamilyCharacterPath = Join-Path $uiDir "family_status_abstract_char.gif"
$uiSettingsPath = Join-Path $uiDir "status_setting.png"
$uiSettingsCharacterPath = Join-Path $uiDir "status_setting_char.gif"
$uiDashboardSideIconPath = Join-Path $uiDir "side.png"
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
    @{ Label = "UI family icon directory"; Path = $uiFamilyIconsDir },
    @{ Label = "Air Groove family icon"; Path = (Join-Path $uiFamilyIconsDir "Air Groove.gif") },
    @{ Label = "Sirius Symboli family icon"; Path = (Join-Path $uiFamilyIconsDir "Sirius Symboli.gif") },
    @{ Label = "Symboli Rudolf family icon"; Path = (Join-Path $uiFamilyIconsDir "Symboli Rudolf.gif") },
    @{ Label = "Tokai Teio family icon"; Path = (Join-Path $uiFamilyIconsDir "Tokai Teio.gif") },
    @{ Label = "Tsurumaru Tsuyoshi family icon"; Path = (Join-Path $uiFamilyIconsDir "Tsurumaru Tsuyoshi.gif") },
    @{ Label = "diet UI background"; Path = $uiDietPath },
    @{ Label = "diet UI character"; Path = $uiDietCharacterPath },
    @{ Label = "relationship UI background"; Path = $uiRelationPath },
    @{ Label = "relationship UI character"; Path = $uiRelationCharacterPath },
    @{ Label = "event UI background"; Path = $uiEventPath },
    @{ Label = "event UI character"; Path = $uiEventCharacterPath },
    @{ Label = "family UI background"; Path = $uiFamilyPath },
    @{ Label = "family UI character"; Path = $uiFamilyCharacterPath },
    @{ Label = "settings UI background"; Path = $uiSettingsPath },
    @{ Label = "settings UI character"; Path = $uiSettingsCharacterPath },
    @{ Label = "dashboard launcher side icon"; Path = $uiDashboardSideIconPath },
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
  --add-data "${uiDietPath};UI" `
  --add-data "${uiDietCharacterPath};UI" `
  --add-data "${uiRelationPath};UI" `
  --add-data "${uiRelationCharacterPath};UI" `
  --add-data "${uiEventPath};UI" `
  --add-data "${uiEventCharacterPath};UI" `
  --add-data "${uiFamilyPath};UI" `
  --add-data "${uiFamilyCharacterPath};UI" `
  --add-data "${uiSettingsPath};UI" `
  --add-data "${uiSettingsCharacterPath};UI" `
  --add-data "${uiDashboardSideIconPath};UI" `
  --add-data "${uiFamilyIconsDir};UI/family_icon" `
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
