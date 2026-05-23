@echo off
REM Dad File Bot - One-Line Installer for Windows
REM ================================================

echo.
echo  ===================================
echo   Dad File Bot - Windows Installer
echo  ===================================
echo.

REM Check if running as admin (optional but recommended)
REM net session >nul 2>&1
REM if %errorlevel% neq 0 (
REM     echo Note: Running without admin privileges. Some features may be limited.
REM     echo.
REM )

REM Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo.
    echo Please install Python 3.8 or higher from:
    echo https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [OK] Python found
for /f "tokens=*" %%a in ('python --version') do (set python_ver=%%a)
echo     Version: %python_ver%
echo.

REM Check Node.js (required for wacli)
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Node.js not found! wacli requires Node.js.
    echo.
    echo Please install Node.js from:
    echo https://nodejs.org/
    echo.
    pause
    exit /b 1
)

echo [OK] Node.js found
for /f "tokens=*" %%a in ('node --version') do (set node_ver=%%a)
echo     Version: %node_ver%
echo.

REM Install wacli
echo [1/4] Installing wacli (WhatsApp CLI)...
npm install -g wacli
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install wacli.
    pause
    exit /b 1
)
echo [OK] wacli installed
echo.

REM Create installation directory
set INSTALL_DIR=%USERPROFILE%\dad-file-bot
if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%"
)

cd /d "%INSTALL_DIR%"

REM Download files from GitHub (or copy if local)
echo [2/4] Downloading Dad File Bot files...
echo     Installing to: %INSTALL_DIR%

REM If running from local folder, copy files
if exist "%~dp0bot.py" (
    echo     Copying from local folder...
    copy "%~dp0*.py" "%INSTALL_DIR%\" >nul
    copy "%~dp0*.yaml" "%INSTALL_DIR%\" >nul
    copy "%~dp0*.txt" "%INSTALL_DIR%\" >nul
) else (
    echo     Downloading from GitHub...
    powershell -Command "& {Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/YOUR_USERNAME/dad-file-bot/main/bot.py' -OutFile 'bot.py'}"
    powershell -Command "& {Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/YOUR_USERNAME/dad-file-bot/main/config.yaml' -OutFile 'config.yaml'}"
    powershell -Command "& {Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/YOUR_USERNAME/dad-file-bot/main/requirements.txt' -OutFile 'requirements.txt'}"
    powershell -Command "& {Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/YOUR_USERNAME/dad-file-bot/main/file_search.py' -OutFile 'file_search.py'}"
    powershell -Command "& {Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/YOUR_USERNAME/dad-file-bot/main/wacli_wrapper.py' -OutFile 'wacli_wrapper.py'}"
)
echo [OK] Files downloaded
echo.

REM Install Python dependencies
echo [3/4] Installing Python dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Python dependencies.
    pause
    exit /b 1
)
echo [OK] Dependencies installed
echo.

REM Create config from template if it doesn't exist
if not exist "%INSTALL_DIR%\config.yaml" (
    copy "%INSTALL_DIR%\config.yaml" "%INSTALL_DIR%\config.yaml.bak" >nul 2>&1
)

echo [4/4] Setup complete!
echo.
echo ===================================
echo         NEXT STEPS
echo ===================================
echo.
echo 1. EDIT CONFIG FILE:
echo    Notepad %INSTALL_DIR%\config.yaml
echo.
echo    Change these values:
echo    - approved_sender: YOUR_DAD'S_NUMBER (e.g., +919876543210)
echo    - scan_directory: E:\\
echo.
echo 2. AUTHENTICATE WITH WHATSAPP:
echo    wacli auth
echo    (Scan QR code with your phone)
echo.
echo 3. BUILD FILE INDEX:
echo    python %INSTALL_DIR%\bot.py index
echo.
echo 4. START THE BOT:
echo    python %INSTALL_DIR%\bot.py
echo.
echo ===================================
echo.

REM Ask if they want to open config
set /p edit_config="Open config.yaml to edit now? (y/n): "
if /i "%edit_config%"=="y" (
    notepad "%INSTALL_DIR%\config.yaml"
)

echo.
echo Happy file sharing! 🐶
echo.
pause
