# ui/video_ban_hang_v5_complete_fixed.py
"""
Video Bán Hàng V5 - Complete Implementation with Issue #7 Fix
- Modern V5 UI (ocean blue tabs, rounded buttons)
- Collapsible sections with proper show/hide
- 2 fields per row layout
- Character Bible integration
- 3-step workflow (Script → Images → Video)
- FIX Issue #7: Enhanced JSONDecodeError handling
- 100% original logic preserved

Author: chamnv-dev
Date: 2025-01-05
Fixed: 2025-01-05 03:09:00 UTC
"""

import datetime
import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPlainTextEdit, QPushButton,
    QScrollArea, QSpinBox, QTabWidget, QTextEdit,
    QVBoxLayout, QWidget
)

# Original imports
try:
    from services import image_gen_service
    from services import sales_script_service as sscript
    from services import sales_video_service as svc
    from ui.widgets.model_selector import ModelSelectorWidget
    from ui.widgets.scene_result_card import SceneResultCard
    from ui.workers.script_worker import ScriptWorker
    from utils.image_utils import convert_to_bytes
except ImportError as e:
    print(f"⚠️ Import warning: {e}")
    sscript = None
    svc = None

# V5 Styling
FONT_H2 = QFont("Segoe UI", 15, QFont.Bold)
FONT_BODY = QFont("Segoe UI", 13)
THUMBNAIL_SIZE = 72
MODEL_IMG = 128
RATE_LIMIT_DELAY_SEC = 10.0

# V5 Button Styles
BTN_PRIMARY = """
    QPushButton {
        background: #1E88E5;
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 700;
        font-size: 14px;
        padding: 8px 16px;
    }
    QPushButton:hover { background: #2196F3; }
    QPushButton:disabled { background: #CCCCCC; color: #888; }
"""

BTN_SUCCESS = """
    QPushButton {
        background: #4CAF50;
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 700;
        font-size: 14px;
        padding: 8px 16px;
    }
    QPushButton:hover { background: #66BB6A; }
    QPushButton:disabled { background: #CCCCCC; color: #888; }
"""

BTN_WARNING = """
    QPushButton {
        background: #FF9800;
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 700;
        font-size: 14px;
        padding: 8px 16px;
    }
    QPushButton:hover { background: #FFB74D; }
"""

BTN_DANGER = """
    QPushButton {
        background: #F44336;
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 700;
        font-size: 14px;
        padding: 8px 16px;
    }
    QPushButton:hover { background: #E57373; }
    QPushButton:disabled { background: #FFCDD2; color: #BDBDBD; }
"""

