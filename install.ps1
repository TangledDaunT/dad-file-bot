# Dad File Bot - PowerShell One-Line Installer
# ============================================
# Run with: irm https://raw.githubusercontent.com/YOUR_USERNAME/dad-file-bot/main/install.ps1 | iex

param(
    [string]$InstallDir = "$env:USERPROFILE\dad-file-bot",
    [string]$GithubRepo = "YOUR_USERNAME/dad-file-bot"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  ===================================" -ForegroundColor Cyan
Write-Host "   Dad File Bot - Windows Installer" -ForegroundColor Cyan
Write-Host "  ===================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "[CHECK] Python..." -NoNewline
try {
    $pythonVersion = python --version 2>$null
    if ($LASTEXITCODE -ne 0) { throw "Python not found" }
    Write-Host " OK ($pythonVersion)" -ForegroundColor Green
} catch {
    Write-Host " FAILED" -ForegroundColor Red
    Write-Host ""
    Write-Host "ERROR: Python is not installed." -ForegroundColor Red
    Write-Host "Please install Python 3.8+ from: https://www.python.org/downloads/"
    Write-Host "Make sure to check 'Add Python to PATH' during installation."
    exit 1
}

# Check Node.js
Write-Host "[CHECK] Node.js..." -NoNewline
try {
    $nodeVersion = node --version 2>$null
    if ($LASTEXITCODE -ne 0) { throw "Node not found" }
    Write-Host " OK ($nodeVersion)" -ForegroundColor Green
} catch {
    Write-Host " FAILED" -ForegroundColor Red
    Write-Host ""
    Write-Host "ERROR: Node.js is required for wacli." -ForegroundColor Red
    Write-Host "Please install from: https://nodejs.org/"
    exit 1
}

# Install wacli
Write-Host ""
Write-Host "[1/5] Installing wacli (WhatsApp CLI)..." -ForegroundColor Yellow
npm install -g wacli 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAILED to install wacli" -ForegroundColor Red
    exit 1
}
Write-Host "  OK - wacli installed" -ForegroundColor Green

# Create directory
Write-Host ""
Write-Host "[2/5] Creating installation directory..." -ForegroundColor Yellow
if (!(Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}
Write-Host "  OK - $InstallDir" -ForegroundColor Green

Set-Location $InstallDir

# Download files
Write-Host ""
Write-Host "[3/5] Downloading files from GitHub..." -ForegroundColor Yellow

$files = @(
    "bot.py",
    "file_search.py",
    "wacli_wrapper.py",
    "config.yaml",
    "requirements.txt",
    "README.md"
)

$baseUrl = "https://raw.githubusercontent.com/$GithubRepo/main"

foreach ($file in $files) {
    $url = "$baseUrl/$file"
    $outFile = Join-Path $InstallDir $file
    try {
        Invoke-WebRequest -Uri $url -OutFile $outFile -TimeoutSec 30
        Write-Host "  Downloaded: $file" -ForegroundColor Green
    } catch {
        Write-Host "  Failed: $file" -ForegroundColor Red
    }
}

# Install Python dependencies
Write-Host ""
Write-Host "[4/5] Installing Python dependencies..." -ForegroundColor Yellow
python -m pip install --upgrade pip 2>&1 | Out-Null
pip install -r requirements.txt 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  WARNING: Some packages may not have installed correctly" -ForegroundColor Yellow
}
Write-Host "  OK - Dependencies installed" -ForegroundColor Green

# Create desktop shortcut
Write-Host ""
Write-Host "[5/5] Creating shortcuts..." -ForegroundColor Yellow

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\Dad File Bot.lnk")
$Shortcut.TargetPath = "cmd.exe"
$Shortcut.Arguments = "/k cd /d `"$InstallDir`" && python bot.py"
$Shortcut.WorkingDirectory = $InstallDir
$Shortcut.IconLocation = "cmd.exe,0"
$Shortcut.Save()

Write-Host "  OK - Desktop shortcut created" -ForegroundColor Green

# Summary
Write-Host ""
Write-Host "  ===================================" -ForegroundColor Green
Write-Host "        INSTALLATION COMPLETE!" -ForegroundColor Green
Write-Host "  ===================================" -ForegroundColor Green
Write-Host ""
Write-Host "Installation directory: $InstallDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. EDIT CONFIG:" -ForegroundColor Cyan
Write-Host "   notepad '$InstallDir\config.yaml'" -ForegroundColor White
Write-Host ""
Write-Host "   Change these values:" -ForegroundColor Gray
Write-Host "     approved_sender: +919876543210  <- Dad's WhatsApp number" -ForegroundColor White
Write-Host "     scan_directory: E:\\             <- Your files location" -ForegroundColor White
Write-Host ""
Write-Host "2. AUTHENTICATE:" -ForegroundColor Cyan
Write-Host "   wacli auth" -ForegroundColor White
Write-Host "   (Scan QR code with your phone)" -ForegroundColor Gray
Write-Host ""
Write-Host "3. INDEX FILES:" -ForegroundColor Cyan
Write-Host "   cd '$InstallDir'" -ForegroundColor White
Write-Host "   python bot.py index" -ForegroundColor White
Write-Host ""
Write-Host "4. START BOT:" -ForegroundColor Cyan
Write-Host "   python bot.py" -ForegroundColor White
Write-Host "   (Or use the Desktop shortcut)" -ForegroundColor Gray
Write-Host ""
Write-Host "  ===================================" -ForegroundColor Green
Write-Host ""

# Ask to open config
$openConfig = Read-Host "Open config.yaml now? (y/n)"
if ($openConfig -eq 'y' -or $openConfig -eq 'Y') {
    notepad "$InstallDir\config.yaml"
}

Write-Host ""
Write-Host "Happy file sharing! 🐶" -ForegroundColor Magenta
Write-Host ""

Set-Location $env:USERPROFILE
