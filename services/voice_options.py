# -*- coding: utf-8 -*-
"""Voice Prosody & Speaking Style Controls

This module provides:
- Speaking style presets for different contexts
- SSML generation for Google TTS with prosody controls
- ElevenLabs voice settings generation
- Helper functions for rate/pitch calculations
"""

import re
from typing import Dict, Any, Optional


# ============================================================================
# TTS PROVIDERS & VOICE OPTIONS
# ============================================================================

# TTS Provider configurations (for advanced features)
TTS_PROVIDER_CONFIGS = {
    "google": {
        "name": "Google Text-to-Speech",
        "name_short": "Google TTS",
        "icon": "🔊",
        "supports_ssml": True,
        "supports_prosody": True
    },
    "elevenlabs": {
        "name": "ElevenLabs",
        "name_short": "ElevenLabs",
        "icon": "🎙️",
        "supports_ssml": False,
        "supports_prosody": True
    },
    "openai": {
        "name": "OpenAI Text-to-Speech",
        "name_short": "OpenAI TTS",
        "icon": "🤖",
        "supports_ssml": False,
        "supports_prosody": False
    }
}

# Voice options for each provider
VOICE_OPTIONS = {
    "google": {
        "vi": [
            {"id": "vi-VN-Wavenet-A", "name": "🇻🇳 Nam Miền Bắc - Wavenet", "gender": "male", "quality": "high"},
            {"id": "vi-VN-Wavenet-B", "name": "🇻🇳 Nữ Miền Bắc - Wavenet", "gender": "female", "quality": "high"},
            {"id": "vi-VN-Wavenet-C", "name": "🇻🇳 Nữ Miền Nam - Wavenet", "gender": "female", "quality": "high"},
            {"id": "vi-VN-Wavenet-D", "name": "🇻🇳 Nam Miền Nam - Wavenet", "gender": "male", "quality": "high"},
            {"id": "vi-VN-Standard-A", "name": "🇻🇳 Nam Miền Bắc - Standard", "gender": "male", "quality": "standard"},
            {"id": "vi-VN-Standard-B", "name": "🇻🇳 Nữ Miền Bắc - Standard", "gender": "female", "quality": "standard"}
        ],
        "en": [
            {"id": "en-US-Neural2-A", "name": "🇺🇸 US Male - Neural", "gender": "male", "quality": "high"},
            {"id": "en-US-Neural2-C", "name": "🇺🇸 US Female - Neural", "gender": "female", "quality": "high"},
            {"id": "en-GB-Neural2-A", "name": "🇬🇧 UK Female - Neural", "gender": "female", "quality": "high"},
            {"id": "en-GB-Neural2-B", "name": "🇬🇧 UK Male - Neural", "gender": "male", "quality": "high"}
        ],
        "ja": [
            {"id": "ja-JP-Neural2-B", "name": "🇯🇵 Japanese Female", "gender": "female", "quality": "high"},
            {"id": "ja-JP-Neural2-C", "name": "🇯🇵 Japanese Male", "gender": "male", "quality": "high"}
        ],
        "ko": [
            {"id": "ko-KR-Neural2-A", "name": "🇰🇷 Korean Female", "gender": "female", "quality": "high"},
            {"id": "ko-KR-Neural2-B", "name": "🇰🇷 Korean Male", "gender": "male", "quality": "high"}
        ],
        "zh": [
            {"id": "zh-CN-Wavenet-A", "name": "🇨🇳 Chinese Female", "gender": "female", "quality": "high"},
            {"id": "zh-CN-Wavenet-B", "name": "🇨🇳 Chinese Male", "gender": "male", "quality": "high"}
        ]
    },
    "elevenlabs": {
        "all": [
            {"id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel - Calm Narration", "gender": "female", "description": "Smooth, calming female voice"},
            {"id": "ErXwobaYiN019PkySvjV", "name": "Antoni - Young & Energetic", "gender": "male", "description": "Youthful, energetic male voice"},
            {"id": "AZnzlk1XvdvUeBnXmlld", "name": "Domi - Confident & Strong", "gender": "female", "description": "Strong, confident female voice"},
            {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella - Soft & Friendly", "gender": "female", "description": "Soft, friendly female voice"},
            {"id": "MF3mGyEYCl7XYWbV9V6O", "name": "Elli - Warm & Professional", "gender": "female", "description": "Warm, professional female voice"},
            {"id": "TxGEqnHWrfWFTfGW9XjX", "name": "Josh - Natural & Conversational", "gender": "male", "description": "Natural, conversational male voice"},
            {"id": "VR6AewLTigWG4xSOukaG", "name": "Arnold - Deep & Authoritative", "gender": "male", "description": "Deep, authoritative male voice"},
            {"id": "pNInz6obpgDQGcFmaJgB", "name": "Adam - Deep & Professional", "gender": "male", "description": "Deep, professional male voice"}
        ]
    },
    "openai": {
        "all": [
            {"id": "alloy", "name": "Alloy", "gender": "neutral", "description": "Neutral, balanced voice"},
            {"id": "echo", "name": "Echo", "gender": "male", "description": "Male voice"},
            {"id": "fable", "name": "Fable", "gender": "neutral", "description": "Expressive, storytelling voice"},
            {"id": "onyx", "name": "Onyx", "gender": "male", "description": "Deep, authoritative male voice"},
            {"id": "nova", "name": "Nova", "gender": "female", "description": "Energetic female voice"},
            {"id": "shimmer", "name": "Shimmer", "gender": "female", "description": "Soft, gentle female voice"}
        ]
    }
}

def get_provider_list():
    """Get list of available TTS providers
    
    Returns:
        List of tuples (provider_key, display_name, icon)
    """
    return [
        (key, config["name_short"], config["icon"])
        for key, config in TTS_PROVIDER_CONFIGS.items()
    ]

def get_voices_for_provider(provider: str, language: str = "vi"):
    """Get available voices for a provider and language
    
    Args:
        provider: Provider key ("google", "elevenlabs", or "openai")
        language: Language code (e.g., "vi", "en", "ja")
    
    Returns:
        List of voice dictionaries with id, name, gender, etc.
    """
    if provider in ("elevenlabs", "openai"):
        return VOICE_OPTIONS.get(provider, {}).get("all", [])
    return VOICE_OPTIONS.get(provider, {}).get(language, [])

def get_voice_info(provider: str, voice_id: str):
    """Get detailed information about a specific voice
    
    Args:
        provider: Provider key
        voice_id: Voice ID
    
    Returns:
        Dictionary with voice info, or None if not found
    """
    if provider in ("elevenlabs", "openai"):
        voices = VOICE_OPTIONS.get(provider, {}).get("all", [])
    else:
        voices = []
        for lang_voices in VOICE_OPTIONS.get(provider, {}).values():
            voices.extend(lang_voices)

    for voice in voices:
        if voice["id"] == voice_id:
            return voice
    return None

def get_default_voice(provider: str, language: str = "vi"):
    """Get default voice for a provider and language
    
    Args:
        provider: Provider key
        language: Language code
    
    Returns:
        Voice ID string
    """
    voices = get_voices_for_provider(provider, language)
    return voices[0]["id"] if voices else None

def get_voice_config(provider: str, voice_id: str, language_code: str = "vi") -> Dict[str, Any]:
    """Build voice configuration dictionary for script generation
    
    Args:
        provider: TTS provider key ("google", "elevenlabs", or "openai")
        voice_id: Voice ID
        language_code: Language code (default "vi")
    
    Returns:
        Dictionary with voice configuration including provider, voice_id, language, and metadata
    """
    voice_info = get_voice_info(provider, voice_id)

    config = {
        "provider": provider,
        "voice_id": voice_id,
        "language_code": language_code
    }

    # Add voice metadata if available
    if voice_info:
        config["voice_name"] = voice_info.get("name", voice_id)
        config["gender"] = voice_info.get("gender", "neutral")
        config["description"] = voice_info.get("description", "")

    # Add provider-specific settings
    provider_config = TTS_PROVIDER_CONFIGS.get(provider, {})
    config["supports_ssml"] = provider_config.get("supports_ssml", False)
    config["supports_prosody"] = provider_config.get("supports_prosody", False)

    return config


# Speaking Style Presets (6 presets)
SPEAKING_STYLES = {
    "professional_presentation": {
        "name": "📢 Thuyết trình chuyên nghiệp",
        "name_en": "Professional Presentation",
        "description": "Giọng trang trọng, rõ ràng, phù hợp thuyết trình",
        "google_tts": {
            "rate": "medium",
            "pitch": "0st",
            "volume": "loud"
        },
        "elevenlabs": {
            "stability": 0.85,
            "similarity_boost": 0.75,
            "style": 0.3
        }
    },
    "conversational": {
        "name": "💬 Trò chuyện tự nhiên",
        "name_en": "Casual Conversation",
        "description": "Giọng thân thiện, tự nhiên như nói chuyện",
        "google_tts": {
            "rate": "medium",
            "pitch": "+1st",
            "volume": "medium"
        },
        "elevenlabs": {
            "stability": 0.65,
            "similarity_boost": 0.80,
            "style": 0.6
        }
    },
    "storytelling": {
        "name": "📖 Kể chuyện",
        "name_en": "Storytelling",
        "description": "Giọng sinh động, có cảm xúc, hấp dẫn",
        "google_tts": {
            "rate": "slow",
            "pitch": "+2st",
            "volume": "medium"
        },
        "elevenlabs": {
            "stability": 0.55,
            "similarity_boost": 0.85,
            "style": 0.75
        }
    },
    "educational": {
        "name": "🎓 Giảng dạy",
        "name_en": "Educational",
        "description": "Giọng rõ ràng, từ tốn, dễ hiểu",
        "google_tts": {
            "rate": "slow",
            "pitch": "0st",
            "volume": "loud"
        },
        "elevenlabs": {
            "stability": 0.90,
            "similarity_boost": 0.70,
            "style": 0.2
        }
    },
    "enthusiastic": {
        "name": "🎉 Nhiệt tình",
        "name_en": "Enthusiastic",
        "description": "Giọng đầy năng lượng, phấn khởi",
        "google_tts": {
            "rate": "fast",
            "pitch": "+3st",
            "volume": "loud"
        },
        "elevenlabs": {
            "stability": 0.50,
            "similarity_boost": 0.85,
            "style": 0.85
        }
    },
    "calm_relaxed": {
        "name": "😌 Thư giãn",
        "name_en": "Calm & Relaxed",
        "description": "Giọng nhẹ nhàng, êm dịu, thư giãn",
        "google_tts": {
            "rate": "slow",
            "pitch": "-1st",
            "volume": "soft"
        },
        "elevenlabs": {
            "stability": 0.80,
            "similarity_boost": 0.75,
            "style": 0.4
        }
    }
}

# TTS Provider Options (ID, Display Name)
TTS_PROVIDERS = [
    ("google", "Google TTS"),
    ("elevenlabs", "ElevenLabs"),
    ("openai", "OpenAI TTS"),
]


def _calculate_rate(preset_rate: str, multiplier: float = 1.0) -> str:
    """Calculate final speaking rate from preset and user multiplier
    
    Args:
        preset_rate: Preset rate string ("slow", "medium", "fast")
        multiplier: User adjustment multiplier (0.5 - 2.0)
    
    Returns:
        Rate string for SSML (e.g., "80%", "100%", "125%")
    """
    # Map preset to percentage
    rate_map = {
        "slow": 75,
        "medium": 100,
        "fast": 125
    }

    base_rate = rate_map.get(preset_rate, 100)
    final_rate = int(base_rate * multiplier)

    # Clamp to reasonable range (50% - 200%)
    final_rate = max(50, min(200, final_rate))

    return f"{final_rate}%"


def _calculate_pitch(preset_pitch: str, adjust_semitones: int = 0) -> str:
    """Calculate final pitch from preset and user adjustment
    
    Args:
        preset_pitch: Preset pitch string (e.g., "0st", "+1st", "-2st")
        adjust_semitones: User adjustment in semitones (-5 to +5)
    
    Returns:
        Pitch string for SSML (e.g., "+2st", "-1st", "0st")
    """
    # Parse preset pitch
    preset_value = 0
    if preset_pitch:
        # Extract number from string like "+2st" or "-1st"
        match = re.match(r'([+-]?\d+)st', preset_pitch)
        if match:
            preset_value = int(match.group(1))

    # Add user adjustment
    final_pitch = preset_value + adjust_semitones

    # Clamp to reasonable range (-5 to +5 semitones)
    final_pitch = max(-5, min(5, final_pitch))

    # Format as SSML string
    if final_pitch > 0:
        return f"+{final_pitch}st"
    elif final_pitch < 0:
        return f"{final_pitch}st"
    else:
        return "0st"


def get_google_tts_ssml(text: str, voice_id: str, style_preset: str = "storytelling",
                        rate_multiplier: float = 1.0, pitch_adjust: int = 0,
                        volume: Optional[str] = None) -> str:
    """Generate SSML markup for Google TTS with prosody controls
    
    Args:
        text: Text to speak
        voice_id: Google TTS voice ID (e.g., "vi-VN-Wavenet-A")
        style_preset: Style preset key from SPEAKING_STYLES
        rate_multiplier: Speaking rate multiplier (0.5 - 2.0, default 1.0)
        pitch_adjust: Pitch adjustment in semitones (-5 to +5, default 0)
        volume: Volume override ("soft", "medium", "loud"), or None to use preset
    
    Returns:
        SSML markup string for Google TTS
    """
    # Get preset configuration
    style_config = SPEAKING_STYLES.get(style_preset, SPEAKING_STYLES["storytelling"])
    google_config = style_config["google_tts"]

    # Calculate final prosody values
    final_rate = _calculate_rate(google_config["rate"], rate_multiplier)
    final_pitch = _calculate_pitch(google_config["pitch"], pitch_adjust)
    final_volume = volume or google_config["volume"]

    # Escape XML special characters in text
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Generate SSML
    ssml = f"""<speak>
  <voice name="{voice_id}">
    <prosody rate="{final_rate}" pitch="{final_pitch}" volume="{final_volume}">
      {text}
    </prosody>
  </voice>
</speak>"""

    return ssml


def get_elevenlabs_settings(style_preset: str = "storytelling",
                            stability_adjust: float = 0.0,
                            style_adjust: float = 0.0) -> Dict[str, Any]:
    """Get ElevenLabs voice settings with user adjustments
    
    Args:
        style_preset: Style preset key from SPEAKING_STYLES
        stability_adjust: Stability adjustment (-0.5 to +0.5, default 0.0)
        style_adjust: Style adjustment (-0.5 to +0.5, default 0.0)
    
    Returns:
        Dictionary of ElevenLabs voice settings
    """
    # Get preset configuration
    style_config = SPEAKING_STYLES.get(style_preset, SPEAKING_STYLES["storytelling"])
    elevenlabs_config = style_config["elevenlabs"]

    # Apply user adjustments and clamp to valid range [0, 1]
    final_stability = max(0.0, min(1.0, elevenlabs_config["stability"] + stability_adjust))
    final_style = max(0.0, min(1.0, elevenlabs_config["style"] + style_adjust))

    return {
        "stability": final_stability,
        "similarity_boost": elevenlabs_config["similarity_boost"],
        "style": final_style,
        "use_speaker_boost": True
    }


def get_style_list() -> list:
    """Get list of style presets for UI display
    
    Returns:
        List of tuples (preset_key, display_name, description)
    """
    return [
        (key, config["name"], config["description"])
        for key, config in SPEAKING_STYLES.items()
    ]


def get_style_info(style_preset: str) -> Dict[str, str]:
    """Get detailed information about a style preset
    
    Args:
        style_preset: Style preset key
    
    Returns:
        Dictionary with name, name_en, and description
    """
    style_config = SPEAKING_STYLES.get(style_preset, SPEAKING_STYLES["storytelling"])
    return {
        "name": style_config["name"],
        "name_en": style_config["name_en"],
        "description": style_config["description"]
    }
