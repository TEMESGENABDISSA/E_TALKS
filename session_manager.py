from telegram.ext import Application
import logging
from typing import Dict
import config
import aiohttp
import asyncio

class SessionManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.active_sessions: Dict[str, Application] = {}
        
    async def validate_token(self, token: str) -> bool:
        """Validate bot token by making a getMe request"""
        async with aiohttp.ClientSession() as session:
            try:
                url = f"https://api.telegram.org/bot{token}/getMe"
                async with session.get(url) as response:
                    if response.status == 200:
                        return True
                    self.logger.error(f"Token validation failed: {await response.text()}")
                    return False
            except Exception as e:
                self.logger.error(f"Token validation error: {e}")
                return False

    async def initialize_sessions(self):
        """Initialize bot sessions with validation"""
        # Check for invalid tokens first
        invalid_tokens = config.validate_tokens()
        if invalid_tokens:
            self.logger.error(f"Invalid token format for users: {', '.join(invalid_tokens)}")
            raise ValueError("Invalid token format detected")

        for user_id, token in config.BOT_TOKENS.items():
            try:
                # Validate token before initializing
                if not await self.validate_token(token):
                    self.logger.error(f"Invalid token for user {user_id}")
                    continue
                    
                application = Application.builder().token(token).build()
                self.active_sessions[user_id] = application
                self.logger.info(f"Initialized session for user {user_id}")
                
            except Exception as e:
                self.logger.error(f"Session initialization error for user {user_id}: {e}")

    async def start_all_sessions(self):
        """Start all validated sessions"""
        for user_id, application in self.active_sessions.items():
            try:
                await application.initialize()
                await application.start()
                self.logger.info(f"Started session for user {user_id}")
                
            except Exception as e:
                self.logger.error(f"Session start error for user {user_id}: {e}")
                # Remove failed session
                del self.active_sessions[user_id]

    async def stop_all_sessions(self):
        """Stop all active sessions"""
        for user_id, application in list(self.active_sessions.items()):
            try:
                await application.stop()
                await application.shutdown()
                self.logger.info(f"Stopped session for user {user_id}")
                
            except Exception as e:
                self.logger.error(f"Session stop error for user {user_id}: {e}")
            finally:
                del self.active_sessions[user_id] 