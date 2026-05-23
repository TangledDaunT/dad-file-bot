@echo off
REM ============================================
REM Dad File Bot - ALL-IN-ONE INSTALLER
REM Install + Authenticate + Start Bot
REM ============================================

echo.
echo ============================================
echo    DAD FILE BOT - COMPLETE SETUP
echo ============================================
echo.
echo This installer will:
echo   1. Install required software
echo   2. Set up WhatsApp authentication
echo   3. Configure the bot
echo   4. Start the bot
echo.
pause

REM Download the Python installer script if not present
if not exist "install_easy.py" (
    echo.
    echo Downloading installer...
    powershell -Command "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/TangledDaunT/dad-file-bot/main/install_easy.py' -OutFile 'install_easy.py' -TimeoutSec 30"
    if errorlevel 1 (
        echo Failed to download installer.
        echo Please check your internet connection.
        pause
        exit /b 1
    )
)

REM Run the Python installer
python install_easy.py

REM If Python isn't in PATH, try direct Python path
if errorlevel 1 (
    echo.
    echo Trying alternative Python path...
    %USERPROFILE%\AppData\Local\Programs\Python\Python3*\python.exe install_easy.py 2>nul
    if errorlevel 1 (
        C:\Python3*\python.exe install_easy.py 2>nul
    )
)

echo.
echo ============================================
echo    Setup complete!
echo ============================================
pause
