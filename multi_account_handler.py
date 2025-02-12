from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
from typing import Dict, Any
import json
import config

class MultiAccountHandler:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.account_states: Dict[str, Dict[str, Any]] = {}
        self.shared_channel_id = config.PRIVATE_CHANNEL_ID
        self.load_states()
        
    def load_states(self):
        """Load account states"""
        try:
            with open('data/account_states.json', 'r') as f:
                self.account_states = json.load(f)
        except FileNotFoundError:
            self.save_states()
            
    def save_states(self):
        """Save account states"""
        try:
            with open('data/account_states.json', 'w') as f:
                json.dump(self.account_states, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error saving states: {e}")
            
    async def forward_to_private_channel(self,
                                       update: Update,
                                       context: ContextTypes.DEFAULT_TYPE):
        """Forward message to private channel"""
        try:
            # Add account identifier
            account_id = context.bot.id
            header = f"From Bot Account: {account_id}\n"
            header += f"User: {update.effective_user.id}\n"
            header += "-------------------\n"
            
            # Forward message
            forwarded = await context.bot.forward_message(
                chat_id=self.shared_channel_id,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )
            
            # Add header as reply
            await context.bot.send_message(
                chat_id=self.shared_channel_id,
                text=header,
                reply_to_message_id=forwarded.message_id
            )
            
        except Exception as e:
            self.logger.error(f"Error forwarding message: {e}") 