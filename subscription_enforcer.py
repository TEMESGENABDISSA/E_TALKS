from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
from typing import Dict, Any
import json
import aiohttp
import config

class SubscriptionEnforcer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.subscriptions: Dict[str, Dict[str, Any]] = {}
        self.load_subscriptions()
        
    def load_subscriptions(self):
        """Load subscription data from file"""
        try:
            with open('data/subscriptions.json', 'r') as f:
                self.subscriptions = json.load(f)
        except FileNotFoundError:
            self.save_subscriptions()
            
    def save_subscriptions(self):
        """Save subscription data to file"""
        try:
            with open('data/subscriptions.json', 'w') as f:
                json.dump(self.subscriptions, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error saving subscriptions: {e}")
            
    async def check_subscriptions(self, 
                                update: Update, 
                                context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check if user has required subscriptions"""
        user_id = str(update.effective_user.id)
        
        try:
            # Check Telegram channel subscription
            is_telegram_member = await self.check_telegram_subscription(
                context, 
                update.effective_user.id
            )
            
            # Check YouTube subscription
            is_youtube_subscriber = await self.check_youtube_subscription(user_id)
            
            if not (is_telegram_member and is_youtube_subscriber):
                await self.send_subscription_prompt(update, context)
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking subscriptions: {e}")
            return False
            
    async def check_telegram_subscription(self, 
                                        context: ContextTypes.DEFAULT_TYPE,
                                        user_id: int) -> bool:
        """Check Telegram channel subscription"""
        try:
            for channel_id in config.REQUIRED_CHANNELS:
                member = await context.bot.get_chat_member(
                    chat_id=channel_id,
                    user_id=user_id
                )
                if member.status not in ['member', 'administrator', 'creator']:
                    return False
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking Telegram subscription: {e}")
            return False
            
    async def check_youtube_subscription(self, user_id: str) -> bool:
        """Check YouTube channel subscription"""
        # Implement YouTube API check here
        # This is a placeholder
        return True
        
    async def send_subscription_prompt(self, 
                                     update: Update, 
                                     context: ContextTypes.DEFAULT_TYPE):
        """Send subscription requirement prompt"""
        keyboard = [
            [
                InlineKeyboardButton(
                    "Join Telegram Channel 📢",
                    url=config.CHANNEL_INFO[config.REQUIRED_CHANNELS[0]]['invite_link']
                )
            ],
            [
                InlineKeyboardButton(
                    "Subscribe YouTube 📺",
                    url=config.YOUTUBE_CHANNEL_URL
                )
            ],
            [
                InlineKeyboardButton(
                    "Check Subscriptions ✅",
                    callback_data="check_subs"
                )
            ]
        ]
        
        await update.message.reply_text(
            "⚠️ Subscription Required\n\n"
            "To access this content, please:\n"
            "1. Join our Telegram channel\n"
            "2. Subscribe to our YouTube channel\n\n"
            "Click the buttons below:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        ) 