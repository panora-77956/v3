# ui/clone_video_panel.py
"""
Clone Video Panel - UI for cloning/analyzing videos from TikTok/YouTube
Author: chamnv-dev
Date: 2025-01-06
"""

import os
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QSlider, QGroupBox, QScrollArea,
    QGridLayout, QTextEdit, QFrame, QMessageBox, QProgressBar
)


class DownloadWorker(QThread):
    """Worker thread for downloading and analyzing video"""
    
    progress = pyqtSignal(str)  # Progress messages
    finished = pyqtSignal(dict)  # Results
    error = pyqtSignal(str)  # Error messages
    
    def __init__(self, url, platform, num_scenes, language, style, api_key=None):
        super().__init__()
        self.url = url
        self.platform = platform
        self.num_scenes = num_scenes
        self.language = language
        self.style = style
        self.api_key = api_key
    
    def run(self):
        """Execute download and analysis"""
        try:
            from services.video_clone_service import VideoCloneService
            
            service = VideoCloneService(log_callback=self._log)
            
            # Download video
            self.progress.emit("📥 Downloading video...")
            video_path = service.download_video(self.url, self.platform)
            
            # Analyze video
            self.progress.emit("🔍 Analyzing scenes...")
            results = service.analyze_video(
                video_path,
                num_scenes=self.num_scenes,
                language=self.language,
                style=self.style,
                api_key=self.api_key
            )
            
            results['video_path'] = video_path
            self.finished.emit(results)
            
        except Exception as e:
            import traceback
            # Log full traceback for debugging
            traceback.print_exc()
            # Emit user-friendly error message
            self.error.emit(str(e))
    
    def _log(self, msg):
        """Log callback"""
        self.progress.emit(msg)


