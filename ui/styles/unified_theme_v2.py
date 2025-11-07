# -*- coding: utf-8 -*-
"""
Unified Theme System v2 - Video Super Ultra v1.0.0.0
Complete dark theme with flat design and consistent typography
PR#6: Complete UI/UX overhaul with 38 improvements - dark theme implementation
"""

# Dark Flat Color Palette (PR#6: Complete UI/UX Overhaul)
COLORS = {
    'primary': '#1E88E5',      # Blue - Primary/Info actions
    'primary_dark': '#1565C0',
    'primary_hover': '#2196F3',
    'success': '#4CAF50',      # Green - Success/Generate
    'success_hover': '#66BB6A',
    'warning': '#FF6B2C',      # Orange - Warning/Auto actions
    'warning_hover': '#FF8A50',
    'danger': '#F44336',       # Red - Delete/Danger
    'danger_hover': '#E57373',
    'info': '#008080',         # Teal - Info/Check
    'info_hover': '#009999',
    'gray': '#666666',         # Gray - Stop/Cancel
    'gray_hover': '#808080',
    'background': '#1E1E1E',   # Dark background
    'surface': '#2D2D2D',      # Dark surface
    'border': '#3D3D3D',       # Dark border
    'divider': '#3D3D3D',
    'hover': '#383838',
    'text_primary': '#E0E0E0',
    'text_secondary': '#B0B0B0',
}

