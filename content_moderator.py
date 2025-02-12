import re
from typing import Union, Tuple
from telegram import Message, Update, InlineKeyboardButton, InlineKeyboardMarkup
import requests
from PIL import Image
from io import BytesIO
import logging
from nudenet import NudeClassifier, NudeDetector
import spacy
from telegram.ext import ContextTypes
from telegram.error import TelegramError
import asyncio
import aiohttp
import io
import numpy as np
from profanity_check import predict_prob, predict
import config

class ContentModerator:
    def __init__(self):
        # Initialize NudeNet classifier
        self.nude_classifier = NudeClassifier()
        self.nude_detector = NudeDetector()
        
        # Load spaCy model for text analysis
        self.nlp = spacy.load("en_core_web_sm")
        
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

        # Initialize logging
        self.logger = logging.getLogger(__name__)
        self.blocked_users = set()
        self.load_blocked_users()

    def load_blocked_users(self):
        """Load previously blocked users"""
        try:
            with open('data/blocked_users.txt', 'r') as f:
                self.blocked_users = set(int(line.strip()) for line in f)
        except FileNotFoundError:
            self.blocked_users = set()
            
    def save_blocked_users(self):
        """Save blocked users to file"""
        with open('data/blocked_users.txt', 'w') as f:
            for user_id in self.blocked_users:
                f.write(f"{user_id}\n")

    async def analyze_media(self, message: Message) -> Tuple[bool, str]:
        """Analyze media content for inappropriate material"""
        try:
            if message.photo:
                file = await message.photo[-1].get_file()
                photo_path = await file.download_to_memory()
                
                # Analyze with NudeNet
                result = self.nude_classifier.classify(photo_path)
                if result and result[0]['unsafe'] > 0.7:  # 70% threshold
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
                    result = self.nude_classifier.classify(thumb_path)
                    if result and result[0]['unsafe'] > 0.7:
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
            # Check profanity probability
            prob = predict_prob([text])[0]
            
            # Check against banned words
            contains_banned = any(word in text.lower() 
                                for word in config.BANNED_WORDS)
            
            is_inappropriate = prob > config.PROFANITY_THRESHOLD or contains_banned
            
            return is_inappropriate, {
                'probability': float(prob),
                'contains_banned_words': contains_banned,
                'text': text[:100] + '...' if len(text) > 100 else text
            }
            
        except Exception as e:
            self.logger.error(f"Text analysis error: {e}")
            return False, {'error': str(e)}
            
    async def check_image_content(self, image_file) -> tuple:
        """Check image for inappropriate content"""
        try:
            # Convert to PIL Image
            image = Image.open(image_file)
            
            # Run NudeNet detection
            result = self.nude_detector.detect(image)
            
            # Check if any inappropriate classes are detected
            is_inappropriate = any(
                pred['class'] in config.BANNED_IMAGE_CLASSES and 
                pred['score'] > config.IMAGE_THRESHOLD 
                for pred in result
            )
            
            return is_inappropriate, {
                'detections': result,
                'image_size': image.size
            }
            
        except Exception as e:
            self.logger.error(f"Image analysis error: {e}")
            return False, {'error': str(e)}
            
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

    async def check_content(self, 
                          update: Update, 
                          context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check if content is appropriate"""
        try:
            message = update.message
            
            # Check text content
            if message.text:
                if not await self.check_text(message.text):
                    await self.handle_inappropriate_content(update, context)
                    return False
                    
            # Check media content
            if message.photo or message.video or message.document:
                if not await self.check_media(message):
                    await self.handle_inappropriate_content(update, context)
                    return False
                    
            # Check links
            if message.entities:
                if not await self.check_links(message):
                    await self.handle_inappropriate_content(update, context)
                    return False
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking content: {e}")
            return False
            
    async def check_text(self, text: str) -> bool:
        """Check text content for inappropriate content"""
        try:
            # Check against blocked patterns
            for pattern in self.blocked_patterns:
                if re.search(pattern, text):
                    return False
                    
            # Check for profanity
            if predict([text])[0] == 1:
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking text: {e}")
            return False
            
    async def check_media(self, message) -> bool:
        """Check media content"""
        try:
            if message.photo:
                file = await message.photo[-1].get_file()
                return await self.check_image(file)
                
            if message.video:
                # Implement video checking logic
                return True  # Placeholder
                
            if message.document:
                # Check document type and content
                return await self.check_document(message.document)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking media: {e}")
            return False
            
    async def check_image(self, file) -> bool:
        """Check image content"""
        try:
            # Download image
            file_path = await file.download_to_memory()
            
            # Check for inappropriate content
            result = self.nude_classifier.classify(file_path)
            
            # If unsafe content detected
            if any(score > 0.7 for score in result.values()):
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking image: {e}")
            return False
            
    async def handle_inappropriate_content(self, 
                                        update: Update, 
                                        context: ContextTypes.DEFAULT_TYPE):
        """Handle inappropriate content"""
        try:
            # Delete message if possible
            await update.message.delete()
            
            # Check if user is channel member
            is_member = await self.check_channel_membership(context, update.effective_user.id)
            
            if not is_member:
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "Join Channel 📢",
                            url=config.CHANNEL_INFO[config.REQUIRED_CHANNELS[0]]['invite_link']
                        )
                    ]
                ]
                
                await update.message.reply_text(
                    "⚠️ Your message contains restricted content.\n"
                    "Please join our channel to share content.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await update.message.reply_text(
                    "⚠️ Your message was removed due to inappropriate content.\n"
                    "Please review our content guidelines."
                )
                
        except Exception as e:
            self.logger.error(f"Error handling inappropriate content: {e}")

    async def check_document(self, document):
        """Check document content"""
        # Implement document checking logic
        return True  # Placeholder

    async def check_links(self, message):
        """Check message links"""
        # Implement link checking logic
        return True  # Placeholder

    async def check_channel_membership(self, context, user_id):
        """Check if user is a member of the required channels"""
        # Implement channel membership checking logic
        return True  # Placeholder

    async def handle_inappropriate_content(self, 
                                        update: Update, 
                                        context: ContextTypes.DEFAULT_TYPE):
        """Handle inappropriate content"""
        try:
            # Delete message if possible
            await update.message.delete()
            
            # Check if user is channel member
            is_member = await self.check_channel_membership(context, update.effective_user.id)
            
            if not is_member:
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "Join Channel 📢",
                            url=config.CHANNEL_INFO[config.REQUIRED_CHANNELS[0]]['invite_link']
                        )
                    ]
                ]
                
                await update.message.reply_text(
                    "⚠️ Your message contains restricted content.\n"
                    "Please join our channel to share content.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await update.message.reply_text(
                    "⚠️ Your message was removed due to inappropriate content.\n"
                    "Please review our content guidelines."
                )
                
        except Exception as e:
            self.logger.error(f"Error handling inappropriate content: {e}") 