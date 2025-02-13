from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
from typing import Dict, List, Set
import json
import aiohttp
import config

class ContentSharing:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.sharing_groups: Dict[str, Dict] = {}
        self.load_groups()
        
    def load_groups(self):
        """Load sharing groups from file"""
        try:
            with open('data/sharing_groups.json', 'r') as f:
                self.sharing_groups = json.load(f)
        except FileNotFoundError:
            self.save_groups()
            
    def save_groups(self):
        """Save sharing groups to file"""
        try:
            with open('data/sharing_groups.json', 'w') as f:
                json.dump(self.sharing_groups, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error saving groups: {e}")
            
    async def scan_groups(self, 
                         update: Update, 
                         context: ContextTypes.DEFAULT_TYPE):
        """Scan and categorize groups"""
        if str(update.effective_user.id) not in config.ADMIN_IDS:
            return
            
        status_message = await update.message.reply_text(
            "🔍 Scanning groups..."
        )
        
        try:
            # Categories for groups
            categories = {
                'ethiopia': [],
                'africa': [],
                'north_america': [],
                'europe': [],
                'asia': [],
                'other': []
            }
            
            # Scan groups (implement your group discovery logic)
            # This is a placeholder for group scanning
            discovered_groups = await self.discover_groups(context)
            
            for group in discovered_groups:
                category = await self.categorize_group(group)
                if category in categories:
                    categories[category].append(group)
                    
            # Save categorized groups
            self.sharing_groups = categories
            self.save_groups()
            
            # Send organized list to private channel
            await self.send_organized_list(context)
            
            await status_message.edit_text(
                "✅ Group scanning complete!\n"
                "Check private channel for the organized list."
            )
            
        except Exception as e:
            self.logger.error(f"Error scanning groups: {e}")
            await status_message.edit_text(
                f"❌ Error scanning groups: {str(e)}"
            )
            
    async def send_organized_list(self, context: ContextTypes.DEFAULT_TYPE):
        """Send organized group list to private channel"""
        try:
            message = "📋 Sharing-Enabled Groups\n\n"
            
            for category, groups in self.sharing_groups.items():
                message += f"\n🌍 {category.title()}\n"
                for group in groups:
                    message += f"• {group['title']} ({group['members']} members)\n"
                    
            keyboard = [
                [
                    InlineKeyboardButton(
                        "Select Groups ✅",
                        callback_data="select_sharing_groups"
                    )
                ]
            ]
            
            await context.bot.send_message(
                chat_id=config.PRIVATE_CHANNEL_ID,
                text=message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            self.logger.error(f"Error sending organized list: {e}")

CHANNEL_LINKS = {
    "main": "#",
    "backup": "#",
    "announcements": "#"
}

GROUP_LINKS = {
    "main": "#",
    "support": "#",
    "community": "#"
}

WELCOME_MESSAGE = """
Welcome to #'s Channel!
Join us for amazing content about #.
"""

ABOUT_MESSAGE = """
About ##:
Expert in #
Contact: #
"""

CHANNEL_INFO = {
    "name": "#",
    "username": "@#",
    "description": "Welcome to #",
    "links": {
        "main": "https://t.me/#",
        "chat": "https://t.me/#",
        "youtube": "https://youtube.com/#"
    }
} 