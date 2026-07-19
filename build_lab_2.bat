@echo off
setlocal
cd /d "%~dp0"
PowerShell -ExecutionPolicy Bypass -File "%~dp0build_lab_2.ps1" %*
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
    echo.
    echo Build failed with code %EXIT_CODE%.
    pause
    exit /b %EXIT_CODE%
)
echo.
echo Build complete.
pause
endlocal
