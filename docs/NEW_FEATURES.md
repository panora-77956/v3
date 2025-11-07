# Text2Video New Features

This document describes the 3 major new features added to the Text2Video panel.

## 1. System Prompts Updater with Hot Reload

### Overview
Allows updating domain-specific system prompts from Google Sheets without restarting the application.

### Location
**Settings Tab** → "🔄 System Prompts Updater" section

### Features
- Fetch latest prompts from Google Sheets CSV export
- Update `services/domain_prompts.py` automatically
- Hot reload prompts without app restart
- Display update status and statistics

### Usage
1. Navigate to Settings tab
2. Find the "System Prompts Updater" section
3. Click "⬇️ Cập nhật System Prompts" button
4. Wait for download and update
5. Prompts are immediately available in Text2Video panel

### Google Sheets Structure
The Google Sheet must have this CSV format:
```
Domain,Topic,System Prompt
GIÁO DỤC/HACKS,Mẹo Vặt (Life Hacks) Độc đáo,"Prompt text here..."
```

### Technical Details
- **Source**: `https://docs.google.com/spreadsheets/d/1ohiL6xOBbjC7La2iUdkjrVjG4IEUnVWhI0fRoarD6P0`
- **CSV Export**: Appends `/export?format=csv&gid=1507296519` to get raw CSV
- **Files Modified**:
  - `services/prompt_updater.py` (NEW)
  - `services/domain_prompts.py`
  - `ui/settings_panel.py`

### API Reference

#### `services/prompt_updater.py`

```python
def fetch_prompts_from_sheets() -> Tuple[Dict[str, Dict[str, str]], str]:
    """
    Fetch system prompts from Google Sheets CSV export
    
    Returns:
        Tuple of (prompts_dict, error_message)
    """

def generate_prompts_code(prompts: Dict[str, Dict[str, str]]) -> str:
    """
    Generate Python code for domain_prompts.py from prompts dictionary
    
    Returns:
        Complete Python code for domain_prompts.py
    """

def update_prompts_file(file_path: str) -> Tuple[bool, str]:
    """
    Update domain_prompts.py file with latest data from Google Sheets
    
    Returns:
        Tuple of (success, message)
    """
```

#### `services/domain_prompts.py`

```python
def load_prompts() -> Dict[str, Dict[str, str]]:
    """Load prompts from file (for hot reload)"""

def reload_prompts() -> Tuple[bool, str]:
    """
    Reload prompts from the current file (hot reload)
    
    Returns:
        Tuple of (success, message)
    """
```

---

## 2. Social Media Content Generation

### Overview
Automatically generates 3 versions of social media posts with different tones after script generation.

### Location
**Text2Video Panel** → "📱 Social Media" tab (Tab 5)

### Features
- **Version 1: Casual/Friendly** (TikTok/YouTube Shorts)
  - Thân mật, gần gũi, nhiều emoji
  - Tone: Casual and conversational
  
- **Version 2: Professional** (LinkedIn/Facebook)
  - Chuyên nghiệp, uy tín, giá trị cao
  - Tone: Business-like and credible
  
- **Version 3: Funny/Engaging** (TikTok/Instagram Reels)
  - Hài hước, vui nhộn, viral
  - Tone: Humorous and attention-grabbing

### Content Structure
Each version includes:
- **Title**: Catchy headline
- **Description**: 2-3 sentence description
- **Hashtags**: 5-10 relevant hashtags
- **CTA**: Call-to-action text
- **Best Posting Time**: Optimal time for platform

### Usage
1. Generate a video script in Text2Video panel
2. Social media content is automatically generated
3. Switch to "📱 Social Media" tab to view results
4. Copy content for your social media posts

### Technical Details
- **Trigger**: Automatically after script generation
- **LLM**: Uses same provider as script generation (Gemini/OpenAI)
- **Files Modified**:
  - `services/llm_story_service.py`
  - `ui/text2video_panel.py`

### API Reference

```python
def generate_social_media(script_data, provider='Gemini 2.5', api_key=None) -> Dict:
    """
    Generate social media content in 3 different tones
    
    Args:
        script_data: Script data dictionary with title, outline, screenplay
        provider: LLM provider (Gemini/OpenAI)
        api_key: Optional API key
    
    Returns:
        Dictionary with 3 social media versions (casual, professional, funny)
        {
            "casual": {
                "title": "...",
                "description": "...",
                "hashtags": ["#tag1", "#tag2"],
                "cta": "...",
                "best_time": "...",
                "platform": "TikTok/YouTube Shorts"
            },
            "professional": {...},
            "funny": {...}
        }
    """
```

### Example Output

```
============================================================
📱 VERSION 1: CASUAL/FRIENDLY (TikTok/YouTube Shorts)
============================================================

🎯 Platform: TikTok/YouTube Shorts

📝 Title:
3 Mẹo Vặt Siêu Dễ Mà Ai Cũng Cần! 😱

📄 Description:
Bạn đã biết 3 mẹo này chưa? Thử ngay để cuộc sống dễ dàng hơn! 🔥

🏷️ Hashtags:
#meovat #lifehacks #tips #viral #fyp

📢 CTA:
Thử ngay và tag bạn bè! 👇

⏰ Best Time: 6-9 PM (weekdays), 10 AM-2 PM (weekends)
```

