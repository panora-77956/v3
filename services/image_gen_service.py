# -*- coding: utf-8 -*-
import os, base64, json, requests, mimetypes, uuid, time
from typing import Optional, Dict, Any, List
from services.core.api_config import GEMINI_IMAGE_MODEL, GEMINI_BASE, gemini_image_endpoint, IMAGE_GEN_TIMEOUT
from services.core.key_manager import get_all_keys, refresh
from services.core.api_key_rotator import APIKeyRotator, APIKeyRotationError


class ImageGenError(Exception):
    """Image generation error"""
    pass


def _extract_image_from_response(data: dict) -> bytes:
    """
    Extract image bytes from Gemini API response
    
    Args:
        data: JSON response from Gemini API
        
    Returns:
        Image as bytes
        
    Raises:
        ImageGenError: If image data cannot be extracted
    """
    candidates = data.get("candidates", [])
    if not candidates:
        raise ImageGenError("No candidates in response")
    
    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts:
        raise ImageGenError("No parts in candidate")
    
    # Look for inline_data with image
    for part in parts:
        if "inline_data" in part:
            mime_type = part["inline_data"].get("mime_type", "")
            if mime_type.startswith("image/"):
                b64_data = part["inline_data"].get("data", "")
                if b64_data:
                    return base64.b64decode(b64_data)
    
    raise ImageGenError("No image data found in response")


