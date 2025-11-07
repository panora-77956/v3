# -*- coding: utf-8 -*-
"""
API Key Rotator - Smart rotation with exponential backoff
Based on geminiService.ts logic with enhanced error handling
"""
import time
from typing import List, Callable, Any, Optional


class APIKeyRotationError(Exception):
    """Error raised when all API keys fail"""
    pass


class APIKeyRotator:
    """
    Smart API key rotation with exponential backoff and intelligent retry logic
    
    Features:
    - Exponential backoff: 2s, 4s, 8s, 16s...
    - Smart error handling: retry 429, fail fast on 401
    - Transparent logging
    """
    
    def __init__(self, keys: List[str], log_callback: Optional[Callable[[str], None]] = None):
        """
        Initialize rotator with keys and optional logging
        
        Args:
            keys: List of API keys to rotate through
            log_callback: Optional callback function for logging (receives string messages)
        """
        self.keys = keys if keys else []
        self.log_callback = log_callback
        
        if not self.keys:
            raise APIKeyRotationError("No API keys provided")
    
    def _log(self, msg: str):
        """Log message if callback is provided"""
        if self.log_callback:
            self.log_callback(msg)
    
    # Maximum backoff delay in seconds
    MAX_BACKOFF_SECONDS = 32
    
    def execute(self, api_call: Callable[[str], Any]) -> Any:
        """
        Execute an API call with smart key rotation and error handling
        
        Args:
            api_call: Function that takes an API key and returns result
                     Should raise exceptions on failure
        
        Returns:
            Result from successful API call
            
        Raises:
            APIKeyRotationError: If all keys fail
        """
        last_error = None
        
        for idx, key in enumerate(self.keys):
            # Exponential backoff: 4s, 8s, 16s, 32s (increased from 2s, 4s, 8s, 16s)
            if idx > 0:
                delay = 4 * (2 ** (idx - 1))  # 4s, 8s, 16s, 32s...
                # Cap at MAX_BACKOFF_SECONDS to avoid excessive waits
                delay = min(delay, self.MAX_BACKOFF_SECONDS)
                self._log(f"[BACKOFF] Waiting {delay}s before trying next key...")
                time.sleep(delay)
            
            key_preview = f"...{key[-6:]}" if len(key) > 6 else "***"
            self._log(f"[KEY {idx + 1}/{len(self.keys)}] Trying key {key_preview}")
            
            try:
                result = api_call(key)
                self._log(f"[SUCCESS] Key {key_preview} succeeded")
                return result
                
            except Exception as e:
                error_msg = str(e).lower()
                last_error = e
                
                # Check HTTP status codes in error message
                # 401: Unauthorized - key is invalid, skip to next immediately
                if '401' in error_msg or 'unauthorized' in error_msg or 'invalid api key' in error_msg:
                    self._log(f"[FAIL] Key {key_preview} is invalid (401/unauthorized)")
                    continue
                
                # 429: Rate limit - continue with backoff
                if '429' in error_msg or 'rate limit' in error_msg or 'quota' in error_msg:
                    self._log(f"[RATE LIMIT] Key {key_preview} hit rate limit (429)")
                    continue
                
                # 403: Forbidden - permission issue, skip
                if '403' in error_msg or 'forbidden' in error_msg:
                    self._log(f"[FORBIDDEN] Key {key_preview} has permission issues (403)")
                    continue
                
                # 5xx: Server errors - might be transient, continue
                if any(code in error_msg for code in ['500', '502', '503', '504']):
                    self._log(f"[SERVER ERROR] Key {key_preview} encountered server error (5xx)")
                    continue
                
                # Other errors - log and continue
                self._log(f"[ERROR] Key {key_preview} failed: {str(e)[:100]}")
                continue
        
        # All keys exhausted
        error_summary = f"All {len(self.keys)} API keys failed"
        if last_error:
            error_summary += f". Last error: {str(last_error)[:200]}"
        
        self._log(f"[EXHAUSTED] {error_summary}")
        raise APIKeyRotationError(error_summary)
