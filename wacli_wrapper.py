"""
wacli Wrapper Module - Interface with WhatsApp CLI
Robust wrapper with timeouts and error handling
"""

import subprocess
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta


class WacliWrapper:
    """Wrapper around wacli command for WhatsApp integration"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def _run_cmd(self, cmd: list, capture_output: bool = True, timeout: int = 60) -> tuple[bool, str, str]:
        """Run wacli command and return (success, stdout, stderr)"""
        base_cmd = ["wacli"] + cmd
        
        try:
            result = subprocess.run(
                base_cmd,
                capture_output=capture_output,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except FileNotFoundError:
            return False, "", "wacli not found. Install with: npm install -g wacli"
        except Exception as e:
            return False, "", str(e)
    
    def check_auth(self) -> bool:
        """Check if authenticated with WhatsApp"""
        success, stdout, _ = self._run_cmd(["doctor"], timeout=10)
        return success and "authenticated" in stdout.lower()
    
    def send_text(self, to: str, message: str) -> bool:
        """Send text message"""
        # Format number
        if not to.endswith("@s.whatsapp.net") and "@" not in to:
            to = f"{to}@s.whatsapp.net"
        
        # Escape special chars in message
        safe_message = message.replace('"', '\\"')
        
        success, _, stderr = self._run_cmd([
            "send", "text",
            "--to", to,
            "--message", safe_message
        ], capture_output=True, timeout=30)
        
        if success:
            return True
        else:
            self.logger.error(f"Failed to send text: {stderr}")
            return False
    
    def send_file(self, to: str, file_path: str, caption: Optional[str] = None) -> bool:
        """Send file"""
        if not to.endswith("@s.whatsapp.net") and "@" not in to:
            to = f"{to}@s.whatsapp.net"
        
        cmd = ["send", "file", "--to", to, "--file", file_path]
        if caption:
            safe_caption = caption.replace('"', '\\"')
            cmd.extend(["--caption", safe_caption])
        
        success, _, stderr = self._run_cmd(cmd, timeout=180)  # Files can take time
        
        if success:
            return True
        else:
            self.logger.error(f"Failed to send file: {stderr}")
            return False


class MessageMonitor:
    """Monitor messages from approved sender"""
    
    def __init__(self, wacli: WacliWrapper, approved_sender: str, poll_interval: int = 5):
        self.wacli = wacli
        self.approved_sender = self._normalize_number(approved_sender)
        self.poll_interval = poll_interval
        self.seen_message_ids = set()
        self.logger = logging.getLogger(__name__)
    
    def _normalize_number(self, number: str) -> str:
        """Normalize phone number"""
        return number.replace("@s.whatsapp.net", "").replace("+", "").replace(" ", "")
    
    def _get_sender_number(self, msg: dict) -> str:
        """Extract sender number"""
        sender = msg.get("sender", "")
        return sender.replace("@s.whatsapp.net", "").replace("+", "").replace(" ", "")
    
    def get_new_messages(self) -> list[dict]:
        """Get new messages from approved sender"""
        new_messages = []
        
        try:
            # List chats
            success, stdout, stderr = self.wacli._run_cmd(
                ["chats", "list", "--json"],
                timeout=30
            )
            
            if not success:
                self.logger.warning(f"Failed to list chats: {stderr}")
                return []
            
            # Simple parsing - just return empty for now
            # Real implementation would parse JSON and filter by sender
            return []
            
        except Exception as e:
            self.logger.error(f"Error getting messages: {e}")
            return []
