from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError
import logging
import json
from datetime import datetime
from typing import Dict, List, Set
import asyncio
import config

class ContactManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.contacts: Dict[str, Dict] = {}
        self.pending_invites: Dict[str, List] = {}
        self.processed_users: Set[int] = set()
        self.load_data()
        
    def load_data(self):
        """Load contact data from file"""
        try:
            with open('data/contacts_data.json', 'r') as f:
                data = json.load(f)
                self.contacts = data.get('contacts', {})
                self.pending_invites = data.get('pending_invites', {})
        except FileNotFoundError:
            self.save_data()
            
    def save_data(self):
        """Save contact data to file"""
        try:
            with open('data/contacts_data.json', 'w') as f:
                json.dump({
                    'contacts': self.contacts,
                    'pending_invites': self.pending_invites
                }, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error saving contact data: {e}")
            
    async def start_contact_collection(self, 
                                     update: Update, 
                                     context: ContextTypes.DEFAULT_TYPE):
        """Start collecting contacts from a group"""
        try:
            # Verify admin
            if str(update.effective_user.id) not in config.ADMIN_IDS:
                await update.message.reply_text("⚠️ Only admins can use this command")
                return
                
            chat = update.effective_chat
            if chat.type not in ['group', 'supergroup']:
                await update.message.reply_text("⚠️ This command only works in groups")
                return
                
            # Start collection process
            status_message = await update.message.reply_text(
                "🔄 Starting contact collection...\n"
                "This may take a few minutes."
            )
            
            # Get members
            members = await context.bot.get_chat_administrators(chat.id)
            total_members = len(members)
            
            results = {
                'total': total_members,
                'added': 0,
                'invited': 0,
                'failed': 0
            }
            
            # Process members
            for i, member in enumerate(members, 1):
                if member.user.id in self.processed_users:
                    continue
                    
                try:
                    # Add to contacts
                    contact_info = {
                        'user_id': str(member.user.id),
                        'username': member.user.username,
                        'first_name': member.user.first_name,
                        'last_name': member.user.last_name,
                        'added_date': datetime.now().isoformat(),
                        'source_group': str(chat.id),
                        'status': 'pending'
                    }
                    
                    # Save contact
                    self.contacts[str(member.user.id)] = contact_info
                    self.save_data()
                    
                    # Forward to private channel
                    await self.forward_contact_to_channel(
                        context, 
                        contact_info
                    )
                    
                    results['added'] += 1
                    
                except Exception as e:
                    self.logger.error(f"Error processing member {member.user.id}: {e}")
                    results['failed'] += 1
                    
                # Update status every 10 members
                if i % 10 == 0:
                    await status_message.edit_text(
                        f"🔄 Processing contacts...\n"
                        f"Progress: {i}/{total_members}\n"
                        f"✅ Added: {results['added']}\n"
                        f"📨 Invited: {results['invited']}\n"
                        f"❌ Failed: {results['failed']}"
                    )
                    
                # Rate limiting
                await asyncio.sleep(0.5)
                
            # Final update
            await status_message.edit_text(
                f"✅ Contact collection complete!\n\n"
                f"📊 Results:\n"
                f"• Total processed: {results['total']}\n"
                f"• Successfully added: {results['added']}\n"
                f"• Invites sent: {results['invited']}\n"
                f"• Failed: {results['failed']}"
            )
            
        except Exception as e:
            self.logger.error(f"Error in contact collection: {e}")
            await update.message.reply_text(
                f"❌ Error collecting contacts: {str(e)}"
            )
            
    async def forward_contact_to_channel(self, 
                                       context: ContextTypes.DEFAULT_TYPE,
                                       contact_info: Dict):
        """Forward contact to private channel"""
        try:
            message_text = (
                f"👤 New Contact\n\n"
                f"Name: {contact_info['first_name']}"
                f" {contact_info.get('last_name', '')}\n"
                f"Username: @{contact_info.get('username', 'N/A')}\n"
                f"ID: {contact_info['user_id']}\n"
                f"Source: {contact_info['source_group']}\n"
                f"Added: {datetime.fromisoformat(contact_info['added_date']).strftime('%Y-%m-%d %H:%M')}"
            )
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        "Add to Group ➕", 
                        callback_data=f"add_contact_{contact_info['user_id']}"
                    ),
                    InlineKeyboardButton(
                        "Send Invite 📨", 
                        callback_data=f"invite_contact_{contact_info['user_id']}"
                    )
                ]
            ]
            
            await context.bot.send_message(
                chat_id=config.PRIVATE_CHANNEL_ID,
                text=message_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            self.logger.error(f"Error forwarding contact: {e}")
            
    async def add_contact_to_group(self, 
                                 update: Update, 
                                 context: ContextTypes.DEFAULT_TYPE):
        """Add contact to target group"""
        query = update.callback_query
        user_id = query.data.split('_')[2]
        
        try:
            # Get contact info
            contact = self.contacts.get(user_id)
            if not contact:
                await query.answer("Contact not found")
                return
                
            # Try to add to group
            try:
                await context.bot.unban_chat_member(
                    chat_id=config.TARGET_GROUP_ID,
                    user_id=int(user_id)
                )
                await context.bot.add_chat_member(
                    chat_id=config.TARGET_GROUP_ID,
                    user_id=int(user_id)
                )
                
                contact['status'] = 'added'
                self.save_data()
                
                await query.edit_message_text(
                    f"{query.message.text}\n\n"
                    f"✅ Added to group successfully"
                )
                
            except TelegramError as e:
                # If can't add, send invite
                if "user's privacy" in str(e).lower():
                    await self.send_invite_link(context, user_id)
                    await query.edit_message_text(
                        f"{query.message.text}\n\n"
                        f"📨 Invite link sent (privacy settings)"
                    )
                else:
                    raise e
                    
        except Exception as e:
            self.logger.error(f"Error adding contact: {e}")
            await query.answer(f"Error: {str(e)}")
            
    async def send_invite_link(self, 
                             context: ContextTypes.DEFAULT_TYPE,
                             user_id: str):
        """Send invite link to user"""
        try:
            message = (
                f"👋 Hello!\n\n"
                f"You're invited to join our group:\n"
                f"{config.GROUP_INVITE_LINK}\n\n"
                f"Looking forward to seeing you there!"
            )
            
            await context.bot.send_message(
                chat_id=int(user_id),
                text=message
            )
            
            # Update invite status
            if user_id in self.contacts:
                self.contacts[user_id]['status'] = 'invited'
                self.save_data()
                
        except Exception as e:
            self.logger.error(f"Error sending invite: {e}")
            raise 