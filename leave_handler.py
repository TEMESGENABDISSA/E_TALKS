from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime
import logging
import json
import config

class LeaveRequestHandler:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.pending_requests = {}
        self.load_requests()
        
    def load_requests(self):
        """Load saved leave requests"""
        try:
            with open('data/leave_requests.json', 'r') as f:
                self.pending_requests = json.load(f)
        except FileNotFoundError:
            self.pending_requests = {}
            
    def save_requests(self):
        """Save leave requests to file"""
        try:
            with open('data/leave_requests.json', 'w') as f:
                json.dump(self.pending_requests, f)
        except Exception as e:
            self.logger.error(f"Error saving leave requests: {e}")
            
    async def handle_leave_attempt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle when user tries to leave"""
        user = update.effective_user
        chat = update.effective_chat
        
        # Check if already has pending request
        if str(user.id) in self.pending_requests:
            await update.message.reply_text(
                "You already have a pending leave request. "
                "Please wait for admin approval."
            )
            return
            
        # Create leave request buttons
        keyboard = [
            [InlineKeyboardButton("Submit Reason 📝", callback_data=f"leave_reason_{chat.id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🚪 Before you leave:\n\n"
            "1. Please tell us why you're leaving\n"
            "2. Wait for admin approval\n\n"
            "This helps us improve our community!",
            reply_markup=reply_markup
        )
        
    async def collect_leave_reason(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Collect reason for leaving"""
        await update.callback_query.edit_message_text(
            "Please reply with your reason for leaving.\n"
            "Start your message with 'REASON:' followed by your explanation."
        )
        
    async def process_leave_reason(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process the submitted leave reason"""
        user = update.effective_user
        message = update.message.text
        
        if not message.upper().startswith("REASON:"):
            await update.message.reply_text(
                "Please start your message with 'REASON:' "
                "followed by your explanation."
            )
            return
            
        reason = message[7:].strip()  # Remove "REASON:" prefix
        
        # Store leave request
        self.pending_requests[str(user.id)] = {
            "user_id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
            "status": "pending"
        }
        self.save_requests()
        
        # Notify admins
        admin_keyboard = [
            [
                InlineKeyboardButton("Approve ✅", callback_data=f"approve_leave_{user.id}"),
                InlineKeyboardButton("Deny ❌", callback_data=f"deny_leave_{user.id}")
            ]
        ]
        admin_markup = InlineKeyboardMarkup(admin_keyboard)
        
        admin_message = (
            f"🚪 Leave Request\n\n"
            f"From: {user.first_name} (@{user.username if user.username else 'No username'})\n"
            f"User ID: {user.id}\n\n"
            f"Reason:\n{reason}"
        )
        
        for admin_id in config.ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=admin_message,
                    reply_markup=admin_markup
                )
            except Exception as e:
                self.logger.error(f"Failed to notify admin {admin_id}: {e}")
                
        # Confirm to user
        await update.message.reply_text(
            "✅ Your leave request has been submitted.\n"
            "Please wait for admin approval.\n"
            "You will be notified once a decision is made."
        )
        
    async def handle_admin_decision(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process admin's decision on leave request"""
        query = update.callback_query
        action, _, user_id = query.data.partition('_leave_')
        
        if str(user_id) not in self.pending_requests:
            await query.answer("Request not found or already processed")
            return
            
        request = self.pending_requests[str(user_id)]
        is_approved = action == "approve"
        
        try:
            if is_approved:
                # Remove from group
                await context.bot.ban_chat_member(
                    chat_id=update.effective_chat.id,
                    user_id=int(user_id),
                    revoke_messages=False
                )
                # Immediately unban to allow future joins
                await context.bot.unban_chat_member(
                    chat_id=update.effective_chat.id,
                    user_id=int(user_id),
                    only_if_banned=True
                )
            
            # Notify user
            await context.bot.send_message(
                chat_id=int(user_id),
                text=(
                    "✅ Your leave request has been approved. You can now leave the group.\n"
                    "Thank you for your time with us!" if is_approved else
                    "❌ Your leave request has been denied. An admin will contact you soon."
                )
            )
            
            # Update request status
            request['status'] = 'approved' if is_approved else 'denied'
            request['processed_by'] = update.effective_user.id
            request['processed_at'] = datetime.now().isoformat()
            self.save_requests()
            
            # Update admin message
            await query.edit_message_text(
                f"Leave request for user {user_id} has been "
                f"{'approved ✅' if is_approved else 'denied ❌'}"
            )
            
        except Exception as e:
            self.logger.error(f"Error processing leave request: {e}")
            await query.answer("Error processing request") 