# -*- coding: utf-8 -*-
import json, requests
from services.core.key_manager import get_key

# Constants for validation
IDEA_RELEVANCE_THRESHOLD = 0.15  # Minimum word overlap ratio (15%)
MIN_WORD_LENGTH = 3  # Minimum word length for relevance checking (filters out words with <3 chars)
MAX_IDEA_DISPLAY_LENGTH = 100  # Maximum length for displaying idea in warnings

# Vietnamese character set for language detection
VIETNAMESE_CHARS = set('àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ')

# Common stop words for relevance checking (Vietnamese and English)
STOP_WORDS = {
    'và', 'các', 'của', 'là', 'được', 'có', 'trong', 'cho', 'với', 'để', 
    'một', 'này', 'đó', 'những', 'như', 'về', 'từ', 'bởi', 'khi', 'sẽ',
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'be', 'been'
}

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

def _get_style_specific_guidance(style):
    """Get specific guidance based on video style to better match user's idea"""
    # Normalize style once for all checks
    style_normalized = style.lower()

    # Use early returns for better performance
    if "vlog" in style_normalized or "cá nhân" in style_normalized:
        return """
═══════════════════════════════════════════════════════════════
📹 PHONG CÁCH: VLOG CÁ NHÂN
═══════════════════════════════════════════════════════════════
- Tone: THÂN MẬT, chân thực, như nói chuyện với bạn bè
- Camera: POV, selfie shots, handheld natural movement
- Hook: Bắt đầu với câu chuyện cá nhân hoặc tình huống thực tế
- Dialogue: Tự nhiên, có thể ngập ngừng, không cần hoàn hảo
- Focus: Chia sẻ trải nghiệm, cảm xúc, bài học cá nhân
"""

    if "review" in style_normalized or "unboxing" in style_normalized:
        return """
═══════════════════════════════════════════════════════════════
📦 PHONG CÁCH: REVIEW/UNBOXING
═══════════════════════════════════════════════════════════════
- Structure: Intro (hook) → Specs/Features → Demo → Pros/Cons → Verdict
- Camera: Close-ups sản phẩm, hands-on shots, B-roll chi tiết
- Hook: "Điều này sẽ thay đổi cách bạn..." hoặc so sánh bất ngờ
- Visual: Chuyển cảnh nhanh, zoom vào chi tiết quan trọng
- Focus: Giá trị thực tế, so sánh, đánh giá trung thực
"""

    if "tutorial" in style_normalized or "hướng dẫn" in style_normalized:
        return """
═══════════════════════════════════════════════════════════════
🎓 PHONG CÁCH: TUTORIAL/HƯỚNG DẪN
═══════════════════════════════════════════════════════════════
- Structure: Problem → Solution steps → Result
- Camera: Over-shoulder, close-up hands, screen recording
- Hook: "Làm thế nào để..." hoặc "Bí quyết để..."
- Visual: Từng bước rõ ràng, text overlays, arrows/highlights
- Focus: Dễ hiểu, có thể làm theo, kết quả cụ thể
"""

    if "quảng cáo" in style_normalized or "tvc" in style_normalized:
        return """
═══════════════════════════════════════════════════════════════
📺 PHONG CÁCH: QUẢNG CÁO TVC
═══════════════════════════════════════════════════════════════
- Structure: Problem → Agitation → Solution → Call-to-Action
- Camera: Cinematic, professional lighting, perfect framing
- Hook: Dramatic problem hoặc lifestyle transformation
- Visual: High-end production, brand colors, lifestyle shots
- Focus: Emotional connection, brand message, clear CTA
"""

    if "music" in style_normalized or "mv" in style_normalized:
        return """
═══════════════════════════════════════════════════════════════
🎵 PHONG CÁCH: MUSIC VIDEO
═══════════════════════════════════════════════════════════════
- Structure: Theo beat và lyrics của nhạc
- Camera: Dynamic movement, artistic angles, rhythm-matching cuts
- Hook: Visual impact ngay từ giây đầu
- Visual: Metaphors, symbolism, artistic interpretation
- Focus: Mood, emotion, visual storytelling match với lyrics
"""

    if "horror" in style_normalized or "kinh dị" in style_normalized:
        return """
═══════════════════════════════════════════════════════════════
👻 PHONG CÁCH: HORROR/KINH DỊ
═══════════════════════════════════════════════════════════════
- Structure: Normal → Unsettling → Terror → Climax
- Camera: Low angles, shaky cam, jump scares, slow creepy zoom
- Hook: Mysterious hoặc creepy atmosphere ngay đầu
- Visual: Dark lighting, shadows, sudden movements
- Focus: Tension build-up, fear, suspense, twisted ending
"""

    if "sci-fi" in style_normalized or "khoa học" in style_normalized:
        return """
═══════════════════════════════════════════════════════════════
🚀 PHONG CÁCH: SCI-FI/KHOA HỌC VIỄN TƯỞNG
═══════════════════════════════════════════════════════════════
- Structure: World-building → Discovery → Conflict → Resolution
- Camera: Futuristic angles, wide establishing shots, tech close-ups
- Hook: "What if..." hoặc advanced technology reveal
- Visual: Futuristic design, tech elements, cool color palette
- Focus: Technology, future society, philosophical questions
"""

    if "fantasy" in style_normalized or "phép thuật" in style_normalized:
        return """
═══════════════════════════════════════════════════════════════
✨ PHONG CÁCH: FANTASY/PHÉP THUẬT
═══════════════════════════════════════════════════════════════
- Structure: Ordinary world → Magic discovery → Quest → Transformation
- Camera: Epic wide shots, magical effects emphasis, wonder moments
- Hook: Magic reveal hoặc mystical world introduction
- Visual: Rich colors, magical elements, fantastical creatures
- Focus: Wonder, magic system, hero's journey, imagination
"""

    if "anime" in style_normalized:
        return """
═══════════════════════════════════════════════════════════════
🎌 PHONG CÁCH: ANIME
═══════════════════════════════════════════════════════════════
- Structure: Character-driven với emotional peaks
- Camera: Dynamic angles, speed lines, dramatic close-ups
- Hook: Action sequence hoặc character intro
- Visual: Vibrant colors, exaggerated expressions, dramatic effects
- Focus: Character emotions, relationships, epic moments
"""

    if "tài liệu" in style_normalized or "documentary" in style_normalized or "phóng sự" in style_normalized:
        return """
═══════════════════════════════════════════════════════════════
📚 PHONG CÁCH: TÀI LIỆU/PHÓNG SỰ
═══════════════════════════════════════════════════════════════
- Structure: Question → Investigation → Discovery → Conclusion
- Camera: Observational, interviews, B-roll footage
- Hook: Surprising fact hoặc important question
- Visual: Real footage, data visualization, expert interviews
- Focus: Truth, education, insight, real stories
"""

    if "sitcom" in style_normalized or "hài" in style_normalized:
        return """
═══════════════════════════════════════════════════════════════
😂 PHONG CÁCH: SITCOM/HÀI KỊCH
═══════════════════════════════════════════════════════════════
- Structure: Setup → Escalation → Punchline
- Camera: Multi-cam, reaction shots, comic timing
- Hook: Funny situation hoặc character quirk
- Visual: Bright lighting, expressive acting, sight gags
- Focus: Humor, timing, relatable situations, callbacks
"""

    if "phim ngắn" in style_normalized or "short film" in style_normalized:
        return """
═══════════════════════════════════════════════════════════════
🎬 PHONG CÁCH: PHIM NGẮN
═══════════════════════════════════════════════════════════════
- Structure: Classic 3-act với twist ending
- Camera: Cinematic composition, meaningful shots, visual metaphors
- Hook: Intriguing premise hoặc character dilemma
- Visual: Artistic, symbolic, every shot tells story
- Focus: Complete story arc, character development, message
"""

    # Default: Cinematic for all other styles including "Điện ảnh", "3D/CGI", "Stop-motion", "Quay thực"
    return """
═══════════════════════════════════════════════════════════════
🎥 PHONG CÁCH: ĐIỆN ẢNH (CINEMATIC)
═══════════════════════════════════════════════════════════════
- Structure: Professional 3-Act structure
- Camera: Cinematic composition, smooth movements, perfect framing
- Hook: Visual impact hoặc intriguing scenario
- Visual: Film-quality lighting, color grading, depth
- Focus: Story depth, character arc, visual excellence
"""


