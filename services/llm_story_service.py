# -*- coding: utf-8 -*-
import os, json, requests
from services.core.key_manager import get_key, get_all_keys, refresh
from services.core.api_key_rotator import APIKeyRotator, APIKeyRotationError

def _load_keys():
    """Load keys using unified key manager"""
    gk = get_key('google')
    ok = get_key('openai')
    return gk, ok

def _n_scenes(total_seconds:int):
    total=max(3, int(total_seconds or 30))
    n=max(1, (total+7)//8)
    per=[8]*(n-1)+[max(1,total-8*(n-1))]
    return n, per

def _mode_from_duration(total_seconds:int):
    return "SHORT" if int(total_seconds) <= 7*60 else "LONG"

# Language code to display name mapping
LANGUAGE_NAMES = {
    'vi': 'Vietnamese (Tiếng Việt)',
    'en': 'English',
    'ja': 'Japanese (日本語)',
    'ko': 'Korean (한국어)',
    'zh': 'Chinese (中文)',
    'fr': 'French (Français)',
    'de': 'German (Deutsch)',
    'es': 'Spanish (Español)',
    'ru': 'Russian (Русский)',
    'th': 'Thai (ภาษาไทย)',
    'id': 'Indonesian (Bahasa Indonesia)'
}

def _schema_prompt(idea, style_vi, out_lang, n, per, mode):
    # Get target language display name
    target_language = LANGUAGE_NAMES.get(out_lang, 'Vietnamese (Tiếng Việt)')
    
    # Build language instruction
    language_instruction = f"""
IMPORTANT LANGUAGE REQUIREMENT:
- All narration, dialogue, and voice-over MUST be in {target_language}
- All scene descriptions should match the cultural context of {target_language}
- Do NOT mix languages unless specifically requested
"""
    
    # Detect if user provided detailed screenplay vs just idea
    # Indicators: SCENE, ACT, INT./EXT., character profiles, dàn ý, kịch bản, screenplay
    idea_lower = (idea or "").lower()
    has_screenplay_markers = any(marker in idea_lower for marker in [
        'scene ', 'act 1', 'act 2', 'act 3', 'int.', 'ext.', 
        'kịch bản', 'screenplay', 'dàn ý', 'hồ sơ nhân vật',
        'fade in', 'fade out', 'close up', 'cut to'
    ])
    
    # Adjust instructions based on input type
    if has_screenplay_markers:
        input_type_instruction = """
**QUAN TRỌNG**: Người dùng đã cung cấp kịch bản CHI TIẾT. Nhiệm vụ của bạn:
1. TUÂN THỦ chặt chẽ nội dung, nhân vật, và cấu trúc câu chuyện đã cho
2. Chỉ điều chỉnh nhẹ để phù hợp format video (visual prompts, timing)
3. GIỮ NGUYÊN ý tưởng gốc, tính cách nhân vật, và luồng cảm xúc
4. KHÔNG sáng tạo lại hoặc thay đổi concept cốt lõi
"""
        base_role = f"""
Bạn là **Biên kịch Chuyển đổi Format AI**. Nhận **kịch bản chi tiết** và chuyển đổi thành **format video tối ưu** mà KHÔNG thay đổi nội dung gốc.
Mục tiêu: GIỮ NGUYÊN câu chuyện và nhân vật, chỉ tối ưu hóa cho video format."""
    else:
        input_type_instruction = ""
        base_role = f"""
Bạn là **Biên kịch Đa năng AI Cao cấp**. Nhận **ý tưởng thô sơ** và phát triển thành **kịch bản phim/video SIÊU HẤP DẪN**.
Mục tiêu: TẠO NỘI DUNG VIRAL với engagement cao, giữ chân người xem từ giây đầu tiên."""
    
    base_rules = f"""
{base_role}

{input_type_instruction}
{language_instruction}

═══════════════════════════════════════════════════════════════
🎬 NGUYÊN TẮC HẤP DẪN TUYỆT ĐỐI
═══════════════════════════════════════════════════════════════

**1. HOOK SIÊU MẠNH (3 giây đầu):**
- Bắt đầu bằng: Hành động kịch tính / Câu hỏi gây sốc / Twist bất ngờ / Cảnh dramatic
- TUYỆT ĐỐI KHÔNG BẮT ĐẦU bằng giới thiệu chậm chạp, mở đầu nhàm chán
- Ví dụ ĐÚNG: "Tôi vừa mất 10 triệu trong 3 phút..." / "Điều này thay đổi tất cả..."
- Ví dụ SAI: "Xin chào mọi người hôm nay tôi sẽ kể..."

**2. EMOTIONAL ROLLERCOASTER:**
- Mỗi cảnh phải có biến động cảm xúc rõ rệt: Tension → Relief → Surprise → Joy/Sadness
- Tránh cảm xúc phẳng lặng, monotone
- Sử dụng: Contrast mạnh (happy↔sad, hope↔despair, calm↔chaos)

**3. PACING & RHYTHM:**
- SHORT format: Tempo NHANH, mỗi cảnh 3-8s, chuyển cảnh dynamic
- LONG format: Có điểm hồi hộp (plot twist) ở giữa (midpoint), không để người xem chán
- Mỗi 15-20s phải có một "mini-hook" để giữ attention

**4. VISUAL STORYTELLING:**
- Mỗi scene PHẢI có hành động cụ thể, KHÔNG chỉ là talking heads
- Camera movements tạo năng lượng: slow zoom-in (tension), quick cuts (action), tracking shot (journey)
- Lighting mood: warm (cozy), cold blue (mystery), high contrast (drama)

**5. CINEMATIC TECHNIQUES:**
- Sử dụng: Slow motion (dramatic moments), Quick montage (time passage), POV shots (immersion)
- Sound design hints: "silence breaks", "music swells", "sudden sound"
- Visual metaphors: rain = sadness, sunrise = hope, shadows = mystery

═══════════════════════════════════════════════════════════════
👤 CHARACTER BIBLE (2–4 nhân vật sống động)
═══════════════════════════════════════════════════════════════

Mỗi nhân vật PHẢI:
- **key_trait**: Tính cách cốt lõi nhất quán (ví dụ: "Dũng cảm nhưng bốc đồng", "Thông minh nhưng nghi ngờ")
- **motivation**: Động lực sâu thẳm, thúc đẩy hành động (ví dụ: "Chứng minh bản thân", "Bảo vệ người thân")
- **default_behavior**: Phản ứng tự nhiên khi stress (ví dụ: "Đùa cợt để giấu lo lắng", "Im lặng suy nghĩ")
- **visual_identity**: Đặc điểm nhận diện (ví dụ: "Áo da đen, scar trên mặt", "Luôn mang kính râm")
- **archetype**: Hero/Mentor/Trickster/Rebel (theo 12 archetypes)
- **fatal_flaw**: Khuyết điểm dẫn đến conflict (ví dụ: "Quá tự tin", "Không tin người")
- **goal_external**: Mục tiêu hữu hình (ví dụ: "Tìm kho báu", "Giải cứu ai đó")
- **goal_internal**: Biến đổi nội tâm (ví dụ: "Học cách tin tưởng", "Chấp nhận quá khứ")

**Đồng nhất tuyến:** Hành động = Hệ quả từ key_trait + motivation. Phát triển từ từ qua các Act.

═══════════════════════════════════════════════════════════════
🎯 CẤU TRÚC THEO PHONG CÁCH
═══════════════════════════════════════════════════════════════

**SHORT** (≤7'): TikTok/Reels style - VIRAL FIRST
- Act 1 (10%): Hook devastating trong 3s đầu + Setup nhanh
- Act 2 (70%): Xung đột leo thang + Mini-twists liên tục + Emotion peaks
- Act 3 (20%): Resolution + Twist cuối hoặc Call-to-action mạnh
- Nhịp: FAST, dynamic, không thời gian chết

**LONG** (>7'): YouTube/Cinematic - DEPTH & ENGAGEMENT
- Act 1 (25%): Hook + World building + Character intro + Inciting incident
- Act 2A (25%): Rising action + Complications + Emotional depth
- **MIDPOINT (5%)**: Major revelation/twist thay đổi mọi thứ
- Act 2B (25%): Pressure tăng + Darkest moment + Character growth
- Act 3 (20%): Climax + Resolution + Satisfying ending + Message
- Nhịp: Varied, có breathing room, nhưng luôn engaging

═══════════════════════════════════════════════════════════════
✨ YÊU CẦU ĐẶC BIỆT
═══════════════════════════════════════════════════════════════

1. **Scene Descriptions** phải VISUAL & SPECIFIC:
   - ✗ SAI: "Nhân vật buồn trong phòng"
   - ✓ ĐÚNG: "Close-up: Tears stream down face, backlit by window, rain outside, slow zoom in"

2. **Dialogue** phải TỰ NHIÊN & IMPACTFUL:
   - Tránh exposition dump
   - Mỗi câu thoại phải reveal character hoặc advance plot
   - Sử dụng subtext (ý nghĩa ẩn)

3. **Visual Variety**:
   - Alternate: Wide shots ↔ Close-ups
   - Mix: Static shots + Camera movements
   - Lighting: Thay đổi mood qua từng cảnh

4. **Payoff Setup**:
   - Foreshadowing sớm cho twist sau
   - Chekhov's Gun: Detail đầu phải có ý nghĩa sau
   - Callback: Reference lại moments trước

═══════════════════════════════════════════════════════════════

**NHỚ:** Mục tiêu cuối cùng = Người xem KHÔNG THỂ rời mắt + Muốn share + Cảm xúc mạnh sau khi xem
""".strip()

    schema = f"""
Trả về **JSON hợp lệ** theo schema EXACT (không thêm ký tự ngoài JSON):

{{
  "title_vi": "Tiêu đề HẤP DẪN, gây tò mò (VI)",
  "title_tgt": "Compelling title in {target_language}",
  "hook_summary": "Mô tả hook 3s đầu - điều gì khiến người xem PHẢI xem tiếp?",
  "character_bible": [{{"name":"","role":"","key_trait":"","motivation":"","default_behavior":"","visual_identity":"","archetype":"","fatal_flaw":"","goal_external":"","goal_internal":""}}],
  "character_bible_tgt": [{{"name":"","role":"","key_trait":"","motivation":"","default_behavior":"","visual_identity":"","archetype":"","fatal_flaw":"","goal_external":"","goal_internal":""}}],
  "outline_vi": "Dàn ý theo {mode}: ACT structure + key emotional beats + major plot points",
  "outline_tgt": "Outline in {target_language}",
  "screenplay_vi": "Screenplay chi tiết: INT./EXT. LOCATION - TIME\\nACTION (visual, cinematic)\\nDIALOGUE\\n- Bao gồm camera angles, lighting, mood, transitions",
  "screenplay_tgt": "Full screenplay in {target_language}",
  "emotional_arc": "Cung cảm xúc của story: [Start emotion] → [Peaks & Valleys] → [End emotion]",
  "scenes": [
    {{
      "prompt_vi":"Visual prompt SIÊU CỤ THỂ (action, lighting, camera, mood, characters) - 2-3 câu cinematic",
      "prompt_tgt":"Detailed visual prompt in {target_language}",
      "duration": 8,
      "characters": ["Nhân vật xuất hiện"],
      "location": "Location cụ thể",
      "time_of_day": "Day/Night/Golden hour/etc",
      "camera_shot": "Wide/Close-up/POV/Tracking/etc + movement",
      "lighting_mood": "Bright/Dark/Warm/Cold/High-contrast/etc",
      "emotion": "Cảm xúc chủ đạo của scene",
      "story_beat": "Plot point: Setup/Rising action/Twist/Climax/Resolution",
      "dialogues": [
        {{"speaker":"Tên","text_vi":"Thoại tự nhiên, có subtext","text_tgt":"Natural line in {target_language}","emotion":"angry/sad/happy/etc"}}
      ],
      "visual_notes": "Ghi chú thêm về visuals: props, colors, symbolism, transitions"
    }}
  ]
}}

**CHÚ Ý:** 
- Cảnh 1 PHẢI là HOOK MẠNH (action/shocking/intriguing)
- Prompts PHẢI visual & cinematic (tránh abstract)
- Mỗi scene có emotion & story beat rõ ràng
""".strip()
    
    # Adjust input label based on detected type
    input_label = "Kịch bản chi tiết" if has_screenplay_markers else "Ý tưởng thô"

    return f"""{base_rules}

ĐẦU VÀO:
- {input_label}: "{idea}"
- Phong cách: "{style_vi}"
- Chế độ: {mode}
- Số cảnh kỹ thuật: {n} (mỗi cảnh 8s; cảnh cuối {per[-1]}s)
- Ngôn ngữ đích: {target_language}

{schema}
"""

def _call_openai(prompt, api_key, model="gpt-4-turbo"):
    """FIXED: Changed from gpt-5 to gpt-4-turbo"""
    url="https://api.openai.com/v1/chat/completions"
    headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"}
    data={
        "model": model,
        "messages":[
            {"role":"system","content":"You output strictly JSON when asked."},
            {"role":"user","content": prompt}
        ],
        "response_format":{"type":"json_object"},
        "temperature":0.9
    }
    r=requests.post(url,headers=headers,json=data,timeout=240); r.raise_for_status()
    txt=r.json()["choices"][0]["message"]["content"]
    return json.loads(txt)

def _call_gemini(prompt, api_key, model="gemini-2.5-flash"):
    """
    Call Gemini API with retry logic for 503 errors
    
    Strategy:
    1. Try primary API key
    2. If 503 error, try up to 2 additional keys from config
    3. Add exponential backoff (1s, 2s, 4s)
    """
    from services.core.api_config import gemini_text_endpoint
    from services.core.key_manager import get_all_keys
    import time
    
    # Build key rotation list
    keys = [api_key]
    all_keys = get_all_keys('google')
    keys.extend([k for k in all_keys if k != api_key])
    
    last_error = None
    
    for attempt, key in enumerate(keys[:3]):  # Try up to 3 keys
        try:
            # Build endpoint
            url = gemini_text_endpoint(key) if model == "gemini-2.5-flash" else \
                  f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            
            headers = {"Content-Type": "application/json"}
            data = {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.9, "response_mime_type": "application/json"}
            }
            
            # Make request
            r = requests.post(url, headers=headers, json=data, timeout=240)
            
            # Check for 503 specifically
            if r.status_code == 503:
                last_error = requests.HTTPError(f"503 Service Unavailable (Key attempt {attempt+1})", response=r)
                if attempt < 2:  # Don't sleep on last attempt
                    backoff = 2 ** attempt  # 1s, 2s, 4s
                    print(f"[WARN] Gemini 503 error, retrying in {backoff}s with next key...")
                    time.sleep(backoff)
                continue  # Try next key
            
            # Raise for other HTTP errors
            r.raise_for_status()
            
            # Parse response
            out = r.json()
            txt = out["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(txt)
            
        except requests.exceptions.HTTPError as e:
            # Only retry 503 errors
            if hasattr(e, 'response') and e.response.status_code == 503:
                last_error = e
                if attempt < 2:
                    backoff = 2 ** attempt
                    print(f"[WARN] HTTP 503, trying key {attempt+2}/{min(3, len(keys))} in {backoff}s...")
                    time.sleep(backoff)
                continue
            else:
                # Other HTTP errors (429, 400, 401, etc.) - raise immediately
                raise
                
        except Exception as e:
            # Non-HTTP errors - raise immediately
            last_error = e
            raise
    
    # All retries exhausted
    if last_error:
        raise RuntimeError(f"Gemini API failed after {min(3, len(keys))} attempts: {last_error}")
    else:
        raise RuntimeError("Gemini API failed with unknown error")

def _calculate_text_similarity(text1, text2):
    """
    Calculate similarity between two texts using Jaccard similarity algorithm.
    
    Jaccard similarity = |intersection| / |union| of word sets
    Returns a value between 0.0 (completely different) and 1.0 (identical).
    
    Args:
        text1: First text string
        text2: Second text string
    
    Returns:
        float: Similarity score between 0.0 and 1.0
    """
    if not text1 or not text2:
        return 0.0
    
    # Normalize: lowercase and split into words
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    # Jaccard similarity: intersection / union
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    
    return intersection / union if union > 0 else 0.0

def _validate_scene_uniqueness(scenes, similarity_threshold=0.8):
    """
    Validate that scenes are unique (not duplicates).
    Checks both prompt_vi and prompt_tgt for similarity.
    
    Args:
        scenes: List of scene dicts with prompt_vi/prompt_tgt
        similarity_threshold: Maximum allowed similarity (default 0.8 = 80%)
    
    Returns:
        List of duplicate pairs found: [(scene1_idx, scene2_idx, similarity), ...]
    """
    duplicates = []
    
    for i in range(len(scenes)):
        for j in range(i + 1, len(scenes)):
            scene1 = scenes[i]
            scene2 = scenes[j]
            
            # Check both Vietnamese and target prompts
            prompt1_vi = scene1.get("prompt_vi", "")
            prompt2_vi = scene2.get("prompt_vi", "")
            prompt1_tgt = scene1.get("prompt_tgt", "")
            prompt2_tgt = scene2.get("prompt_tgt", "")
            
            # Calculate similarity for both language versions
            sim_vi = _calculate_text_similarity(prompt1_vi, prompt2_vi)
            sim_tgt = _calculate_text_similarity(prompt1_tgt, prompt2_tgt)
            
            # Use the higher similarity score
            max_sim = max(sim_vi, sim_tgt)
            
            if max_sim >= similarity_threshold:
                duplicates.append((i + 1, j + 1, max_sim))  # 1-based indexing for display
    
    return duplicates

def _enforce_character_consistency(scenes, character_bible):
    """
    Store character visual identity details for reference.
    Character consistency is now handled via the character_details field in build_prompt_json(),
    not by modifying the scene prompts (which would cause TTS to read technical info).
    
    This function now only validates that character_bible data exists,
    without modifying scene prompts.
    
    Args:
        scenes: List of scene dicts
        character_bible: List of character dicts with visual_identity field
    
    Returns:
        Scenes unchanged (character consistency handled elsewhere)
    """
    # BUG FIX: Do NOT modify prompt_vi or prompt_tgt
    # Character consistency is handled by build_prompt_json() via character_details field
    # Modifying prompts here causes "CHARACTER CONSISTENCY: ..." to appear in voiceover text
    return scenes

def generate_script(idea, style, duration_seconds, provider='Gemini 2.5', api_key=None, output_lang='vi', domain=None, topic=None, voice_config=None):
    """
    Generate video script with optional domain/topic expertise and voice settings
    
    Args:
        idea: Video idea/concept
        style: Video style
        duration_seconds: Total duration
        provider: LLM provider (Gemini/OpenAI)
        api_key: Optional API key
        output_lang: Output language code
        domain: Optional domain expertise (e.g., "Marketing & Branding")
        topic: Optional topic within domain (e.g., "Giới thiệu sản phẩm")
        voice_config: Optional voice configuration dict with provider, voice_id, language_code
    
    Returns:
        Script data dict with scenes, character_bible, etc.
    """
    gk, ok=_load_keys()
    n, per = _n_scenes(duration_seconds)
    mode = _mode_from_duration(duration_seconds)
    
    # Build base prompt
    prompt=_schema_prompt(idea=idea, style_vi=style, out_lang=output_lang, n=n, per=per, mode=mode)
    
    # Prepend expert intro if domain/topic selected
    if domain and topic:
        try:
            from services.domain_prompts import build_expert_intro
            # Map language code to vi/en for domain prompts
            prompt_lang = "vi" if output_lang == "vi" else "en"
            expert_intro = build_expert_intro(domain, topic, prompt_lang)
            prompt = f"{expert_intro}\n\n{prompt}"
        except Exception as e:
            # Log but don't fail if domain prompt loading fails
            print(f"[WARN] Could not load domain prompt: {e}")
    
    # Call LLM
    if provider.lower().startswith("gemini"):
        key=api_key or gk
        if not key: raise RuntimeError("Chưa cấu hình Google API Key cho Gemini.")
        res=_call_gemini(prompt,key,"gemini-2.5-flash")
    else:
        key=api_key or ok
        if not key: raise RuntimeError("Chưa cấu hình OpenAI API Key cho GPT-4 Turbo.")
        # FIXED: Use gpt-4-turbo instead of gpt-5
        res=_call_openai(prompt,key,"gpt-4-turbo")
    if "scenes" not in res: raise RuntimeError("LLM không trả về đúng schema.")
    
    # ISSUE #1 FIX: Validate scene uniqueness
    scenes = res.get("scenes", [])
    duplicates = _validate_scene_uniqueness(scenes, similarity_threshold=0.8)
    if duplicates:
        dup_msg = ", ".join([f"Scene {i} & {j} ({sim*100:.0f}% similar)" for i, j, sim in duplicates])
        print(f"[WARN] Duplicate scenes detected: {dup_msg}")
        # Note: We warn but don't fail - the UI can decide how to handle this
    
    # ISSUE #2 FIX: Enforce character consistency
    character_bible = res.get("character_bible", [])
    if character_bible:
        res["scenes"] = _enforce_character_consistency(scenes, character_bible)
    
    # Store voice configuration in result for consistency
    if voice_config:
        res["voice_config"] = voice_config
    
    # ép durations
    for i,d in enumerate(per):
        if i < len(res["scenes"]): res["scenes"][i]["duration"]=int(d)
    return res


def generate_social_media(script_data, provider='Gemini 2.5', api_key=None):
    """
    Generate social media content in 3 different tones
    
    Args:
        script_data: Script data dictionary with title, outline, screenplay
        provider: LLM provider (Gemini/OpenAI)
        api_key: Optional API key
    
    Returns:
        Dictionary with 3 social media versions (casual, professional, funny)
    """
    gk, ok = _load_keys()
    
    # Extract key elements from script
    title = script_data.get("title_vi") or script_data.get("title_tgt", "")
    outline = script_data.get("outline_vi") or script_data.get("outline_tgt", "")
    screenplay = script_data.get("screenplay_vi") or script_data.get("screenplay_tgt", "")
    
    # Build prompt
    prompt = f"""Bạn là chuyên gia Social Media Marketing. Dựa trên kịch bản video sau, hãy tạo 3 phiên bản nội dung mạng xã hội với các tone khác nhau.

**KỊCH BẢN VIDEO:**
Tiêu đề: {title}
Dàn ý: {outline}

**YÊU CẦU:**
Tạo 3 phiên bản post cho mạng xã hội, mỗi phiên bản bao gồm:
1. Title (tiêu đề hấp dẫn)
2. Description (mô tả chi tiết 2-3 câu)
3. Hashtags (5-10 hashtags phù hợp)
4. CTA (Call-to-action mạnh mẽ)
5. Best posting time (thời gian đăng tối ưu)

**3 PHIÊN BẢN:**
- Version 1: Casual/Friendly (TikTok/YouTube Shorts) - Tone thân mật, gần gũi, emoji nhiều
- Version 2: Professional (LinkedIn/Facebook) - Tone chuyên nghiệp, uy tín, giá trị cao
- Version 3: Funny/Engaging (TikTok/Instagram Reels) - Tone hài hước, vui nhộn, viral

Trả về JSON với format:
{{
  "casual": {{
    "title": "...",
    "description": "...",
    "hashtags": ["#tag1", "#tag2", ...],
    "cta": "...",
    "best_time": "...",
    "platform": "TikTok/YouTube Shorts"
  }},
  "professional": {{
    "title": "...",
    "description": "...",
    "hashtags": ["#tag1", "#tag2", ...],
    "cta": "...",
    "best_time": "...",
    "platform": "LinkedIn/Facebook"
  }},
  "funny": {{
    "title": "...",
    "description": "...",
    "hashtags": ["#tag1", "#tag2", ...],
    "cta": "...",
    "best_time": "...",
    "platform": "TikTok/Instagram Reels"
  }}
}}
"""
    
    # Call LLM
    if provider.lower().startswith("gemini"):
        key = api_key or gk
        if not key:
            raise RuntimeError("Chưa cấu hình Google API Key cho Gemini.")
        res = _call_gemini(prompt, key, "gemini-2.5-flash")
    else:
        key = api_key or ok
        if not key:
            raise RuntimeError("Chưa cấu hình OpenAI API Key cho GPT-4 Turbo.")
        res = _call_openai(prompt, key, "gpt-4-turbo")
    
    return res


def generate_thumbnail_design(script_data, provider='Gemini 2.5', api_key=None):
    """
    Generate detailed thumbnail design specifications
    
    Args:
        script_data: Script data dictionary with title, outline, screenplay
        provider: LLM provider (Gemini/OpenAI)
        api_key: Optional API key
    
    Returns:
        Dictionary with thumbnail design specifications
    """
    gk, ok = _load_keys()
    
    # Extract key elements from script
    title = script_data.get("title_vi") or script_data.get("title_tgt", "")
    outline = script_data.get("outline_vi") or script_data.get("outline_tgt", "")
    character_bible = script_data.get("character_bible", [])
    
    # Build character summary
    char_summary = ""
    if character_bible:
        char_summary = "Nhân vật chính:\n"
        for char in character_bible[:3]:  # Top 3 characters
            char_summary += f"- {char.get('name', 'Unknown')}: {char.get('visual_identity', 'N/A')}\n"
    
    # Build prompt
    prompt = f"""Bạn là chuyên gia Thiết kế Thumbnail cho YouTube/TikTok. Dựa trên kịch bản video sau, hãy tạo specifications chi tiết cho thumbnail.

**KỊCH BẢN VIDEO:**
Tiêu đề: {title}
Dàn ý: {outline}
{char_summary}

**YÊU CẦU:**
Tạo specifications chi tiết cho thumbnail bao gồm:
1. Concept (ý tưởng tổng thể)
2. Color Palette (bảng màu với mã hex, 3-5 màu)
3. Typography (text overlay, font, size, effects)
4. Layout (composition, focal point, rule of thirds)
5. Visual Elements (các yếu tố cần có: người, vật, background)
6. Style Guide (phong cách tổng thể: photorealistic, cartoon, minimalist...)

Thumbnail phải:
- Nổi bật trong feed (high contrast, bold colors)
- Gây tò mò (create curiosity gap)
- Dễ đọc trên mobile (text lớn, rõ ràng)
- Phù hợp với nội dung video

Trả về JSON với format:
{{
  "concept": "Ý tưởng tổng thể cho thumbnail...",
  "color_palette": [
    {{"name": "Primary", "hex": "#FF5733", "usage": "Background"}},
    {{"name": "Accent", "hex": "#33FF57", "usage": "Text highlight"}},
    ...
  ],
  "typography": {{
    "main_text": "Text chính trên thumbnail",
    "font_family": "Tên font (ví dụ: Montserrat Bold)",
    "font_size": "72-96pt",
    "effects": "Drop shadow, outline, glow..."
  }},
  "layout": {{
    "composition": "Mô tả cách bố trí (ví dụ: Character trái, text phải)",
    "focal_point": "Điểm nhấn chính",
    "rule_of_thirds": "Sử dụng rule of thirds như thế nào"
  }},
  "visual_elements": {{
    "subject": "Nhân vật/Chủ thể chính",
    "props": ["Vật dụng 1", "Vật dụng 2"],
    "background": "Mô tả background",
    "effects": ["Effect 1", "Effect 2"]
  }},
  "style_guide": "Phong cách tổng thể (ví dụ: Bold and dramatic with high contrast...)"
}}
"""
    
    # Call LLM
    if provider.lower().startswith("gemini"):
        key = api_key or gk
        if not key:
            raise RuntimeError("Chưa cấu hình Google API Key cho Gemini.")
        res = _call_gemini(prompt, key, "gemini-2.5-flash")
    else:
        key = api_key or ok
        if not key:
            raise RuntimeError("Chưa cấu hình OpenAI API Key cho GPT-4 Turbo.")
        res = _call_openai(prompt, key, "gpt-4-turbo")
    
    return res