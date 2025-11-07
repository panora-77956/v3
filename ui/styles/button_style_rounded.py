# ui/styles/button_style_rounded.py
"""
Rounded Button Style - Theo hình mẫu
- Border-radius lớn (20px+)
- Font đậm hơn (+1px, bold)
- Icon + Text
"""

ROUNDED_BUTTON_STYLE = """
/* ============================================
   ROUNDED BUTTONS - New Design
   ============================================ */

QPushButton {
    background: #1E88E5;
    color: white;
    border: none;
    border-radius: 24px;  /* ROUNDED - 24px for 48px height */
    padding: 10px 24px;
    min-height: 48px;
    font-family: "Segoe UI", Arial, sans-serif;
    font-weight: 700;  /* BOLD */
    font-size: 14px;   /* +1px from 13px */
    letter-spacing: 0.3px;
}

QPushButton:hover {
    background: #2196F3;
    transform: scale(1.02);
}

QPushButton:pressed {
    background: #1565C0;
}

QPushButton:disabled {
    background: #E0E0E0;
    color: #9E9E9E;
}

/* Success - Green (Viết kịch bản, Tạo video, etc) */
QPushButton[objectName*="success"],
QPushButton[objectName*="generate"],
QPushButton[objectName*="viet"],
QPushButton[objectName*="tao"] {
    background: #FF6B35;  /* Orange like image */
    border-radius: 24px;
}

QPushButton[objectName*="success"]:hover {
    background: #FF8555;
}

/* Info - Gray (Tạo ảnh) */
QPushButton[objectName*="image"],
QPushButton[objectName*="anh"] {
    background: #BDBDBD;  /* Gray like image */
    color: #424242;
    border-radius: 24px;
}

QPushButton[objectName*="image"]:hover {
    background: #D0D0D0;
}

/* Video - Purple */
QPushButton[objectName*="video"] {
    background: #9C27B0;  /* Purple like image */
    border-radius: 24px;
}

QPushButton[objectName*="video"]:hover {
    background: #AB47BC;
}

/* Stop - Pink/Light Red */
QPushButton[objectName*="stop"],
QPushButton[objectName*="dung"] {
    background: #FFB3C1;  /* Light pink like image */
    color: #D32F2F;
    border-radius: 24px;
}

QPushButton[objectName*="stop"]:hover {
    background: #FFC4D0;
}

/* Compact buttons (32px height) */
QPushButton.compact {
    min-height: 32px;
    border-radius: 16px;
    padding: 6px 16px;
    font-size: 13px;
}

/* Large action buttons (56px height) */
QPushButton.large {
    min-height: 56px;
    border-radius: 28px;
    padding: 14px 32px;
    font-size: 15px;
    font-weight: 700;
}
"""