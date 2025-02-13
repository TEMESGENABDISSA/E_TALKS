import os
from dotenv import load_dotenv
from pathlib import Path
import sys
import codecs
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import logging

load_dotenv()

# Set UTF-8 encoding for stdout
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)

# Telegram Bot Configuration
BOT_TOKEN = "#"  # Replace with your bot token
PRIVATE_CHANNEL_ID = "#"  # Replace with your private channel ID
ADMIN_ID = "#"  # Replace with your admin ID

# Bot Status
IS_ADMIN_ONLINE = False

# Social Media Links
SOCIAL_LINKS = {
    "LinkedIn": "https://linkedin.com/in/#",
    "Channel": "https://t.me/#",
    "Group": "https://t.me/#",
    "YouTube": "https://youtube.com/#",
    "Gmail": "#@gmail.com"
}

def get_social_links_keyboard():
    """Create keyboard markup for social links"""
    keyboard = []
    row = []
    
    for platform, url in SOCIAL_LINKS.items():
        if len(row) == 2:  # Max 2 buttons per row
            keyboard.append(row)
            row = []
            
        if platform == "Gmail":
            # Special handling for email
            button = InlineKeyboardButton(
                f"{platform} 📧", 
                callback_data=f"email_{url}"
            )
        else:
            button = InlineKeyboardButton(
                f"{platform} 🔗", 
                url=url
            )
        row.append(button)
        
    if row:  # Add remaining buttons
        keyboard.append(row)
        
    # Add back button
    keyboard.append([
        InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")
    ])
    
    return InlineKeyboardMarkup(keyboard)

# Auto reply message
OFFLINE_MESSAGE = (
    "\n\n\n\nThanks for your message! I will reach out to you soon.\n\n\n\n"
    "In the meantime, feel free to connect with us:\n\n"
    "📢 Telegram Channel: https://t.me/#\n"
    "💭 Telegram Group: https://t.me/#\n \n\n"
    " \n\nStay tuned for more updates! 🌟"
)

# Feature flags
WELCOME_MESSAGE_ENABLED = True
CONTENT_MODERATION_ENABLED = True

# Moderation messages
BLOCKED_USER_MESSAGE = "Sorry, you have been blocked due to inappropriate content."
INAPPROPRIATE_CONTENT_MESSAGE = "Your message has been flagged as inappropriate. You have been blocked from using this bot."

# Base directory for assets
BASE_DIR = Path(__file__).resolve().parent

# Add profile information
ABOUT_PERSON = {
    "name": "##",  # Changed from "Temesgen Abdissa"
    "profession": "#",
    "bio": "#",
    "expertise": "#"
}

# Group Migration Settings
SOURCE_GROUP_ID = "#"  # Replace with your source group ID
TARGET_GROUP_ID = "#"  # Replace with your target group ID
CHANNEL_INVITE_LINK = "https://t.me/#"

# Rate limiting settings
ADD_MEMBER_DELAY = 5  # seconds between each add
MAX_ADDS_PER_HOUR = 50
BATCH_SIZE = 10  # number of members to process in one batch

# Messages
CONSENT_MESSAGE = """
🔔 Important Notice:
We're migrating members to our new group. By clicking "Accept", you agree to:
- Share your contact info
- Be added to the new group
- Receive updates from our channel

Do you consent?
"""

# Channel and Group Settings
REQUIRED_CHANNEL_ID = "#"  # Replace with your channel ID
PRIVATE_CHANNEL_ID = "#"  # Replace with your private channel ID
GROUP_ID = "#"  # Replace with your group ID

# Multiple Admin IDs
ADMIN_IDS = [
    "#",  # Admin 1 ID
    "#",  # Admin 2 ID
    "#",  # Admin 3 ID
    "#"   # Admin 4 ID
]

# Messages
JOIN_REQUEST_MESSAGE = (
    "👋 Welcome! To continue, please:\n"
    "1️⃣ Join our channel: @#\n"
    "2️⃣ Click 'Check Membership' below"
)

