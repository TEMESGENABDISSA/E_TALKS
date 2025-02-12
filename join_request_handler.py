from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
import config

class JoinRequestHandler:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.pending_requests = {}  # Store pending requests
        
    async def check_approval_status(self, user_id: int) -> bool:
        """Check if user is approved"""
        return user_id in config.APPROVED_USERS
        
    async def handle_new_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Handle new user interaction"""
        user_id = update.effective_user.id
        
        # Skip for admins
        if str(user_id) in config.ADMIN_IDS:
            return True
            
        # Check if already approved
        if await self.check_approval_status(user_id):
            return True
            
        # Send welcome message with join button
        keyboard = [
            [
                InlineKeyboardButton("Join Channel 📢", url=config.CHANNEL_INVITE_LINK),
                InlineKeyboardButton("Submit Introduction 📝", callback_data="submit_intro")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            config.JOIN_REQUEST_SETTINGS["WELCOME_MESSAGE"],
            reply_markup=reply_markup
        )
        return False
        
    async def handle_introduction(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process user introduction"""
        user = update.effective_user
        intro_text = update.message.text
        
        # Store in pending requests
        self.pending_requests[user.id] = {
            'name': user.first_name,
            'username': user.username,
            'introduction': intro_text,
            'timestamp': update.message.date
        }
        
        # Notify admins
        admin_keyboard = [
            [
                InlineKeyboardButton("Approve ✅", callback_data=f"approve_{user.id}"),
                InlineKeyboardButton("Reject ❌", callback_data=f"reject_{user.id}")
            ]
        ]
        admin_markup = InlineKeyboardMarkup(admin_keyboard)
        
        admin_message = (
            f"🆕 New Join Request\n\n"
            f"From: {user.first_name} (@{user.username if user.username else 'No username'})\n"
            f"ID: {user.id}\n\n"
            f"Introduction:\n{intro_text}"
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
        
        # Notify user
        await update.message.reply_text(config.JOIN_REQUEST_SETTINGS["PENDING_MESSAGE"])
        
    async def handle_approval_decision(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle admin's approval decision"""
        query = update.callback_query
        action, user_id = query.data.split('_')
        user_id = int(user_id)
        
        if action == "approve":
            config.APPROVED_USERS.add(user_id)
            await context.bot.send_message(
                chat_id=user_id,
                text=config.JOIN_REQUEST_SETTINGS["APPROVED_MESSAGE"]
            )
            await query.edit_message_text(f"✅ User {user_id} has been approved.")
            
        elif action == "reject":
            if user_id in self.pending_requests:
                del self.pending_requests[user_id]
            await context.bot.send_message(
                chat_id=user_id,
                text=config.JOIN_REQUEST_SETTINGS["REJECTED_MESSAGE"]
            )
            await query.edit_message_text(f"❌ User {user_id} has been rejected.") 