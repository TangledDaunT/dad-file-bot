# Dad File Bot - COMPLETE One-Liner
# Installs everything, authenticates WhatsApp, configures, and starts bot
# Run: irm https://raw.githubusercontent.com/TangledDaunT/dad-file-bot/main/install_full.ps1 | iex

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Banner
Write-Host ""
Write-Host "  ═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "                                                     " -ForegroundColor Cyan
Write-Host "     📁 DAD FILE BOT - COMPLETE INSTALLER           " -ForegroundColor Cyan  
Write-Host "                                                     " -ForegroundColor Cyan
Write-Host "     Install → Authenticate → Configure → Run       " -ForegroundColor Cyan
Write-Host "                                                     " -ForegroundColor Cyan
Write-Host "  ═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Configuration
$InstallDir = "$env:USERPROFILE\dad-file-bot"
$GithubRepo = "TangledDaunT/dad-file-bot"

function Test-Command($Command) {
    try { Get-Command $Command -ErrorAction Stop; return $true } catch { return $false }
}

function Show-Progress($Step, $Total, $Message) {
    Write-Host ""
    Write-Host "[$Step/$Total] $Message" -ForegroundColor Yellow
}

function Wait-ForEnter($Message) {
    Write-Host ""
    Write-Host $Message -ForegroundColor Cyan
    Read-Host "Press ENTER to continue"
}

# Step 1: Check Python
Show-Progress 1 7 "Checking Python..."
if (Test-Command "python") {
    $pythonVersion = python --version 2>&1
    Write-Host "    ✓ $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "    ✗ Python not installed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Python 3.8+ from:" -ForegroundColor Yellow
    Write-Host "https://www.python.org/downloads/" -ForegroundColor White
    Write-Host ""
    Write-Host "Make sure to check 'Add Python to PATH' during installation." -ForegroundColor Gray
    exit 1
}

# Step 2: Check Node.js
Show-Progress 2 7 "Checking Node.js..."
if (Test-Command "node") {
    $nodeVersion = node --version 2>&1
    Write-Host "    ✓ Node.js $nodeVersion" -ForegroundColor Green
} else {
    Write-Host "    ✗ Node.js not installed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Node.js from:" -ForegroundColor Yellow
    Write-Host "https://nodejs.org/" -ForegroundColor White
    exit 1
}

# Step 3: Install wacli
Show-Progress 3 7 "Installing wacli (WhatsApp CLI)..."
Write-Host "    This may take a minute..." -ForegroundColor Gray
try {
    npm install -g wacli 2>&1 | Out-Null
    Write-Host "    ✓ wacli installed" -ForegroundColor Green
} catch {
    Write-Host "    ✗ Failed to install wacli" -ForegroundColor Red
    exit 1
}

