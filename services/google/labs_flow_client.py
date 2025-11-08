import base64
import json
import mimetypes
import re
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests

# Import content policy filter for prompt sanitization
try:
    from services.google.content_policy_filter import sanitize_prompt_for_google_labs
except ImportError:
    try:
        from content_policy_filter import sanitize_prompt_for_google_labs
    except ImportError:
        # Fallback: no filtering if module not available
        def sanitize_prompt_for_google_labs(prompt, enable_age_up=True):
            return prompt, []

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
    # SECTION 0B: VOICEOVER LANGUAGE (TOP PRIORITY)
    # ═══════════════════════════════════════════════════════════════
    audio = prompt_data.get("audio", {})
    if isinstance(audio, dict):
        voiceover = audio.get("voiceover", {})
        if isinstance(voiceover, dict):
            vo_lang = voiceover.get("language", "")
            vo_text = voiceover.get("text", "")

            if vo_lang and vo_text:
                # Map language codes to full names
                lang_name_map = {
                    'vi': 'Vietnamese', 'en': 'English', 'ja': 'Japanese',
                    'ko': 'Korean', 'zh': 'Chinese', 'fr': 'French',
                    'de': 'German', 'es': 'Spanish', 'ru': 'Russian',
                    'th': 'Thai', 'id': 'Indonesian'
                }
                lang_name = lang_name_map.get(vo_lang, vo_lang.upper())

                # CRITICAL: This MUST be at the very top
                voice_directive = (
                    f"═══════════════════════════════════════════════\n"
                    f"CRITICAL AUDIO REQUIREMENT (HIGHEST PRIORITY)\n"
                    f"═══════════════════════════════════════════════\n"
                    f"ALL voiceover and dialogue audio MUST be spoken in {lang_name} ({vo_lang}).\n"
                    f"Do NOT use any other language for voice audio.\n"
                    f"Text-to-speech MUST use {lang_name} ({vo_lang}) language model.\n"
                    f"\nVoiceover text:\n\"{vo_text}\"\n"
                    f"═══════════════════════════════════════════════"
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
        if "anime" in style_lower or "flat colors" in style_lower or "outlined" in style_lower:
            main_style = "2D Hand-Drawn Anime Animation"
        elif "realistic" in style_lower:
            main_style = "Photorealistic Live Action"
        elif "cinematic" in style_lower:
            main_style = "Cinematic Film Style"

        # Build VISUAL STYLE LOCK section (similar to CHARACTER IDENTITY LOCK)
        style_lock = (
            "╔═══════════════════════════════════════════════════════════╗\n"
            "║  VISUAL STYLE LOCK (CRITICAL PRIORITY)                   ║\n"
            "║  THIS SECTION MUST NEVER BE IGNORED OR MODIFIED          ║\n"
            "╚═══════════════════════════════════════════════════════════╝\n\n"
            f"REQUIRED STYLE: {main_style}\n\n"
            "THIS EXACT VISUAL STYLE FOR ALL SCENES:\n"
        )

        # Add style-specific requirements
        if "anime" in style_lower or "flat colors" in style_lower or "outlined" in style_lower:
            style_lock += (
                "✓ 2D hand-drawn animation aesthetic\n"
                "✓ Flat colors with cel-shading technique\n"
                "✓ Bold black outlines (3-5px width around characters and objects)\n"
                "✓ Cartoon/illustrated look, NOT photographic\n"
                "✓ Traditional anime art style (like Japanese TV animation)\n"
                "✓ Simplified backgrounds with painted look\n"
                "✓ Expressive character designs with large eyes\n\n"
                "FORBIDDEN VISUAL STYLES:\n"
                "✗ Realistic photography or photorealistic rendering\n"
                "✗ 3D computer animation (CGI)\n"
                "✗ Semi-realistic or hybrid styles\n"
                "✗ Rotoscoping or live-action traced\n"
                "✗ Western cartoon styles (Disney 3D, Pixar)\n"
                "✗ Mixed 2D/3D elements\n"
                "✗ Photographic lighting or textures\n"
            )
        elif "realistic" in style_lower or "cinematic" in style_lower:
            style_lock += (
                "✓ Photorealistic rendering with natural textures\n"
                "✓ Realistic lighting and shadows\n"
                "✓ Real-world physics and proportions\n"
                "✓ Detailed textures and materials\n"
                "✓ Natural camera work\n\n"
                "FORBIDDEN VISUAL STYLES:\n"
                "✗ Anime or cartoon aesthetics\n"
                "✗ 2D hand-drawn animation\n"
                "✗ Flat colors or cel-shading\n"
                "✗ Stylized or illustrated look\n"
                "✗ Bold outlines or cartoon features\n"
            )

        style_lock += (
            "\n🎨 STYLE CONSISTENCY RULES:\n"
            "1. Use EXACTLY the same visual style in every single scene\n"
            "2. NEVER mix realistic and anime styles\n"
            "3. NEVER change rendering technique mid-story\n"
            "4. NEVER switch between 2D and 3D\n"
            "5. Maintain IDENTICAL art direction throughout\n"
            "6. All scenes must look like they're from the SAME production\n\n"
            "⚠️  Any style variation is STRICTLY FORBIDDEN.\n"
        )

        # Add style seed if available
        if style_seed:
            style_lock += f"Use style seed: {style_seed} for visual consistency.\n"

        style_lock += (
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

class LabsFlowClient:
    """
    Google Labs Flow Client with multi-token rotation support
    
    Features:
    - Automatic token rotation across multiple OAuth tokens for load balancing
    - Robust error handling with retries
    - Supports both I2V (image-to-video) and T2V (text-to-video) generation
    - Smart 401 error handling: skips invalid tokens immediately
    """
    MAX_RETRY_ATTEMPTS = 9  # Maximum total retry attempts across all tokens
    RETRY_SLEEP_MULTIPLIER = 0.7  # Multiplier for exponential backoff sleep time

    def __init__(self, bearers: List[str], timeout: Tuple[int,int]=(20,180), on_event: Optional[Callable[[dict], None]]=None):
        self.tokens=[t.strip() for t in (bearers or []) if t.strip()]
        if not self.tokens: raise ValueError("No Labs tokens provided")
        self._idx=0; self.timeout=timeout; self.on_event=on_event
        self._invalid_tokens=set()  # Track tokens that returned 401

    def _tok(self)->str:
        """Get next token using round-robin rotation for load balancing"""
        t=self.tokens[self._idx % len(self.tokens)]; self._idx+=1; return t

    def _emit(self, kind: str, **kw):
        if self.on_event:
            try: self.on_event({"kind":kind, **kw})
            except Exception: pass

    def _post(self, url: str, payload: dict, suppress_error_logging: bool = False) -> dict:
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

                # FIX: Stringify payload for text/plain Content-Type
                headers = _headers(current_token)
                content_type = headers.get("content-type", "")

                if content_type.startswith("text/plain"):
                    # Content-Type is text/plain → stringify payload
                    # This matches Google Labs Flow API requirements
                    data_to_send = json.dumps(payload, ensure_ascii=False)
                    r = requests.post(url, headers=headers, data=data_to_send, timeout=self.timeout)
                else:
                    # Content-Type is application/json → use json= parameter
                    # (backward compatibility)
                    r = requests.post(url, headers=headers, json=payload, timeout=self.timeout)

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
                
                # Only emit error if not suppressed (for retry attempts)
                if not suppress_error_logging:
                    self._emit("http_other_err", code=r.status_code, detail=det)
                
                r.raise_for_status()
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

        # CRITICAL FIX: Send prompt as JSON string (Option A)
        # Google Labs expects FULL JSON structure, not parsed text

        # Parse prompt_text to get original data
        original_prompt_data = None
        if isinstance(prompt_text, dict):
            original_prompt_data = prompt_text
        elif isinstance(prompt_text, str):
            # If already a string, check if it's JSON or plain text
            try:
                # Try to parse as JSON
                original_prompt_data = json.loads(prompt_text)
            except:
                # Not JSON - it's plain text
                original_prompt_data = prompt_text
        else:
            original_prompt_data = str(prompt_text)
        
        # ═══════════════════════════════════════════════════════════════
        # CONTENT POLICY FILTER: Sanitize prompt to comply with Google's policies
        # This prevents HTTP 400 errors caused by content policy violations
        # (especially regarding minors/children)
        # ═══════════════════════════════════════════════════════════════
        sanitized_prompt_data, policy_warnings = sanitize_prompt_for_google_labs(
            original_prompt_data, 
            enable_age_up=True
        )
        
        # Emit warnings if any content was sanitized
        if policy_warnings:
            for warning in policy_warnings:
                self._emit("content_policy_warning", warning=warning)
        
        # Convert sanitized data to optimized text format for API
        # Use _build_complete_prompt_text to convert structured JSON to text
        if isinstance(sanitized_prompt_data, dict):
            # Convert dict to complete text prompt using the builder function
            prompt = _build_complete_prompt_text(sanitized_prompt_data)
        elif isinstance(sanitized_prompt_data, str):
            # Already a string - check if it's JSON that needs conversion
            try:
                # Try to parse as JSON to validate
                parsed = json.loads(sanitized_prompt_data)
                # If successful, it's JSON - convert to text format
                prompt = _build_complete_prompt_text(parsed)
            except:
                # Not JSON - it's plain text, use as-is
                # (This maintains backward compatibility for simple text prompts)
                prompt = sanitized_prompt_data
        else:
            prompt = str(sanitized_prompt_data)
        
        # Extract negative prompt
        negative_prompt = _extract_negative_prompt(original_prompt_data)

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

        def _try(body, suppress_errors=False):
            url=I2V_URL if mid else T2V_URL
            return self._post(url, body, suppress_error_logging=suppress_errors) or {}

        def _is_invalid(e: Exception)->bool:
            s=str(e).lower()
            return ("400" in str(e)) or ("invalid json" in s) or ("invalid argument" in s)
        
        def _is_auth_error(e: Exception)->bool:
            """Check if error is a 401 authentication error"""
            s=str(e).lower()
            return ("401" in str(e)) or ("unauthorized" in s) or ("authentication" in s and "invalid" in s)

        # 1) Try batch with model fallbacks
        # Suppress error logging during retries - only log final failure
        data=None; last_err=None
        for idx, mkey in enumerate(models):
            is_last_model = (idx == len(models) - 1)
            try:
                # Suppress error logging for intermediate attempts, allow logging on last attempt
                data=_try(_make_body(mkey, mid, copies), suppress_errors=(not is_last_model))
                last_err=None; break
            except Exception as e:
                last_err=e
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
                    for idx, mkey in enumerate(models):
                        is_last_model = (idx == len(models) - 1)
                        try:
                            # Suppress error logging for intermediate attempts
                            data=_try(_make_body(mkey, mid, copies), suppress_errors=(not is_last_model))
                            last_err=None; break
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
                for idx, mkey in enumerate(models):
                    is_last_model = (idx == len(models) - 1)
                    try:
                        # Suppress error logging for intermediate attempts
                        dat=_try(_make_body(mkey, mid, 1), suppress_errors=(not is_last_model))
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
        return len(job.get("operation_names",[]))

    def _wrap_ops(self, op_names: List[str], metadata: Optional[Dict[str, Dict]] = None)->dict:
        """
        Wrap operation names into the payload format for batch check.
        
        Args:
            op_names: List of operation names
            metadata: Optional dict mapping operation name to metadata (sceneId, status)
        
        Returns:
            Payload dict with operations list
        
        NOTE: Batch check requests do NOT include clientContext (verified from real Google Labs requests)
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

        # CRITICAL: Batch check does NOT include clientContext!
        # Only START requests (start_one, generate_videos_batch) include clientContext
        return {"operations": operations}

    def batch_check_operations(self, op_names: List[str], metadata: Optional[Dict[str, Dict]] = None)->Dict[str,Dict]:
        """
        Check status of video generation operations.
        
        Args:
            op_names: List of operation names to check
            metadata: Optional dict mapping operation name to metadata (sceneId, status)
        
        Returns:
            Dict mapping operation name to status info
        
        NOTE: This endpoint does NOT require clientContext (based on real Google Labs Flow requests)
        """
        if not op_names: return {}
        data=self._post(BATCH_CHECK_URL, self._wrap_ops(op_names, metadata)) or {}
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

        # Prepare prompt in correct format - convert structured JSON to text
        if isinstance(prompt, dict):
            # Convert dict to complete text prompt using the builder function
            prompt_text = _build_complete_prompt_text(prompt)
        elif isinstance(prompt, str):
            # Check if it's JSON that needs conversion
            try:
                parsed = json.loads(prompt)
                # If successful, it's JSON - convert to text format
                prompt_text = _build_complete_prompt_text(parsed)
            except:
                # Not JSON - it's plain text, use as-is
                prompt_text = prompt
        else:
            prompt_text = str(prompt)
        
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

# Backward compatibility
LabsClient = LabsFlowClient
