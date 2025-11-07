#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example: Generate Audio for Video Scenes

This example demonstrates how to use the TTS service to generate
Vietnamese audio for video scenes.
"""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.audio_generator import validate_voiceover_config


def example_1_simple_vietnamese_audio():
    """Example 1: Simple Vietnamese audio generation"""
    print("=" * 70)
    print("Example 1: Simple Vietnamese Audio Generation")
    print("=" * 70)

    voiceover_config = {
        "tts_provider": "google",
        "voice_id": "vi-VN-Wavenet-A",
        "language": "vi",
        "text": "Xin chào! Đây là ví dụ về tạo giọng nói tiếng Việt tự động.",
        "prosody": {
            "rate": 1.0,
            "pitch": 0
        }
    }

    print("\nConfiguration:")
    print(json.dumps(voiceover_config, indent=2, ensure_ascii=False))

    # Validate configuration
    is_valid, error = validate_voiceover_config(voiceover_config)
    if not is_valid:
        print(f"❌ Invalid configuration: {error}")
        return

    print("✓ Configuration is valid")
    print("⚠ Audio generation requires API key (see config.json)")


def main():
    """Run all examples"""
    print("Vietnamese TTS Audio Generation Examples")
    print("=" * 70)

    try:
        example_1_simple_vietnamese_audio()
        print("\n✓ Example completed!")
        print("\nSee docs/TTS_SERVICE.md for more information")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
