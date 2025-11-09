import base64
import json
import mimetypes
import os
import re
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests

# Optional default_project_id from user config (non-breaking)
try:
    from utils import config as _cfg_mod  # type: ignore
    _cfg = getattr(_cfg_mod, "load", lambda: {})() if hasattr(_cfg_mod, "load") else {}
    _cfg_pid = None
    if isinstance(_cfg, dict):
        _cfg_pid = _cfg.get("default_project_id") or (_cfg.get("labs") or {}).get("default_project_id")
    if _cfg_pid:
        DEFAULT_PROJECT_ID = _cfg_pid  # override safely if present
except Exception:
    pass


# Support both package and flat layouts
try:
    from services.endpoints import BATCH_CHECK_URL, I2V_URL, T2V_URL, UPLOAD_IMAGE_URL
except Exception:  # pragma: no cover
    from endpoints import BATCH_CHECK_URL, I2V_URL, T2V_URL, UPLOAD_IMAGE_URL

DEFAULT_PROJECT_ID = "87b19267-13d6-49cd-a7ed-db19a90c9339"

# Prompt length limits for video generation API
MAX_PROMPT_LENGTH = 5000  # Maximum total prompt length
MAX_PLAIN_STRING_LENGTH = 4000  # Maximum length for plain string prompts
MAX_CHARACTER_DETAILS_LENGTH = 1500  # Maximum length for character details when truncating
MAX_SCENE_DESCRIPTION_LENGTH = 3000  # Maximum length for scene description when truncating

def _headers(bearer: str) -> dict:
    return {
        "authorization": f"Bearer {bearer}",
        "content-type": "application/json; charset=utf-8",
        "origin": "https://labs.google",
        "referer": "https://labs.google/",
        "user-agent": "Mozilla/5.0"
    }

def _encode_image_file(path: str):
    with open(path, "rb") as f:
        raw = f.read()
    b64 = base64.b64encode(raw).decode("utf-8")
    mime = mimetypes.guess_type(path)[0] or "image/jpeg"
    return b64, mime

_URL_PAT = re.compile(r'^(https?://|gs://)', re.I)
def _collect_urls_any(obj: Any) -> List[str]:
    urls=set(); KEYS={"gcsUrl","gcsUri","signedUrl","signedUri","downloadUrl","downloadUri","videoUrl","url","uri","fileUri"}
    def visit(x):
        if isinstance(x, dict):
            for k,v in x.items():
                if k in KEYS and isinstance(v,str) and _URL_PAT.match(v): urls.add(v)
                else: visit(v)
        elif isinstance(x, list):
            for it in x: visit(it)
        elif isinstance(x, str):
            if _URL_PAT.match(x): urls.add(x)
    visit(obj)
    lst=list(urls); lst.sort(key=lambda u: (0 if "/video/" in u else 1, len(u)))
    return lst

def _convert_aspect_ratio_to_vertex(aspect_ratio: str) -> str:
    """Convert Google Labs aspect ratio format to Vertex AI format."""
    mapping = {
        "VIDEO_ASPECT_RATIO_LANDSCAPE": "16:9",
        "VIDEO_ASPECT_RATIO_PORTRAIT": "9:16",
        "VIDEO_ASPECT_RATIO_SQUARE": "1:1"
    }
    return mapping.get(aspect_ratio, "16:9")

def _convert_model_key_to_vertex(model_key: str) -> str:
    """Convert Google Labs model key to Vertex AI model format."""
    # Extract base model name from keys like "veo_3_1_t2v_fast_ultra"
    if "veo_3_1" in model_key or "veo_3.1" in model_key:
        return "veo-3.1"
    elif "veo_2" in model_key or "veo_2.0" in model_key:
        return "veo-2.0"
    # Default to veo-3.1
    return "veo-3.1"

def _normalize_status(item: dict) -> str:
    if item.get("done") is True:
        if item.get("error"): return "FAILED"
        return "DONE"
    s=item.get("status") or ""
    if s in ("MEDIA_GENERATION_STATUS_SUCCEEDED","SUCCEEDED","SUCCESS"): return "DONE"
    if s in ("MEDIA_GENERATION_STATUS_FAILED","FAILED","ERROR"): return "FAILED"
    return "PROCESSING"

def _extract_negative_prompt(prompt_data: Any) -> str:
    """Extract negative prompt from prompt data structure."""
    if isinstance(prompt_data, dict):
        negatives = prompt_data.get("negatives", [])
        if isinstance(negatives, list) and negatives:
            return ", ".join(str(neg) for neg in negatives)
    return "text, words, letters, subtitles, captions, titles, credits, on-screen text, watermarks, logos, brands, camera shake, fisheye, photorealistic, live action, 3D CGI, Disney 3D, Pixar style"

