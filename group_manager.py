from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest, Forbidden
import logging
import asyncio
import config
from datetime import datetime

class GroupManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.processing_groups = set()
        self.processed_users = set()
        
    async def start_member_processing(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start processing group members"""
        try:
            group_id = update.effective_chat.id
            
            if group_id in self.processing_groups:
                await update.message.reply_text("⚠️ Already processing members from this group!")
                return
                
            self.processing_groups.add(group_id)
            
            # Get member count
            chat = await context.bot.get_chat(group_id)
            member_count = await context.bot.get_chat_members_count(group_id)
            
            # Ask for confirmation
            keyboard = [
                [
                    InlineKeyboardButton("Start ✅", callback_data=f"process_members_{group_id}"),
                    InlineKeyboardButton("Cancel ❌", callback_data="cancel_processing")
                ]
            ]
            await update.message.reply_text(
                f"Ready to process {member_count} members from {chat.title}\n"
                f"This will:\n"
                f"• Add members to private channel\n"
                f"• Send invites to restricted users\n"
                f"• Track processing status\n\n"
                f"Continue?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            self.logger.error(f"Error starting member processing: {e}")
            await update.message.reply_text("❌ Error starting member processing")
            
    async def process_members(self, update: Update, context: ContextTypes.DEFAULT_TYPE, group_id: int):
        """Process members from a group"""
        query = update.callback_query
        await query.answer()
        
        try:
            # Initialize counters
            added_count = 0
            invited_count = 0
            failed_count = 0
            
            # Get all members
            members = await context.bot.get_chat_members(group_id)
            total_members = len(members)
            
            # Update status message
            status_message = await query.edit_message_text(
                "🔄 Processing members...\n"
                "Progress: 0%"
            )
            
            # Process members in batches
            batch_size = 10
            for i in range(0, len(members), batch_size):
                batch = members[i:i + batch_size]
                
                for member in batch:
                    user = member.user
                    if user.id in self.processed_users:
                        continue
                        
                    try:
                        # Try to add to private channel
                        await context.bot.add_chat_member(
                            chat_id=config.PRIVATE_CHANNEL_ID,
                            user_id=user.id
                        )
                        added_count += 1
                        
                    except (BadRequest, Forbidden):
                        # If can't add, send invite
                        try:
                            await context.bot.send_message(
                                chat_id=user.id,
                                text=(
                                    f"👋 Hello {user.first_name}!\n\n"
                                    f"You're invited to join our channel:\n"
                                    f"{config.CHANNEL_INVITE_LINK}"
                                )
                            )
                            invited_count += 1
                        except:
                            failed_count += 1
                            
                    self.processed_users.add(user.id)
                    
                # Update progress
                progress = ((i + len(batch)) / total_members) * 100
                await status_message.edit_text(
                    f"🔄 Processing members...\n"
                    f"Progress: {progress:.1f}%\n"
                    f"✅ Added: {added_count}\n"
                    f"📨 Invited: {invited_count}\n"
                    f"❌ Failed: {failed_count}"
                )
                
                # Rate limiting
                await asyncio.sleep(2)
                
            # Final update
            await status_message.edit_text(
                f"✅ Processing complete!\n\n"
                f"📊 Results:\n"
                f"• Total processed: {total_members}\n"
                f"• Successfully added: {added_count}\n"
                f"• Invites sent: {invited_count}\n"
                f"• Failed: {failed_count}"
            )
            
        except Exception as e:
            self.logger.error(f"Error processing members: {e}")
            await query.edit_message_text("❌ Error processing members")
            
        finally:
            self.processing_groups.remove(group_id)
            
    async def cancel_processing(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel member processing"""
        query = update.callback_query
        await query.answer()
        
        group_id = int(query.data.split('_')[2])
        if group_id in self.processing_groups:
            self.processing_groups.remove(group_id)
            
        await query.edit_message_text("❌ Member processing cancelled") 