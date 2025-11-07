# services/video_clone_service.py
"""
Video Clone Service
Download and analyze videos from TikTok/YouTube URLs
"""

import os
import shutil
import tempfile
import subprocess
from typing import List, Dict, Optional, Set
import re
from urllib.parse import urlparse


class VideoCloneService:
    """Service to download and analyze videos from social media platforms"""
    
    def __init__(self, log_callback=None):
        """
        Initialize video clone service
        
        Args:
            log_callback: Optional callback for logging
        """
        self.log = log_callback or print
        self._temp_dirs: Set[str] = set()  # Track temp directories we create
    
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
            RuntimeError: If download fails
        """
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
        
        try:
            # Build yt-dlp command
            cmd = [
                'yt-dlp',
                '-f', 'best[ext=mp4]/best',  # Prefer mp4 format
                '--no-playlist',  # Don't download playlists
                '-o', output_template,
                url
            ]
            
            # Add platform-specific options
            if platform == 'tiktok':
                # TikTok specific options
                cmd.extend(['--user-agent', 'Mozilla/5.0'])
            
            # Execute download
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                raise RuntimeError(f"Download failed: {error_msg}")
            
            # Find downloaded file
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
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("Download timeout (5 minutes exceeded)")
        except Exception as e:
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
