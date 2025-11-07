# Voice Prosody & Speaking Style Controls

## Overview

This feature adds comprehensive voice prosody and speaking style controls to the video generation interface, allowing users to control how the voiceover narration sounds across all scenes in their video.

## Features

### 6 Speaking Style Presets

1. **📢 Thuyết trình chuyên nghiệp (Professional Presentation)**
   - Formal, clear tone suitable for presentations
   - Slow, steady pace with loud volume
   - High stability, low expressiveness

2. **💬 Trò chuyện tự nhiên (Casual Conversation)**
   - Friendly, natural conversational tone
   - Medium pace with slightly higher pitch
   - Moderate stability and expressiveness

3. **📖 Kể chuyện (Storytelling)** *[DEFAULT]*
   - Lively, emotional, engaging tone
   - Slow pace with elevated pitch
   - Lower stability, high expressiveness

4. **🎓 Giảng dạy (Educational)**
   - Clear, measured, easy to understand
   - Slow pace with neutral pitch
   - Very high stability, low expressiveness

5. **🎉 Nhiệt tình (Enthusiastic)**
   - Energetic, excited tone
   - Fast pace with high pitch
   - Lowest stability, highest expressiveness

6. **😌 Thư giãn (Calm & Relaxed)**
   - Gentle, soothing, relaxed tone
   - Slow pace with lower pitch
   - High stability, moderate expressiveness

### Prosody Controls (Fine-Tuning)

1. **Tốc độ nói (Speaking Rate)**
   - Range: 0.5x - 2.0x (default: 1.0x)
   - Slider with real-time multiplier display
   - Presets: Chậm (0.75x), Trung bình (1.0x), Nhanh (1.25x)

2. **Cao độ giọng (Pitch)**
   - Range: -5st to +5st (default: 0st)
   - Slider with semitone display
   - Presets: Thấp (-2st), Bình thường (0st), Cao (+2st)

3. **Biểu cảm (Expressiveness)**
   - Range: 0.0 - 1.0 (default: 0.5)
   - Slider with decimal display
   - Presets: Đơn điệu (0.2), Rõ ràng (0.5), Sinh động (0.8)

### Global Settings

- **☑ Áp dụng cho tất cả cảnh (Apply to all scenes)**
  - Checked by default
  - Ensures consistent voice prosody across entire video
  - Future: Can be unchecked for per-scene customization

## User Interface

The voice settings appear as a collapsible group box titled **"🎙️ Cài đặt giọng nói & ngữ điệu"** in the left panel of the video generation interface.

### Layout

```
┌─ 🎙️ Cài đặt giọng nói & ngữ điệu ────────────────┐
│                                                   │
│ Phong cách:    [📖 Kể chuyện         ▼]         │
│ Giọng sinh động, có cảm xúc, hấp dẫn             │
│                                                   │
│ Tốc độ nói:    [━━━━●━━━━━] 1.0x                │
│ Cao độ giọng:  [━━━━━●━━━━] 0st                  │
│ Biểu cảm:      [━━━━━●━━━━] 0.5                  │
│                                                   │
│ ☑ Áp dụng cho tất cả cảnh                        │
│                                                   │
└───────────────────────────────────────────────────┘
```

## Technical Implementation

### Module Structure

#### `services/voice_options.py`

Core module providing:
- `SPEAKING_STYLES`: Dictionary of all 6 style presets
- `get_google_tts_ssml()`: Generate SSML markup for Google TTS
- `get_elevenlabs_settings()`: Generate settings for ElevenLabs
- `get_style_list()`: Get list of styles for UI display
- `get_style_info()`: Get detailed info about a style
- Helper functions: `_calculate_rate()`, `_calculate_pitch()`

#### `ui/text2video_panel.py`

GUI components:
- `cb_speaking_style`: ComboBox for style selection
- `slider_rate`: Horizontal slider for speaking rate
- `slider_pitch`: Horizontal slider for pitch
- `slider_expressiveness`: Horizontal slider for expressiveness
- `lbl_style_description`: Dynamic description label
- `cb_apply_voice_all`: Checkbox for global application
- Event handlers: `_on_speaking_style_changed()`, `_on_rate_changed()`, etc.
- `get_voice_settings()`: Method to retrieve current settings

#### `ui/text2video_panel_impl.py`

Integration:
- `build_prompt_json()`: Updated to accept `voice_settings` parameter
- Voice settings embedded in `audio.voiceover` section of prompt JSON

### Data Flow

1. User selects speaking style preset → Sliders auto-update
2. User adjusts sliders → Settings updated in real-time
3. User generates video → `get_voice_settings()` called
4. Settings passed to `build_prompt_json()` for each scene
5. Voice settings included in prompt JSON's audio section

