import re
from typing import Union, Tuple, Optional
from telegram import Message, Update, InlineKeyboardButton, InlineKeyboardMarkup
import requests
from PIL import Image
from io import BytesIO
import logging
from nudenet import NudeDetector
import spacy
from telegram.ext import ContextTypes
from telegram.error import TelegramError
import asyncio
import aiohttp
import io
import numpy as np
import os
from better_profanity import profanity
import config
from pathlib import Path

class ContentModerator:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.banned_words = set()
        self.max_message_length = 1000
        self.nude_detector = None
        
        # Try to initialize nude detector if available
        try:
            from nudenet import NudeDetector
            self.nude_detector = NudeDetector()
            self.logger.info("NudeDetector initialized successfully")
        except Exception as e:
            self.logger.warning(f"NudeDetector initialization failed: {e}")
            self.logger.info("Running without image moderation")
        
        # Load spaCy model for text analysis
        self.nlp = spacy.load("en_core_web_sm")
        
        # Initialize profanity filter
        profanity.load_censor_words()
        
        # Enhanced patterns
        self.inappropriate_patterns = [
            r'(?i)(porn|xxx|sex|nude|adult|18\+|onlyfans)',
            r'(?i)(escort|prostitute|dating|hookup)',
            r'(?i)(cocaine|heroin|drug|weed|meth)',
            r'(?i)(gambling|casino|bet|lottery)',
            r'(?i)(fuck|shit|dick|ass|bitch|pussy)',
        ]

        self.spam_patterns = [
            r'(?i)(buy|sell|cheap|discount|offer|limited)',
            r'(?i)(win|prize|lottery|lucky|selected)',
            r'(?i)(crypto|bitcoin|eth|investment|profit)',
        ]

        self.blocked_users = set()
        self.load_blocked_users()

    def load_blocked_users(self):
        """Load previously blocked users"""
        try:
            with open('data/blocked_users.txt', 'r', encoding='utf-8') as f:
                self.blocked_users = set()
                for line in f:
                    try:
                        user_id = line.strip()
                        if user_id:  # Skip empty lines
                            self.blocked_users.add(int(user_id))
                    except ValueError:
                        self.logger.warning(f"Invalid user ID in blocked_users.txt: {line.strip()}")
        except FileNotFoundError:
            self.blocked_users = set()
            # Create the file if it doesn't exist
            os.makedirs('data', exist_ok=True)
            with open('data/blocked_users.txt', 'w', encoding='utf-8') as f:
                pass
        except Exception as e:
            self.logger.error(f"Error loading blocked users: {e}")
            self.blocked_users = set()
            
    def save_blocked_users(self):
        """Save blocked users to file"""
        try:
            os.makedirs('data', exist_ok=True)
            with open('data/blocked_users.txt', 'w', encoding='utf-8') as f:
                for user_id in self.blocked_users:
                    f.write(f"{user_id}\n")
        except Exception as e:
            self.logger.error(f"Error saving blocked users: {e}")
            
    async def analyze_media(self, message: Message) -> Tuple[bool, str]:
        """Analyze media content for inappropriate material"""
        try:
            if message.photo:
                file = await message.photo[-1].get_file()
                photo_path = await file.download_to_memory()
                
                # Analyze with NudeNet
                result = self.nude_detector.detect(photo_path, min_prob=0.6)
                if len(result) > 0:  # If any inappropriate content is detected
                    return True, "inappropriate_media"

            elif message.video or message.animation:
                # For videos/GIFs, analyze thumbnail
                if message.video:
                    thumb = message.video.thumb
                elif message.animation:
                    thumb = message.animation.thumb
                    
                if thumb:
                    file = await thumb.get_file()
                    thumb_path = await file.download_to_memory()
                    result = self.nude_detector.detect(thumb_path, min_prob=0.6)
                    if len(result) > 0:  # If any inappropriate content is detected
                        return True, "inappropriate_media"

        except Exception as e:
            self.logger.error(f"Media analysis error: {e}")
            return False, ""

        return False, ""

    def analyze_text(self, text: str) -> Tuple[bool, str]:
        """Enhanced text analysis using spaCy and patterns"""
        if not text:
            return False, ""

        # SpaCy analysis for context
        doc = self.nlp(text)
        
        # Check for sexual content in context
        sexual_terms = ['sex', 'nude', 'porn', 'xxx']
        if any(token.text.lower() in sexual_terms for token in doc):
            return True, "sexual_content"

        # Check patterns
        for pattern in self.inappropriate_patterns:
            if re.search(pattern, text):
                return True, "inappropriate_content"

        # Check for spam
        spam_count = 0
        for pattern in self.spam_patterns:
            if re.search(pattern, text):
                spam_count += 1
        if spam_count >= 2:  # Require multiple matches for spam
            return True, "spam"

        return False, ""

    async def should_block_message(self, message: Message) -> Tuple[bool, str]:
        """Enhanced message analysis"""
        try:
            # Check text content
            if message.text:
                is_inappropriate, reason = self.analyze_text(message.text)
                if is_inappropriate:
                    return True, reason

            # Check media content
            if message.photo or message.video or message.animation:
                is_inappropriate, reason = await self.analyze_media(message)
                if is_inappropriate:
                    return True, reason

                # Check media captions
                if message.caption:
                    is_inappropriate, reason = self.analyze_text(message.caption)
                    if is_inappropriate:
                        return True, reason

            # Check documents
            if message.document:
                if message.document.mime_type:
                    if 'image' in message.document.mime_type or 'video' in message.document.mime_type:
                        # Check filename for inappropriate content
                        if message.document.file_name:
                            is_inappropriate, reason = self.analyze_text(message.document.file_name)
                            if is_inappropriate:
                                return True, reason

        except Exception as e:
            self.logger.error(f"Content moderation error: {e}")
            return False, "error"

        return False, ""

    async def check_text_content(self, text: str) -> tuple:
        """Check text for inappropriate content"""
        try:
            # Check for profanity
            if profanity.contains_profanity(text):
                return True, "Text contains profanity"
            
            # Check against banned words
            contains_banned = any(word in text.lower() 
                                for word in config.BANNED_WORDS)
            
            is_inappropriate = contains_banned
            
            return is_inappropriate, {
                'contains_banned_words': contains_banned,
                'text': text[:100] + '...' if len(text) > 100 else text
            }
            
        except Exception as e:
            self.logger.error(f"Text analysis error: {e}")
            return False, {'error': str(e)}
            
    async def check_image_content(self, image_data: Union[str, bytes]) -> Tuple[bool, dict]:
        """Check image for inappropriate content"""
        try:
            # Convert image data to PIL Image if it's bytes
            if isinstance(image_data, bytes):
                image = Image.open(BytesIO(image_data))
                # Convert to RGB if necessary
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                # Save to temporary buffer
                buffer = BytesIO()
                image.save(buffer, format='JPEG')
                image_data = buffer.getvalue()
            
            # Detect nudity
            result = self.nude_detector.detect(image_data, min_prob=0.6)
            
            is_inappropriate = len(result) > 0  # If any inappropriate content is detected
            
            return is_inappropriate, {
                'detections': result,
                'message': 'Inappropriate content detected' if is_inappropriate else 'No inappropriate content detected'
            }
            
        except Exception as e:
            logging.error(f"Error checking image content: {str(e)}")
            return True, {'error': str(e)}  # Fail closed - treat errors as inappropriate content
            
    async def forward_to_admin(self, 
                             update: Update, 
                             context: ContextTypes.DEFAULT_TYPE,
                             violation_info: dict):
        """Forward violating content to admin channel"""
        try:
            user = update.effective_user
            message = update.message
            
            # Create admin notification
            admin_text = (
                f"🚫 Content Violation\n\n"
                f"User: {user.first_name} (@{user.username})\n"
                f"ID: {user.id}\n"
                f"Type: {violation_info['type']}\n"
                f"Confidence: {violation_info.get('confidence', 'N/A')}\n\n"
                f"Details: {violation_info.get('details', 'No details available')}"
            )
            
            # Forward message silently
            await message.forward(
                chat_id=config.ADMIN_CHANNEL_ID,
                disable_notification=True
            )
            
            # Send violation details
            await context.bot.send_message(
                chat_id=config.ADMIN_CHANNEL_ID,
                text=admin_text,
                disable_notification=True
            )
            
        except Exception as e:
            self.logger.error(f"Forward to admin error: {e}")
            
    async def block_user(self, 
                        update: Update, 
                        context: ContextTypes.DEFAULT_TYPE,
                        reason: str):
        """Block user and handle cleanup"""
        try:
            user_id = update.effective_user.id
            
            if user_id in self.blocked_users:
                return
                
            # Block user
            await context.bot.ban_chat_member(
                chat_id=update.effective_chat.id,
                user_id=user_id,
                revoke_messages=True
            )
            
            # Add to blocked set
            self.blocked_users.add(user_id)
            self.save_blocked_users()
            
            # Notify admins
            await context.bot.send_message(
                chat_id=config.ADMIN_CHANNEL_ID,
                text=(
                    f"🚫 User Blocked\n"
                    f"ID: {user_id}\n"
                    f"Reason: {reason}"
                ),
                disable_notification=True
            )
            
        except Exception as e:
            self.logger.error(f"Block user error: {e}")
            
    async def moderate_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Main moderation function"""
        try:
            message = update.message
            user_id = update.effective_user.id
            
            # Skip if user already blocked
            if user_id in self.blocked_users:
                return True
                
            violation_info = {
                'type': None,
                'confidence': None,
                'details': None
            }
            
            # Check text content
            if message.text or message.caption:
                text = message.text or message.caption
                is_inappropriate, text_info = await self.check_text_content(text)
                
                if is_inappropriate:
                    violation_info.update({
                        'type': 'text',
                        'confidence': text_info['probability'],
                        'details': text_info
                    })
                    
            # Check image content
            if message.photo:
                photo_file = await message.photo[-1].get_file()
                photo_bytes = await photo_file.download_as_bytearray()
                
                is_inappropriate, image_info = await self.check_image_content(
                    io.BytesIO(photo_bytes)
                )
                
                if is_inappropriate:
                    violation_info.update({
                        'type': 'image',
                        'confidence': max(d['score'] for d in image_info['detections']),
                        'details': image_info
                    })
                    
            # Handle violation if found
            if violation_info['type']:
                await self.forward_to_admin(update, context, violation_info)
                await self.block_user(
                    update, 
                    context, 
                    f"Inappropriate {violation_info['type']} content"
                )
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Moderation error: {e}")
            return False

    async def check_content(self, update, context) -> Tuple[bool, str]:
        """Check if content is appropriate"""
        try:
            # Check text content
            if update.message.text:
                return await self.check_text(update.message.text)
                
            # Check image content
            elif update.message.photo and self.nude_detector:
                return await self.check_image(update.message.photo[-1], context)
                
            # Allow other content types
            return True, ""
            
        except Exception as e:
            self.logger.error(f"Error in content check: {e}")
            return True, ""  # Allow content if check fails

    async def check_text(self, text: str) -> Tuple[bool, str]:
        """Check if text content is appropriate"""
        if not text:
            return True, ""

        # Check message length
        if len(text) > self.max_message_length:
            return False, "Message too long"

        # Check for banned words
        text_lower = text.lower()
        for word in self.banned_words:
            if word in text_lower:
                return False, "Contains inappropriate content"

        return True, ""

    async def check_image(self, photo, context) -> Tuple[bool, str]:
        """Check if image content is appropriate"""
        if not self.nude_detector:
            return True, "Image moderation disabled"
            
        try:
            # Download photo
            file = await context.bot.get_file(photo.file_id)
            photo_path = Path(f"temp_{photo.file_id}.jpg")
            await file.download_to_drive(photo_path)

            # Check image
            result = self.nude_detector.detect(str(photo_path))
            
            # Clean up
            photo_path.unlink(missing_ok=True)

            # Check results
            if result and any(pred['score'] > 0.6 for pred in result):
                return False, "Inappropriate image content detected"

            return True, ""

        except Exception as e:
            self.logger.error(f"Image check error: {e}")
            return True, "Image check failed"
        finally:
            # Ensure cleanup
            if photo_path.exists():
                photo_path.unlink()

    def load_banned_words(self, filename: str):
        """Load banned words from file"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                self.banned_words = set(word.strip().lower() for word in f)
        except Exception as e:
            self.logger.error(f"Error loading banned words: {e}")

    async def check_message(self, text: str) -> Tuple[bool, str]:
        """
        Check if message content is appropriate
        Returns: (is_appropriate, reason_if_not)
        """
        if not text:
            return False, "Empty message"

        # Check message length
        if len(text) > self.max_message_length:
            return False, "Message too long"

        # Check for banned words
        text_lower = text.lower()
        for word in self.banned_words:
            if word in text_lower:
                return False, "Contains inappropriate content"

        # Check for excessive special characters
        if len(re.findall(r'[!?]{3,}', text)) > 0:
            return False, "Contains excessive punctuation"

        # Check for URLs if not allowed
        if re.search(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text):
            return False, "URLs not allowed"

        return True, ""

    async def filter_message(self, text: str) -> str:
        """Filter inappropriate content from message"""
        if not text:
            return text

        filtered_text = text
        for word in self.banned_words:
            filtered_text = re.sub(
                rf'\b{re.escape(word)}\b', 
                '*' * len(word), 
                filtered_text, 
                flags=re.IGNORECASE
            )
        return filtered_text 