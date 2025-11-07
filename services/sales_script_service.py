# -*- coding: utf-8 -*-
from typing import Dict, Any, List, Optional
import datetime, json, re, logging, sys
from pathlib import Path
from services.gemini_client import GeminiClient, MissingAPIKey

logger = logging.getLogger(__name__)

def parse_llm_response_safe(response_text: str, source: str = "LLM") -> Dict[str, Any]:
    """
    Robust JSON parser with 5 fallback strategies to handle malformed LLM responses.
    
    Args:
        response_text: Raw text response from LLM
        source: Source identifier for logging (e.g., "SalesScript", "SocialMedia")
    
    Returns:
        Parsed JSON dictionary
        
    Raises:
        json.JSONDecodeError: If all parsing strategies fail
    """
    if not response_text or not response_text.strip():
        raise ValueError(f"Empty response from {source}")
    
    # Strategy 1: Direct JSON parse
    try:
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        logger.debug(f"{source} Strategy 1 failed (direct parse): {e}")
    
    # Strategy 2: Extract from markdown code blocks
    try:
        # Remove markdown code blocks (```json ... ``` or ``` ... ```)
        if "```" in response_text:
            # Extract content between code blocks
            pattern = r'```(?:json)?\s*(.*?)\s*```'
            matches = re.findall(pattern, response_text, re.DOTALL)
            if matches:
                cleaned = matches[0].strip()
                return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.debug(f"{source} Strategy 2 failed (markdown extraction): {e}")
    
    # Strategy 3: Fix common issues
    try:
        cleaned = response_text.strip()
        
        # Remove BOM if present
        if cleaned.startswith('\ufeff'):
            cleaned = cleaned[1:]
        
        # Remove invisible characters
        cleaned = cleaned.replace('\u200b', '')
        
        # Remove markdown code blocks
        cleaned = re.sub(r'```(?:json)?\s*', '', cleaned)
        cleaned = re.sub(r'\s*```', '', cleaned)
        
        # Replace single quotes with double quotes (simple approach)
        if "'" in cleaned and cleaned.count("'") > cleaned.count('"'):
            cleaned = cleaned.replace("'", '"')
        
        # Remove trailing commas before } or ]
        cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)
        
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.debug(f"{source} Strategy 3 failed (common fixes): {e}")
    
    # Strategy 4: Find JSON by boundaries
    try:
        # Find first { and last }
        start = response_text.find('{')
        end = response_text.rfind('}')
        
        if start != -1 and end != -1 and end > start:
            json_str = response_text[start:end+1]
            
            # Try to parse
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # Apply fixes from strategy 3
                json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
                return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.debug(f"{source} Strategy 4 failed (boundary extraction): {e}")
    
    # Strategy 5: Detailed error logging and re-raise
    logger.error(f"{source} All parsing strategies failed!")
    logger.error(f"Response length: {len(response_text)} characters")
    logger.error(f"First 500 chars: {response_text[:500]}")
    logger.error(f"Last 500 chars: {response_text[-500:]}")
    
    # Try one last time to get a better error message
    try:
        json.loads(response_text)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"{source} JSON parsing failed after all strategies. "
            f"Error at line {e.lineno}, column {e.colno}: {e.msg}",
            e.doc,
            e.pos
        )
    
    # Should not reach here
    raise ValueError(f"Unexpected parsing failure for {source}")

