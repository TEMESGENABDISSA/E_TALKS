from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError
import logging
from typing import Optional
import config

class ChannelManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    async def check_channel_membership(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check if user is a member of required channel"""
        try:
            user_id = update.effective_user.id
            
            # Skip check for admins
            if str(user_id) in config.ADMIN_IDS:
                return True
                
            # Check membership for each required channel
            for channel_id in config.REQUIRED_CHANNELS:
                try:
                    member = await context.bot.get_chat_member(
                        chat_id=channel_id,
                        user_id=user_id
                    )
                    if member.status not in ['member', 'administrator', 'creator']:
                        await self.send_join_prompt(update, context, channel_id)
                        return False
                except TelegramError as e:
                    self.logger.error(f"Error checking membership: {e}")
                    continue
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Membership check error: {e}")
            return False
            
    async def send_join_prompt(self, 
                             update: Update, 
                             context: ContextTypes.DEFAULT_TYPE,
                             channel_id: str):
        """Send channel join prompt to user"""
        try:
            channel_info = config.CHANNEL_INFO.get(channel_id, {})
            keyboard = [
                [
                    InlineKeyboardButton(
                        "Join Channel 📢", 
                        url=channel_info.get('invite_link', '')
                    ),
                    InlineKeyboardButton(
                        "Check Membership ✅", 
                        callback_data=f"check_member_{channel_id}"
                    )
                ]
            ]
            
            await update.message.reply_text(
                config.MESSAGES['JOIN_REQUIRED'].format(
                    channel_name=channel_info.get('name', 'our channel')
                ),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            self.logger.error(f"Error sending join prompt: {e}") 