# services/video_clone_service.py
"""
Video Clone Service
Download and analyze videos from TikTok/YouTube URLs
"""

import os
import shutil
import subprocess
import sys
import tempfile
from typing import Callable, Dict, Optional, Set
from urllib.parse import urlparse


class VideoCloneService:
    """Service to download and analyze videos from social media platforms"""

    def __init__(self, log_callback: Optional[Callable] = None):
        """
        Initialize video clone service

        Args:
            log_callback: Optional callback for logging
        """
        self.log = log_callback or print
        self._temp_dirs: Set[str] = set()  # Track temp directories we create
        self._check_dependencies()

    def _check_dependencies(self):
        """
        Check if required dependencies (yt-dlp, ffmpeg) are available
        Logs warnings but doesn't raise errors during initialization
        """
        # Check for yt-dlp Python module
        yt_dlp_available = False
        try:
            import yt_dlp
            yt_dlp_available = True
            self.log(f"[VideoClone] yt-dlp version: {yt_dlp.version.__version__}")
        except ImportError:
            self.log("[VideoClone] WARNING: yt-dlp module not found")
        except Exception as e:
            self.log(f"[VideoClone] WARNING: Error checking yt-dlp: {e}")

        self._yt_dlp_available = yt_dlp_available

        # Check for ffmpeg
        ffmpeg_available = False
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                ffmpeg_available = True
                # Extract version from first line
                version_line = result.stdout.split('\n')[0]
                self.log(f"[VideoClone] {version_line}")
        except FileNotFoundError:
            self.log("[VideoClone] WARNING: ffmpeg not found in PATH")
        except Exception as e:
            self.log(f"[VideoClone] WARNING: Error checking ffmpeg: {e}")

        self._ffmpeg_available = ffmpeg_available

    def is_yt_dlp_available(self) -> bool:
        """
        Check if yt-dlp is available

        Returns:
            True if yt-dlp is available, False otherwise
        """
        return self._yt_dlp_available

    def is_ffmpeg_available(self) -> bool:
        """
        Check if ffmpeg is available

        Returns:
            True if ffmpeg is available, False otherwise
        """
        return self._ffmpeg_available

    def get_installation_instructions(self) -> str:
        """
        Get installation instructions for missing dependencies

        Returns:
            Formatted installation instructions
        """
        instructions = []

        if not self._yt_dlp_available:
            if sys.platform == 'win32':
                instructions.append(
                    "yt-dlp Python module is not installed.\n\n"
                    "To install yt-dlp on Windows:\n"
                    "1. Using pip: pip install yt-dlp\n"
                    "2. Or using the requirements file: pip install -r requirements.txt\n"
                )
            else:
                instructions.append(
                    "yt-dlp Python module is not installed.\n\n"
                    "To install yt-dlp:\n"
                    "- Using pip: pip install yt-dlp\n"
                    "- Or using the requirements file: pip install -r requirements.txt\n"
                )

        if not self._ffmpeg_available:
            if sys.platform == 'win32':
                instructions.append(
                    "ffmpeg is not installed or not in PATH.\n\n"
                    "To install ffmpeg on Windows:\n"
                    "1. Download from: https://ffmpeg.org/download.html\n"
                    "2. Extract and add to system PATH\n"
                )
            else:
                instructions.append(
                    "ffmpeg is not installed or not in PATH.\n\n"
                    "To install ffmpeg:\n"
                    "- Ubuntu/Debian: sudo apt-get install ffmpeg\n"
                    "- macOS: brew install ffmpeg\n"
                )

        return "\n".join(instructions)

    def download_video(
        self,
        url: str,
        platform: str = "auto",
        output_dir: Optional[str] = None
    ) -> str:
        """
        Download video from URL using yt-dlp

        Args:
            url: Video URL (TikTok or YouTube)
            platform: Platform type ('tiktok', 'youtube', or 'auto')
            output_dir: Output directory (if None, uses temp directory)

        Returns:
            Path to downloaded video file

        Raises:
            ValueError: If URL is invalid
            RuntimeError: If download fails or yt-dlp is not available
        """
        # Check if yt-dlp is available
        if not self._yt_dlp_available:
            error_msg = (
                "yt-dlp Python module is not installed.\n\n"
                + self.get_installation_instructions()
            )
            self.log("[VideoClone] ERROR: yt-dlp not available")
            raise RuntimeError(error_msg)

        # Validate URL using urlparse
        if not url:
            raise ValueError("URL is empty")

        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid URL format")
            if parsed.scheme not in ('http', 'https'):
                raise ValueError("URL must use http or https protocol")
        except Exception as e:
            raise ValueError(f"Invalid URL: {e}")

        # Auto-detect platform if needed
        if platform == "auto":
            platform = self._detect_platform(url)
            self.log(f"[VideoClone] Detected platform: {platform}")

        # Create output directory
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="video_clone_")
            self._temp_dirs.add(output_dir)  # Track temp directory
        os.makedirs(output_dir, exist_ok=True)

        # Set output template
        output_template = os.path.join(output_dir, "%(title)s.%(ext)s")

        self.log(f"[VideoClone] Downloading from {platform}...")
        self.log(f"[VideoClone] Output directory: {output_dir}")

        try:
            import yt_dlp

            # Configure yt-dlp options
            ydl_opts = {
                'format': 'best[ext=mp4]/best',  # Prefer mp4 format
                'noplaylist': True,  # Don't download playlists
                'outtmpl': output_template,
                'quiet': False,
                'no_warnings': False,
            }

            # Add platform-specific options
            if platform == 'tiktok':
                # TikTok specific options
                ydl_opts['http_headers'] = {'User-Agent': 'Mozilla/5.0'}

            self.log("[VideoClone] Running yt-dlp download...")

            # Download using yt-dlp Python API
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Download the video
                info = ydl.extract_info(url, download=True)

                # Get the downloaded filename
                if 'requested_downloads' in info and info['requested_downloads']:
                    video_path = info['requested_downloads'][0]['filepath']
                else:
                    # Fallback: construct filename from template
                    filename = ydl.prepare_filename(info)
                    video_path = filename

            # Verify file exists
            if not os.path.exists(video_path):
                # Try to find any video file in the output directory
                video_files = [
                    os.path.join(output_dir, f)
                    for f in os.listdir(output_dir)
                    if f.endswith(('.mp4', '.webm', '.mkv'))
                ]

                if not video_files:
                    raise RuntimeError("No video file found after download")

                video_path = video_files[0]

            self.log(f"[VideoClone] ✓ Downloaded: {os.path.basename(video_path)}")

            return video_path

        except ImportError as e:
            # This should not happen as we check _yt_dlp_available, but keep as safety
            error_msg = (
                "yt-dlp module not found. Please ensure yt-dlp is installed.\n\n"
                + self.get_installation_instructions()
            )
            self.log(f"[VideoClone] ERROR: {error_msg}")
            raise RuntimeError(error_msg) from e
        except Exception as e:
            self.log(f"[VideoClone] ERROR: Download failed: {e}")
            raise RuntimeError(f"Download failed: {e}")

    def _detect_platform(self, url: str) -> str:
        """
        Auto-detect platform from URL using hostname parsing

        Args:
            url: Video URL

        Returns:
            Platform name ('tiktok', 'youtube', or 'unknown')
        """
        try:
            parsed = urlparse(url)
            hostname = parsed.netloc.lower()

            # Remove 'www.' prefix if present
            if hostname.startswith('www.'):
                hostname = hostname[4:]

            # Check for TikTok domains
            if hostname == 'tiktok.com' or hostname.endswith('.tiktok.com'):
                return 'tiktok'

            # Check for YouTube domains
            if hostname in ('youtube.com', 'youtu.be') or hostname.endswith('.youtube.com'):
                return 'youtube'

            return 'unknown'

        except Exception:
            return 'unknown'

    def analyze_video(
        self,
        video_path: str,
        num_scenes: int = 5,
        language: str = "vi",
        style: str = "Cinematic",
        api_key: Optional[str] = None
    ) -> Dict:
        """
        Analyze video: extract scenes and generate prompts

        Args:
            video_path: Path to video file
            num_scenes: Number of scenes to extract
            language: Language for prompts
            style: Video style
            api_key: Google API key for vision API

        Returns:
            Dict with analysis results: {
                'scenes': List[Dict],
                'prompts': List[str],
                'metadata': Dict,
                'transcription': str
            }
        """
        from services.scene_detector import SceneDetector
        from services.vision_prompt_generator import VisionPromptGenerator

        self.log("[VideoClone] Analyzing video...")

        # Extract scenes
        detector = SceneDetector(log_callback=self.log)
        scenes = detector.extract_scenes(video_path, num_scenes=num_scenes)

        # Get metadata
        metadata = detector.get_video_metadata(video_path)

        # Generate prompts using vision API
        vision_gen = VisionPromptGenerator(api_key=api_key, log_callback=self.log)
        prompts = vision_gen.generate_scene_prompts(
            scenes,
            language=language,
            style=style
        )

        # Transcribe audio (placeholder for now)
        transcription = vision_gen.transcribe_audio(video_path, language=language)

        self.log("[VideoClone] ✓ Analysis complete")

        return {
            'scenes': scenes,
            'prompts': prompts,
            'metadata': metadata,
            'transcription': transcription
        }

    def validate_url(self, url: str) -> tuple:
        """
        Validate URL and detect platform

        Args:
            url: Video URL to validate

        Returns:
            Tuple of (is_valid: bool, platform: str, error_msg: str)
        """
        if not url:
            return False, "", "URL is empty"

        # Use urlparse for robust validation
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False, "", "Invalid URL format"
            if parsed.scheme not in ('http', 'https'):
                return False, "", "URL must use http or https protocol"
        except Exception as e:
            return False, "", f"Invalid URL: {e}"

        platform = self._detect_platform(url)

        if platform == 'unknown':
            return False, "", "URL is not from TikTok or YouTube"

        return True, platform, ""

    def cleanup_temp_files(self, video_path: str):
        """
        Clean up temporary files created during processing

        Args:
            video_path: Path to video file (will delete parent dir if temp)
        """
        try:
            # Check if parent directory is in our tracked temp dirs
            parent_dir = os.path.dirname(video_path)

            if parent_dir in self._temp_dirs:
                if os.path.exists(parent_dir):
                    shutil.rmtree(parent_dir, ignore_errors=True)
                    self._temp_dirs.discard(parent_dir)
                    self.log(f"[VideoClone] Cleaned up temp directory: {parent_dir}")
        except Exception as e:
            self.log(f"[VideoClone] Warning: Cleanup failed: {e}")


class VideoCloneError(Exception):
    """Custom exception for video clone errors"""
    pass
