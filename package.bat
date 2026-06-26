@echo off
cd /d "%~dp0"

if not exist "dist\Blancome\Blancome.exe" (
    echo ERROR: dist\Blancome\Blancome.exe not found. Run build.bat first.
    pause
    exit /b 1
)

set /p VERSION="Version number (e.g. 1.0.0): "
set OUTFILE=Blancome-v%VERSION%-windows.zip

:: Copy settings.example.json so users have a reference
if exist "settings.example.json" (
    copy /y "settings.example.json" "dist\Blancome\settings.example.json" >nul
)

:: Remove personal settings file (developer's own config must not ship)
if exist "dist\Blancome\settings.json" del "dist\Blancome\settings.json"

:: Remove OAuth tokens too
if exist "dist\Blancome\google_token.json"     del "dist\Blancome\google_token.json"
if exist "dist\Blancome\microsoft_token.json"  del "dist\Blancome\microsoft_token.json"

echo Zipping...
if exist "%OUTFILE%" del "%OUTFILE%"
powershell -Command "Compress-Archive -Path 'dist\Blancome\*' -DestinationPath '%OUTFILE%' -Force"

echo.
echo ============================================================
echo  Package ready: %OUTFILE%
echo  Upload this file to your GitHub Release.
echo ============================================================
echo.
pause