LEAVE_REQUEST_MESSAGE = (
    "❗️ Before you leave:\n"
    "1. Please tell us why you're leaving\n"
    "2. Wait for admin approval\n\n"
    "Your feedback helps us improve!"
)

# Invitation links
GROUP_INVITE_LINK = "https://t.me/#"  # Get from group settings

# Feature flags
REQUIRE_CHANNEL_JOIN = True
REQUIRE_JOIN_REQUEST = True
TRACK_LEAVE_REQUESTS = True

# Add these to your existing config.py
REQUIRED_CHANNEL_USERNAME = "@#"  # Your channel username

JOIN_MESSAGES = {
    "NOT_MEMBER": (
        "👋 Welcome! Before we continue, please:\n\n"
        "1️⃣ Join our channel: {channel_link}\n"
        "2️⃣ Click 'Check Membership' below\n\n"
        "This helps us keep you updated with the latest news!"
    ),
    "VERIFIED": "✅ Thank you for joining! You can now send messages.",
    "STILL_NOT_MEMBER": "❌ Please join our channel first to continue."
}

# Add these to your config.py
JOIN_REQUEST_SETTINGS = {
    "ENABLED": True,
    "WELCOME_MESSAGE": (
        "👋 Welcome to #!\n\n"
        "Before you can message the admin, please:\n"
        "1️⃣ Join our channel: @#\n"
        "2️⃣ Submit a brief introduction\n"
        "3️⃣ Wait for approval\n\n"
        "This helps us maintain a quality community!"
    ),
    "INTRO_PROMPT": (
        "Please tell us about yourself:\n\n"
        "• Your name\n"
        "• Your interests\n"
        "• How you found us\n"
        "• What you'd like to discuss"
    ),
    "PENDING_MESSAGE": "✍️ Your join request is being reviewed. We'll notify you once approved!",
    "APPROVED_MESSAGE": "✅ Your join request has been approved! You can now send messages.",
    "REJECTED_MESSAGE": "❌ Your join request was not approved at this time."
}

# Store approved user IDs (you might want to move this to a database later)
APPROVED_USERS = set()

# Group Management Settings
GROUP_SETTINGS = {
    "BATCH_SIZE": 10,  # Number of members to process at once
    "DELAY": 2,  # Seconds between batches
    "MAX_RETRIES": 3,  # Maximum retry attempts per user
}

# Messages
GROUP_MESSAGES = {
    "INVITE": (
        "👋 Hello {name}!\n\n"
        "You're invited to join our channel:\n"
        "{channel_link}\n\n"
        "Join us for exclusive content and updates!"
    ),
    "PROCESSING": "🔄 Processing members...\n Progress: {progress}%",
    "COMPLETE": (
        "✅ Processing complete!\n\n"
        "📊 Results:\n"
        "• Total processed: {total}\n"
        "• Successfully added: {added}\n"
        "• Invites sent: {invited}\n"
        "• Failed: {failed}"
    )
}

# Leave Request Settings
LEAVE_REQUEST_SETTINGS = {
    "ENABLED": True,
    "REQUIRE_REASON": True,
    "MIN_REASON_LENGTH": 10,
    "COOLDOWN_HOURS": 24,  # Hours between requests
    "AUTO_REMOVE_AFTER_APPROVAL": True
}

# Messages for leave requests
LEAVE_MESSAGES = {
    "REQUEST_RECEIVED": (
        "Your leave request has been submitted.\n"
        "Please wait for admin approval.\n"
        "You will be notified of the decision."
    ),
    "ALREADY_PENDING": (
        "You already have a pending leave request.\n"
        "Please wait for admin approval."
    ),
    "APPROVED": (
        "✅ Your leave request has been approved.\n"
        "Thank you for being part of our community!\n"
        "You're welcome back anytime:\n"
        "{invite_link}"
    ),
    "DENIED": (
        "❌ Your leave request has been denied.\n"
        "An admin will contact you soon to discuss your concerns."
    )
}

