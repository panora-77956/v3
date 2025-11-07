# Examples Directory

This directory contains example scripts demonstrating how to use various features of the video generation system.

## Available Examples

### generate_scene_audio.py

Demonstrates how to use the TTS (Text-to-Speech) service to generate Vietnamese audio for video scenes.

**Usage:**
```bash
python examples/generate_scene_audio.py
```

**Features demonstrated:**
- Simple Vietnamese audio generation
- Using Google TTS with vi-VN-Wavenet-A voice
- Configuration validation
- Error handling

**Requirements:**
- Google API key configured in `config.json`

## Setup

Before running examples, ensure you have:

1. Installed all dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configured your API keys in `config.json`:
   ```json
   {
     "google_api_keys": ["YOUR_GOOGLE_API_KEY"]
   }
   ```

## More Information

- See `docs/TTS_SERVICE.md` for detailed TTS service documentation
- See `docs/CONFIGURATION.md` for API key configuration
- See `docs/NEW_FEATURES.md` for feature overviews

## Contributing

Feel free to add more examples that demonstrate:
- Different TTS providers (ElevenLabs, OpenAI)
- Video generation workflows
- Image generation
- Multi-scene projects
