import json
import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QHBoxLayout, QPushButton, QTabWidget, QTextEdit, 
    QVBoxLayout, QWidget, QLabel, QScrollArea, QFrame, QGroupBox,
    QApplication, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

# Import the prompt builder function to show actual API prompt
try:
    from services.google.labs_flow_client import _build_complete_prompt_text
except ImportError:
    # Fallback if import fails
    def _build_complete_prompt_text(prompt_data):
        """Fallback: just convert to string"""
        if isinstance(prompt_data, str):
            return prompt_data
        return json.dumps(prompt_data, ensure_ascii=False, indent=2)


class PromptViewer(QDialog):
    """Enhanced Prompt Viewer with parsed JSON sections"""

    def __init__(self, prompt_json: str, dialogues=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chi tiết Prompt")
        self.resize(950, 700)

        # Parse JSON
        try:
            self.data = json.loads(prompt_json)
        except (json.JSONDecodeError, TypeError) as e:
            print(f"[Warning] Could not parse prompt JSON: {e}")
            self.data = {}

        self.prompt_json = prompt_json

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Tabs
        tabs = QTabWidget()
        tabs.setFont(QFont("Segoe UI", 11, QFont.Bold))

        # Tab 1: API Prompt (NEW - The actual text sent to Google Labs)
        tabs.addTab(self._build_api_prompt_tab(), "🚀 API Prompt")

        # Tab 2: Prompts (Vietnamese + English)
        tabs.addTab(self._build_prompts_tab(), "📝 Prompts")

        # Tab 3: Details (Audio, Camera, Character...)
        tabs.addTab(self._build_details_tab(), "🎬 Chi tiết")

        # Tab 4: Raw JSON
        tabs.addTab(self._build_json_tab(), "📄 JSON")

        # Tab 5: Dialogues (if available)
        if dialogues:
            tabs.addTab(self._build_dialogues_tab(dialogues), "💬 Lời thoại")

        main_layout.addWidget(tabs)

        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_close = QPushButton("✖ Đóng")
        btn_close.setFixedHeight(40)
        btn_close.setFixedWidth(120)
        btn_close.setStyleSheet("""
            QPushButton {
                background: #1E88E5;
                color: white;
                border: none;
                border-radius: 20px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background: #2196F3; }
        """)
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        main_layout.addLayout(btn_layout)

        # Style
        self.setStyleSheet("""
            QDialog { background: #FAFAFA; }
            QTabWidget::pane { border: none; background: white; }
            QTabBar::tab {
                min-width: 120px;
                padding: 12px 16px;
                font-weight: 700;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background: #00ACC1;
                color: white;
            }
            QTabBar::tab:!selected {
                background: #E0E0E0;
                color: #616161;
            }
            QTabBar::tab:hover {
                background: #B2EBF2;
            }
        """)

    def _build_api_prompt_tab(self):
        """Tab showing the actual formatted prompt sent to Google Labs API"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Header with explanation
        header = QLabel(
            "📤 This is the ACTUAL formatted text prompt sent to Google Labs Flow API.\n"
            "The API converts the JSON structure below into this optimized text format."
        )
        header.setWordWrap(True)
        header.setFont(QFont("Segoe UI", 11))
        header.setStyleSheet("""
            QLabel {
                background: #E3F2FD;
                color: #0D47A1;
                padding: 12px;
                border-radius: 6px;
                border-left: 4px solid #1976D2;
            }
        """)
        layout.addWidget(header)

        # Build the actual API prompt text
        try:
            api_prompt_text = _build_complete_prompt_text(self.data)
        except Exception as e:
            api_prompt_text = f"[Error building API prompt: {e}]\n\nFallback to JSON:\n{self.prompt_json}"

        # Text area showing the formatted prompt
        text_edit = QTextEdit()
        text_edit.setPlainText(api_prompt_text)
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("Consolas", 10))
        text_edit.setStyleSheet("""
            QTextEdit {
                background: #FAFAFA;
                border: 2px solid #2196F3;
                border-radius: 6px;
                padding: 12px;
                font-family: 'Consolas', 'Courier New', monospace;
                line-height: 1.5;
            }
        """)
        layout.addWidget(text_edit)

        # Info label
        info = QLabel(
            "💡 Tip: This text format is optimized for Google's Veo video generation model. "
            "It includes character consistency rules, visual style locks, and scene descriptions."
        )
        info.setWordWrap(True)
        info.setFont(QFont("Segoe UI", 9))
        info.setStyleSheet("color: #666; padding: 8px;")
        layout.addWidget(info)

        # Button layout
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        # Copy button
        btn_copy = QPushButton("📋 Copy to Clipboard")
        btn_copy.setFixedHeight(40)
        btn_copy.setStyleSheet("""
            QPushButton {
                background: #2196F3;
                color: white;
                border: none;
                border-radius: 20px;
                font-weight: bold;
                font-size: 13px;
                padding: 0 20px;
            }
            QPushButton:hover { background: #1976D2; }
        """)
        btn_copy.clicked.connect(lambda: self._copy_to_clipboard(api_prompt_text))
        btn_layout.addWidget(btn_copy)
        
        # Save button
        btn_save = QPushButton("💾 Save as Text File")
        btn_save.setFixedHeight(40)
        btn_save.setStyleSheet("""
            QPushButton {
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 20px;
                font-weight: bold;
                font-size: 13px;
                padding: 0 20px;
            }
            QPushButton:hover { background: #45a049; }
        """)
        btn_save.clicked.connect(lambda: self._save_text_prompt(api_prompt_text))
        btn_layout.addWidget(btn_save)
        
        layout.addLayout(btn_layout)

        return widget

    def _build_prompts_tab(self):
        """Tab 1: Show Vietnamese and English prompts with copy buttons"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Get localization data
        loc = self.data.get('localization', {})
        vi_data = loc.get('vi', {})
        en_data = loc.get('en', {})

        vi_prompt = vi_data.get('prompt', '')
        en_prompt = en_data.get('prompt', '')

        # If no localization, try old format
        if not vi_prompt:
            vi_prompt = self.data.get('prompt_vi', '')
        if not en_prompt:
            en_prompt = self.data.get('prompt_tgt', '')

        # Vietnamese Prompt Section
        vi_group = self._create_prompt_section(
            "📷 Prompt Ảnh (Vietnamese)",
            vi_prompt or "(Không có)",
            "#1E88E5"
        )
        layout.addWidget(vi_group)

        # English Prompt Section
        en_group = self._create_prompt_section(
            "🎬 Prompt Video (Target Language)",
            en_prompt or "(Không có)",
            "#00838F"
        )
        layout.addWidget(en_group)

        layout.addStretch()
        return widget

    def _create_prompt_section(self, title, text, color):
        """Create a prompt section with copy button"""
        group = QGroupBox(title)
        group.setFont(QFont("Segoe UI", 12, QFont.Bold))
        group.setStyleSheet(f"""
            QGroupBox {{
                background: white;
                border: 2px solid {color};
                border-radius: 8px;
                margin-top: 12px;
                padding: 16px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 4px 12px;
                background: {color};
                color: white;
                border-radius: 4px;
                left: 12px;
            }}
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # Text area
        text_edit = QTextEdit()
        text_edit.setPlainText(text)
        text_edit.setReadOnly(True)
        text_edit.setMinimumHeight(120)
        text_edit.setMaximumHeight(180)
        text_edit.setStyleSheet("""
            QTextEdit {
                background: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 10px;
                font-size: 12px;
                font-family: 'Segoe UI';
            }
        """)
        layout.addWidget(text_edit)

        # Copy button
        btn_copy = QPushButton("📋 Copy")
        btn_copy.setFixedHeight(36)
        btn_copy.setFixedWidth(100)
        btn_copy.setStyleSheet(f"""
            QPushButton {{
                background: {color};
                color: white;
                border: none;
                border-radius: 18px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{ opacity: 0.9; }}
        """)
        btn_copy.clicked.connect(lambda: self._copy_to_clipboard(text))
        layout.addWidget(btn_copy)

        return group

    def _build_details_tab(self):
        """Tab 2: Show detailed information"""
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Scene Info
        scene_id = self.data.get('scene_id', 'N/A')
        objective = self.data.get('objective', '')
        if objective:
            layout.addWidget(self._create_info_section(
                "🎯 Objective", 
                objective,
                "#FF6B35"
            ))

        # Character Details
        char_details = self.data.get('character_details', '')
        if char_details:
            layout.addWidget(self._create_info_section(
                "👥 Character Details",
                char_details,
                "#9C27B0"
            ))

        # Setting Details
        setting = self.data.get('setting_details', '')
        if setting:
            layout.addWidget(self._create_info_section(
                "🌍 Setting",
                setting,
                "#4CAF50"
            ))

        # Audio Section
        audio = self.data.get('audio', {})
        if audio:
            layout.addWidget(self._create_audio_section(audio))

        # Camera Direction
        camera = self.data.get('camera_direction', [])
        if camera:
            layout.addWidget(self._create_camera_section(camera))

        # Constraints
        constraints = self.data.get('constraints', {})
        if constraints:
            layout.addWidget(self._create_constraints_section(constraints))

        # Negatives
        negatives = self.data.get('negatives', [])
        if negatives:
            layout.addWidget(self._create_list_section(
                "🚫 Negatives",
                negatives,
                "#F44336"
            ))

        layout.addStretch()
        scroll.setWidget(content)

        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

        return widget

    def _create_info_section(self, title, text, color):
        """Create an info section"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: white;
                border-left: 4px solid {color};
                border-radius: 4px;
                padding: 12px;
            }}
        """)

        layout = QVBoxLayout(frame)

        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        title_label.setStyleSheet(f"color: {color};")
        layout.addWidget(title_label)

        text_label = QLabel(text)
        text_label.setWordWrap(True)
        text_label.setFont(QFont("Segoe UI", 10))
        text_label.setStyleSheet("color: #424242; padding: 8px 0;")
        layout.addWidget(text_label)

        return frame

    def _create_audio_section(self, audio):
        """Create audio settings section"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: white;
                border-left: 4px solid #00BCD4;
                border-radius: 4px;
                padding: 12px;
            }
        """)

        layout = QVBoxLayout(frame)

        title = QLabel("🎙️ Audio Settings")
        title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        title.setStyleSheet("color: #00BCD4;")
        layout.addWidget(title)

        # Voiceover
        vo = audio.get('voiceover', {})
        if vo:
            vo_text = f"""
<b>Language:</b> {vo.get('language', 'N/A')}<br>
<b>TTS Provider:</b> {vo.get('tts_provider', 'N/A')}<br>
<b>Voice ID:</b> {vo.get('voice_id', 'N/A')}<br>
<b>Speaking Style:</b> {vo.get('speaking_style', 'N/A')}<br>
<b>Text:</b> {vo.get('text', 'N/A')}
            """
            vo_label = QLabel(vo_text)
            vo_label.setWordWrap(True)
            vo_label.setFont(QFont("Segoe UI", 10))
            layout.addWidget(vo_label)

        # Background Music
        bgm = audio.get('background_music', {})
        if bgm:
            bgm_text = f"""
<b>Background Music:</b> {bgm.get('type', 'N/A')}<br>
<b>Description:</b> {bgm.get('description', 'N/A')}<br>
<b>Mood:</b> {bgm.get('mood', 'N/A')}
            """
            bgm_label = QLabel(bgm_text)
            bgm_label.setWordWrap(True)
            bgm_label.setFont(QFont("Segoe UI", 10))
            layout.addWidget(bgm_label)

        return frame

    def _create_camera_section(self, camera):
        """Create camera direction section"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: white;
                border-left: 4px solid #FF9800;
                border-radius: 4px;
                padding: 12px;
            }
        """)

        layout = QVBoxLayout(frame)

        title = QLabel("🎥 Camera Direction")
        title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        title.setStyleSheet("color: #FF9800;")
        layout.addWidget(title)

        for i, shot in enumerate(camera, 1):
            shot_text = f"<b>{shot.get('t', 'N/A')}</b>: {shot.get('shot', 'N/A')}"
            shot_label = QLabel(shot_text)
            shot_label.setWordWrap(True)
            shot_label.setFont(QFont("Segoe UI", 10))
            shot_label.setStyleSheet("padding: 4px 0; color: #616161;")
            layout.addWidget(shot_label)

        return frame

    def _create_constraints_section(self, constraints):
        """Create constraints section"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: white;
                border-left: 4px solid #3F51B5;
                border-radius: 4px;
                padding: 12px;
            }
        """)

        layout = QVBoxLayout(frame)

        title = QLabel("⚙️ Constraints")
        title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        title.setStyleSheet("color: #3F51B5;")
        layout.addWidget(title)

        text = f"""
