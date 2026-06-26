@echo off
cd /d "%~dp0"

where pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller not found — installing...
    pip install pyinstaller
)

echo Building Blancome...
py -3.13 -m PyInstaller blancome.spec --clean

if %errorlevel% neq 0 (
    echo.
    echo Build FAILED. Check the output above for errors.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Build complete!  dist\Blancome\Blancome.exe is ready.
echo ============================================================
echo.
echo  Before running the exe, copy your .env file here:
echo    dist\Blancome\.env
echo.
pause
