#!/usr/bin/env python3
"""
Dad File Bot - Easy Installer (Windows)
One command to install everything, authenticate WhatsApp, and start the bot.
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path


def print_banner():
    """Print welcome banner"""
    print("""
    ╔═══════════════════════════════════════════╗
    ║                                           ║
    ║       📁 DAD FILE BOT - EASY INSTALL      ║
    ║                                           ║
    ║  Install → Authenticate → Start Bot       ║
    ║                                           ║
    ╚═══════════════════════════════════════════╝
    """)


def run_command(cmd, capture=True, timeout=60):
    """Run a shell command and return success/output"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=capture,
            text=True,
            timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)


def check_python():
    """Check if Python is installed"""
    print("[1/7] Checking Python...")
    success, stdout, stderr = run_command("python --version")
    if success:
        print(f"    ✓ {stdout.strip()}")
        return True
    else:
        print("    ✗ Python not found!")
        print("\nPlease install Python 3.8+ from https://www.python.org/downloads/")
        print('Make sure to check "Add Python to PATH" during installation.')
        return False


def check_nodejs():
    """Check if Node.js is installed"""
    print("\n[2/7] Checking Node.js...")
    success, stdout, stderr = run_command("node --version")
    if success:
        print(f"    ✓ {stdout.strip()}")
        return True
    else:
        print("    ✗ Node.js not found!")
        print("\nPlease install Node.js from https://nodejs.org/")
        return False


def install_wacli():
    """Install wacli globally"""
    print("\n[3/7] Installing wacli (WhatsApp CLI)...")
    print("    This may take a minute...")
    success, stdout, stderr = run_command("npm install -g wacli", timeout=120)
    if success or "already exists" in stderr.lower():
        print("    ✓ wacli installed")
        return True
    else:
        print(f"    ✗ Failed: {stderr}")
        return False


def install_python_packages(install_dir):
    """Install Python dependencies"""
    print("\n[4/7] Installing Python packages...")
    
    # Upgrade pip first
    run_command("python -m pip install --upgrade pip --quiet", timeout=60)
    
    req_file = os.path.join(install_dir, "requirements.txt")
    if os.path.exists(req_file):
        success, stdout, stderr = run_command(
            f"pip install -r \"{req_file}\" --quiet", 
            timeout=120
        )
        if success:
            print("    ✓ Packages installed")
            return True
        else:
            print(f"    ✗ Failed: {stderr}")
            return False
    else:
        # Install manually if requirements.txt not found
        packages = "fuzzywuzzy python-Levenshtein pyyaml"
        success, _, _ = run_command(f"pip install {packages} --quiet", timeout=120)
        print("    ✓ Packages installed")
        return success


def download_files(install_dir):
    """Download bot files from GitHub"""
    print("\n[5/7] Downloading bot files...")
    
    GITHUB_REPO = "TangledDaunT/dad-file-bot"
    base_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/"
    
    files = {
        "bot.py": "bot.py",
        "file_search.py": "file_search.py", 
        "wacli_wrapper.py": "wacli_wrapper.py",
        "config.yaml": "config.yaml",
        "requirements.txt": "requirements.txt"
    }
    
    os.makedirs(install_dir, exist_ok=True)
    
    for filename, _ in files.items():
        url = base_url + filename
        filepath = os.path.join(install_dir, filename)
        
        # Try to download using PowerShell (more reliable on Windows)
        ps_cmd = f'Invoke-WebRequest -Uri "{url}" -OutFile "{filepath}" -TimeoutSec 30'
        success, _, _ = run_command(f'powershell -Command "{ps_cmd}"', timeout=35)
        
        if success:
            print(f"    ✓ {filename}")
        else:
            print(f"    ✗ Failed to download {filename}")
    
    return True


def configure_bot(install_dir):
    """Get user config and update config.yaml"""
    print("\n[6/7] Configuration...")
    
    config_path = os.path.join(install_dir, "config.yaml")
    
    # Default values
    dad_number = ""
    scan_dir = "E:\\" 
    
    # Ask for dad's number
    print("\n    Enter your dad's WhatsApp number (with country code, e.g. +919876543210):")
    dad_input = input("    > ").strip()
    if dad_input:
        dad_number = dad_input
    
    # Ask for scan directory
    print(f"\n    Enter the directory to scan for files [default: {scan_dir}]:")
    dir_input = input("    > ").strip()
    if dir_input:
        scan_dir = dir_input
    
    # Update config file
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace values
        content = content.replace('approved_sender: "+919876543210"', f'approved_sender: "{dad_number}"')
        content = content.replace('scan_directory: "E:\\"', f'scan_directory: "{scan_dir}"')
        
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("    ✓ Config saved")
    else:
        print("    ⚠ Config file not found, using defaults")
    
    return dad_number


