"""Clean camera terms from voiceover"""
import re

class VoiceoverCleaner:
    def clean(self, voiceover: str) -> str:
        patterns = [
            r'^Cận cảnh\s+\w+\.\s*',
            r'^Toàn cảnh\s+.*?\.\s*',
            r'^Close-up\s+of\s+\w+\.\s*',
            r'^\w+\s+đang\s+\w+\.\s*',
        ]
        cleaned = voiceover
        for pattern in patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        return cleaned.strip()
    
    def clean_outline(self, outline):
        for scene in outline.get('scenes', []):
            original = scene.get('voiceover', '')
            scene['voiceover'] = self.clean(original)
        return outline
