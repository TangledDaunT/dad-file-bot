# 📁 Dad File Bot

A Python WhatsApp bot that lets your dad request files via text message. He sends a file name or number, and the bot finds and sends back the document automatically.

## 🎯 What It Does

- Your dad sends a WhatsApp message like: *"file of mayawati vs state of UP"*
- Bot searches your E:\ drive for matching PDF/DOC files
- Sends all matches and lets him pick which one
- Sends the file directly via WhatsApp

## 🚀 Quick Start (One-Line Install) - DOES EVERYTHING!

Open **PowerShell** and run this ONE command:

```powershell
irm https://raw.githubusercontent.com/TangledDaunT/dad-file-bot/main/install_full.ps1 | iex
```

This will:
1. ✅ Check/install Python & Node.js
2. ✅ Install WhatsApp CLI (wacli)
3. ✅ Download all bot files
4. ✅ Ask for configuration (dad's number)
5. **→ Show QR code for WhatsApp login**
6. ✅ Build file index
7. **→ Start the bot!**

That's it! Your dad can start using it immediately.

### Alternative: Download and Run

Download `install_windows.bat` from the releases page and double-click it.

## 📋 Requirements

- Windows 10/11
- Python 3.8+
- Node.js 16+ (for WhatsApp CLI)

## ⚙️ Setup

### 1. Install

```cmd
install.bat
```

### 2. Configure

Edit `config.yaml`:

```yaml
approved_sender: "+919876543210"  # Your dad's WhatsApp number
scan_directory: "E:\\"              # Where to look for files
file_extensions:
  - ".pdf"
  - ".doc"
  - ".docx"
```

### 3. Authenticate

```cmd
wacli auth
```

Scan the QR code with your phone to link the bot.

### 4. Index Files

```cmd
python bot.py index
```

### 5. Start the Bot

```cmd
python bot.py
```

## 💬 How Dad Uses It

| He sends... | Bot responds... |
|------------|-----------------|
| `mayawati vs state` | List of matching files to choose |
| `672` | Sends file with number 672 in name |
| `1` | Sends file #1 from last search |
| `help` | Shows help message |
| `index` | Refreshes file list |

## 📁 File Structure

```
dad-file-bot/
├── bot.py              # Main bot logic
├── file_search.py      # File indexing & fuzzy search
├── wacli_wrapper.py    # WhatsApp CLI wrapper
├── config.yaml         # Configuration
├── requirements.txt    # Python dependencies
├── install.bat         # Windows installer
└── README.md           # This file
```

## 🛠️ Manual Installation

If the one-liner doesn't work:

```batch
# Install wacli
npm install -g wacli

# Install Python packages
pip install fuzzywuzzy python-Levenshtein watchdog pyyaml

# Clone/download the files
git clone https://github.com/TangledDaunT/dad-file-bot.git
cd dad-file-bot

# Then edit config.yaml and run bot.py
```

## 🔧 Troubleshooting

**"wacli not found"** - Install Node.js from https://nodejs.org/

**"No files found"** - Run `python bot.py index` to build the file index

**"Not authenticated"** - Run `wacli auth` and scan the QR code

## 📝 License

ISC - Use at your own responsibility.

Built with ❤️ for dad.