def generate_image_gemini(prompt: str, timeout: int = None, retry_delay: float = 15.0, enforce_rate_limit: bool = True, log_callback=None) -> bytes:
    """
    Generate image using Gemini Flash Image model with APIKeyRotator (PR#5)
    
    Args:
        prompt: Text prompt for image generation
        timeout: Request timeout in seconds (default from api_config)
        retry_delay: Base delay before first API call (15.0s for Gemini free tier safety)
        enforce_rate_limit: If True, wait before first API call (default True)
        log_callback: Optional callback function for logging (receives string messages)
        
    Returns:
        Generated image as bytes
        
    Raises:
        ImageGenError: If generation fails
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
    
    timeout = timeout or IMAGE_GEN_TIMEOUT
    refresh()
    keys = get_all_keys('google')
    if not keys:
        raise ImageGenError("No Google API keys available")
    
    log(f"[DEBUG] Tìm thấy {len(keys)} Google API keys")
    
    # Enforce rate limit before first call
    if enforce_rate_limit:
        log(f"[RATE LIMIT] Đợi {retry_delay}s trước khi gọi API...")
        time.sleep(retry_delay)
    
    # PR#5: Define API call function for APIKeyRotator
    def api_call_with_key(api_key: str) -> bytes:
        """Make API call with given key"""
        url = gemini_image_endpoint(api_key)
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.9,
                "topK": 40,
                "topP": 0.95,
            }
        }
        
        response = requests.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract image data using helper
        return _extract_image_from_response(data)
    
    # PR#5: Use APIKeyRotator
    try:
        rotator = APIKeyRotator(keys, log_callback=log)
        return rotator.execute(api_call_with_key)
    except APIKeyRotationError as e:
        raise ImageGenError(str(e))


# New implementation: Intelligent rate-limited image generation with API key rotation
def generate_image_with_rate_limit(
    aspect_ratio: str = "1:1",
    reference_images: list = None,
) -> Optional[bytes]:
    """
    Generate image with intelligent API key rotation and rate limiting
    
    This function uses the new APIKeyRotationManager to handle:
    - Per-key usage tracking and cooldowns
    - Exponential backoff (2s, 4s, 8s) on rate limits
    - 60s cooldown after exhausting retries on a key
    - Minimum 2s interval between calls on same key
    - Smart rotation that skips rate-limited keys
    
    Args:
        prompt: Image generation prompt (REQUIRED)
        api_keys: List of API keys to rotate through (optional, uses config if not provided)
        model: Model to use (gemini, dalle, imagen_4, etc.)
        aspect_ratio: Image aspect ratio (e.g., "9:16", "16:9", "1:1", "4:5")
        size: Image size
        delay_before: Seconds to wait before making the call (default 0, no delay)
        rate_limit_delay: Minimum seconds between calls (default 10.0)
        max_calls_per_minute: Maximum API calls per minute (default 6)
        logger: Optional callback function for logging (alias for log_callback)
        log_callback: Optional callback function for logging
        
        # Legacy parameters (kept for backwards compatibility, ignored):
        delay_before: Ignored - rotation manager handles delays
        size: Ignored - use aspect_ratio instead
        rate_limit_delay: Ignored - rotation manager handles delays
        max_calls_per_minute: Ignored - rotation manager handles rate limits
    
    Returns:
        Generated image bytes or None if generation fails
        
    Note:
        - For Imagen 4: Automatically normalizes 4:5 to 3:4 (closest supported ratio)
        - For Gemini: Accepts any aspect ratio from UI
        - Legacy parameters (delay_before, size, etc.) are ignored - use new rotation manager
    """
    # Support both logger and log_callback parameter names
    log_fn = logger or log_callback
    
    def log(msg):
        if log_fn:
            log_fn(msg)
    
    # Load API keys if not provided
    if not api_keys:
        from services.core.key_manager import get_all_keys, refresh
        refresh()
        api_keys = get_all_keys('google')
    
    if not api_keys:
        log("[ERROR] No Google API keys available")
        return None
    
    log(f"[IMAGE GEN] Using {len(api_keys)} API keys with intelligent rotation")
    
    # Normalize aspect ratio for Imagen 4
    normalized_ratio = aspect_ratio
    if model.lower() == 'imagen_4':
        # Imagen 4 doesn't support 4:5, normalize to 3:4
        if aspect_ratio == "4:5":
            normalized_ratio = "3:4"
            log(f"[ASPECT RATIO] Normalized {aspect_ratio} to {normalized_ratio} for Imagen 4")
    
    # Call appropriate generation function with key rotation
    try:
        if model.lower() in ("gemini", "imagen_4"):
            log(f"[IMAGE GEN] Tạo ảnh với {model}...")
            
            # Build generation config with aspect ratio hint if provided
            generation_config = {
                "temperature": 0.9,
                "topK": 40,
                "topP": 0.95,
            }
            
            # Add aspect ratio to prompt for better results
            # Note: Gemini doesn't have explicit aspect_ratio parameter, so we enhance the prompt
            aspect_hint = ""
            if aspect_ratio and aspect_ratio != "1:1":
                if aspect_ratio in ("9:16", "4:5"):
                    aspect_hint = " (portrait orientation, vertical format)"
                elif aspect_ratio in ("16:9", "21:9"):
                    aspect_hint = " (landscape orientation, horizontal format)"
            
            enhanced_prompt = prompt + aspect_hint if aspect_hint else prompt
            
            # Use APIKeyRotator for key rotation with shared API call logic
            def api_call_with_key(api_key: str) -> bytes:
                """Make API call with given key"""
                url = gemini_image_endpoint(api_key)
                
                payload = {
                    "contents": [{
                        "parts": parts
                    }],
                    "generationConfig": generation_config
                }
                
                response = requests.post(url, json=payload, timeout=IMAGE_GEN_TIMEOUT)
                response.raise_for_status()
                
                data = response.json()
                
                # Extract image data using helper
                return _extract_image_from_response(data)
            
            # Use APIKeyRotator with provided keys
            rotator = APIKeyRotator(api_keys, log_callback=log_fn)
            return rotator.execute(api_call_with_key)
            
        elif model.lower() == "dalle":
            log(f"[IMAGE GEN] Tạo ảnh với DALL-E...")
            # Import DALL-E client if available
            try:
                from services.openai.dalle_client import generate_image
                return generate_image(prompt, size=size)
            except ImportError:
                log("[ERROR] DALL-E client không khả dụng")
                return None
        else:
            log(f"[ERROR] Unsupported model: {model}")
            return None
        
    except Exception as e:
        log(f"[ERROR] Image generation failed: {str(e)[:200]}")
        return None