# Workers (từ original)
class ImageGenerationWorker(QThread):
    """Worker thread for generating images"""
    progress = pyqtSignal(str)
    scene_image_ready = pyqtSignal(int, bytes)
    thumbnail_ready = pyqtSignal(int, bytes)
    finished = pyqtSignal(bool)

    def __init__(self, outline, cfg, model_paths, prod_paths, use_whisk=False, character_bible=None, account_mgr=None):
        super().__init__()
        self.outline = outline
        self.cfg = cfg
        self.model_paths = model_paths
        self.prod_paths = prod_paths
        self.use_whisk = use_whisk
        self.character_bible = character_bible
        self.account_mgr = account_mgr
        self.should_stop = False

    def run(self):
        try:
            # Check if multi-account parallel mode is enabled
            if self.account_mgr and self.account_mgr.is_multi_account_enabled():
                self._run_parallel()
            else:
                self._run_sequential()

        except Exception as e:
            self.progress.emit(f"Lỗi: {e}")
            self.finished.emit(False)

    def _run_sequential(self):
        """Original sequential implementation - backward compatibility"""
        try:
            from services.core.config import load as load_cfg
            cfg_data = load_cfg()
            api_keys = cfg_data.get('google_api_keys', [])

            if not api_keys:
                self.progress.emit("[ERROR] Không có Google API keys")
                self.finished.emit(False)
                return

            aspect_ratio = self.cfg.get('ratio', '9:16')
            model = 'gemini' if 'Gemini' in self.cfg.get('image_model', 'Gemini') else 'imagen_4'

            self.progress.emit(f"[INFO] Sequential mode: {len(api_keys)} API keys, model: {model}")

            if self.character_bible and hasattr(self.character_bible, 'characters'):
                char_count = len(self.character_bible.characters)
                if char_count > 0:
                    self.progress.emit(f"[CHARACTER BIBLE] Injecting consistency for {char_count} character(s)")

            # Generate scene images
            scenes = self.outline.get("scenes", [])
            for i, scene in enumerate(scenes):
                if self.should_stop:
                    break

                # NOTE: Rate limiting now handled by generate_image_with_rate_limit()
                # No need for manual delay here anymore

                self.progress.emit(f"Tạo ảnh cảnh {scene.get('index')}...")

                prompt = scene.get("prompt_image", "")

                if self.character_bible and hasattr(self.character_bible, 'characters'):
                    try:
                        from services.google.character_bible import inject_character_consistency
                        prompt = inject_character_consistency(prompt, self.character_bible)
                    except Exception as e:
                        self.progress.emit(f"[WARNING] Failed to inject: {e}")

                img_data = None
                if self.use_whisk and self.model_paths and self.prod_paths:
                    try:
                        from services import whisk_service
                        img_data = whisk_service.generate_image(
                            prompt=prompt,
                            model_image=self.model_paths[0] if self.model_paths else None,
                            product_image=self.prod_paths[0] if self.prod_paths else None,
                            debug_callback=self.progress.emit,
                        )
                        if img_data:
                            self.progress.emit(f"Cảnh {scene.get('index')}: Whisk ✓")
                    except Exception as e:
                        self.progress.emit(f"Whisk failed: {str(e)[:100]}")
                        img_data = None

                if img_data is None and image_gen_service:
                    try:
                        self.progress.emit(f"Cảnh {scene.get('index')}: Dùng Gemini...")

                        # Enhanced: Respect rate limit for subsequent requests
                        img_data_url = image_gen_service.generate_image_with_rate_limit(
                            text=prompt,
                            api_keys=api_keys,
                            model=model,
                            aspect_ratio=aspect_ratio,
                            delay_before=RATE_LIMIT_DELAY_SEC if i > 0 else 0,
                            logger=lambda msg: self.progress.emit(msg),
                        )

                        if img_data_url and convert_to_bytes:
                            img_data, error = convert_to_bytes(img_data_url)
                            if img_data:
                                self.progress.emit(f"Cảnh {scene.get('index')}: Gemini ✓")
                            else:
                                self.progress.emit(f"Cảnh {scene.get('index')}: {error}")
                        else:
                            img_data = None
                    except Exception as e:
                        self.progress.emit(f"Gemini failed: {e}")
                        img_data = None

                if img_data:
                    self.scene_image_ready.emit(scene.get("index"), img_data)

            # Generate thumbnails
            social_media = self.outline.get("social_media", {})
            versions = social_media.get("versions", [])

            for i, version in enumerate(versions):
                if self.should_stop:
                    break

                # NOTE: Rate limiting now handled by generate_image_with_rate_limit()

                self.progress.emit(f"Tạo thumbnail {i+1}...")

                prompt = version.get("thumbnail_prompt", "")
                text_overlay = version.get("thumbnail_text_overlay", "")

                try:
                    if image_gen_service:
                        # Enhanced: Always delay for thumbnails (come after scene images)
                        thumb_data_url = image_gen_service.generate_image_with_rate_limit(
                            text=prompt,
                            api_keys=api_keys,
                            model=model,
                            aspect_ratio=aspect_ratio,
                            delay_before=RATE_LIMIT_DELAY_SEC,
                            logger=lambda msg: self.progress.emit(msg)
                        )

                        if thumb_data_url and convert_to_bytes:
                            thumb_data, error = convert_to_bytes(thumb_data_url)

                            if thumb_data:
                                import tempfile

                                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                                    tmp.write(thumb_data)
                                    tmp_path = tmp.name

                                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_out:
                                    out_path = tmp_out.name

                                if sscript:
                                    sscript.generate_thumbnail_with_text(tmp_path, text_overlay, out_path)

                                with open(out_path, "rb") as f:
                                    final_thumb = f.read()

                                os.unlink(tmp_path)
                                os.unlink(out_path)

                                self.thumbnail_ready.emit(i, final_thumb)
                                self.progress.emit(f"Thumbnail {i+1}: ✓")
                            else:
                                self.progress.emit(f"Thumbnail {i+1}: {error}")
                except Exception as e:
                    self.progress.emit(f"Thumbnail {i+1} error: {e}")

            self.finished.emit(True)

        except Exception as e:
            self.progress.emit(f"Lỗi sequential: {e}")
            self.finished.emit(False)

    def _run_parallel(self):
        """Parallel implementation using multiple accounts"""
        import threading
        from queue import Queue

        try:
            accounts = self.account_mgr.get_enabled_accounts()
            num_accounts = len(accounts)

            self.progress.emit(f"🚀 Parallel mode: {num_accounts} accounts")

            aspect_ratio = self.cfg.get('ratio', '9:16')
            model = 'gemini' if 'Gemini' in self.cfg.get('image_model', 'Gemini') else 'imagen_4'

            if self.character_bible and hasattr(self.character_bible, 'characters'):
                char_count = len(self.character_bible.characters)
                if char_count > 0:
                    self.progress.emit(f"[CHARACTER BIBLE] Injecting consistency for {char_count} character(s)")

            # Prepare scenes
            scenes = self.outline.get("scenes", [])

            # Distribute scenes across accounts using round-robin
            batches = [[] for _ in range(num_accounts)]
            for idx, scene in enumerate(scenes):
                account_idx = idx % num_accounts
                batches[account_idx].append((idx, scene))

            # Results queue for thread-safe communication
            results_queue = Queue()

            # Create and start threads
            threads = []
            for i, (account, batch) in enumerate(zip(accounts, batches)):
                if not batch:
                    continue

                thread = threading.Thread(
                    target=self._process_image_batch,
                    args=(account.tokens, batch, model, aspect_ratio, results_queue, i),
                    daemon=True,
                    name=f"ImageGen-{account.name}"
                )
                threads.append(thread)
                self.progress.emit(f"Thread {i+1}: {len(batch)} scenes → {account.name}")
                thread.start()

            # Monitor progress
            total_scenes = len(scenes)
            completed = 0

            while completed < total_scenes:
                if self.should_stop:
                    break

                try:
                    # Wait for results from any thread
                    scene_idx, img_data, error = results_queue.get(timeout=1.0)

                    if img_data:
                        self.scene_image_ready.emit(scene_idx, img_data)
                        self.progress.emit(f"✓ Cảnh {scene_idx} ({completed+1}/{total_scenes})")
                    elif error:
                        self.progress.emit(f"✗ Cảnh {scene_idx}: {error}")

                    completed += 1

                except Exception:
                    # Timeout or other error, check if threads still running
                    if all(not t.is_alive() for t in threads):
                        break

            # Wait for all threads to complete
            for thread in threads:
                thread.join(timeout=5.0)

            # Process thumbnails sequentially (usually fewer, so not worth parallelizing)
            self._generate_thumbnails_sequential(model, aspect_ratio)

            self.finished.emit(True)

        except Exception as e:
            self.progress.emit(f"Lỗi parallel: {e}")
            self.finished.emit(False)

    def _process_image_batch(self, api_keys, batch, model, aspect_ratio, results_queue, thread_id):
        """Process a batch of scenes in a thread"""
        try:
            for scene_idx, scene in batch:
                if self.should_stop:
                    break

                prompt = scene.get("prompt_image", "")

                # Inject character consistency
                if self.character_bible and hasattr(self.character_bible, 'characters'):
                    try:
                        from services.google.character_bible import inject_character_consistency
                        prompt = inject_character_consistency(prompt, self.character_bible)
                    except Exception:
                        pass

                img_data = None
                error = None

                # Use Whisk if enabled
                if self.use_whisk and self.model_paths and self.prod_paths:
                    try:
                        from services import whisk_service
                        img_data = whisk_service.generate_image(
                            prompt=prompt,
                            model_image=self.model_paths[0] if self.model_paths else None,
                            product_image=self.prod_paths[0] if self.prod_paths else None,
                            debug_callback=None,
                        )
                    except Exception as e:
                        error = f"Whisk: {str(e)[:50]}"

                # Fallback to Gemini/Imagen
                if img_data is None:
                    try:
                        # Import in thread scope to ensure it's available
                        if image_gen_service:
                            img_data_url = image_gen_service.generate_image_with_rate_limit(
                                text=prompt,
                                api_keys=api_keys,
                                model=model,
                                aspect_ratio=aspect_ratio,
                                delay_before=10,  # 10s delay per thread
                                logger=None,
                            )

                            if img_data_url:
                                # Import convert_to_bytes in thread scope
                                if convert_to_bytes:
                                    img_data, err = convert_to_bytes(img_data_url)
                                    if not img_data:
                                        error = err
                    except Exception as e:
                        error = f"Gemini: {str(e)[:50]}"

                # Queue result - use scene_idx from batch tuple, not scene.get('index')
                results_queue.put((scene_idx, img_data, error))

        except Exception as e:
            # Log thread error but don't crash
            results_queue.put((0, None, f"Thread {thread_id} error: {str(e)[:50]}"))

    def _generate_thumbnails_sequential(self, model, aspect_ratio):
        """Generate thumbnails sequentially (backward compatibility)"""
        try:
            from services.core.config import load as load_cfg
            cfg_data = load_cfg()
            api_keys = cfg_data.get('google_api_keys', [])

            social_media = self.outline.get("social_media", {})
            versions = social_media.get("versions", [])

            for i, version in enumerate(versions):
                if self.should_stop:
                    break

                self.progress.emit(f"Tạo thumbnail {i+1}...")

                prompt = version.get("thumbnail_prompt", "")
                text_overlay = version.get("thumbnail_text_overlay", "")

                try:
                    if image_gen_service:
                        thumb_data_url = image_gen_service.generate_image_with_rate_limit(
                            text=prompt,
                            api_keys=api_keys,
                            model=model,
                            aspect_ratio=aspect_ratio,
                            delay_before=RATE_LIMIT_DELAY_SEC,
                            logger=lambda msg: self.progress.emit(msg)
                        )

                        if thumb_data_url and convert_to_bytes:
                            thumb_data, error = convert_to_bytes(thumb_data_url)

                            if thumb_data:
                                import tempfile

                                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                                    tmp.write(thumb_data)
                                    tmp_path = tmp.name

                                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_out:
                                    out_path = tmp_out.name

                                if sscript:
                                    sscript.generate_thumbnail_with_text(tmp_path, text_overlay, out_path)

                                with open(out_path, "rb") as f:
                                    final_thumb = f.read()

                                os.unlink(tmp_path)
                                os.unlink(out_path)

                                self.thumbnail_ready.emit(i, final_thumb)
                                self.progress.emit(f"Thumbnail {i+1}: ✓")
                            else:
                                self.progress.emit(f"Thumbnail {i+1}: {error}")
                except Exception as e:
                    self.progress.emit(f"Thumbnail {i+1} error: {e}")

        except Exception as e:
            self.progress.emit(f"Thumbnail generation error: {e}")

    def stop(self):
        self.should_stop = True