def _schema_prompt(idea, style_vi, out_lang, n, per, mode):
    # Get target language display name
    target_language = LANGUAGE_NAMES.get(out_lang, 'Vietnamese (Tiếng Việt)')

    # Get style-specific guidance
    style_guidance = _get_style_specific_guidance(style_vi)

    # Build language instruction
    language_instruction = f"""
IMPORTANT LANGUAGE REQUIREMENT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌍 TARGET LANGUAGE: {target_language}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**CRITICAL - MUST FOLLOW:**
1. ALL "text_tgt" fields in dialogues MUST be in {target_language}
2. ALL "prompt_tgt" fields MUST be in {target_language}
3. "title_tgt", "outline_tgt", "screenplay_tgt" MUST be in {target_language}
4. Scene descriptions in "prompt_tgt" should match cultural context of {target_language}
5. Character names can stay in original form but dialogue MUST be {target_language}

**Example for Vietnamese (vi):**
  "text_vi": "Xin chào",
  "text_tgt": "Xin chào"  ← SAME as source

**Example for English (en):**
  "text_vi": "Xin chào",
  "text_tgt": "Hello"  ← TRANSLATED to English

**Example for Japanese (ja):**
  "text_vi": "Xin chào", 
  "text_tgt": "こんにちは"  ← TRANSLATED to Japanese

⚠️ DO NOT mix languages - stick to {target_language} for ALL target fields!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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
        input_type_instruction = """