# Button Configurations
BUTTON_SETTINGS = {
    'MAX_BUTTONS_PER_ROW': 2,
    'CALLBACK_TIMEOUT': 30,  # seconds
    'MENU_TIMEOUT': 3600,    # 1 hour
}

# Menu Configurations
MENU_MESSAGES = {
    'MAIN_MENU': "🌟 Welcome to #! What would you like to do?",
    'SOCIAL_MENU': "Choose a social media platform:",
    'CHANNEL_MENU': "Join our channels:",
    'HELP_MENU': "How can we help you?"
}

# Button Labels
BUTTON_LABELS = {
    'SOCIAL': '📱 Social Links',
    'CHANNEL': '📢 Channel',
    'CONTACT': '💬 Contact Admin',
    'HELP': '❓ Help',
    'BACK': '🔙 Back'
}

# Add these migration settings to your config.py

# Migration Messages
INVITE_MESSAGE = (
    "👋 Hello!\n\n"
    "You're invited to join our group:\n"
    "{invite_link}\n\n"
    "Looking forward to seeing you there!"
)

# Migration Settings
MIGRATION_SETTINGS = {
    'BATCH_SIZE': 10,        # Number of users to process at once
    'DELAY': 2,             # Seconds between batches
    'MAX_RETRIES': 3,       # Maximum retry attempts
    'TIMEOUT': 30,          # Seconds to wait for response
}

# Content Moderation Settings
MODERATION_SETTINGS = {
    'ENABLED': True,
    'MAX_VIOLATIONS': 3,
    'BLOCK_DURATION': 24 * 60 * 60  # 24 hours in seconds
}

# Content Detection Thresholds
PROFANITY_THRESHOLD = 0.8
IMAGE_THRESHOLD = 0.85

# Banned Content
BANNED_WORDS = [
    'porn',
    'xxx',
    # Add more banned words...
]

BANNED_IMAGE_CLASSES = [
    'NUDE',
    'PORN',
    'SEXY',
    # Add more banned classes...
]

# Admin Channel for Violations
ADMIN_CHANNEL_ID = "your_admin_channel_id_here"  # Replace with your admin channel ID

# Moderation Messages
MODERATION_MESSAGES = {
    'CONTENT_REMOVED': "⚠️ Your message was removed due to inappropriate content.",
    'USER_BLOCKED': "🚫 You have been blocked due to violation of our content policy.",
    'ADMIN_NOTIFICATION': (
        "🚫 Content Violation\n"
        "User: {user}\n"
        "Type: {type}\n"
        "Confidence: {confidence}\n"
        "Action: {action}"
    )
}

# Channel Requirements
REQUIRED_CHANNELS = [
    "#",  # Main channel ID
    "#"   # Secondary channel ID
]

CHANNEL_INFO = {
    "main": {
        "id": "#",
        "name": "#",
        "username": "#",
        "invite_link": "#"
    }
}

# Private Channel
PRIVATE_CHANNEL_ID = "#"  # Private logging channel ID

# Multi-User Support
USER_TOKENS = {
    "user1": "#",  # Replace with actual bot token
    "user2": "#",  # Replace with actual bot token
    "user3": "#"   # Replace with actual bot token
}

# Messages
MESSAGES = {
    'JOIN_REQUIRED': (
        "👋 Welcome! Please join {channel_name} to continue.\n\n"
        "1️⃣ Click 'Join Channel' below\n"
        "2️⃣ Then click 'Check Membership'\n\n"
        "This helps you stay updated with our latest content!"
    ),
    'NOT_MEMBER': "❌ Please join the channel first to continue.",
    'MEMBERSHIP_CONFIRMED': "✅ Thank you for joining! You can now send messages."
}

# Add these consent settings to your config.py

CONSENT_VERSION = "1.0"

