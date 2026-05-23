#!/usr/bin/env python3
"""
Dad File Bot - Robust WhatsApp File Bot
Handles file search and delivery via WhatsApp for approved contacts
"""

import os
import sys
import time
import logging
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from file_search import FileIndexer, search_files, format_file_size
from wacli_wrapper import WacliWrapper, MessageMonitor


# ==================== SETUP ====================

def setup_logging(log_file: Path) -> logging.Logger:
    """Setup logging with absolute path - call this first!"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    handlers = [
        logging.FileHandler(log_file, encoding='utf-8', mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
    
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=handlers,
        force=True
    )
    
    return logging.getLogger(__name__)


@dataclass
class PendingSelection:
    """Track pending file selection with timestamp for cleanup"""
    files: List[dict]
    timestamp: datetime = field(default_factory=datetime.now)
    query: str = ""
    
    def is_expired(self, timeout_minutes: int = 10) -> bool:
        return datetime.now() - self.timestamp > timedelta(minutes=timeout_minutes)


class ConfigurationError(Exception):
    """Raised when configuration is invalid"""
    pass


class SafeConfig:
    """Safe configuration wrapper with defaults"""
    
    DEFAULTS = {
        'approved_sender': '',
        'scan_directory': 'E:\\\\',
        'file_extensions': ['.pdf', '.doc', '.docx'],
        'fuzzy_threshold': 60,
        'max_results': 10,
        'poll_interval': 5,
        'index_file': 'file_index.db',
        'log_file': 'dad_file_bot.log',
        'selection_timeout_minutes': 10,
        'max_file_size_mb': 64,
        'max_summary_files': 100,
    }
    
    def __init__(self, config_path: str):
        self.raw_config = self._load_config(config_path)
        self._validate_required()
    
    def _load_config(self, config_path: str) -> dict:
        paths_to_try = [
            Path(config_path),
            Path(__file__).parent / config_path,
            Path(__file__).parent / 'config.yaml',
        ]
        
        for path in paths_to_try:
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        return yaml.safe_load(f) or {}
                except Exception as e:
                    raise ConfigurationError(f"Failed to load config from {path}: {e}")
        
        raise ConfigurationError(
            f"Config file not found. Tried: {[str(p) for p in paths_to_try]}"
        )
    
    def _validate_required(self):
        approved = self.get('approved_sender')
        if not approved:
            raise ConfigurationError(
                "approved_sender is required in config.yaml. "
                "Add: approved_sender: '+919876543210'"
            )
    
    def get(self, key: str) -> Any:
        return self.raw_config.get(key, self.DEFAULTS.get(key))
    
    def __getitem__(self, key: str) -> Any:
        return self.get(key)


# ==================== BOT ====================

class DadFileBot:
    """Main bot class - receives requests and sends files"""
    
    MAX_FILE_SIZE_MB = 64
    MAX_SUMMARY_FILES = 100
    SELECTION_TIMEOUT_MINUTES = 10
    MAX_RETRIES = 3
    RETRY_DELAY = 5
    
    def __init__(self, config_path: str = "config.yaml"):
        self.working_dir = Path(__file__).parent.absolute()
        
        # Logging FIRST
        log_path = self.working_dir / 'dad_file_bot.log'
        self.logger = setup_logging(log_path)
        self.logger.info("Starting Dad File Bot...")
        
        try:
            self.config = SafeConfig(config_path)
        except ConfigurationError as e:
            self.logger.error(f"Configuration error: {e}")
            print(f"\n❌ Configuration Error: {e}\n")
            sys.exit(1)
        
        # Components
        db_path = self.working_dir / self.config.get('index_file')
        scan_dir = self.config.get('scan_directory')
        scan_path = Path(scan_dir)
        
        if not scan_path.exists():
            self.logger.error(f"Scan directory does not exist: {scan_dir}")
            print(f"\n❌ Error: Directory '{scan_dir}' not found!")
            sys.exit(1)
        
        self.indexer = FileIndexer(
            db_path=str(db_path),
            scan_directory=str(scan_path),
            extensions=self.config.get('file_extensions')
        )
        
        self.wacli = WacliWrapper()
        self.monitor = MessageMonitor(
            wacli=self.wacli,
            approved_sender=self.config.get('approved_sender'),
            poll_interval=self.config.get('poll_interval')
        )
        
        self.pending_selections: Dict[str, PendingSelection] = {}
        self.logger.info("Dad File Bot initialized successfully")
    
    def build_file_index(self) -> int:
        """Build/refresh file index"""
        self.logger.info(f"Building index for {self.config.get('scan_directory')}...")
        try:
            count = self.indexer.build_index()
            self.logger.info(f"Indexed {count} files")
            return count
        except Exception as e:
            self.logger.error(f"Failed to build index: {e}", exc_info=True)
            raise
    
    def handle_message(self, sender: str, message_text: str) -> bool:
        """Process incoming message"""
        self.logger.info(f"Processing message from {sender}")
        
        message_text = message_text.strip()
        message_lower = message_text.lower()
        
        self._cleanup_expired_selections()
        
        # Check for selection first (don't lose state on typo!)
        if sender in self.pending_selections:
            selection_result = self._handle_possible_selection(sender, message_text)
            if selection_result is not None:
                return selection_result
        
        # Commands (case-insensitive)
        if message_lower in ['hi', 'hello', 'hey', 'start']:
            return self._send_help(sender)
        
        if message_lower in ['help', '?']:
            return self._send_help(sender)
        
        if message_lower in ['index', 'reindex', 'refresh', 'update']:
            return self._handle_reindex(sender)
        
        if message_lower in ['list', 'show all', 'files']:
            return self._send_file_list_summary(sender)
        
        if message_lower in ['cancel', 'stop', 'clear']:
            return self._handle_cancel(sender)
        
        return self._search_and_send(sender, message_text)
    
    def _handle_possible_selection(self, sender: str, message_text: str) -> Optional[bool]:
        """Try to handle as selection. Returns bool if handled, None if not"""
        pending = self.pending_selections.get(sender)
        if not pending:
            return None
        
        try:
            selection = int(message_text.strip())
        except ValueError:
            # NOT A NUMBER - don't delete state!
            return None
        
        files = pending.files
        
        if selection < 1 or selection > len(files):
            # Invalid number - KEEP state, let them retry
            return self.wacli.send_text(
                sender,
                f"❌ Enter a number between 1 and {len(files)}.\n"
                f"Or send 'cancel' to start over."
            )
        
        # Valid - send and clear
        selected = files[selection - 1]
        del self.pending_selections[sender]
        return self._send_file(sender, selected)
    
    def _handle_reindex(self, sender: str) -> bool:
        try:
            count = self.build_file_index()
            return self.wacli.send_text(sender, f"📁 Index refreshed! Found {count} files.")
        except Exception as e:
            self.logger.error(f"Reindex failed: {e}")
            return self.wacli.send_text(sender, "❌ Failed to refresh index.")
    
    def _handle_cancel(self, sender: str) -> bool:
        if sender in self.pending_selections:
            del self.pending_selections[sender]
        return self.wacli.send_text(sender, "✅ Selection cleared. Send a new search.")
    
    def _cleanup_expired_selections(self):
        timeout = self.config.get('selection_timeout_minutes', self.SELECTION_TIMEOUT_MINUTES)
        expired = [
            sender for sender, pending in self.pending_selections.items()
            if pending.is_expired(timeout)
        ]
        for sender in expired:
            self.logger.info(f"Cleaning up expired selection for {sender}")
            del self.pending_selections[sender]
    
    def _search_and_send(self, sender: str, query: str) -> bool:
        try:
            threshold = self.config.get('fuzzy_threshold')
            max_results = self.config.get('max_results')
            
            results = search_files(query, self.indexer, threshold=threshold, max_results=max_results)
            
            if not results:
                return self.wacli.send_text(
                    sender, 
                    f"❌ No files found for '{query}'.\n\n"
                    f"Try: different keywords, file number (e.g., '672'), or 'list'"
                )
            
            if len(results) == 1:
                return self._send_file(sender, results[0])
            
            # Store state for selection
            self.pending_selections[sender] = PendingSelection(files=results, query=query)
            return self._send_selection_list(sender, results, query)
            
        except Exception as e:
            self.logger.error(f"Search failed: {e}", exc_info=True)
            return self.wacli.send_text(sender, "❌ Search failed. Please try again.")
    
    def _send_selection_list(self, sender: str, results: list, query: str) -> bool:
        response = f"📄 Found {len(results)} files for '{query}':\n\n"
        
        for i, file in enumerate(results, 1):
            size = format_file_size(file['size_bytes'])
            score = file.get('score', 100)
            filename = file['filename']
            display_name = filename if len(filename) <= 50 else filename[:47] + "..."
            
            response += f"{i}. {display_name}\n"
            response += f"   💾 {size}"
            if score < 100:
                response += f" | Match: {score}%"
            response += "\n\n"
        
        response += f"Reply with 1-{len(results)} to get a file, or 'cancel' to search again."
        return self.wacli.send_text(sender, response)
    
    def _send_file(self, sender: str, file_info: dict) -> bool:
        try:
            filepath = Path(file_info['filepath'])
            filename = file_info['filename']
            
            if not filepath.exists():
                return self.wacli.send_text(sender, "❌ File not found. Send 'index' to refresh.")
            
            if not os.access(filepath, os.R_OK):
                return self.wacli.send_text(sender, "❌ Cannot read file (no permission).")
            
            size_mb = file_info['size_bytes'] / (1024 * 1024)
            max_mb = self.config.get('max_file_size_mb', self.MAX_FILE_SIZE_MB)
            
            if size_mb > max_mb:
                return self.wacli.send_text(sender, f"❌ File too large ({size_mb:.1f} MB). Limit: {max_mb} MB")
            
            self.logger.info(f"Sending: {filepath.name}")
            
            success = self.wacli.send_file(sender, str(filepath), caption=f"📄 {filename}")
            
            if success:
                size = format_file_size(file_info['size_bytes'])
                self.wacli.send_text(sender, f"✅ Sent: {filename} ({size})")
            else:
                self.wacli.send_text(sender, "❌ Failed to send file. Try again.")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to send file: {e}", exc_info=True)
            return self.wacli.send_text(sender, "❌ Error sending file.")
    
    def _send_help(self, sender: str) -> bool:
        help_text = """👋 Hello! I'm your file assistant.