class SceneCard(QFrame):
    """Card widget to display a scene"""
    
    def __init__(self, scene_index, frame_path, prompt, timestamp, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(1)
        self.setStyleSheet("""
            SceneCard {
                background: white;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                padding: 10px;
            }
            SceneCard:hover {
                border: 2px solid #1E88E5;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # Header
        header = QLabel(f"Scene {scene_index + 1} - {timestamp:.2f}s")
        header.setFont(QFont("Segoe UI", 11, QFont.Bold))
        header.setStyleSheet("color: #1E88E5;")
        layout.addWidget(header)
        
        # Thumbnail
        if os.path.exists(frame_path):
            thumbnail = QLabel()
            pixmap = QPixmap(frame_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(300, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                thumbnail.setPixmap(scaled)
                thumbnail.setAlignment(Qt.AlignCenter)
                layout.addWidget(thumbnail)
        
        # Prompt
        prompt_label = QLabel("Prompt:")
        prompt_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        layout.addWidget(prompt_label)
        
        prompt_text = QTextEdit()
        prompt_text.setPlainText(prompt)
        prompt_text.setMaximumHeight(80)
        prompt_text.setStyleSheet("background: #F5F5F5; border: 1px solid #E0E0E0; border-radius: 4px;")
        layout.addWidget(prompt_text)


class CloneVideoPanel(QWidget):
    """Main panel for Clone Video feature"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(16, 16, 16, 16)
        
        # LEFT SIDE: Input controls
        left_panel = self._create_input_panel()
        main_layout.addWidget(left_panel, stretch=1)
        
        # RIGHT SIDE: Results display
        right_panel = self._create_results_panel()
        main_layout.addWidget(right_panel, stretch=2)
    
    def _create_input_panel(self) -> QWidget:
        """Create left input panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("🎬 Clone Video")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet("color: #7C4DFF;")
        layout.addWidget(title)
        
        # Description
        desc = QLabel("Download and analyze videos from TikTok/YouTube")
        desc.setFont(QFont("Segoe UI", 10))
        desc.setStyleSheet("color: #666;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        layout.addSpacing(10)
        
        # URL Input Group
        url_group = QGroupBox("Video URL")
        url_group.setFont(QFont("Segoe UI", 11, QFont.Bold))
        url_layout = QVBoxLayout(url_group)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter TikTok or YouTube URL...")
        self.url_input.setFont(QFont("Segoe UI", 11))
        self.url_input.setMinimumHeight(35)
        url_layout.addWidget(self.url_input)
        
        # Platform selector
        platform_layout = QHBoxLayout()
        platform_label = QLabel("Platform:")
        platform_label.setFont(QFont("Segoe UI", 10))
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(["Auto-detect", "TikTok", "YouTube"])
        self.platform_combo.setFont(QFont("Segoe UI", 10))
        platform_layout.addWidget(platform_label)
        platform_layout.addWidget(self.platform_combo)
        url_layout.addLayout(platform_layout)
        
        layout.addWidget(url_group)
        
        # Options Group
        options_group = QGroupBox("Analysis Options")
        options_group.setFont(QFont("Segoe UI", 11, QFont.Bold))
        options_layout = QVBoxLayout(options_group)
        
        # Number of scenes
        scenes_layout = QHBoxLayout()
        scenes_label = QLabel("Number of scenes:")
        scenes_label.setFont(QFont("Segoe UI", 10))
        self.scenes_slider = QSlider(Qt.Horizontal)
        self.scenes_slider.setMinimum(1)
        self.scenes_slider.setMaximum(10)
        self.scenes_slider.setValue(5)
        self.scenes_value_label = QLabel("5")
        self.scenes_value_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.scenes_slider.valueChanged.connect(
            lambda v: self.scenes_value_label.setText(str(v))
        )
        scenes_layout.addWidget(scenes_label)
        scenes_layout.addWidget(self.scenes_slider)
        scenes_layout.addWidget(self.scenes_value_label)
        options_layout.addLayout(scenes_layout)
        
        # Language selector
        lang_layout = QHBoxLayout()
        lang_label = QLabel("Language:")
        lang_label.setFont(QFont("Segoe UI", 10))
        self.language_combo = QComboBox()
        self.language_combo.addItems([
            "Tiếng Việt (vi)",
            "English (en)",
            "日本語 (ja)",
            "한국어 (ko)",
            "中文 (zh)"
        ])
        self.language_combo.setFont(QFont("Segoe UI", 10))
        lang_layout.addWidget(lang_label)
        lang_layout.addWidget(self.language_combo)
        options_layout.addLayout(lang_layout)
        
        # Style selector
        style_layout = QHBoxLayout()
        style_label = QLabel("Video Style:")
        style_label.setFont(QFont("Segoe UI", 10))
        self.style_combo = QComboBox()
        self.style_combo.addItems([
            "Cinematic",
            "Anime",
            "Documentary",
            "Vlog",
            "Professional",
            "Artistic"
        ])
        self.style_combo.setFont(QFont("Segoe UI", 10))
        style_layout.addWidget(style_label)
        style_layout.addWidget(self.style_combo)
        options_layout.addLayout(style_layout)
        
        layout.addWidget(options_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Download button
        self.download_btn = QPushButton("📥 Download & Analyze Video")
        self.download_btn.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.download_btn.setMinimumHeight(45)
        self.download_btn.setStyleSheet("""
            QPushButton {
                background: #7C4DFF;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
            }
            QPushButton:hover {
                background: #6A3DE8;
            }
            QPushButton:pressed {
                background: #5835D1;
            }
            QPushButton:disabled {
                background: #BDBDBD;
            }
        """)
        self.download_btn.clicked.connect(self._on_download_clicked)
        layout.addWidget(self.download_btn)
        
        layout.addStretch()
        
        return panel
    
    def _create_results_panel(self) -> QWidget:
        """Create right results panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("Results")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #333;")
        layout.addWidget(title)
        
        # Status label
        self.status_label = QLabel("Enter a URL and click 'Download & Analyze' to begin")
        self.status_label.setFont(QFont("Segoe UI", 10))
        self.status_label.setStyleSheet("color: #666;")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Metadata display
        self.metadata_label = QLabel("")
        self.metadata_label.setFont(QFont("Segoe UI", 9))
        self.metadata_label.setStyleSheet("color: #888; background: #F5F5F5; padding: 8px; border-radius: 4px;")
        self.metadata_label.setVisible(False)
        layout.addWidget(self.metadata_label)
        
        # Scenes scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: #FAFAFA; }")
        
        self.scenes_container = QWidget()
        self.scenes_layout = QGridLayout(self.scenes_container)
        self.scenes_layout.setSpacing(16)
        scroll.setWidget(self.scenes_container)
        
        layout.addWidget(scroll, stretch=1)
        
        # Generate button
        self.generate_btn = QPushButton("🎨 Generate Similar Video")
        self.generate_btn.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.generate_btn.setMinimumHeight(45)
        self.generate_btn.setVisible(False)
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background: #26A69A;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
            }
            QPushButton:hover {
                background: #229488;
            }
            QPushButton:pressed {
                background: #1E8276;
            }
        """)
        self.generate_btn.clicked.connect(self._on_generate_clicked)
        layout.addWidget(self.generate_btn)
        
        return panel
    
    def _on_download_clicked(self):
        """Handle download button click"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a URL")
            return
        
        # Validate URL
        from services.video_clone_service import VideoCloneService
        service = VideoCloneService()
        is_valid, platform, error = service.validate_url(url)
        
        if not is_valid:
            QMessageBox.warning(self, "Invalid URL", error)
            return
        
        # Get parameters
        platform_map = {"Auto-detect": "auto", "TikTok": "tiktok", "YouTube": "youtube"}
        platform_selected = platform_map[self.platform_combo.currentText()]
        
        num_scenes = self.scenes_slider.value()
        
        # Extract language code using mapping
        language_map = {
            "Tiếng Việt (vi)": "vi",
            "English (en)": "en",
            "日本語 (ja)": "ja",
            "한국어 (ko)": "ko",
            "中文 (zh)": "zh"
        }
        language = language_map.get(self.language_combo.currentText(), "en")
        
        style = self.style_combo.currentText()
        
        # Get API key
        api_key = None
        try:
            from services.core.key_manager import get_all_keys
            keys = get_all_keys('google')
            if keys:
                api_key = keys[0]
        except (ImportError, Exception) as e:
            print(f"Warning: Could not load API key: {e}")
        
        # Start worker
        self.download_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.status_label.setText("Starting download...")
        
        self.worker = DownloadWorker(
            url, platform_selected, num_scenes, language, style, api_key
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()
    
    def _on_progress(self, message):
        """Handle progress update"""
        self.status_label.setText(message)
    
    def _on_finished(self, results):
        """Handle completion"""
        self.download_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("✓ Analysis complete!")
        
        # Display metadata
        metadata = results.get('metadata', {})
        meta_text = (
            f"Duration: {metadata.get('duration', 0):.1f}s  |  "
            f"Resolution: {metadata.get('width', 0)}x{metadata.get('height', 0)}  |  "
            f"FPS: {metadata.get('fps', 0):.1f}"
        )
        self.metadata_label.setText(meta_text)
        self.metadata_label.setVisible(True)
        
        # Display scenes
        self._display_scenes(results)
        
        # Show generate button
        self.generate_btn.setVisible(True)
        
        # Store results
        self._current_results = results
    
    def _on_error(self, error_msg):
        """Handle error"""
        self.download_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"❌ Error: {error_msg}")
        QMessageBox.critical(self, "Error", f"Failed to download/analyze video:\n\n{error_msg}")
    
    def _display_scenes(self, results):
        """Display extracted scenes"""
        # Clear previous scenes
        while self.scenes_layout.count():
            item = self.scenes_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        scenes = results.get('scenes', [])
        prompts = results.get('prompts', [])
        
        # Display in grid (2 columns)
        for i, scene in enumerate(scenes):
            prompt = prompts[i] if i < len(prompts) else ""
            card = SceneCard(
                i,
                scene.get('frame_path', ''),
                prompt,
                scene.get('timestamp', 0.0)
            )
            
            row = i // 2
            col = i % 2
            self.scenes_layout.addWidget(card, row, col)
    
    def _on_generate_clicked(self):
        """Handle generate similar video button click"""
        QMessageBox.information(
            self,
            "Feature Coming Soon",
            "Integration with Text2Video workflow will be added soon!\n\n"
            "This will automatically populate the Text2Video tab with:\n"
            "- Extracted scene prompts\n"
            "- Detected language\n"
            "- Video style settings"
        )
