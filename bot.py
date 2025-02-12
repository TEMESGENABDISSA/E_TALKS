import logging
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from config import (
    BOT_TOKEN, PRIVATE_CHANNEL_ID, SOCIAL_LINKS, 
    ADMIN_ID, OFFLINE_MESSAGE, ABOUT_TEMESGEN, get_social_links_keyboard,
    ADMIN_IDS, REQUIRE_CHANNEL_JOIN, CHANNEL_INVITE_LINK,
    REQUIRED_CHANNEL_USERNAME, REQUIRED_CHANNEL_ID, JOIN_MESSAGES
)
from user_manager import UserManager
from content_moderator import ContentModerator
from membership_checker import MembershipChecker
import os
from pathlib import Path
from dotenv import load_dotenv
from telegram.error import TelegramError
from join_request_handler import JoinRequestHandler
from group_manager import GroupManager
from leave_handler import LeaveRequestHandler
from button_handler import ButtonHandler
from conversation_manager import ConversationManager
from member_migration import MemberMigration
from channel_manager import ChannelManager
from message_forwarder import MessageForwarder
from session_manager import SessionManager
import asyncio
from consent_manager import ConsentManager
from membership_manager import MembershipManager
from contact_manager import ContactManager
from communication_logger import CommunicationLogger
from content_sharing import ContentSharing
from subscription_enforcer import SubscriptionEnforcer

# Load environment variables
load_dotenv()

# Import config module
try:
    import config
except ImportError:
    raise ImportError("Could not import config.py. Make sure it exists in the same directory.")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Add this line to define logger
logger = logging.getLogger(__name__)

# Enable debug logging for PTB library
logging.getLogger('telegram').setLevel(logging.INFO)
logging.getLogger('telegram.ext').setLevel(logging.INFO)

# Global variables
is_admin_online = False
user_manager = UserManager()
content_moderator = ContentModerator()
content_sharing = ContentSharing()
subscription_enforcer = SubscriptionEnforcer()

# Initialize checker
membership_checker = MembershipChecker()

# Initialize handlers
join_request_handler = JoinRequestHandler()

# Initialize manager
group_manager = GroupManager()

# Initialize handler
leave_handler = LeaveRequestHandler()

# Initialize button handler
button_handler = ButtonHandler()

# Initialize managers
conversation_manager = ConversationManager()
member_migration = MemberMigration()

# Initialize managers
channel_manager = ChannelManager()
message_forwarder = MessageForwarder(config.PRIVATE_CHANNEL_ID)
session_manager = SessionManager()

# Initialize consent manager
consent_manager = ConsentManager()

# Initialize contact manager
contact_manager = ContactManager()

# Initialize loggers
comm_logger = CommunicationLogger()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command"""
    try:
        keyboard = [
            [InlineKeyboardButton("🤝 Connect with Me 🤝", callback_data='social_links')]  # Fixed callback_data
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = (
            "👋 Hello! This is Temesgen.\n\n"
            "I'm offline right now, but you can drop your message if it's urgent!✉️\n\n"
            "🔄 I'll respond as soon as I'm back online.💬\n\n"
        )
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup
        )
        
        # Send welcome message if new user
        if user_manager.is_new_user(update.effective_user.id):
            await send_welcome_message(update, context)
            
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await error_handler(update, context)

async def send_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message to new users"""
    try:
        user = update.effective_user
        welcome_text = (
            f"👋 Welcome {user.first_name}! Thank you for reaching out! 🌟\n\n"
            f"I'm Temesgen's messaging bot. I'll make sure your messages reach him safely. 📬\n\n"
            f"Feel free to send your message, and I'll ensure it gets to him! 💫"
        )
        await update.message.reply_text(welcome_text)
        user_manager.mark_user_welcomed(user.id, user)
        logger.info(f"Welcome message sent to user {user.id}")
    except Exception as e:
        logger.error(f"Error sending welcome message: {e}")