# Unified Dark Theme Stylesheet with Segoe UI (PR#6: Complete UI/UX Overhaul)
UNIFIED_STYLESHEET = """
/* Global - Dark theme with Segoe UI, 13px base */
QWidget {
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
    color: #E0E0E0;
    background-color: #1E1E1E;
}

/* Labels - 13px normal weight */
QLabel {
    color: #E0E0E0;
    font-size: 13px;
    font-weight: normal;
    background: transparent;
}

/* Buttons - Flat dark design with consistent colors (PR#6) */
QPushButton {
    background: #1E88E5;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    min-height: 32px;
    font-weight: 600;
    font-size: 13px;
    font-family: "Segoe UI", Arial, sans-serif;
}

QPushButton:hover {
    background: #2196F3;
}

QPushButton:pressed {
    background: #1565C0;
}

QPushButton:disabled {
    background: #4D4D4D;
    color: #808080;
}

/* Settings panel buttons - 24px height (PR#6: Part E #27) */
QPushButton[objectName*="btn_check"],
QPushButton[objectName*="btn_delete"],
QPushButton[objectName*="btn_primary"] {
    min-height: 24px;
    padding: 4px 12px;
    font-size: 12px;
}

/* Success Buttons (Green) - Save/Generate actions (PR#6: Part G #35) */
QPushButton[objectName*="save"],
QPushButton[objectName*="success"],
QPushButton[objectName*="luu"],
QPushButton[objectName*="auto"] {
    background: #4CAF50;
}

QPushButton[objectName*="save"]:hover,
QPushButton[objectName*="success"]:hover,
QPushButton[objectName*="luu"]:hover,
QPushButton[objectName*="auto"]:hover {
    background: #66BB6A;
}

QPushButton[objectName*="save"]:pressed,
QPushButton[objectName*="success"]:pressed,
QPushButton[objectName*="luu"]:pressed,
QPushButton[objectName*="auto"]:pressed {
    background: #388E3C;
}

/* Warning Buttons (Orange) - Auto/Import actions (PR#6: Part B #7, Part G #35) */
QPushButton[objectName*="import"],
QPushButton[objectName*="warning"],
QPushButton[objectName*="nhap"] {
    background: #FF6B2C;
}

QPushButton[objectName*="import"]:hover,
QPushButton[objectName*="warning"]:hover,
QPushButton[objectName*="nhap"]:hover {
    background: #FF8A50;
}

QPushButton[objectName*="import"]:pressed,
QPushButton[objectName*="warning"]:pressed,
QPushButton[objectName*="nhap"]:pressed {
    background: #E65100;
}

/* Danger Buttons (Red) - Delete/Stop actions (PR#6: Part G #35) */
QPushButton[objectName*="delete"],
QPushButton[objectName*="danger"],
QPushButton[objectName*="xoa"],
QPushButton[objectName*="del"],
QPushButton[objectName*="stop"],
QPushButton[objectName*="dung"] {
    background: #F44336;
}

QPushButton[objectName*="delete"]:hover,
QPushButton[objectName*="danger"]:hover,
QPushButton[objectName*="xoa"]:hover,
QPushButton[objectName*="del"]:hover,
QPushButton[objectName*="stop"]:hover,
QPushButton[objectName*="dung"]:hover {
    background: #E57373;
}

QPushButton[objectName*="delete"]:pressed,
QPushButton[objectName*="danger"]:pressed,
QPushButton[objectName*="xoa"]:pressed,
QPushButton[objectName*="del"]:pressed,
QPushButton[objectName*="stop"]:pressed,
QPushButton[objectName*="dung"]:pressed {
    background: #D32F2F;
}

/* Info Buttons (Teal) - Check/Info actions (PR#6: Part E #31-33) */
QPushButton[objectName*="check"],
QPushButton[objectName*="info"],
QPushButton[objectName*="kiem"],
QPushButton[objectName*="test"] {
    background: #008080;
}

QPushButton[objectName*="check"]:hover,
QPushButton[objectName*="info"]:hover,
QPushButton[objectName*="kiem"]:hover,
QPushButton[objectName*="test"]:hover {
    background: #009999;
}

QPushButton[objectName*="check"]:pressed,
QPushButton[objectName*="info"]:pressed,
QPushButton[objectName*="kiem"]:pressed,
QPushButton[objectName*="test"]:pressed {
    background: #006666;
}

/* Gray Buttons - Stop/Cancel actions (PR#6: Part B #8) */
QPushButton[objectName*="gray"] {
    background: #666666;
}

QPushButton[objectName*="gray"]:hover {
    background: #808080;
}

QPushButton[objectName*="gray"]:pressed {
    background: #4D4D4D;
}

/* Text Inputs - Dark theme (PR#6: Part G #36) */
QLineEdit, QTextEdit, QPlainTextEdit {
    background: #2D2D2D;
    border: 1px solid #3D3D3D;
    border-radius: 4px;
    padding: 12px;
    color: #E0E0E0;
    font-size: 13px;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 2px solid #1E88E5;
    padding: 11px;
}

QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {
    background: #252525;
    color: #666666;
}

/* Combo Box - Dark theme */
QComboBox {
    background: #2D2D2D;
    border: 1px solid #3D3D3D;
    border-radius: 4px;
    padding: 10px;
    min-width: 100px;
    font-size: 13px;
    color: #E0E0E0;
}

QComboBox:hover {
    border: 1px solid #1E88E5;
}

QComboBox::drop-down {
    border: none;
    padding-right: 10px;
}

QComboBox QAbstractItemView {
    background: #2D2D2D;
    border: 1px solid #3D3D3D;
    selection-background-color: #1E88E5;
    selection-color: #FFFFFF;
    color: #E0E0E0;
    font-size: 13px;
}

/* Spin Box - Dark theme */
QSpinBox {
    background: #2D2D2D;
    border: 1px solid #3D3D3D;
    border-radius: 4px;
    padding: 10px;
    font-size: 13px;
    color: #E0E0E0;
}

QSpinBox:focus {
    border: 2px solid #1E88E5;
    padding: 9px;
}

/* List Widget - Dark theme (PR#6: Part E #24-25, #29-30) */
QListWidget {
    background: #2D2D2D;
    border: 1px solid #3D3D3D;
    border-radius: 4px;
    font-size: 12px;
    font-family: "Courier New", monospace;
    color: #E0E0E0;
}

QListWidget::item {
    padding: 8px;
    border-bottom: 1px solid #383838;
}

QListWidget::item:selected {
    background: #1E88E5;
    color: #FFFFFF;
}

QListWidget::item:hover {
    background: #383838;
}

/* Table Widget - Dark theme */
QTableWidget {
    background: #2D2D2D;
    border: 1px solid #3D3D3D;
    border-radius: 8px;
    gridline-color: #383838;
    font-size: 13px;
    color: #E0E0E0;
}

QTableWidget::item {
    padding: 8px;
}

QTableWidget::item:selected {
    background: #1E88E5;
    color: #FFFFFF;
}

QTableWidget::item:hover {
    background: #383838;
}

QHeaderView::section {
    background: #252525;
    padding: 10px;
    border: none;
    border-bottom: 2px solid #1E88E5;
    font-weight: bold;
    font-size: 14px;
    color: #E0E0E0;
}

/* Tab Widget - Dark theme */
QTabWidget::pane {
    border: 1px solid #3D3D3D;
    border-radius: 4px;
    background: #2D2D2D;
}

/* Tab Bar - Bold font with dark theme colors (PR#6: Part A #1-2, Part G #34) */
QTabBar::tab {
    font-family: "Segoe UI", Arial, sans-serif;
    font-weight: 700;
    font-size: 14px;
    min-width: 150px;
    padding: 12px 24px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    color: #E0E0E0;
    background: #383838;
}

/* Main navigation tabs - Different colors (PR#6: Part A #1, Part G #34) */
QTabBar::tab:nth-child(1) {
    background: #1E88E5;  /* Blue - Cài đặt */
}

QTabBar::tab:nth-child(2) {
    background: #4CAF50;  /* Green - Image2Video */
}

QTabBar::tab:nth-child(3) {
    background: #FF6B2C;  /* Orange - Text2Video */
}

QTabBar::tab:nth-child(4) {
    background: #9C27B0;  /* Purple - Video bán hàng */
}

QTabBar::tab:selected {
    border-bottom: 4px solid #FFFFFF;
    font-size: 15px;
    padding-bottom: 8px;
}

QTabBar::tab:hover:!selected {
    background-color: rgba(255, 255, 255, 0.15);
}

/* Group Box - Dark theme with compact spacing (PR#6: Part E #26) */
QGroupBox {
    border: 1px solid #3D3D3D;
    border-radius: 8px;
    margin-top: 6px;
    padding-top: 6px;
    background: #2D2D2D;
    font-family: "Segoe UI", Arial, sans-serif;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 6px 12px;
    color: #E0E0E0;
    font-weight: 700;
    font-size: 16px;
    font-family: "Segoe UI", Arial, sans-serif;
}

/* Scroll Bar - Dark theme (PR#6: Part E #30) */
QScrollBar:vertical {
    border: none;
    background: #252525;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #4D4D4D;
    border-radius: 5px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #666666;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    border: none;
    background: #252525;
    height: 10px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background: #4D4D4D;
    border-radius: 5px;
    min-width: 20px;
}

QScrollBar::handle:horizontal:hover {
    background: #666666;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* Progress Bar - Dark theme */
QProgressBar {
    border: 1px solid #3D3D3D;
    border-radius: 4px;
    text-align: center;
    background: #252525;
    font-size: 13px;
    color: #E0E0E0;
}

QProgressBar::chunk {
    background: #1E88E5;
    border-radius: 3px;
}

/* Checkbox - Dark theme */
QCheckBox {
    spacing: 8px;
    font-size: 13px;
    color: #E0E0E0;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #666666;
    border-radius: 3px;
    background: #2D2D2D;
}

QCheckBox::indicator:checked {
    background: #1E88E5;
    border: 2px solid #1E88E5;
}

QCheckBox::indicator:hover {
    border: 2px solid #1E88E5;
}

/* Radio Button - Dark theme */
QRadioButton {
    spacing: 8px;
    font-size: 13px;
    color: #E0E0E0;
}

QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #666666;
    border-radius: 9px;
    background: #2D2D2D;
}

QRadioButton::indicator:checked {
    background: #1E88E5;
    border: 2px solid #1E88E5;
}

QRadioButton::indicator:hover {
    border: 2px solid #1E88E5;
}

/* Tool Button - Dark theme */
QToolButton {
    background: transparent;
    border: none;
    padding: 8px;
    border-radius: 4px;
    font-size: 13px;
    color: #E0E0E0;
}

QToolButton:hover {
    background: #383838;
}

QToolButton:pressed {
    background: #3D3D3D;
}
"""


def apply_theme(app):
    """
    Apply unified Material Design v2 theme to the application
    
    Args:
        app: QApplication instance
    """
    app.setStyleSheet(UNIFIED_STYLESHEET)