**QUAN TRỌNG**: Người dùng đã cung cấp Ý TƯỞNG. Nhiệm vụ của bạn:
1. PHÁT TRIỂN chính xác theo ý tưởng mà người dùng đưa ra
2. GIỮ NGUYÊN chủ đề, bối cảnh, nhân vật trong ý tưởng gốc
3. Chỉ thêm chi tiết, cảm xúc, và cấu trúc để tạo kịch bản hoàn chỉnh
4. KHÔNG thay đổi concept cốt lõi hoặc tạo câu chuyện hoàn toàn khác
5. Nếu ý tưởng đề cập nhân vật/địa điểm/sự kiện cụ thể → PHẢI xuất hiện trong kịch bản
"""
        base_role = f"""
Bạn là **Biên kịch Đa năng AI Cao cấp**. Nhận **ý tưởng thô sơ** và phát triển thành **kịch bản phim/video SIÊU HẤP DẪN**.
Mục tiêu: TẠO NỘI DUNG VIRAL dựa CHÍNH XÁC trên ý tưởng của người dùng, giữ chân người xem từ giây đầu tiên."""
    
    base_rules = f"""
{base_role}

{input_type_instruction}
{language_instruction}

{style_guidance}

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
- QUAN TRỌNG: Kịch bản phải LIÊN QUAN TRỰC TIẾP đến ý tưởng người dùng cung cấp
""".strip()

    # Adjust input label based on detected type
    input_label = "Kịch bản chi tiết" if has_screenplay_markers else "Ý tưởng thô"
    
    # Add idea adherence reminder
    idea_adherence_reminder = ""
    if not has_screenplay_markers:
        idea_adherence_reminder = f"""
⚠️ TUYỆT ĐỐI PHẢI ĐỌC KỸ YÊU CẦU NÀY:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Kịch bản BẮT BUỘC phải xây dựng dựa trên ý tưởng: "{idea}"

- Nếu ý tưởng nhắc đến nhân vật cụ thể (ví dụ: "Bạch Tuyết", "Superman", "Jack") 
  → Nhân vật ĐÓ phải xuất hiện trong kịch bản
- Nếu ý tưởng nhắc đến địa điểm (ví dụ: "rừng", "Paris", "trường học") 
  → Phải đặt câu chuyện ở địa điểm ĐÓ
- Nếu ý tưởng nhắc đến sự kiện (ví dụ: "cưới", "du lịch", "thi đấu") 
  → Sự kiện ĐÓ phải là trọng tâm câu chuyện
- Nếu ý tưởng là câu chuyện cổ tích/nổi tiếng 
  → Giữ nguyên cốt truyện chính, chỉ điều chỉnh cho phù hợp video format