async def check_channel_membership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user is a member of the required channel"""
    try:
        user_id = update.effective_user.id
        
        # Skip check for admin
        if str(user_id) == str(ADMIN_ID):
            return True
            
        chat_member = await context.bot.get_chat_member(
            chat_id=REQUIRED_CHANNEL_ID,
            user_id=user_id
        )
        
        # Debug membership check
        print(f"Member status: {chat_member.status}")
        
        return chat_member.status in ['member', 'administrator', 'creator']
        
    except TelegramError as e:
        logger.error(f"Error checking channel membership: {e}")
        return False

async def send_join_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send message requesting user to join channel"""
    keyboard = [
        [
            InlineKeyboardButton("Join Channel 📢", url=CHANNEL_INVITE_LINK),
            InlineKeyboardButton("Check Membership ✅", callback_data="check_membership")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        JOIN_MESSAGES["NOT_MEMBER"].format(
            channel_link=REQUIRED_CHANNEL_USERNAME
        ),
        reply_markup=reply_markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages"""
    try:
        # Check subscriptions first
        if not await subscription_enforcer.check_subscriptions(update, context):
            return
            
        # Check content
        if not await content_moderator.check_content(update, context):
            return
            
        # Process message
        await process_message(update, context)
        
    except Exception as e:
        logger.error(f"Error in handle_message: {e}")

def get_response_for_message(message: str) -> str:
    """Get appropriate response based on message content"""
    message = message.lower()
    
    if 'help' in message:
        return config.HELP_MESSAGE
    elif 'price' in message or 'cost' in message:
        return config.PRICING_MESSAGE
    elif 'join' in message or 'channel' in message:
        return config.CHANNEL_INFO_MESSAGE
    elif 'admin' in message or 'support' in message:
        return config.SUPPORT_MESSAGE
    else:
        return config.DEFAULT_RESPONSE

async def process_message_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages"""
    try:
        user_id = update.effective_user.id
        
        # First check channel membership
        is_member = await check_channel_membership(update, context)
        if not is_member:
            await send_join_message(update, context)
            return
            
        # Then check join request status
        if not await join_request_handler.check_approval_status(user_id):
            # New user or pending approval
            if update.message.text and "INTRODUCTION:" in update.message.text.upper():
                # Handle introduction submission
                await join_request_handler.handle_introduction(update, context)
                return
            else:
                # Request introduction
                await join_request_handler.handle_new_user(update, context)
                return
        
        # Check if user is blocked
        if user_manager.is_blocked(update.effective_user.id):
            # Silently ignore blocked users
            return
            
        # Content moderation
        should_block, reason = await content_moderator.should_block_message(update.message)
        
        if should_block:
            # Block user
            user_manager.block_user(update.effective_user.id, reason)
            
            # Forward to private channel without notification
            await context.bot.forward_message(
                chat_id=PRIVATE_CHANNEL_ID,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id,
                disable_notification=True
            )
            
            # Send block notification to admin
            await context.bot.send_message(
                chat_id=PRIVATE_CHANNEL_ID,
                text=f"🚫 User blocked for {reason}\n"
                     f"User: {update.effective_user.first_name}\n"
                     f"ID: {update.effective_user.id}",
                disable_notification=True
            )
            
            # Notify user (without read receipt)
            await update.message.reply_text(
                "Your message has been flagged as inappropriate. "
                "You have been blocked.",
                disable_notification=True
            )
            return

        # Save message details
        user = update.effective_user
        message_info = (
            f"From: {user.first_name} {user.last_name if user.last_name else ''}\n"
            f"Username: @{user.username if user.username else 'No username'}\n"
            f"User  ID: {user.id}\n"
            f"Message ID: {update.message.message_id}\n"
            f"Time: {update.message.date}\n"
            f"-------------------"
        )
        
        await context.bot.send_message(
            chat_id=PRIVATE_CHANNEL_ID,
            text=message_info
        )
        
        # Add user to database if new
        if user_manager.is_new_user(update.effective_user.id):
            user_manager.mark_user_welcomed(update.effective_user.id, update.effective_user)
        
        # Improve offline message handling
        if not is_admin_online:
            keyboard = [
                [InlineKeyboardButton("🤝 Connect with me!✨", callback_data='SOCIAL_LINKS')]  # Updated callback data
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                await update.message.reply_text(
                    OFFLINE_MESSAGE,
                    reply_markup=reply_markup,
                    disable_web_page_preview=False  # Show link previews
                )
            except Exception as reply_error:
                logger.error(f"Error sending offline message: {reply_error}")
    
    except Exception as e:
        logger.error(f"Error in process_message_content: {e}")
        await error_handler(update, context)

async def social_links_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the connect button callback"""
    try:
        query = update.callback_query
        await query.answer()

        # Create keyboard with social links
        keyboard = []
        
        # Add About Me button first
        keyboard.append([InlineKeyboardButton("👨‍💻 About Temesgen", callback_data='about_me')])
        
        # Add social links
        for platform, url in SOCIAL_LINKS.items():
            button_text = f"{'📧' if platform == 'Gmail' else '🔗'} {platform}"
            button_url = f"mailto:{url}" if platform == "Gmail" else url
            keyboard.append([InlineKeyboardButton(button_text, url=button_url)])
        
        # Add back button
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data='back')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text="🌟 Connect with Temesgen:\n\n"
                 "Choose how you'd like to connect:",
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Error in social_links_callback: {e}")
        await error_handler(update, context)

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the back button"""
    try:
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("🌟 Connect with Me 🌟", callback_data='SOCIAL_LINKS')]  # Updated callback data
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "👋 Hello! This is Temesgen.\n\n"
            "I'm offline right now, but you can drop your message if it's urgent! ✉️\n\n"
            "🔄 I'll respond as soon as I'm back online. 💬\n\n",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error in back_to_main: {e}")

async def toggle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle admin's online/offline status"""
    global is_admin_online
    
    if str(update.effective_user.id) != ADMIN_ID:
        return
    
    is_admin_online = not is_admin_online
    status = "online" if is_admin_online else "offline"
    await update.message.reply_text(f"Status changed to: {status}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check bot status - admin only"""
    if str(update.effective_user.id) != ADMIN_ID:
        return
    
    try:
        user_count = len(user_manager.users)
        blocked_users = sum(1 for user in user_manager.users.values() if user.get('blocked', False))
        
        status_message = (
            f"🤖 Bot Status Report:\n\n"
            f"✅ Bot is running\n"
            f"👥 Total users: {user_count}\n"
            f"🚫 Blocked users: {blocked_users}\n"
            f"🔄 Admin status: {'Online' if is_admin_online else 'Offline'}\n"
        )
        
        await update.message.reply_text(status_message)
    except Exception as e:
        logger.error(f"Error in status command: {e}")

async def about_me_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the About Temesgen button callback"""
    try:
        query = update.callback_query
        await query.answer()

        # Create services text with professional icons
        services_text = "\n".join(ABOUT_TEMESGEN['services'])
        
        # Create contact information text in desired order
        contact_text = (
            f"💼 LinkedIn: {ABOUT_TEMESGEN['contact_info']['linkedin']}\n"
            f"📧 Email: {ABOUT_TEMESGEN['contact_info']['email']}\n"
            f"📱 Telegram: {ABOUT_TEMESGEN['contact_info']['telegram']}"
        )
        
        about_text = (
            f"👨‍💻 *{ABOUT_TEMESGEN['name']}*\n\n"
            f"*Professional Background:*\n"
            f"💼 {ABOUT_TEMESGEN['profession']}\n"
            f"🎵 Passion: {ABOUT_TEMESGEN['passion']}\n"
            f"👑 {ABOUT_TEMESGEN['role']}\n\n"
            f"*Services Provided:*\n{services_text}\n\n"
            f"*Contact Information:*\n{contact_text}\n\n"
            f"_Let's bring your ideas to life!_ 🚀"
        ) 

        # Create keyboard with contact buttons in desired order
        keyboard = [
            [InlineKeyboardButton("💼 LinkedIn Profile", url=ABOUT_TEMESGEN['contact_info']['linkedin'])],
            [InlineKeyboardButton("📧 Send Email", url=f"mailto:{ABOUT_TEMESGEN['contact_info']['email']}")],
            [InlineKeyboardButton("📱 Telegram", url=ABOUT_TEMESGEN['contact_info']['telegram'])],
            [InlineKeyboardButton("🔙 Return to Menu", callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text=about_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in about_me_callback: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")

async def start_migration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to start migration process"""
    if str(update.effective_user.id) != str(ADMIN_ID):
        await update.message.reply_text("⚠️ This command is only available to administrators.")
        return

    try:
        # Get members from source group
        keyboard = [
            [
                InlineKeyboardButton("Start Migration ✅", callback_data="migrate_confirm"),
                InlineKeyboardButton("Cancel ❌", callback_data="migrate_cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔄 Ready to start member migration.\n"
            "This will:\n"
            "- Check member permissions\n"
            "- Request consent from members\n"
            "- Add consenting members to the new group\n\n"
            "Do you want to proceed?",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")
        logging.error(f"Migration error: {str(e)}")

async def migration_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle migration confirmation"""
    query = update.callback_query
    
    if query.data == "migrate_confirm":
        await member_migration.execute_migration(update, context)
    elif query.data == "migrate_cancel":
        await query.edit_message_text("Migration cancelled.")

async def handle_left_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle when user leaves or is removed from chat"""
    if update.message.left_chat_member.id == update.message.from_user.id:
        # User left voluntarily
        await leave_handler.handle_leave_attempt(update, context)
        
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries including consent responses"""
    query = update.callback_query
    
    try:
        if query.data.startswith('consent_'):
            await consent_manager.handle_consent_response(update, context)
        else:
            # Handle other callbacks...
            await handle_existing_callbacks(update, context)
            
    except Exception as e:
        logger.error(f"Callback error: {e}")
        await query.answer("❌ An error occurred")

async def create_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create main menu with working buttons"""
    buttons = [
        {'text': '📱 Social Links', 'callback_data': 'social_menu'},
        {'text': '📢 Channel', 'callback_data': 'menu_channel'},
        {'text': '💬 Contact Admin', 'callback_data': 'action_contact'},
        {'text': '❓ Help', 'callback_data': 'menu_help'}
    ]
    
    await button_handler.send_menu_message(
        update,
        context,
        "🌟 Welcome to EmamuTalks! What would you like to do?",
        buttons
    )

async def handle_social_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle social media buttons"""
    query = update.callback_query
    
    social_buttons = [
        {'text': '📸 Instagram', 'callback_data': 'social_instagram'},
        {'text': '🐦 Twitter', 'callback_data': 'social_twitter'},
        {'text': '🔙 Back', 'callback_data': 'menu_main'}
    ]
    
    await button_handler.update_menu(
        update,
        context,
        query.message.message_id,
        "Choose a social media platform:",
        social_buttons
    )

async def handle_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle menu navigation buttons"""
    query = update.callback_query
    menu_type = query.data.split('_')[1]
    
    if menu_type == 'main':
        # Return to main menu
        buttons = [
            {'text': '📱 Social Links', 'callback_data': 'social_menu'},
            {'text': '📢 Channel', 'callback_data': 'menu_channel'},
            {'text': '💬 Contact Admin', 'callback_data': 'action_contact'},
            {'text': '❓ Help', 'callback_data': 'menu_help'}
        ]
        await button_handler.update_menu(
            update,
            context,
            query.message.message_id,
            config.MENU_MESSAGES['MAIN_MENU'],
            buttons
        )
        
    elif menu_type == 'channel':
        # Show channel menu
        buttons = [
            {'text': '📢 Main Channel', 'callback_data': 'action_join_main'},
            {'text': '💭 Discussion Group', 'callback_data': 'action_join_group'},
            {'text': '🔙 Back', 'callback_data': 'menu_main'}
        ]
        await button_handler.update_menu(
            update,
            context,
            query.message.message_id,
            config.MENU_MESSAGES['CHANNEL_MENU'],
            buttons
        )
        
    elif menu_type == 'help':
        # Show help menu
        buttons = [
            {'text': '📖 Commands', 'callback_data': 'action_commands'},
            {'text': '❓ FAQ', 'callback_data': 'action_faq'},
            {'text': '👤 Support', 'callback_data': 'action_support'},
            {'text': '🔙 Back', 'callback_data': 'menu_main'}
        ]
        await button_handler.update_menu(
            update,
            context,
            query.message.message_id,
            config.MENU_MESSAGES['HELP_MENU'],
            buttons
        )

async def handle_action_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle action buttons"""
    query = update.callback_query
    action = query.data.split('_')[1]
    
    if action == 'contact':
        await query.message.reply_text(
            "To contact admin, please send your message here.\n"
            "An admin will respond as soon as possible."
        )
        
    elif action == 'join_main':
        await query.message.reply_text(
            f"Join our main channel:\n{config.CHANNEL_INVITE_LINK}"
        )
        
    elif action == 'join_group':
        await query.message.reply_text(
            f"Join our discussion group:\n{config.GROUP_INVITE_LINK}"
        )
        
    elif action == 'commands':
        await query.message.reply_text(
            "Available commands:\n"
            "/start - Start the bot\n"
            "/help - Show this help message\n"
            "/menu - Show main menu"
        )
        
    elif action == 'faq':
        await query.message.reply_text(
            "Frequently Asked Questions:\n"
            "1. How to join channel?\n"
            "2. How to contact admin?\n"
            "3. How to use bot features?"
        )
        
    elif action == 'support':
        await query.message.reply_text(
            "For support, please contact:\n"
            "@AdminUsername"
        )

async def handle_existing_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle other existing callback queries"""
    query = update.callback_query
    
    if query.data.startswith("check_membership"):
        await membership_checker.handle_callback_query(update, context)
    elif query.data.startswith(("approve_leave_", "deny_leave_")):
        await leave_handler.handle_admin_decision(update, context)
    elif query.data.startswith("migrate_"):
        await migration_callback(update, context)

async def process_group_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /process_group command"""
    if str(update.effective_user.id) not in config.ADMIN_IDS:
        await update.message.reply_text("⚠️ This command is only for administrators")
        return
        
    if update.effective_chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("⚠️ This command only works in groups")
        return
        
    await group_manager.start_member_processing(update, context)

async def handle_collect_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /collect_contacts command"""
    await contact_manager.start_contact_collection(update, context)

async def generate_log_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /log_report command"""
    if str(update.effective_user.id) not in config.ADMIN_IDS:
        return
        
    report = await comm_logger.generate_log_report()
    await update.message.reply_text(report)

async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process message after all checks pass"""
    try:
        message = update.message
        user_id = str(update.effective_user.id)
        
        # Log message processing
        logger.info(f"Processing message from user {user_id}")
        
        # Handle different message types
        if message.text:
            await handle_text_message(update, context)
        elif message.photo:
            await handle_photo_message(update, context)
        elif message.video:
            await handle_video_message(update, context)
        elif message.document:
            await handle_document_message(update, context)
        else:
            await message.reply_text(
                "✅ Message received and processed."
            )
            
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await update.message.reply_text(
            "❌ Error processing your message. Please try again."
        )

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    message = update.message
    await message.reply_text(
        "✅ Your message has been processed."
    )

async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages"""
    message = update.message
    await message.reply_text(
        "✅ Photo received and processed."
    )

async def handle_video_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle video messages"""
    message = update.message
    await message.reply_text(
        "✅ Video received and processed."
    )

async def handle_document_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document messages"""
    message = update.message
    await message.reply_text(
        "✅ Document received and processed."
    )

async def main():
    """Start the bot with multiple sessions"""
    try:
        # Initialize all sessions
        await session_manager.initialize_sessions()
        
        # Add handlers to each session
        for application in session_manager.active_sessions.values():
            application.add_handler(MessageHandler(
                filters.ALL & ~filters.COMMAND, 
                handle_message
            ))
            
        # Add handlers
        application.add_handler(CommandHandler(
            "collect_contacts", 
            handle_collect_contacts
        ))
        application.add_handler(CallbackQueryHandler(
            contact_manager.add_contact_to_group,
            pattern="^add_contact_"
        ))
        application.add_handler(CommandHandler("log_report", generate_log_report))
            
        # Add button handler
        application.add_handler(CallbackQueryHandler(button_handler.handle_callback))
        
        # Add command for showing main menu
        application.add_handler(CommandHandler("start", button_handler.show_main_menu))
            
        # Add command for scanning groups
        application.add_handler(CommandHandler(
            "scan_groups",
            content_sharing.scan_groups
        ))
            
        # Start all sessions
        await session_manager.start_all_sessions()
        
        # Keep the bot running
        await asyncio.Event().wait()
        
    except KeyboardInterrupt:
        # Stop all sessions on interrupt
        await session_manager.stop_all_sessions()
        
    except Exception as e:
        logger.error(f"Main error: {e}")

if __name__ == '__main__':
    asyncio.run(main())