class VideoBanHangV5(QWidget):
    """Video Bán Hàng V5 - Complete with Issue #7 fix"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # State
        self.prod_paths = []
        self.last_outline = None
        self.scene_images = {}
        self.thumbnail_images = {}
        self.character_bible = None

        # Cache system
        self.cache = {
            "outline": None,
            "scene_images": {},
            "scene_prompts": {},
            "thumbnails": {},
            "character_bible": None,
        }

        # Download settings
        self.chk_auto_download = None
        self.ed_download_path = None

        self._build_ui()

    def _build_ui(self):
        """Build 2-column UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # LEFT COLUMN (460px)
        self.left_widget = QWidget()
        self.left_widget.setFixedWidth(460)
        left_layout = QVBoxLayout(self.left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        self._build_left_column(left_layout)
        main_layout.addWidget(self.left_widget)

        # RIGHT COLUMN
        self.right_widget = QWidget()
        right_layout = QVBoxLayout(self.right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self._build_right_column(right_layout)
        main_layout.addWidget(self.right_widget, 1)

    def _build_left_column(self, layout):
        """Build left column with collapsible sections"""

        # FIXED SECTION
        lbl_proj = QLabel("📁 Dự án")
        lbl_proj.setFont(FONT_H2)
        layout.addWidget(lbl_proj)

        lbl_name = QLabel("Tên dự án:")
        lbl_name.setFont(QFont("Segoe UI", 13, QFont.Bold))
        layout.addWidget(lbl_name)

        self.ed_name = QLineEdit()
        self.ed_name.setFont(QFont("Segoe UI", 13))
        self.ed_name.setPlaceholderText("Nhập tên dự án...")
        if svc:
            self.ed_name.setText(svc.default_project_name())
        self.ed_name.setMinimumHeight(42)
        self.ed_name.setStyleSheet("""
            QLineEdit {
                background: white;
                border: 2px solid #BDBDBD;
                border-radius: 6px;
                padding: 8px 12px;
            }
            QLineEdit:focus { border: 2px solid #1E88E5; }
        """)
        layout.addWidget(self.ed_name)

        lbl_idea = QLabel("Ý tưởng:")
        lbl_idea.setFont(QFont("Segoe UI", 13, QFont.Bold))
        layout.addWidget(lbl_idea)

        self.ed_idea = QTextEdit()
        self.ed_idea.setFont(QFont("Segoe UI", 13))
        self.ed_idea.setPlaceholderText("Nhập ý tưởng...")
        self.ed_idea.setFixedHeight(80)
        self.ed_idea.setStyleSheet("""
            QTextEdit {
                background: white;
                border: 2px solid #BDBDBD;
                border-radius: 6px;
                padding: 10px;
            }
            QTextEdit:focus { border: 2px solid #1E88E5; }
        """)
        layout.addWidget(self.ed_idea)

        lbl_content = QLabel("Nội dung:")
        lbl_content.setFont(QFont("Segoe UI", 13, QFont.Bold))
        layout.addWidget(lbl_content)

        self.ed_product = QTextEdit()
        self.ed_product.setFont(QFont("Segoe UI", 13))
        self.ed_product.setPlaceholderText("Nhập nội dung chi tiết...")
        self.ed_product.setFixedHeight(130)
        self.ed_product.setStyleSheet("""
            QTextEdit {
                background: white;
                border: 2px solid #BDBDBD;
                border-radius: 6px;
                padding: 10px;
            }
            QTextEdit:focus { border: 2px solid #1E88E5; }
        """)
        layout.addWidget(self.ed_product)

        layout.addSpacing(16)

        # COLLAPSIBLE SECTIONS
        # Model section
        self.gb_model = self._create_collapsible_group("👤 Thông tin người mẫu")
        self.gb_model.setCheckable(True)
        self.gb_model.setChecked(False)
        self.gb_model.toggled.connect(lambda c: self._on_section_toggled(self.gb_model, c))

        self._model_container = QWidget()
        model_content = QVBoxLayout(self._model_container)
        model_content.setContentsMargins(0, 0, 0, 0)

        if ModelSelectorWidget:
            self.model_selector = ModelSelectorWidget(title="")
            model_content.addWidget(self.model_selector)

        model_layout = QVBoxLayout()
        model_layout.addWidget(self._model_container)
        self._model_container.setVisible(False)

        self.gb_model.setLayout(model_layout)
        layout.addWidget(self.gb_model)

        # Product images section
        self.gb_products = self._create_collapsible_group("📦 Ảnh sản phẩm")
        self.gb_products.setCheckable(True)
        self.gb_products.setChecked(False)
        self.gb_products.toggled.connect(lambda c: self._on_section_toggled(self.gb_products, c))

        self._products_container = QWidget()
        prod_content = QVBoxLayout(self._products_container)
        prod_content.setContentsMargins(0, 0, 0, 0)

        btn_prod = QPushButton("📁 Chọn ảnh sản phẩm")
        btn_prod.setMinimumHeight(32)
        btn_prod.setStyleSheet(BTN_PRIMARY)
        btn_prod.clicked.connect(self._pick_product_images)
        prod_content.addWidget(btn_prod)

        self.prod_thumb_container = QHBoxLayout()
        self.prod_thumb_container.setSpacing(4)
        prod_content.addLayout(self.prod_thumb_container)

        prod_layout = QVBoxLayout()
        prod_layout.addWidget(self._products_container)
        self._products_container.setVisible(False)

        self.gb_products.setLayout(prod_layout)
        layout.addWidget(self.gb_products)

        # Video settings section (2 fields per row)
        self.gb_settings = self._create_collapsible_group("⚙️ Cài đặt video")
        self.gb_settings.setCheckable(True)
        self.gb_settings.setChecked(False)
        self.gb_settings.toggled.connect(lambda c: self._on_section_toggled(self.gb_settings, c))

        self._settings_container = QWidget()
        settings_content = QVBoxLayout(self._settings_container)
        settings_content.setContentsMargins(0, 0, 0, 0)

        # Settings form - 2 columns
        form = QGridLayout()
        form.setSpacing(8)
        form.setColumnMinimumWidth(0, 110)
        form.setColumnMinimumWidth(2, 110)
        form.setColumnStretch(1, 1)
        form.setColumnStretch(3, 1)

        def make_widget(widget_class, **kwargs):
            w = widget_class()
            w.setMinimumHeight(32)
            for k, v in kwargs.items():
                if hasattr(w, k):
                    getattr(w, k)(v) if callable(getattr(w, k)) else setattr(w, k, v)
            return w

        # Row 0: Style columns
        self.cb_style = make_widget(QComboBox)
        self.cb_style.addItems(["Viral", "KOC Review", "Kể chuyện"])
        lbl = QLabel("Kịch bản:")
        lbl.setFont(QFont("Segoe UI", 13, QFont.Bold))
        form.addWidget(lbl, 0, 0)
        form.addWidget(self.cb_style, 0, 1)

        self.cb_imgstyle = make_widget(QComboBox)
        self.cb_imgstyle.addItems(["Điện ảnh", "Hiện đại/Trendy", "Anime", "Hoạt hình 3D"])
        lbl = QLabel("Hình ảnh:")
        lbl.setFont(QFont("Segoe UI", 13, QFont.Bold))
        form.addWidget(lbl, 0, 2)
        form.addWidget(self.cb_imgstyle, 0, 3)

        # Row 1: Model columns
        self.cb_script_model = make_widget(QComboBox)
        self.cb_script_model.addItems(["Gemini", "ChatGPT"])
        lbl = QLabel("Model KB:")
        lbl.setFont(QFont("Segoe UI", 13, QFont.Bold))
        form.addWidget(lbl, 1, 0)
        form.addWidget(self.cb_script_model, 1, 1)

        self.cb_image_model = make_widget(QComboBox)
        self.cb_image_model.addItems(["Gemini", "Whisk"])
        lbl = QLabel("Tạo ảnh:")
        lbl.setFont(QFont("Segoe UI", 13, QFont.Bold))
        form.addWidget(lbl, 1, 2)
        form.addWidget(self.cb_image_model, 1, 3)

        # Row 2: Voice | Language
        self.ed_voice = make_widget(QLineEdit)
        self.ed_voice.setPlaceholderText("ElevenLabs VoiceID")
        lbl = QLabel("Lời thoại:")
        lbl.setFont(QFont("Segoe UI", 13, QFont.Bold))
        form.addWidget(lbl, 2, 0)
        form.addWidget(self.ed_voice, 2, 1)

        self.cb_lang = make_widget(QComboBox)
        LANGUAGES = ["Tiếng Việt", "Tiếng Anh", "Tiếng Trung - Giản thể"]
        self.cb_lang.addItems(LANGUAGES)

        self.LANGUAGE_MAP = {
            "Tiếng Việt": "vi",
            "Tiếng Anh": "en",
            "Tiếng Trung - Giản thể": "zh-CN",
        }
        lbl = QLabel("Ngôn ngữ:")
        lbl.setFont(QFont("Segoe UI", 13, QFont.Bold))
        form.addWidget(lbl, 2, 2)
        form.addWidget(self.cb_lang, 2, 3)

        # Row 3: Duration | Videos
        self.sp_duration = make_widget(QSpinBox)
        self.sp_duration.setRange(8, 1200)
        self.sp_duration.setSingleStep(8)
        self.sp_duration.setValue(32)
        self.sp_duration.setSuffix(" s")
        lbl = QLabel("Thời lượng:")
        lbl.setFont(QFont("Segoe UI", 13, QFont.Bold))
        form.addWidget(lbl, 3, 0)
        form.addWidget(self.sp_duration, 3, 1)

        self.sp_videos = make_widget(QSpinBox)
        self.sp_videos.setRange(1, 4)
        self.sp_videos.setValue(1)
        lbl = QLabel("Số vid/cảnh:")
        lbl.setFont(QFont("Segoe UI", 13, QFont.Bold))
        form.addWidget(lbl, 3, 2)
        form.addWidget(self.sp_videos, 3, 3)

        # Row 4: Ratio | Platform
        self.cb_ratio = make_widget(QComboBox)
        self.cb_ratio.addItems(["9:16", "16:9", "1:1", "4:5"])
        lbl = QLabel("Tỉ lệ:")
        lbl.setFont(QFont("Segoe UI", 13, QFont.Bold))
        form.addWidget(lbl, 4, 0)
        form.addWidget(self.cb_ratio, 4, 1)

        self.cb_social = make_widget(QComboBox)
        self.cb_social.addItems(["TikTok", "Facebook", "YouTube"])
        lbl = QLabel("Nền tảng:")
        lbl.setFont(QFont("Segoe UI", 13, QFont.Bold))
        form.addWidget(lbl, 4, 2)
        form.addWidget(self.cb_social, 4, 3)

        settings_content.addLayout(form)

        settings_layout = QVBoxLayout()
        settings_layout.addWidget(self._settings_container)
        self._settings_container.setVisible(False)

        self.gb_settings.setLayout(settings_layout)
        layout.addWidget(self.gb_settings)

        layout.addStretch()

        # Action buttons
        self._build_action_buttons(layout)

    def _build_action_buttons(self, layout):
        """Build action buttons with V5 styling"""

        # ROW 1: Workflow buttons
        workflow_row = QHBoxLayout()
        workflow_row.setSpacing(6)

        self.btn_script = QPushButton("📝 Viết kịch bản")
        self.btn_script.setMinimumHeight(42)
        self.btn_script.setStyleSheet(BTN_WARNING)
        self.btn_script.clicked.connect(self._on_write_script)
        workflow_row.addWidget(self.btn_script)

        self.btn_images = QPushButton("🎨 Tạo ảnh")
        self.btn_images.setMinimumHeight(42)
        self.btn_images.setEnabled(False)
        self.btn_images.setStyleSheet(BTN_WARNING)
        self.btn_images.clicked.connect(self._on_generate_images)
        workflow_row.addWidget(self.btn_images)

        self.btn_video = QPushButton("🎬 Video")
        self.btn_video.setMinimumHeight(42)
        self.btn_video.setEnabled(False)
        self.btn_video.setStyleSheet(BTN_SUCCESS)
        self.btn_video.clicked.connect(self._on_generate_video)
        workflow_row.addWidget(self.btn_video)

        layout.addLayout(workflow_row)

        # ROW 2: Auto + Stop buttons
        auto_row = QHBoxLayout()
        auto_row.setSpacing(6)

        self.btn_auto = QPushButton("⚡ Tạo video tự động (3 bước)")
        self.btn_auto.setMinimumHeight(42)
        self.btn_auto.setStyleSheet("""
            QPushButton {
                background: #FF6B35;
                color: white;
                border: none;
                border-radius: 21px;
                font-weight: 700;
                font-size: 14px;
            }
            QPushButton:hover { background: #FF8555; }
        """)
        self.btn_auto.clicked.connect(self._on_auto_workflow)
        auto_row.addWidget(self.btn_auto, 3)

        self.btn_stop = QPushButton("⏹️ Dừng")
        self.btn_stop.setMinimumHeight(42)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet(BTN_DANGER)
        self.btn_stop.clicked.connect(self.stop_processing)
        auto_row.addWidget(self.btn_stop, 1)

        layout.addLayout(auto_row)

    def _build_right_column(self, layout):
        """Build right column with tabs - OCEAN BLUE SELECTED"""

        self.results_tabs = QTabWidget()
        self.results_tabs.setFont(QFont("Segoe UI", 13, QFont.Bold))

        # Tab 1: Scenes
        scenes_tab = self._build_scenes_tab()
        self.results_tabs.addTab(scenes_tab, "🎬 Cảnh")

        # Tab 2: Character Bible
        bible_tab = self._build_character_bible_tab()
        self.results_tabs.addTab(bible_tab, "👤 Character Bible")

        # Tab 3: Thumbnail
        thumb_tab = self._build_thumbnail_tab()
        self.results_tabs.addTab(thumb_tab, "📺 Thumbnail")

        # Tab 4: Social
        social_tab = self._build_social_tab()
        self.results_tabs.addTab(social_tab, "📱 Social")

        # OCEAN BLUE STYLING
        self.results_tabs.setStyleSheet("""
            QTabBar::tab {
                min-width: 140px;
                padding: 12px 18px;
                font-weight: 700;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 3px;
            }
            QTabBar::tab:selected {
                background: #00ACC1;
                color: white;
                border-bottom: 4px solid #00838F;
            }
            QTabBar::tab:!selected {
                background: #F5F5F5;
                color: #616161;
            }
            QTabBar::tab:hover {
                background: #B2EBF2;
            }
        """)

        layout.addWidget(self.results_tabs, 1)

        # Log area
        gb_log = QGroupBox("Nhật ký xử lý")
        lv = QVBoxLayout(gb_log)
        self.ed_log = QPlainTextEdit()
        self.ed_log.setReadOnly(True)
        self.ed_log.setMaximumHeight(80)
        self.ed_log.setFont(QFont("Courier New", 11))
        self.ed_log.setStyleSheet("""
            QPlainTextEdit {
                background: #C8E6C9;
                color: #1B5E20;
                border: 2px solid #4CAF50;
                border-radius: 6px;
            }
        """)
        lv.addWidget(self.ed_log)
        layout.addWidget(gb_log)

    def _build_scenes_tab(self):
        """Build scenes tab"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        self.scenes_layout = QVBoxLayout(container)
        self.scenes_layout.setContentsMargins(16, 16, 16, 16)
        self.scenes_layout.setSpacing(0)

        self.scene_cards = []

        self.scenes_layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _build_character_bible_tab(self):
        """Build Character Bible tab"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Header
        header_layout = QHBoxLayout()

        title_label = QLabel("📖 Character Bible - Visual Consistency System")
        title_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        self.btn_regen_bible = QPushButton("🔄 Regenerate")
        self.btn_regen_bible.setMinimumHeight(32)
        self.btn_regen_bible.setEnabled(False)
        self.btn_regen_bible.setStyleSheet(BTN_WARNING)
        self.btn_regen_bible.clicked.connect(self._regenerate_character_bible)
        header_layout.addWidget(self.btn_regen_bible)

        self.btn_copy_bible = QPushButton("📋 Copy")
        self.btn_copy_bible.setMinimumHeight(32)
        self.btn_copy_bible.setEnabled(False)
        self.btn_copy_bible.setStyleSheet(BTN_PRIMARY)
        self.btn_copy_bible.clicked.connect(self._copy_character_bible)
        header_layout.addWidget(self.btn_copy_bible)

        layout.addLayout(header_layout)

        # Description
        desc_label = QLabel(
            "Character Bible ensures consistent appearance across scenes. "
            "Each character has 5 unique consistency anchors."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666; padding: 8px; background: #f5f5f5; border-radius: 4px;")
        layout.addWidget(desc_label)

        # Display area
        self.ed_character_bible = QTextEdit()
        self.ed_character_bible.setReadOnly(True)
        self.ed_character_bible.setFont(QFont("Courier New", 10))
        self.ed_character_bible.setPlaceholderText(
            "Character Bible will appear here after script generation..."
        )
        layout.addWidget(self.ed_character_bible, 1)

        scroll.setWidget(container)
        return scroll

    def _build_thumbnail_tab(self):
        """Build thumbnail tab - horizontal layout"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        self.thumbnail_widgets = []
        for i in range(3):
            version_card = QGroupBox(f"Phiên bản {i+1}")
            version_card.setMinimumWidth(290)

            card_layout = QVBoxLayout(version_card)

            img_thumb = QLabel()
            img_thumb.setFixedSize(270, 480)
            img_thumb.setAlignment(Qt.AlignCenter)
            img_thumb.setText("Chưa tạo")
            img_thumb.setStyleSheet("border: 2px solid #E0E0E0; border-radius: 8px;")
            card_layout.addWidget(img_thumb)

            self.thumbnail_widgets.append({"thumbnail": img_thumb})
            layout.addWidget(version_card)

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _build_social_tab(self):
        """Build social media tab"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(20)

        self.social_version_widgets = []
        for i in range(3):
            version_card = QGroupBox(f"📱 Phiên bản {i+1}")
            card_layout = QVBoxLayout(version_card)
            card_layout.setSpacing(12)

            # Caption
            lbl_caption = QLabel("📝 Caption:")
            lbl_caption.setFont(QFont("Segoe UI", 13, QFont.Bold))
            card_layout.addWidget(lbl_caption)

            ed_caption = QTextEdit()
            ed_caption.setReadOnly(True)
            ed_caption.setMinimumHeight(100)
            ed_caption.setFont(QFont("Segoe UI", 13))
            card_layout.addWidget(ed_caption)

            # Hashtags
            lbl_hashtags = QLabel("🏷️ Hashtags:")
            lbl_hashtags.setFont(QFont("Segoe UI", 13, QFont.Bold))
            card_layout.addWidget(lbl_hashtags)

            ed_hashtags = QTextEdit()
            ed_hashtags.setReadOnly(True)
            ed_hashtags.setMinimumHeight(60)
            ed_hashtags.setFont(QFont("Courier New", 12))
            card_layout.addWidget(ed_hashtags)

            # Copy buttons
            btn_row = QHBoxLayout()

            btn_copy_caption = QPushButton("📋 Copy Caption")
            btn_copy_caption.setStyleSheet(BTN_PRIMARY)
            btn_copy_caption.clicked.connect(
                lambda _, e=ed_caption: self._copy_to_clipboard(e.toPlainText())
            )
            btn_row.addWidget(btn_copy_caption)

            btn_copy_hashtags = QPushButton("📋 Copy Hashtags")
            btn_copy_hashtags.setStyleSheet(BTN_PRIMARY)
            btn_copy_hashtags.clicked.connect(
                lambda _, e=ed_hashtags: self._copy_to_clipboard(e.toPlainText())
            )
            btn_row.addWidget(btn_copy_hashtags)

            btn_copy_all = QPushButton("📋 Copy All")
            btn_copy_all.setStyleSheet(BTN_SUCCESS)
            btn_copy_all.clicked.connect(
                lambda _, c=ed_caption, h=ed_hashtags:
                    self._copy_to_clipboard(f"{c.toPlainText()}\n\n{h.toPlainText()}")
            )
            btn_row.addWidget(btn_copy_all)

            card_layout.addLayout(btn_row)

            self.social_version_widgets.append({
                "widget": version_card,
                "caption": ed_caption,
                "hashtags": ed_hashtags
            })

            layout.addWidget(version_card)

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _create_collapsible_group(self, title):
        """Create collapsible group box"""
        gb = QGroupBox(title)
        gb.setFont(QFont("Segoe UI", 11, QFont.Bold))
        gb.setStyleSheet("""
            QGroupBox {
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 16px;
                background: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 4px 12px;
                background: white;
                border-radius: 4px;
            }
            QGroupBox:checked {
                border: 2px solid #2196F3;
            }
        """)
        return gb

    def _on_section_toggled(self, toggled_section, checked):
        """Handle section toggle - accordion behavior"""
        container = None
        if toggled_section == self.gb_model:
            container = getattr(self, '_model_container', None)
        elif toggled_section == self.gb_products:
            container = getattr(self, '_products_container', None)
        elif toggled_section == self.gb_settings:
            container = getattr(self, '_settings_container', None)

        if container:
            container.setVisible(checked)

        if checked:
            sections = [
                (self.gb_model, getattr(self, '_model_container', None)),
                (self.gb_products, getattr(self, '_products_container', None)),
                (self.gb_settings, getattr(self, '_settings_container', None))
            ]
            for section, section_container in sections:
                if section != toggled_section and section.isChecked():
                    section.blockSignals(True)
                    section.setChecked(False)
                    section.blockSignals(False)
                    if section_container:
                        section_container.setVisible(False)

    def _pick_product_images(self):
        """Pick product images"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Chọn ảnh sản phẩm", "", "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if not files:
            return

        self.prod_paths = files
        self._refresh_product_thumbnails()

    def _refresh_product_thumbnails(self):
        """Refresh product thumbnails"""
        while self.prod_thumb_container.count():
            item = self.prod_thumb_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        max_show = 5
        for i, path in enumerate(self.prod_paths[:max_show]):
            thumb = QLabel()
            thumb.setFixedSize(THUMBNAIL_SIZE, THUMBNAIL_SIZE)
            thumb.setScaledContents(True)
            thumb.setPixmap(
                QPixmap(path).scaled(
                    THUMBNAIL_SIZE, THUMBNAIL_SIZE,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )
            thumb.setStyleSheet("border: 1px solid #90CAF9;")
            self.prod_thumb_container.addWidget(thumb)

        if len(self.prod_paths) > max_show:
            extra = QLabel(f"+{len(self.prod_paths) - max_show}")
            extra.setFixedSize(THUMBNAIL_SIZE, THUMBNAIL_SIZE)
            extra.setAlignment(Qt.AlignCenter)
            extra.setStyleSheet("border: 1px dashed #666; font-weight: bold;")
            self.prod_thumb_container.addWidget(extra)

        self.prod_thumb_container.addStretch(1)

    def _collect_cfg(self):
        """Collect configuration"""
        models = []
        model_paths = []
        first_model_json = ""

        if hasattr(self, 'model_selector'):
            models = self.model_selector.get_models()
            model_paths = [m["image_path"] for m in models if m.get("image_path")]

            if models and models[0].get("data"):
                try:
                    first_model_json = json.dumps(models[0]["data"], ensure_ascii=False)
                except:
                    first_model_json = str(models[0]["data"])

        return {
            "project_name": (self.ed_name.text() or "").strip() or (svc.default_project_name() if svc else "Project"),
            "idea": self.ed_idea.toPlainText(),
            "product_main": self.ed_product.toPlainText(),
            "script_style": self.cb_style.currentText(),
            "image_style": self.cb_imgstyle.currentText(),
            "script_model": self.cb_script_model.currentText(),
            "image_model": self.cb_image_model.currentText(),
            "voice_id": self.ed_voice.text().strip(),
            "duration_sec": int(self.sp_duration.value()),
            "videos_count": int(self.sp_videos.value()),
            "ratio": self.cb_ratio.currentText(),
            "speech_lang": self.LANGUAGE_MAP.get(self.cb_lang.currentText(), "vi"),
            "social_platform": self.cb_social.currentText(),
            "first_model_json": first_model_json,
            "product_count": len(self.prod_paths),
            "models": models,
            "model_paths": model_paths,
        }

    def _append_log(self, msg):
        """Append log message"""
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.ed_log.appendPlainText(f"[{ts}] {msg}")

    def _copy_to_clipboard(self, text):
        """Copy to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        self._append_log("Đã copy vào clipboard")

    def _regenerate_character_bible(self):
        """Regenerate character bible"""
        if not self.cache.get("outline"):
            QMessageBox.warning(self, "Chưa có kịch bản", "Vui lòng viết kịch bản trước.")
            return

        self._append_log("🔄 Đang tạo lại Character Bible...")

        try:
            from services.google.character_bible import create_character_bible, format_character_bible_for_display

            outline = self.cache["outline"]
            script_json = outline.get("script_json", {})
            existing_bible = script_json.get("character_bible", [])

            cfg = self._collect_cfg()
            video_concept = f"{cfg.get('idea', '')} {cfg.get('product_main', '')}"
            screenplay = outline.get("screenplay_text", "")

            bible = create_character_bible(video_concept, screenplay, existing_bible)
            self.character_bible = bible
            self.cache["character_bible"] = bible

            bible_text = format_character_bible_for_display(bible)
            self.ed_character_bible.setPlainText(bible_text)

            self._append_log("✓ Character Bible đã được tạo lại")

        except Exception as e:
            self._append_log(f"❌ Lỗi: {e}")
            QMessageBox.critical(self, "Lỗi", f"Không thể tạo Character Bible: {e}")

    def _copy_character_bible(self):
        """Copy character bible"""
        text = self.ed_character_bible.toPlainText()
        if text:
            self._copy_to_clipboard(text)
        else:
            self._append_log("⚠ Character Bible trống")

    def _on_auto_workflow(self):
        """Auto workflow - 3 steps"""
        self._append_log("⚡ Bắt đầu quy trình tự động (3 bước)...")

        self.btn_auto.setEnabled(False)
        self.btn_script.setEnabled(False)
        self.btn_images.setEnabled(False)
        self.btn_video.setEnabled(False)

        self._append_log("📝 Bước 1/3: Viết kịch bản...")
        self._on_write_script()

    def _on_write_script(self):
        """Write script"""
        cfg = self._collect_cfg()

        self._append_log("Bắt đầu tạo kịch bản...")
        self.btn_script.setEnabled(False)
        self.btn_script.setText("⏳ Đang tạo...")
        self.btn_stop.setEnabled(True)

        if ScriptWorker:
            self.script_worker = ScriptWorker(cfg)
            self.script_worker.progress.connect(self._append_log)
            self.script_worker.done.connect(self._on_script_done)
            self.script_worker.error.connect(self._on_script_error)
            self.script_worker.start()
        else:
            self._append_log("❌ ScriptWorker not available")

    def _on_script_done(self, outline):
        """Script done"""
        try:
            self.last_outline = outline
            self.cache["outline"] = outline

            for scene in outline.get("scenes", []):
                scene_idx = scene.get("index", 0)
                self.cache["scene_prompts"][scene_idx] = {
                    "video": scene.get("prompt_video"),
                    "image": scene.get("prompt_image"),
                    "speech": scene.get("speech"),
                }

            social_media = outline.get("social_media", {})
            versions = social_media.get("versions", [])

            for i, version in enumerate(versions[:3]):
                if i < len(self.social_version_widgets):
                    widget_data = self.social_version_widgets[i]
                    caption = version.get("caption", "")
                    hashtags = " ".join(version.get("hashtags", []))
                    widget_data["caption"].setPlainText(caption)
                    widget_data["hashtags"].setPlainText(hashtags)

            self._display_scene_cards(outline.get("scenes", []))

            character_bible = outline.get("character_bible")
            character_bible_text = outline.get("character_bible_text", "")
            if character_bible:
                self.character_bible = character_bible
                self.cache["character_bible"] = character_bible
                self.ed_character_bible.setPlainText(character_bible_text)
                self.btn_regen_bible.setEnabled(True)
                self.btn_copy_bible.setEnabled(True)
                self._append_log(f"✓ Character Bible: {len(character_bible.characters)} nhân vật")
            else:
                self.ed_character_bible.setPlainText("(Không có Character Bible)")

            self._append_log(f"✓ Kịch bản: {len(outline.get('scenes', []))} cảnh")
            self._append_log(f"✓ Social: {len(versions)} phiên bản")

            self.btn_images.setEnabled(True)

        except Exception as e:
            self._append_log(f"❌ Lỗi: {e}")
        finally:
            self.btn_script.setEnabled(True)
            self.btn_script.setText("📝 Viết kịch bản")
            self.btn_stop.setEnabled(False)

    def _on_script_error(self, error_msg):
        """
        Enhanced error handler with specific JSONDecodeError handling
        FIX for Issue #7: Better error messages and recovery options
        """

        # Check for JSON-related errors
        if "JSONDecodeError" in error_msg or "Failed to parse JSON" in error_msg:
            # Extract key information
            line_match = re.search(r'line (\d+)', error_msg)
            col_match = re.search(r'column (\d+)', error_msg)

            # Build user-friendly message
            title = "❌ Lỗi Phân Tích Kịch Bản (Issue #7)"

            message_parts = [
                "Không thể đọc kịch bản do lỗi định dạng dữ liệu.\n"
            ]

            if line_match and col_match:
                line_num = line_match.group(1)
                col_num = col_match.group(1)
                message_parts.append(f"📍 Lỗi tại dòng {line_num}, cột {col_num}\n")

            message_parts.extend([
                "\n🔍 Nguyên nhân thường gặp:",
                "• AI trả về dữ liệu thiếu dấu phẩy hoặc ngoặc",
                "• Có ký tự đặc biệt trong tên sản phẩm/nội dung",
                "• Nội dung quá dài (>10000 ký tự)",
                "• Emoji hoặc unicode không hợp lệ",
                "\n✅ Cách khắc phục:",
                "1️⃣ Rút ngắn nội dung sản phẩm (< 5000 ký tự)",
                "2️⃣ Xóa emoji và ký tự đặc biệt khỏi input",
                "3️⃣ Thử đổi Model (Gemini ↔ ChatGPT)",
                "4️⃣ Kiểm tra API key còn hoạt động",
                "5️⃣ Đơn giản hóa ý tưởng và mô tả",
                "\n⚠️ Nếu vẫn lỗi, báo cáo với:",
                f"• Dòng: {line_num if line_match else 'N/A'}",
                f"• Cột: {col_num if col_match else 'N/A'}",
                f"• Thời gian: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"• Model: {self.cb_script_model.currentText()}",
            ])

            full_message = "\n".join(message_parts)

            # Show detailed error dialog with Retry option
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle(title)
            msg_box.setText(full_message)
            msg_box.setDetailedText(f"Technical Details:\n\n{error_msg}")
            msg_box.setStandardButtons(QMessageBox.Retry | QMessageBox.Close)
            msg_box.setDefaultButton(QMessageBox.Retry)

            result = msg_box.exec_()

            # Detailed logging for debugging
            self._append_log("=" * 60)
            self._append_log("❌ JSONDecodeError Details (Issue #7):")
            self._append_log(f"Time: {datetime.datetime.now()}")
            self._append_log(f"Line: {line_num if line_match else 'N/A'}")
            self._append_log(f"Col: {col_num if col_match else 'N/A'}")
            self._append_log(f"Model: {self.cb_script_model.currentText()}")
            self._append_log(f"Style: {self.cb_style.currentText()}")
            self._append_log(f"Content length: {len(self.ed_product.toPlainText())} chars")
            self._append_log(f"Error: {error_msg[:500]}")
            self._append_log("=" * 60)

            # If user clicked Retry, try again
            if result == QMessageBox.Retry:
                self._append_log("🔄 Retrying script generation...")
                # Small delay before retry
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(1000, self._on_write_script)
                return

        elif error_msg.startswith("MissingAPIKey:"):
            QMessageBox.warning(
                self, "Thiếu API Key",
                "Chưa nhập Google API Key.\n\n"
                "Vào tab Cài đặt để thêm API key."
            )
            self._append_log("❌ Thiếu Google API Key")

        else:
            # Generic error
            QMessageBox.critical(
                self, "Lỗi Tạo Kịch Bản",
                f"{error_msg}\n\n"
                "Check console (Nhật ký xử lý) for details."
            )
            self._append_log(f"❌ {error_msg}")

        # Re-enable buttons
        self.btn_script.setEnabled(True)
        self.btn_script.setText("📝 Viết kịch bản")
        self.btn_stop.setEnabled(False)

    def _display_scene_cards(self, scenes):
        """Display scene cards"""
        while self.scenes_layout.count() > 1:
            item = self.scenes_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.scene_cards = []
        self.scene_images = {}

        if SceneResultCard:
            for i, scene in enumerate(scenes):
                scene_idx = scene.get("index", i + 1)
                card = SceneResultCard(scene_idx, scene, alternating_color=(i % 2 == 1))

                # Connect scene card signals to handlers
                card.recreate_requested.connect(self._on_scene_recreate_image)
                card.generate_video_requested.connect(self._on_scene_generate_video)

                self.scenes_layout.insertWidget(i, card)
                self.scene_cards.append(card)
                self.scene_images[scene_idx] = {"card": card, "path": None}

    def _on_generate_images(self):
        """Generate images"""
        if not self.cache["outline"]:
            QMessageBox.warning(self, "Chưa có kịch bản", "Vui lòng viết kịch bản trước.")
            return

        cfg = self._collect_cfg()
        use_whisk = cfg.get("image_model") == "Whisk"
        model_paths = cfg.get("model_paths", [])

        self._append_log("Bắt đầu tạo ảnh...")
        self.btn_images.setEnabled(False)
        self.btn_stop.setEnabled(True)

        character_bible = self.cache.get("character_bible")

        # Get account manager for multi-account support
        from services.account_manager import get_account_manager
        account_mgr = get_account_manager()

        self.img_worker = ImageGenerationWorker(
            self.cache["outline"], cfg, model_paths,
            self.prod_paths, use_whisk, character_bible,
            account_mgr=account_mgr
        )

        self.img_worker.progress.connect(self._append_log)
        self.img_worker.scene_image_ready.connect(self._on_scene_image_ready)
        self.img_worker.thumbnail_ready.connect(self._on_thumbnail_ready)
        self.img_worker.finished.connect(self._on_images_finished)

        self.img_worker.start()

    def _on_scene_image_ready(self, scene_idx, img_data):
        """Scene image ready"""
        if svc:
            cfg = self._collect_cfg()
            dirs = svc.ensure_project_dirs(cfg["project_name"])
            img_path = dirs["preview"] / f"scene_{scene_idx}.png"

            with open(img_path, "wb") as f:
                f.write(img_data)

            self.cache["scene_images"][scene_idx] = str(img_path)

            if scene_idx in self.scene_images:
                card = self.scene_images[scene_idx].get("card")
                if card:
                    card.set_image_path(str(img_path))
                self.scene_images[scene_idx]["path"] = str(img_path)

            self._append_log(f"✓ Ảnh cảnh {scene_idx}")

    def _on_thumbnail_ready(self, version_idx, img_data):
        """Thumbnail ready"""
        if svc:
            cfg = self._collect_cfg()
            dirs = svc.ensure_project_dirs(cfg["project_name"])
            img_path = dirs["preview"] / f"thumbnail_v{version_idx+1}.png"

            with open(img_path, "wb") as f:
                f.write(img_data)

            self.cache["thumbnails"][version_idx] = str(img_path)

            if version_idx < len(self.thumbnail_widgets):
                widget_data = self.thumbnail_widgets[version_idx]
                pixmap = QPixmap(str(img_path))
                widget_data["thumbnail"].setPixmap(
                    pixmap.scaled(270, 480, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )

            self._append_log(f"✓ Thumbnail {version_idx+1}")

    def _on_images_finished(self, success):
        """Images finished"""
        if success:
            self._append_log("✓ Hoàn tất tạo ảnh")
            self.btn_video.setEnabled(True)
        else:
            self._append_log("❌ Có lỗi khi tạo ảnh")

        self.btn_images.setEnabled(True)
        self.btn_stop.setEnabled(False)

   # ui/video_ban_hang_v5_complete_fixed.py - CONTINUATION

    def _on_generate_video(self):
        """Generate video"""
        if not self.cache["outline"]:
            QMessageBox.warning(self, "Chưa có kịch bản", "Vui lòng viết kịch bản trước.")
            return

        if not self.cache["scene_images"]:
            QMessageBox.warning(self, "Chưa có ảnh", "Vui lòng tạo ảnh trước.")
            return

        cfg = self._collect_cfg()

        self._append_log("Bắt đầu tạo video...")
        self._append_log(f"✓ Cache: {len(self.cache['scene_images'])} ảnh")
        self._append_log(f"✓ Ngôn ngữ: {cfg.get('speech_lang', 'vi')}")

        voice_id = cfg.get('voice_id', '')
        if voice_id:
            self._append_log(f"✓ Voice ID: {voice_id}")

        self.btn_video.setEnabled(False)

        QMessageBox.information(
            self, "Thông báo",
            "Chức năng tạo video sẽ được triển khai trong phiên bản tiếp theo."
        )

        self.btn_video.setEnabled(True)

        # TODO: When video generation is fully implemented
        # if video_path and self.chk_auto_download and self.chk_auto_download.isChecked():
        #     self._auto_download_video(video_path)

    def _on_scene_recreate_image(self, scene_idx):
        """Recreate image for a specific scene (triggered by scene card button)"""
        if not self.cache["outline"]:
            QMessageBox.warning(self, "Chưa có kịch bản", "Vui lòng viết kịch bản trước.")
            return

        cfg = self._collect_cfg()
        use_whisk = cfg.get("image_model") == "Whisk"
        model_paths = cfg.get("model_paths", [])

        self._append_log(f"🔄 Tạo lại ảnh cho cảnh {scene_idx}...")

        # Find the scene data
        scenes = self.cache["outline"].get("scenes", [])
        target_scene = None
        for scene in scenes:
            if scene.get("index") == scene_idx:
                target_scene = scene
                break

        if not target_scene:
            QMessageBox.warning(self, "Lỗi", f"Không tìm thấy cảnh {scene_idx}")
            return

        # Get character bible
        character_bible = self.cache.get("character_bible")

        # Create a single-scene image worker
        from services.account_manager import get_account_manager
        account_mgr = get_account_manager()

        # Create a temporary outline with only this scene
        temp_outline = {"scenes": [target_scene]}

        self.img_worker = ImageGenerationWorker(
            temp_outline, cfg, model_paths,
            self.prod_paths, use_whisk, character_bible,
            account_mgr=account_mgr
        )

        self.img_worker.progress.connect(self._append_log)
        self.img_worker.scene_image_ready.connect(self._on_scene_image_ready)
        self.img_worker.finished.connect(lambda success: self._on_single_scene_image_finished(success, scene_idx))

        self.img_worker.start()

    def _on_single_scene_image_finished(self, success, scene_idx):
        """Callback when single scene image generation finishes"""
        if success:
            self._append_log(f"✓ Hoàn tất tạo lại ảnh cảnh {scene_idx}")
        else:
            self._append_log(f"❌ Có lỗi khi tạo lại ảnh cảnh {scene_idx}")

    def _on_scene_generate_video(self, scene_idx):
        """Generate video for a specific scene (triggered by scene card button)"""
        if not self.cache["outline"]:
            QMessageBox.warning(self, "Chưa có kịch bản", "Vui lòng viết kịch bản trước.")
            return

        # Check if this scene has an image
        if scene_idx not in self.cache.get("scene_images", {}):
            QMessageBox.warning(
                self, "Chưa có ảnh",
                f"Cảnh {scene_idx} chưa có ảnh. Vui lòng tạo ảnh trước."
            )
            return

        cfg = self._collect_cfg()

        # Find the scene data
        scenes = self.cache["outline"].get("scenes", [])
        target_scene = None
        for scene in scenes:
            if scene.get("index") == scene_idx:
                target_scene = scene
                break

        if not target_scene:
            QMessageBox.warning(self, "Lỗi", f"Không tìm thấy cảnh {scene_idx}")
            return

        self._append_log(f"🎬 Bắt đầu tạo video cho cảnh {scene_idx}...")

        # Get video prompt
        video_prompt = target_scene.get("prompt_video", "")
        if not video_prompt:
            QMessageBox.warning(
                self, "Thiếu prompt",
                f"Cảnh {scene_idx} không có prompt video"
            )
            return

        # Get aspect ratio from config
        aspect_ratio = cfg.get("ratio", "9:16")

        # Map aspect ratio to API format
        aspect_map = {
            "9:16": "VIDEO_ASPECT_RATIO_PORTRAIT",
            "16:9": "VIDEO_ASPECT_RATIO_LANDSCAPE",
            "1:1": "VIDEO_ASPECT_RATIO_SQUARE"
        }
        aspect_api = aspect_map.get(aspect_ratio, "VIDEO_ASPECT_RATIO_PORTRAIT")

        # Get project name for output directory
        project_name = cfg.get("project_name", "default")
        if svc:
            dirs = svc.ensure_project_dirs(project_name)
            dir_videos = str(dirs["video"])
        else:
            dir_videos = str(Path.home() / "Downloads" / project_name / "Video")
            Path(dir_videos).mkdir(parents=True, exist_ok=True)

        # Prepare payload for video worker
        payload = {
            "scenes": [{
                "prompt": video_prompt,
                "aspect": aspect_api
            }],
            "copies": 1,
            "model_key": "veo_3_1_t2v_fast_ultra",  # Default model
            "title": f"{project_name}_scene{scene_idx}",
            "dir_videos": dir_videos,
            "upscale_4k": False,
            "auto_download": True,
            "quality": "1080p"
        }

        # Import and create video worker
        try:
            from ui.workers.video_worker import VideoGenerationWorker

            # Create worker
            self.video_worker = VideoGenerationWorker(payload)

            # Connect signals
            self.video_worker.log.connect(self._append_log)
            self.video_worker.scene_completed.connect(
                lambda scene, path: self._on_single_scene_video_completed(scene_idx, path)
            )
            self.video_worker.error_occurred.connect(
                lambda err: self._append_log(f"❌ Lỗi tạo video cảnh {scene_idx}: {err}")
            )

            # Start worker
            self.video_worker.start()

        except ImportError as e:
            self._append_log(f"❌ Không thể import VideoGenerationWorker: {e}")
            QMessageBox.warning(
                self, "Lỗi",
                "Không thể khởi động video generation worker"
            )

    def _on_single_scene_video_completed(self, scene_idx, video_path):
        """Callback when single scene video generation completes"""
        self._append_log(f"✓ Hoàn tất tạo video cảnh {scene_idx}: {video_path}")

        # Auto-download if enabled
        if self.chk_auto_download and self.chk_auto_download.isChecked():
            self._auto_download_video(video_path)

    def stop_processing(self):
        """Stop all workers"""
        if hasattr(self, "script_worker") and self.script_worker:
            if self.script_worker.isRunning():
                self.script_worker.terminate()
                self._append_log("[INFO] Đã dừng script worker")

        if hasattr(self, "img_worker") and self.img_worker:
            if self.img_worker.isRunning():
                self.img_worker.terminate()
                self._append_log("[INFO] Đã dừng image worker")

        # Re-enable buttons
        self.btn_script.setEnabled(True)
        self.btn_script.setText("📝 Viết kịch bản")
        self.btn_images.setEnabled(True)
        self.btn_stop.setEnabled(False)

        self._append_log("[INFO] Đã dừng xử lý")

    def _change_download_path(self):
        """Change download folder via file dialog"""
        if self.ed_download_path is None:
            self._append_log("⚠ Chức năng này đã được chuyển sang tab Cài đặt")
            return

        current_path = self.ed_download_path.text()

        new_path = QFileDialog.getExistingDirectory(
            self,
            "Chọn thư mục lưu video",
            current_path,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )

        if new_path:
            self.ed_download_path.setText(new_path)
            self._append_log(f"✓ Đổi thư mục tải: {new_path}")

    def _auto_download_video(self, source_path):
        """
        Copy video to download folder and open folder

        Args:
            source_path (str): Path to the source video file to download
        """
        if self.ed_download_path is None:
            download_dir = Path.home() / "Downloads" / "VideoSuperUltra"
        else:
            try:
                download_dir = Path(self.ed_download_path.text())
            except:
                download_dir = Path.home() / "Downloads" / "VideoSuperUltra"

        try:
            download_dir.mkdir(parents=True, exist_ok=True)

            source = Path(source_path)
            destination = download_dir / source.name

            # Copy file
            shutil.copy2(source, destination)

            self._append_log(f"✓ Đã tải về: {destination}")

            # Show notification
            reply = QMessageBox.question(
                self,
                "Tải thành công",
                f"Video đã được tải về:\n{destination}\n\nMở thư mục?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )

            if reply == QMessageBox.Yes:
                self._open_folder(download_dir)

        except Exception as e:
            self._append_log(f"✗ Lỗi tải video: {e}")
            QMessageBox.warning(self, "Lỗi", f"Không thể tải video:\n{e}")

    def _open_folder(self, folder_path):
        """
        Open folder in file explorer

        Args:
            folder_path (Path): Path object or string path to the folder to open
        """
        try:
            if platform.system() == 'Windows':
                subprocess.Popen(['explorer', str(folder_path)])
            elif platform.system() == 'Darwin':
                subprocess.Popen(['open', str(folder_path)])
            else:
                subprocess.Popen(['xdg-open', str(folder_path)])
        except Exception as e:
            self._append_log(f"⚠ Không thể mở thư mục: {e}")


# END OF FILE