### Prompt JSON Structure

```json
{
  "audio": {
    "voiceover": {
      "language": "vi",
      "text": "Scene narration text",
      "speaking_style": "storytelling",
      "rate_multiplier": 1.0,
      "pitch_adjust": 0,
      "expressiveness": 0.5
    },
    "music_bed": "subtle, minimal, non-intrusive"
  }
}
```

## TTS Provider Integration

### Google TTS (with SSML)

The `get_google_tts_ssml()` function generates SSML markup:

```xml
<speak>
  <voice name="vi-VN-Wavenet-A">
    <prosody rate="75%" pitch="+2st" volume="medium">
      Narration text here
    </prosody>
  </voice>
</speak>
```

**Mapping:**
- Rate: Converted from preset ("slow"/"medium"/"fast") to percentage
- Pitch: Converted from semitones (e.g., "+2st")
- Volume: Mapped from preset ("soft"/"medium"/"loud")
- Expressiveness: Approximated via volume + rate combination

### ElevenLabs

The `get_elevenlabs_settings()` function generates settings:

```python
{
    "stability": 0.55,           # Controls voice consistency
    "similarity_boost": 0.85,    # Voice clone accuracy
    "style": 0.75,               # Expressiveness/emotion
    "use_speaker_boost": True    # Enhanced clarity
}
```

**Mapping:**
- Stability: Direct mapping from preset
- Similarity_boost: Fixed per preset
- Style: Maps to expressiveness
- Rate/Pitch: Not directly supported, mentioned in prompt

## User Experience Flow

1. **Select Style Preset**
   - User opens voice settings group
   - Selects "📖 Kể chuyện" from dropdown
   - Description shows: "Giọng sinh động, có cảm xúc, hấp dẫn"
   - Sliders auto-fill with preset values

2. **Fine-Tune (Optional)**
   - User adjusts rate slider → Label shows "1.2x"
   - User adjusts pitch slider → Label shows "+2st"
   - User adjusts expressiveness → Label shows "0.7"
   - Preset switches to "Tùy chỉnh" (Custom)

3. **Apply to All Scenes**
   - Checkbox remains checked (default)
   - Ensures consistency across entire video

4. **Generate Video**
   - Voice settings automatically applied to all scenes
   - Consistent prosody throughout video

## Testing

### Unit Tests

Test file: `/tmp/test_voice_options.py`

Tests:
- ✓ All 6 speaking styles defined correctly
- ✓ SSML generation for Google TTS
- ✓ ElevenLabs settings generation
- ✓ Style list retrieval
- ✓ Style info retrieval
- ✓ Edge cases and value clamping

### Integration Tests

Test file: `/tmp/test_ui_integration.py`

Tests:
- ✓ Voice settings correctly integrated into prompt JSON
- ✓ Backward compatibility (works without voice settings)

### UI Tests

Test file: `/tmp/test_ui_visual.py`

Tests:
- ✓ All UI widgets initialized correctly
- ✓ Event handlers working correctly
- ✓ get_voice_settings() returns correct data
- ✓ Slider and label updates synchronized

## Backward Compatibility

The implementation maintains full backward compatibility:
- `build_prompt_json()` has optional `voice_settings` parameter
- When not provided, basic voiceover config is used
- Existing code continues to work without modifications

## Future Enhancements

1. **Per-Scene Customization**
   - Uncheck "Apply to all scenes"
   - Different prosody for each scene (dramatic, calm, etc.)

2. **Voice Preview**
   - Add "Preview" button to test voice settings
   - Generate short audio sample before full video

3. **Custom Presets**
   - Allow users to save their own style presets
   - Share presets across projects

4. **Advanced Controls**
   - Volume control slider
   - Emphasis markers for specific words
   - Pause duration control

5. **TTS Provider Selection**
   - Add dropdown to choose between Google TTS and ElevenLabs
   - Show provider-specific controls

## Notes

- Default preset: **Storytelling** (index 2)
- All sliders update in real-time
- Settings persist within session
- Bilingual labels (VI/EN) for international users
- Accessible via keyboard navigation

## Related Files

- `services/voice_options.py` - Core voice prosody module
- `ui/text2video_panel.py` - GUI implementation
- `ui/text2video_panel_impl.py` - Integration layer
- `services/google/tts_voices.py` - Google TTS voice list
- `services/tts_service.py` - TTS service utilities

## Author

- User: nguyen2715-hue
- Date: 2025-11-03
- Feature Request: Voice Prosody & Speaking Style Controls
