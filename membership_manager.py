from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, Any
import config

class MembershipManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.members: Dict[str, Dict[str, Any]] = {}
        self.leave_requests: Dict[str, Dict[str, Any]] = {}
        self.load_data()
        
    def load_data(self):
        """Load membership data from file"""
        try:
            with open('data/membership_data.json', 'r') as f:
                data = json.load(f)
                self.members = data.get('members', {})
                self.leave_requests = data.get('leave_requests', {})
        except FileNotFoundError:
            self.save_data()
            
    def save_data(self):
        """Save membership data to file"""
        try:
            with open('data/membership_data.json', 'w') as f:
                json.dump({
                    'members': self.members,
                    'leave_requests': self.leave_requests
                }, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error saving membership data: {e}")
            
    async def handle_new_member(self, 
                              chat_id: str, 
                              user_id: str, 
                              username: str,
                              join_date: datetime = None):
        """Record new member join"""
        if join_date is None:
            join_date = datetime.now()
            
        member_key = f"{chat_id}_{user_id}"
        self.members[member_key] = {
            'user_id': user_id,
            'username': username,
            'chat_id': chat_id,
            'join_date': join_date.isoformat(),
            'status': 'active'
        }
        self.save_data()
        
    async def check_leave_eligibility(self, 
                                    chat_id: str, 
                                    user_id: str) -> tuple[bool, str]:
        """Check if user can leave the channel/group"""
        member_key = f"{chat_id}_{user_id}"
        if member_key not in self.members:
            return False, "You are not registered as a member."
            
        member = self.members[member_key]
        join_date = datetime.fromisoformat(member['join_date'])
        time_passed = datetime.now() - join_date
        min_duration = timedelta(days=180)  # 6 months
        
        if time_passed < min_duration:
            days_remaining = (min_duration - time_passed).days
            return False, (
                f"⚠️ You must remain a member for at least 6 months before leaving.\n"
                f"Time remaining: {days_remaining} days"
            )
            
        return True, "Eligible to request leave"
        
    async def submit_leave_request(self, 
                                 update: Update, 
                                 context: ContextTypes.DEFAULT_TYPE):
        """Handle user leave request"""
        user = update.effective_user
        chat_id = str(update.effective_chat.id)
        user_id = str(user.id)
        
        # Check eligibility
        can_leave, message = await self.check_leave_eligibility(chat_id, user_id)
        
        if not can_leave:
            await update.message.reply_text(message)
            return
            
        # Create leave request
        request_key = f"{chat_id}_{user_id}"
        self.leave_requests[request_key] = {
            'user_id': user_id,
            'username': user.username,
            'chat_id': chat_id,
            'request_date': datetime.now().isoformat(),
            'status': 'pending'
        }
        self.save_data()
        
        # Notify user
        await update.message.reply_text(
            "✅ Your leave request has been submitted.\n"
            "Please wait for admin approval."
        )
        
        # Notify admins
        await self.notify_admins_leave_request(update, context, request_key)
        
    async def notify_admins_leave_request(self, 
                                        update: Update, 
                                        context: ContextTypes.DEFAULT_TYPE,
                                        request_key: str):
        """Notify admins about leave request"""
        request = self.leave_requests[request_key]
        member = self.members[request_key]
        join_date = datetime.fromisoformat(member['join_date'])
        
        keyboard = [
            [
                InlineKeyboardButton(
                    "Approve ✅", 
                    callback_data=f"approve_leave_{request_key}"
                ),
                InlineKeyboardButton(
                    "Deny ❌", 
                    callback_data=f"deny_leave_{request_key}"
                )
            ]
        ]
        
        message = (
            f"🔔 New Leave Request\n\n"
            f"User: @{request['username']}\n"
            f"User ID: {request['user_id']}\n"
            f"Join Date: {join_date.strftime('%Y-%m-%d')}\n"
            f"Member Duration: {(datetime.now() - join_date).days} days\n"
            f"Request Date: {datetime.fromisoformat(request['request_date']).strftime('%Y-%m-%d')}"
        )
        
        # Send to all admins
        for admin_id in config.ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=message,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e:
                self.logger.error(f"Error notifying admin {admin_id}: {e}")
                
    async def handle_admin_decision(self, 
                                  update: Update, 
                                  context: ContextTypes.DEFAULT_TYPE):
        """Handle admin's decision on leave request"""
        query = update.callback_query
        action, request_key = query.data.split('_', 2)[1:]
        
        if request_key not in self.leave_requests:
            await query.answer("Request not found or already processed")
            return
            
        request = self.leave_requests[request_key]
        approved = action == "approve"
        
        # Update request status
        request['status'] = 'approved' if approved else 'denied'
        request['decision_date'] = datetime.now().isoformat()
        request['decided_by'] = str(query.from_user.id)
        self.save_data()
        
        # Notify user
        try:
            if approved:
                await context.bot.send_message(
                    chat_id=request['chat_id'],
                    text=f"✅ Your request to leave has been approved. You may now leave the channel/group."
                )
                # Update member status
                self.members[request_key]['status'] = 'left'
                self.save_data()
            else:
                await context.bot.send_message(
                    chat_id=request['chat_id'],
                    text=f"❌ Your request to leave has been denied by the admin."
                )
        except Exception as e:
            self.logger.error(f"Error notifying user: {e}")
            
        # Update admin's message
        decision = "Approved ✅" if approved else "Denied ❌"
        await query.edit_message_text(
            f"{query.message.text}\n\n"
            f"Decision: {decision}\n"
            f"By: @{query.from_user.username}"
        ) 

DEFAULT_SETTINGS = {
    "channel_id": "#",
    "group_id": "#",
    "admin_channel": "#",
    "support_contact": "#"
} 