# Step 4: Create directory and download files
Show-Progress 4 7 "Downloading bot files..."
if (!(Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

$files = @("bot.py", "file_search.py", "wacli_wrapper.py", "config.yaml", "requirements.txt")
$baseUrl = "https://raw.githubusercontent.com/$GithubRepo/main"

foreach ($file in $files) {
    $url = "$baseUrl/$file"
    $outFile = Join-Path $InstallDir $file
    try {
        Invoke-WebRequest -Uri $url -OutFile $outFile -TimeoutSec 30 -ErrorAction Stop
        Write-Host "    ✓ $file" -ForegroundColor Green
    } catch {
        Write-Host "    ✗ Failed: $file" -ForegroundColor Red
    }
}

# Step 5: Install Python dependencies
Show-Progress 5 7 "Installing Python packages..."
python -m pip install --upgrade pip --quiet 2>&1 | Out-Null
pip install -r (Join-Path $InstallDir "requirements.txt") --quiet 2>&1 | Out-Null
Write-Host "    ✓ Packages installed" -ForegroundColor Green

# Step 6: Configure
Show-Progress 6 7 "Configuration"
Write-Host ""
Write-Host "Enter your dad's WhatsApp number (with country code):" -ForegroundColor Yellow
Write-Host "Example: +919876543210" -ForegroundColor Gray
$dadNumber = Read-Host ">"
if ($dadNumber) {
    $configPath = Join-Path $InstallDir "config.yaml"
    $config = Get-Content $configPath -Raw
    $config = $config -replace 'approved_sender: "\+919876543210"', "approved_sender: `"$dadNumber`""
    $config = $config -replace 'scan_directory: "E:\\\\', 'scan_directory: "E:\\"'
    Set-Content -Path $configPath -Value $config
    Write-Host "    ✓ Config saved" -ForegroundColor Green
}

# Step 7: WhatsApp Authentication
Show-Progress 7 7 "WhatsApp Authentication"
Write-Host ""
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "                   IMPORTANT!                      " -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "You need to scan a QR code with your phone to link WhatsApp." -ForegroundColor White
Write-Host ""
Write-Host "Steps:" -ForegroundColor Yellow
Write-Host "  1. Open WhatsApp on your phone" -ForegroundColor White
Write-Host "  2. Go to Settings → Linked Devices → Link a Device" -ForegroundColor White
Write-Host "  3. Point camera at the QR code that will appear" -ForegroundColor White
Write-Host ""
Wait-ForEnter "Ready? Press ENTER to show QR code..."

Write-Host ""
Write-Host "Opening wacli authentication..." -ForegroundColor Cyan
Write-Host "(If no QR appears, check the window behind this one)" -ForegroundColor Gray
Write-Host ""

# Try to run wacli auth
$authProcess = Start-Process -FilePath "wacli" -ArgumentList "auth" -NoNewWindow -PassThru

Write-Host "Waiting for authentication..." -ForegroundColor Yellow
Write-Host "(This may take up to 2 minutes)" -ForegroundColor Gray

# Wait for auth to complete or timeout
$timeout = 120
$elapsed = 0
while (!$authProcess.HasExited -and $elapsed -lt $timeout) {
    Start-Sleep -Seconds 1
    $elapsed++
    if ($elapsed % 10 -eq 0) {
        Write-Host "  ...still waiting ($elapsed seconds)" -ForegroundColor Gray
    }
}

if (!$authProcess.HasExited) {
    Write-Host ""
    Write-Host "⚠ Authentication is taking too long. Check the other window." -ForegroundColor Yellow
    Write-Host "Press ENTER here when you've scanned the QR code..." -ForegroundColor Cyan
    Read-Host
}

# Verify auth worked
Write-Host ""
Write-Host "Verifying authentication..." -ForegroundColor Yellow
$wacliCheck = Start-Process -FilePath "wacli" -ArgumentList "doctor" -WindowStyle Hidden -PassThru -Wait
if ($wacliCheck.ExitCode -eq 0) {
    Write-Host "    ✓ WhatsApp authenticated!" -ForegroundColor Green
} else {
    Write-Host "    ⚠ Could not verify authentication" -ForegroundColor Yellow
    Write-Host "      The bot may still work. Try running: wacli auth" -ForegroundColor Gray
}

# Build file index
Write-Host ""
Write-Host "[EXTRA] Building file index..." -ForegroundColor Yellow
Write-Host "    Scanning E:\ drive for PDF/DOC files..." -ForegroundColor Gray
cd $InstallDir
$indexOutput = python bot.py index 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "    ✓ Index built" -ForegroundColor Green
    if ($indexOutput -match "Indexed (\d+)") {
        Write-Host "      Found $($matches[1]) files" -ForegroundColor Gray
    }
} else {
    Write-Host "    ⚠ Index failed (will retry on bot start)" -ForegroundColor Yellow
}

# Create desktop shortcut
Write-Host ""
Write-Host "Creating shortcut..." -ForegroundColor Yellow
try {
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\Dad File Bot.lnk")
    $Shortcut.TargetPath = "cmd.exe"
    $Shortcut.Arguments = "/k cd /d `"$InstallDir`" && python bot.py"
    $Shortcut.WorkingDirectory = $InstallDir
    $Shortcut.IconLocation = "cmd.exe,0"
    $Shortcut.Save()
    Write-Host "    ✓ Desktop shortcut created" -ForegroundColor Green
} catch {
    Write-Host "    ⚠ Could not create shortcut" -ForegroundColor Yellow
}

# Summary and start
Write-Host ""
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "         ✅ SETUP COMPLETE!                        " -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "Installation: $InstallDir" -ForegroundColor Cyan
Write-Host "Desktop shortcut: Created" -ForegroundColor Cyan
Write-Host ""
Write-Host "The bot is ready to start!" -ForegroundColor White
Write-Host ""

$startNow = Read-Host "Start the bot now? (y/n)"
if ($startNow -eq 'y' -or $startNow -eq 'Y') {
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "         🚀 STARTING DAD FILE BOT                  " -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Your dad can now send messages to request files!" -ForegroundColor White
    Write-Host "Press Ctrl+C to stop the bot." -ForegroundColor Gray
    Write-Host ""
    
    # Start the bot in the current window
    python bot.py
} else {
    Write-Host ""
    Write-Host "To start later:" -ForegroundColor Yellow
    Write-Host "  1. Double-click 'Dad File Bot' on your desktop" -ForegroundColor White
    Write-Host "  2. Or run: cd $InstallDir; python bot.py" -ForegroundColor White
}

Write-Host ""
Write-Host "Happy file sharing! 🐶" -ForegroundColor Magenta
Write-Host ""
