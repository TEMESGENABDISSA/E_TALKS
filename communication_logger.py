from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime
import json
import logging
from typing import Dict, Any, Optional
import config
import os

class CommunicationLogger:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.communication_logs: Dict[str, list] = {}
        self.setup_logging()
        self.load_logs()
        
    def setup_logging(self):
        """Setup logging configuration"""
        if not os.path.exists('logs'):
            os.makedirs('logs')
            
        # File handler for detailed logs
        file_handler = logging.FileHandler('logs/communication.log')
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
    def load_logs(self):
        """Load communication logs from file"""
        try:
            with open('data/communication_logs.json', 'r') as f:
                self.communication_logs = json.load(f)
        except FileNotFoundError:
            self.save_logs()
            
    def save_logs(self):
        """Save communication logs to file"""
        try:
            with open('data/communication_logs.json', 'w') as f:
                json.dump(self.communication_logs, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error saving logs: {e}")
            
    async def log_communication_attempt(self,
                                      update: Update,
                                      context: ContextTypes.DEFAULT_TYPE,
                                      is_member: bool,
                                      action_taken: str):
        """Log communication attempt"""
        user = update.effective_user
        chat = update.effective_chat
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'user_id': str(user.id),
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'chat_type': chat.type,
            'chat_id': str(chat.id),
            'is_member': is_member,
            'action_taken': action_taken,
            'message_type': update.message.type if update.message else 'callback_query',
            'bot_online': True
        }
        
        # Add to logs
        user_key = str(user.id)
        if user_key not in self.communication_logs:
            self.communication_logs[user_key] = []
        self.communication_logs[user_key].append(log_entry)
        
        # Save logs
        self.save_logs()
        
        # Log to file
        self.logger.info(
            f"Communication attempt - User: {user.username} ({user.id}) - "
            f"Member: {is_member} - Action: {action_taken}"
        )
        
        # Forward to admin channel if configured
        if config.ADMIN_LOG_CHANNEL_ID:
            await self.notify_admins(context, log_entry)
            
    async def check_membership_and_log(self,
                                     update: Update,
                                     context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check channel membership and log attempt"""
        user = update.effective_user
        
        # Check membership
        is_member = False
        try:
            for channel_id in config.REQUIRED_CHANNELS:
                member = await context.bot.get_chat_member(
                    chat_id=channel_id,
                    user_id=user.id
                )
                if member.status in ['member', 'administrator', 'creator']:
                    is_member = True
                    break
                    
        except Exception as e:
            self.logger.error(f"Error checking membership: {e}")
            
        # Log attempt
        action = "allowed" if is_member else "blocked"
        await self.log_communication_attempt(update, context, is_member, action)
        
        # Handle non-members
        if not is_member:
            await self.send_join_prompt(update, context)
            return False
            
        return True
        
    async def send_join_prompt(self,
                              update: Update,
                              context: ContextTypes.DEFAULT_TYPE):
        """Send channel join prompt"""
        keyboard = [
            [
                InlineKeyboardButton(
                    "Join Channel 📢",
                    url=config.CHANNEL_INFO[config.REQUIRED_CHANNELS[0]]['invite_link']
                ),
                InlineKeyboardButton(
                    "Check Membership ✅",
                    callback_data="check_membership"
                )
            ]
        ]
        
        await update.message.reply_text(
            config.MESSAGES['JOIN_REQUIRED'].format(
                channel_name=config.CHANNEL_INFO[config.REQUIRED_CHANNELS[0]]['name']
            ),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    async def notify_admins(self,
                           context: ContextTypes.DEFAULT_TYPE,
                           log_entry: Dict[str, Any]):
        """Notify admins about communication attempt"""
        message = (
            f"📝 Communication Log\n\n"
            f"User: @{log_entry['username']} "
            f"({log_entry['first_name']} {log_entry.get('last_name', '')})\n"
            f"ID: {log_entry['user_id']}\n"
            f"Member: {'✅' if log_entry['is_member'] else '❌'}\n"
            f"Action: {log_entry['action_taken']}\n"
            f"Time: {datetime.fromisoformat(log_entry['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        try:
            await context.bot.send_message(
                chat_id=config.ADMIN_LOG_CHANNEL_ID,
                text=message
            )
        except Exception as e:
            self.logger.error(f"Error notifying admins: {e}")
            
    async def get_user_logs(self, user_id: str) -> Optional[list]:
        """Get communication logs for specific user"""
        return self.communication_logs.get(str(user_id), [])
        
    async def generate_log_report(self,
                                start_date: Optional[datetime] = None,
                                end_date: Optional[datetime] = None) -> str:
        """Generate log report for specified date range"""
        if not start_date:
            start_date = datetime.min
        if not end_date:
            end_date = datetime.max
            
        report = []
        total_attempts = 0
        member_attempts = 0
        blocked_attempts = 0
        
        for user_logs in self.communication_logs.values():
            for log in user_logs:
                log_date = datetime.fromisoformat(log['timestamp'])
                if start_date <= log_date <= end_date:
                    total_attempts += 1
                    if log['is_member']:
                        member_attempts += 1
                    else:
                        blocked_attempts += 1
                        
        report.append(f"📊 Communication Log Report\n")
        report.append(f"Period: {start_date.date()} to {end_date.date()}\n")
        report.append(f"Total attempts: {total_attempts}")
        report.append(f"Member attempts: {member_attempts}")
        report.append(f"Blocked attempts: {blocked_attempts}")
        
        return "\n".join(report) 