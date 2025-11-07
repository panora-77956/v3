# -*- coding: utf-8 -*-
"""
SceneResultCard Widget - Compact card with 50% image size
"""
import json

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


class SceneResultCard(QFrame):
    """
    Compact scene result card with:
    - 80x80px image preview (compact size)
    - Alternating backgrounds (#FFFFFF / #E3F2FD)
    - Title, description, speech text
    - Action buttons: Prompt, Recreate, Generate Video
    """

    prompt_requested = pyqtSignal(int)  # scene index
    recreate_requested = pyqtSignal(int)  # scene index
    generate_video_requested = pyqtSignal(int)  # scene index

    def __init__(self, scene_index, scene_data, alternating_color=False, parent=None):
        super().__init__(parent)
        self.scene_index = scene_index
        self.scene_data = scene_data
        self.alternating_color = alternating_color

        # Set alternating background - Issue 2: Remove explicit border for flat design
        # Use alternating backgrounds but with flat design (no explicit border)
        bg_color = "#E3F2FD" if alternating_color else "#FFFFFF"
        self.setStyleSheet(f"""
            QFrame {{
                background: {bg_color};
                border: none;
                border-radius: 8px;
                margin: 4px 0px;
            }}
        """)

        self._build_ui()

    def _build_ui(self):
        """Build the compact card UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # Left: Image preview - Issue 1: Increased to 320x200px for better visibility
        self.img_preview = QLabel()
        self.img_preview.setFixedSize(320, 200)
        self.img_preview.setStyleSheet("""
            QLabel {
                background: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }
        """)
        self.img_preview.setAlignment(Qt.AlignCenter)
        self.img_preview.setText("Chưa tạo")
        self.img_preview.setFont(QFont("Segoe UI", 9))
        main_layout.addWidget(self.img_preview)

        # Right: Content area
        content_layout = QVBoxLayout()
        content_layout.setSpacing(4)

        # Title (blue, bold) - Font size set to 16px per requirement
        lbl_title = QLabel(f"Cảnh {self.scene_index}")
        lbl_title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        lbl_title.setStyleSheet("color: #1976D2;")
        content_layout.addWidget(lbl_title)

        # Description - Issue 5d: Set font size to 13px
        desc_text = self.scene_data.get('description', '') or self.scene_data.get('desc', '')
        if desc_text and len(desc_text) > 80:
            desc_text = desc_text[:80] + "..."
        lbl_desc = QLabel(desc_text or "Không có mô tả")
        lbl_desc.setWordWrap(True)
        lbl_desc.setFont(QFont("Segoe UI", 13))
        lbl_desc.setStyleSheet("color: #424242; border: none;")  # Issue 5c: Remove border
        content_layout.addWidget(lbl_desc)

        # Speech text (Lời thoại) - Issue 1: Set font size to 12px (smaller, secondary info)
        speech_text = self.scene_data.get('speech', '') or self.scene_data.get('voice_over', '')
        if speech_text:
            if len(speech_text) > 100:
                speech_text = speech_text[:100] + "..."
            lbl_speech = QLabel(f"🎤 Lời thoại: {speech_text}")
            lbl_speech.setWordWrap(True)
            lbl_speech.setFont(QFont("Segoe UI", 12))
            lbl_speech.setStyleSheet("color: #757575; border: none;")  # Issue 5c: Remove border
            content_layout.addWidget(lbl_speech)

        # Action buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(4)

        # Issue 5c: Button style without unnecessary borders
        btn_style = """
            QPushButton {
                background: transparent;
                border: 1px solid #BDBDBD;
                border-radius: 4px;
                padding: 4px 10px;
                color: #616161;
                font-size: 10px;
                min-height: 24px;
            }
            QPushButton:hover {
                background: #F5F5F5;
                border-color: #1976D2;
                color: #1976D2;
            }
        """

        btn_prompt = QPushButton("📝 Prompt")
        btn_prompt.setStyleSheet(btn_style)
        btn_prompt.clicked.connect(lambda: self._show_prompt_dialog())
        buttons_layout.addWidget(btn_prompt)

        btn_recreate = QPushButton("🔄 Tạo lại")
        btn_recreate.setStyleSheet(btn_style)
        btn_recreate.clicked.connect(lambda: self.recreate_requested.emit(self.scene_index))
        buttons_layout.addWidget(btn_recreate)

        btn_video = QPushButton("🎬 Tạo Video")
        btn_video.setStyleSheet(btn_style)
        btn_video.clicked.connect(lambda: self.generate_video_requested.emit(self.scene_index))
        buttons_layout.addWidget(btn_video)

        buttons_layout.addStretch()
        content_layout.addLayout(buttons_layout)
        content_layout.addStretch()

        main_layout.addLayout(content_layout, 1)

    def _show_prompt_dialog(self):
        """Show prompt dialog with JSON format"""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Prompts - Cảnh {self.scene_index}")
        dialog.setMinimumSize(700, 500)

        layout = QVBoxLayout(dialog)

        # Title
        title = QLabel(f"📝 Prompts cho Cảnh {self.scene_index}")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(title)

        # Image prompt section
        lbl_img = QLabel("📷 Prompt Ảnh:")
        lbl_img.setFont(QFont("Segoe UI", 11, QFont.Bold))
        layout.addWidget(lbl_img)

        ed_img_prompt = QTextEdit()
        ed_img_prompt.setReadOnly(True)
        img_prompt = self.scene_data.get('prompt_image', '')
        # Format as JSON if possible
        try:
            if isinstance(img_prompt, dict):
                img_prompt = json.dumps(img_prompt, ensure_ascii=False, indent=2)
            elif isinstance(img_prompt, str) and img_prompt.strip().startswith('{'):
                img_prompt = json.dumps(json.loads(img_prompt), ensure_ascii=False, indent=2)
        except:
            pass
        ed_img_prompt.setPlainText(img_prompt)
        ed_img_prompt.setMaximumHeight(180)
        ed_img_prompt.setFont(QFont("Courier New", 9))
        layout.addWidget(ed_img_prompt)

        btn_copy_img = QPushButton("📋 Copy Prompt Ảnh")
        btn_copy_img.clicked.connect(lambda: self._copy_to_clipboard(ed_img_prompt.toPlainText()))
        layout.addWidget(btn_copy_img)

        # Video prompt section
        lbl_vid = QLabel("🎬 Prompt Video:")
        lbl_vid.setFont(QFont("Segoe UI", 11, QFont.Bold))
        layout.addWidget(lbl_vid)

        ed_vid_prompt = QTextEdit()
        ed_vid_prompt.setReadOnly(True)
        vid_prompt = self.scene_data.get('prompt_video', '')
        # Format as JSON if possible
        try:
            if isinstance(vid_prompt, dict):
                vid_prompt = json.dumps(vid_prompt, ensure_ascii=False, indent=2)
            elif isinstance(vid_prompt, str) and vid_prompt.strip().startswith('{'):
                vid_prompt = json.dumps(json.loads(vid_prompt), ensure_ascii=False, indent=2)
        except:
            pass
        ed_vid_prompt.setPlainText(vid_prompt)
        ed_vid_prompt.setMaximumHeight(180)
        ed_vid_prompt.setFont(QFont("Courier New", 9))
        layout.addWidget(ed_vid_prompt)

        btn_copy_vid = QPushButton("📋 Copy Prompt Video")
        btn_copy_vid.clicked.connect(lambda: self._copy_to_clipboard(ed_vid_prompt.toPlainText()))
        layout.addWidget(btn_copy_vid)

        # Close button
        btn_close = QPushButton("✖ Đóng")
        btn_close.clicked.connect(dialog.close)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)

        dialog.exec_()

    def _copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        QMessageBox.information(self, "Thành công", "Đã copy vào clipboard!")

    def set_image(self, image_bytes):
        """Set image from bytes - Issue 1: Updated to 320x200px"""
        pixmap = QPixmap()
        pixmap.loadFromData(image_bytes)
        self.img_preview.setPixmap(pixmap.scaled(320, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def set_image_pixmap(self, pixmap):
        """Set image from pixmap - Issue 1: Updated to 320x200px"""
        self.img_preview.setPixmap(pixmap.scaled(320, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def set_image_path(self, path):
        """Set image from file path - Issue 1: Updated to 320x200px"""
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            self.img_preview.setPixmap(pixmap.scaled(320, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