def authenticate_whatsapp():
    """Run wacli auth and show QR code"""
    print("\n[7/7] WhatsApp Authentication...")
    print("\n" + "="*60)
    print("📱 SCAN THE QR CODE WITH YOUR PHONE")
    print("="*60)
    print("\nSteps:")
    print("1. Open WhatsApp on your phone")
    print("2. Go to Settings → Linked Devices")
    print("3. Tap 'Link a Device'")
    print("4. Point camera at the QR code below")
    print("\n" + "="*60 + "\n")
    
    input("Press ENTER to show QR code...")
    print("\n")
    
    # Run wacli auth - this will show the QR code and wait
    result = subprocess.run("wacli auth", shell=True)
    
    if result.returncode == 0:
        print("\n" + "="*60)
        print("✓ WhatsApp authenticated successfully!")
        print("="*60)
        return True
    else:
        print("\n" + "="*60)
        print("✗ Authentication failed or timed out")
        print("="*60)
        return False


def build_file_index(install_dir):
    """Run initial file indexing"""
    print("\n[EXTRA] Building file index...")
    print("    Scanning for PDF and DOC files...")
    
    bot_path = os.path.join(install_dir, "bot.py")
    success, stdout, stderr = run_command(
        f'python "{bot_path}" index',
        capture=True,
        timeout=300
    )
    
    if success:
        # Parse output for count
        if "Indexed" in stdout:
            print(f"    ✓ {stdout.strip()}")
        else:
            print("    ✓ Index built")
        return True
    else:
        print(f"    ✗ Failed: {stderr}")
        return False


def start_bot(install_dir):
    """Start the bot"""
    print("\n" + "="*60)
    print("🚀 STARTING DAD FILE BOT")
    print("="*60 + "\n")
    
    bot_path = os.path.join(install_dir, "bot.py")
    
    print("The bot is now running!")
    print("Your dad can now send messages to request files.")
    print("\nPress Ctrl+C to stop the bot.\n")
    
    # Run the bot (this blocks until Ctrl+C)
    try:
        subprocess.run(f'python "{bot_path}"', shell=True, cwd=install_dir)
    except KeyboardInterrupt:
        print("\n\nBot stopped. Goodbye! 👋")


def create_desktop_shortcut(install_dir):
    """Create desktop shortcut for easy access"""
    try:
        shortcut_path = os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop', 'Dad File Bot.lnk')
        
        # PowerShell script to create shortcut
        script = f'''
        $WshShell = New-Object -ComObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
        $Shortcut.TargetPath = "cmd.exe"
        $Shortcut.Arguments = '/k cd /d "{install_dir}" && python bot.py'
        $Shortcut.WorkingDirectory = "{install_dir}"
        $Shortcut.IconLocation = "cmd.exe,0"
        $Shortcut.Save()
        '''
        
        subprocess.run(['powershell', '-Command', script], capture_output=True)
        return True
    except:
        return False


def main():
    """Main installer flow"""
    print_banner()
    
    # Set installation directory
    install_dir = os.path.join(os.environ.get('USERPROFILE', os.getcwd()), 'dad-file-bot')
    
    # Check prerequisites
    if not check_python():
        input("\nPress ENTER to exit...")
        sys.exit(1)
    
    if not check_nodejs():
        input("\nPress ENTER to exit...")
        sys.exit(1)
    
    # Install components
    if not install_wacli():
        print("\nFailed to install wacli. Please try manually:")
        print("  npm install -g wacli")
        input("\nPress ENTER to exit...")
        sys.exit(1)
    
    # Download files
    print("\nDownloading to:", install_dir)
    download_files(install_dir)
    
    # Install Python packages
    install_python_packages(install_dir)
    
    # Configure
    configure_bot(install_dir)
    
    # WhatsApp Auth
    if not authenticate_whatsapp():
        print("\nYou can authenticate later by running: wacli auth")
        retry = input("\nTry again now? (y/n): ").strip().lower()
        if retry == 'y':
            authenticate_whatsapp()
    
    # Build index
    build_file_index(install_dir)
    
    # Create shortcut
    create_desktop_shortcut(install_dir)
    
    # Start the bot
    start_bot(install_dir)


if __name__ == "__main__":
    main()
