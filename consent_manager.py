from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
import json
from datetime import datetime
from typing import Dict, Any
import config

class ConsentManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.user_consents: Dict[str, Dict[str, Any]] = {}
        self.load_consents()
        
    def load_consents(self):
        """Load saved user consents"""
        try:
            with open('data/user_consents.json', 'r') as f:
                self.user_consents = json.load(f)
        except FileNotFoundError:
            self.user_consents = {}
            
    def save_consents(self):
        """Save user consents"""
        try:
            with open('data/user_consents.json', 'w') as f:
                json.dump(self.user_consents, f)
        except Exception as e:
            self.logger.error(f"Error saving consents: {e}")
            
    async def request_consent(self, 
                            update: Update, 
                            context: ContextTypes.DEFAULT_TYPE,
                            consent_type: str) -> bool:
        """Request user consent for specific action"""
        user_id = str(update.effective_user.id)
        
        # Check if consent already given
        if self.has_consent(user_id, consent_type):
            return True
            
        consent_text = config.CONSENT_MESSAGES.get(consent_type, "")
        keyboard = [
            [
                InlineKeyboardButton("I Agree ✅", 
                                   callback_data=f"consent_{consent_type}_yes"),
                InlineKeyboardButton("I Decline ❌", 
                                   callback_data=f"consent_{consent_type}_no")
            ]
        ]
        
        await update.message.reply_text(
            consent_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return False
        
    def has_consent(self, user_id: str, consent_type: str) -> bool:
        """Check if user has given consent"""
        return (user_id in self.user_consents and
                consent_type in self.user_consents[user_id] and
                self.user_consents[user_id][consent_type].get('status') == 'granted')
                
    async def handle_consent_response(self, 
                                    update: Update, 
                                    context: ContextTypes.DEFAULT_TYPE):
        """Handle user's consent response"""
        query = update.callback_query
        user_id = str(query.from_user.id)
        _, consent_type, response = query.data.split('_')
        
        if user_id not in self.user_consents:
            self.user_consents[user_id] = {}
            
        self.user_consents[user_id][consent_type] = {
            'status': 'granted' if response == 'yes' else 'denied',
            'timestamp': datetime.now().isoformat(),
            'version': config.CONSENT_VERSION
        }
        
        self.save_consents()
        
        await query.edit_message_text(
            config.CONSENT_RESPONSES[response]
        )
        
        return response == 'yes' 