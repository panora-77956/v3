# -*- coding: utf-8 -*-
"""
API Key Rotation Manager with Intelligent Rate Limiting
Optimized for Google Free Tier (15 RPM limit)
"""
import time
from typing import Callable, Optional, Any, List
from dataclasses import dataclass


@dataclass
class KeyState:
    """Track state for a single API key"""
    key: str
    last_used: float = 0.0
    retry_count: int = 0
    cooldown_until: float = 0.0
    total_calls: int = 0
    
    def is_available(self) -> bool:
        """Check if key is available (not in cooldown)"""
        return time.time() >= self.cooldown_until
    
    def time_until_available(self) -> float:
        """Get seconds until key becomes available"""
        return max(0.0, self.cooldown_until - time.time())


class APIKeyRotationManager:
    """
    Manages API key rotation with intelligent rate limiting
    Optimized for Google Free Tier with 15 RPM limit
    """
    
    # Configuration for FREE TIER (gemini-2.5-flash-image has VERY LOW rate limit)
    MIN_INTERVAL_BETWEEN_CALLS = 20.0  # 20s for ultra safety (free tier = 15 RPM = 4s/request)  # 15s between calls on same key (ultra safe)
    BACKOFF_DELAYS = [10.0, 20.0, 40.0]  # Long exponential backoff delays
    EXHAUSTED_COOLDOWN = 180.0  # 3 minutes cooldown after exhausting retries
    MAX_RETRIES_PER_KEY = 3
    
    def __init__(self, api_keys: List[str], log_callback: Callable = None):
        """
        Initialize rotation manager
        
        Args:
            api_keys: List of API keys to rotate through
            log_callback: Optional callback for logging messages
        """
        if not api_keys:
            raise ValueError("At least one API key is required")
        
        self.key_states = [KeyState(key=key) for key in api_keys]
        self.current_index = 0
        self.log_callback = log_callback
    
    def log(self, message: str):
        """Log message if callback is provided"""
        if self.log_callback:
            self.log_callback(message)
    
    def get_next_available_key(self) -> Optional[KeyState]:
        """Get next available key that's not in cooldown"""
        attempts = 0
        
        while attempts < len(self.key_states):
            key_state = self.key_states[self.current_index]
            
            if key_state.is_available():
                # Check minimum interval since last use
                time_since_last = time.time() - key_state.last_used
                if time_since_last >= self.MIN_INTERVAL_BETWEEN_CALLS:
                    return key_state
                else:
                    # Need to wait
                    wait_time = self.MIN_INTERVAL_BETWEEN_CALLS - time_since_last
                    self.log(f"[RATE LIMIT] Key needs {wait_time:.1f}s cooldown")
                    time.sleep(wait_time)
                    return key_state
            
            # Try next key
            self.current_index = (self.current_index + 1) % len(self.key_states)
            attempts += 1
        
        return None
    
    def mark_key_used(self, key_state: KeyState):
        """Mark key as used"""
        key_state.last_used = time.time()
        key_state.total_calls += 1
    
    def handle_rate_limit(self, key_state: KeyState):
        """Handle rate limit error with exponential backoff"""
        key_state.retry_count += 1
        
        if key_state.retry_count <= len(self.BACKOFF_DELAYS):
            delay = self.BACKOFF_DELAYS[key_state.retry_count - 1]
            self.log(f"[BACKOFF] Retry {key_state.retry_count}/{self.MAX_RETRIES_PER_KEY}, waiting {delay}s")
            time.sleep(delay)
        else:
            # Exhausted retries
            key_state.cooldown_until = time.time() + self.EXHAUSTED_COOLDOWN
            self.log(f"[COOLDOWN] Key exhausted, cooling down for {self.EXHAUSTED_COOLDOWN}s")
            key_state.retry_count = 0
    
    def handle_success(self, key_state: KeyState):
        """Handle successful API call"""
        key_state.retry_count = 0
    
    def call_with_rotation(
        self, 
        api_call: Callable[[str], Any],
        max_total_attempts: int = None
    ) -> Optional[Any]:
        """Call API with automatic key rotation and rate limiting"""
        if max_total_attempts is None:
            max_total_attempts = len(self.key_states) * self.MAX_RETRIES_PER_KEY
        
        total_attempts = 0
        
        while total_attempts < max_total_attempts:
            key_state = self.get_next_available_key()
            
            if key_state is None:
                min_wait = min(k.time_until_available() for k in self.key_states)
                if min_wait > 0:
                    # Add extra buffer when all keys are cooling down
                    wait_time = max(min_wait, 60.0)  # Minimum 60s global cooldown
                    self.log(f"[WAIT] All keys cooling down, waiting {wait_time:.1f}s")
                    time.sleep(wait_time)
                    continue
            
            total_attempts += 1
            self.mark_key_used(key_state)
            
            try:
                self.log(f"[CALL] Attempt {total_attempts}/{max_total_attempts} (Key #{self.current_index + 1})")
                result = api_call(key_state.key)
                
                self.handle_success(key_state)
                self.current_index = (self.current_index + 1) % len(self.key_states)
                return result
                
            except Exception as e:
                error_msg = str(e).lower()
                
                if '429' in error_msg or 'rate limit' in error_msg or 'quota' in error_msg or 'resource_exhausted' in error_msg:
                    self.log(f"[RATE LIMIT] Key #{self.current_index + 1} rate limited")
                    self.handle_rate_limit(key_state)
                    self.current_index = (self.current_index + 1) % len(self.key_states)
                else:
                    self.log(f"[ERROR] API call failed: {e}")
                    self.current_index = (self.current_index + 1) % len(self.key_states)
        
        self.log(f"[FAILED] All {max_total_attempts} attempts exhausted")
        return None