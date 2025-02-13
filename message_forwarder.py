from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError
import logging
from datetime import datetime
import json
import os
from typing import Dict, List
from pathlib import Path

class MessageForwarder:
    def __init__(self, channel_id: str):
        self.channel_id = channel_id
        self.data_dir = Path("data")
        self.history_file = self.data_dir / f"forwarded_messages_{channel_id}.json"
        self.forwarded_messages: Dict[str, List[int]] = {}
        self.logger = logging.getLogger(__name__)
        
        # Ensure data directory and files exist
        self.ensure_data_directory()
        self.load_message_history()
        
    def load_message_history(self):
        """Load message history from JSON file, create if doesn't exist"""
        try:
            if self.history_file.exists() and self.history_file.stat().st_size > 0:
                try:
                    with open(self.history_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if content.strip():  # Check if file is not just whitespace
                            self.forwarded_messages = json.loads(content)
                        else:
                            self.forwarded_messages = {}
                except json.JSONDecodeError as e:
                    self.logger.error(f"Corrupted JSON file, creating backup and starting fresh: {e}")
                    # Create backup of corrupted file
                    backup_file = self.history_file.with_suffix('.json.bak')
                    self.history_file.rename(backup_file)
                    self.forwarded_messages = {}
            else:
                self.forwarded_messages = {}
            
            # Save to ensure proper format
            self.save_message_history()
            
        except Exception as e:
            self.logger.error(f"Unexpected error loading message history: {e}")
            self.forwarded_messages = {}
            
    def save_message_history(self):
        """Save message history to JSON file"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.forwarded_messages, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Error saving message history: {e}")
            
    async def forward_message(self, 
                            update: Update, 
                            context: ContextTypes.DEFAULT_TYPE,
                            user_account_id: str) -> bool:
        """Forward message to private channel"""
        try:
            if not update.message:
                self.logger.warning("No message to forward")
                return False
                
            if not update.effective_user:
                self.logger.warning("No user information available")
                return False
                
            message = update.message
            user = update.effective_user
            
            # Create forwarding info
            forward_info = {
                'user_id': user.id,
                'username': user.username or "No username",
                'first_name': user.first_name or "No name",
                'timestamp': datetime.now().isoformat(),
                'user_account': user_account_id
            }
            
            # Forward the message
            try:
                forwarded = await message.forward(
                    chat_id=self.channel_id,
                    disable_notification=True
                )
            except TelegramError as e:
                self.logger.error(f"Failed to forward message: {e}")
                return False
            
            # Send user info
            try:
                await context.bot.send_message(
                    chat_id=self.channel_id,
                    text=self._format_user_info(forward_info),
                    reply_to_message_id=forwarded.message_id,
                    disable_notification=True
                )
            except TelegramError as e:
                self.logger.error(f"Failed to send user info: {e}")
                # Continue since message was already forwarded
            
            # Update history
            user_id = str(user.id)
            if user_id not in self.forwarded_messages:
                self.forwarded_messages[user_id] = []
            
            self.forwarded_messages[user_id].append(forwarded.message_id)
            self.save_message_history()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Forward error: {e}")
            return False
            
    def _format_user_info(self, info: dict) -> str:
        """Format user info for forwarded message"""
        return (
            f"📬 Forwarded Message Info:\n"
            f"From: {info['first_name']} (@{info['username']})\n"
            f"User ID: {info['user_id']}\n"
            f"Account: {info['user_account']}\n"
            f"Time: {info['timestamp']}"
        )

    def get_user_messages(self, user_id: int) -> List[int]:
        """Get list of message IDs forwarded by a user"""
        return self.forwarded_messages.get(str(user_id), [])

    def ensure_data_directory(self):
        """Ensure data directory and files exist"""
        try:
            # Create data directory if it doesn't exist
            self.data_dir.mkdir(parents=True, exist_ok=True)
            
            # Create empty JSON file if it doesn't exist
            if not self.history_file.exists():
                with open(self.history_file, 'w', encoding='utf-8') as f:
                    json.dump({}, f)
                
        except Exception as e:
            self.logger.error(f"Error ensuring data directory: {e}")

    def recover_history(self):
        """Attempt to recover message history from backup"""
        try:
            backup_file = self.history_file.with_suffix('.json.bak')
            if backup_file.exists():
                with open(backup_file, 'r', encoding='utf-8') as f:
                    self.forwarded_messages = json.load(f)
                    self.save_message_history()
                    self.logger.info("Successfully recovered message history from backup")
                    return True
        except Exception as e:
            self.logger.error(f"Failed to recover message history: {e}")
        return False 