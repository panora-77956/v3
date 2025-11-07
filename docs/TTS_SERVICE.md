# TTS Service Documentation

## Overview

The TTS (Text-to-Speech) service provides audio generation functionality for video projects. It supports multiple TTS providers:

- **Google Cloud Text-to-Speech** - High quality, multilingual, supports SSML
- **ElevenLabs** - Natural sounding voices with emotion control
- **OpenAI TTS** - Fast, reliable text-to-speech

## Quick Start

### Basic Usage

```python
from services.tts_service import synthesize_speech

# Define voiceover configuration
voiceover_config = {
    "tts_provider": "google",
    "voice_id": "vi-VN-Wavenet-A",
    "language": "vi",
    "text": "Xin chào, đây là bài kiểm tra giọng nói tiếng Việt.",
    "prosody": {
        "rate": 1.0,
        "pitch": 0
    }
}

# Generate audio
audio_bytes = synthesize_speech(voiceover_config, output_path="output.mp3")
```

### Generate from Scene JSON

```python
from services.tts_service import generate_audio_from_scene
import json

# Load scene JSON
with open('scene_01.json', 'r') as f:
    scene_data = json.load(f)

# Generate audio
audio_path = generate_audio_from_scene(scene_data, output_dir="./audio")
print(f"Audio saved to: {audio_path}")
```

## Configuration

### Google TTS Configuration

```json
{
  "tts_provider": "google",
  "voice_id": "vi-VN-Wavenet-A",
  "language": "vi",
  "text": "Your text here",
  "ssml_markup": "<speak><prosody rate=\"100%\" pitch=\"+0st\">Your text</prosody></speak>",
  "prosody": {
    "rate": 1.0,
    "pitch": 0
  }
}
```

**Available Vietnamese Voices:**
- `vi-VN-Wavenet-A` - Nam Miền Bắc (Male, Northern accent) - High quality
- `vi-VN-Wavenet-B` - Nữ Miền Bắc (Female, Northern accent) - High quality
- `vi-VN-Wavenet-C` - Nữ Miền Nam (Female, Southern accent) - High quality
- `vi-VN-Wavenet-D` - Nam Miền Nam (Male, Southern accent) - High quality
- `vi-VN-Standard-A` - Nam Miền Bắc (Male, Northern accent) - Standard quality
- `vi-VN-Standard-B` - Nữ Miền Bắc (Female, Northern accent) - Standard quality

**Prosody Parameters:**
- `rate`: Speaking rate (0.25 to 4.0, default 1.0)
- `pitch`: Pitch adjustment in semitones (-20.0 to 20.0, default 0.0)

### ElevenLabs Configuration

```json
{
  "tts_provider": "elevenlabs",
  "voice_id": "21m00Tcm4TlvDq8ikWAM",
  "text": "Your text here",
  "elevenlabs_settings": {
    "stability": 0.5,
    "similarity_boost": 0.75,
    "style": 0.5,
    "use_speaker_boost": true
  }
}
```

### OpenAI TTS Configuration

```json
{
  "tts_provider": "openai",
  "voice_id": "alloy",
  "text": "Your text here",
  "prosody": {
    "rate": 1.0
  }
}
```

**Available Voices:** `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`

## Scene JSON Structure

The TTS service expects scene JSON files with the following structure:

```json
{
  "scene_index": 1,
  "description": "Scene description",
  "audio": {
    "voiceover": {
      "language": "vi",
      "tts_provider": "google",
      "voice_id": "vi-VN-Wavenet-A",
      "voice_name": "🇻🇳 Nam Miền Bắc - Wavenet",
      "speaking_style": "storytelling",
      "text": "Voiceover text in Vietnamese",
      "ssml_markup": "<speak><prosody rate=\"100%\" pitch=\"+0st\">Voiceover text</prosody></speak>",
      "prosody": {
        "rate": 1.0,
        "pitch": 0
      }
    }
  }
}
```

## API Key Configuration

The TTS service automatically loads API keys from `config.json`. Add your keys:

```json
{
  "google_api_keys": ["YOUR_GOOGLE_API_KEY"],
  "elevenlabs_api_keys": ["YOUR_ELEVENLABS_API_KEY"],
  "openai_api_keys": ["YOUR_OPENAI_API_KEY"]
}
```

## Helper Functions

### Batch Audio Generation

```python
from services.audio_generator import generate_batch_audio

scenes = [
    {"scene": 1, "voiceover": "Text 1", "voice_id": "vi-VN-Wavenet-A"},
    {"scene": 2, "voiceover": "Text 2", "voice_id": "vi-VN-Wavenet-A"}
]

results = generate_batch_audio(scenes, output_dir="./audio")
# Returns: {1: "audio/scene_01_audio.mp3", 2: "audio/scene_02_audio.mp3"}
```

### Configuration Validation

```python
from services.audio_generator import validate_voiceover_config

config = {
    "tts_provider": "google",
    "voice_id": "vi-VN-Wavenet-A",
    "text": "Test"
}

is_valid, error = validate_voiceover_config(config)
if not is_valid:
    print(f"Invalid config: {error}")
```

## Troubleshooting

### No audio generated

**Cause:** Missing API key

**Solution:** Add your API key to `config.json`:
```json
{
  "google_api_keys": ["YOUR_KEY_HERE"]
}
```

### Wrong language/voice

**Cause:** Mismatch between `language` and `voice_id`

**Solution:** Ensure voice_id matches the language:
- Vietnamese: Use `vi-VN-*` voices with `language: "vi"`
- English: Use `en-US-*` or `en-GB-*` voices with `language: "en"`

### SSML errors

**Cause:** Invalid SSML markup

**Solution:** Use the helper to generate SSML:
```python
from services.voice_options import get_google_tts_ssml

ssml = get_google_tts_ssml(
    text="Your text",
    voice_id="vi-VN-Wavenet-A",
    style_preset="storytelling"
)
```

## Integration with Video Generation

The TTS service integrates with the video generation pipeline. Audio files are generated for each scene and can be combined with video clips.

Example workflow:
1. Generate scene prompts
2. Generate audio for each scene using TTS service
3. Generate video clips for each scene
4. Combine video + audio using video editing tools

## Error Handling

The TTS service includes comprehensive error handling and logging:

```python
import logging
logging.basicConfig(level=logging.INFO)

# Errors are logged automatically
audio = synthesize_speech(config)
# Check logs for detailed error messages
```

## Performance Tips

1. **Use Standard voices** for faster generation (vs Wavenet/Neural)
2. **Cache audio files** by scene content hash to avoid regeneration
3. **Batch process** multiple scenes in parallel if needed
4. **Monitor API quotas** to avoid rate limiting

## Examples

See `examples/generate_scene_audio.py` for complete examples of:
- Basic TTS synthesis
- Scene JSON processing
- Configuration validation
- Error handling

Run the example:
```bash
python examples/generate_scene_audio.py
```
