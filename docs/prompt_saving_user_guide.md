# Prompt Saving Feature - User Guide

## Overview

This feature allows users to save Google Labs Flow prompts in two formats:
1. **Formatted Text (.txt)**: The actual text prompt sent to Google Labs Veo API
2. **JSON Format (.json)**: The structured data representation

## How to Use

### Saving as Formatted Text (Google Labs Flow Format)

1. Open the **Prompt Viewer** dialog (click on any prompt in the application)
2. Navigate to the **"🚀 API Prompt"** tab
3. Click the **"💾 Save as Text File"** button
4. Choose a location and filename (default: `google_labs_prompt_YYYYMMDD_HHMMSS.txt`)
5. Click **Save**

The saved text file will include:
- Header with timestamp and description
- The complete formatted prompt with:
  - Character Identity Lock sections
  - Visual Style Lock directives
  - Scene descriptions
  - Camera directions
  - Audio settings (voiceover, background music)
  - Negative prompts

### Saving as JSON

1. Open the **Prompt Viewer** dialog
2. Navigate to the **"📄 JSON"** tab
3. Click the **"💾 Save as JSON File"** button
4. Choose a location and filename (default: `google_labs_prompt_YYYYMMDD_HHMMSS.json`)
5. Click **Save**

The saved JSON file will be formatted with proper indentation for easy reading.

## Example Output

### Formatted Text Output (`google_labs_prompt_20251108_155500.txt`)

```
# Google Labs Flow API Prompt
# Generated: 2025-11-08 15:55:00
# This is the formatted text prompt sent to Google Labs Veo API
#======================================================================

╔═══════════════════════════════════════════════════════════╗
║  CHARACTER IDENTITY LOCK (CoT + RCoT TECHNIQUE)          ║
║  THIS SECTION MUST NEVER BE IGNORED OR MODIFIED          ║
╚═══════════════════════════════════════════════════════════╝

CRITICAL CHARACTER IDENTITY LOCK:
Main character: Young professional woman
1. Hair: Long black hair in ponytail
2. Eyes: Brown almond-shaped eyes
3. Outfit: Blue business suit

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NEVER CHANGE DIRECTIVES (10 CRITICAL RULES):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. NEVER change character facial features (eyes, nose, mouth, face shape)
2. NEVER change character hairstyle, hair color, or hair length
...
```

### JSON Output (`google_labs_prompt_20251108_155500.json`)

```json
{
  "scene_id": "scene_001",
  "objective": "Create a professional video scene",
  "character_details": "CRITICAL CHARACTER IDENTITY LOCK:\nMain character: Young professional woman...",
  "setting_details": "Modern office environment with glass windows and city view",
  "audio": {
    "voiceover": {
      "language": "vi",
      "text": "Chào mừng đến với presentation của chúng tôi về AI và tương lai",
      "tts_provider": "elevenlabs",
      "voice_id": "professional_female_vi"
    }
  },
  "constraints": {
    "duration_seconds": 8,
    "aspect_ratio": "VIDEO_ASPECT_RATIO_LANDSCAPE",
    "visual_style_tags": ["2D anime", "flat colors", "bold outlines"]
  }
}
```

## Benefits

### Formatted Text File Benefits:
- **Exact API Format**: See exactly what is sent to Google Labs
- **Human Readable**: Easy to review and understand
- **Shareable**: Can share with team members or use as reference
- **Documentation**: Keep records of what prompts were used for each video
- **Learning**: Understand how the structured JSON is converted to API format

### JSON File Benefits:
- **Programmatic Use**: Easy to parse and reuse in code
- **Version Control**: Track changes in git
- **Backup**: Keep copies of prompt configurations
- **Editing**: Can be edited and re-imported
- **Analysis**: Can analyze prompt patterns across projects

## Technical Details

### File Format: Formatted Text
- **Extension**: `.txt`
- **Encoding**: UTF-8 (supports Vietnamese and other languages)
- **Structure**: 
  1. Header comments (lines starting with #)
  2. Character Identity Lock section
  3. Visual Style Lock section
  4. Scene descriptions
  5. Camera directions
  6. Audio settings
  7. Negative prompts

### File Format: JSON
- **Extension**: `.json`
- **Encoding**: UTF-8
- **Formatting**: Pretty-printed with 2-space indentation
- **Structure**: Follows Google Labs Flow prompt schema

## Use Cases

1. **Documentation**: Save prompts for successful videos to reference later
2. **Sharing**: Send formatted prompts to team members or clients
3. **Comparison**: Compare different prompt versions to see what works best
4. **Backup**: Keep copies of all prompts before making changes
5. **Learning**: Study how different parameters affect video generation
6. **Debugging**: When reporting issues, include the exact prompt used
7. **Templates**: Save successful prompts as templates for future projects

## Notes

- Both save functions include timestamp in default filename to avoid overwriting
- Files are saved with UTF-8 encoding to properly handle Vietnamese text
- Success/error messages are shown after save operations
- File dialogs remember the last used directory
- You can copy prompts to clipboard before saving (using the Copy button)