KHÔNG ĐƯỢC tự ý tạo câu chuyện hoàn toàn khác không liên quan!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    return f"""{base_rules}
{idea_adherence_reminder}
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

def _validate_idea_relevance(idea, generated_content, threshold=0.15):
    """
    Validate that the generated content is related to the original idea.
    
    This helps catch cases where the LLM generates completely unrelated content.
    Uses word overlap as a simple but effective similarity metric.
    
    Args:
        idea: Original user idea/concept
        generated_content: Dict with title, outline, screenplay from LLM
        threshold: Minimum word overlap ratio (default 0.15 = 15%)
    
    Returns:
        tuple: (is_valid: bool, similarity: float, warning_message: str or None)
    """
    if not idea or not generated_content:
        return True, 0.0, None
    
    # Extract key content from generated script
    title = generated_content.get("title_vi", "") or generated_content.get("title_tgt", "")
    outline = generated_content.get("outline_vi", "") or generated_content.get("outline_tgt", "")
    screenplay = generated_content.get("screenplay_vi", "") or generated_content.get("screenplay_tgt", "")
    
    # Combine all generated text
    generated_text = f"{title} {outline} {screenplay}".lower()
    idea_text = idea.lower()
    
    # Extract important words from idea (filter out common stop words)
    # Use module-level constant for better maintainability
    idea_words = [w for w in idea_text.split() if len(w) >= MIN_WORD_LENGTH and w not in STOP_WORDS]
    
    if not idea_words:
        return True, 0.0, None  # Can't validate if no meaningful words
    
    # Count how many idea words appear in generated content
    matched_words = [w for w in idea_words if w in generated_text]
    similarity = len(matched_words) / len(idea_words) if idea_words else 0.0
    
    is_valid = similarity >= threshold
    
    if not is_valid:
        # Smart truncation: only add '...' if idea is actually longer than max length
        idea_display = idea if len(idea) <= MAX_IDEA_DISPLAY_LENGTH else idea[:MAX_IDEA_DISPLAY_LENGTH] + '...'
        warning = (
            f"⚠️ CẢNH BÁO: Kịch bản có thể không liên quan đến ý tưởng!\n"
            f"   Ý tưởng: '{idea_display}'\n"
            f"   Độ liên quan: {similarity*100:.1f}% (ngưỡng tối thiểu: {threshold*100:.1f}%)\n"
            f"   Từ khóa trong ý tưởng: {', '.join(idea_words[:10])}\n"
            f"   Từ khóa xuất hiện: {', '.join(matched_words[:10]) if matched_words else 'Không có'}"
        )
        return False, similarity, warning
    
    return True, similarity, None

def _validate_dialogue_language(scenes, target_lang):
    """
    Validate that dialogue text_tgt fields are in the correct target language.
    
    This is a simple heuristic check - we look for signs that dialogues
    might be in the wrong language (e.g., Vietnamese text when English is expected).
    
    Args:
        scenes: List of scene dicts with dialogues
        target_lang: Target language code (e.g., 'en', 'ja', 'vi')
    
    Returns:
        tuple: (is_valid: bool, warning_message: str or None)
    """
    if not scenes or target_lang == 'vi':
        # Can't validate Vietnamese or if no scenes
        return True, None
    
    issues = []
    
    for scene_idx, scene in enumerate(scenes, 1):
        dialogues = scene.get("dialogues", [])
        for dlg_idx, dlg in enumerate(dialogues, 1):
            if isinstance(dlg, dict):
                text_tgt = dlg.get("text_tgt", "")
                if text_tgt:
                    # Simple heuristic: check for Vietnamese characters using module constant
                    has_vietnamese = any(c.lower() in VIETNAMESE_CHARS for c in text_tgt)
                    
                    # If target is not Vietnamese but text has Vietnamese chars
                    if has_vietnamese and target_lang != 'vi':
                        speaker = dlg.get("speaker", "Unknown")
                        issues.append(
                            f"Scene {scene_idx}, Dialogue {dlg_idx} ({speaker}): "
                            f"Contains Vietnamese characters but target language is {LANGUAGE_NAMES.get(target_lang, target_lang)}"
                        )
    
    if issues:
        warning = (
            f"⚠️ CẢNH BÁO: Một số lời thoại có thể không đúng ngôn ngữ đích!\n\n"
            f"Phát hiện {len(issues)} vấn đề:\n" +
            "\n".join(f"- {issue}" for issue in issues[:5])  # Show first 5
        )
        if len(issues) > 5:
            warning += f"\n... và {len(issues) - 5} vấn đề khác"
        
        return False, warning
    
    return True, None

def generate_script(idea, style, duration_seconds, provider='Gemini 2.5', api_key=None, output_lang='vi', domain=None, topic=None, voice_config=None, progress_callback=None):
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
        progress_callback: Optional function(message: str, percent: int) for progress updates
    
    Returns:
        Script data dict with scenes, character_bible, etc.
    """
    def report_progress(msg, percent):
        """Helper to report progress if callback is provided"""
        if progress_callback:
            progress_callback(msg, percent)
    
    report_progress("Đang chuẩn bị...", 5)
    
    gk, ok=_load_keys()
    n, per = _n_scenes(duration_seconds)
    mode = _mode_from_duration(duration_seconds)
    
    report_progress("Đang xây dựng prompt...", 10)

    # Build base prompt
    prompt=_schema_prompt(idea=idea, style_vi=style, out_lang=output_lang, n=n, per=per, mode=mode)

    # Prepend expert intro if domain/topic selected
    if domain and topic:
        report_progress(f"Đang thêm chuyên môn {domain}...", 15)
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
        report_progress("Đang chờ phản hồi từ Gemini... (có thể mất 1-3 phút)", 25)
        res=_call_gemini(prompt,key,"gemini-2.5-flash")
        report_progress("Đã nhận phản hồi từ Gemini", 50)
    else:
        key=api_key or ok
        if not key: raise RuntimeError("Chưa cấu hình OpenAI API Key cho GPT-4 Turbo.")
        report_progress("Đang chờ phản hồi từ OpenAI... (có thể mất 1-3 phút)", 25)
        # FIXED: Use gpt-4-turbo instead of gpt-5
        res=_call_openai(prompt,key,"gpt-4-turbo")
        report_progress("Đã nhận phản hồi từ OpenAI", 50)
    if "scenes" not in res: raise RuntimeError("LLM không trả về đúng schema.")
    
    report_progress("Đang kiểm tra tính duy nhất của các cảnh...", 60)

    # ISSUE #1 FIX: Validate scene uniqueness
    scenes = res.get("scenes", [])
    duplicates = _validate_scene_uniqueness(scenes, similarity_threshold=0.8)
    if duplicates:
        dup_msg = ", ".join([f"Scene {i} & {j} ({sim*100:.0f}% similar)" for i, j, sim in duplicates])
        print(f"[WARN] Duplicate scenes detected: {dup_msg}")
        # Note: We warn but don't fail - the UI can decide how to handle this
    
    report_progress("Đang kiểm tra độ liên quan của kịch bản...", 70)
    
    # ISSUE #3 FIX: Validate idea relevance
    # Use module-level constant for threshold
    is_relevant, relevance_score, warning_msg = _validate_idea_relevance(idea, res, threshold=IDEA_RELEVANCE_THRESHOLD)
    if not is_relevant and warning_msg:
        print(warning_msg)
        # Store warning in result so UI can display it to user
        res["idea_relevance_warning"] = warning_msg
        res["idea_relevance_score"] = relevance_score
    else:
        # Store score for debugging/telemetry
        res["idea_relevance_score"] = relevance_score
    
    report_progress("Đang kiểm tra ngôn ngữ lời thoại...", 75)
    
    # ISSUE #4 FIX: Validate dialogue language consistency
    dialogue_valid, dialogue_warning = _validate_dialogue_language(scenes, output_lang)
    if not dialogue_valid and dialogue_warning:
        print(dialogue_warning)
        res["dialogue_language_warning"] = dialogue_warning
    
    report_progress("Đang tạo character bible...", 80)
    
    # ISSUE #2 FIX: Enforce character consistency
    character_bible = res.get("character_bible", [])
    if character_bible:
        res["scenes"] = _enforce_character_consistency(scenes, character_bible)

    # Store voice configuration in result for consistency
    if voice_config:
        report_progress("Đang lưu voice config...", 90)
        res["voice_config"] = voice_config
    
    report_progress("Đang điều chỉnh thời lượng cảnh...", 95)

    # ép durations
    for i,d in enumerate(per):
        if i < len(res["scenes"]): res["scenes"][i]["duration"]=int(d)
    
    report_progress("Hoàn tất!", 100)
    
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