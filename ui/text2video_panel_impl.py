
import json
import os
import re
import shutil
import subprocess
import datetime
import time
from xml.sax.saxutils import escape as xml_escape

from PyQt5.QtCore import QObject, pyqtSignal

from services.google.labs_flow_client import DEFAULT_PROJECT_ID, LabsFlowClient
from services.utils.video_downloader import VideoDownloader
from services.account_manager import get_account_manager
from utils import config as cfg
from utils.filename_sanitizer import sanitize_project_name, sanitize_filename

# Backward compatibility
LabsClient = LabsFlowClient

_ASPECT_MAP = {
    "16:9": "VIDEO_ASPECT_RATIO_LANDSCAPE",
    "21:9": "VIDEO_ASPECT_RATIO_LANDSCAPE",
    "9:16": "VIDEO_ASPECT_RATIO_PORTRAIT",
    "4:5": "VIDEO_ASPECT_RATIO_PORTRAIT",
    "1:1": "VIDEO_ASPECT_RATIO_SQUARE",
}

# Location extraction constants
# Regex pattern for parsing screenplay headers: INT./EXT. LOCATION - TIME (duration)
# Example: "INT. HẺM NHỎ - NGÀY (8s)" or "EXT. PARK - DAY"
_SCREENPLAY_LOCATION_PATTERN = re.compile(
    r'(INT\.|EXT\.)\s+(.+?)\s*-\s*(.+?)(?:\s*\(|\s*$)',
    re.IGNORECASE | re.MULTILINE
)

# Time keywords for daytime detection (support Vietnamese and English)
_DAYTIME_KEYWORDS = ["NGÀY", "DAY", "MORNING", "SÁNG", "BUỔI SÁNG"]
_NIGHTTIME_KEYWORDS = ["ĐÊM", "NIGHT", "EVENING", "TỐI", "BUỔI TỐI"]
_LANGS = [
    ("Tiếng Việt","vi"), ("Tiếng Anh","en"), ("Tiếng Nhật","ja"), ("Tiếng Hàn","ko"), ("Tiếng Trung","zh"),
    ("Tiếng Pháp","fr"), ("Tiếng Đức","de"), ("Tiếng Tây Ban Nha","es"), ("Tiếng Nga","ru"), ("Tiếng Thái","th"), ("Tiếng Indonesia","id")
]
_VIDEO_MODELS = [
    "veo_3_1_i2v_s_fast_portrait_ultra",
    "veo_3_1_i2v_s_fast_landscape_ultra",
    "veo_3_1_i2v_s_slow_portrait_ultra",
    "veo_3_1_i2v_s_slow_landscape_ultra",
    "veo_2_general_002",
    "veo_2_i2v_001"
]

# Mapping for display names
_MODEL_DISPLAY_NAMES = {
    "veo_3_1_i2v_s_fast_portrait_ultra": "Veo3.1 i2v Fast Portrait",
    "veo_3_1_i2v_s_fast_landscape_ultra": "Veo3.1 i2v Fast Landscape",
    "veo_3_1_i2v_s_slow_portrait_ultra": "Veo3.1 i2v Slow Portrait",
    "veo_3_1_i2v_s_slow_landscape_ultra": "Veo3.1 i2v Slow Landscape",
    "veo_2_general_002": "Veo2 General",
    "veo_2_i2v_001": "Veo2 i2v"
}

# Error message truncation limit for logging
_MAX_ERROR_MESSAGE_LENGTH = 100

# Style tag mapping for comprehensive visual styles
STYLE_TAG_MAP = {
    # Animation Styles
    "anime_2d": {
        "tags": ["anime", "flat colors", "bold outlines", "2d animation", "cel-shading", "consistent character design"],
        "negatives": [
            "realistic photography", "photorealistic", "3D CGI", 
            "Disney 3D", "Pixar style", "live action", "real people"
        ]
    },
    "anime_cinematic": {
        "tags": ["anime", "cinematic lighting", "dramatic camera", "2d animation", "consistent character design"],
        "negatives": [
            "realistic photography", "photorealistic", "3D CGI",
            "live action", "real people"
        ]
    },
    
    # Realistic Styles
    "realistic": {
        "tags": ["photorealistic", "realistic textures", "natural lighting", "consistent character appearance"],
        "negatives": ["anime", "cartoon", "illustrated", "2d animation"]
    },
    "cinematic": {
        "tags": ["cinematic", "film-like", "dramatic lighting", "professional cinematography", "consistent character appearance"],
        "negatives": ["amateur", "low quality", "home video"]
    },
    
    # Genre Styles
    "sci_fi": {
        "tags": ["sci-fi", "futuristic", "neon lighting", "technology", "holographic", "cyberpunk", "consistent character design"],
        "negatives": ["medieval", "ancient", "rustic", "natural"]
    },
    "horror": {
        "tags": ["horror", "dark", "eerie", "suspenseful", "gothic", "ominous", "consistent character appearance"],
        "negatives": ["bright", "cheerful", "colorful", "happy", "comedy"]
    },
    "fantasy": {
        "tags": ["fantasy", "magical", "enchanted", "mystical", "vibrant", "ethereal", "consistent character design"],
        "negatives": ["realistic", "modern", "technological", "scientific"]
    },
    "action": {
        "tags": ["action", "dynamic", "high energy", "intense", "fast-paced", "explosive", "consistent character appearance"],
        "negatives": ["slow", "static", "calm", "peaceful"]
    },
    "romance": {
        "tags": ["romance", "soft lighting", "warm colors", "dreamy", "gentle", "intimate", "consistent character appearance"],
        "negatives": ["harsh", "dark", "violent", "aggressive"]
    },
    "comedy": {
        "tags": ["comedy", "bright", "playful", "exaggerated", "vibrant", "fun", "consistent character design"],
        "negatives": ["dark", "serious", "dramatic", "horror"]
    },
    
    # Special Styles
    "documentary": {
        "tags": ["documentary", "realistic", "natural lighting", "clear", "informative", "educational", "consistent appearance"],
        "negatives": ["stylized", "artistic", "abstract", "fantasy"]
    },
    "film_noir": {
        "tags": ["film noir", "black and white", "dramatic shadows", "high contrast", "vintage", "1940s aesthetic", "consistent character appearance"],
        "negatives": ["colorful", "bright", "modern", "futuristic"]
    },
    
    # Legacy mappings (for backward compatibility)
    "anime": {
        "tags": ["anime", "flat colors", "bold outlines", "2d animation", "cel-shading", "consistent character design"],
        "negatives": ["realistic photography", "photorealistic", "3D CGI"]
    }
}

def get_model_key_from_display(display_name):
    """Convert display name back to API key"""
    for key, display in _MODEL_DISPLAY_NAMES.items():
        if display == display_name:
            return key
    return display_name  # Fallback

def extract_location_context(scene_data):
    """
    Extract location context from scene data.
    First tries scene.location field, then falls back to parsing screenplay text.
    
    Args:
        scene_data: Scene dict with potential 'location' field or 'screenplay_vi' text
    
    Returns:
        Formatted location context string or None
    """
    # First try: direct location field from LLM-generated scene
    location = scene_data.get("location", "").strip()
    if location:
        return location

    # Second try: parse scene header from screenplay text (if available)
    screenplay = scene_data.get("screenplay_vi", "") or scene_data.get("screenplay_tgt", "")
    if screenplay:
        match = _SCREENPLAY_LOCATION_PATTERN.search(screenplay)
        if match:
            int_ext = match.group(1).strip()  # INT. or EXT.
            location_name = match.group(2).strip()  # e.g., HẺM NHỎ
            time = match.group(3).strip()  # e.g., NGÀY

            # Build descriptive context
            setting_type = "Interior" if "INT" in int_ext.upper() else "Exterior"
            # Check for daytime keywords
            time_upper = time.upper()
            is_daytime = any(keyword in time_upper for keyword in _DAYTIME_KEYWORDS)
            time_desc = "daytime" if is_daytime else "nighttime"

            return f"{setting_type} setting: {location_name}, {time_desc} lighting"

    return None

def _build_setting_details(location_context):
    """
    Build setting_details string with optional location context.
    
    Args:
        location_context: Optional location context string
    
    Returns:
        Formatted setting_details string
    """
    base_details = "Clean composition, minimal props, no clutter; coherent lighting per scene style."
    if location_context:
        return f"{location_context}. {base_details}"
    return base_details

