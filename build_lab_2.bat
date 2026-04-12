@echo off
setlocal

set "APP_DIR=%~dp0"
if "%APP_DIR:~-1%"=="\" set "APP_DIR=%APP_DIR:~0,-1%"
for %%I in ("%APP_DIR%\..") do set "PROJECT_ROOT=%%~fI"

set "PYTHON_EXE=%PROJECT_ROOT%\.venv\Scripts\python.exe"
set "SPEC_PATH=%APP_DIR%\lab_2.spec"
set "DIST_DIR=%PROJECT_ROOT%\dist"
set "WORK_DIR=%PROJECT_ROOT%\build\lab_2"

if not exist "%PYTHON_EXE%" (
    echo Missing interpreter:
    echo %PYTHON_EXE%
    pause
    exit /b 1
)

if not exist "%SPEC_PATH%" (
    echo Missing spec file:
    echo %SPEC_PATH%
    pause
    exit /b 1
)

pushd "%APP_DIR%"

echo Using Python: %PYTHON_EXE%
echo Spec file: %SPEC_PATH%
echo Work dir: %WORK_DIR%
echo Dist dir: %DIST_DIR%
echo.

"%PYTHON_EXE%" -m PyInstaller --noconfirm --clean --workpath "%WORK_DIR%" --distpath "%DIST_DIR%" "%SPEC_PATH%"
set "EXIT_CODE=%ERRORLEVEL%"

popd

if not "%EXIT_CODE%"=="0" (
    echo.
    echo Build failed with code %EXIT_CODE%.
    pause
    exit /b %EXIT_CODE%
)

echo.
echo Build complete.
echo Output: %DIST_DIR%
pause
endlocal