def _scene_count(total_sec:int)->int:
    return max(1, (int(total_sec)+8-1)//8)

def _json_sanitize(raw:str)->str:
    s = raw.find("{"); e = raw.rfind("}")
    if s != -1 and e != -1 and e > s:
        return raw[s:e+1]
    return raw

def _try_parse_json(raw:str)->Dict[str,Any]:
    """Parse JSON with robust error handling - delegates to parse_llm_response_safe"""
    raw = _json_sanitize(raw)
    return parse_llm_response_safe(raw, "SalesScript")

def _models_description(first_model_json:str)->str:
    return first_model_json if first_model_json else "No specific models described."

def _images_refs(has_model:bool, product_count:int)->str:
    out=[]
    if has_model: out.append("- An image is provided with source reference 'model-1'")
    for i in range(product_count): out.append(f"- An image is provided with source reference 'product-{i+1}'")
    return "\\n".join(out)

def _build_system_prompt(cfg:Dict[str,Any], sceneCount:int, models_json:str, product_count:int)->str:
    visualStyleString = cfg.get("image_style") or "Cinematic"
    idea = cfg.get("idea") or ""
    content = cfg.get("product_main") or ""
    duration = int(cfg.get("duration_sec") or 0)
    scriptStyle = cfg.get("script_style") or "story-telling"
    languageCode = cfg.get("speech_lang") or "vi"
    aspectRatio = cfg.get("ratio") or "9:16"
    voiceId = cfg.get("voice_id") or "ElevenLabs_VoiceID"
    imagesList = _images_refs(bool(models_json.strip()), product_count)

    return f"""
Objective: Create a detailed video script in JSON format. The output MUST be a valid JSON object with a "scenes" key containing an array of scene objects. The entire script, including all descriptions and voiceovers, MUST be in the language specified by the languageCode ({languageCode}).

Video Idea: {idea}
Core Content: {content}
Total Duration: Approximately {duration} seconds.
Script Style: {scriptStyle}
Visual Style: {visualStyleString}
Setting/Background Generation: You MUST invent a suitable and compelling setting/background for the video based on the idea, content, and characters. The setting must be consistent with the overall theme.
Models/Characters:
{_models_description(models_json)}

Reference Images:
{imagesList if imagesList else '- No reference images provided.'}

Task Instructions:
1.  Analyze all provided information.
2.  Break down the video into exactly {sceneCount} distinct scenes for the {duration}-second duration.
3.  For each scene, provide a concise description in the target language ({languageCode}).
4.  Create a separate voiceover field containing the dialogue/narration in the target language ({languageCode}). This field MUST include descriptive audio tags in square brackets to guide the text-to-speech model. The tags should also be in the target language if appropriate (e.g., for actions like [cười], [khóc]). This is a critical requirement.
    Available Audio Tags (Adapt these to the target language for the voiceover):
    {{
      "emotion_tags": {{"happy": "[vui vẻ]", "excited": "[hào hứng]", "sad": "[buồn bã]", "angry": "[tức giận]", "surprised": "[ngạc nhiên]", "disappointed": "[thất vọng]", "scared": "[sợ hãi]", "confident": "[tự tin]", "nervous": "[lo lắng]", "crying": "[khóc]", "laughs": "[cười]", "sighs": "[thở dài]"}},
      "tone_tags": {{"whispers": "[thì thầm]", "shouts": "[hét lên]", "sarcastic": "[mỉa mai]", "dramatic_tone": "[giọng kịch tính]", "reflective": "[suy tư]", "gentle_voice": "[giọng nhẹ nhàng]", "serious_tone": "[giọng nghiêm túc]"}},
      "style_tags": {{"storytelling": "[giọng kể chuyện]", "advertisement": "[giọng quảng cáo]"}},
      "timing_tags": {{"pause": "[ngừng lại]", "hesitates": "[do dự]", "rushed": "[vội vã]", "slows_down": "[chậm lại]"}},
      "action_tags": {{"clears_throat": "[hắng giọng]", "gasp": "[thở hổn hển]"}}
    }}
5.  The voicer field MUST be set to this exact value: {voiceId}.
6.  The languageCode field MUST be set to {languageCode}.
7.  Generate a detailed prompt object for a text-to-video AI model.
8.  The prompt.Output_Format.Structure must be filled with specific details (English):
    - character_details: reference image ('model-1') + EXACT clothing/hairstyle/gender from Models/Characters.
    - setting_details, key_action (may reference 'product-1'), camera_direction.
    - original_language_dialogue: copy top-level voiceover without audio tags (in {languageCode}).
    - dialogue_or_voiceover: English translation of the original dialogue.
9.  Audio tags appear ONLY in the top-level voiceover.
10. Output ONLY a valid JSON object. No extra text.

Output Format (Strictly Adhere):
{{
  "scenes": [
    {{
      "scene": 1,
      "description": "A short summary of the scene, in the target language.",
      "voiceover": "[emotion][pause] sample voiceover in target language.",
      "voicer": "{voiceId}",
      "languageCode": "{languageCode}",
      "prompt": {{
        "Objective": "Generate a short video clip for this scene.",
        "Persona": {{
          "Role": "Creative Video Director",
          "Tone": "Cinematic and evocative",
          "Knowledge_Level": "Expert in visual storytelling"
        }},
        "Task_Instructions": [
          "Create a video clip lasting approximately {{round({duration} / {sceneCount})}} seconds."
        ],
        "Constraints": [
          "Aspect ratio: {aspectRatio}",
          "Visual style: {visualStyleString}"
        ],
        "Input_Examples": [],
        "Output_Format": {{
          "Type": "JSON",
          "Structure": {{
            "character_details": "In English...",
            "setting_details": "In English...",
            "key_action": "In English...",
            "camera_direction": "In English...",
            "original_language_dialogue": "In {languageCode}, no audio tags.",
            "dialogue_or_voiceover": "In English translation."
          }}
        }}
      }}
    }}
  ]
}}
""".strip()

def _build_image_prompt(struct:Dict[str,Any], visualStyleString:str)->str:
    camera = (struct or {}).get("camera_direction","")
    setting = (struct or {}).get("setting_details","")
    character = (struct or {}).get("character_details","")
    action = (struct or {}).get("key_action","")
    return f"""Objective: Generate ONE SINGLE photorealistic, high-quality preview image for a video scene, meticulously following all instructions. The output MUST be a single, unified image.

--- SCENE COMPOSITION ---
- Overall Style: {visualStyleString}.
- Camera & Shot: {camera}.
- Setting: {setting}.
- Character & Clothing: {character}.
- Key Action: {action}.

--- ABSOLUTE, NON-NEGOTIABLE RULES ---
1. SINGLE IMAGE OUTPUT (CRITICAL): The output MUST be ONE single, coherent image. NO collages, grids, split-screens, or multi-panel images are allowed under any circumstances.
2. CHARACTER FIDELITY: The character's clothing, hairstyle, and gender MUST PERFECTLY and EXACTLY match the description provided in the scene composition. This OVERRIDES ALL other instructions.
3. NO TEXT OR WATERMARKS: The image MUST be 100% free of any text, letters, words, subtitles, captions, logos, watermarks, or any form of typography.

--- NEGATIVE PROMPT (Elements to strictly AVOID) ---
- collage, grid, multiple panels, multi-panel, split screen, diptych, triptych, multiple frames.
- text, words, letters, logos, watermarks, typography, signatures, labels, captions, subtitles.
- cartoon, illustration, drawing, sketch, anime, 3d render.
""".strip()

def _build_social_media_prompt(cfg: Dict[str, Any], outline_vi: str) -> str:
    """Build prompt for generating social media content"""
    platform = cfg.get("social_platform", "TikTok")
    language = cfg.get("speech_lang", "vi")
    product = cfg.get("product_main", "")
    idea = cfg.get("idea", "")
    
    return f"""Create 3 different social media content versions for {platform}.

Video Idea: {idea}
Product/Content: {product}
Video Outline: {outline_vi}
Language: {language}
Platform: {platform}

For EACH of the 3 versions, provide:
1. caption: Engaging post caption (2-3 lines, use emojis)
2. hashtags: Array of relevant hashtags (5-8 tags)
3. thumbnail_prompt: Prompt for 9:16 thumbnail image generation
4. thumbnail_text_overlay: Short catchy text to overlay on thumbnail (ALL CAPS, max 25 chars)
5. platform: "{platform}"
6. language: "{language}"

Output MUST be valid JSON with this structure:
{{
  "versions": [
    {{
      "caption": "...",
      "hashtags": ["#tag1", "#tag2"],
      "thumbnail_prompt": "9:16 vertical image...",
      "thumbnail_text_overlay": "SHORT TEXT!",
      "platform": "{platform}",
      "language": "{language}"
    }}
  ]
}}"""

def build_outline(cfg:Dict[str,Any])->Dict[str,Any]:
    """
    Build script outline with scenes, social media, and character bible.
    This is the main entry point for script generation.
    
    Args:
        cfg: Configuration dict with video parameters
        
    Returns:
        Dict containing script_json, scenes, social_media, etc.
    """
    sceneCount = _scene_count(int(cfg.get("duration_sec") or 0))
    models_json = cfg.get("first_model_json") or ""
    product_count = int(cfg.get("product_count") or 0)
    
    # Log language configuration for debugging
    speech_lang = cfg.get("speech_lang", "vi")
    voice_id = cfg.get("voice_id", "")
    logger.info(f"build_outline: speech_lang={speech_lang}, voice_id={voice_id}")
    
    client = GeminiClient()
    sys_prompt = _build_system_prompt(cfg, sceneCount, models_json, product_count)
    raw = client.generate(sys_prompt, "Return ONLY the JSON object. No prose.", timeout=240)
    script_json = _try_parse_json(raw)

    scenes = script_json.get("scenes", [])
    if not isinstance(scenes, list): scenes = []
    if len(scenes) > sceneCount: scenes = scenes[:sceneCount]
    if len(scenes) < sceneCount:
        base_lang = cfg.get("speech_lang") or "vi"
        voiceId = cfg.get("voice_id") or "ElevenLabs_VoiceID"
        for i in range(len(scenes)+1, sceneCount+1):
            scenes.append({"scene": i, "description": "", "voiceover": "", "voicer": voiceId, "languageCode": base_lang,
                           "prompt":{"Output_Format":{"Structure": {"character_details":"","setting_details":"","key_action":"","camera_direction":"","original_language_dialogue":"","dialogue_or_voiceover":""}}}})
    script_json["scenes"] = scenes

    visualStyleString = cfg.get("image_style") or "Cinematic"
    outline_scenes = []
    outline_vi = ""
    for sc in scenes:
        struct = (((sc or {}).get("prompt",{}) or {}).get("Output_Format",{}) or {}).get("Structure",{}) or {}
        img_prompt = _build_image_prompt(struct, visualStyleString)
        outline_scenes.append({
            "index": sc.get("scene"),
            "title": f"Cảnh {sc.get('scene')}",
            "desc": sc.get("description",""),
            "speech": sc.get("voiceover",""),
            "emotion": struct.get("emotion", ""),
            "duration": float(cfg.get("duration_sec", 32)) / sceneCount,
            "prompt_video": json.dumps(sc.get("prompt",{}), ensure_ascii=False),
            "prompt_image": img_prompt
        })
        outline_vi += f"Cảnh {sc.get('scene')}: {sc.get('description', '')}\n"
    
    # Generate social media content (3 versions)
    social_media = {"versions": []}
    try:
        social_prompt = _build_social_media_prompt(cfg, outline_vi)
        social_raw = client.generate(social_prompt, "Return ONLY valid JSON.", timeout=120)
        social_json = _try_parse_json(social_raw)
        social_media = social_json if "versions" in social_json else {"versions": []}
    except Exception as e:
        logger.warning(f"Failed to generate social media content: {e}")
        # Fallback: create default versions
        platform = cfg.get("social_platform", "TikTok")
        language = cfg.get("speech_lang", "vi")
        social_media = {
            "versions": [
                {
                    "caption": "🎬 Video mới cực hay! Xem ngay!",
                    "hashtags": ["#viral", "#trending"],
                    "thumbnail_prompt": "9:16 vertical image with bright colors",
                    "thumbnail_text_overlay": "XEM NGAY!",
                    "platform": platform,
                    "language": language
                }
            ]
        }
    
    # Generate Character Bible for visual consistency
    character_bible = None
    character_bible_text = ""
    try:
        from services.google.character_bible import create_character_bible, format_character_bible_for_display
        # Extract character info from script if available
        existing_bible = script_json.get("character_bible", [])
        idea = cfg.get("idea", "")
        content = cfg.get("product_main", "")
        video_concept = f"{idea} {content}"
        screenplay = json.dumps(script_json, ensure_ascii=False)
        
        # Create character bible
        bible = create_character_bible(video_concept, screenplay, existing_bible)
        character_bible = bible
        character_bible_text = format_character_bible_for_display(bible)
    except Exception as e:
        logger.warning(f"Failed to generate character bible: {e}")
        character_bible_text = "(Failed to generate character bible)"

    return {
        "meta": {"created_at": datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), "scenes": len(outline_scenes),
                 "ratio": cfg.get("ratio") or "9:16"},
        "script_json": script_json,
        "scenes": outline_scenes,
        "social_media": social_media,
        "outline_vi": outline_vi,
        "screenplay_text": json.dumps(script_json, ensure_ascii=False, indent=2),
        "character_bible": character_bible,
        "character_bible_text": character_bible_text
    }


