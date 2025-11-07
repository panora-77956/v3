# -*- coding: utf-8 -*-
"""
Audio Generation Helper
Utilities to generate audio for video scenes
"""
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

from services.tts_service import generate_audio_from_scene

logger = logging.getLogger(__name__)


def generate_scene_audio(scene_data: Dict[str, Any], 
                         output_dir: str,
                         scene_index: Optional[int] = None) -> Optional[str]:
    """
    Generate audio file for a single scene
    
    Args:
        scene_data: Scene data dict (can be from JSON or generated script)
        output_dir: Directory to save audio file
        scene_index: Optional scene index (used for filename)
    
    Returns:
        Path to generated audio file, or None if failed
    """
    # Try to get scene index from data if not provided
    if scene_index is None:
        scene_index = scene_data.get("scene_index") or scene_data.get("scene", 1)

    # Ensure scene_data has the expected structure
    if "audio" not in scene_data:
        # Try to build audio config from legacy fields
        voiceover_config = {
            "tts_provider": scene_data.get("tts_provider", "google"),
            "voice_id": scene_data.get("voice_id", "vi-VN-Wavenet-A"),
            "language": scene_data.get("languageCode") or scene_data.get("language", "vi"),
            "text": scene_data.get("voiceover") or scene_data.get("speech", ""),
        }

        if not voiceover_config["text"]:
            logger.warning(f"No voiceover text found for scene {scene_index}")
            return None

        scene_data = {
            "scene_index": scene_index,
            "audio": {
                "voiceover": voiceover_config
            }
        }

    # Generate audio
    return generate_audio_from_scene(scene_data, output_dir)


def generate_batch_audio(scenes: List[Dict[str, Any]], 
                         output_dir: str) -> Dict[int, str]:
    """
    Generate audio files for multiple scenes
    
    Args:
        scenes: List of scene data dicts
        output_dir: Directory to save audio files
    
    Returns:
        Dict mapping scene index to audio file path
    """
    results = {}

    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    for i, scene in enumerate(scenes, 1):
        scene_index = scene.get("scene_index") or scene.get("scene", i)

        logger.info(f"Generating audio for scene {scene_index}...")

        audio_path = generate_scene_audio(scene, output_dir, scene_index)

        if audio_path:
            results[scene_index] = audio_path
            logger.info(f"✓ Scene {scene_index} audio: {audio_path}")
        else:
            logger.warning(f"⚠ Failed to generate audio for scene {scene_index}")

    return results


def validate_voiceover_config(voiceover_config: Dict[str, Any]) -> tuple:
    """
    Validate voiceover configuration
    
    Args:
        voiceover_config: Voiceover configuration dict
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ["tts_provider", "voice_id", "text"]

    for field in required_fields:
        if not voiceover_config.get(field):
            return False, f"Missing required field: {field}"

    # Validate provider
    valid_providers = ["google", "elevenlabs", "openai"]
    provider = voiceover_config.get("tts_provider")
    if provider not in valid_providers:
        return False, f"Invalid provider: {provider}. Must be one of {valid_providers}"

    # Provider-specific validation
    if provider == "google":
        language = voiceover_config.get("language", "vi")
        voice_id = voiceover_config.get("voice_id", "")

        # Check if language matches voice_id prefix
        if language and voice_id:
            expected_prefix = f"{language}-"
            # Map short codes to full codes
            lang_map = {
                "vi": "vi-VN",
                "en": "en-US",
                "ja": "ja-JP",
                "ko": "ko-KR",
                "zh": "zh-CN"
            }
            expected_prefix = f"{lang_map.get(language, language)}-"

            if not voice_id.startswith(expected_prefix):
                logger.warning(
                    f"Voice ID '{voice_id}' doesn't match language '{language}'. "
                    f"Expected prefix: {expected_prefix}"
                )

    return True, ""


def load_and_generate_audio(scene_json_path: str, 
                            output_dir: str) -> Optional[str]:
    """
    Load scene JSON file and generate audio
    
    Args:
        scene_json_path: Path to scene JSON file
        output_dir: Directory to save audio file
    
    Returns:
        Path to generated audio file, or None if failed
    """
    try:
        with open(scene_json_path, 'r', encoding='utf-8') as f:
            scene_data = json.load(f)

        return generate_scene_audio(scene_data, output_dir)

    except Exception as e:
        logger.error(f"Failed to load and generate audio from {scene_json_path}: {e}")
        return None