def build_prompt_json(scene_index:int, desc_vi:str, desc_tgt:str, lang_code:str, ratio_str:str, style:str, seconds:int=8, copies:int=1, resolution_hint:str=None, character_bible=None, enhanced_bible=None, voice_settings=None, location_context:str=None, tts_provider:str=None, voice_id:str=None, voice_name:str=None, domain:str=None, topic:str=None, quality:str=None, dialogues:list=None, base_seed:int=None, style_seed:int=None):
    """
    Enhanced prompt JSON schema with comprehensive metadata:
    - Full persona with expertise_context
    - Complete audio object with detailed voiceover (TTS provider, voice details, prosody, ElevenLabs settings) and background_music
    - domain_context object with domain, topic, system_prompt
    - metadata object with creation info and optimization settings
    - bilingual localization (vi + target)
    
    Part D: Now supports enhanced_bible (CharacterBible object) for detailed character consistency
    Part E: Now supports location_context for maintaining consistent backgrounds across scenes
    Part F: Enhanced audio, domain_context, and metadata fields (Issue #5)
    Part G: Now supports dialogues for proper voiceover generation (Issue #7)
    Issue #33: Now supports base_seed for consistent style across scenes
    PR #8: Now supports style_seed for visual style consistency (separate from character seed)
    
    Args:
        base_seed: Optional base seed for consistency across scenes.
                  If None, generates a random seed.
                  Sequential scenes use base_seed + scene_index for consistency.
        style_seed: Optional style seed for visual style consistency across scenes.
                   If None, generates a random seed.
                   Used to maintain same visual style (anime/realistic) throughout.
    """

    ratio_map = {
        '16:9': ('1920x1080', 'VIDEO_ASPECT_RATIO_LANDSCAPE'),
        '21:9': ('2560x1080', 'VIDEO_ASPECT_RATIO_LANDSCAPE'),
        '9:16': ('1080x1920', 'VIDEO_ASPECT_RATIO_PORTRAIT'),
        '4:5' : ('1080x1350', 'VIDEO_ASPECT_RATIO_PORTRAIT'),
        '1:1' : ('1080x1080', 'VIDEO_ASPECT_RATIO_SQUARE'),
    }
    res_default, _ = ratio_map.get(ratio_str, ('1920x1080', 'VIDEO_ASPECT_RATIO_LANDSCAPE'))
    resolution = resolution_hint or res_default
    seconds = max(3, int(seconds or 8))
    copies = max(1, int(copies or 1))

    b1 = round(seconds * 0.25, 2)
    b2 = round(seconds * 0.55, 2)
    b3 = round(seconds * 0.80, 2)
    segments = [
        {"t": f"0.0-{b1}s", "shot": "Establish subject & scene; clean composition; slow, steady motion."},
        {"t": f"{b1}-{b2}s", "shot": "Key action / gesture; maintain framing consistency; avoid jump cuts."},
        {"t": f"{b2}-{b3}s", "shot": "Detail emphasis; micro-movements; texture & highlights."},
        {"t": f"{b3}-{seconds:.1f}s", "shot": "Clear end beat; micro push-in or hold; leave space for on-screen text."},
    ]

    # Get style from STYLE_TAG_MAP
    style_key = style  # This comes from cb_style.currentData()
    
    # Handle separator or invalid selections
    if not style_key or (isinstance(style_key, str) and style_key.startswith("separator")):
        style_key = "anime_2d"  # Default fallback
    
    # Get style configuration
    style_config = STYLE_TAG_MAP.get(style_key)
    
    if not style_config:
        # Fallback: try to match by text (for backward compatibility with old text-based styles)
        style_lower = str(style).lower().replace(" ", "_").replace("(", "").replace(")", "")
        for key in STYLE_TAG_MAP:
            if key in style_lower or style_lower in key:
                style_config = STYLE_TAG_MAP[key]
                break
    
    if not style_config:
        # Final fallback: use anime_2d
        style_config = STYLE_TAG_MAP["anime_2d"]
    
    visual_style_tags = style_config["tags"]
    style_negatives = style_config.get("negatives", [])
    
    # PR #8: Add style consistency markers to visual_style_tags
    visual_style_tags = list(visual_style_tags)  # Create a copy to avoid modifying original
    if style_seed is not None:
        visual_style_tags.extend([
            f"style_seed:{style_seed}",
            "consistent visual style across all scenes",
            "same art direction throughout",
            "unified rendering technique",
            "no style variations between scenes"
        ])

    # Part E: Enhanced location consistency with specific location context
    location_lock = "Keep to single coherent environment; no random background swaps."
    if location_context:
        location_lock = f"CRITICAL: All scenes must be in {location_context}. Do NOT change background, setting, or environment. Maintain exact location consistency across all scenes."

    # BUG FIX #2: Enhanced character consistency locks
    hard_locks = {
        "identity": "CRITICAL: Keep same person/character across all scenes. Same face, same body, same identity. Do NOT change the character or introduce different people.",
        "wardrobe": "Outfit consistency is required. Do NOT change outfit, color, or add accessories without instruction.",
        "hair_makeup": "Keep hair and makeup consistent; do NOT change length or color unless explicitly instructed.",
        "location": location_lock
    }

    # Part D: Enhanced character details with detailed bible
    # Keep original character_details from character_bible without modification
    # This ensures the prompt JSON is sent unmodified to Google Labs Flow
    character_details = "CRITICAL: Keep same person/character across all scenes. Primary talent remains visually consistent across all scenes."
    if enhanced_bible and hasattr(enhanced_bible, 'characters'):
        # Use detailed character bible - preserve original without injection
        try:
            # Build character details from enhanced bible characters with MORE DETAIL
            char_parts = []
            for char in enhanced_bible.characters:
                if isinstance(char, dict):
                    nm = char.get("name", "")
                    role = char.get("role", "")
                    visual = char.get("visual_identity", "")
                    key_trait = char.get("key_trait", "")
                    
                    # Extract detailed physical attributes from character bible
                    hair_dna = char.get("hair_dna", {})
                    eye_signature = char.get("eye_signature", {})
                    physical_blueprint = char.get("physical_blueprint", {})
                    facial_map = char.get("facial_map", {})
                    consistency_anchors = char.get("consistency_anchors", [])

                    if nm:
                        # Build EXTREMELY DETAILED character description with physical attributes and accessories
                        parts = [f"{nm}"]
                        if role:
                            parts.append(f"({role})")
                        
                        # Build comprehensive visual description
                        visual_details = []
                        if visual:
                            visual_details.append(visual)
                        
                        # Add detailed physical descriptions
                        if hair_dna:
                            hair_color = hair_dna.get("color", "")
                            hair_length = hair_dna.get("length", "")
                            hair_style = hair_dna.get("style", "")
                            hair_texture = hair_dna.get("texture", "")
                            if hair_color or hair_length or hair_style:
                                hair_desc = f"{hair_color} {hair_length} {hair_style} {hair_texture} hair".strip()
                                visual_details.append(hair_desc)
                        
                        if eye_signature:
                            eye_color = eye_signature.get("color", "")
                            eye_shape = eye_signature.get("shape", "")
                            if eye_color or eye_shape:
                                eye_desc = f"{eye_shape} {eye_color} eyes".strip()
                                visual_details.append(eye_desc)
                        
                        if physical_blueprint:
                            build = physical_blueprint.get("build", "")
                            skin_tone = physical_blueprint.get("skin_tone", "")
                            if build:
                                visual_details.append(f"{build} build")
                            if skin_tone:
                                visual_details.append(f"{skin_tone} skin")
                        
                        if facial_map:
                            marks = facial_map.get("distinguishing_marks", "")
                            if marks and marks != "none":
                                visual_details.append(f"distinguishing marks: {marks}")
                        
                        # Add top 3 consistency anchors as specific accessories/features
                        if consistency_anchors:
                            for anchor in consistency_anchors[:3]:
                                # Remove numbering like "1. " from anchor text
                                anchor_text = anchor.split(". ", 1)[1] if ". " in anchor else anchor
                                visual_details.append(anchor_text)
                        
                        # Combine all visual details
                        if visual_details:
                            parts.append(f"— Visual: {', '.join(visual_details)}")
                        
                        if key_trait:
                            parts.append(f"Trait: {key_trait}")

                        char_parts.append(" ".join(parts))

            if char_parts:
                character_details = "CRITICAL: Keep same person/character across all scenes. " + "; ".join(char_parts) + ". Keep appearance and demeanor consistent across all scenes."
        except Exception as e:
            # Log the error for debugging but continue with fallback
            import sys
            print(f"[WARN] Character bible processing failed: {e}", file=sys.stderr)
            # Intentional fallback to basic character_details - continue processing
    elif character_bible and isinstance(character_bible, list) and len(character_bible) > 0:
        # BUG FIX #2: Include ALL characters with visual_identity and CRITICAL consistency note
        # Enhanced with MORE DETAIL including physical attributes and accessories
        char_parts = []
        for char in character_bible:
            nm = char.get("name", "")
            role = char.get("role", "")
            visual = char.get("visual_identity", "")
            key_trait = char.get("key_trait", "")
            
            # Extract detailed physical attributes from character bible
            hair_dna = char.get("hair_dna", {})
            eye_signature = char.get("eye_signature", {})
            physical_blueprint = char.get("physical_blueprint", {})
            facial_map = char.get("facial_map", {})
            consistency_anchors = char.get("consistency_anchors", [])

            if nm:
                # Build EXTREMELY DETAILED character description with physical attributes and accessories
                parts = [f"{nm}"]
                if role:
                    parts.append(f"({role})")
                
                # Build comprehensive visual description
                visual_details = []
                if visual:
                    visual_details.append(visual)
                
                # Add detailed physical descriptions
                if hair_dna:
                    hair_color = hair_dna.get("color", "")
                    hair_length = hair_dna.get("length", "")
                    hair_style = hair_dna.get("style", "")
                    hair_texture = hair_dna.get("texture", "")
                    if hair_color or hair_length or hair_style:
                        hair_desc = f"{hair_color} {hair_length} {hair_style} {hair_texture} hair".strip()
                        visual_details.append(hair_desc)
                
                if eye_signature:
                    eye_color = eye_signature.get("color", "")
                    eye_shape = eye_signature.get("shape", "")
                    if eye_color or eye_shape:
                        eye_desc = f"{eye_shape} {eye_color} eyes".strip()
                        visual_details.append(eye_desc)
                
                if physical_blueprint:
                    build = physical_blueprint.get("build", "")
                    skin_tone = physical_blueprint.get("skin_tone", "")
                    if build:
                        visual_details.append(f"{build} build")
                    if skin_tone:
                        visual_details.append(f"{skin_tone} skin")
                
                if facial_map:
                    marks = facial_map.get("distinguishing_marks", "")
                    if marks and marks != "none":
                        visual_details.append(f"distinguishing marks: {marks}")
                
                # Add top 3 consistency anchors as specific accessories/features
                if consistency_anchors:
                    for anchor in consistency_anchors[:3]:
                        # Remove numbering like "1. " from anchor text
                        anchor_text = anchor.split(". ", 1)[1] if ". " in anchor else anchor
                        visual_details.append(anchor_text)
                
                # Combine all visual details
                if visual_details:
                    parts.append(f"— Visual: {', '.join(visual_details)}")
                
                if key_trait:
                    parts.append(f"Trait: {key_trait}")

                char_parts.append(" ".join(parts))

        if char_parts:
            character_details = "CRITICAL: Keep same person/character across all scenes. " + "; ".join(char_parts) + ". Keep appearance and demeanor consistent across all scenes."
        else:
            # Fallback if no characters have proper data
            main = character_bible[0]
            nm = main.get("name", "")
            role = main.get("role", "")
            key = main.get("key_trait", "")
            mot = main.get("motivation", "")
            character_details = f"CRITICAL: Keep same person/character across all scenes. {nm} ({role}) — trait: {key}; motivation: {mot}. Keep appearance and demeanor consistent."

    # Part G: Build voiceover text from dialogues when available
    # Priority: dialogues > scene description
    # This ensures the TTS speaks actual dialogue, not visual description
    vo_text = ""
    if dialogues:
        # Extract dialogue text based on target language
        dialogue_texts = []
        for dlg in dialogues:
            if isinstance(dlg, dict):
                # Determine which text field to use based on language
                text_field = "text_vi" if lang_code == "vi" else "text_tgt"
                fallback_field = "text_tgt" if lang_code == "vi" else "text_vi"
                text = dlg.get(text_field) or dlg.get(fallback_field) or ""

                speaker = dlg.get("speaker", "")
                if speaker and text:
                    dialogue_texts.append(f"{speaker}: {text}")
                elif text:
                    dialogue_texts.append(text)

        if dialogue_texts:
            vo_text = " ".join(dialogue_texts).strip()

    # Fallback to scene description if no dialogues
    if not vo_text:
        # Enhanced: Match voiceover language with target language setting
        # Logic:
        #   - IF lang_code == "vi" (Vietnamese) → Use desc_vi (Vietnamese prompt)
        #   - ELSE (en, ja, ko, zh, fr, de, es, ru, th, id) → Use desc_tgt (Target language prompt)
        # This ensures voiceover text matches the selected TTS language
        if lang_code == "vi":
            vo_text = (desc_vi or desc_tgt or "").strip()
        else:
            vo_text = (desc_tgt or desc_vi or "").strip()

    # Part D: NEVER truncate voiceover - prompt optimizer will handle this
    # if len(vo_text)>240: vo_text = vo_text[:240] + "…"

    # Part F: Build comprehensive voiceover config with all TTS details
    speaking_style = voice_settings.get("speaking_style", "storytelling") if voice_settings else "storytelling"
    rate_multiplier = voice_settings.get("rate_multiplier", 1.0) if voice_settings else 1.0
    pitch_adjust = voice_settings.get("pitch_adjust", 0) if voice_settings else 0
    expressiveness = voice_settings.get("expressiveness", 0.5) if voice_settings else 0.5

    # Get style info for descriptions
    try:
        from services.voice_options import get_style_info, get_elevenlabs_settings, SPEAKING_STYLES
        style_info = get_style_info(speaking_style)
        style_description = style_info.get("description", "")

        # Get ElevenLabs settings (using voice adjustments if available from voice_settings)
        # Note: ElevenLabs adjustments would come from separate UI controls, defaulting to 0.0 for now
        elevenlabs_settings = get_elevenlabs_settings(speaking_style, 0.0, 0.0)
    except (ImportError, KeyError, AttributeError) as e:
        print(f"[Warning] Could not load voice settings: {e}")
        style_description = ""
        elevenlabs_settings = {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.5,
            "use_speaker_boost": True
        }

    # Build prosody descriptions
    rate_description = "normal speed"
    if rate_multiplier < 0.9:
        rate_description = "slow, deliberate pace"
    elif rate_multiplier > 1.1:
        rate_description = "fast, energetic pace"

    pitch_description = "neutral pitch"
    if pitch_adjust < -2:
        pitch_description = "lower, deeper voice"
    elif pitch_adjust > 2:
        pitch_description = "higher, brighter voice"

    expressiveness_description = "moderate emotion"
    if expressiveness < 0.3:
        expressiveness_description = "flat, monotone delivery"
    elif expressiveness > 0.7:
        expressiveness_description = "highly expressive, dynamic delivery"

    # BUG FIX #3: Add validation flag to track if voice matches target language
    # The get_voices_for_provider function already filters voices by language,
    # so if a voice_id is provided, it should already match the language
    voice_lang_validated = bool(voice_id and tts_provider)

    voiceover_config = {
        "language": lang_code or "vi",
        "tts_provider": tts_provider or "google",
        "voice_id": voice_id or "",
        "voice_name": voice_name or "",
        "voice_description": f"TTS voice for {lang_code or 'vi'} language content",
        "voice_language_validated": voice_lang_validated,
        "speaking_style": speaking_style,
        "style_description": style_description,
        "text": vo_text,
        "ssml_markup": f'<speak><prosody rate="{int(rate_multiplier * 100)}%" pitch="{pitch_adjust:+d}st">{xml_escape(vo_text)}</prosody></speak>',
        "prosody": {
            "rate": rate_multiplier,
            "rate_description": rate_description,
            "pitch": pitch_adjust,
            "pitch_description": pitch_description,
            "expressiveness": expressiveness,
            "expressiveness_description": expressiveness_description
        },
        "elevenlabs_settings": elevenlabs_settings
    }

    # Part F: Build domain context
    domain_context = {}
    if domain and topic:
        try:
            from services.domain_prompts import get_system_prompt, build_expert_intro
            system_prompt = get_system_prompt(domain, topic)
            expertise_intro = build_expert_intro(domain, topic, lang_code or "vi")

            domain_context = {
                "domain": domain,
                "topic": topic,
                "expertise_intro": expertise_intro,
                "system_prompt": system_prompt
            }
        except Exception as e:
            import sys
            print(f"[WARN] Domain context failed: {e}", file=sys.stderr)

    # BUG FIX #4: Remove duplicate expertise_context from persona
    # Keep expertise_intro only in domain_context to avoid data duplication
    persona = {
        "role": "Creative Video Director",
        "tone": "Cinematic and evocative",
        "knowledge_level": "Expert in visual storytelling"
    }

    # Part F: Build metadata
    metadata = {
        "created_by": "v3-text2video-panel",
        "creation_date": datetime.datetime.now().isoformat(),
        "video_type": "short-form",
        "target_audience": "general",
        "platform_optimization": ["youtube_shorts", "tiktok", "instagram_reels"]
    }

    # Build Task_Instructions for better language control and voiceover quality
    task_instructions = []

    # 1. Duration instruction
    task_instructions.append(f"Create a video clip lasting approximately {seconds} seconds.")

    # 2. CRITICAL: Language requirement
    lang_name_map = {
        'vi': 'Vietnamese',
        'en': 'English',
        'ja': 'Japanese',
        'ko': 'Korean',
        'zh': 'Chinese',
        'fr': 'French',
        'de': 'German',
        'es': 'Spanish',
        'ru': 'Russian',
        'th': 'Thai',
        'id': 'Indonesian'
    }
    lang_name = lang_name_map.get(lang_code, 'Vietnamese')
    task_instructions.append(
        f"CRITICAL: All voiceover dialogue MUST be in {lang_name} ({lang_code})."
    )

    # 3. Voiceover with emotional cues
    if vo_text:
        # Extract emotional cues from speaking_style
        emotional_cues = []

        if speaking_style == "storytelling":
            emotional_cues.append("narration tone")
        elif speaking_style == "conversational":
            emotional_cues.append("casual, friendly")
        elif speaking_style == "enthusiastic":
            emotional_cues.append("energetic, enthusiastic")
        elif speaking_style == "calm_relaxed":
            emotional_cues.append("calm, relaxed")
        elif speaking_style == "educational":
            emotional_cues.append("clear, educational")
        elif speaking_style == "professional_presentation":
            emotional_cues.append("professional, formal")

        # Add emotion based on scene description (simple keyword matching)
        desc_lower = (desc_vi or desc_tgt or "").lower()
        if any(word in desc_lower for word in ["tức giận", "angry", "giận dữ", "rage", "furious"]):
            emotional_cues.append("tức giận")
        if any(word in desc_lower for word in ["vui", "happy", "hào hứng", "joy", "excited"]):
            emotional_cues.append("vui vẻ")
        if any(word in desc_lower for word in ["buồn", "sad", "lo lắng", "worry", "melancholy"]):
            emotional_cues.append("buồn bã")
        if any(word in desc_lower for word in ["sợ", "fear", "kinh hoàng", "terror", "afraid"]):
            emotional_cues.append("sợ hãi")
        if any(word in desc_lower for word in ["lạnh lùng", "cold", "sắc lạnh", "stern"]):
            emotional_cues.append("lạnh lùng")
        if any(word in desc_lower for word in ["bí ẩn", "mysterious", "mystery"]):
            emotional_cues.append("bí ẩn")
        if any(word in desc_lower for word in ["hài hước", "funny", "comedy", "laugh"]):
            emotional_cues.append("hài hước")

        # Build emotion prefix
        emotion_prefix = f"[{', '.join(emotional_cues)}] " if emotional_cues else ""
        task_instructions.append(f"voiceover: '{emotion_prefix}{vo_text}'")

    # 4. Visual style from constraints
    if visual_style_tags:
        style_desc = ", ".join(visual_style_tags)
        task_instructions.append(f"Visual style: {style_desc}")

    # 5. Character consistency reminder
    if character_bible or enhanced_bible:
        task_instructions.append(
            "Character consistency: Maintain exact character appearance as "
            "described in character_details."
        )

    data = {
        "scene_id": f"s{scene_index:02d}",
        "objective": "Generate a short video clip for this scene based on screenplay and prompts.",
        "Task_Instructions": task_instructions,
        "persona": persona,
        "constraints": {
            "duration_seconds": seconds,
            "aspect_ratio": ratio_str,
            "resolution": resolution,
            "visual_style_tags": visual_style_tags,
            "camera": { "fps": 24, "lens_hint": "50mm look", "stabilization": "steady tripod-like" }
        },
        "assets": { "images": {} },
        "hard_locks": hard_locks,
        "character_details": character_details,
        "setting_details": _build_setting_details(location_context),
        "key_action": f"[SCENE {scene_index}] " + (desc_tgt or desc_vi or "").strip(),
        "camera_direction": segments,
        "audio": {
            "voiceover": voiceover_config,
            "background_music": {
                "type": "ambient",
                "description": "Subtle background music that complements the scene mood",
                "volume": 0.3,
                "mood": style.lower() if style else "neutral"
            }
        },
        "graphics": {
            # NOTE: Subtitles are configured here and sent to video generation API.
            # Actual rendering is performed by the video generation service (e.g., Veo API)
            # or post-processing pipeline. This config ensures subtitles are enabled
            # with correct language and styling.
            "subtitles": {
                "enabled": True,
                "language": lang_code or "vi",
                "style": "clean small caps, bottom-safe",
                "animation": "fade-in"
            },
            "on_screen_text": []
        },
        "negatives": [
            "Do NOT change character identity, outfit, or location without instruction.",
            "Avoid jarring cuts or random background swaps.",
            "No brand logos unless present in references.",
            "No unrealistic X-ray views; use graphic overlays only."
        ] + style_negatives,  # Add style-specific negatives
        "generation": {
            "seed": (base_seed + scene_index) if base_seed is not None else __import__("random").randint(0, 2**31-1),
            "style_seed": style_seed,  # PR #8: Style consistency seed
            "copies": copies,
            "quality": quality or "standard",
            "consistency_mode": "strict"
        },
        "localization": {
            "vi": {"prompt": f"[SCENE {scene_index}] " + (desc_vi or '').strip()},
            (lang_code if lang_code else "en"): {"prompt": f"[SCENE {scene_index}] " + (desc_tgt or desc_vi or '').strip()}
        }
    }

    # Add domain_context if available
    if domain_context:
        data["domain_context"] = domain_context

    # Add metadata
    data["metadata"] = metadata

    return data

