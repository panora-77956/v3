# -*- coding: utf-8 -*-
"""
Full Material Design 3 Theme
With Roboto font, elevation shadows, and Material colors
"""

from PyQt5.QtGui import QFontDatabase, QFont
from PyQt5.QtWidgets import QGraphicsDropShadowEffect
from PyQt5.QtGui import QColor
import os

# Material Design 3 Color System
COLORS = {
    "primary": "#1E88E5",          # Blue
    "on_primary": "#FFFFFF",
    "primary_container": "#D1E4FF",
    "on_primary_container": "#001D36",
    
    "secondary": "#4CAF50",        # Green
    "on_secondary": "#FFFFFF",
    
    "error": "#F44336",            # Red
    "on_error": "#FFFFFF",
    
    "background": "#FDFBFF",
    "on_background": "#1A1C1E",
    
    "surface": "#FFFFFF",
    "on_surface": "#1A1C1E",
    "surface_variant": "#E1E2EC",
    
    "outline": "#73777F",
    "shadow": "#000000",
}

# Load Roboto fonts
def load_roboto_fonts():
    """Load Roboto font family into Qt"""
    fonts_dir = os.path.join(os.path.dirname(__file__), "fonts")
    fonts = [
        "Roboto-Regular.ttf",
        "Roboto-Medium.ttf",
        "Roboto-Bold.ttf"
    ]
    
    for font_file in fonts:
        font_path = os.path.join(fonts_dir, font_file)
        if os.path.exists(font_path):
            QFontDatabase.addApplicationFont(font_path)
            print(f"✅ Loaded: {font_file}")
        else:
            print(f"⚠ Missing: {font_file}")

# Material Design Elevation System
def add_elevation(widget, level=2):
    """
    Add Material Design elevation shadow to widget
    
    Levels:
    - 0: No shadow (flat on surface)
    - 1: 1dp elevation (raised button rest)
    - 2: 2dp elevation (raised button hover)
    - 3: 3dp elevation (refresh indicator, search bar)
    - 4: 4dp elevation (app bar)
    - 6: 6dp elevation (floating action button rest)
    - 8: 8dp elevation (button pressed, card raised)
    """
    if level == 0:
        widget.setGraphicsEffect(None)
        return
    
    shadow = QGraphicsDropShadowEffect()
    
    # Material Design shadow specs
    blur_radius = {
        1: 3,
        2: 6,
        3: 8,
        4: 10,
        6: 16,
        8: 24,
    }.get(level, 6)
    
    offset_y = {
        1: 1,
        2: 2,
        3: 3,
        4: 4,
        6: 6,
        8: 8,
    }.get(level, 2)
    
    shadow.setBlurRadius(blur_radius)
    shadow.setColor(QColor(0, 0, 0, 40))  # 16% opacity
    shadow.setOffset(0, offset_y)
    widget.setGraphicsEffect(shadow)

# Full Material Design Stylesheet
MATERIAL_STYLESHEET = """
/* Material Design 3 - Full Theme with Roboto */

QWidget {
    font-family: "Roboto", "Segoe UI", sans-serif;
    font-size: 14px;
    color: #1A1C1E;
    background-color: #FDFBFF;
}

/* Typography Scale */
QLabel {
    font-family: "Roboto", "Segoe UI", sans-serif;
    color: #1A1C1E;
}

/* Buttons - Material with elevation */
QPushButton {
    background: #1E88E5;
    color: white;
    border: none;
    border-radius: 20px;  /* Material Design uses more rounded corners */
    padding: 10px 24px;
    min-height: 40px;
    font-family: "Roboto Medium", "Roboto", sans-serif;
    font-weight: 500;
    font-size: 14px;
    letter-spacing: 0.1px;
}

QPushButton:hover {
    background: #2196F3;
}

QPushButton:pressed {
    background: #1565C0;
}

QPushButton:disabled {
    background: #E1E2EC;
    color: #73777F;
}

/* Success Buttons */
QPushButton[objectName*="save"],
QPushButton[objectName*="success"],
QPushButton[objectName*="luu"] {
    background: #4CAF50;
}

QPushButton[objectName*="save"]:hover,
QPushButton[objectName*="success"]:hover,
QPushButton[objectName*="luu"]:hover {
    background: #66BB6A;
}

/* Danger Buttons */
QPushButton[objectName*="delete"],
QPushButton[objectName*="danger"],
QPushButton[objectName*="xoa"] {
    background: #F44336;
}

QPushButton[objectName*="delete"]:hover,
QPushButton[objectName*="danger"]:hover,
QPushButton[objectName*="xoa"]:hover {
    background: #E57373;
}

/* Text Inputs - Material Design */
QLineEdit, QTextEdit {
    background: #FFFFFF;
    border: none;
    border-bottom: 1px solid #73777F;
    border-radius: 4px 4px 0 0;
    padding: 12px;
    color: #1A1C1E;
    font-family: "Roboto", sans-serif;
    font-size: 14px;
}

QLineEdit:focus, QTextEdit:focus {
    border-bottom: 2px solid #1E88E5;
    padding-bottom: 11px;
}

/* Group Box - Material Card */
QGroupBox {
    background: #FFFFFF;
    border: none;
    border-radius: 12px;
    margin-top: 12px;
    padding: 16px;
    font-family: "Roboto Medium", sans-serif;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 8px 16px;
    color: #1A1C1E;
    font-weight: 500;
    font-size: 16px;
    font-family: "Roboto Medium", sans-serif;
}

/* Tabs - Material Design */
QTabBar::tab {
    font-family: "Roboto Medium", sans-serif;
    font-weight: 500;
    font-size: 14px;
    padding: 12px 24px;
    margin-right: 4px;
    border-radius: 12px 12px 0 0;
    color: #73777F;
    background: transparent;
}

QTabBar::tab:selected {
    color: #1E88E5;
    background: #D1E4FF;
    border-bottom: 3px solid #1E88E5;
}

QTabBar::tab:hover:!selected {
    background: #E1E2EC;
}

/* Progress Bar - Material */
QProgressBar {
    border: none;
    border-radius: 4px;
    background: #E1E2EC;
    height: 8px;
    text-align: center;
}

QProgressBar::chunk {
    background: #1E88E5;
    border-radius: 4px;
}

/* Scroll Bar - Material */
QScrollBar:vertical {
    background: #F5F5F5;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background: #BDBDBD;
    border-radius: 6px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #9E9E9E;
}
"""

def apply_material_theme(app):
    """Apply full Material Design theme with Roboto fonts"""
    load_roboto_fonts()
    app.setStyleSheet(MATERIAL_STYLESHEET)
    
    # Set default font to Roboto
    roboto_font = QFont("Roboto", 14)
    app.setFont(roboto_font)
    
    print("✅ Material Design theme applied with Roboto fonts")
