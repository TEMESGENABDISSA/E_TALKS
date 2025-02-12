from telegram.ext import Application
import logging
from typing import Dict
import config

class SessionManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.active_sessions: Dict[str, Application] = {}
        
    async def initialize_sessions(self):
        """Initialize bot sessions for all user accounts"""
        try:
            for user_id, token in config.USER_TOKENS.items():
                application = Application.builder().token(token).build()
                self.active_sessions[user_id] = application
                self.logger.info(f"Initialized session for user {user_id}")
                
        except Exception as e:
            self.logger.error(f"Session initialization error: {e}")
            raise
            
    async def start_all_sessions(self):
        """Start all bot sessions"""
        for user_id, application in self.active_sessions.items():
            try:
                await application.initialize()
                await application.start()
                self.logger.info(f"Started session for user {user_id}")
                
            except Exception as e:
                self.logger.error(f"Session start error for user {user_id}: {e}")
                
    async def stop_all_sessions(self):
        """Stop all bot sessions"""
        for user_id, application in self.active_sessions.items():
            try:
                await application.stop()
                await application.shutdown()
                self.logger.info(f"Stopped session for user {user_id}")
                
            except Exception as e:
                self.logger.error(f"Session stop error for user {user_id}: {e}") 