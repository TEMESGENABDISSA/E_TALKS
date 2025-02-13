from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
import json
import os
from datetime import datetime
from typing import Dict, Any
import config

class ConsentManager:
    def __init__(self):
        self.user_consents: Dict[str, Any] = {}
        self.consents_file = "user_consents.json"
        self.logger = logging.getLogger(__name__)
        self.load_consents()
        
    def load_consents(self):
        """Load user consents from JSON file, create if doesn't exist"""
        try:
            if os.path.exists(self.consents_file) and os.path.getsize(self.consents_file) > 0:
                with open(self.consents_file, 'r', encoding='utf-8') as f:
                    self.user_consents = json.load(f)
            else:
                # Initialize empty consents and save
                self.user_consents = {}
                self.save_consents()
        except json.JSONDecodeError as e:
            self.logger.error(f"Error loading consents: {e}")
            # If file is corrupted, start fresh
            self.user_consents = {}
            self.save_consents()
        except Exception as e:
            self.logger.error(f"Unexpected error loading consents: {e}")
            self.user_consents = {}
            
    def save_consents(self):
        """Save user consents to JSON file"""
        try:
            with open(self.consents_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_consents, f, indent=4)
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

    def has_user_consented(self, user_id: int) -> bool:
        """Check if user has given consent"""
        return str(user_id) in self.user_consents

    def give_consent(self, user_id: int):
        """Record user's consent"""
        self.user_consents[str(user_id)] = {
            'consented': True,
            'timestamp': datetime.now().isoformat()
        }
        self.save_consents()

    def revoke_consent(self, user_id: int):
        """Revoke user's consent"""
        if str(user_id) in self.user_consents:
            del self.user_consents[str(user_id)]
            self.save_consents() 