CONSENT_TYPES = {
    'contact_save': 'Contact Information Storage',
    'content_analysis': 'Content Analysis',
    'group_add': 'Group Addition',
    'data_processing': 'Data Processing'
}

CONSENT_MESSAGES = {
    'contact_save': (
        "📱 Contact Storage Consent\n\n"
        "We'd like to store your contact information to:\n"
        "• Enable admin messaging\n"
        "• Send important updates\n"
        "• Manage group memberships\n\n"
        "Your data will be handled according to our privacy policy."
    ),
    'content_analysis': (
        "🔍 Content Analysis Consent\n\n"
        "We analyze message content to:\n"
        "• Maintain community standards\n"
        "• Prevent inappropriate content\n"
        "• Improve user experience\n\n"
        "No personal data is stored during analysis."
    ),
    'group_add': (
        "👥 Group Addition Consent\n\n"
        "We'd like to:\n"
        "• Add you to related groups\n"
        "• Send channel invitations\n"
        "• Share community updates\n\n"
        "You can leave groups at any time."
    ),
    'data_processing': (
        "📊 Data Processing Consent\n\n"
        "We process your data to:\n"
        "• Improve bot functionality\n"
        "• Customize your experience\n"
        "• Send relevant updates\n\n"
        "Your privacy is our priority."
    )
}

CONSENT_RESPONSES = {
    'yes': "✅ Thank you for your consent. You can proceed now.",
    'no': "❌ You've declined. Some features may be limited."
}

# Privacy Settings
PRIVACY_SETTINGS = {
    'DATA_RETENTION_DAYS': 30,
    'MAX_STORED_MESSAGES': 1000,
    'REQUIRE_CONSENT': True,
    'ALLOW_ANALYTICS': False
}

# Your Channel and Group Settings
GROUP_INFO = {
    "main": {
        "id": "#",
        "name": "#",
        "invite_link": "#"
    }
}

# Required Channel for Membership
REQUIRED_CHANNELS = [
    "#"  # Replace with your channel ID
]

# Private Channel for Forwarded Messages
PRIVATE_CHANNEL_ID = "#"  # Replace with your private channel ID

# Admin Settings
ADMIN_IDS = [
    "#"  # Replace with your Telegram user ID
]

# Bot Token
BOT_TOKEN = "#"  # Replace with your bot token

# Add these membership settings to your config.py

MEMBERSHIP_SETTINGS = {
    'MIN_DURATION_DAYS': 180,  # 6 months
    'GRACE_PERIOD_DAYS': 7,    # Warning period before forced removal
    'NOTIFY_BEFORE_DAYS': 14   # Days before minimum duration to notify user
}

# Membership Messages
MEMBERSHIP_MESSAGES = {
    'JOIN_WELCOME': (
        "👋 Welcome to our channel!\n\n"
        "Please note:\n"
        "• Minimum membership duration: 6 months\n"
        "• Admin approval required to leave\n"
        "• Use /leave to request departure"
    ),
    'DURATION_WARNING': (
        "⚠️ Minimum Duration Notice\n\n"
        "You must remain a member for at least 6 months.\n"
        "Time remaining: {days_left} days"
    ),
    'LEAVE_REQUEST': (
        "📝 Leave Request Process:\n\n"
        "1. Check eligibility (/check_eligibility)\n"
        "2. Submit request (/leave)\n"
        "3. Wait for admin approval"
    )
}

# Add these contact management settings to your config.py

# Admin IDs (replace with actual admin IDs)
ADMIN_IDS = [
     "#",  # Admin 1 ID
    "#",  # Admin 2 ID
    "#",  # Admin 3 ID
    "#"   # Admin 4 ID
]

# Group Settings
TARGET_GROUP_ID = "#"  # Replace with your target group ID
GROUP_INVITE_LINK = "https://t.me/#"

# Contact Collection Settings
CONTACT_SETTINGS = {
    'BATCH_SIZE': 50,        # Number of contacts to process at once
    'RATE_LIMIT': 0.5,       # Seconds between operations
    'MAX_RETRIES': 3,        # Maximum retry attempts
    'PRIVACY_CHECK': True    # Whether to check privacy settings
}

