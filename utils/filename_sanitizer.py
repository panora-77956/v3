"""
Filename sanitization utility for handling Vietnamese characters and special characters.
Ensures cross-platform compatibility for filenames.

Author: chamnv-dev
Date: 2025-01-05
"""

import re
import unicodedata


# Vietnamese character mapping to ASCII equivalents
VIETNAMESE_CHAR_MAP = {
    'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
    'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
    'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
    'đ': 'd',
    'è': 'e', 'é': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
    'ê': 'e', 'ề': 'e', 'ế': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
    'ì': 'i', 'í': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
    'ò': 'o', 'ó': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
    'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
    'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
    'ù': 'u', 'ú': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
    'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
    'ỳ': 'y', 'ý': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y',
    'À': 'A', 'Á': 'A', 'Ả': 'A', 'Ã': 'A', 'Ạ': 'A',
    'Ă': 'A', 'Ằ': 'A', 'Ắ': 'A', 'Ẳ': 'A', 'Ẵ': 'A', 'Ặ': 'A',
    'Â': 'A', 'Ầ': 'A', 'Ấ': 'A', 'Ẩ': 'A', 'Ẫ': 'A', 'Ậ': 'A',
    'Đ': 'D',
    'È': 'E', 'É': 'E', 'Ẻ': 'E', 'Ẽ': 'E', 'Ẹ': 'E',
    'Ê': 'E', 'Ề': 'E', 'Ế': 'E', 'Ể': 'E', 'Ễ': 'E', 'Ệ': 'E',
    'Ì': 'I', 'Í': 'I', 'Ỉ': 'I', 'Ĩ': 'I', 'Ị': 'I',
    'Ò': 'O', 'Ó': 'O', 'Ỏ': 'O', 'Õ': 'O', 'Ọ': 'O',
    'Ô': 'O', 'Ồ': 'O', 'Ố': 'O', 'Ổ': 'O', 'Ỗ': 'O', 'Ộ': 'O',
    'Ơ': 'O', 'Ờ': 'O', 'Ớ': 'O', 'Ở': 'O', 'Ỡ': 'O', 'Ợ': 'O',
    'Ù': 'U', 'Ú': 'U', 'Ủ': 'U', 'Ũ': 'U', 'Ụ': 'U',
    'Ư': 'U', 'Ừ': 'U', 'Ứ': 'U', 'Ử': 'U', 'Ữ': 'U', 'Ự': 'U',
    'Ỳ': 'Y', 'Ý': 'Y', 'Ỷ': 'Y', 'Ỹ': 'Y', 'Ỵ': 'Y',
}


def remove_vietnamese_accents(text: str) -> str:
    """
    Convert Vietnamese characters to ASCII equivalents.
    
    Args:
        text: Input text with Vietnamese characters
    
    Returns:
        Text with Vietnamese characters converted to ASCII
    
    Examples:
        >>> remove_vietnamese_accents("Hẻm Nhỏ")
        'Hem Nho'
        >>> remove_vietnamese_accents("Đêm")
        'Dem'
    """
    result = []
    for char in text:
        result.append(VIETNAMESE_CHAR_MAP.get(char, char))
    return ''.join(result)


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    Sanitize a filename for cross-platform compatibility.
    
    This function:
    - Converts Vietnamese characters to ASCII
    - Removes or replaces invalid characters
    - Replaces spaces with underscores
    - Ensures the filename is not empty
    - Truncates to max_length if needed
    
    Args:
        filename: Original filename (with or without extension)
        max_length: Maximum length for the filename (default: 200)
    
    Returns:
        Sanitized filename safe for all platforms
    
    Examples:
        >>> sanitize_filename("Hẻm Nhỏ - Ngày.mp4")
        'Hem_Nho_-_Ngay.mp4'
        >>> sanitize_filename("Video: Test/File")
        'Video_Test_File'
    """
    if not filename:
        return "untitled"
    
    # Split extension if present
    parts = filename.rsplit('.', 1)
    name = parts[0]
    ext = f".{parts[1]}" if len(parts) > 1 else ""
    
    # Convert Vietnamese to ASCII
    name = remove_vietnamese_accents(name)
    
    # Replace colons with dashes (common in titles like "Project: Name")
    name = name.replace(':', ' -')
    
    # Remove invalid path characters: < > " / \ | ? * (colon already handled above)
    name = re.sub(r'[<>"/\\|?*]', '', name)
    
    # Replace spaces with underscores
    name = name.replace(' ', '_')
    
    # Remove consecutive underscores
    name = re.sub(r'_+', '_', name)
    
    # Remove leading/trailing underscores and dashes
    name = name.strip('_-')
    
    # Ensure name is not empty
    if not name:
        name = "untitled"
    
    # Truncate if too long (leave room for extension)
    max_name_length = max_length - len(ext)
    if len(name) > max_name_length:
        name = name[:max_name_length].rstrip('_-')
    
    return name + ext


def sanitize_project_name(project_name: str, max_length: int = 100) -> str:
    """
    Sanitize a project/directory name for cross-platform compatibility.
    
    Similar to sanitize_filename but more conservative for directory names.
    
    Args:
        project_name: Original project/directory name
        max_length: Maximum length for the name (default: 100)
    
    Returns:
        Sanitized project name safe for directory creation
    
    Examples:
        >>> sanitize_project_name("Dự Án: Video Hẻm Nhỏ")
        'Du_An_Video_Hem_Nho'
    """
    if not project_name:
        return "Project"
    
    # Convert Vietnamese to ASCII
    name = remove_vietnamese_accents(project_name)
    
    # Replace colons with dashes (common in project names like "Project: Name")
    name = name.replace(':', ' -')
    
    # Remove invalid path characters: < > " / \ | ? * (colon already handled above)
    name = re.sub(r'[<>"/\\|?*]', '', name)
    
    # Replace spaces with underscores
    name = name.replace(' ', '_')
    
    # Remove consecutive underscores
    name = re.sub(r'_+', '_', name)
    
    # Remove leading/trailing underscores and dashes
    name = name.strip('_-')
    
    # Ensure name is not empty
    if not name:
        name = "Project"
    
    # Truncate if too long
    if len(name) > max_length:
        name = name[:max_length].rstrip('_-')
    
    return name


def is_safe_filename(filename: str) -> bool:
    """
    Check if a filename is safe for cross-platform use.
    
    Args:
        filename: Filename to check
    
    Returns:
        True if filename is safe, False otherwise
    
    Examples:
        >>> is_safe_filename("video_file.mp4")
        True
        >>> is_safe_filename("video:file.mp4")
        False
        >>> is_safe_filename("Hẻm Nhỏ.mp4")
        False
    """
    if not filename or filename in ('.', '..'):
        return False
    
    # Check for invalid characters
    invalid_chars = r'[<>:"/\\|?*]'
    if re.search(invalid_chars, filename):
        return False
    
    # Check for Vietnamese characters
    for char in filename:
        if char in VIETNAMESE_CHAR_MAP:
            return False
    
    # Check for control characters
    if any(ord(char) < 32 for char in filename):
        return False
    
    return True