class _Worker(QObject):
    log = pyqtSignal(str)
    story_done = pyqtSignal(dict, dict)   # data, context (paths)
    job_card = pyqtSignal(dict)
    job_finished = pyqtSignal()
    progress_update = pyqtSignal(str, int)  # NEW signal: (message, percent)

    def __init__(self, task, payload):
        super().__init__()
        self.task = task
        self.payload = payload
        self.should_stop = False  # PR#4: Add stop flag
        self.video_downloader = VideoDownloader(log_callback=lambda msg: self.log.emit(msg))

    def _handle_labs_event(self, event, log_func):
        """
        Handle diagnostic events from LabsClient.
        
        Args:
            event: Event dict from LabsClient with structure:
                   {"kind": str, ...event-specific fields...}
                   Common event kinds: video_generator_info, api_call_info, 
                   trying_model, model_success, model_failed, operations_result,
                   start_one_result, http_other_err, content_policy_warning
            log_func: Callable[[str], None] - Logging function to use.
                     Takes a formatted log message string.
                     Examples: self.log.emit or lambda msg: queue.put(("log", msg))
        """
        kind = event.get("kind", "")
        if kind == "video_generator_info":
            gen_type = event.get("generator_type", "Unknown")
            model = event.get("model_key", "")
            aspect = event.get("aspect_ratio", "")
            log_func(f"[INFO] Video Generator: {gen_type} | Model: {model} | Aspect: {aspect}")
        elif kind == "api_call_info":
            endpoint = event.get("endpoint", "")
            endpoint_type = event.get("endpoint_type", "")
            num_req = event.get("num_requests", 0)
            log_func(f"[INFO] API Call: {endpoint_type} endpoint | {num_req} request(s)")
            log_func(f"[DEBUG] Endpoint URL: {endpoint}")
        elif kind == "trying_model":
            model = event.get("model_key", "")
            log_func(f"[DEBUG] Trying model: {model}")
        elif kind == "model_success":
            model = event.get("model_key", "")
            log_func(f"[DEBUG] Model {model} succeeded")
        elif kind == "model_failed":
            model = event.get("model_key", "")
            error = event.get("error", "")
            log_func(f"[WARN] Model {model} failed: {error}")
        elif kind == "operations_result":
            num_ops = event.get("num_operations", 0)
            has_key = event.get("has_operations_key", False)
            log_func(f"[DEBUG] API returned {num_ops} operations (has_operations_key={has_key})")
        elif kind == "start_one_result":
            count = event.get("operation_count", 0)
            requested = event.get("requested_copies", 0)
            log_func(f"[INFO] Video generation: {count}/{requested} operations created")
        elif kind == "http_other_err":
            code = event.get("code", "")
            detail = event.get("detail", "")
            log_func(f"[ERROR] HTTP {code}: {detail}")
        elif kind == "content_policy_warning":
            # Content policy filter warning (e.g., minor references aged up)
            warning = event.get("warning", "")
            log_func(f"[CONTENT POLICY] ⚠️  {warning}")
            log_func(f"[INFO] Prompt automatically sanitized to comply with Google's content policies")



    def run(self):
        try:
            if self.task == "script":
                self._run_script()
            elif self.task == "video":
                self._run_video()
        except Exception as e:
            # Include traceback for better debugging
            import traceback
            error_details = traceback.format_exc()
            self.log.emit(f"[ERR] Worker error: {e}")
            self.log.emit(f"[DEBUG] {error_details}")
        finally:
            # BUG FIX: Emit finished signal for both script and video tasks
            # This ensures UI buttons are re-enabled and thread is cleaned up
            self.job_finished.emit()

    def _run_script(self):
        p = self.payload
        self.log.emit("[INFO] Gọi LLM sinh kịch bản...")
        try:
            from services.llm_story_service import generate_script
        except Exception:
            from llm_story_service import generate_script

        # Build voice config if provided
        voice_config = None
        if p.get("tts_provider") and p.get("voice_id"):
            from services.voice_options import get_voice_config
            voice_config = get_voice_config(
                provider=p["tts_provider"],
                voice_id=p["voice_id"],
                language_code=p["out_lang_code"]
            )
        
        # NEW: Progress callback to emit both log and progress signals
        def on_progress(message, percent):
            self.log.emit(f"[PROGRESS {percent}%] {message}")
            self.progress_update.emit(message, percent)

        # Generate script with voice and domain/topic settings
        data = generate_script(
            idea=p["idea"],
            style=p["style"],
            duration_seconds=p["duration"],
            provider=p["provider"],
            output_lang=p["out_lang_code"],
            domain=p.get("domain"),
            topic=p.get("topic"),
            voice_config=voice_config,
            progress_callback=on_progress  # NEW: Pass progress callback
        )
        
        # Issue #33: Generate base seed for video generation consistency (character)
        # PR #8: Generate style seed for visual style consistency (separate from character seed)
        import random
        base_seed = p.get("base_seed")
        if base_seed is None:
            base_seed = random.randint(0, 2**31 - 1)
        
        style_seed = p.get("style_seed")
        if style_seed is None:
            style_seed = random.randint(0, 2**31 - 1)
        
        # Store both seeds with script data
        data["base_seed"] = base_seed
        data["style_seed"] = style_seed
        
        # auto-save to folders
        st = cfg.load()
        root = st.get("download_root") or ""
        if not root:
            root = os.path.join(os.path.expanduser("~"), "Downloads")
            self.log.emit("[WARN] Chưa cấu hình thư mục tải về trong Cài đặt, dùng Downloads mặc định.")
        title = p["project"] or data.get("title_vi") or data.get("title_tgt") or "Project"
        os.makedirs(root, exist_ok=True)
        # Sanitize title to avoid invalid path characters and Vietnamese characters
        safe_title = sanitize_project_name(title)
        prj_dir = os.path.join(root, safe_title); os.makedirs(prj_dir, exist_ok=True)
        dir_script = os.path.join(prj_dir, "01_KichBan"); os.makedirs(dir_script, exist_ok=True)
        dir_prompts= os.path.join(prj_dir, "02_Prompts"); os.makedirs(dir_prompts, exist_ok=True)
        dir_videos = os.path.join(prj_dir, "03_Videos"); os.makedirs(dir_videos, exist_ok=True)

        try:
            with open(os.path.join(dir_script, "screenplay_vi.txt"), "w", encoding="utf-8") as f:
                f.write(data.get("screenplay_vi",""))
            with open(os.path.join(dir_script, "screenplay_tgt.txt"), "w", encoding="utf-8") as f:
                f.write(data.get("screenplay_tgt",""))
            with open(os.path.join(dir_script, "outline_vi.txt"), "w", encoding="utf-8") as f:
                f.write(data.get("outline_vi",""))
            with open(os.path.join(dir_script, "character_bible.json"), "w", encoding="utf-8") as f:
                json.dump(data.get("character_bible",[]), f, ensure_ascii=False, indent=2)
            # Save voice config and domain/topic if present
            if data.get("voice_config"):
                with open(os.path.join(dir_script, "voice_config.json"), "w", encoding="utf-8") as f:
                    json.dump(data["voice_config"], f, ensure_ascii=False, indent=2)
            if p.get("domain") and p.get("topic"):
                domain_info = {
                    "domain": p["domain"],
                    "topic": p["topic"],
                    "language": p["out_lang_code"]
                }
                with open(os.path.join(dir_script, "domain_topic.json"), "w", encoding="utf-8") as f:
                    json.dump(domain_info, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log.emit(f"[WARN] Lưu kịch bản thất bại: {e}")

        ctx = {"title": title, "prj_dir": prj_dir, "dir_script": dir_script, "dir_prompts": dir_prompts, "dir_videos": dir_videos, "scenes": data.get("scenes",[])}
        # Issue #33: Pass base_seed in context
        ctx["base_seed"] = base_seed
        # PR #8: Pass style_seed in context
        ctx["style_seed"] = style_seed
        self.log.emit("[INFO] Hoàn tất sinh kịch bản & lưu file.")
        self.story_done.emit(data, ctx)

    def _download(self, url, dst_path):
        try:
            self.video_downloader.download(url, dst_path)
            return True
        except Exception as e:
            self.log.emit(f"[ERR] Download fail: {e}")
            return False

    def _make_thumb(self, video_path, out_dir, scene, copy):
        try:
            os.makedirs(out_dir, exist_ok=True)
            thumb = os.path.join(out_dir, f"thumb_c{scene}_v{copy}.jpg")
            if shutil.which("ffmpeg"):
                cmd=["ffmpeg","-y","-ss","00:00:00","-i",video_path,"-frames:v","1","-q:v","3",thumb]
                subprocess.run(cmd, check=True)
                return thumb
        except Exception as e:
            self.log.emit(f"[WARN] Tạo thumbnail lỗi: {e}")
        return ""

    def _run_video(self):
        p = self.payload
        st = cfg.load()

        # ISSUE #4 FIX: Multi-account support with parallel processing
        account_mgr = get_account_manager()

        # Check if multi-account mode is enabled for parallel processing
        if account_mgr.is_multi_account_enabled():
            self.log.emit(f"[INFO] Multi-account mode: {len(account_mgr.get_enabled_accounts())} accounts active")
            self.log.emit(f"[INFO] Using PARALLEL processing for faster generation")
            self._run_video_parallel(p, account_mgr)
            return
        else:
            # Fallback to single account mode
            self.log.emit(f"[INFO] Single-account mode: Using SEQUENTIAL processing")
            tokens = st.get("tokens") or []
            project_id = st.get("default_project_id") or DEFAULT_PROJECT_ID

        copies = p["copies"]
        title = p["title"]
        dir_videos = p["dir_videos"]
        up4k = p.get("upscale_4k", False)
        quality = p.get("quality", "1080p")  # Get quality setting
        auto_download = p.get("auto_download", True)  # Get auto-download setting
        thumbs_dir = os.path.join(dir_videos, "thumbs")

        jobs = []
        # Cache for LabsClient instances by project_id to avoid redundant creation
        client_cache = {}

        # Event handler for diagnostic logging (uses helper method)
        def on_labs_event(event):
            self._handle_labs_event(event, self.log.emit)

        # PR#5: Batch generation - make one call per scene with copies parameter (not N calls)
        for scene_idx, scene in enumerate(p["scenes"], start=1):
            # Use actual_scene_num if provided (for retry), otherwise use scene_idx
            actual_scene_num = scene.get("actual_scene_num", scene_idx)
            ratio = scene["aspect"]
            model_key = p.get("model_key","")

            # Create or reuse client for this project_id
            if project_id not in client_cache:
                client_cache[project_id] = LabsClient(tokens, on_event=on_labs_event)
            client = client_cache[project_id]

            # Single API call with copies parameter (instead of N calls)
            body = {"prompt": scene["prompt"], "copies": copies, "model": model_key, "aspect_ratio": ratio}
            self.log.emit(f"[INFO] Start scene {actual_scene_num} with {copies} copies in one batch…")
            rc = client.start_one(body, model_key, ratio, scene["prompt"], copies=copies, project_id=project_id)

            if rc > 0:
                # Only create cards for operations that actually exist in the API response
                # The body dict is updated by client.start_one() with operation_names list
                actual_count = len(body.get("operation_names", []))

                if actual_count < copies:
                    self.log.emit(f"[WARN] Scene {actual_scene_num}: API returned {actual_count} operations but {copies} copies were requested")

                # Create cards only for videos that actually exist
                for copy_idx in range(1, actual_count + 1):
                    card={"scene":actual_scene_num,"copy":copy_idx,"status":"PROCESSING","json":scene["prompt"],"url":"","path":"","thumb":"","dir":dir_videos}
                    self.job_card.emit(card)

                    # Store card data with copy index for operation name mapping
                    # copy_idx is 1-based, so we'll use copy_idx-1 to index into operation_names (0-based)
                    job_info = {
                        'card': card,
                        'body': body,
                        'scene': actual_scene_num,
                        'copy': copy_idx  # 1-based index
                    }
                    jobs.append(job_info)
            else:
                # All copies failed to start
                for copy_idx in range(1, copies+1):
                    card={"scene":actual_scene_num,"copy":copy_idx,"status":"FAILED_START","error_reason":"Failed to start video generation","json":scene["prompt"],"url":"","path":"","thumb":"","dir":dir_videos}
                    self.job_card.emit(card)

        # polling with improved error handling
        retry_count = {}  # Track retry attempts per operation
        download_retry_count = {}  # Track download retry attempts
        max_retries = 3
        max_download_retries = 5

        for poll_round in range(120):
            # PR#4: Check stop flag
            if self.should_stop:
                self.log.emit("[INFO] Đã dừng xử lý theo yêu cầu người dùng.")
                break

            if not jobs:
                self.log.emit("[INFO] Tất cả video đã hoàn tất hoặc thất bại.")
                break

            # Extract all operation names from all jobs
            names = []
            metadata = {}
            for job_info in jobs:
                job_dict = job_info['body']
                names.extend(job_dict.get("operation_names", []))
                # Collect metadata for batch check
                op_meta = job_dict.get("operation_metadata", {})
                if op_meta:
                    metadata.update(op_meta)

            # Batch check with error handling
            try:
                rs = client.batch_check_operations(names, metadata)
            except Exception as e:
                self.log.emit(f"[WARN] Lỗi kiểm tra trạng thái (vòng {poll_round + 1}): {e}")
                import time
                time.sleep(10)  # Wait longer on error before retry
                continue

            new_jobs=[]
            for job_info in jobs:
                card = job_info['card']
                job_dict = job_info['body']
                copy_idx = job_info['copy']  # 1-based copy index

                # Get operation names list and map this copy to its operation
                op_names = job_dict.get("operation_names", [])
                if not op_names:
                    # No operation name - keep in queue for one more iteration in case it appears
                    # Initialize skip counter if not present
                    if 'no_op_count' not in job_info:
                        job_info['no_op_count'] = 0
                    job_info['no_op_count'] += 1

                    # Only skip after multiple attempts
                    if job_info['no_op_count'] > 3:
                        sc = card['scene']
                        cp = card['copy']
                        self.log.emit(f"[WARN] Cảnh {sc} video {cp}: không có operation name sau 3 lần thử")
                    else:
                        new_jobs.append(job_info)
                    continue

                # Map copy index to the correct operation name (copy_idx is 1-based, array is 0-based)
                op_index = copy_idx - 1
                if op_index >= len(op_names):
                    # This copy's operation doesn't exist - should not happen due to earlier check
                    sc = card['scene']
                    cp = card['copy']
                    self.log.emit(f"[ERR] Cảnh {sc} video {cp}: operation index {op_index} out of bounds (only {len(op_names)} operations)")
                    card["status"] = "FAILED"
                    card["error_reason"] = "Operation index out of bounds"
                    self.job_card.emit(card)
                    continue

                op_name = op_names[op_index]
                op_result = rs.get(op_name) or {}

                # VEO3 WORKING STRUCTURE: Check raw API response
                raw_response = op_result.get('raw', {})
                status = raw_response.get('status', '')

                scene = card["scene"]
                copy_num = card["copy"]

                if status == 'MEDIA_GENERATION_STATUS_SUCCESSFUL':
                    # Extract video URL from correct path
                    op_metadata = raw_response.get('operation', {}).get('metadata', {})
                    video_info = op_metadata.get('video', {})
                    video_url = video_info.get('fifeUrl', '')

                    if video_url:
                        card["status"] = "READY"
                        card["url"] = video_url

                        self.log.emit(f"[SUCCESS] Scene {scene} Copy {copy_num}: Video ready!")

                        # Download logic - Always download videos
                        # Sanitize filename to handle Vietnamese characters and special characters
                        raw_fn = f"{title}_scene{scene}_copy{copy_num}.mp4"
                        fn = sanitize_filename(raw_fn)
                        fp = os.path.join(dir_videos, fn)

                        self.log.emit(f"[INFO] Downloading scene {scene} copy {copy_num}...")

                        try:
                            if self._download(video_url, fp):
                                card["status"] = "DOWNLOADED"
                                card["path"] = fp

                                thumb = self._make_thumb(fp, thumbs_dir, scene, copy_num)
                                card["thumb"] = thumb

                                self.log.emit(f"[SUCCESS] ✓ Downloaded: {os.path.basename(fp)}")
                            else:
                                # Track download retries
                                download_key = f"{scene}_{copy_num}"
                                retries = download_retry_count.get(download_key, 0)
                                if retries < max_download_retries:
                                    download_retry_count[download_key] = retries + 1
                                    self.log.emit(f"[WARN] Download failed, will retry ({retries + 1}/{max_download_retries})")
                                    card["status"] = "DOWNLOAD_FAILED"
                                    card["url"] = video_url
                                    self.job_card.emit(card)
                                    new_jobs.append(job_info)
                                    continue
                                else:
                                    self.log.emit(f"[ERR] Download failed after {max_download_retries} attempts")
                                    card["status"] = "DOWNLOAD_FAILED"
                                    card["url"] = video_url
                                    card["error_reason"] = "Download failed after retries"
                                    self.job_card.emit(card)
                        except Exception as e:
                            # Track download retries for exceptions
                            download_key = f"{scene}_{copy_num}"
                            retries = download_retry_count.get(download_key, 0)
                            if retries < max_download_retries:
                                download_retry_count[download_key] = retries + 1
                                self.log.emit(f"[ERR] Download error: {e} - will retry ({retries + 1}/{max_download_retries})")
                                card["status"] = "DOWNLOAD_FAILED"
                                card["url"] = video_url
                                self.job_card.emit(card)
                                new_jobs.append(job_info)
                                continue
                            else:
                                self.log.emit(f"[ERR] Download error after {max_download_retries} attempts: {e}")
                                card["status"] = "DOWNLOAD_FAILED"
                                card["url"] = video_url
                                card["error_reason"] = f"Download error: {str(e)[:50]}"
                                self.job_card.emit(card)

                        self.job_card.emit(card)
                    else:
                        # Video marked successful but no URL - this is an error state
                        self.log.emit(f"[ERR] Scene {scene} Copy {copy_num}: No video URL in response")
                        card["status"] = "DONE_NO_URL"
                        card["error_reason"] = "No video URL in response"
                        self.job_card.emit(card)

                elif status == 'MEDIA_GENERATION_STATUS_FAILED':
                    # Try to extract error details from API response
                    error_info = raw_response.get('operation', {}).get('error', {})
                    error_message = error_info.get('message', '')

                    # Categorize the error
                    if 'quota' in error_message.lower() or 'limit' in error_message.lower():
                        error_reason = "Vượt quota API"
                    elif 'policy' in error_message.lower() or 'content' in error_message.lower() or 'safety' in error_message.lower():
                        error_reason = "Nội dung không phù hợp"
                    elif 'timeout' in error_message.lower():
                        error_reason = "Timeout"
                    elif error_message:
                        error_reason = error_message[:80]
                    else:
                        error_reason = "Video generation failed"

                    card["status"] = "FAILED"
                    card["error_reason"] = error_reason
                    self.log.emit(f"[ERR] Scene {scene} Copy {copy_num} FAILED: {error_reason}")
                    self.job_card.emit(card)

                else:
                    # Still processing (PENDING, ACTIVE, or other states)
                    card["status"] = "PROCESSING"
                    self.job_card.emit(card)
                    new_jobs.append(job_info)

            jobs=new_jobs

            if jobs:
                poll_info = f"vòng {poll_round + 1}/120"
                # Warn if approaching timeout
                if poll_round >= 100:
                    self.log.emit(f"[WARN] Đang chờ {len(jobs)} video ({poll_info}) - sắp hết thời gian chờ!")
                else:
                    self.log.emit(f"[INFO] Đang chờ {len(jobs)} video ({poll_info})...")
                try:
                    import time
                    time.sleep(5)
                except Exception:
                    pass

        # If we exit the loop with remaining jobs, they timed out
        if jobs:
            self.log.emit(f"[WARN] Hết thời gian chờ, còn {len(jobs)} video chưa hoàn thành")
            for job_info in jobs:
                card = job_info['card']
                if card.get("status") == "PROCESSING":
                    card["status"] = "TIMEOUT"
                    card["error_reason"] = "Quá thời gian chờ (timeout)"
                    self.job_card.emit(card)

        # 4K upscale

        if up4k:
            has_ffmpeg = shutil.which("ffmpeg") is not None
            if not has_ffmpeg:
                self.log.emit("[WARN] Không tìm thấy ffmpeg trong PATH — bỏ qua upscale 4K.")
            else:
                for job_info in jobs:
                    card = job_info['card']
                    if card.get("path"):
                        src=card["path"]
                        dst=src.replace(".mp4","_4k.mp4")
                        cmd=["ffmpeg","-y","-i",src,"-vf","scale=3840:-2","-c:v","libx264","-preset","fast",dst]
                        try:
                            subprocess.run(cmd, check=True)
                            card["path"]=dst
                            card["status"]="UPSCALED_4K"
                            self.job_card.emit(card)
                        except Exception as e:
                            self.log.emit(f"[ERR] 4K upscale fail: {e}")

    def _run_video_parallel(self, p, account_mgr):
        """
        Parallel video generation using multiple accounts
        Distributes scenes across accounts using round-robin for faster processing
        """
        import threading
        from queue import Queue

        st = cfg.load()
        copies = p["copies"]
        title = p["title"]
        dir_videos = p["dir_videos"]
        up4k = p.get("upscale_4k", False)
        quality = p.get("quality", "1080p")
        auto_download = p.get("auto_download", True)
        thumbs_dir = os.path.join(dir_videos, "thumbs")

        accounts = account_mgr.get_enabled_accounts()
        num_accounts = len(accounts)

        self.log.emit(f"[INFO] 🚀 Parallel mode: {num_accounts} accounts, {len(p['scenes'])} scenes")

        # Distribute scenes across accounts using round-robin
        batches = [[] for _ in range(num_accounts)]
        for scene_idx, scene in enumerate(p["scenes"], start=1):
            account_idx = (scene_idx - 1) % num_accounts
            batches[account_idx].append((scene_idx, scene))

        # Results queue for thread-safe communication
        results_queue = Queue()
        all_jobs = []  # Jobs storage protected by jobs_lock for thread-safety
        jobs_lock = threading.Lock()

        # Create and start threads
        threads = []
        for i, (account, batch) in enumerate(zip(accounts, batches)):
            if not batch:
                continue

            thread = threading.Thread(
                target=self._process_scene_batch,
                args=(account, batch, p, results_queue, all_jobs, jobs_lock, i),
                daemon=True,
                name=f"Text2Video-{account.name}"
            )
            threads.append(thread)
            self.log.emit(f"[INFO] Thread {i+1}: {len(batch)} scenes → {account.name}")
            thread.start()

        # Monitor progress from all threads
        total_scenes = len(p["scenes"])
        completed_starts = 0

        while completed_starts < total_scenes:
            if self.should_stop:
                self.log.emit("[INFO] Parallel processing stopped by user")
                break

            try:
                # Wait for results from any thread
                import queue
                msg_type, data = results_queue.get(timeout=1.0)

                if msg_type == "scene_started":
                    scene_idx, job_infos = data
                    completed_starts += 1
                    # Only log success if jobs were actually created
                    if job_infos:
                        self.log.emit(
                            f"[INFO] Scene {scene_idx} started ({completed_starts}/{total_scenes})"
                        )
                    else:
                        self.log.emit(
                            f"[ERROR] Scene {scene_idx} failed to start "
                            f"({completed_starts}/{total_scenes})"
                        )
                elif msg_type == "card":
                    # Emit card update
                    self.job_card.emit(data)
                elif msg_type == "log":
                    self.log.emit(data)

            except queue.Empty:
                # Timeout, check if threads still running
                if all(not t.is_alive() for t in threads):
                    break
            except Exception as e:
                self.log.emit(f"[WARN] Progress monitoring error: {e}")
                if all(not t.is_alive() for t in threads):
                    break

        # Wait for all threads to complete scene starts (generous timeout for API calls)
        for thread in threads:
            thread.join(timeout=60.0)  # 60s timeout to handle slow network/API

        # Summary of scene starts
        if len(all_jobs) == 0:
            self.log.emit(
                f"[ERROR] All {total_scenes} scenes failed to start. "
                "No video generation jobs were created."
            )
            self.log.emit(
                "[ERROR] Common causes: API quota exceeded, invalid account credentials, "
                "or content policy violations."
            )
            self.log.emit("[INFO] Please check account settings and try again.")
        else:
            successful_scenes = len(set(job['scene'] for job in all_jobs))
            self.log.emit(
                f"[INFO] {successful_scenes}/{total_scenes} scenes started successfully. "
                f"Starting polling for {len(all_jobs)} jobs..."
            )

        # Now poll for all jobs (same logic as sequential but with all jobs from all threads)
        self._poll_all_jobs(all_jobs, dir_videos, thumbs_dir, up4k, auto_download, quality)

    def _process_scene_batch(self, account, batch, p, results_queue, all_jobs, jobs_lock, thread_id):
        """
        Process a batch of scenes in a separate thread
        
        Note: For retry operations, scenes contain 'actual_scene_num' field to preserve
        the original scene number when retrying a single scene. This ensures logs and
        cards show the correct scene number (e.g., "scene 2") instead of the enumeration
        index (e.g., "scene 1" for a single-item retry batch).
        """
        try:
            # Create event handler for diagnostic logging (uses helper method)
            def on_labs_event(event):
                # Wrap log function to put messages in queue
                def log_to_queue(msg):
                    results_queue.put(("log", msg))
                self._handle_labs_event(event, log_to_queue)

            # Create client for this account with event handler
            client = LabsClient(account.tokens, on_event=on_labs_event)

            copies = p["copies"]
            model_key = p.get("model_key", "")
            dir_videos = p["dir_videos"]

            thread_name = f"T{thread_id+1}"

            for scene_idx, scene in batch:
                if self.should_stop:
                    results_queue.put(("log", f"{thread_name}: Stopped by user"))
                    break

                try:
                    # Use actual_scene_num if provided (for retry), otherwise use scene_idx
                    actual_scene_num = scene.get("actual_scene_num", scene_idx)
                    ratio = scene["aspect"]

                    # Start generation
                    body = {"prompt": scene["prompt"], "copies": copies, "model": model_key, "aspect_ratio": ratio}
                    results_queue.put(("log", f"{thread_name}: Starting scene {actual_scene_num} ({copies} copies)"))

                    rc = client.start_one(body, model_key, ratio, scene["prompt"], copies=copies, project_id=account.project_id)

                    if rc > 0:
                        actual_count = len(body.get("operation_names", []))

                        if actual_count < copies:
                            results_queue.put(("log", f"{thread_name}: Scene {actual_scene_num} returned {actual_count}/{copies} operations"))

                        # Create job cards
                        job_infos = []
                        for copy_idx in range(1, actual_count + 1):
                            card = {
                                "scene": actual_scene_num,
                                "copy": copy_idx,
                                "status": "PROCESSING",
                                "json": scene["prompt"],
                                "url": "",
                                "path": "",
                                "thumb": "",
                                "dir": dir_videos
                            }
                            results_queue.put(("card", card))

                            job_info = {
                                'card': card,
                                'body': body,
                                'scene': actual_scene_num,
                                'copy': copy_idx,
                                'client': client,  # Keep client reference for polling
                                'project_id': account.project_id  # Issue #2 FIX: Store project_id for batch_check
                            }
                            job_infos.append(job_info)

                        # Add to global jobs list (thread-safe)
                        with jobs_lock:
                            all_jobs.extend(job_infos)

                        results_queue.put(("scene_started", (actual_scene_num, job_infos)))
                        results_queue.put(("log", f"{thread_name}: Scene {actual_scene_num} started successfully"))
                    else:
                        # Failed to start - API returned 0 operations
                        # This can happen due to: quota exceeded, invalid credentials,
                        # API errors, or content policy violations
                        error_reason = (
                            "Failed to start video generation (API returned 0 operations). "
                            "Check: account credentials, API quota, and content policy compliance."
                        )
                        for copy_idx in range(1, copies + 1):
                            card = {
                                "scene": actual_scene_num,
                                "copy": copy_idx,
                                "status": "FAILED_START",
                                "error_reason": error_reason,
                                "json": scene["prompt"],
                                "url": "",
                                "path": "",
                                "thumb": "",
                                "dir": dir_videos
                            }
                            results_queue.put(("card", card))

                        results_queue.put(("scene_started", (actual_scene_num, [])))
                        results_queue.put(
                            ("log", f"{thread_name}: Scene {actual_scene_num} failed to start - {error_reason}")
                        )

                    # Small delay between scenes to respect API rate limits
                    # TODO: Make this configurable per account rate limits
                    time.sleep(0.5)

                except Exception as e:
                    # Exception during scene start - create failure cards
                    error_msg = f"Exception during start: {str(e)[:_MAX_ERROR_MESSAGE_LENGTH]}"
                    results_queue.put(("log", f"{thread_name}: Error on scene {actual_scene_num}: {e}"))

                    for copy_idx in range(1, copies + 1):
                        card = {
                            "scene": actual_scene_num,
                            "copy": copy_idx,
                            "status": "FAILED_START",
                            "error_reason": error_msg,
                            "json": scene.get("prompt", ""),
                            "url": "",
                            "path": "",
                            "thumb": "",
                            "dir": dir_videos
                        }
                        results_queue.put(("card", card))

                    results_queue.put(("scene_started", (actual_scene_num, [])))

            results_queue.put(("log", f"{thread_name}: Batch complete"))

        except Exception as e:
            results_queue.put(("log", f"Thread {thread_id+1} error: {e}"))

    def _poll_all_jobs(self, jobs, dir_videos, thumbs_dir, up4k, auto_download, quality):
        """Poll all jobs for completion (shared logic between parallel and sequential)"""
        if not jobs:
            self.log.emit("[INFO] No jobs to poll")
            return

        # Group jobs by client to batch poll efficiently
        client_jobs = {}
        for job_info in jobs:
            client = job_info.get('client')
            if client not in client_jobs:
                client_jobs[client] = []
            client_jobs[client].append(job_info)

        retry_count = {}
        download_retry_count = {}
        max_retries = 3
        max_download_retries = 5

        for poll_round in range(120):
            if self.should_stop:
                self.log.emit("[INFO] Polling stopped by user")
                break

            if not jobs:
                self.log.emit("[INFO] All videos completed or failed")
                break

            # Poll each client's jobs
            for client, client_job_list in list(client_jobs.items()):
                if not client_job_list:
                    continue

                # Extract all operation names for this client
                names = []
                metadata = {}
                # Issue #2 FIX: Get project_id from first job (all jobs for same client have same project_id)
                project_id = None
                for job_info in client_job_list:
                    job_dict = job_info['body']
                    names.extend(job_dict.get("operation_names", []))
                    # Collect metadata for batch check
                    op_meta = job_dict.get("operation_metadata", {})
                    if op_meta:
                        metadata.update(op_meta)
                    # Get project_id from first job
                    if project_id is None:
                        project_id = job_info.get('project_id')

                if not names:
                    continue

                # Batch check - Issue #2 FIX: Pass project_id for multi-account support
                try:
                    rs = client.batch_check_operations(names, metadata, project_id=project_id)
                except Exception as e:
                    self.log.emit(f"[WARN] Poll error (round {poll_round + 1}): {e}")
                    time.sleep(10)
                    continue

                # Process results (same logic as original sequential)
                new_jobs = []
                for job_info in client_job_list:
                    card = job_info['card']
                    job_dict = job_info['body']
                    copy_idx = job_info['copy']

                    op_names = job_dict.get("operation_names", [])
                    if not op_names:
                        if 'no_op_count' not in job_info:
                            job_info['no_op_count'] = 0
                        job_info['no_op_count'] += 1

                        if job_info['no_op_count'] > 3:
                            self.log.emit(f"[WARN] Scene {card['scene']} copy {card['copy']}: no operation name")
                        else:
                            new_jobs.append(job_info)
                        continue

                    op_index = copy_idx - 1
                    if op_index >= len(op_names):
                        self.log.emit(f"[ERR] Scene {card['scene']} copy {card['copy']}: operation index out of bounds")
                        card["status"] = "FAILED"
                        card["error_reason"] = "Operation index out of bounds"
                        self.job_card.emit(card)
                        continue

                    op_name = op_names[op_index]
                    op_result = rs.get(op_name) or {}
                    raw_response = op_result.get('raw', {})
                    status = raw_response.get('status', '')

                    scene = card["scene"]
                    copy_num = card["copy"]

                    if status == 'MEDIA_GENERATION_STATUS_SUCCESSFUL':
                        op_metadata = raw_response.get('operation', {}).get('metadata', {})
                        video_info = op_metadata.get('video', {})
                        video_url = video_info.get('fifeUrl', '')

                        if video_url:
                            card["status"] = "READY"
                            card["url"] = video_url
                            self.log.emit(f"[SUCCESS] Scene {scene} Copy {copy_num}: Video ready!")

                            # Download if enabled
                            if auto_download:
                                out_name = f"scene_{scene:03d}_copy_{copy_num:02d}.mp4"
                                dst_path = os.path.join(dir_videos, out_name)

                                if self._download(video_url, dst_path):
                                    card["path"] = dst_path
                                    card["status"] = "DOWNLOADED"

                                    # Thumbnail
                                    thumb = self._make_thumb(dst_path, thumbs_dir, scene, copy_num)
                                    if thumb:
                                        card["thumb"] = thumb

                                    self.log.emit(f"[DOWNLOAD] Scene {scene} Copy {copy_num}: Downloaded")
                                else:
                                    card["status"] = "DOWNLOAD_FAILED"
                                    card["error_reason"] = "Tải video thất bại"

                            self.job_card.emit(card)
                        else:
                            # Video marked successful but no URL - error state
                            self.log.emit(f"[ERR] Scene {scene} Copy {copy_num}: Không có URL video trong phản hồi")
                            card["status"] = "DONE_NO_URL"
                            card["error_reason"] = "Không có URL video"
                            self.job_card.emit(card)

                    elif status in ['MEDIA_GENERATION_STATUS_FAILED', 'MEDIA_GENERATION_STATUS_BLOCKED']:
                        # Extract detailed error information from API response
                        error_info = raw_response.get('operation', {}).get('error', {})
                        error_message = error_info.get('message', '')

                        # Categorize the error for better user understanding
                        if 'quota' in error_message.lower() or 'limit' in error_message.lower():
                            error_reason = "Vượt quota API"
                        elif 'policy' in error_message.lower() or 'content' in error_message.lower() or 'safety' in error_message.lower():
                            error_reason = "Nội dung không phù hợp (vi phạm chính sách)"
                        elif 'timeout' in error_message.lower():
                            error_reason = "Timeout - quá thời gian chờ"
                        elif status == 'MEDIA_GENERATION_STATUS_BLOCKED':
                            error_reason = "Bị chặn (nội dung vi phạm)"
                        elif error_message:
                            error_reason = error_message[:80]
                        else:
                            error_reason = "Tạo video thất bại"

                        card["status"] = "FAILED"
                        card["error_reason"] = error_reason
                        self.log.emit(f"[FAILED] Scene {scene} Copy {copy_num}: {error_reason}")
                        self.job_card.emit(card)

                    else:
                        # Still processing
                        card["status"] = "PROCESSING"
                        self.job_card.emit(card)
                        new_jobs.append(job_info)

                client_jobs[client] = new_jobs

            # Update main jobs list
            jobs = [job for job_list in client_jobs.values() for job in job_list]

            if jobs:
                # Warn if approaching timeout
                if poll_round >= 100:
                    self.log.emit(f"[WARN] Waiting for {len(jobs)} videos (round {poll_round + 1}/120) - approaching timeout!")
                else:
                    self.log.emit(f"[INFO] Waiting for {len(jobs)} videos (round {poll_round + 1}/120)...")
                time.sleep(5)

        # If we exit the loop with remaining jobs, they timed out
        if jobs:
            self.log.emit(f"[WARN] Polling timeout reached, {len(jobs)} videos still processing")
            for job_info in jobs:
                card = job_info['card']
                if card.get("status") == "PROCESSING":
                    card["status"] = "TIMEOUT"
                    card["error_reason"] = "Polling timeout (quá thời gian chờ)"
                    self.job_card.emit(card)

        # 4K upscale if requested
        if up4k and shutil.which("ffmpeg"):
            self.log.emit("[INFO] Starting 4K upscale...")
            for job_info in jobs:
                card = job_info['card']
                if card.get("path"):
                    src = card["path"]
                    dst = src.replace(".mp4", "_4k.mp4")
                    cmd = ["ffmpeg", "-y", "-i", src, "-vf", "scale=3840:-2", "-c:v", "libx264", "-preset", "fast", dst]
                    try:
                        subprocess.run(cmd, check=True)
                        card["path"] = dst
                        card["status"] = "UPSCALED_4K"
                        self.job_card.emit(card)
                        self.log.emit(f"[4K] Scene {card['scene']} Copy {card['copy']}: Upscaled")
                    except Exception as e:
                        self.log.emit(f"[ERR] 4K upscale failed: {e}")