# Contact Messages
CONTACT_MESSAGES = {
    'COLLECTION_START': "🔄 Starting contact collection...",
    'COLLECTION_PROGRESS': (
        "Progress: {current}/{total}\n"
        "✅ Added: {added}\n"
        "📨 Invited: {invited}\n"
        "❌ Failed: {failed}"
    ),
    'COLLECTION_COMPLETE': (
        "✅ Contact collection complete!\n\n"
        "📊 Results:\n"
        "• Total: {total}\n"
        "• Added: {added}\n"
        "• Invited: {invited}\n"
        "• Failed: {failed}"
    ),
    'INVITE_MESSAGE': (
        "👋 Hello!\n\n"
        "You're invited to join our group:\n"
        "{invite_link}\n\n"
        "Looking forward to seeing you there!"
    )
}

# Add these logging settings to your config.py

# Logging Channels
ADMIN_LOG_CHANNEL_ID = "-1002384506961"  # Admin notifications channel ID

# Logging Settings
LOG_SETTINGS = {
    'DETAILED_LOGS': True,
    'LOG_RETENTION_DAYS': 30,
    'NOTIFY_ADMINS': True,
    'LOG_LEVEL': 'INFO'
}

# Log Messages
LOG_MESSAGES = {
    'ATTEMPT_BLOCKED': (
        "⚠️ Communication Attempt Blocked\n"
        "User: {username}\n"
        "Reason: Not a channel member"
    ),
    'ATTEMPT_ALLOWED': (
        "✅ Communication Attempt Allowed\n"
        "User: {username}"
    ),
    'MEMBER_JOINED': (
        "👋 New Member Joined\n"
        "User: {username}\n"
        "Can now communicate with admins"
    )
}

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent

# File paths
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)  # Create data directory if it doesn't exist

# File paths for JSON storage
CONSENTS_FILE = DATA_DIR / "user_consents.json"
STATES_FILE = DATA_DIR / "user_states.json"
MESSAGES_FILE = DATA_DIR / "forwarded_messages.json"

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Make sure to set this in your environment
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]
CHANNEL_ID = os.getenv("CHANNEL_ID")

# Consent configuration
CONSENT_VERSION = "1.0"
CONSENT_MESSAGES = {
    "data_processing": (
        "To use this bot, we need your consent to process and store your data. "
        "This includes your messages and user information. Do you agree?"
    ),
    "channel_join": (
        "To continue using this bot, you need to join our channel. "
        "Do you agree to join?"
    )
}

CONSENT_RESPONSES = {
    "yes": "Thank you for your consent! You can now use the bot.",
    "no": "Without consent, we cannot provide our services. "
           "You can try again later using /start"
}

# Channel configuration
CHANNEL_INFO = {
    "main": {
        "id": CHANNEL_ID,
        "name": "#",
        "username": "#",
        "invite_link": "#"
    }
}

REQUIRED_CHANNELS = ["main"]

# Initialize logging
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "bot.log"),
        logging.StreamHandler()
    ]
)

# Bot tokens configuration
BOT_TOKENS = {
    "user1": os.getenv("BOT_TOKEN_1"),
    "user2": os.getenv("BOT_TOKEN_2"),
    "user3": os.getenv("BOT_TOKEN_3")
}

# Validate tokens
def validate_tokens():
    invalid_tokens = []
    for user, token in BOT_TOKENS.items():
        if not token or len(token.split(':')) != 2:
            invalid_tokens.append(user)
    return invalid_tokens

WELCOME_MESSAGE = """
Welcome to #! 
Join our community:
Channel: @#
Group: @#
YouTube: #
"""

ABOUT_CHANNEL = """
# - Your Source for Tech Knowledge
Join us on:
📢 Channel: @#
💭 Group: @#
📺 YouTube: #
"""