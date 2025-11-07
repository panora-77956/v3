# -*- coding: utf-8 -*-
"""
Image Worker - Non-blocking image generation using QThread
"""
import time

from PyQt5.QtCore import QThread, pyqtSignal

from utils.image_utils import convert_to_bytes


class ImageWorker(QThread):
    """
    Background worker for image generation
    Prevents UI freezing during image generation API calls
    """

    # Signals
    progress = pyqtSignal(int, str)     # Scene index, progress message
    scene_done = pyqtSignal(int, bytes) # Scene index, image bytes
    all_done = pyqtSignal()             # All scenes completed
    error = pyqtSignal(int, str)        # Scene index, error message

    def __init__(self, scenes: list, model: str = "gemini", parent=None):
        """
        Initialize image worker
        
        Args:
            scenes: List of scene dictionaries with 'prompt' and 'index' keys
            model: Model to use ("gemini" or "whisk")
            parent: Parent QObject
        """
        super().__init__(parent)
        self.scenes = scenes
        self.model = model

    def run(self):
        """Execute image generation in background thread"""
        # Get API keys from config
        from services.core.config import load as load_cfg
        cfg = load_cfg()
        api_keys = cfg.get('google_api_keys', [])
        
        if not api_keys:
            self.error.emit(0, "Không có Google API keys trong config")
            self.all_done.emit()
            return
        
        for i, scene in enumerate(self.scenes):
            try:
                scene_idx = scene.get('index', i)
                prompt = scene.get('prompt', '')
                aspect_ratio = scene.get('aspect_ratio', '1:1')

                self.progress.emit(scene_idx, f"Đang tạo ảnh cảnh {scene_idx + 1}...")

                # Generate image based on model using rate-limited function
                if self.model == "gemini":
                    from services.image_gen_service import generate_image_with_rate_limit
                    img_result = generate_image_with_rate_limit(
                        prompt=prompt,
                        api_keys=api_keys,
                        model="gemini",
                        aspect_ratio=aspect_ratio,
                        logger=lambda msg: self.progress.emit(scene_idx, msg)
                    )
                    
                    # Handle both bytes and data URL string formats
                    img_bytes = None
                    if img_result:
                        img_bytes, error = convert_to_bytes(img_result)
                        if not img_bytes and error:
                            self.error.emit(scene_idx, error)
                else:
                    from services.whisk_service import generate_image
                    img_bytes = generate_image(prompt)

                if img_bytes:
                    self.scene_done.emit(scene_idx, img_bytes)
                else:
                    self.error.emit(scene_idx, "Không nhận được dữ liệu ảnh")

                # Rate limiting between requests (reduced since generate_image_with_rate_limit handles it)
                time.sleep(0.5)

            except Exception as e:
                self.error.emit(scene_idx, f"Lỗi: {str(e)}")

        self.all_done.emit()
