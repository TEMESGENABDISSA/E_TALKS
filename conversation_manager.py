from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime, timedelta
import logging
import json
import os
import threading
from typing import Dict, Any
import config

class ConversationManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.user_states: Dict[str, Any] = {}
        self.states_file = "user_states.json"
        self._lock = threading.Lock()  # Add thread safety
        self.load_states()
        
    def load_states(self):
        """Load user states from JSON file with proper error handling"""
        try:
            if os.path.exists(self.states_file) and os.path.getsize(self.states_file) > 0:
                with open(self.states_file, 'r', encoding='utf-8') as f:
                    self.user_states = json.load(f)
            else:
                self.user_states = {}
                self.save_states()
        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(f"Error loading states: {e}")
            self.user_states = {}
            self.save_states()
            
    def save_states(self):
        """Thread-safe save of user states"""
        with self._lock:
            try:
                with open(self.states_file, 'w', encoding='utf-8') as f:
                    json.dump(self.user_states, f, indent=4, ensure_ascii=False)
            except IOError as e:
                self.logger.error(f"Error saving states: {e}")
            
    async def handle_message(self, 
                           update: Update, 
                           context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages with state management"""
        user_id = str(update.effective_user.id)
        message_text = update.message.text
        
        # Initialize or get user state
        if user_id not in self.user_states:
            self.user_states[user_id] = {
                'message_count': 0,
                'last_message_time': None,
                'triggers_used': [],
                'first_message_responded': False
            }
            
        # Update state
        self.user_states[user_id]['message_count'] += 1
        self.user_states[user_id]['last_message_time'] = datetime.now().isoformat()
        
        # Handle first message
        if not self.user_states[user_id]['first_message_responded']:
            await self.handle_first_message(update, context)
            self.user_states[user_id]['first_message_responded'] = True
            
        # Check for triggers
        await self.check_triggers(update, context, message_text)
        
        # Save updated state
        self.save_states()
        
    async def handle_first_message(self, 
                                 update: Update, 
                                 context: ContextTypes.DEFAULT_TYPE):
        """Handle user's first message"""
        welcome_message = (
            "👋 Welcome! Thanks for your message.\n\n"
            "I'm here to help you with:\n"
            "• Channel membership\n"
            "• Group access\n"
            "• Content sharing\n\n"
            "How can I assist you today?"
        )
        
        keyboard = [
            [
                InlineKeyboardButton(
                    "Join Channel 📢", 
                    url=config.CHANNEL_INFO[config.REQUIRED_CHANNELS[0]]['invite_link']
                )
            ],
            [
                InlineKeyboardButton(
                    "Help ℹ️", 
                    callback_data="help"
                )
            ]
        ]
        
        await update.message.reply_text(
            welcome_message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    async def check_triggers(self, 
                           update: Update, 
                           context: ContextTypes.DEFAULT_TYPE,
                           message_text: str):
        """Check and respond to message triggers"""
        triggers = {
            'help': self.handle_help_trigger,
            'join': self.handle_join_trigger,
            'admin': self.handle_admin_trigger,
            # Add more triggers as needed
        }
        
        for trigger, handler in triggers.items():
            if trigger.lower() in message_text.lower():
                await handler(update, context)
                self.user_states[str(update.effective_user.id)]['triggers_used'].append(trigger)
                break
        
    def get_user_state(self, user_id: int) -> Dict[str, Any]:
        """Get user state with initialization if needed"""
        user_id_str = str(user_id)
        if user_id_str not in self.user_states:
            self.user_states[user_id_str] = {
                'state': None,
                'data': {}
            }
            self.save_states()
        return self.user_states[user_id_str]
        
    async def process_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Process incoming message and determine response type"""
        user_id = update.effective_user.id
        state = self.get_user_state(user_id)
        message_text = update.message.text
        
        # Update state
        state['message_count'] += 1
        state['last_message'] = datetime.now().isoformat()
        
        # Check triggers
        triggers = self.check_message_triggers(message_text)
        new_triggers = set(triggers) - set(state.get('triggers_hit', []))
        
        # Update triggers hit
        state['triggers_hit'] = list(set(state.get('triggers_hit', [])) | new_triggers)
        
        # Determine if we should respond
        should_respond = (
            state['message_count'] == 1 or  # First message
            new_triggers or  # New trigger hit
            self.check_time_gap(state['last_auto_reply'])  # Enough time passed
        )
        
        if should_respond:
            state['last_auto_reply'] = datetime.now().isoformat()
            
        self.save_states()
        return should_respond
        
    def check_message_triggers(self, message: str) -> list:
        """Check message for response triggers"""
        triggers = []
        message = message.lower()
        
        # Add your trigger words/phrases here
        if 'help' in message:
            triggers.append('help')
        if 'price' in message or 'cost' in message:
            triggers.append('pricing')
        if 'join' in message or 'channel' in message:
            triggers.append('channel')
        if 'admin' in message or 'support' in message:
            triggers.append('support')
            
        return triggers
        
    def check_time_gap(self, last_reply: str, min_gap_hours: int = 12) -> bool:
        """Check if enough time has passed since last auto-reply"""
        if not last_reply:
            return True
            
        last_time = datetime.fromisoformat(last_reply)
        time_gap = datetime.now() - last_time
        return time_gap > timedelta(hours=min_gap_hours)

    def update_user_state(self, user_id: int, state: str, data: Dict[str, Any] = None):
        """Update user state with thread safety"""
        with self._lock:
            user_id_str = str(user_id)
            self.user_states[user_id_str] = {
                'state': state,
                'data': data or {}
            }
            self.save_states() 