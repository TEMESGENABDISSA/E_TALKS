import pytest
from telegram import Update, InlineKeyboardMarkup
from unittest.mock import MagicMock
import os
import sys

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from emamutalks.button_handler import ButtonHandler
    from emamutalks.config import get_social_links_keyboard
except ImportError as e:
    print(f"Import Error: {e}")
    print(f"Python Path: {sys.path}")
    raise

def test_button_handler_structure():
    """Test the structure of ButtonHandler"""
    handler = ButtonHandler()
    
    # Test initialization
    assert handler is not None
    assert hasattr(handler, 'callback_map')
    
    # Test callback map contents
    assert 'social_links' in handler.callback_map
    assert 'main_menu' in handler.callback_map
    assert 'email' in handler.callback_map
    
    # Test method existence
    assert hasattr(handler, 'handle_social_links')
    assert hasattr(handler, 'handle_main_menu')
    assert hasattr(handler, 'handle_error')

def test_social_links_keyboard():
    """Test social links keyboard creation"""
    keyboard = get_social_links_keyboard()
    assert isinstance(keyboard, InlineKeyboardMarkup)
    
    # Test keyboard structure
    buttons = keyboard.inline_keyboard
    assert len(buttons) > 0
    assert any('Back to Menu' in str(button) for row in buttons for button in row)

if __name__ == "__main__":
    pytest.main(["-v"]) 