# -*- coding: utf-8 -*-
"""
Image utility functions for format conversion and handling
"""
import base64
import re
from typing import Optional, Tuple


def convert_to_bytes(data) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Convert image data to bytes, handling both bytes and data URL formats.
    
    This function provides backward compatibility with existing code that returns
    bytes while also supporting future implementations that may return data URL strings.
    
    Args:
        data: Image data as bytes or data URL string (data:image/png;base64,...)
        
    Returns:
        tuple: (img_bytes, error_message) where:
            - img_bytes is the decoded image data or None if conversion failed
            - error_message is None on success or error description on failure
            
    Examples:
        >>> # Bytes input (current behavior)
        >>> img_bytes, error = convert_to_bytes(b'\\x89PNG...')
        >>> assert img_bytes == b'\\x89PNG...' and error is None
        
        >>> # Data URL input (future-proof)
        >>> data_url = "data:image/png;base64,iVBORw0KGgo..."
        >>> img_bytes, error = convert_to_bytes(data_url)
        >>> assert isinstance(img_bytes, bytes) and error is None
    """
    if isinstance(data, bytes):
        # Already bytes, use directly (current behavior)
        return data, None
    elif isinstance(data, str):
        # Data URL string, convert to bytes (future-proof)
        match = re.search(r'data:[^;]+;base64,(.+)', data)
        if match:
            try:
                return base64.b64decode(match.group(1)), None
            except Exception as e:
                return None, f"Base64 decode failed: {str(e)}"
        else:
            return None, "Invalid data URL format"
    else:
        return None, "Unknown image format"
