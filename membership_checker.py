from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
from typing import Optional
import config

class MembershipChecker:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def check_membership(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check if user is a member of required channel"""
        try:
            user_id = update.effective_user.id
            chat_member = await context.bot.get_chat_member(
                chat_id=config.REQUIRED_CHANNEL_ID,
                user_id=user_id
            )
            return chat_member.status in ['member', 'administrator', 'creator']
        except Exception as e:
            self.logger.error(f"Membership check error: {e}")
            return False

    async def request_join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send join request message with button"""
        keyboard = [
            [
                InlineKeyboardButton("Join Channel 📢", url=config.CHANNEL_INVITE_LINK),
                InlineKeyboardButton("Check Membership ✅", callback_data="check_membership")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            config.JOIN_REQUEST_MESSAGE,
            reply_markup=reply_markup
        )

    async def handle_leave_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle group leave requests"""
        user = update.effective_user
        
        keyboard = [
            [InlineKeyboardButton("Submit Reason 📝", callback_data="submit_leave_reason")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            config.LEAVE_REQUEST_MESSAGE,
            reply_markup=reply_markup
        )
        
        # Notify admins
        admin_message = (
            f"🚪 Leave Request\n"
            f"User: {user.first_name} ({user.id})\n"
            f"Username: @{user.username if user.username else 'None'}"
        )
        
        for admin_id in config.ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=admin_message,
                    reply_markup=InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("Approve ✅", callback_data=f"approve_leave_{user.id}"),
                            InlineKeyboardButton("Deny ❌", callback_data=f"deny_leave_{user.id}")
                        ]
                    ])
                )
            except Exception as e:
                self.logger.error(f"Failed to notify admin {admin_id}: {e}") 