@echo off
REM Double-click this file on Windows to start the Veston Campaign Tool
cd /d "%~dp0"

echo.
echo ======================================
echo   Setting up Veston Campaign Tool...
echo ======================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed.
    echo.
    echo To install it:
    echo   1. Go to python.org/downloads
    echo   2. Download the latest version for Windows
    echo   3. IMPORTANT: Check "Add Python to PATH" during install
    echo   4. Run the installer
    echo   5. Then double-click this file again
    echo.
    pause
    exit /b 1
)

REM Install dependencies
echo Installing dependencies...
python -m pip install flask requests python-dotenv --quiet 2>nul

REM Check if .env exists
if not exist .env (
    echo.
    echo No .env file found. Creating one...
    echo.
    echo You need your API keys. Get them from:
    echo   - DropLeads: your DropLeads dashboard
    echo   - Instantly: app.instantly.ai ^> Settings ^> API
    echo.
    set /p DL_KEY="Paste your DropLeads API key (or press Enter to skip): "
    set /p IN_KEY="Paste your Instantly API key (or press Enter to skip): "
    echo.
    (
        echo DROPLEADS_API_KEY=%DL_KEY%
        echo INSTANTLY_API_KEY=%IN_KEY%
    ) > .env
    echo Saved to .env file.
    echo.
)

echo Starting... (your browser will open automatically)
echo.
python campaign_app.py
