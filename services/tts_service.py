# -*- coding: utf-8 -*-
"""
TTS Service - Text-to-Speech Audio Generation
Supports Google TTS, ElevenLabs, and OpenAI TTS providers
"""
import os, base64, requests
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path
import logging

from services.core.config import load as load_config
from services.core.key_manager import refresh, rotated_list

logger = logging.getLogger(__name__)

def _tokens_of(kinds:Tuple[str,...])->List[str]:
    out=[]; c=load_config(); refresh()
    # New structured lists
    if "elevenlabs" in kinds:
        out += [k for k in (c.get("elevenlabs_api_keys") or []) if k]
    if "openai" in kinds:
        out += [k for k in (c.get("openai_api_keys") or []) if k]
    if "google" in kinds or "gemini" in kinds or "google_tts" in kinds:
        out += [k for k in (c.get("google_api_keys") or []) if k]
        if c.get("google_api_key"): out.append(c.get("google_api_key"))
    # Legacy mixed store
    for t in (c.get("tokens") or []):
        if isinstance(t, dict) and (t.get("kind") in kinds):
            v=t.get("token") or t.get("value") or ""
            if v: out.append(v)
        elif isinstance(t, str) and len(t)>30:
            if "labs" in kinds:
                out.append(t)
    # de-dup preserve order
    seen=set(); arr=[]
    for k in out:
        if k and k not in seen: arr.append(k); seen.add(k)
    # rotate by first matched provider
    provider = "google" if ("google" in kinds or "gemini" in kinds or "google_tts" in kinds) else ("openai" if "openai" in kinds else ("elevenlabs" if "elevenlabs" in kinds else "labs"))
    try:
        arr = rotated_list(provider, arr)
    except Exception:
        pass
    return arr


def synthesize_speech_google(text: str, voice_id: str, language_code: str = "vi-VN",
                             ssml_markup: Optional[str] = None, 
                             speaking_rate: float = 1.0,
                             pitch: float = 0.0,
                             api_key: Optional[str] = None) -> Optional[bytes]:
    """
    Synthesize speech using Google Cloud Text-to-Speech API
    
    Args:
        text: Text to synthesize (plain text)
        voice_id: Google TTS voice ID (e.g., "vi-VN-Wavenet-A")
        language_code: Language code (e.g., "vi-VN", "en-US")
        ssml_markup: Optional SSML markup (if provided, takes precedence over text)
        speaking_rate: Speaking rate (0.25 to 4.0, default 1.0)
        pitch: Pitch adjustment in semitones (-20.0 to 20.0, default 0.0)
        api_key: Optional API key (if not provided, will use from config)
    
    Returns:
        Audio content as bytes (MP3 format), or None if failed
    """
    # Get API key
    if not api_key:
        keys = _tokens_of(("google_tts", "google", "gemini"))
        if not keys:
            logger.error("No Google API key found for TTS")
            return None
        api_key = keys[0]

    # Build request
    url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"

    # Determine input type
    if ssml_markup:
        input_data = {"ssml": ssml_markup}
    else:
        input_data = {"text": text}

    # Build voice config
    voice_config = {
        "languageCode": language_code,
        "name": voice_id
    }

    # Build audio config
    audio_config = {
        "audioEncoding": "MP3",
        "speakingRate": speaking_rate,
        "pitch": pitch
    }

    # Build request body
    request_body = {
        "input": input_data,
        "voice": voice_config,
        "audioConfig": audio_config
    }

    try:
        logger.info(f"Synthesizing speech with Google TTS: voice={voice_id}, lang={language_code}")
        response = requests.post(url, json=request_body, timeout=30)
        response.raise_for_status()

        result = response.json()
        audio_content = result.get("audioContent")

        if audio_content:
            # Decode base64 audio
            audio_bytes = base64.b64decode(audio_content)
            logger.info(f"Successfully synthesized {len(audio_bytes)} bytes of audio")
            return audio_bytes
        else:
            logger.error("No audio content in Google TTS response")
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Google TTS API request failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Google TTS synthesis failed: {e}")
        return None


def synthesize_speech_elevenlabs(text: str, voice_id: str,
                                 stability: float = 0.5,
                                 similarity_boost: float = 0.75,
                                 style: float = 0.5,
                                 api_key: Optional[str] = None) -> Optional[bytes]:
    """
    Synthesize speech using ElevenLabs API
    
    Args:
        text: Text to synthesize
        voice_id: ElevenLabs voice ID
        stability: Voice stability (0.0 to 1.0)
        similarity_boost: Voice similarity boost (0.0 to 1.0)
        style: Style exaggeration (0.0 to 1.0)
        api_key: Optional API key
    
    Returns:
        Audio content as bytes (MP3 format), or None if failed
    """
    # Get API key
    if not api_key:
        keys = _tokens_of(("elevenlabs",))
        if not keys:
            logger.error("No ElevenLabs API key found")
            return None
        api_key = keys[0]

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }

    request_body = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
            "use_speaker_boost": True
        }
    }

    try:
        logger.info(f"Synthesizing speech with ElevenLabs: voice={voice_id}")
        response = requests.post(url, headers=headers, json=request_body, timeout=30)
        response.raise_for_status()

        audio_bytes = response.content
        logger.info(f"Successfully synthesized {len(audio_bytes)} bytes of audio")
        return audio_bytes

    except requests.exceptions.RequestException as e:
        logger.error(f"ElevenLabs API request failed: {e}")
        return None
    except Exception as e:
        logger.error(f"ElevenLabs synthesis failed: {e}")
        return None