def generate_thumbnail_with_text(base_image_path: str, text: str, output_path: str) -> None:
    """
    Generate thumbnail with text overlay using Pillow
    
    Args:
        base_image_path: Path to base image
        text: Text to overlay (will be wrapped)
        output_path: Path to save output image
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        raise ImportError("Pillow is required. Install with: pip install Pillow>=10.0.0")
    
    # Open base image
    img = Image.open(base_image_path)
    
    # Convert to RGB if needed
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Create drawing context
    draw = ImageDraw.Draw(img)
    
    # Try to load a bold font, fallback to default
    font_size = max(40, img.height // 20)
    try:
        # Try common font locations
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:\\Windows\\Fonts\\arialbd.ttf"
        ]
        font = None
        for fp in font_paths:
            if Path(fp).exists():
                font = ImageFont.truetype(fp, font_size)
                break
        if font is None:
            font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()
    
    # Text positioning - center top with semi-transparent background
    text = text.upper()
    
    # Calculate text bounding box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Position at top center
    x = (img.width - text_width) // 2
    y = img.height // 8
    
    # Draw semi-transparent background
    padding = 20
    bg_bbox = [x - padding, y - padding, x + text_width + padding, y + text_height + padding]
    
    # Create overlay for semi-transparent background
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle(bg_bbox, fill=(0, 0, 0, 180))
    
    # Composite overlay
    img = img.convert('RGBA')
    img = Image.alpha_composite(img, overlay)
    img = img.convert('RGB')
    
    # Draw text
    draw = ImageDraw.Draw(img)
    draw.text((x, y), text, font=font, fill=(255, 255, 255))
    
    # Save
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    img.save(output_path, quality=95)
