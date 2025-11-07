"""
Create Error Icons Script
Generates error, warning, success, and info icons for the application

Requirements:
    - Pillow (PIL): pip install Pillow

Usage:
    python docs/create_icons.py
    
This script will create 4 icon files in resources/icons/:
- error.png (red)
- warning.png (orange)
- success.png (green)
- info.png (blue)
    
Author: chamnv-dev
Date: 2025-11-07
"""

from PIL import Image, ImageDraw
import os


def create_error_icon(filename, color, symbol, output_dir='resources/icons'):
    """
    Create a simple error/warning/success icon
    
    Args:
        filename: Output filename (e.g., 'error.png')
        color: RGB tuple for the background (e.g., (229, 57, 53))
        symbol: Symbol to draw ('!', 'X', '✓')
        output_dir: Output directory path
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    size = 128
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw circle background
    padding = 10
    draw.ellipse([padding, padding, size-padding, size-padding], fill=color)

    # Draw symbol
    if symbol == '!':
        # Exclamation mark
        draw.rectangle([size//2 - 8, 25, size//2 + 8, 70], fill='white')
        draw.ellipse([size//2 - 10, 80, size//2 + 10, 100], fill='white')
    elif symbol == 'X':
        # X mark
        line_width = 12
        offset = 30
        # First diagonal
        draw.line([offset, offset, size-offset, size-offset], fill='white', width=line_width)
        # Second diagonal
        draw.line([offset, size-offset, size-offset, offset], fill='white', width=line_width)
    elif symbol == '✓':
        # Check mark
        points = [(35, 65), (55, 85), (90, 40)]
        draw.line([points[0], points[1]], fill='white', width=12)
        draw.line([points[1], points[2]], fill='white', width=12)

    output_path = os.path.join(output_dir, filename)
    img.save(output_path)
    print(f'✓ Created {output_path}')


def main():
    """Main function to create all icons"""
    print("=" * 60)
    print("Creating Error Icons")
    print("=" * 60)

    icons = [
        ('error.png', (229, 57, 53), 'X', 'Error icon (Red)'),
        ('warning.png', (255, 152, 0), '!', 'Warning icon (Orange)'),
        ('success.png', (76, 175, 80), '✓', 'Success icon (Green)'),
        ('info.png', (33, 150, 243), '!', 'Info icon (Blue)'),
    ]

    for filename, color, symbol, description in icons:
        print(f"\nCreating {description}...")
        create_error_icon(filename, color, symbol)

    print("\n" + "=" * 60)
    print("✅ All icons created successfully!")
    print("=" * 60)
    print("\nIcons are saved in: resources/icons/")
    print("\nYou can now use these icons in your application:")
    print("  from utils.icon_utils import get_error_icon")
    print("  icon = get_error_icon(size=(64, 64))")


if __name__ == '__main__':
    main()
