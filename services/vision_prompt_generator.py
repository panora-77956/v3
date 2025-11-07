# services/vision_prompt_generator.py
"""
Vision Prompt Generator Service
Generate descriptive prompts from video frames using Gemini Vision API
"""

import base64
import os
from typing import List, Optional
import requests

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None


class VisionPromptGenerator:
    """Generate prompts from images using Gemini Vision API"""
    
    def __init__(self, api_key: str = None, log_callback=None):
        """
        Initialize vision prompt generator
        
        Args:
            api_key: Google API key (if None, will try to get from key manager)
            log_callback: Optional callback for logging
        """
        self.log = log_callback or print
        self.api_key = api_key
        
        # Try to get API key from key manager if not provided
        if not self.api_key:
            try:
                from services.core.key_manager import get_all_keys
                keys = get_all_keys('google')
                if keys:
                    self.api_key = keys[0]
            except Exception as e:
                self.log(f"[VisionPrompt] Warning: Could not load API key: {e}")
    
    def generate_scene_prompts(
        self, 
        scenes: List[dict], 
        language: str = "vi",
        style: str = "Cinematic"
    ) -> List[str]:
        """
        Generate prompts for multiple scenes
        
        Args:
            scenes: List of scene dicts with 'frame_path' key
            language: Target language for prompts (vi, en, ja, ko, etc.)
            style: Video style (Cinematic, Anime, Documentary, etc.)
        
        Returns:
            List of generated prompts (one per scene)
        """
        prompts = []
        
        for i, scene in enumerate(scenes):
            frame_path = scene.get('frame_path')
            if not frame_path or not os.path.exists(frame_path):
                self.log(f"[VisionPrompt] Warning: Frame {i} not found")
                prompts.append("")
                continue
            
            try:
                prompt = self._generate_prompt_for_frame(
                    frame_path, 
                    language=language,
                    style=style,
                    scene_index=i
                )
                prompts.append(prompt)
                self.log(f"[VisionPrompt] ✓ Generated prompt {i+1}/{len(scenes)}")
                
            except Exception as e:
                self.log(f"[VisionPrompt] Error generating prompt for scene {i}: {e}")
                prompts.append("")
        
        return prompts
    
    def _generate_prompt_for_frame(
        self, 
        frame_path: str,
        language: str = "vi",
        style: str = "Cinematic",
        scene_index: int = 0
    ) -> str:
        """
        Generate a descriptive prompt for a single frame
        
        Args:
            frame_path: Path to image file
            language: Target language
            style: Video style
            scene_index: Index of scene (for logging)
        
        Returns:
            Generated prompt text
        """
        if not self.api_key:
            raise RuntimeError("Google API key not configured")
        
        # Prepare image
        image_data = self._prepare_image(frame_path)
        
        # Build system instruction based on language and style
        system_instruction = self._build_system_instruction(language, style)
        
        # Call Gemini Vision API
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": image_data
                            }
                        },
                        {
                            "text": system_instruction
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 200
            }
        }
        
        try:
            response = requests.post(
                endpoint,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            if 'candidates' in data and len(data['candidates']) > 0:
                content = data['candidates'][0]['content']
                if 'parts' in content and len(content['parts']) > 0:
                    return content['parts'][0]['text'].strip()
            
            raise RuntimeError("No content in response")
            
        except requests.RequestException as e:
            raise RuntimeError(f"Vision API request failed: {e}")
    
    def _prepare_image(self, image_path: str, max_size: int = 1024) -> str:
        """
        Prepare image for API: resize if needed and encode to base64
        
        Args:
            image_path: Path to image file
            max_size: Maximum dimension (width or height)
        
        Returns:
            Base64 encoded image data
        """
        if not PIL_AVAILABLE:
            raise RuntimeError(
                "PIL/Pillow>=10.0.0 is required for image processing. "
                "Install it with: pip install Pillow>=10.0.0"
            )
        
        try:
            # Open and resize image if needed
            img = Image.open(image_path)
            
            # Resize if too large
            if max(img.size) > max_size:
                ratio = max_size / max(img.size)
                new_size = tuple(int(dim * ratio) for dim in img.size)
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Save to bytes and encode
            import io
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            image_bytes = buffer.getvalue()
            
            return base64.b64encode(image_bytes).decode('utf-8')
            
        except Exception as e:
            raise RuntimeError(f"Image preparation failed: {e}")
    
    def _build_system_instruction(self, language: str, style: str) -> str:
        """
        Build system instruction for prompt generation
        
        Args:
            language: Target language code
            style: Video style
        
        Returns:
            System instruction text
        """
        lang_map = {
            'vi': 'Vietnamese',
            'en': 'English',
            'ja': 'Japanese',
            'ko': 'Korean',
            'zh': 'Chinese',
            'es': 'Spanish',
            'fr': 'French'
        }
        
        lang_name = lang_map.get(language, 'English')
        
        instruction = f"""Analyze this video frame and generate a detailed, descriptive prompt for video generation.

Requirements:
1. Describe the scene in {lang_name}
2. Style: {style}
3. Include: main subjects, actions, setting, lighting, camera angle
4. Be concise but vivid (2-3 sentences max)
5. Focus on visual elements that can be recreated in video

Output only the prompt text, nothing else."""
        
        return instruction
    
    def transcribe_audio(
        self, 
        video_path: str, 
        language: str = "vi"
    ) -> str:
        """
        Extract and transcribe audio from video
        
        Note: This is a placeholder. Actual implementation would use
        Whisper API or Google Speech-to-Text
        
        Args:
            video_path: Path to video file
            language: Language code
        
        Returns:
            Transcribed text
        """
        self.log("[VisionPrompt] Audio transcription not yet implemented")
        return "[Audio transcription feature coming soon]"
