from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime, timedelta
import logging
from typing import Dict, Any
import json
import config

class SubscriptionControl:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.subscriptions: Dict[str, Dict[str, Any]] = {}
        self.device_locks: Dict[str, bool] = {}
        self.load_data()
        
    def load_data(self):
        """Load subscription data"""
        try:
            with open('data/subscription_control.json', 'r') as f:
                data = json.load(f)
                self.subscriptions = data.get('subscriptions', {})
                self.device_locks = data.get('device_locks', {})
        except FileNotFoundError:
            self.save_data()
            
    def save_data(self):
        """Save subscription data"""
        try:
            with open('data/subscription_control.json', 'w') as f:
                json.dump({
                    'subscriptions': self.subscriptions,
                    'device_locks': self.device_locks
                }, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error saving data: {e}")
            
    async def handle_link_click(self, 
                              update: Update, 
                              context: ContextTypes.DEFAULT_TYPE):
        """Handle channel link clicks"""
        user_id = str(update.effective_user.id)
        
        # Lock device
        self.device_locks[user_id] = True
        self.save_data()
        
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
                    "Verify Subscriptions ✅",
                    callback_data="verify_subs"
                )
            ]
        ]
        
        await update.message.reply_text(
            "🔒 Device Access Limited\n\n"
            "To continue using your device:\n"
            "1. Join our Telegram channel\n"
            "2. Subscribe to YouTube channel\n"
            "3. Verify your subscriptions\n\n"
            "Your device access will be restored after verification.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    async def handle_unsubscribe_attempt(self, 
                                       update: Update, 
                                       context: ContextTypes.DEFAULT_TYPE):
        """Handle unsubscribe attempts"""
        user_id = str(update.effective_user.id)
        
        if user_id not in self.subscriptions:
            self.subscriptions[user_id] = {
                'join_date': datetime.now().isoformat(),
                'can_leave': False
            }
            self.save_data()
            
        join_date = datetime.fromisoformat(
            self.subscriptions[user_id]['join_date']
        )
        months_subscribed = (datetime.now() - join_date).days / 30
        
        if months_subscribed < 6:
            await update.message.reply_text(
                "⚠️ Unsubscribe Restricted\n\n"
                f"You must remain subscribed for 6 months.\n"
                f"Time remaining: {int(6 - months_subscribed)} months\n\n"
                "Contact admin for special requests."
            )
            return False
            
        # Request admin approval
        await self.request_leave_approval(update, context)
        return False