Send me:
• Keywords: "mayawati vs state"
• File number: "672"
• list - show file summary
• index - refresh file list
• cancel - clear selection

I'll find and send your files! 📁"""
        return self.wacli.send_text(sender, help_text)
    
    def _send_file_list_summary(self, sender: str) -> bool:
        try:
            max_summary = self.config.get('max_summary_files', self.MAX_SUMMARY_FILES)
            all_files = self.indexer.get_all_files()
            files = all_files[:max_summary]
            total_count = len(all_files)
            
            if not files:
                return self.wacli.send_text(sender, "📁 No files indexed. Send 'index' to scan.")
            
            total_size = sum(f['size_bytes'] for f in files)
            
            ext_counts = {}
            for f in files:
                ext = Path(f['filename']).suffix.upper() or 'NO EXT'
                ext_counts[ext] = ext_counts.get(ext, 0) + 1
            
            response = f"📊 File Summary:\n\n"
            response += f"Total: {total_count} files\n"
            response += f"Size: {format_file_size(total_size)}\n\n"
            response += "By type:\n"
            for ext, count in sorted(ext_counts.items()):
                response += f"  {ext}: {count}\n"
            
            return self.wacli.send_text(sender, response)
            
        except Exception as e:
            self.logger.error(f"Summary failed: {e}", exc_info=True)
            return self.wacli.send_text(sender, "❌ Error generating summary.")
    
    def run(self):
        """Main bot loop with error handling"""
        self.logger.info("Starting bot...")
        
        # Check authentication
        if not self.wacli.check_auth():
            self.logger.error("Not authenticated with WhatsApp!")
            print("\n" + "="*50)
            print("⚠️  NOT AUTHENTICATED")
            print("="*50)
            print("\nRun: wacli auth")
            print("Scan QR code with your phone")
            print("="*50 + "\n")
            return
        
        self.logger.info(f"Authenticated! Approved sender: {self.config.get('approved_sender')}")
        
        # Build initial index
        try:
            count = self.build_file_index()
            self.wacli.send_text(
                self.config.get('approved_sender'),
                f"🤖 Bot started!\n📁 {count} files indexed.\nSend 'help' for help."
            )
        except Exception as e:
            self.logger.error(f"Initial index failed: {e}")
        
        poll_interval = self.config.get('poll_interval', 5)
        consecutive_errors = 0
        max_consecutive_errors = 10
        
        try:
            while True:
                try:
                    # Get new messages
                    messages = self.monitor.get_new_messages()
                    consecutive_errors = 0  # Reset on success
                    
                    for msg in messages:
                        try:
                            content = msg.get('content', '')
                            sender = msg.get('sender', '')
                            
                            if sender and content:
                                self.handle_message(sender, content)
                        except Exception as e:
                            self.logger.error(f"Error handling message: {e}", exc_info=True)
                            # Don't crash the bot for a single bad message
                    
                except Exception as e:
                    consecutive_errors += 1
                    self.logger.error(f"Error in poll loop: {e}")
                    
                    if consecutive_errors >= max_consecutive_errors:
                        self.logger.critical(f"Too many consecutive errors ({consecutive_errors}). Shutting down.")
                        break
                    
                    # Exponential backoff
                    sleep_time = min(poll_interval * (2 ** consecutive_errors), 300)  # Max 5 min
                    self.logger.info(f"Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                    continue
                
                time.sleep(poll_interval)
                
        except KeyboardInterrupt:
            self.logger.info("Bot stopped by user")
            try:
                self.wacli.send_text(
                    self.config.get('approved_sender'),
                    "🤖 Bot shutting down. Goodbye!"
                )
            except:
                pass
        except Exception as e:
            self.logger.error(f"Bot error: {e}", exc_info=True)
            raise
    
    def close(self):
        """Cleanup resources"""
        self.logger.info("Shutting down...")
        self.indexer.close()


def main():
    """Entry point"""
    # Check if index command
    if len(sys.argv) > 1 and sys.argv[1] == 'index':
        bot = DadFileBot()
        try:
            bot.build_file_index()
        finally:
            bot.close()
        return
    
    # Run bot
    bot = DadFileBot()
    try:
        bot.run()
    except KeyboardInterrupt:
        pass
    finally:
        bot.close()


if __name__ == "__main__":
    main()
