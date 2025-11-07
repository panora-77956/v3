# services/scene_detector.py
"""
Scene Detection Service
Extract key frames from video using ffmpeg scene detection
"""

import os
import shutil
import subprocess
import tempfile
from typing import List, Dict
import json


class SceneDetector:
    """Detect scenes in video and extract key frames"""

    def __init__(self, log_callback=None):
        """
        Initialize scene detector
        
        Args:
            log_callback: Optional callback for logging
        """
        self.log = log_callback or print

    def extract_scenes(
        self, 
        video_path: str, 
        num_scenes: int = 5,
        threshold: float = 0.3
    ) -> List[Dict]:
        """
        Extract key frames from video based on scene detection
        
        Args:
            video_path: Path to input video file
            num_scenes: Number of scenes to extract (default: 5)
            threshold: Scene detection threshold 0.0-1.0 (default: 0.3)
        
        Returns:
            List of dicts with {timestamp, frame_path, duration, scene_index}
        
        Raises:
            FileNotFoundError: If video file doesn't exist
            RuntimeError: If ffmpeg fails
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        self.log(f"[SceneDetector] Analyzing video: {os.path.basename(video_path)}")

        # Get video duration first
        duration = self._get_video_duration(video_path)
        self.log(f"[SceneDetector] Video duration: {duration:.2f}s")

        # Create temp directory for frames
        temp_dir = tempfile.mkdtemp(prefix="scene_frames_")

        try:
            # Detect scene changes
            scene_times = self._detect_scene_changes(video_path, threshold, num_scenes)

            if not scene_times:
                # Fallback: extract evenly spaced frames
                self.log("[SceneDetector] No scenes detected, using evenly spaced frames")
                scene_times = self._get_evenly_spaced_times(duration, num_scenes)

            # Extract frames at scene times
            scenes = []
            for i, timestamp in enumerate(scene_times[:num_scenes]):
                frame_path = os.path.join(temp_dir, f"scene_{i:03d}.jpg")

                if self._extract_frame(video_path, timestamp, frame_path):
                    scenes.append({
                        'scene_index': i,
                        'timestamp': timestamp,
                        'frame_path': frame_path,
                        'duration': duration
                    })
                    self.log(f"[SceneDetector] ✓ Extracted scene {i+1}/{num_scenes} at {timestamp:.2f}s")

            self.log(f"[SceneDetector] Extracted {len(scenes)} scenes")
            return scenes

        except Exception as e:
            # Clean up temp directory on error
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError(f"Scene extraction failed: {e}")

    def _get_video_duration(self, video_path: str) -> float:
        """Get video duration using ffprobe"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'json',
                video_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                raise RuntimeError(f"ffprobe failed: {result.stderr}")

            data = json.loads(result.stdout)
            return float(data['format']['duration'])

        except Exception as e:
            self.log(f"[SceneDetector] Warning: Could not get duration: {e}")
            return 60.0  # Default fallback

    def _detect_scene_changes(
        self, 
        video_path: str, 
        threshold: float,
        max_scenes: int
    ) -> List[float]:
        """
        Detect scene changes using ffmpeg's scene detection filter
        
        Returns:
            List of timestamps where scenes change
        """
        try:
            # Use ffmpeg scene detection filter
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vf', f'select=gt(scene\\,{threshold}),showinfo',
                '-f', 'null',
                '-'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            # Parse scene times from stderr (ffmpeg outputs to stderr)
            scene_times = []
            for line in result.stderr.split('\n'):
                if 'pts_time:' in line:
                    try:
                        # Extract timestamp from showinfo output
                        pts_time = line.split('pts_time:')[1].split()[0]
                        scene_times.append(float(pts_time))
                    except (IndexError, ValueError):
                        continue

            # Return unique sorted times
            return sorted(list(set(scene_times)))[:max_scenes]

        except Exception as e:
            self.log(f"[SceneDetector] Warning: Scene detection failed: {e}")
            return []

    def _get_evenly_spaced_times(self, duration: float, num_scenes: int) -> List[float]:
        """Generate evenly spaced timestamps as fallback"""
        if num_scenes <= 1:
            return [duration / 2.0]

        interval = duration / (num_scenes + 1)
        return [interval * (i + 1) for i in range(num_scenes)]

    def _extract_frame(self, video_path: str, timestamp: float, output_path: str) -> bool:
        """
        Extract a single frame at given timestamp
        
        Args:
            video_path: Input video path
            timestamp: Time in seconds
            output_path: Output image path
        
        Returns:
            True if successful, False otherwise
        """
        try:
            cmd = [
                'ffmpeg',
                '-ss', str(timestamp),
                '-i', video_path,
                '-vframes', '1',
                '-q:v', '2',  # High quality
                '-y',  # Overwrite
                output_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30
            )

            return result.returncode == 0 and os.path.exists(output_path)

        except Exception as e:
            self.log(f"[SceneDetector] Warning: Frame extraction failed: {e}")
            return False

    def get_video_metadata(self, video_path: str) -> Dict:
        """
        Get video metadata (duration, resolution, fps)
        
        Args:
            video_path: Path to video file
        
        Returns:
            Dict with metadata
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height,r_frame_rate,duration',
                '-show_entries', 'format=duration',
                '-of', 'json',
                video_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                raise RuntimeError(f"ffprobe failed: {result.stderr}")

            data = json.loads(result.stdout)
            stream = data.get('streams', [{}])[0]
            format_info = data.get('format', {})

            # Parse frame rate
            fps_str = stream.get('r_frame_rate', '30/1')
            try:
                num, den = map(int, fps_str.split('/'))
                fps = num / den if den != 0 else 30.0
            except (ValueError, ZeroDivisionError, AttributeError) as e:
                self.log(f"[SceneDetector] Warning: Could not parse FPS '{fps_str}': {e}")
                fps = 30.0

            return {
                'width': stream.get('width', 0),
                'height': stream.get('height', 0),
                'fps': fps,
                'duration': float(format_info.get('duration', stream.get('duration', 0)))
            }

        except Exception as e:
            self.log(f"[SceneDetector] Warning: Could not get metadata: {e}")
            return {
                'width': 1920,
                'height': 1080,
                'fps': 30.0,
                'duration': 0.0
            }
