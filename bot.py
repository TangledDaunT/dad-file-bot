"""
Dad File Bot - Main Bot Logic
WhatsApp file retrieval bot for your dad
"""

import os
import sys
import time
import logging
import yaml
from pathlib import Path
from datetime import datetime

from file_search import FileIndexer, search_files, format_file_size
from wacli_wrapper import WacliWrapper, MessageMonitor


class DadFileBot:
    """Main bot class - receives requests and sends files"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Ensure paths are absolute
        self.working_dir = Path(__file__).parent.absolute()
        self.db_path = self.working_dir / self.config.get('index_file', 'file_index.db')
        self.log_file = self.working_dir / self.config.get('log_file', 'dad_file_bot.log')
        
        # Initialize components
        self.indexer = FileIndexer(
            db_path=str(self.db_path),
            scan_directory=self.config['scan_directory'],
            extensions=self.config['file_extensions']
        )
        
        self.wacli = WacliWrapper()
        self.monitor = MessageMonitor(
            wacli=self.wacli,
            approved_sender=self.config['approved_sender'],
            poll_interval=self.config.get('poll_interval', 5)
        )
        
        self.pending_selections = {}  # Store pending file selections by sender
        
        self.logger.info("Dad File Bot initialized")
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file"""
        if not os.path.exists(config_path):
            # Look in script directory
            script_dir = Path(__file__).parent
            config_path = script_dir / config_path
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler('dad_file_bot.log', encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def build_file_index(self) -> int:
        """Build/refresh file index"""
        self.logger.info(f"Building index for {self.config['scan_directory']}...")
        count = self.indexer.build_index()
        self.logger.info(f"Indexed {count} files")
        return count
    
    def handle_message(self, sender: str, message_text: str) -> bool:
        """
        Process incoming message and respond
        Returns True if handled successfully
        """
        message_text = message_text.strip()
        self.logger.info(f"Processing message from {sender}: {message_text}")
        
        # Check if this is a selection response (number like "1", "2", etc.)
        if sender in self.pending_selections:
            try:
                selection = int(message_text)
                result = self._handle_selection(sender, selection)
                del self.pending_selections[sender]
                return result
            except ValueError:
                # Not a number, clear pending selection
                del self.pending_selections[sender]
        
        # Check for special commands
        if message_text.lower() in ['hi', 'hello', 'help']:
            return self._send_help(sender)
        
        if message_text.lower() in ['index', 'reindex', 'refresh']:
            count = self.build_file_index()
            return self.wacli.send_text(sender, f"📁 File index refreshed! Found {count} files.")
        
        if message_text.lower() in ['list', 'show all']:
            return self._send_file_list_summary(sender)
        
        # Search for files
        return self._search_and_send(sender, message_text)
    
    def _handle_selection(self, sender: str, selection: int) -> bool:
        """Handle file selection from numbered list"""
        files = self.pending_selections.get(sender, [])
        
        if not files or selection < 1 or selection > len(files):
            return self.wacli.send_text(sender, "❌ Invalid selection. Please try searching again.")
        
        selected = files[selection - 1]
        return self._send_file(sender, selected)
    
    def _search_and_send(self, sender: str, query: str) -> bool:
        """Search for files and send results or file"""
        threshold = self.config.get('fuzzy_threshold', 60)
        max_results = self.config.get('max_results', 10)
        
        results = search_files(query, self.indexer, threshold=threshold, max_results=max_results)
        
        if not results:
            return self.wacli.send_text(
                sender, 
                f"❌ No files found for '{query}'.\n\nTry:\n• Searching with different keywords\n• File number (e.g., '672')\n• Type 'list' to see all files"
            )
        
        if len(results) == 1:
            # Single match - send directly
            return self._send_file(sender, results[0])
        
        # Multiple matches - send options
        self.pending_selections[sender] = results
        
        response = f"📄 Multiple files found for '{query}':\n\n"
        for i, file in enumerate(results, 1):
            size = format_file_size(file['size_bytes'])
            score = file.get('score', 100)
            response += f"{i}. {file['filename']}\n   💾 {size}"
            if score < 100:
                response += f" | Match: {score}%"
            response += "\n\n"
        
        response += "Reply with a number (1, 2, 3...) to get that file."
        
        return self.wacli.send_text(sender, response)
    
    def _send_file(self, sender: str, file_info: dict) -> bool:
        """Send a file to the sender"""
        filepath = file_info['filepath']
        filename = file_info['filename']
        
        if not os.path.exists(filepath):
            return self.wacli.send_text(sender, "❌ File not found on disk. Please reindex.")
        
        # Check file size (WhatsApp has ~100MB limit)
        size_mb = file_info['size_bytes'] / (1024 * 1024)
        if size_mb > 100:
            return self.wacli.send_text(
                sender,
                f"❌ File too large ({size_mb:.1f} MB). WhatsApp limit is 100 MB."
            )
        
        self.logger.info(f"Sending file: {filepath} to {sender}")
        
        # Send file with caption
        caption = f"📄 {filename}"
        success = self.wacli.send_file(sender, filepath, caption=caption)
        
        if success:
            self.logger.info(f"File sent successfully: {filename}")
            # Also send a confirmation text
            size = format_file_size(file_info['size_bytes'])
            self.wacli.send_text(sender, f"✅ Sent: {filename} ({size})")
        else:
            self.wacli.send_text(sender, "❌ Failed to send file. Please try again.")
        
        return success
    
    def _send_help(self, sender: str) -> bool:
        """Send help message"""
        help_text = """👋 Hello! I'm your file assistant.

Send me:
• file number (e.g., "672")
• file name or keywords (e.g., "mayawati vs state")
• "list" - to see all files
• "index" - to refresh file list

I'll find and send your files! 📁"""
        return self.wacli.send_text(sender, help_text)
    
    def _send_file_list_summary(self, sender: str) -> bool:
        """Send summary of available files"""
        files = self.indexer.get_all_files()
        
        total_size = sum(f['size_bytes'] for f in files)
        total_count = len(files)
        
        # Group by extension
        ext_counts = {}
        for f in files:
            ext = Path(f['filename']).suffix.upper()
            ext_counts[ext] = ext_counts.get(ext, 0) + 1
        
        response = f"📊 File Index Summary:\n\n"
        response += f"Total files: {total_count}\n"
        response += f"Total size: {format_file_size(total_size)}\n\n"
        response += "By type:\n"
        for ext, count in sorted(ext_counts.items()):
            response += f"  {ext}: {count} files\n"
        
        response += "\nTo search, send file number or keywords."
        
        return self.wacli.send_text(sender, response)
    
    def run(self):
        """Main bot loop"""
        self.logger.info("Starting Dad File Bot...")
        
        # Check authentication
        if not self.wacli.check_auth():
            self.logger.error("Not authenticated with WhatsApp!")
            print("\n" + "="*50)
            print("⚠️  NOT AUTHENTICATED")
            print("="*50)
            print("\nPlease run:")
            print("  wacli auth")
            print("\nThen scan the QR code with your phone.")
            print("="*50 + "\n")
            return
        
        self.logger.info(f"Authenticated! Approved sender: {self.config['approved_sender']}")
        
        # Build initial index
        count = self.build_file_index()
        self.wacli.send_text(
            self.config['approved_sender'],
            f"🤖 Dad File Bot started!\n📁 Indexed {count} files.\n\nSend 'help' for instructions."
        )
        
        poll_interval = self.config.get('poll_interval', 5)
        
        try:
            while True:
                # Get new messages
                messages = self.monitor.get_new_messages()
                
                for msg in messages:
                    content = msg.get('content', '')
                    sender = msg.get('sender', '')
                    
                    # Only process if from approved sender
                    if sender and content:
                        self.handle_message(sender, content)
                
                time.sleep(poll_interval)
                
        except KeyboardInterrupt:
            self.logger.info("Bot stopped by user")
            self.wacli.send_text(
                self.config['approved_sender'],
                "🤖 Dad File Bot shutting down. Goodbye!"
            )
        except Exception as e:
            self.logger.error(f"Bot error: {e}", exc_info=True)
            raise
    
    def close(self):
        """Cleanup resources"""
        self.indexer.close()


def main():
    """Entry point"""
    # Check if index command
    if len(sys.argv) > 1 and sys.argv[1] == 'index':
        bot = DadFileBot()
        bot.build_file_index()
        bot.close()
        return
    
    # Run bot
    bot = DadFileBot()
    try:
        bot.run()
    finally:
        bot.close()


if __name__ == "__main__":
    main()