---

## 3. Thumbnail Design Specifications

### Overview
Generates detailed thumbnail design specifications for your video, including colors, typography, layout, and visual elements.

### Location
**Text2Video Panel** → "🖼️ Thumbnail" tab (Tab 4)

### Features
- **Concept**: Overall design idea and theme
- **Color Palette**: 3-5 colors with hex codes and usage
- **Typography**: Text overlay, font, size, effects
- **Layout**: Composition, focal point, rule of thirds
- **Visual Elements**: Subject, props, background, effects
- **Style Guide**: Overall aesthetic and tone

### Design Principles
Thumbnails are optimized for:
- High contrast and bold colors
- Curiosity gap to drive clicks
- Mobile readability (large, clear text)
- Content alignment with video

### Usage
1. Generate a video script in Text2Video panel
2. Thumbnail design is automatically generated
3. Switch to "🖼️ Thumbnail" tab to view specifications
4. Use specs to create thumbnail in design tool

### Technical Details
- **Trigger**: Automatically after script generation
- **LLM**: Uses same provider as script generation (Gemini/OpenAI)
- **Files Modified**:
  - `services/llm_story_service.py`
  - `ui/text2video_panel.py`

### API Reference

```python
def generate_thumbnail_design(script_data, provider='Gemini 2.5', api_key=None) -> Dict:
    """
    Generate detailed thumbnail design specifications
    
    Args:
        script_data: Script data dictionary with title, outline, screenplay
        provider: LLM provider (Gemini/OpenAI)
        api_key: Optional API key
    
    Returns:
        Dictionary with thumbnail design specifications
        {
            "concept": "Overall design idea...",
            "color_palette": [
                {"name": "Primary", "hex": "#FF5733", "usage": "Background"},
                ...
            ],
            "typography": {
                "main_text": "Text on thumbnail",
                "font_family": "Montserrat Bold",
                "font_size": "72-96pt",
                "effects": "Drop shadow, outline..."
            },
            "layout": {
                "composition": "Character left, text right",
                "focal_point": "Face of main character",
                "rule_of_thirds": "Subject on left third"
            },
            "visual_elements": {
                "subject": "Main character",
                "props": ["Item 1", "Item 2"],
                "background": "Background description",
                "effects": ["Effect 1", "Effect 2"]
            },
            "style_guide": "Bold and dramatic with high contrast..."
        }
    """
```

### Example Output

```
============================================================
🖼️ THUMBNAIL DESIGN SPECIFICATIONS
============================================================

💡 CONCEPT:
Bold and attention-grabbing design featuring the main character
with shocked expression, overlaid with large text highlighting
the key benefit.

🎨 COLOR PALETTE:
  • Primary: #FF5733 - Background gradient
  • Accent: #33FF57 - Text highlight
  • Dark: #1A1A1A - Text outline
  • Bright: #FFFFFF - Main text

✍️ TYPOGRAPHY:
  • Main Text: KHÔNG NGỜ! 3 ĐIỀU NÀY
  • Font Family: Montserrat Black
  • Font Size: 84pt
  • Effects: 4px white outline, 2px drop shadow

📐 LAYOUT:
  • Composition: Character occupies left 60%, text on right 40%
  • Focal Point: Character's surprised facial expression
  • Rule of Thirds: Face at upper left intersection point

🎭 VISUAL ELEMENTS:
  • Subject: Main character with surprised expression
  • Props: Light bulb icon, exclamation marks
  • Background: Vibrant gradient from orange to red
  • Effects: Glow effect around character, motion lines

🎬 STYLE GUIDE:
High-energy and bold design with maximum contrast. Hyper-stylized
with exaggerated expressions and text. Creates immediate curiosity.
```

---

## Integration Flow

```
User clicks "⚡ Tạo video tự động"
    ↓
Step 1: Generate Script
    ↓
Auto-generate Social Media Content
    ├─ Casual version
    ├─ Professional version
    └─ Funny version
    ↓
Auto-generate Thumbnail Design
    ├─ Concept
    ├─ Color palette
    ├─ Typography
    ├─ Layout
    ├─ Visual elements
    └─ Style guide
    ↓
Step 2: Generate Videos
    ↓
Step 3: Download & Process
```

## Error Handling

All features include robust error handling:

1. **Network Errors**: Timeouts, connection issues
2. **API Errors**: LLM failures, quota exceeded
3. **Parse Errors**: Invalid JSON, malformed data
4. **File Errors**: Permission denied, disk full

Errors are logged to console with clear messages and don't block the main workflow.

## Testing

Run the test suite:
```bash
cd /home/runner/work/v3/v3
python3 /tmp/test_features.py
```

Expected output:
```
🎉 All tests passed!
```

## Future Enhancements

Possible improvements:
1. Support for more social media platforms (Twitter/X, Threads)
2. Multiple thumbnail design variations
3. Export social media content to clipboard/file
4. Preview thumbnail design in app
5. Bulk update prompts from multiple Google Sheets
6. Schedule prompt updates (daily/weekly)
7. Version control for prompts (rollback support)
