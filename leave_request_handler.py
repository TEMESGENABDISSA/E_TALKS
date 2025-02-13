from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
from typing import Dict, Any
import json
from datetime import datetime
import config

class LeaveRequestHandler:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.leave_requests: Dict[str, Dict[str, Any]] = {}
        self.load_requests()
        
    def load_requests(self):
        """Load leave requests"""
        try:
            with open('data/leave_requests.json', 'r') as f:
                self.leave_requests = json.load(f)
        except FileNotFoundError:
            self.save_requests()
            
    def save_requests(self):
        """Save leave requests"""
        try:
            with open('data/leave_requests.json', 'w') as f:
                json.dump(self.leave_requests, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error saving requests: {e}")
            
    async def handle_leave_attempt(self,
                                 update: Update,
                                 context: ContextTypes.DEFAULT_TYPE):
        """Handle leave attempt"""
        user_id = str(update.effective_user.id)
        
        # Ask for reason
        keyboard = [
            [
                InlineKeyboardButton(
                    "Submit Reason 📝",
                    callback_data="submit_leave_reason"
                )
            ]
        ]
        
        await update.message.reply_text(
            "ℹ️ Leave Request Process\n\n"
            "1. Submit your reason for leaving\n"
            "2. Wait for admin approval\n"
            "3. Receive decision notification\n\n"
            "Click below to submit your reason:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    async def collect_leave_reason(self,
                                 update: Update,
                                 context: ContextTypes.DEFAULT_TYPE):
        """Collect reason for leaving"""
        query = update.callback_query
        user_id = str(query.from_user.id)
        
        # Start reason collection conversation
        context.user_data['collecting_reason'] = True
        
        await query.edit_message_text(
            "Please tell us why you want to leave:\n"
            "(Send your reason as a message)"
        )
        
    async def process_leave_reason(self,
                                 update: Update,
                                 context: ContextTypes.DEFAULT_TYPE):
        """Process submitted leave reason"""
        if not context.user_data.get('collecting_reason'):
            return
            
        user_id = str(update.effective_user.id)
        reason = update.message.text
        
        
        self.leave_requests[user_id] = {
            'reason': reason,
            'timestamp': datetime.now().isoformat(),
            'status': 'pending'
        }
        self.save_requests()
        
        
        await self.notify_admins(update, context, user_id, reason)
        
     
        await update.message.reply_text(
            "✅ Leave request submitted!\n\n"
            "• Admin will review your request\n"
            "• You'll be notified of the decision\n"
            "• Please wait for approval"
        )
        
        context.user_data['collecting_reason'] = False
        
    async def notify_admins(self,
                          update: Update,
                          context: ContextTypes.DEFAULT_TYPE,
                          user_id: str,
                          reason: str):
        """Notify admins about leave request"""
        keyboard = [
            [
                InlineKeyboardButton(
                    "Approve ✅",
                    callback_data=f"approve_leave_{user_id}"
                ),
                InlineKeyboardButton(
                    "Deny ❌",
                    callback_data=f"deny_leave_{user_id}"
                )
            ]
        ]
        
        user = await context.bot.get_chat_member(
            chat_id=update.effective_chat.id,
            user_id=int(user_id)
        )
        
        message = (
            "🔔 New Leave Request\n\n"
            f"User: @{user.user.username}\n"
            f"ID: {user_id}\n"
            f"Joined: {self.leave_requests[user_id]['timestamp']}\n"
            f"Reason: {reason}\n\n"
            "Please review and decide:"
        )
        
        for admin_id in config.ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=message,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e:
                self.logger.error(f"Error notifying admin {admin_id}: {e}") 