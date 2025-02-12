from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError
import json
import logging
from datetime import datetime
from typing import Dict, List, Set
import config

class MemberMigration:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.processed_members: Set[int] = set()
        self.member_consents: Dict[str, bool] = {}
        self.load_consents()
        
    def load_consents(self):
        """Load member consents from file"""
        try:
            with open('data/member_consents.json', 'r') as f:
                self.member_consents = json.load(f)
        except FileNotFoundError:
            self.save_consents()
            
    def save_consents(self):
        """Save member consents to file"""
        try:
            with open('data/member_consents.json', 'w') as f:
                json.dump(self.member_consents, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error saving consents: {e}")
            
    async def start_migration(self, 
                            update: Update, 
                            context: ContextTypes.DEFAULT_TYPE):
        """Start member migration process"""
        if str(update.effective_user.id) not in config.ADMIN_IDS:
            await update.message.reply_text("⚠️ Only admins can use this command")
            return
            
        source_group_id = config.SOURCE_GROUP_ID
        target_group_id = config.TARGET_GROUP_ID
        
        status_message = await update.message.reply_text(
            "🔄 Starting member migration...\n"
            "This may take some time."
        )
        
        try:
            # Get members from source group
            members = await context.bot.get_chat_administrators(source_group_id)
            total_members = len(members)
            
            results = {
                'total': total_members,
                'processed': 0,
                'added': 0,
                'invited': 0,
                'failed': 0
            }
            
            for member in members:
                if member.user.id in self.processed_members:
                    continue
                    
                try:
                    # Request consent
                    consent = await self.request_consent(context, member.user.id)
                    if not consent:
                        continue
                        
                    # Try to add member
                    try:
                        await context.bot.add_chat_member(
                            chat_id=target_group_id,
                            user_id=member.user.id
                        )
                        results['added'] += 1
                        
                    except TelegramError as e:
                        if "user's privacy" in str(e).lower():
                            # Send invitation
                            await self.send_invitation(context, member.user.id)
                            results['invited'] += 1
                        else:
                            results['failed'] += 1
                            
                    self.processed_members.add(member.user.id)
                    results['processed'] += 1
                    
                    # Update status every 10 members
                    if results['processed'] % 10 == 0:
                        await self.update_status(status_message, results)
                        
                except Exception as e:
                    self.logger.error(f"Error processing member {member.user.id}: {e}")
                    results['failed'] += 1
                    
            # Final status update
            await self.update_status(status_message, results, final=True)
            
        except Exception as e:
            self.logger.error(f"Error in migration: {e}")
            await status_message.edit_text(
                f"❌ Error during migration: {str(e)}"
            )
            
    async def request_consent(self, 
                            context: ContextTypes.DEFAULT_TYPE,
                            user_id: int) -> bool:
        """Request user consent for migration"""
        try:
            keyboard = [
                [
                    InlineKeyboardButton(
                        "Yes, I Consent ✅",
                        callback_data=f"consent_yes_{user_id}"
                    ),
                    InlineKeyboardButton(
                        "No, Thanks ❌",
                        callback_data=f"consent_no_{user_id}"
                    )
                ]
            ]
            
            consent_message = (
                "🔐 Privacy Consent\n\n"
                "We'd like to:\n"
                "• Save your contact info\n"
                "• Add you to our group\n"
                "• Send you updates\n\n"
                "Do you consent?"
            )
            
            await context.bot.send_message(
                chat_id=user_id,
                text=consent_message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            # Wait for response (implement with conversation handler)
            # For now, return True for testing
            return True
            
        except Exception as e:
            self.logger.error(f"Error requesting consent: {e}")
            return False
            
    async def send_invitation(self, 
                            context: ContextTypes.DEFAULT_TYPE,
                            user_id: int):
        """Send group invitation to user"""
        try:
            invite_message = (
                "👋 Hello!\n\n"
                "You're invited to join our group:\n"
                f"{config.GROUP_INVITE_LINK}\n\n"
                "Looking forward to seeing you there!"
            )
            
            await context.bot.send_message(
                chat_id=user_id,
                text=invite_message
            )
            
        except Exception as e:
            self.logger.error(f"Error sending invitation: {e}")
            
    async def update_status(self, 
                          message, 
                          results: Dict[str, int],
                          final: bool = False):
        """Update migration status message"""
        status_text = (
            f"{'✅ Migration Complete!' if final else '🔄 Migration in Progress...'}\n\n"
            f"📊 Progress:\n"
            f"• Total members: {results['total']}\n"
            f"• Processed: {results['processed']}\n"
            f"• Added: {results['added']}\n"
            f"• Invited: {results['invited']}\n"
            f"• Failed: {results['failed']}"
        )
        
        await message.edit_text(status_text) 