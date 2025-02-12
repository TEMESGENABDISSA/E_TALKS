from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
import logging
from typing import Dict, Any
import config

class ButtonHandler:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.active_menus = {}  # Track active menu states
        self.callback_map = {
            'join_channel': self.handle_join_channel,
            'check_membership': self.handle_check_membership,
            'contact_admin': self.handle_contact_admin,
            'help': self.handle_help,
            'approve_leave': self.handle_approve_leave,
            'deny_leave': self.handle_deny_leave
        }
        
    async def create_menu(self, title: str, buttons: list) -> InlineKeyboardMarkup:
        """Create a menu with working buttons"""
        keyboard = []
        row = []
        
        for button in buttons:
            if len(row) == 2:  # Max 2 buttons per row
                keyboard.append(row)
                row = []
            row.append(InlineKeyboardButton(
                text=button['text'],
                callback_data=button['callback_data']
            ))
            
        if row:  # Add remaining buttons
            keyboard.append(row)
            
        return InlineKeyboardMarkup(keyboard)
        
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show main menu with buttons"""
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
            ],
            [
                InlineKeyboardButton(
                    "Contact Admin 📩", 
                    callback_data="contact_admin"
                ),
                InlineKeyboardButton(
                    "Help ℹ️", 
                    callback_data="help"
                )
            ]
        ]
        
        
        await update.message.reply_text(
            "Welcome! Please select an option:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        try:
            # Always answer callback query first
            await query.answer()
            
            # Extract callback data
            callback_data = query.data
            
            # Log the callback
            self.logger.info(f"Button pressed: {callback_data} by user {query.from_user.id}")
            
            # Find and execute handler
            if '_' in callback_data:
                action, *params = callback_data.split('_')
                if action in self.callback_map:
                    await self.callback_map[action](update, context, *params)
                else:
                    self.logger.warning(f"Unknown callback action: {action}")
            else:
                if callback_data in self.callback_map:
                    await self.callback_map[callback_data](update, context)
                else:
                    self.logger.warning(f"Unknown callback data: {callback_data}")
                    
        except Exception as e:
            self.logger.error(f"Error handling callback: {e}")
            await query.edit_message_text(
                "❌ An error occurred. Please try again later."
            )
            
    async def handle_check_membership(self, 
                                    update: Update, 
                                    context: ContextTypes.DEFAULT_TYPE):
        """Handle membership check button"""
        query = update.callback_query
        user_id = query.from_user.id
        
        try:
            # Check membership in required channels
            is_member = True
            for channel_id in config.REQUIRED_CHANNELS:
                try:
                    member = await context.bot.get_chat_member(
                        chat_id=channel_id,
                        user_id=user_id
                    )
                    if member.status not in ['member', 'administrator', 'creator']:
                        is_member = False
                        break
                except Exception as e:
                    self.logger.error(f"Error checking membership: {e}")
                    is_member = False
                    break
                    
            if is_member:
                await query.edit_message_text(
                    "✅ You are a member of all required channels!\n"
                    "You can now use all features."
                )
            else:
                keyboard = [[
                    InlineKeyboardButton(
                        "Join Channel 📢",
                        url=config.CHANNEL_INFO[config.REQUIRED_CHANNELS[0]]['invite_link']
                    ),
                    InlineKeyboardButton(
                        "Check Again 🔄",
                        callback_data="check_membership"
                    )
                ]]
                
                await query.edit_message_text(
                    "❌ You need to join our channel first!\n"
                    "Please join and click 'Check Again'",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
        except Exception as e:
            self.logger.error(f"Error in membership check: {e}")
            await query.edit_message_text(
                "❌ Error checking membership. Please try again later."
            )
            
    async def handle_contact_admin(self, 
                                 update: Update, 
                                 context: ContextTypes.DEFAULT_TYPE):
        """Handle contact admin button"""
        query = update.callback_query
        user_id = query.from_user.id
        
        try:
            # Check if user can contact admin
            can_contact = await self.check_contact_permission(context, user_id)
            
            if can_contact:
                keyboard = [[
                    InlineKeyboardButton(
                        "Message Admin 📝",
                        callback_data="start_admin_message"
                    ),
                    InlineKeyboardButton(
                        "Back 🔙",
                        callback_data="main_menu"
                    )
                ]]
                
                await query.edit_message_text(
                    "📩 You can message the admin now.\n"
                    "Click 'Message Admin' to start.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                keyboard = [[
                    InlineKeyboardButton(
                        "Join Channel 📢",
                        url=config.CHANNEL_INFO[config.REQUIRED_CHANNELS[0]]['invite_link']
                    ),
                    InlineKeyboardButton(
                        "Check Again 🔄",
                        callback_data="check_membership"
                    )
                ]]
                
                await query.edit_message_text(
                    "⚠️ You need to be a channel member to contact admin.\n"
                    "Please join our channel first!",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
        except Exception as e:
            self.logger.error(f"Error in contact admin: {e}")
            await query.edit_message_text(
                "❌ Error processing request. Please try again later."
            )
            
    async def handle_help(self, 
                         update: Update, 
                         context: ContextTypes.DEFAULT_TYPE):
        """Handle help button"""
        query = update.callback_query
        
        help_text = (
            "🔹 *Available Commands*:\n"
            "/start - Show main menu\n"
            "/help - Show this help message\n"
            "/check - Check membership status\n\n"
            "🔹 *How to use*:\n"
            "1. Join our channel\n"
            "2. Verify membership\n"
            "3. Access features\n\n"
            "🔹 *Need help?*\n"
            "Contact admin for assistance"
        )
        
        keyboard = [[
            InlineKeyboardButton(
                "Back to Menu 🔙",
                callback_data="main_menu"
            )
        ]]
        
        await query.edit_message_text(
            help_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    async def check_contact_permission(self, 
                                     context: ContextTypes.DEFAULT_TYPE,
                                     user_id: int) -> bool:
        """Check if user has permission to contact admin"""
        try:
            for channel_id in config.REQUIRED_CHANNELS:
                member = await context.bot.get_chat_member(
                    chat_id=channel_id,
                    user_id=user_id
                )
                if member.status not in ['member', 'administrator', 'creator']:
                    return False
            return True
        except Exception as e:
            self.logger.error(f"Error checking contact permission: {e}")
            return False
            
    async def send_menu_message(self, 
                              update: Update, 
                              context: ContextTypes.DEFAULT_TYPE,
                              title: str,
                              buttons: list):
        """Send a new menu message with buttons"""
        try:
            markup = await self.create_menu(title, buttons)
            message = await update.message.reply_text(
                title,
                reply_markup=markup
            )
            
            # Track this menu
            self.active_menus[message.message_id] = {
                'title': title,
                'buttons': buttons,
                'last_pressed': None
            }
            
            return message
            
        except Exception as e:
            self.logger.error(f"Error sending menu: {e}")
            return None
            
    async def update_menu(self,
                         update: Update,
                         context: ContextTypes.DEFAULT_TYPE,
                         message_id: int,
                         new_title: str = None,
                         new_buttons: list = None):
        """Update an existing menu"""
        try:
            if message_id not in self.active_menus:
                return False
                
            menu = self.active_menus[message_id]
            title = new_title or menu['title']
            buttons = new_buttons or menu['buttons']
            
            markup = await self.create_menu(title, buttons)
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text=title,
                reply_markup=markup
            )
            
            # Update tracked menu
            self.active_menus[message_id].update({
                'title': title,
                'buttons': buttons
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating menu: {e}")
            return False 