<b>Duration:</b> {constraints.get('duration_seconds', 'N/A')}s<br>
<b>Aspect Ratio:</b> {constraints.get('aspect_ratio', 'N/A')}<br>
<b>Resolution:</b> {constraints.get('resolution', 'N/A')}<br>
<b>Visual Styles:</b> {', '.join(constraints.get('visual_style_tags', []))}
        """

        label = QLabel(text)
        label.setWordWrap(True)
        label.setFont(QFont("Segoe UI", 10))
        label.setStyleSheet("color: #424242; padding: 8px 0;")
        layout.addWidget(label)

        return frame

    def _create_list_section(self, title, items, color):
        """Create a list section"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: white;
                border-left: 4px solid {color};
                border-radius: 4px;
                padding: 12px;
            }}
        """)

        layout = QVBoxLayout(frame)

        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        title_label.setStyleSheet(f"color: {color};")
        layout.addWidget(title_label)

        for item in items:
            item_label = QLabel(f"• {item}")
            item_label.setWordWrap(True)
            item_label.setFont(QFont("Segoe UI", 10))
            item_label.setStyleSheet("color: #616161; padding: 2px 0;")
            layout.addWidget(item_label)

        return frame

    def _build_json_tab(self):
        """Tab 3: Raw JSON"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(self.prompt_json)
        text_edit.setFont(QFont("Courier New", 10))
        text_edit.setStyleSheet("""
            QTextEdit {
                background: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 12px;
            }
        """)
        layout.addWidget(text_edit)

        # Save JSON button
        btn_save_json = QPushButton("💾 Save as JSON File")
        btn_save_json.setFixedHeight(40)
        btn_save_json.setStyleSheet("""
            QPushButton {
                background: #FF9800;
                color: white;
                border: none;
                border-radius: 20px;
                font-weight: bold;
                font-size: 13px;
                padding: 0 20px;
            }
            QPushButton:hover { background: #F57C00; }
        """)
        btn_save_json.clicked.connect(lambda: self._save_json_prompt(self.prompt_json))
        layout.addWidget(btn_save_json)

        return widget

    def _build_dialogues_tab(self, dialogues):
        """Tab 4: Dialogues"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)

        try:
            lines = [
                f"<b>{d.get('speaker', '?')}</b>: {d.get('text_vi', '')} / {d.get('text_tgt', '')}"
                for d in dialogues
            ]
            text_edit.setHtml("<br><br>".join(lines))
        except Exception:
            text_edit.setPlainText("(Không có lời thoại)")

        text_edit.setFont(QFont("Segoe UI", 11))
        text_edit.setStyleSheet("""
            QTextEdit {
                background: white;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 12px;
            }
        """)
        layout.addWidget(text_edit)

        return widget

    def _copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        try:
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(text)
                # Could show a toast notification here
        except Exception:
            pass

    def _save_text_prompt(self, prompt_text):
        """Save the formatted text prompt to a file"""
        try:
            # Generate default filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"google_labs_prompt_{timestamp}.txt"
            
            # Open file dialog
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Google Labs Flow Prompt",
                default_name,
                "Text Files (*.txt);;All Files (*.*)"
            )
            
            if file_path:
                # Ensure .txt extension
                if not file_path.endswith('.txt'):
                    file_path += '.txt'
                
                # Write prompt to file
                with open(file_path, 'w', encoding='utf-8') as f:
                    # Add header comment
                    f.write("# Google Labs Flow API Prompt\n")
                    f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("# This is the formatted text prompt sent to Google Labs Veo API\n")
                    f.write("#" + "="*70 + "\n\n")
                    f.write(prompt_text)
                
                # Show success message
                QMessageBox.information(
                    self,
                    "Success",
                    f"Prompt saved successfully to:\n{file_path}"
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save prompt:\n{str(e)}"
            )

    def _save_json_prompt(self, json_text):
        """Save the JSON prompt to a file"""
        try:
            # Generate default filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"google_labs_prompt_{timestamp}.json"
            
            # Open file dialog
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Prompt as JSON",
                default_name,
                "JSON Files (*.json);;All Files (*.*)"
            )
            
            if file_path:
                # Ensure .json extension
                if not file_path.endswith('.json'):
                    file_path += '.json'
                
                # Parse and re-format JSON for pretty printing
                try:
                    data = json.loads(json_text)
                    formatted_json = json.dumps(data, ensure_ascii=False, indent=2)
                except:
                    # If parsing fails, save as-is
                    formatted_json = json_text
                
                # Write JSON to file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(formatted_json)
                
                # Show success message
                QMessageBox.information(
                    self,
                    "Success",
                    f"JSON prompt saved successfully to:\n{file_path}"
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save JSON:\n{str(e)}"
            )