def _build_complete_prompt_text(prompt_data: Any) -> str:
    """
    Build a COMPLETE text prompt from JSON structure.
    
    CRITICAL: Order matters! API reads top→bottom, so most important
    requirements MUST be at the top.
    """
    # If already a string, return as-is (backward compatibility)
    if isinstance(prompt_data, str):
        return prompt_data

    # If not dict, convert to string
    if not isinstance(prompt_data, dict):
        return str(prompt_data)

    sections = []

    # ═══════════════════════════════════════════════════════════════
    # SECTION 0A: CHARACTER IDENTITY LOCK (CoT + RCoT - ABSOLUTE TOP!)
    # Issue #41: Extremely detailed character descriptions MUST be first
    # for maximum consistency across all scenes in multi-scene videos
    # ═══════════════════════════════════════════════════════════════
    character_details = prompt_data.get("character_details", "")
    if character_details and "CRITICAL" in character_details:
        # Extract character names and details for identity lock
        identity_lock = (
            "╔═══════════════════════════════════════════════════════════╗\n"
            "║  CHARACTER IDENTITY LOCK (CoT + RCoT TECHNIQUE)          ║\n"
            "║  THIS SECTION MUST NEVER BE IGNORED OR MODIFIED          ║\n"
            "╚═══════════════════════════════════════════════════════════╝\n\n"
            f"{character_details}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "NEVER CHANGE DIRECTIVES (10 CRITICAL RULES):\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "1. NEVER change character facial features (eyes, nose, mouth, face shape)\n"
            "2. NEVER change character hairstyle, hair color, or hair length\n"
            "3. NEVER change character outfit, clothing colors, or accessories\n"
            "4. NEVER change character body type, height, or build\n"
            "5. NEVER change character skin tone or complexion\n"
            "6. NEVER add or remove character accessories (jewelry, glasses, etc.)\n"
            "7. NEVER change character age or apparent age\n"
            "8. NEVER swap characters with different people\n"
            "9. NEVER modify character proportions or physical characteristics\n"
            "10. NEVER introduce new characters not listed above\n\n"
            "CONSISTENCY ENFORCEMENT:\n"
            "✓ Use EXACT SAME character appearance in ALL scenes\n"
            "✓ Maintain IDENTICAL visual identity across entire video\n"
            "✓ Keep ALL physical features UNCHANGED throughout\n"
            "✓ Preserve character design from scene 1 to final scene\n"
            "╔═══════════════════════════════════════════════════════════╗\n"
            "║  END OF CHARACTER IDENTITY LOCK                          ║\n"
            "╚═══════════════════════════════════════════════════════════╝"
        )
        sections.append(identity_lock)

    # ═══════════════════════════════════════════════════════════════
    # SECTION 0B: VOICEOVER LANGUAGE (TOP PRIORITY - ENHANCED)
    # Issue #2: Strengthen voiceover/dialogue instructions
    # ═══════════════════════════════════════════════════════════════
    audio = prompt_data.get("audio", {})
    if isinstance(audio, dict):
        voiceover = audio.get("voiceover", {})
        if isinstance(voiceover, dict):
            vo_lang = voiceover.get("language", "")
            vo_text = voiceover.get("text", "")
            tts_provider = voiceover.get("tts_provider", "")
            voice_id = voiceover.get("voice_id", "")
            voice_name = voiceover.get("voice_name", "")
            speaking_style = voiceover.get("speaking_style", "")

            if vo_lang and vo_text:
                # Map language codes to full names
                lang_name_map = {
                    'vi': 'Vietnamese', 'en': 'English', 'ja': 'Japanese',
                    'ko': 'Korean', 'zh': 'Chinese', 'fr': 'French',
                    'de': 'German', 'es': 'Spanish', 'ru': 'Russian',
                    'th': 'Thai', 'id': 'Indonesian'
                }
                lang_name = lang_name_map.get(vo_lang, vo_lang.upper())

                # CRITICAL: Enhanced voice directive with stronger instructions
                voice_directive = (
                    f"╔═══════════════════════════════════════════════════════════╗\n"
                    f"║  CRITICAL AUDIO REQUIREMENT (ABSOLUTE TOP PRIORITY)      ║\n"
                    f"║  THIS SECTION MUST NEVER BE IGNORED OR SKIPPED           ║\n"
                    f"╚═══════════════════════════════════════════════════════════╝\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"VOICE & DIALOGUE REQUIREMENTS (10 CRITICAL RULES):\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"1. ALL spoken dialogue MUST be in {lang_name} ({vo_lang})\n"
                    f"2. ALL voiceover narration MUST be in {lang_name} ({vo_lang})\n"
                    f"3. NEVER use any language other than {lang_name} for voice\n"
                    f"4. Text-to-speech engine MUST use {lang_name} ({vo_lang}) model\n"
                    f"5. Character dialogue MUST be audible and clear\n"
                    f"6. Voiceover MUST be synchronized with video timing\n"
                    f"7. Audio levels MUST be balanced and professional\n"
                    f"8. Background music MUST NOT overpower the voice\n"
                    f"9. Voice tone and emotion MUST match the scene content\n"
                    f"10. INCLUDE voiceover audio - do NOT create silent video\n\n"
                    f"VOICE CONFIGURATION:\n"
                    f"- Language: {lang_name} ({vo_lang})\n"
                )
                
                if tts_provider:
                    voice_directive += f"- TTS Provider: {tts_provider}\n"
                if voice_id:
                    voice_directive += f"- Voice ID: {voice_id}\n"
                if voice_name:
                    voice_directive += f"- Voice Name: {voice_name}\n"
                if speaking_style:
                    voice_directive += f"- Speaking Style: {speaking_style}\n"
                
                voice_directive += (
                    f"\n📢 VOICEOVER TEXT (MUST BE SPOKEN IN {lang_name}):\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"\"{vo_text}\"\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"⚠️  AUDIO ENFORCEMENT:\n"
                    f"✓ Generate voiceover audio with the EXACT text above\n"
                    f"✓ Use {lang_name} ({vo_lang}) TTS engine ONLY\n"
                    f"✓ Ensure voice is clear, natural, and emotionally appropriate\n"
                    f"✓ Match voice prosody (rate, pitch, emotion) to scene context\n"
                    f"✓ DO NOT create a silent video - audio is MANDATORY\n"
                    f"✓ DO NOT use English or any other language for voiceover\n\n"
                    f"╔═══════════════════════════════════════════════════════════╗\n"
                    f"║  END OF CRITICAL AUDIO REQUIREMENT                       ║\n"
                    f"╚═══════════════════════════════════════════════════════════╝"
                )
                sections.append(voice_directive)

    # ═══════════════════════════════════════════════════════════════
    # SECTION 1: VISUAL STYLE LOCK (PR #8 - Enhanced style consistency)
    # ═══════════════════════════════════════════════════════════════
    constraints = prompt_data.get("constraints", {})
    visual_style_tags = constraints.get("visual_style_tags", [])
    
    # Extract style_seed from generation params (PR #8)
    generation_params = prompt_data.get("generation", {})
    style_seed = generation_params.get("style_seed")

    if visual_style_tags:
        style_text = ", ".join(visual_style_tags)
        style_lower = style_text.lower()
        
        # Determine main style from tags
        main_style = "2D Hand-Drawn Anime"  # Default
        is_anime_style = False
        is_realistic_style = False
        is_genre_style = False
        genre_style_type = None
        
        # Check genre-specific styles first (more specific patterns)
        if "sci-fi" in style_lower or "futuristic" in style_lower or "cyberpunk" in style_lower:
            main_style = "Sci-Fi / Futuristic"
            is_genre_style = True
            genre_style_type = "sci_fi"
        elif "horror" in style_lower or ("dark" in style_lower and "eerie" in style_lower):
            main_style = "Horror / Dark Thriller"
            is_genre_style = True
            genre_style_type = "horror"
        elif "fantasy" in style_lower or "magical" in style_lower or "mystical" in style_lower:
            main_style = "Fantasy / Magical"
            is_genre_style = True
            genre_style_type = "fantasy"
        elif "action" in style_lower or ("dynamic" in style_lower and "fast-paced" in style_lower):
            main_style = "Action / High Energy"
            is_genre_style = True
            genre_style_type = "action"
        elif "romance" in style_lower or ("dreamy" in style_lower and "soft lighting" in style_lower):
            main_style = "Romance / Soft Aesthetic"
            is_genre_style = True
            genre_style_type = "romance"
        elif "comedy" in style_lower or ("playful" in style_lower and "bright" in style_lower):
            main_style = "Comedy / Playful"
            is_genre_style = True
            genre_style_type = "comedy"
        elif "documentary" in style_lower or "educational" in style_lower:
            main_style = "Documentary / Educational"
            is_genre_style = True
            genre_style_type = "documentary"
        elif "film noir" in style_lower or ("black and white" in style_lower and "vintage" in style_lower):
            main_style = "Film Noir / Vintage"
            is_genre_style = True
            genre_style_type = "film_noir"
        # Then check anime styles
        elif "anime" in style_lower or "flat colors" in style_lower or "outlined" in style_lower or "2d animation" in style_lower or "cel-shading" in style_lower:
            main_style = "2D Hand-Drawn Anime Animation"
            is_anime_style = True
        # Finally check realistic styles (most generic)
        elif "realistic" in style_lower or "photorealistic" in style_lower:
            main_style = "Photorealistic Live Action"
            is_realistic_style = True
        elif "cinematic" in style_lower and "anime" not in style_lower:
            main_style = "Cinematic Film Style"
            is_realistic_style = True

        # Build VISUAL STYLE LOCK section (similar to CHARACTER IDENTITY LOCK)
        # Issue #1: Enhanced with stronger anime/visual style enforcement
        style_lock = (
            "╔═══════════════════════════════════════════════════════════╗\n"
            "║  VISUAL STYLE LOCK (ABSOLUTE CRITICAL PRIORITY)          ║\n"
            "║  THIS SECTION MUST NEVER BE IGNORED OR MODIFIED          ║\n"
            "╚═══════════════════════════════════════════════════════════╝\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"REQUIRED VISUAL STYLE: {main_style}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "VISUAL STYLE REQUIREMENTS (12 CRITICAL RULES):\n"
        )
        
        # Add style-specific requirements with enhanced enforcement
        if is_anime_style:
            style_lock += (
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "ANIME STYLE REQUIREMENTS:\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "1. MUST use 2D hand-drawn anime animation aesthetic (Japanese anime style)\n"
                "2. MUST use flat colors with cel-shading technique (NO gradient shading)\n"
                "3. MUST have bold black outlines around characters and objects (3-5px width)\n"
                "4. MUST look like traditional Japanese TV anime (similar to Studio Ghibli, Demon Slayer, My Hero Academia)\n"
                "5. MUST use simplified, painted-look backgrounds (NOT photographic)\n"
                "6. MUST have expressive character designs with large, detailed eyes\n"
                "7. MUST use vibrant, saturated anime color palette\n"
                "8. MUST use cartoon/illustrated rendering (NO photorealistic elements)\n"
                "9. MUST maintain consistent 2D aesthetic throughout entire video\n"
                "10. Characters MUST be drawn/illustrated, NOT photographed or 3D modeled\n"
                "11. Animation MUST use anime techniques (limited animation, keyframes, motion lines)\n"
                "12. Overall look MUST be unmistakably anime - if it looks realistic, it's WRONG\n\n"
                "✅ REQUIRED ANIME CHARACTERISTICS:\n"
                "✓ 2D hand-drawn animation aesthetic (Japanese anime style)\n"
                "✓ Flat colors with cel-shading technique\n"
                "✓ Bold black outlines (3-5px width) around ALL characters and objects\n"
                "✓ Cartoon/illustrated look, completely non-photographic\n"
                "✓ Traditional anime art style (Japanese TV animation aesthetic)\n"
                "✓ Simplified backgrounds with painted/illustrated look\n"
                "✓ Expressive character designs with large, detailed eyes\n"
                "✓ Anime-specific visual effects (motion lines, impact frames, speed lines)\n"
                "✓ Vibrant, saturated anime color palette\n"
                "✓ Limited animation techniques (holds, keyframes, smears)\n\n"
                "❌ ABSOLUTELY FORBIDDEN (WILL CAUSE FAILURE):\n"
                "✗ Realistic photography or photorealistic rendering of ANY kind\n"
                "✗ 3D computer animation (CGI) or 3D modeling\n"
                "✗ Semi-realistic, hybrid, or mixed styles\n"
                "✗ Rotoscoping or live-action traced footage\n"
                "✗ Western cartoon styles (Disney 3D, Pixar, DreamWorks)\n"
                "✗ Mixed 2D/3D elements or hybrid rendering\n"
                "✗ Photographic lighting, textures, or materials\n"
                "✗ Realistic skin textures, hair rendering, or fabric simulation\n"
                "✗ Ray-traced lighting or realistic shadows\n"
                "✗ Motion capture or realistic human movement\n"
                "✗ Live-action footage or real-world photography\n\n"
                "🎨 ANIME STYLE ENFORCEMENT:\n"
                "⚠️  If the output looks realistic, photographic, or 3D → REJECT IT\n"
                "⚠️  If there are NO bold outlines → NOT anime style\n"
                "⚠️  If colors are gradient-shaded instead of flat → NOT anime style\n"
                "⚠️  If it looks like a real photo or live-action → COMPLETELY WRONG\n"
                "⚠️  The style MUST be unmistakably Japanese 2D anime\n"
            )
        elif is_realistic_style:
            style_lock += (
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "REALISTIC/CINEMATIC STYLE REQUIREMENTS:\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "1. MUST use photorealistic rendering with natural textures\n"
                "2. MUST have realistic lighting and shadows (NO flat cel-shading)\n"
                "3. MUST follow real-world physics and proportions\n"
                "4. MUST use detailed, photographic textures and materials\n"
                "5. MUST look like live-action film or photography\n"
                "6. MUST use natural camera work and cinematography\n"
                "7. MUST have realistic human features and proportions\n"
                "8. MUST use gradient shading and realistic color grading\n"
                "9. NO cartoon or illustrated elements\n"
                "10. NO bold outlines or anime aesthetics\n"
                "11. NO flat colors or cel-shading\n"
                "12. Overall look MUST be photographic/cinematic - if it looks like anime, it's WRONG\n\n"
                "✅ REQUIRED REALISTIC CHARACTERISTICS:\n"
                "✓ Photorealistic rendering with natural textures\n"
                "✓ Realistic lighting and shadows (ray-traced quality)\n"
                "✓ Real-world physics and proportions\n"
                "✓ Detailed photographic textures and materials\n"
                "✓ Natural camera work and professional cinematography\n"
                "✓ Realistic human features, skin textures, hair\n"
                "✓ Gradient shading and realistic color grading\n"
                "✓ Cinematic depth of field and bokeh effects\n\n"
                "❌ ABSOLUTELY FORBIDDEN (WILL CAUSE FAILURE):\n"
                "✗ Anime or cartoon aesthetics of ANY kind\n"
                "✗ 2D hand-drawn animation look\n"
                "✗ Flat colors or cel-shading technique\n"
                "✗ Bold outlines around characters or objects\n"
                "✗ Stylized or illustrated rendering\n"
                "✗ Cartoon character designs or exaggerated features\n"
                "✗ Anime-style large eyes or simplified faces\n"
                "✗ Painted or illustrated backgrounds\n\n"
            )
        elif is_genre_style:
            # Add genre-specific style requirements
            style_lock += (
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"{main_style.upper()} STYLE REQUIREMENTS:\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            )
            
            if genre_style_type == "sci_fi":
                style_lock += (
                    "1. MUST have futuristic, sci-fi aesthetic throughout\n"
                    "2. MUST use neon lighting, holographic effects, or tech elements\n"
                    "3. MUST include futuristic technology, cyberpunk, or sci-fi elements\n"
                    "4. MUST maintain consistent futuristic visual language\n"
                    "5. Color palette: neon blues, purples, cyans, or high-tech colors\n"
                    "6. Environment: futuristic cityscapes, space, or tech settings\n"
                    "7. NO medieval, ancient, or rustic aesthetics\n"
                    "8. NO natural or traditional elements unless integrated with tech\n\n"
                )
            elif genre_style_type == "horror":
                style_lock += (
                    "1. MUST have dark, eerie, suspenseful atmosphere throughout\n"
                    "2. MUST use gothic, ominous, or horror visual elements\n"
                    "3. MUST maintain consistent horror aesthetic and mood\n"
                    "4. Lighting: dark, shadowy, dramatic contrasts\n"
                    "5. Color palette: desaturated, dark tones, ominous colors\n"
                    "6. Mood: tense, eerie, unsettling, suspenseful\n"
                    "7. NO bright, cheerful, or colorful elements\n"
                    "8. NO happy, comedy, or upbeat aesthetics\n\n"
                )
            elif genre_style_type == "fantasy":
                style_lock += (
                    "1. MUST have magical, enchanted, mystical aesthetic\n"
                    "2. MUST use fantasy elements: magic, mythical creatures, enchantments\n"
                    "3. MUST maintain consistent fantasy visual language\n"
                    "4. Color palette: vibrant, ethereal, magical colors\n"
                    "5. Environment: enchanted forests, magical realms, fantasy settings\n"
                    "6. Atmosphere: mystical, otherworldly, fantastical\n"
                    "7. NO realistic modern settings or technology\n"
                    "8. NO scientific or technological aesthetics\n\n"
                )
            elif genre_style_type == "action":
                style_lock += (
                    "1. MUST have dynamic, high-energy aesthetic throughout\n"
                    "2. MUST convey intense, fast-paced, explosive action\n"
                    "3. MUST maintain consistent action-oriented visual language\n"
                    "4. Motion: dynamic camera work, fast movements\n"
                    "5. Energy: intense, high-impact, explosive visuals\n"
                    "6. Composition: dynamic angles, motion blur, impact frames\n"
                    "7. NO slow, static, or calm aesthetics\n"
                    "8. NO peaceful or tranquil settings\n\n"
                )
            elif genre_style_type == "romance":
                style_lock += (
                    "1. MUST have soft, dreamy, romantic aesthetic throughout\n"
                    "2. MUST use soft lighting, warm colors, gentle atmosphere\n"
                    "3. MUST maintain consistent romantic visual language\n"
                    "4. Lighting: soft, warm, golden hour, dreamy\n"
                    "5. Color palette: warm tones, pastels, soft colors\n"
                    "6. Mood: gentle, intimate, dreamy, romantic\n"
                    "7. NO harsh lighting or dark atmospheres\n"
                    "8. NO violent, aggressive, or intense aesthetics\n\n"
                )
            elif genre_style_type == "comedy":
                style_lock += (
                    "1. MUST have bright, playful, fun aesthetic throughout\n"
                    "2. MUST use vibrant colors, exaggerated expressions, playful elements\n"
                    "3. MUST maintain consistent comedy/playful visual language\n"
                    "4. Lighting: bright, cheerful, well-lit\n"
                    "5. Color palette: vibrant, saturated, fun colors\n"
                    "6. Mood: playful, fun, lighthearted, energetic\n"
                    "7. NO dark, serious, or dramatic atmospheres\n"
                    "8. NO horror or intense emotional aesthetics\n\n"
                )
            elif genre_style_type == "documentary":
                style_lock += (
                    "1. MUST have realistic, clear, informative aesthetic\n"
                    "2. MUST use natural lighting, educational presentation\n"
                    "3. MUST maintain consistent documentary visual language\n"
                    "4. Style: realistic, clear, professional, educational\n"
                    "5. Lighting: natural, even, well-balanced\n"
                    "6. Presentation: informative, clear, documentary-style\n"
                    "7. NO stylized, artistic, or abstract elements\n"
                    "8. NO fantasy or overly creative aesthetics\n\n"
                )
            elif genre_style_type == "film_noir":
                style_lock += (
                    "1. MUST have black and white or desaturated aesthetic\n"
                    "2. MUST use dramatic shadows, high contrast, vintage 1940s look\n"
                    "3. MUST maintain consistent film noir visual language\n"
                    "4. Lighting: dramatic shadows, chiaroscuro, high contrast\n"
                    "5. Color: black and white or heavily desaturated\n"
                    "6. Atmosphere: vintage, 1940s aesthetic, noir mood\n"
                    "7. NO colorful, bright, or modern aesthetics\n"
                    "8. NO futuristic or contemporary styles\n\n"
                )
            
            # Add genre-specific tags from visual_style_tags
            style_lock += (
                f"✅ REQUIRED CHARACTERISTICS FOR {main_style.upper()}:\n"
            )
            for tag in visual_style_tags:
                style_lock += f"✓ {tag}\n"
            style_lock += "\n"
        
        style_lock += (
            "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "STYLE CONSISTENCY ENFORCEMENT (CRITICAL):\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "1. Use EXACTLY the same visual style in EVERY SINGLE scene\n"
            "2. NEVER mix realistic and anime styles - choose ONE and stick to it\n"
            "3. NEVER change rendering technique between scenes\n"
            "4. NEVER switch between 2D and 3D mid-video\n"
            "5. Maintain IDENTICAL art direction from start to finish\n"
            "6. All scenes MUST look like they're from the SAME production\n"
            "7. Visual style MUST remain consistent across entire video\n"
            "8. NO style variations, NO style drift, NO mixed approaches\n"
            "9. First scene sets the style - ALL other scenes MUST match it\n"
            "10. ANY style inconsistency is a CRITICAL FAILURE\n\n"
        )
        
        # Add style seed if available
        if style_seed:
            style_lock += (
                f"🎲 STYLE SEED FOR CONSISTENCY:\n"
                f"Use style seed: {style_seed}\n"
                f"This seed ensures visual style consistency across all scenes.\n"
                f"DO NOT vary the visual style - the seed locks it in place.\n\n"
            )
        
        style_lock += (
            "⚠️  CRITICAL WARNINGS:\n"
            "• Any deviation from the specified style is UNACCEPTABLE\n"
            "• Style mixing or drift will result in REJECTED output\n"
            "• Visual style is as important as content - enforce it strictly\n"
            "• When in doubt, err on the side of STRONGER style enforcement\n\n"
            "╔═══════════════════════════════════════════════════════════╗\n"
            "║  END OF VISUAL STYLE LOCK                                ║\n"
            "╚═══════════════════════════════════════════════════════════╝"
        )
        sections.append(style_lock)

    # ═══════════════════════════════════════════════════════════════
    # SECTION 2: CHARACTER CONSISTENCY
    # Note: Main character details now in IDENTITY LOCK at top (Issue #41)
    # This section kept for backward compatibility with non-critical characters
    # ═══════════════════════════════════════════════════════════════
    # Skip if already added to IDENTITY LOCK section
    character_details_backup = prompt_data.get("character_details", "")
    if character_details_backup and "CRITICAL" not in character_details_backup:
        sections.append(f"CHARACTER CONSISTENCY:\n{character_details_backup}")

    # ═══════════════════════════════════════════════════════════════
    # SECTION 3: HARD LOCKS (existing, unchanged)
    # ═══════════════════════════════════════════════════════════════
    hard_locks = prompt_data.get("hard_locks", {})
    if hard_locks:
        locks = []
        for key, value in hard_locks.items():
            if value:
                locks.append(f"- {key.replace('_', ' ').title()}: {value}")
        if locks:
            sections.append("CONSISTENCY REQUIREMENTS:\n" + "\n".join(locks))

    # ═══════════════════════════════════════════════════════════════
    # SECTION 4: SETTING DETAILS (existing, unchanged)
    # ═══════════════════════════════════════════════════════════════
    setting_details = prompt_data.get("setting_details", "")
    if setting_details:
        sections.append(f"SETTING: {setting_details}")

    # ═══════════════════════════════════════════════════════════════
    # SECTION 5: SCENE ACTION (with character & style reminders)
    # Triple Reinforcement #2: Prepend character and style reminders
    # ═══════════════════════════════════════════════════════════════
    key_action = prompt_data.get("key_action", "")

    # Check localization
    if not key_action:
        localization = prompt_data.get("localization", {})
        if isinstance(localization, dict):
            for lang in ["vi", "en"]:
                if lang in localization:
                    lang_data = localization[lang]
                    if isinstance(lang_data, dict) and "prompt" in lang_data:
                        key_action = str(lang_data["prompt"])
                        break

    if key_action:
        # Add style reminder before scene action (Triple Reinforcement #2 - PR #8)
        style_reminder = ""
        if visual_style_tags:
            style_text_lower = ", ".join(visual_style_tags).lower()
            if "anime" in style_text_lower or "flat colors" in style_text_lower or "outlined" in style_text_lower:
                style_reminder = "[2D anime style with bold outlines and flat colors] "
            elif "realistic" in style_text_lower or "cinematic" in style_text_lower:
                style_reminder = "[Photorealistic live-action style] "
        
        # Add character reminder before scene action (Triple Reinforcement #2)
        character_reminder = ""
        if character_details:
            # Extract just character names for brief reminder
            char_reminder_parts = []
            if "—" in character_details:
                # Parse format like "Prince (main character) — Visual: ..."
                for line in character_details.split(";"):
                    if "—" in line:
                        name_part = line.split("—")[0].strip()
                        char_reminder_parts.append(name_part)
            
            if char_reminder_parts:
                character_reminder = (
                    "⚠️  CHARACTER REMINDER: " + "; ".join(char_reminder_parts) + 
                    " — Keep EXACT same appearance as defined in CHARACTER IDENTITY LOCK above.\n\n"
                )
        
        sections.append(f"SCENE ACTION:\n{style_reminder}{character_reminder}{key_action}")

    # ═══════════════════════════════════════════════════════════════
    # SECTION 6: CAMERA DIRECTION (existing, unchanged)
    # ═══════════════════════════════════════════════════════════════
    camera_dir = prompt_data.get("camera_direction", [])
    if isinstance(camera_dir, list) and camera_dir:
        cam_text = []
        for cam in camera_dir:
            if isinstance(cam, dict):
                time = cam.get("t", "")
                shot = cam.get("shot", "")
                if time and shot:
                    cam_text.append(f"[{time}] {shot}")
        if cam_text:
            sections.append("CAMERA:\n" + "\n".join(cam_text))

    # NOTE: Task_Instructions section REMOVED
    # Its content (voice + style) is now at top as critical sections

    # ═══════════════════════════════════════════════════════════════
    # SECTION 7: NEGATIVES (Enhanced with character & style consistency)
    # Triple Reinforcement #3: Add character and style consistency negatives
    # ═══════════════════════════════════════════════════════════════
    negatives = prompt_data.get("negatives", [])
    
    # Add character consistency negatives if characters are defined (Triple Reinforcement #3)
    if character_details:
        character_negatives = [
            "NEVER change character facial features across scenes",
            "NEVER change character hairstyle or hair color",
            "NEVER change character outfit or clothing",
            "NEVER introduce different-looking versions of same character",
            "NEVER swap character identities or appearances"
        ]
        # Prepend to existing negatives for higher priority
        negatives = character_negatives + list(negatives)
    
    # Add style-specific negatives (PR #8 - Triple Reinforcement #3)
    if visual_style_tags:
        style_text_lower = ", ".join(visual_style_tags).lower()
        style_negatives = []
        
        if "anime" in style_text_lower or "flat colors" in style_text_lower or "outlined" in style_text_lower:
            style_negatives = [
                "photorealistic rendering",
                "realistic photography",
                "3D CGI animation",
                "semi-realistic style",
                "live-action footage",
                "rotoscoping",
                "mixed 2D/3D",
                "Disney 3D style",
                "Pixar animation",
                "realistic lighting and textures",
                "photographic quality"
            ]
        elif "realistic" in style_text_lower or "cinematic" in style_text_lower:
            style_negatives = [
                "anime style",
                "2D animation",
                "cartoon aesthetic",
                "cel-shading",
                "bold outlines",
                "flat colors",
                "illustrated look",
                "stylized rendering"
            ]
        
        # Prepend style negatives for high priority
        negatives = style_negatives + list(negatives)
    
    if negatives:
        neg_text = "\n".join(f"- {neg}" for neg in negatives)
        sections.append(f"AVOID:\n{neg_text}")

    # Combine all sections with clear separators
    complete_prompt = "\n\n".join(sections)

    return complete_prompt

def _save_prompt_to_disk(prompt_data: Any, project_dir: Optional[str] = None, 
                        scene_num: Optional[int] = None, model_key: str = "",
                        aspect_ratio: str = "") -> Optional[str]:
    """
    Save prompt to disk for Issue #1 - Auto-save prompts to project folder.
    
    Args:
        prompt_data: The original prompt data (dict or str)
        project_dir: Project download directory (if None, uses default from config)
        scene_num: Scene number (optional, for naming)
        model_key: Model used for generation
        aspect_ratio: Aspect ratio used
    
    Returns:
        Path to saved prompt file, or None if save failed
    """
    try:
        # Determine project directory
        if not project_dir:
            # Try to get from config
            try:
                from utils import config as _cfg_mod
                _cfg = _cfg_mod.load() if hasattr(_cfg_mod, "load") else {}
                project_dir = _cfg.get("download_root", "")
            except Exception:
                pass
        
        if not project_dir:
            # Fallback to current directory
            project_dir = os.getcwd()
        
        # Create prompts folder
        prompts_dir = os.path.join(project_dir, "prompts")
        os.makedirs(prompts_dir, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        scene_part = f"scene_{scene_num}_" if scene_num is not None else ""
        filename = f"{scene_part}{timestamp}.json"
        filepath = os.path.join(prompts_dir, filename)
        
        # Build complete prompt text for saving
        complete_prompt = _build_complete_prompt_text(prompt_data)
        
        # Prepare metadata
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "scene_num": scene_num,
            "model_key": model_key,
            "aspect_ratio": aspect_ratio,
            "original_prompt_data": prompt_data if isinstance(prompt_data, dict) else {"text": str(prompt_data)},
            "complete_prompt_text": complete_prompt
        }
        
        # Save JSON metadata file
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        # Also save plain text version of the exact prompt sent to Google Labs Flow
        # This is what the user requested - a separate file with just the prompt text
        txt_filename = f"{scene_part}{timestamp}.txt"
        txt_filepath = os.path.join(prompts_dir, txt_filename)
        with open(txt_filepath, "w", encoding="utf-8") as f:
            f.write(complete_prompt)
        
        return filepath
        
    except Exception as e:
        # Silent failure - don't break video generation if prompt save fails
        print(f"[WARN] Failed to save prompt to disk: {e}")
        return None

class LabsClient:
    MAX_RETRY_ATTEMPTS = 9  # Maximum total retry attempts across all tokens
    RETRY_SLEEP_MULTIPLIER = 0.7  # Multiplier for exponential backoff sleep time

    def __init__(self, bearers: List[str], timeout: Tuple[int,int]=(20,180), on_event: Optional[Callable[[dict], None]]=None):
        self.tokens=[t.strip() for t in (bearers or []) if t.strip()]
        if not self.tokens: raise ValueError("No Labs tokens provided")
        self._idx=0; self.timeout=timeout; self.on_event=on_event
        self._invalid_tokens=set()  # Track tokens that returned 401

    def _tok(self)->str:
        t=self.tokens[self._idx % len(self.tokens)]; self._idx+=1; return t

    def _emit(self, kind: str, **kw):
        if self.on_event:
            try: self.on_event({"kind":kind, **kw})
            except Exception: pass

    def _post(self, url: str, payload: dict) -> dict:
        last=None
        # Calculate available tokens and max attempts
        # Note: We don't directly iterate over tokens_to_try, instead we use round-robin
        # via self._tok() and skip invalid ones. tokens_to_try is used to:
        # 1. Determine max_attempts based on valid tokens
        # 2. Check if all tokens are already invalid (fail fast)
        tokens_to_try = [t for t in self.tokens if t not in self._invalid_tokens]
        if not tokens_to_try:
            # All tokens are invalid - fail immediately with clear error message
            error_msg = (
                f"All {len(self.tokens)} authentication token(s) are invalid or expired. "
                "Please update your Google Labs OAuth tokens in the API Credentials settings. "
                "To get new tokens, visit https://labs.google and inspect network requests."
            )
            self._emit("http_other_err", code=401, detail=error_msg)
            raise requests.HTTPError(error_msg)

        max_attempts = min(3 * len(tokens_to_try), self.MAX_RETRY_ATTEMPTS)
        attempts_made = 0
        skip_count = 0  # Prevent infinite loop when all tokens are invalid
        max_skips = len(self.tokens) * 2  # Allow skipping all tokens twice

        while attempts_made < max_attempts and skip_count < max_skips:
            current_token = None
            try:
                # Get next token using round-robin rotation
                current_token = self._tok()
                # Skip if this token is marked invalid (don't count as an attempt)
                if current_token in self._invalid_tokens:
                    skip_count += 1
                    continue

                attempts_made += 1
                skip_count = 0  # Reset skip count when we make an actual attempt

                r=requests.post(url, headers=_headers(current_token), json=payload, timeout=self.timeout)
                if r.status_code==200:
                    self._emit("http_ok", code=200)
                    try: return r.json()
                    except Exception: return {}

                # Handle 401 Unauthorized - mark token as invalid and skip to next immediately
                if r.status_code == 401:
                    self._invalid_tokens.add(current_token)
                    token_id = f"Token #{self.tokens.index(current_token) + 1}" if current_token in self.tokens else "Unknown token"
                    error_msg = f"{token_id} is invalid (401 Unauthorized)"
                    self._emit("http_other_err", code=401, detail=error_msg)
                    
                    # Check if all tokens are now invalid - fail fast
                    if len(self._invalid_tokens) >= len(self.tokens):
                        all_invalid_msg = (
                            f"All {len(self.tokens)} authentication token(s) are invalid or expired. "
                            "Please update your Google Labs OAuth tokens in the API Credentials settings. "
                            "To get new tokens, visit https://labs.google and inspect network requests."
                        )
                        # Don't emit again - we'll let the exception propagate
                        # self._emit("http_other_err", code=401, detail=all_invalid_msg)
                        raise requests.HTTPError(all_invalid_msg)
                    
                    # Don't sleep, immediately try next token
                    last = requests.HTTPError(f"401 Client Error: Unauthorized for url: {url}")
                    continue

                det=""
                try: det=r.json().get("error",{}).get("message","")[:300]
                except Exception: det=(r.text or "")[:300]
                self._emit("http_other_err", code=r.status_code, detail=det); r.raise_for_status()
            except requests.HTTPError as e:
                error_msg = str(e).lower()
                # Check if it's a 401 in the exception message
                if '401' in error_msg or 'unauthorized' in error_msg:
                    # Mark current token as invalid
                    if current_token:
                        self._invalid_tokens.add(current_token)
                    
                    # Check if all tokens are now invalid - fail fast
                    if len(self._invalid_tokens) >= len(self.tokens):
                        # If error message already contains the full "All X authentication token(s)" message,
                        # just re-raise it without emitting again (avoid duplicate messages)
                        if "authentication token" in error_msg and "invalid or expired" in error_msg:
                            raise  # Re-raise the original exception with full message
                        
                        all_invalid_msg = (
                            f"All {len(self.tokens)} authentication token(s) are invalid or expired. "
                            "Please update your Google Labs OAuth tokens in the API Credentials settings. "
                            "To get new tokens, visit https://labs.google and inspect network requests."
                        )
                        raise requests.HTTPError(all_invalid_msg)
                    
                    # Don't sleep, try next token immediately
                    last=e
                    continue
                last=e; time.sleep(self.RETRY_SLEEP_MULTIPLIER*(attempts_made))
            except Exception as e:
                last=e; time.sleep(self.RETRY_SLEEP_MULTIPLIER*(attempts_made))

        if last is None:
            last = Exception("All tokens are invalid or max attempts reached")
        raise last

    def upload_image_file(self, image_path: str, aspect_hint="IMAGE_ASPECT_RATIO_PORTRAIT")->Optional[str]:
        """
        Upload an image file to Google Labs for image-to-video generation.
        
        Args:
            image_path: Path to the image file
            aspect_hint: Aspect ratio hint (e.g., IMAGE_ASPECT_RATIO_PORTRAIT)
        
        Returns:
            Media ID string if successful, None otherwise
        """
        b64,mime=_encode_image_file(image_path)
        payload={"imageInput":{"rawImageBytes":b64,"mimeType":mime,"isUserUploaded":True,"aspectRatio":aspect_hint},
                 "clientContext":{"sessionId":f";{int(time.time()*1000)}","tool":"ASSET_MANAGER"}}
        data=self._post(UPLOAD_IMAGE_URL,payload) or {}
        mid=(data.get("mediaGenerationId") or {}).get("mediaGenerationId")
        return mid

    def start_one(self, job: Dict, model_key: str, aspect_ratio: str, prompt_text: str, copies:int=1, project_id: Optional[str]=DEFAULT_PROJECT_ID)->int:
        """Start a scene with robust fallbacks: delay-after-upload, model ladder (I2V vs T2V), reupload-on-400, per-copy fallback, complete prompt preservation."""
        copies=max(1,int(copies)); base_seed=int(job.get("seed",0)) if str(job.get("seed","")).isdigit() else 0
        mid=job.get("media_id")

        # Log which video generator will be used
        generator_type = "Image-to-Video (I2V)" if mid else "Text-to-Video (T2V)"
        self._emit("video_generator_info", generator_type=generator_type, has_start_image=bool(mid),
                   model_key=model_key, aspect_ratio=aspect_ratio, copies=copies, project_id=project_id)

        # Issue #1 FIX: Auto-save prompt to disk before generation
        # Save to project_dir/prompts/ folder for user reference
        scene_num = job.get("scene_num") or job.get("scene")  # Try to get scene number
        project_dir = job.get("dir") or job.get("project_dir")  # Try to get project directory
        saved_path = _save_prompt_to_disk(
            prompt_data=prompt_text,
            project_dir=project_dir,
            scene_num=scene_num,
            model_key=model_key,
            aspect_ratio=aspect_ratio
        )
        if saved_path:
            self._emit("prompt_saved", filepath=saved_path, scene_num=scene_num)

        # Give backend a moment to index the uploaded image (avoids 400/500 immediately after upload)
        time.sleep(1.0)

        # IMPORTANT: choose fallbacks based on whether we're doing I2V (has start image) or T2V (no image)
        FALLBACKS_I2V={
            "VIDEO_ASPECT_RATIO_PORTRAIT":[
                "veo_3_1_i2v_s_fast_portrait_ultra","veo_3_1_i2v_s_fast_portrait","veo_3_1_i2v_s_portrait","veo_3_1_i2v_s"
            ],
            "VIDEO_ASPECT_RATIO_LANDSCAPE":[
                "veo_3_1_i2v_s_fast_ultra","veo_3_1_i2v_s_fast","veo_3_1_i2v_s"
            ],
            "VIDEO_ASPECT_RATIO_SQUARE":[
                "veo_3_1_i2v_s_fast","veo_3_1_i2v_s"
            ]
        }
        FALLBACKS_T2V={
            "VIDEO_ASPECT_RATIO_PORTRAIT":[
                "veo_3_1_t2v_fast_ultra","veo_3_1_t2v"
            ],
            "VIDEO_ASPECT_RATIO_LANDSCAPE":[
                "veo_3_1_t2v_fast_ultra","veo_3_1_t2v"
            ],
            "VIDEO_ASPECT_RATIO_SQUARE":[
                "veo_3_1_t2v_fast_ultra","veo_3_1_t2v"
            ]
        }
        fallbacks = FALLBACKS_I2V if mid else FALLBACKS_T2V
        # start with the user's chosen model, then ladder through same-family models for the aspect
        models=[model_key]+[m for m in fallbacks.get(aspect_ratio, []) if m!=model_key]

        # compose prompt text (build complete prompt with all fields)
        prompt=_build_complete_prompt_text(prompt_text)
        
        # Extract negative prompt from prompt data
        negative_prompt = _extract_negative_prompt(prompt_text) if isinstance(prompt_text, dict) else "text, words, letters, subtitles, captions, titles, credits, on-screen text, watermarks, logos, brands, camera shake, fisheye"

        def _make_body(use_model, mid_val, copies_n):
            # Build Google Labs API format request
            requests_list = []
            for k in range(copies_n):
                seed = base_seed + k if copies_n > 1 else base_seed
                
                request_item = {
                    "aspectRatio": aspect_ratio,
                    "seed": seed,
                    "videoModelKey": use_model
                }
                
                # Add prompt - different field for I2V vs T2V
                if mid_val:
                    # Image-to-video: use imageInput with startImage
                    request_item["imageInput"] = {
                        "startImage": {"mediaId": mid_val},
                        "prompt": prompt
                    }
                else:
                    # Text-to-video: use textInput
                    request_item["textInput"] = {"prompt": prompt}
                
                requests_list.append(request_item)
            
            # Build final body with Google Labs format
            body = {"requests": requests_list}
            
            # Include project ID if provided
            if project_id:
                body["clientContext"] = {"projectId": project_id}
            
            return body

        def _try(body):
            url=I2V_URL if mid else T2V_URL
            # Log the endpoint being called
            self._emit("api_call_info", endpoint=url, endpoint_type="I2V" if mid else "T2V",
                      request_body_keys=list(body.keys()), num_requests=len(body.get("requests", [])))
            return self._post(url, body) or {}

        def _is_invalid(e: Exception)->bool:
            s=str(e).lower()
            return ("400" in str(e)) or ("invalid json" in s) or ("invalid argument" in s)
        
        def _is_auth_error(e: Exception)->bool:
            """Check if error is a 401 authentication error"""
            s=str(e).lower()
            return ("401" in str(e)) or ("unauthorized" in s) or ("authentication" in s and "invalid" in s)

        # 1) Try batch with model fallbacks
        data=None; last_err=None
        for mkey in models:
            try:
                self._emit("trying_model", model_key=mkey, attempt="batch")
                data=_try(_make_body(mkey, mid, copies))
                last_err=None
                self._emit("model_success", model_key=mkey, has_data=data is not None)
                break
            except Exception as e:
                last_err=e
                self._emit("model_failed", model_key=mkey, error=str(e)[:200])
                # Stop immediately on auth errors (401) - no point trying other models
                if _is_auth_error(e):
                    break
                # Also stop on non-invalid errors (e.g., network issues)
                if not _is_invalid(e):
                    break

        # 2) If invalid and have image -> reupload once then retry ladder (I2V only)
        # BUT skip if we have an auth error - no point reuploading if tokens are invalid
        if last_err and _is_invalid(last_err) and not _is_auth_error(last_err) and mid and job.get("image_path"):
            try:
                new_mid=self.upload_image_file(job["image_path"])
                if new_mid:
                    job["media_id"]=new_mid; mid=new_mid
                    for mkey in models:
                        try:
                            data=_try(_make_body(mkey, mid, copies)); last_err=None; break
                        except Exception as e2:
                            last_err=e2
                            # Stop on auth errors
                            if _is_auth_error(e2):
                                break
                            if not _is_invalid(e2):
                                break
            except Exception as e3:
                last_err=e3

        # 3) Per-copy fallback (still invalid)
        # BUT skip if we have an auth error - tokens are invalid, no point retrying
        job.setdefault("operation_names",[])
        job.setdefault("video_by_idx", [None]*copies)
        job.setdefault("thumb_by_idx", [None]*copies)
        job.setdefault("op_index_map", {})
        job.setdefault("operation_metadata", {})
        if data is None and last_err is not None:
            # Don't retry per-copy if we have an auth error
            if _is_auth_error(last_err):
                # Just raise the auth error - user needs to fix their tokens
                raise last_err
            
            for k in range(copies):
                for mkey in models:
                    try:
                        dat=_try(_make_body(mkey, mid, 1))
                        ops=dat.get("operations",[]) if isinstance(dat,dict) else []
                        if ops:
                            nm=(ops[0].get("operation") or {}).get("name") or ops[0].get("name") or ""
                            if nm:
                                job["operation_names"].append(nm)
                                job["op_index_map"][nm]=k
                                # Store metadata for batch check (sceneId and status from Google API)
                                # Always store metadata with at least the default status for Google API compatibility
                                scene_id = ops[0].get("sceneId", "")
                                status = ops[0].get("status", "MEDIA_GENERATION_STATUS_PENDING")
                                job["operation_metadata"][nm] = {"sceneId": scene_id, "status": status}
                                break
                    except Exception as e:
                        # If it's an auth error, stop trying and raise immediately
                        if _is_auth_error(e):
                            raise
                        # Otherwise, continue trying other models/copies
                        continue
            return len(job.get("operation_names",[]))

        # 4) Batch success
        ops=data.get("operations",[]) if isinstance(data,dict) else []
        self._emit("operations_result", num_operations=len(ops), data_type=type(data).__name__,
                   has_operations_key="operations" in (data if isinstance(data, dict) else {}))
        for ci,op in enumerate(ops):
            nm=(op.get("operation") or {}).get("name") or op.get("name") or ""
            if nm:
                job["operation_names"].append(nm)
                job["op_index_map"][nm]=ci
                # Store metadata for batch check (sceneId and status from Google API)
                # Always store metadata with at least the default status for Google API compatibility
                scene_id = op.get("sceneId", "")
                status = op.get("status", "MEDIA_GENERATION_STATUS_PENDING")
                job["operation_metadata"][nm] = {"sceneId": scene_id, "status": status}
        if job.get("operation_names"): job["status"]="PENDING"

        final_count = len(job.get("operation_names",[]))
        self._emit("start_one_result", operation_count=final_count, requested_copies=copies)
        return final_count

    def _wrap_ops(self, op_names: List[str], metadata: Optional[Dict[str, Dict]] = None, project_id: Optional[str] = None)->dict:
        """
        Wrap operation names into the payload format for batch check.
        
        Args:
            op_names: List of operation names
            metadata: Optional dict mapping operation name to metadata (sceneId, status)
            project_id: Optional project ID for multi-account support (Issue #2 FIX)
        
        Returns:
            Payload dict with operations list
        
        NOTE: Based on testing, we'll try including clientContext with projectId for multi-account support.
              If API rejects it, we fall back to original behavior.
        """
        uniq=[]; seen=set()
        for s in op_names or []:
            if s and s not in seen: seen.add(s); uniq.append(s)

        # Build operations list with metadata if available
        operations = []
        for op_name in uniq:
            op_entry = {"operation": {"name": op_name}}
            # Include sceneId and status if available in metadata
            if metadata and op_name in metadata:
                meta = metadata[op_name]
                if meta.get("sceneId"):
                    op_entry["sceneId"] = meta["sceneId"]
                if meta.get("status"):
                    op_entry["status"] = meta["status"]
            operations.append(op_entry)

        # Issue #2 FIX: Include clientContext with projectId for multi-account support
        # This helps the API know which project context to query for operations
        payload = {"operations": operations}
        if project_id:
            payload["clientContext"] = {"projectId": project_id}
        
        return payload

    def batch_check_operations(self, op_names: List[str], metadata: Optional[Dict[str, Dict]] = None, project_id: Optional[str] = None)->Dict[str,Dict]:
        """
        Check status of video generation operations.
        
        Args:
            op_names: List of operation names to check
            metadata: Optional dict mapping operation name to metadata (sceneId, status)
            project_id: Optional project ID for multi-account support (Issue #2 FIX)
        
        Returns:
            Dict mapping operation name to status info
        
        NOTE: Issue #2 FIX - Added project_id parameter to support multi-account scenarios
              where each account has its own project context.
        """
        if not op_names: 
            return {}
        
        # Issue #2 FIX: Enhanced diagnostic logging
        num_requested = len(op_names)
        self._emit("batch_check_start", num_operations=num_requested, project_id=project_id)
        
        # Make the batch check request with optional project_id
        # Try with project_id first, fallback without it if API rejects
        data = None
        try:
            data = self._post(BATCH_CHECK_URL, self._wrap_ops(op_names, metadata, project_id)) or {}
        except Exception as e:
            # If project_id caused error (e.g., API doesn't support it), retry without
            error_msg = str(e).lower()
            if project_id and ("invalid" in error_msg or "unrecognized" in error_msg or "400" in error_msg):
                self._emit("batch_check_fallback", error=str(e)[:100], retry_without_project=True)
                # Retry without project_id
                data = self._post(BATCH_CHECK_URL, self._wrap_ops(op_names, metadata, None)) or {}
            else:
                # Different error - re-raise it
                raise
        
        out={}
        def _dedup(xs):
            seen=set(); r=[]
            for x in xs:
                if x not in seen: seen.add(x); r.append(x)
            return r
        for item in data.get("operations",[]):
            key=(item.get("operation") or {}).get("name") or item.get("name") or ""
            st=_normalize_status(item)
            urls=_collect_urls_any(item.get("response",{})) or _collect_urls_any(item)
            vurls=[u for u in urls if "/video/" in u]; iurls=[u for u in urls if "/image/" in u]
            out[key or "unknown"]={"status": ("COMPLETED" if st=="DONE" and vurls else ("DONE_NO_URL" if st=="DONE" else st)),
                                   "video_urls": _dedup(vurls), "image_urls": _dedup(iurls), "raw": item}
        
        # Issue #2 FIX: Enhanced diagnostic logging
        num_returned = len(out)
        num_missing = num_requested - num_returned
        self._emit("batch_check_result", 
                  num_requested=num_requested, 
                  num_returned=num_returned, 
                  num_missing=num_missing,
                  missing_ops=[name for name in op_names if name not in out] if num_missing > 0 else [])
        
        return out

    def generate_videos_batch(self, prompt: str, num_videos: int = 1, model_key: str = "veo_3_1_t2v_fast_ultra",
                              aspect_ratio: str = "VIDEO_ASPECT_RATIO_LANDSCAPE",
                              project_id: Optional[str] = DEFAULT_PROJECT_ID) -> List[str]:
        """
        Generate multiple videos in one API call (PR#4: Batch video generation)
        Google Lab Flow supports up to 4 videos per request
        
        Args:
            prompt: Text prompt for video generation
            num_videos: Number of videos to generate (max 4)
            model_key: Video model to use
            aspect_ratio: Aspect ratio (e.g., VIDEO_ASPECT_RATIO_LANDSCAPE)
            project_id: Project ID for the request
            
        Returns:
            List of operation names for polling
        """
        if num_videos > 4:
            num_videos = 4

        # Build complete prompt with all fields
        prompt_text = _build_complete_prompt_text(prompt)
        
        # Build Google Labs API format request
        requests_list = []
        base_seed = int(time.time() * 1000)
        for i in range(num_videos):
            seed = base_seed + i
            request_item = {
                "aspectRatio": aspect_ratio,
                "seed": seed,
                "videoModelKey": model_key,
                "textInput": {"prompt": prompt_text}
            }
            requests_list.append(request_item)
        
        # Build final payload with Google Labs format
        payload = {"requests": requests_list}
        
        # Include project ID if provided
        if project_id:
            payload["clientContext"] = {"projectId": project_id}

        # Call T2V endpoint
        data = self._post(T2V_URL, payload) or {}

        # Extract operation names
        operations = data.get("operations", [])
        operation_names = []
        for op in operations:
            name = (op.get("operation") or {}).get("name") or op.get("name") or ""
            if name:
                operation_names.append(name)

        return operation_names