def synthesize_speech_openai(text: str, voice: str = "alloy",
                            model: str = "tts-1",
                            speed: float = 1.0,
                            api_key: Optional[str] = None) -> Optional[bytes]:
    """
    Synthesize speech using OpenAI TTS API
    
    Args:
        text: Text to synthesize
        voice: Voice name (alloy, echo, fable, onyx, nova, shimmer)
        model: Model name (tts-1 or tts-1-hd)
        speed: Speaking speed (0.25 to 4.0)
        api_key: Optional API key
    
    Returns:
        Audio content as bytes (MP3 format), or None if failed
    """
    # Get API key
    if not api_key:
        keys = _tokens_of(("openai",))
        if not keys:
            logger.error("No OpenAI API key found")
            return None
        api_key = keys[0]

    url = "https://api.openai.com/v1/audio/speech"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    request_body = {
        "model": model,
        "input": text,
        "voice": voice,
        "speed": speed
    }

    try:
        logger.info(f"Synthesizing speech with OpenAI TTS: voice={voice}, model={model}")
        response = requests.post(url, headers=headers, json=request_body, timeout=30)
        response.raise_for_status()

        audio_bytes = response.content
        logger.info(f"Successfully synthesized {len(audio_bytes)} bytes of audio")
        return audio_bytes

    except requests.exceptions.RequestException as e:
        logger.error(f"OpenAI TTS API request failed: {e}")
        return None
    except Exception as e:
        logger.error(f"OpenAI TTS synthesis failed: {e}")
        return None


def synthesize_speech(voiceover_config: Dict[str, Any], 
                     output_path: Optional[str] = None) -> Optional[bytes]:
    """
    Synthesize speech from voiceover configuration (high-level function)
    
    Args:
        voiceover_config: Voiceover configuration dict with:
            - tts_provider: "google", "elevenlabs", or "openai"
            - voice_id: Voice ID for the provider
            - language: Language code (for Google TTS)
            - text: Text to synthesize
            - ssml_markup: Optional SSML markup (for Google TTS)
            - prosody: Optional prosody settings (rate, pitch, etc.)
            - elevenlabs_settings: Optional ElevenLabs settings
        output_path: Optional path to save audio file
    
    Returns:
        Audio content as bytes, or None if failed
    """
    provider = voiceover_config.get("tts_provider", "google")
    text = voiceover_config.get("text", "")
    voice_id = voiceover_config.get("voice_id", "")

    if not text:
        logger.warning("No text provided for TTS synthesis")
        return None

    if not voice_id:
        logger.warning(f"No voice_id provided for TTS synthesis with provider {provider}")
        return None

    # Synthesize based on provider
    audio_bytes = None

    if provider == "google":
        # Extract Google TTS parameters
        language = voiceover_config.get("language", "vi")
        # Map language code to full language code (vi -> vi-VN, en -> en-US, etc.)
        lang_map = {
            "vi": "vi-VN",
            "en": "en-US",
            "ja": "ja-JP",
            "ko": "ko-KR",
            "zh": "zh-CN"
        }
        language_code = lang_map.get(language, language)

        ssml_markup = voiceover_config.get("ssml_markup")
        prosody = voiceover_config.get("prosody", {})
        speaking_rate = prosody.get("rate", 1.0)
        pitch = prosody.get("pitch", 0)

        audio_bytes = synthesize_speech_google(
            text=text,
            voice_id=voice_id,
            language_code=language_code,
            ssml_markup=ssml_markup,
            speaking_rate=speaking_rate,
            pitch=pitch
        )

    elif provider == "elevenlabs":
        # Extract ElevenLabs parameters
        settings = voiceover_config.get("elevenlabs_settings", {})
        stability = settings.get("stability", 0.5)
        similarity_boost = settings.get("similarity_boost", 0.75)
        style = settings.get("style", 0.5)

        audio_bytes = synthesize_speech_elevenlabs(
            text=text,
            voice_id=voice_id,
            stability=stability,
            similarity_boost=similarity_boost,
            style=style
        )

    elif provider == "openai":
        # Extract OpenAI TTS parameters
        prosody = voiceover_config.get("prosody", {})
        speed = prosody.get("rate", 1.0)

        audio_bytes = synthesize_speech_openai(
            text=text,
            voice=voice_id,
            speed=speed
        )

    else:
        logger.error(f"Unknown TTS provider: {provider}")
        return None

    # Save to file if output path provided
    if audio_bytes and output_path:
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_bytes(audio_bytes)
            logger.info(f"Saved audio to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save audio to {output_path}: {e}")

    return audio_bytes


def generate_audio_from_scene(scene_json: Dict[str, Any], 
                              output_dir: str) -> Optional[str]:
    """
    Generate audio file from scene JSON configuration
    
    Args:
        scene_json: Scene JSON dict with 'audio' -> 'voiceover' configuration
        output_dir: Directory to save audio file
    
    Returns:
        Path to generated audio file, or None if failed
    """
    # Extract voiceover config from scene
    audio_config = scene_json.get("audio", {})
    voiceover_config = audio_config.get("voiceover", {})

    if not voiceover_config:
        logger.warning("No voiceover configuration found in scene JSON")
        return None

    # Generate output filename
    scene_index = scene_json.get("scene_index", 1)
    output_filename = f"scene_{scene_index:02d}_audio.mp3"
    output_path = os.path.join(output_dir, output_filename)

    # Synthesize speech
    audio_bytes = synthesize_speech(voiceover_config, output_path)

    if audio_bytes:
        return output_path
    else:
        return None
