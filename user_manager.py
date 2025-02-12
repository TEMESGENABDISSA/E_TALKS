import json
import os
from datetime import datetime

class UserManager:
    def __init__(self, storage_file='user_data.json'):
        self.storage_file = storage_file
        self.users = self._load_users()

    def _load_users(self):
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_users(self):
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)
            with open(self.storage_file, 'w') as f:
                json.dump(self.users, f)
        except Exception as e:
            print(f"Error saving users: {e}")

    def is_new_user(self, user_id):
        return str(user_id) not in self.users

    def mark_user_welcomed(self, user_id, user_info):
        user_id = str(user_id)
        if user_id not in self.users:
            self.users[user_id] = {
                'first_seen': datetime.now().isoformat(),
                'welcomed': True,
                'blocked': False,
                'username': user_info.username,
                'first_name': user_info.first_name,
                'last_name': user_info.last_name
            }
            self._save_users()
            return True
        return False

    def block_user(self, user_id, reason):
        user_id = str(user_id)
        if user_id in self.users:
            self.users[user_id]['blocked'] = True
            self.users[user_id]['block_reason'] = reason
            self.users[user_id]['block_time'] = datetime.now().isoformat()
        else:
            self.users[user_id] = {
                'first_seen': datetime.now().isoformat(),
                'welcomed': False,
                'blocked': True,
                'block_reason': reason,
                'block_time': datetime.now().isoformat()
            }
        self._save_users()

    def is_blocked(self, user_id):
        user_id = str(user_id)
        if user_id not in self.users or not self.users[user_id].get('blocked', False):
            return False
            
        # Check if 24 hours have passed since blocking
        block_time = datetime.fromisoformat(self.users[user_id].get('block_time', ''))
        time_diff = datetime.now() - block_time
        
        # If 24 hours have passed, unblock the user
        if time_diff.total_seconds() >= 24 * 3600:  # 24 hours in seconds
            self.unblock_user(user_id)
            return False
            
        return True
        
    def unblock_user(self, user_id):
        """Unblock a user"""
        user_id = str(user_id)
        if user_id in self.users:
            self.users[user_id]['blocked'] = False
            self.users[user_id]['unblock_time'] = datetime.now().isoformat()
            self._save_users()