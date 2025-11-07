# -*- coding: utf-8 -*-
"""
Light Theme V2 - Optimized for GUI Redesign
- Compact buttons (32px height)
- Better spacing (8px grid)
- Improved typography
- Material Design colors
"""

# Material Design Color Palette
COLORS = {
    "primary": "#1E88E5",
    "primary_dark": "#1565C0",
    "primary_hover": "#2196F3",
    "success": "#4CAF50",
    "success_hover": "#66BB6A",
    "warning": "#FF9800",
    "warning_hover": "#FFB74D",
    "danger": "#F44336",
    "danger_hover": "#E57373",
    "info": "#008080",
    "info_hover": "#009999",
    "gray": "#666666",
    "gray_hover": "#808080",
    "background": "#FAFAFA",
    "surface": "#FFFFFF",
    "border": "#E0E0E0",
    "divider": "#E0E0E0",
    "hover": "#EEEEEE",
    "text_primary": "#212121",
    "text_secondary": "#757575",
}

# Unified Light Theme V2
LIGHT_STYLESHEET_V2 = """
/* ============================================
   GLOBAL STYLES - Light Theme V2
   ============================================ */
QWidget {
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
    color: #212121;
    background-color: #FAFAFA;
}

/* ============================================
   TYPOGRAPHY
   ============================================ */
QLabel {
    color: #212121;
    font-size: 13px;
    background: transparent;
}

/* ============================================
   BUTTONS - COMPACT (32px height)
   ============================================ */
QPushButton {
    background: #1E88E5;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 12px;
    min-height: 32px;
    max-height: 32px;
    font-weight: 500;
    font-size: 13px;
}

QPushButton:hover {
    background: #2196F3;
}

QPushButton:pressed {
    background: #1565C0;
}

QPushButton:disabled {
    background: #E0E0E0;
    color: #9E9E9E;
}

/* Success Buttons (Green) */
QPushButton[objectName*="save"],
QPushButton[objectName*="success"],
QPushButton[objectName*="luu"],
QPushButton[objectName*="generate"] {
    background: #4CAF50;
}

QPushButton[objectName*="save"]:hover,
QPushButton[objectName*="success"]:hover,
QPushButton[objectName*="luu"]:hover,
QPushButton[objectName*="generate"]:hover {
    background: #66BB6A;
}

QPushButton[objectName*="save"]:pressed,
QPushButton[objectName*="success"]:pressed,
QPushButton[objectName*="luu"]:pressed,
QPushButton[objectName*="generate"]:pressed {
    background: #388E3C;
}

/* Warning Buttons (Orange) */
QPushButton[objectName*="import"],
QPushButton[objectName*="warning"],
QPushButton[objectName*="nhap"],
QPushButton[objectName*="auto"] {
    background: #FF9800;
}

QPushButton[objectName*="import"]:hover,
QPushButton[objectName*="warning"]:hover,
QPushButton[objectName*="nhap"]:hover,
QPushButton[objectName*="auto"]:hover {
    background: #FFB74D;
}

/* Danger Buttons (Red) */
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

/* Info Buttons (Teal) */
QPushButton[objectName*="check"],
QPushButton[objectName*="info"],
QPushButton[objectName*="kiem"],
QPushButton[objectName*="test"],
QPushButton[objectName*="primary"] {
    background: #008080;
}

QPushButton[objectName*="check"]:hover,
QPushButton[objectName*="info"]:hover,
QPushButton[objectName*="kiem"]:hover,
QPushButton[objectName*="test"]:hover,
QPushButton[objectName*="primary"]:hover {
    background: #009999;
}

/* Gray/Browse Buttons */
QPushButton[objectName*="browse"],
QPushButton[objectName*="expand"],
QPushButton[objectName*="collapse"] {
    background: #757575;
}

QPushButton[objectName*="browse"]:hover,
QPushButton[objectName*="expand"]:hover,
QPushButton[objectName*="collapse"]:hover {
    background: #9E9E9E;
}

/* ============================================
   TEXT INPUTS - COMPACT (32px height)
   ============================================ */
QLineEdit, QTextEdit, QPlainTextEdit {
    background: #FFFFFF;
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    padding: 8px 12px;
    color: #212121;
    font-size: 13px;
    min-height: 32px;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 2px solid #1E88E5;
    padding: 7px 11px;
}

QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {
    background: #F5F5F5;
    color: #9E9E9E;
    border-color: #EEEEEE;
}

QLineEdit:read-only {
    background: #F5F5F5;
    color: #424242;
}

/* ============================================
   COMBO BOX
   ============================================ */
QComboBox {
    background: #FFFFFF;
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    padding: 8px 12px;
    min-height: 32px;
    min-width: 100px;
    font-size: 13px;
    color: #212121;
}

QComboBox:hover {
    border: 1px solid #1E88E5;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

QComboBox QAbstractItemView {
    background: #FFFFFF;
    border: 1px solid #E0E0E0;
    selection-background-color: #1E88E5;
    selection-color: #FFFFFF;
    color: #212121;
    font-size: 13px;
    padding: 4px;
}

/* ============================================
   SPIN BOX
   ============================================ */
QSpinBox, QDoubleSpinBox {
    background: #FFFFFF;
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    padding: 8px 12px;
    min-height: 32px;
    font-size: 13px;
    color: #212121;
}

QSpinBox:focus, QDoubleSpinBox:focus {
    border: 2px solid #1E88E5;
    padding: 7px 11px;
}

/* ============================================
   LIST WIDGET - 120px height, monospace
   ============================================ */
QListWidget {
    background: #FFFFFF;
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    min-height: 120px;
    font-size: 12px;
    font-family: "Courier New", monospace;
    color: #212121;
    padding: 4px;
}

QListWidget::item {
    padding: 6px 8px;
    border-bottom: 1px solid #F5F5F5;
}

QListWidget::item:selected {
    background: #1E88E5;
    color: #FFFFFF;
}

QListWidget::item:hover {
    background: #EEEEEE;
}

/* ============================================
   TABLE WIDGET
   ============================================ */
QTableWidget {
    background: #FFFFFF;
    border: 1px solid #E0E0E0;
    border-radius: 6px;
    gridline-color: #F5F5F5;
    font-size: 13px;
    color: #212121;
}

QTableWidget::item {
    padding: 8px;
}

QTableWidget::item:selected {
    background: #1E88E5;
    color: #FFFFFF;
}

QTableWidget::item:hover {
    background: #EEEEEE;
}

QHeaderView::section {
    background: #F5F5F5;
    padding: 8px;
    border: none;
    border-bottom: 2px solid #1E88E5;
    font-weight: 600;
    font-size: 13px;
    color: #212121;
}

/* ============================================
   TAB WIDGET - COMPACT (13px font, less padding)
   ============================================ */
QTabWidget::pane {
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    background: #FFFFFF;
    padding: 4px;
}

QTabBar::tab {
    font-family: "Segoe UI", Arial, sans-serif;
    font-weight: 600;
    font-size: 13px;
    min-width: 100px;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    color: #FFFFFF;
    background: #BDBDBD;
}

QTabBar::tab:selected {
    background: #1E88E5;
    border-bottom: 3px solid #1565C0;
    padding-bottom: 5px;
    font-weight: 700;
}

QTabBar::tab:hover:!selected {
    background: #9E9E9E;
}

/* ============================================
   GROUP BOX - 8px spacing
   ============================================ */
QGroupBox {
    border: 1px solid #E0E0E0;
    border-radius: 6px;
    margin-top: 8px;
    padding-top: 8px;
    background: #FFFFFF;
    font-family: "Segoe UI", Arial, sans-serif;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 4px 12px;
    color: #212121;
    font-weight: 700;
    font-size: 14px;
}

/* ============================================
   SCROLL BAR - Compact
   ============================================ */
QScrollBar:vertical {
    border: none;
    background: #F5F5F5;
    width: 10px;
    margin: 0;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: #BDBDBD;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #9E9E9E;
}

QScrollBar::add-line:vertical, 
QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    border: none;
    background: #F5F5F5;
    height: 10px;
    margin: 0;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background: #BDBDBD;
    border-radius: 5px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background: #9E9E9E;
}

QScrollBar::add-line:horizontal, 
QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ============================================
   PROGRESS BAR
   ============================================ */
QProgressBar {
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    text-align: center;
    background: #F5F5F5;
    font-size: 12px;
    color: #212121;
    height: 24px;
}

QProgressBar::chunk {
    background: #1E88E5;
    border-radius: 3px;
}

/* ============================================
   CHECKBOX & RADIO BUTTON
   ============================================ */
QCheckBox, QRadioButton {
    spacing: 8px;
    font-size: 13px;
    color: #212121;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #9E9E9E;
    border-radius: 3px;
    background: #FFFFFF;
}

QCheckBox::indicator:checked {
    background: #1E88E5;
    border: 2px solid #1E88E5;
    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTgiIGhlaWdodD0iMTgiIHZpZXdCb3g9IjAgMCAxOCAxOCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJNNiA5TDggMTFMMTIgNyIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz48L3N2Zz4=);
}

QCheckBox::indicator:hover {
    border: 2px solid #1E88E5;
}

QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #9E9E9E;
    border-radius: 9px;
    background: #FFFFFF;
}

QRadioButton::indicator:checked {
    background: #1E88E5;
    border: 2px solid #1E88E5;
}

QRadioButton::indicator:hover {
    border: 2px solid #1E88E5;
}

/* ============================================
   TOOL BUTTON
   ============================================ */
QToolButton {
    background: transparent;
    border: none;
    padding: 6px;
    border-radius: 4px;
    font-size: 13px;
    color: #212121;
}

QToolButton:hover {
    background: #EEEEEE;
}

QToolButton:pressed {
    background: #E0E0E0;
}

/* ============================================
   MENU & MENU BAR
   ============================================ */
QMenuBar {
    background: #FFFFFF;
    border-bottom: 1px solid #E0E0E0;
    font-size: 13px;
}

QMenuBar::item {
    padding: 8px 16px;
    background: transparent;
}

QMenuBar::item:selected {
    background: #EEEEEE;
}

QMenu {
    background: #FFFFFF;
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    padding: 4px;
    font-size: 13px;
}

QMenu::item {
    padding: 8px 24px 8px 8px;
    border-radius: 2px;
}

QMenu::item:selected {
    background: #1E88E5;
    color: #FFFFFF;
}

QMenu::separator {
    height: 1px;
    background: #E0E0E0;
    margin: 4px 8px;
}

/* ============================================
   TOOLTIP
   ============================================ */
QToolTip {
    background: #424242;
    color: #FFFFFF;
    border: none;
    border-radius: 4px;
    padding: 6px 12px;
    font-size: 12px;
}
"""

def apply_light_theme_v2(app):
    """
    Apply Light Theme V2 with compact design
    
    Args:
        app: QApplication instance
    """
    app.setStyleSheet(LIGHT_STYLESHEET_V2)