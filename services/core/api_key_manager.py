"""Centralized API Key Management"""
import threading
from typing import List, Optional

class APIKeyManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._keys = {
            'google_labs_tokens': [],
            'google_gemini_keys': [],
            'elevenlabs_keys': [],
        }
        self._current_indices = {
            'google_labs_tokens': 0,
            'google_gemini_keys': 0,
            'elevenlabs_keys': 0,
        }
        self._initialized = True
    
    def set_keys(self, key_type: str, keys: List[str]):
        self._keys[key_type] = [k for k in keys if k and k.strip()]
        self._current_indices[key_type] = 0
    
    def get_all_keys(self, key_type: str) -> List[str]:
        return self._keys.get(key_type, [])
    
    def get_next_key(self, key_type: str) -> Optional[str]:
        keys = self.get_all_keys(key_type)
        if not keys:
            return None
        idx = self._current_indices[key_type]
        key = keys[idx % len(keys)]
        self._current_indices[key_type] = (idx + 1) % len(keys)
        return key

_manager = APIKeyManager()

def get_key_manager() -> APIKeyManager:
    return _manager
