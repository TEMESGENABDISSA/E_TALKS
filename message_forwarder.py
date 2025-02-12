from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError
import logging
from datetime import datetime
import json

class MessageForwarder:
    def __init__(self, private_channel_id: str):
        self.logger = logging.getLogger(__name__)
        self.private_channel_id = private_channel_id
        self.forwarded_messages = {}
        self.load_message_history()
        
    def load_message_history(self):
        """Load message forwarding history"""
        try:
            with open('data/forwarded_messages.json', 'r') as f:
                self.forwarded_messages = json.load(f)
        except FileNotFoundError:
            self.forwarded_messages = {}
            
    def save_message_history(self):
        """Save message forwarding history"""
        try:
            with open('data/forwarded_messages.json', 'w') as f:
                json.dump(self.forwarded_messages, f)
        except Exception as e:
            self.logger.error(f"Error saving message history: {e}")
            
    async def forward_message(self, 
                            update: Update, 
                            context: ContextTypes.DEFAULT_TYPE,
                            user_account_id: str) -> bool:
        """Forward message to private channel"""
        try:
            message = update.message
            user = update.effective_user
            
            # Create forwarding info
            forward_info = {
                'user_id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'timestamp': datetime.now().isoformat(),
                'user_account': user_account_id
            }
            
            # Forward the message
            forwarded = await message.forward(
                chat_id=self.private_channel_id,
                disable_notification=True
            )
            
            # Send user info
            await context.bot.send_message(
                chat_id=self.private_channel_id,
                text=self._format_user_info(forward_info),
                reply_to_message_id=forwarded.message_id,
                disable_notification=True
            )
            
            # Update history
            self.forwarded_messages[str(message.message_id)] = {
                'forwarded_id': forwarded.message_id,
                'info': forward_info
            }
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