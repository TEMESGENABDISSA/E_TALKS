import pytest
from telegram import Update, CallbackQuery, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from unittest.mock import AsyncMock, MagicMock
from button_handler import ButtonHandler

# Mark the test as async
@pytest.mark.asyncio
async def test_social_links():
    """Test the social links functionality"""
    # Create mock objects
    button_handler = ButtonHandler()
    update = MagicMock(spec=Update)
    context = MagicMock(spec=CallbackContext)
    
    # Setup mock callback query
    query = AsyncMock(spec=CallbackQuery)
    update.callback_query = query
    
    # Test social links handler
    await button_handler.handle_social_links(update, context)
    
    # Verify answer was called
    query.answer.assert_called_once()
    
    # Verify message was edited with correct keyboard
    query.edit_message_text.assert_called_once()
    call_args = query.edit_message_text.call_args
    assert "social media" in call_args[1]['text']
    assert isinstance(call_args[1]['reply_markup'], InlineKeyboardMarkup)

# Alternative synchronous test if needed
def test_button_handler_init():
    """Test ButtonHandler initialization"""
    handler = ButtonHandler()
    assert hasattr(handler, 'logger')
    assert 'social_links' in handler.callback_map
    assert 'main_menu' in handler.callback_map

if __name__ == "__main__":
    pytest.main([__file__]) 