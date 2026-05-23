"""
wacli Wrapper Module - Interface with WhatsApp CLI
"""

import subprocess
import json
import logging
from pathlib import Path
from typing import Optional
import time
import re


class WacliWrapper:
    """Wrapper around wacli command for WhatsApp integration"""
    
    def __init__(self, store_dir: Optional[str] = None):
        self.store_dir = store_dir
        self.logger = logging.getLogger(__name__)
    
    def _run_cmd(self, cmd: list, capture_output: bool = True) -> tuple[bool, str]:
        """Run wacli command and return success status + output"""
        base_cmd = ["wacli"]
        if self.store_dir:
            base_cmd.extend(["--store", self.store_dir])
        base_cmd.extend(cmd)
        
        try:
            result = subprocess.run(
                base_cmd,
                capture_output=capture_output,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                return True, result.stdout
            else:
                self.logger.error(f"wacli error: {result.stderr}")
                return False, result.stderr
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except FileNotFoundError:
            return False, "wacli not found. Please install wacli first."
        except Exception as e:
            return False, str(e)
    
    def check_auth(self) -> bool:
        """Check if authenticated with WhatsApp"""
        success, output = self._run_cmd(["doctor"])
        return success and "authenticated" in output.lower()
    
    def get_self_jid(self) -> Optional[str]:
        """Get own WhatsApp JID"""
        success, output = self._run_cmd(["doctor", "--json"])
        if success:
            try:
                data = json.loads(output)
                return data.get("jid")
            except json.JSONDecodeError:
                pass
        return None
    
    def send_text(self, to: str, message: str) -> bool:
        """Send text message to a number"""
        # Format number
        if not to.endswith("@s.whatsapp.net") and "@" not in to:
            to = f"{to}@s.whatsapp.net"
        
        success, output = self._run_cmd([
            "send", "text",
            "--to", to,
            "--message", message
        ], capture_output=False)
        
        if success:
            self.logger.info(f"Sent message to {to}")
        else:
            self.logger.error(f"Failed to send message: {output}")
        
        return success
    
    def send_file(self, to: str, file_path: str, caption: Optional[str] = None) -> bool:
        """Send file to a number"""
        # Format number
        if not to.endswith("@s.whatsapp.net") and "@" not in to:
            to = f"{to}@s.whatsapp.net"
        
        cmd = ["send", "file", "--to", to, "--file", file_path]
        if caption:
            cmd.extend(["--caption", caption])
        
        success, output = self._run_cmd(cmd, capture_output=False)
        
        if success:
            self.logger.info(f"Sent file {file_path} to {to}")
        else:
            self.logger.error(f"Failed to send file: {output}")
        
        return success
    
    def list_chats(self, limit: int = 50) -> list[dict]:
        """List recent chats"""
        success, output = self._run_cmd([
            "chats", "list",
            "--limit", str(limit),
            "--json"
        ])
        
        if success:
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                pass
        return []
    
    def get_messages(self, chat_jid: str, limit: int = 20) -> list[dict]:
        """Get messages from a chat"""
        success, output = self._run_cmd([
            "messages", "list",
            "--chat", chat_jid,
            "--limit", str(limit),
            "--json"
        ])
        
        if success:
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                pass
        return []
    
    def search_messages(self, query: str, limit: int = 20) -> list[dict]:
        """Search messages across all chats"""
        success, output = self._run_cmd([
            "messages", "search",
            query,
            "--limit", str(limit),
            "--json"
        ])
        
        if success:
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                pass
        return []


class MessageMonitor:
    """Monitor messages from approved sender"""
    
    def __init__(self, wacli: WacliWrapper, approved_sender: str, poll_interval: int = 5):
        self.wacli = wacli
        self.approved_sender = self._normalize_number(approved_sender)
        self.poll_interval = poll_interval
        self.seen_message_ids = set()
        self.logger = logging.getLogger(__name__)
    
    def _normalize_number(self, number: str) -> str:
        """Normalize phone number format"""
        # Remove common prefixes and suffixes
        number = number.replace("@s.whatsapp.net", "")
        number = number.replace("+", "")
        return number
    
    def _get_sender_number(self, msg: dict) -> str:
        """Extract sender number from message"""
        sender = msg.get("sender", "")
        # Handle both @s.whatsapp.net format and other formats
        return sender.replace("@s.whatsapp.net", "").replace("+", "")
    
    def get_new_messages(self) -> list[dict]:
        """Get new messages from approved sender"""
        new_messages = []
        
        # Search for recent messages from approved sender
        try:
            # Get all recent messages and filter
            # Note: wacli list --limit gets messages chronologically
            # We'll look across all messages
            chats = self.wacli.list_chats(limit=10)
            
            for chat in chats:
                chat_jid = chat.get("jid", "")
                sender_num = self._normalize_number(chat_jid)
                
                if sender_num == self.approved_sender:
                    # Get messages from this chat
                    messages = self.wacli.get_messages(chat_jid, limit=10)
                    
                    for msg in messages:
                        msg_id = msg.get("id") or f"{msg.get('sender')}:{msg.get('timestamp')}:{msg.get('content', '')}"
                        
                        if msg_id not in self.seen_message_ids:
                            self.seen_message_ids.add(msg_id)
                            # Only add if it's actually from the sender (not us)
                            if self._get_sender_number(msg) == self.approved_sender:
                                new_messages.append(msg)
        except Exception as e:
            self.logger.error(f"Error getting messages: {e}")
        
        # Keep seen IDs set manageable
        if len(self.seen_message_ids) > 1000:
            self.seen_message_ids = set(list(self.seen_message_ids)[-500:])
        
        return new_messages
    
    def sync_and_get_messages(self, since_seconds: int = 30) -> list[dict]:
        """
        Alternative: Use sync --follow approach
        This runs wacli sync and captures new messages
        """
        messages = []
        
        try:
            # Run sync with timeout to get recent messages
            cmd = ["wacli", "sync"]
            if self.wacli.store_dir:
                cmd.extend(["--store", self.wacli.store_dir])
            cmd.extend(["--timeout", str(since_seconds)])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=since_seconds + 10
            )
            
            # Parse JSON output if available
            if result.stdout:
                try:
                    for line in result.stdout.strip().split('\n'):
                        if line.strip():
                            data = json.loads(line)
                            # Check if message is from approved sender
                            sender = self._get_sender_number(data)
                            if sender == self.approved_sender:
                                messages.append(data)
                except json.JSONDecodeError:
                    pass
                    
        except subprocess.TimeoutExpired:
            pass
        except Exception as e:
            self.logger.error(f"Sync error: {e}")
        
        return messages
