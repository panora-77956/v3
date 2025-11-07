# -*- coding: utf-8 -*-
import base64, requests, time
from typing import Optional
from services.core.api_config import gemini_image_endpoint, IMAGE_GEN_TIMEOUT
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
    prompt: str = None,
    text: str = None,
    api_keys: list = None,
    model: str = "gemini",
    aspect_ratio: str = "1:1",
    size: str = None,
    delay_before: float = 0,
    rate_limit_delay: float = 10.0,
    max_calls_per_minute: int = 6,
    logger = None,
    log_callback = None,
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
        prompt: Image generation prompt (alternative to 'text', one is required)
        text: Image generation prompt (alternative to 'prompt', one is required)
        api_keys: List of API keys to rotate through (optional, uses config if not provided)
        model: Model to use (gemini, dalle, imagen_4, etc.)
        aspect_ratio: Image aspect ratio (e.g., "9:16", "16:9", "1:1", "4:5")
        logger: Optional callback function for logging (alias for log_callback)
        log_callback: Optional callback function for logging
        reference_images: Reference images for generation (optional)
        
        # Legacy parameters (kept for backwards compatibility, currently not used):
        size: Image size (legacy parameter for DALL-E, not currently used)
        delay_before: Seconds to wait before call (not used - rotation manager handles delays)
        rate_limit_delay: Minimum seconds between calls (not used - rotation manager handles this)
        max_calls_per_minute: Maximum API calls per minute (not used - rotation manager handles this)
    
    Returns:
        Generated image bytes or None if generation fails
        
    Note:
        - Either 'prompt' or 'text' parameter must be provided
        - For Imagen 4: Automatically normalizes 4:5 to 3:4 (closest supported ratio)
        - For Gemini: Accepts any aspect ratio from UI
        - Legacy parameters (size, delay_before, rate_limit_delay, max_calls_per_minute) are 
          accepted for backward compatibility but are not used by the current implementation
    """
    # Support both 'prompt' and 'text' parameter names for backward compatibility
    if prompt is None and text is None:
        raise ValueError("Either 'prompt' or 'text' parameter is required")
    
    # Use whichever is provided, preferring 'prompt' if both are given
    actual_prompt = prompt if prompt is not None else text
    
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

            enhanced_prompt = actual_prompt + aspect_hint if aspect_hint else actual_prompt

            # Build parts array for API payload
            parts = [{"text": enhanced_prompt}]

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
            try:
                rotator = APIKeyRotator(api_keys, log_callback=log_fn)
                return rotator.execute(api_call_with_key)
            except APIKeyRotationError as e:
                # All Gemini keys exhausted - check if it's due to rate limits
                error_msg = str(e).lower()
                if 'rate limit' in error_msg or '429' in error_msg or 'quota' in error_msg:
                    log("[RATE LIMIT] All Gemini API keys are rate limited!")
                    log("[INFO] Attempting fallback to Whisk API...")
                    
                    # Try Whisk as fallback if reference images are available
                    if reference_images and len(reference_images) > 0:
                        try:
                            from services import whisk_service
                            whisk_result = whisk_service.generate_image(
                                prompt=actual_prompt,
                                model_image=reference_images[0] if len(reference_images) > 0 else None,
                                product_image=reference_images[1] if len(reference_images) > 1 else None,
                                debug_callback=log_fn
                            )
                            if whisk_result:
                                log("[SUCCESS] Whisk fallback succeeded!")
                                return whisk_result
                            else:
                                log("[ERROR] Whisk fallback returned no data")
                        except Exception as whisk_err:
                            log(f"[ERROR] Whisk fallback failed: {str(whisk_err)[:100]}")
                    else:
                        log("[SKIP] Whisk requires reference images (not provided)")
                
                # Re-raise the original error if Whisk fallback didn't work
                raise

        elif model.lower() == "dalle":
            log(f"[IMAGE GEN] Tạo ảnh với DALL-E...")
            # Import DALL-E client if available
            try:
                from services.openai.dalle_client import generate_image
                return generate_image(actual_prompt, size=size)
            except ImportError:
                log("[ERROR] DALL-E client không khả dụng")
                return None
        else:
            log(f"[ERROR] Unsupported model: {model}")
            return None

    except Exception as e:
        log(f"[ERROR] Image generation failed: {str(e)[:200]}")
        return None
