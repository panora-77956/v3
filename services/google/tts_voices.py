# -*- coding: utf-8 -*-
"""Google Cloud Text-to-Speech Voices Fetcher"""

import requests
import json
from typing import List, Dict

# Hardcoded fallback voices (if API fails)
FALLBACK_VOICES = {
    "vi": [
        {"name": "vi-VN-Standard-A", "ssmlGender": "FEMALE"},
        {"name": "vi-VN-Standard-B", "ssmlGender": "MALE"},
        {"name": "vi-VN-Standard-C", "ssmlGender": "FEMALE"},
        {"name": "vi-VN-Standard-D", "ssmlGender": "MALE"},
        {"name": "vi-VN-Wavenet-A", "ssmlGender": "FEMALE"},
        {"name": "vi-VN-Wavenet-B", "ssmlGender": "MALE"},
    ],
    "en": [
        {"name": "en-US-Standard-A", "ssmlGender": "MALE"},
        {"name": "en-US-Standard-B", "ssmlGender": "MALE"},
        {"name": "en-US-Standard-C", "ssmlGender": "FEMALE"},
        {"name": "en-US-Standard-D", "ssmlGender": "MALE"},
        {"name": "en-US-Wavenet-A", "ssmlGender": "MALE"},
        {"name": "en-US-Wavenet-B", "ssmlGender": "MALE"},
        {"name": "en-US-Wavenet-C", "ssmlGender": "FEMALE"},
        {"name": "en-US-Wavenet-D", "ssmlGender": "MALE"},
    ],
}

_VOICES_CACHE = {}

def get_available_voices(language_code: str = "vi", api_key: str = None) -> List[Dict]:
    """
    Get available TTS voices for a language
    
    Args:
        language_code: ISO language code (vi, en, ja, ko, etc.)
        api_key: Google Cloud API key (optional)
    
    Returns:
        List of voice dicts with 'name' and 'ssmlGender'
    """
    # Check cache
    if language_code in _VOICES_CACHE:
        return _VOICES_CACHE[language_code]
    
    # Try API if key provided
    if api_key:
        try:
            url = f"https://texttospeech.googleapis.com/v1/voices?key={api_key}"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            all_voices = data.get("voices", [])
            
            # Filter by language
            filtered = [
                {
                    "name": v["name"],
                    "ssmlGender": v.get("ssmlGender", "NEUTRAL")
                }
                for v in all_voices
                if v["languageCodes"][0].startswith(language_code)
            ]
            
            if filtered:
                _VOICES_CACHE[language_code] = filtered
                return filtered
        except Exception as e:
            print(f"[WARN] Failed to fetch voices from API: {e}")
    
    # Fallback to hardcoded
    fallback = FALLBACK_VOICES.get(language_code, FALLBACK_VOICES.get("en", []))
    _VOICES_CACHE[language_code] = fallback
    return fallback

def format_voice_name(voice: Dict) -> str:
    """Format voice for display: 'vi-VN-Standard-A (Female)'"""
    name = voice["name"]
    gender = voice["ssmlGender"].capitalize()
    return f"{name} ({gender})"
