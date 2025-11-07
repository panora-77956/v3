# -*- coding: utf-8 -*-
"""
API Key Rotation Manager with Exponential Backoff and Per-Key Tracking

Features:
- Per-key usage tracking (calls, failures, last used time)
- Exponential backoff: 2s → 4s → 8s before retries
- 60s cooldown after exhausting retries on a key
- Minimum 2s interval between calls on same key
- Smart rotation that skips rate-limited keys automatically
- Thread-safe key rotation with locks

Based on the pattern from geminiService.ts (executeWithKeyRotation)
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Any, Dict


@dataclass
class KeyUsageTracker:
    """Track usage statistics for a single API key"""
    key: str
    total_calls: int = 0
    failed_calls: int = 0
    rate_limit_hits: int = 0
    last_used_time: float = 0.0
    last_rate_limit_time: float = 0.0
    cooldown_until: float = 0.0  # Unix timestamp when key is available again
    consecutive_failures: int = 0


class APIKeyRotationManager:
    """
    Intelligent API key rotation manager with exponential backoff
    
    Features:
    - Tracks usage per key (calls, failures, cooldowns)
    - Exponential backoff: 2s, 4s, 8s for retries
    - 60s cooldown after max retries
    - Minimum 2s between calls on same key
    - Automatically skips rate-limited keys
    """
    
    # Configuration constants
    MAX_RETRIES_PER_KEY = 3  # Try each key up to 3 times with backoff
    INITIAL_BACKOFF_SECONDS = 2.0  # Start with 2 seconds
    COOLDOWN_SECONDS = 60.0  # 60 seconds cooldown after exhausting retries
    MIN_CALL_INTERVAL_SECONDS = 2.0  # Minimum 2 seconds between calls on same key
    EXHAUSTED_KEYS_RETRY_INTERVAL_SECONDS = 5.0  # Wait 5s before rechecking when all keys exhausted
    
    def __init__(self, api_keys: List[str], log_callback: Optional[Callable[[str], None]] = None):
        """
        Initialize the rotation manager
        
        Args:
            api_keys: List of API keys to rotate through
            log_callback: Optional callback for logging messages
        """
        self.api_keys = [key for key in api_keys if key and key.strip()]
        self.log_callback = log_callback
        self.lock = threading.Lock()
        
        # Initialize trackers for each key
        self.key_trackers: Dict[str, KeyUsageTracker] = {}
        for key in self.api_keys:
            self.key_trackers[key] = KeyUsageTracker(key=key)
        
        if not self.api_keys:
            raise ValueError("No valid API keys provided")
    
    def _log(self, msg: str):
        """Log message if callback is provided"""
        if self.log_callback:
            self.log_callback(msg)
    
    def _key_preview(self, key: str) -> str:
        """Get a safe preview of the key for logging"""
        if len(key) > 6:
            return f"...{key[-6:]}"
        return "***"
    
    def _is_key_available(self, tracker: KeyUsageTracker) -> bool:
        """Check if a key is available (not in cooldown)"""
        current_time = time.time()
        return current_time >= tracker.cooldown_until
    
    def _get_available_keys(self) -> List[KeyUsageTracker]:
        """Get list of available keys (not in cooldown)"""
        current_time = time.time()
        available = []
        
        for key in self.api_keys:
            tracker = self.key_trackers[key]
            if current_time >= tracker.cooldown_until:
                available.append(tracker)
        
        return available
    
    def _wait_for_min_interval(self, tracker: KeyUsageTracker):
        """Wait if minimum interval hasn't passed since last call"""
        if tracker.last_used_time > 0:
            elapsed = time.time() - tracker.last_used_time
            if elapsed < self.MIN_CALL_INTERVAL_SECONDS:
                wait_time = self.MIN_CALL_INTERVAL_SECONDS - elapsed
                self._log(f"[MIN INTERVAL] Waiting {wait_time:.1f}s before reusing key {self._key_preview(tracker.key)}")
                time.sleep(wait_time)
    
    def _handle_rate_limit(self, tracker: KeyUsageTracker, retry_count: int) -> bool:
        """
        Handle rate limit error with exponential backoff
        
        Args:
            tracker: Key tracker that hit rate limit
            retry_count: Current retry attempt (0-based)
            
        Returns:
            True if should retry, False if max retries exceeded
        """
        tracker.rate_limit_hits += 1
        tracker.last_rate_limit_time = time.time()
        tracker.consecutive_failures += 1
        
        if retry_count >= self.MAX_RETRIES_PER_KEY:
            # Max retries exceeded - put key in cooldown
            tracker.cooldown_until = time.time() + self.COOLDOWN_SECONDS
            self._log(
                f"[COOLDOWN] Key {self._key_preview(tracker.key)} exhausted {self.MAX_RETRIES_PER_KEY} retries. "
                f"Cooldown for {self.COOLDOWN_SECONDS}s"
            )
            return False
        
        # Calculate exponential backoff: 2s, 4s, 8s
        backoff_delay = self.INITIAL_BACKOFF_SECONDS * (2 ** retry_count)
        self._log(
            f"[RATE LIMIT] Key {self._key_preview(tracker.key)} hit limit. "
            f"Retry {retry_count + 1}/{self.MAX_RETRIES_PER_KEY} after {backoff_delay}s"
        )
        time.sleep(backoff_delay)
        return True
    
    def execute_with_rotation(self, api_call: Callable[[str], Any]) -> Any:
        """
        Execute API call with intelligent key rotation
        
        Args:
            api_call: Function that takes an API key and returns result.
                     Should raise exception on failure (e.g., requests.HTTPError)
        
        Returns:
            Result from successful API call
            
        Raises:
            Exception: If all keys fail or are exhausted
        """
        with self.lock:
            all_keys_tried = set()
            
            while True:
                # Get available keys
                available_keys = self._get_available_keys()
                
                if not available_keys:
                    self._log("[EXHAUSTED] All keys are in cooldown. Waiting for cooldown to expire...")
                    # Wait and check again
                    time.sleep(self.EXHAUSTED_KEYS_RETRY_INTERVAL_SECONDS)
                    available_keys = self._get_available_keys()
                    
                    if not available_keys:
                        raise Exception(
                            f"All {len(self.api_keys)} API keys are rate-limited or in cooldown. "
                            f"Please wait {self.COOLDOWN_SECONDS}s before retrying."
                        )
                
                # Try each available key with exponential backoff
                for tracker in available_keys:
                    if tracker.key in all_keys_tried:
                        continue
                    
                    # Wait for minimum interval if key was recently used
                    self._wait_for_min_interval(tracker)
                    
                    retry_count = 0
                    while retry_count <= self.MAX_RETRIES_PER_KEY:
                        try:
                            self._log(
                                f"[KEY {len(all_keys_tried) + 1}/{len(self.api_keys)}] "
                                f"Trying key {self._key_preview(tracker.key)}"
                            )
                            
                            # Update usage stats
                            tracker.last_used_time = time.time()
                            tracker.total_calls += 1
                            
                            # Make the API call
                            result = api_call(tracker.key)
                            
                            # Success! Reset failure counters
                            tracker.consecutive_failures = 0
                            self._log(
                                f"[SUCCESS] Key {self._key_preview(tracker.key)} succeeded "
                                f"(call #{tracker.total_calls})"
                            )
                            return result
                            
                        except Exception as e:
                            error_msg = str(e).lower()
                            tracker.failed_calls += 1
                            
                            # Check if it's a rate limit error
                            is_rate_limit = any(
                                keyword in error_msg
                                for keyword in ['429', 'rate limit', 'quota', 'too many requests']
                            )
                            
                            if is_rate_limit:
                                # Handle rate limit with backoff
                                should_retry = self._handle_rate_limit(tracker, retry_count)
                                if should_retry:
                                    retry_count += 1
                                    continue  # Retry with backoff
                                else:
                                    # Max retries exceeded, mark key as tried and move to next
                                    all_keys_tried.add(tracker.key)
                                    break
                            else:
                                # Non-rate-limit error - log and try next key
                                self._log(
                                    f"[ERROR] Key {self._key_preview(tracker.key)} failed: "
                                    f"{str(e)[:100]}"
                                )
                                tracker.consecutive_failures += 1
                                all_keys_tried.add(tracker.key)
                                break
                    
                    # If we exhausted retries, mark as tried
                    if retry_count > self.MAX_RETRIES_PER_KEY:
                        all_keys_tried.add(tracker.key)
                
                # Check if we've tried all keys
                if len(all_keys_tried) >= len(self.api_keys):
                    raise Exception(
                        f"All {len(self.api_keys)} API keys failed after retries. "
                        f"Total calls made: {sum(t.total_calls for t in self.key_trackers.values())}, "
                        f"Total failures: {sum(t.failed_calls for t in self.key_trackers.values())}"
                    )
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of all keys
        
        Returns:
            Dictionary with key statistics and availability
        """
        current_time = time.time()
        available_count = sum(
            1 for t in self.key_trackers.values()
            if current_time >= t.cooldown_until
        )
        rate_limited_count = sum(
            1 for t in self.key_trackers.values()
            if current_time < t.cooldown_until
        )
        
        return {
            'total_keys': len(self.api_keys),
            'available_keys': available_count,
            'rate_limited_keys': rate_limited_count,
            'key_details': [
                {
                    'key_preview': self._key_preview(t.key),
                    'total_calls': t.total_calls,
                    'failed_calls': t.failed_calls,
                    'rate_limit_hits': t.rate_limit_hits,
                    'consecutive_failures': t.consecutive_failures,
                    'is_available': current_time >= t.cooldown_until,
                    'cooldown_remaining': max(0, t.cooldown_until - current_time)
                }
                for t in self.key_trackers.values()
            ]
        }
