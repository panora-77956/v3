"""
Icon Utilities - Helper functions for loading and managing UI icons
This module provides functions to load icons from the resources directory
with fallback support for emoji when images are not available.

Author: chamnv-dev
Date: 2025-11-07
Version: 1.0.0
"""

import os
from typing import Optional, Tuple
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt


# Define resource paths
def get_resource_path(relative_path: str) -> str:
    """
    Get absolute path to resource file
    
    Args:
        relative_path: Path relative to resources directory
        
    Returns:
        Absolute path to the resource file
    """
    # Get the path to the project root (parent of utils directory)
    current_file = os.path.abspath(__file__)
    utils_dir = os.path.dirname(current_file)
    project_root = os.path.dirname(utils_dir)
    return os.path.join(project_root, 'resources', relative_path)


class IconType:
    """Enum-like class for icon types"""
    ERROR = 'error'
    WARNING = 'warning'
    SUCCESS = 'success'
    INFO = 'info'


# Icon file mapping
ICON_FILES = {
    IconType.ERROR: 'icons/error.png',
    IconType.WARNING: 'icons/warning.png',
    IconType.SUCCESS: 'icons/success.png',
    IconType.INFO: 'icons/info.png',
}

# Emoji fallbacks when images are not available
EMOJI_FALLBACKS = {
    IconType.ERROR: '❌',
    IconType.WARNING: '⚠️',
    IconType.SUCCESS: '✅',
    IconType.INFO: 'ℹ️',
}


def load_icon_pixmap(icon_type: str, size: Optional[Tuple[int, int]] = None) -> Optional[QPixmap]:
    """
    Load an icon as a QPixmap
    
    Args:
        icon_type: Type of icon (error, warning, success, info)
        size: Optional tuple (width, height) to scale the icon
        
    Returns:
        QPixmap object if icon file exists, None otherwise
    """
    if icon_type not in ICON_FILES:
        return None

    icon_path = get_resource_path(ICON_FILES[icon_type])

    if not os.path.exists(icon_path):
        return None

    pixmap = QPixmap(icon_path)

    if pixmap.isNull():
        return None

    # Scale if size is specified
    if size:
        width, height = size
        pixmap = pixmap.scaled(
            width, height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

    return pixmap


def load_icon(icon_type: str) -> QIcon:
    """
    Load an icon as a QIcon
    
    Args:
        icon_type: Type of icon (error, warning, success, info)
        
    Returns:
        QIcon object (may be null if icon file doesn't exist)
    """
    pixmap = load_icon_pixmap(icon_type)
    if pixmap:
        return QIcon(pixmap)
    return QIcon()


def get_icon_or_emoji(icon_type: str, prefer_image: bool = True) -> Tuple[Optional[QPixmap], str]:
    """
    Get icon pixmap and fallback emoji
    
    Args:
        icon_type: Type of icon (error, warning, success, info)
        prefer_image: If True, tries to load image first
        
    Returns:
        Tuple of (QPixmap or None, emoji string)
    """
    emoji = EMOJI_FALLBACKS.get(icon_type, '•')

    if prefer_image:
        pixmap = load_icon_pixmap(icon_type)
        if pixmap:
            return pixmap, emoji

    return None, emoji


def has_icon_support() -> bool:
    """
    Check if icon files are available
    
    Returns:
        True if at least one icon file exists, False otherwise
    """
    for icon_type, icon_file in ICON_FILES.items():
        icon_path = get_resource_path(icon_file)
        if os.path.exists(icon_path):
            return True
    return False


def get_icon_status() -> dict:
    """
    Get status of all icon files
    
    Returns:
        Dictionary mapping icon types to their availability status
    """
    status = {}
    for icon_type, icon_file in ICON_FILES.items():
        icon_path = get_resource_path(icon_file)
        status[icon_type] = os.path.exists(icon_path)
    return status


# Convenience functions for common use cases
def get_error_icon(size: Optional[Tuple[int, int]] = None) -> Optional[QPixmap]:
    """Get error icon pixmap"""
    return load_icon_pixmap(IconType.ERROR, size)


def get_warning_icon(size: Optional[Tuple[int, int]] = None) -> Optional[QPixmap]:
    """Get warning icon pixmap"""
    return load_icon_pixmap(IconType.WARNING, size)


def get_success_icon(size: Optional[Tuple[int, int]] = None) -> Optional[QPixmap]:
    """Get success icon pixmap"""
    return load_icon_pixmap(IconType.SUCCESS, size)


def get_info_icon(size: Optional[Tuple[int, int]] = None) -> Optional[QPixmap]:
    """Get info icon pixmap"""
    return load_icon_pixmap(IconType.INFO, size)


if __name__ == '__main__':
    """Test icon loading"""
    print("Icon Utilities Test")
    print("=" * 50)

    print(f"\nIcon support available: {has_icon_support()}")
    print("\nIcon status:")
    for icon_type, available in get_icon_status().items():
        status = "✓ Available" if available else "✗ Missing"
        print(f"  {icon_type}: {status}")

    print("\nTesting icon loading:")
    for icon_type in [IconType.ERROR, IconType.WARNING, IconType.SUCCESS, IconType.INFO]:
        pixmap, emoji = get_icon_or_emoji(icon_type)
        if pixmap:
            print(f"  {icon_type}: Loaded pixmap {pixmap.width()}x{pixmap.height()}, fallback: {emoji}")
        else:
            print(f"  {icon_type}: Using emoji fallback: {emoji}")
