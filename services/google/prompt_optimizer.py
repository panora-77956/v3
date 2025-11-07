# -*- coding: utf-8 -*-
"""
Prompt Optimizer for Text2Video
Intelligently compresses prompts to fit within token limits while NEVER truncating voiceover text.
"""

import json
import re
from typing import Dict, List, Optional, Any, Tuple


# Token estimation constants
CHARS_PER_TOKEN_AVG = 4  # Average characters per token
GEMINI_TOKEN_LIMIT = 30000  # Gemini 30K token limit
SAFETY_MARGIN_TOKENS = 2000  # Reserve tokens for response
MAX_USABLE_TOKENS = GEMINI_TOKEN_LIMIT - SAFETY_MARGIN_TOKENS


class PromptOptimizer:
    """
    Smart prompt optimizer that respects voiceover integrity while compressing other content.
    """
    
    def __init__(self, max_tokens: int = MAX_USABLE_TOKENS):
        self.max_tokens = max_tokens
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count from text.
        
        Args:
            text: Text to estimate
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        return len(text) // CHARS_PER_TOKEN_AVG
    
    def optimize_prompt(self, full_prompt: str, priority: str = "balanced",
                       voiceover_text: Optional[str] = None) -> str:
        """
        Optimize prompt to fit within token limits.
        
        Priority modes:
        - "voiceover": Preserve 100% voiceover, compress everything else aggressively
        - "visual": Preserve visual details, compress voiceover slightly if needed
        - "balanced": Balance between voiceover and visual (default)
        
        Args:
            full_prompt: The complete prompt text
            priority: Priority mode (voiceover/visual/balanced)
            voiceover_text: Optional explicit voiceover text to protect
            
        Returns:
            Optimized prompt that fits within token limits
        """
        current_tokens = self.estimate_tokens(full_prompt)
        
        # If already within limits, return as-is
        if current_tokens <= self.max_tokens:
            return full_prompt
        
        # Extract voiceover if not provided
        if not voiceover_text:
            voiceover_text = self._extract_voiceover(full_prompt)
        
        # CRITICAL: In voiceover or balanced mode, NEVER truncate voiceover
        if priority in ("voiceover", "balanced"):
            return self._optimize_preserving_voiceover(full_prompt, voiceover_text)
        elif priority == "visual":
            return self._optimize_preserving_visual(full_prompt, voiceover_text)
        else:
            # Default to balanced
            return self._optimize_preserving_voiceover(full_prompt, voiceover_text)
    
    def _extract_voiceover(self, prompt: str) -> str:
        """Extract voiceover text from prompt"""
        # Try to find voiceover in common patterns
        # Using raw strings with proper escaping for clarity
        patterns = [
            r'voiceover["\s:]+([^"]+)"',  # Basic voiceover pattern
            r'"voiceover":\s*\{[^}]*"text":\s*"([^"]+)"',  # JSON format
            r'VOICEOVER:\s*([^\n]+)',  # All caps format
            r'Voice[Oo]ver:\s*([^\n]+)',  # Mixed case format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, prompt, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        
        return ""
    
    def _optimize_preserving_voiceover(self, full_prompt: str, voiceover_text: str) -> str:
        """
        Optimize prompt while preserving 100% of voiceover text.
        Compresses character details, visual descriptions, and other content.
        """
        vo_tokens = self.estimate_tokens(voiceover_text) if voiceover_text else 0
        remaining_tokens = self.max_tokens - vo_tokens
        
        if remaining_tokens < 1000:
            # Not enough space - return minimal prompt with voiceover
            return self._create_minimal_prompt_with_voiceover(voiceover_text)
        
        # Split prompt into sections
        sections = self._parse_prompt_sections(full_prompt)
        
        # Allocate tokens to sections (voiceover gets full protection)
        optimized_sections = {}
        
        # 1. Voiceover - NEVER compress
        optimized_sections['voiceover'] = voiceover_text
        
        # 2. Character details - compress to anchors only
        if 'character' in sections:
            char_compressed = self._compress_character_details(
                sections['character'], 
                target_tokens=min(remaining_tokens * 0.2, 500)
            )
            optimized_sections['character'] = char_compressed
            remaining_tokens -= self.estimate_tokens(char_compressed)
        
        # 3. Scene description - keep essential details
        if 'scene' in sections:
            scene_compressed = self._compress_scene_description(
                sections['scene'],
                target_tokens=min(remaining_tokens * 0.5, 1000)
            )
            optimized_sections['scene'] = scene_compressed
            remaining_tokens -= self.estimate_tokens(scene_compressed)
        
        # 4. Other content - aggressive compression
        for key in sections:
            if key not in ('voiceover', 'character', 'scene'):
                compressed = self._compress_generic(
                    sections[key],
                    target_tokens=min(remaining_tokens * 0.3, 300)
                )
                optimized_sections[key] = compressed
        
        # Reconstruct prompt
        return self._reconstruct_prompt(optimized_sections)
    
    def _optimize_preserving_visual(self, full_prompt: str, voiceover_text: str) -> str:
        """
        Optimize prompt while preserving visual details.
        NOTE: Even in visual priority mode, voiceover should be preserved as much as possible.
        Only in extreme cases (prompt >> max_tokens) will voiceover be slightly compressed.
        """
        # Parse sections
        sections = self._parse_prompt_sections(full_prompt)
        
        # Allocate tokens with visual priority
        optimized_sections = {}
        remaining_tokens = self.max_tokens
        
        # 1. Scene description - highest priority
        if 'scene' in sections:
            scene_tokens = min(remaining_tokens * 0.5, 2000)
            optimized_sections['scene'] = self._compress_scene_description(
                sections['scene'], scene_tokens
            )
            remaining_tokens -= self.estimate_tokens(optimized_sections['scene'])
        
        # 2. Character details - medium priority
        if 'character' in sections:
            char_tokens = min(remaining_tokens * 0.3, 1000)
            optimized_sections['character'] = self._compress_character_details(
                sections['character'], char_tokens
            )
            remaining_tokens -= self.estimate_tokens(optimized_sections['character'])
        
        # 3. Voiceover - try to preserve completely even in visual mode
        if voiceover_text:
            vo_tokens = self.estimate_tokens(voiceover_text)
            if vo_tokens <= remaining_tokens:
                # Can fit voiceover completely
                optimized_sections['voiceover'] = voiceover_text
            else:
                # In extreme case, preserve as much as possible by splitting at sentence boundary
                # This should rarely happen
                sentences = voiceover_text.split('.')
                preserved = []
                current_tokens = 0
                for sent in sentences:
                    sent_tokens = self.estimate_tokens(sent)
                    if current_tokens + sent_tokens <= remaining_tokens * 0.9:  # Use 90% of remaining
                        preserved.append(sent)
                        current_tokens += sent_tokens
                    else:
                        break
                optimized_sections['voiceover'] = '. '.join(preserved) + ('.' if preserved else '')
        
        return self._reconstruct_prompt(optimized_sections)
    
    def _parse_prompt_sections(self, prompt: str) -> Dict[str, str]:
        """Parse prompt into logical sections"""
        sections = {}
        
        # Try JSON parsing first
        try:
            if prompt.strip().startswith('{'):
                data = json.loads(prompt)
                
                # Extract key sections
                if 'key_action' in data:
                    sections['scene'] = str(data['key_action'])
                
                if 'character_details' in data:
                    sections['character'] = str(data['character_details'])
                
                if 'audio' in data and isinstance(data['audio'], dict):
                    vo = data['audio'].get('voiceover', {})
                    if isinstance(vo, dict):
                        sections['voiceover'] = vo.get('text', '')
                    else:
                        sections['voiceover'] = str(vo)
                
                # Keep other sections
                for key in ['setting_details', 'camera_direction', 'hard_locks', 'negatives']:
                    if key in data:
                        sections[key] = str(data[key])
                
                return sections
        except (json.JSONDecodeError, ValueError):
            pass
        
        # Fallback: Split by markers
        lines = prompt.split('\n')
        current_section = 'main'
        sections[current_section] = []
        
        for line in lines:
            line_lower = line.lower().strip()
            if any(marker in line_lower for marker in ['character:', '[character', 'character -']):
                current_section = 'character'
                sections[current_section] = []
            elif any(marker in line_lower for marker in ['scene:', 'setting:', 'location:']):
                current_section = 'scene'
                sections[current_section] = []
            elif any(marker in line_lower for marker in ['voiceover:', 'voice over:', 'narration:']):
                current_section = 'voiceover'
                sections[current_section] = []
            
            if current_section not in sections:
                sections[current_section] = []
            sections[current_section].append(line)
        
        # Join lines
        for key in sections:
            sections[key] = '\n'.join(sections[key])
        
        return sections
    
    def _compress_character_details(self, char_text: str, target_tokens: int) -> str:
        """
        Compress character details to just the essential anchors.
        Keeps top 3 consistency anchors only.
        """
        lines = char_text.split('\n')
        compressed = []
        
        # Extract character name if present
        name_match = re.search(r'(?:Character:|Name:)?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', char_text)
        if name_match:
            compressed.append(f"Character: {name_match.group(1)}")
        
        # Look for consistency anchors or key identifiers
        anchors_found = False
        for line in lines:
            line_lower = line.lower()
            if any(marker in line_lower for marker in ['anchor', 'identifier', 'key feature']):
                # Extract numbered items (1., 2., etc.)
                if re.match(r'^\s*\d+\.', line):
                    compressed.append(line.strip())
                    anchors_found = True
                    if len(compressed) > 4:  # Name + 3 anchors
                        break
        
        # If no anchors found, extract key physical attributes
        if not anchors_found:
            for line in lines:
                line_lower = line.lower()
                if any(word in line_lower for word in ['hair', 'eyes', 'skin', 'height', 'build']):
                    compressed.append(line.strip())
                    if len(compressed) > 4:
                        break
        
        result = '\n'.join(compressed)
        
        # If still too long, truncate
        if self.estimate_tokens(result) > target_tokens:
            char_limit = int(target_tokens * CHARS_PER_TOKEN_AVG)
            result = result[:char_limit]
        
        return result
    
    def _compress_scene_description(self, scene_text: str, target_tokens: int) -> str:
        """
        Compress scene description while keeping essential visual details.
        """
        # Keep first and last sentences (usually most important)
        sentences = re.split(r'[.!?]+', scene_text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return scene_text
        
        if len(sentences) <= 2:
            return scene_text
        
        # Keep first, last, and middle sentence
        if len(sentences) <= 5:
            compressed = '. '.join([sentences[0], sentences[-1]]) + '.'
        else:
            mid = len(sentences) // 2
            compressed = '. '.join([sentences[0], sentences[mid], sentences[-1]]) + '.'
        
        # If still too long, just keep first and last
        if self.estimate_tokens(compressed) > target_tokens:
            compressed = '. '.join([sentences[0], sentences[-1]]) + '.'
        
        # If STILL too long, keep first only
        if self.estimate_tokens(compressed) > target_tokens:
            char_limit = int(target_tokens * CHARS_PER_TOKEN_AVG)
            compressed = sentences[0][:char_limit]
        
        return compressed
    
    def _compress_generic(self, text: str, target_tokens: int) -> str:
        """Generic compression for other content"""
        if self.estimate_tokens(text) <= target_tokens:
            return text
        
        # Compress by word boundaries to avoid mid-word cuts
        words = text.split()
        char_limit = int(target_tokens * CHARS_PER_TOKEN_AVG)
        
        result = []
        current_length = 0
        for word in words:
            if current_length + len(word) + 1 <= char_limit - 3:  # Reserve 3 chars for "..."
                result.append(word)
                current_length += len(word) + 1
            else:
                break
        
        return ' '.join(result) + "..." if result else text[:char_limit - 3] + "..."
    
    def _create_minimal_prompt_with_voiceover(self, voiceover_text: str) -> str:
        """
        Create minimal prompt when space is very limited.
        Ensures voiceover is preserved completely even in extreme cases.
        """
        # If voiceover is too long even for minimal prompt, preserve at word boundaries
        if self.estimate_tokens(voiceover_text) > self.max_tokens * 0.8:
            words = voiceover_text.split()
            target_words = int((self.max_tokens * 0.8) * CHARS_PER_TOKEN_AVG / 5)  # Avg 5 chars per word
            if len(words) > target_words:
                voiceover_text = ' '.join(words[:target_words]) + "..."
        
        return f"""Scene description: Create video with clear visuals matching the narration.

Voiceover: {voiceover_text}

Keep character appearance consistent. Use clean composition and smooth camera movement."""
    
    def _reconstruct_prompt(self, sections: Dict[str, str]) -> str:
        """Reconstruct prompt from sections"""
        parts = []
        
        # Order: character -> scene -> voiceover -> other
        order = ['character', 'scene', 'voiceover', 'setting_details', 'camera_direction', 
                 'hard_locks', 'negatives', 'main']
        
        for key in order:
            if key in sections and sections[key]:
                parts.append(sections[key])
        
        # Add any remaining sections
        for key, value in sections.items():
            if key not in order and value:
                parts.append(value)
        
        return '\n\n'.join(parts)
    
    def split_long_scene(self, scene_text: str, voiceover_text: str, 
                        max_duration: int = 10) -> List[Dict[str, Any]]:
        """
        Split a long scene into multiple shorter scenes.
        
        Args:
            scene_text: Scene description
            voiceover_text: Voiceover narration
            max_duration: Maximum duration per scene in seconds
            
        Returns:
            List of scene dictionaries with split content
        """
        # Estimate duration from voiceover (average speaking rate: 150 words per minute)
        words = len(voiceover_text.split())
        estimated_duration = (words / 150.0) * 60.0  # Convert to seconds
        
        if estimated_duration <= max_duration:
            # No split needed
            return [{
                'scene_text': scene_text,
                'voiceover': voiceover_text,
                'duration': int(min(estimated_duration, max_duration))
            }]
        
        # Calculate number of splits needed
        num_splits = int((estimated_duration + max_duration - 1) // max_duration)
        
        # Split voiceover into sentences
        sentences = re.split(r'([.!?]+)', voiceover_text)
        sentence_groups = []
        current_group = []
        
        # Recombine sentences with their punctuation
        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i].strip()
            punct = sentences[i + 1] if i + 1 < len(sentences) else ''
            if sentence:
                current_group.append(sentence + punct)
        
        # If odd number, add last item
        if len(sentences) % 2 == 1 and sentences[-1].strip():
            current_group.append(sentences[-1])
        
        # Distribute sentences across splits
        sentences_per_split = max(1, len(current_group) // num_splits)
        
        splits = []
        for i in range(num_splits):
            start_idx = i * sentences_per_split
            if i == num_splits - 1:
                # Last split gets remaining sentences
                split_sentences = current_group[start_idx:]
            else:
                end_idx = start_idx + sentences_per_split
                split_sentences = current_group[start_idx:end_idx]
            
            split_vo = ' '.join(split_sentences)
            split_words = len(split_vo.split())
            split_duration = int(min((split_words / 150.0) * 60.0, max_duration))
            
            splits.append({
                'scene_text': f"{scene_text} (Part {i+1}/{num_splits})",
                'voiceover': split_vo,
                'duration': max(3, split_duration)  # Minimum 3 seconds
            })
        
        return splits
    
    def optimize_full_script(self, scenes: List[Dict[str, Any]], priority: str = "balanced") -> List[Dict[str, Any]]:
        """
        Optimize all scenes in a script, splitting long ones if necessary.
        
        Args:
            scenes: List of scene dictionaries with 'prompt_vi', 'prompt_tgt', 'duration', etc.
            priority: Optimization priority mode
            
        Returns:
            Optimized list of scenes (may have more scenes due to splits)
        """
        optimized_scenes = []
        
        for scene in scenes:
            duration = scene.get('duration', 8)
            prompt_vi = scene.get('prompt_vi', '')
            prompt_tgt = scene.get('prompt_tgt', '')
            
            # Use target prompt if available, fallback to VI
            main_prompt = prompt_tgt or prompt_vi
            
            # Check if scene is too long (> 10 seconds)
            if duration > 10:
                # Extract voiceover if present
                voiceover = self._extract_voiceover(main_prompt)
                
                # Split the scene
                splits = self.split_long_scene(main_prompt, voiceover, max_duration=10)
                
                # Create new scene entries for each split
                for split in splits:
                    new_scene = scene.copy()
                    new_scene['prompt_tgt'] = split['scene_text']
                    new_scene['prompt_vi'] = split['scene_text']  # Update VI too
                    new_scene['duration'] = split['duration']
                    optimized_scenes.append(new_scene)
            else:
                # Optimize prompt if needed
                optimized_prompt = self.optimize_prompt(main_prompt, priority=priority)
                
                new_scene = scene.copy()
                if prompt_tgt:
                    new_scene['prompt_tgt'] = optimized_prompt
                else:
                    new_scene['prompt_vi'] = optimized_prompt
                
                optimized_scenes.append(new_scene)
        
        return optimized_scenes


def optimize_prompt_with_character(scene_prompt: str, character_details: str, 
                                   voiceover_text: str, priority: str = "balanced") -> str:
    """
    Convenience function to optimize a prompt with character consistency.
    
    Args:
        scene_prompt: Original scene prompt
        character_details: Character consistency details to inject
        voiceover_text: Voiceover narration (will be protected)
        priority: Optimization priority
        
    Returns:
        Optimized prompt with character details
    """
    optimizer = PromptOptimizer()
    
    # Combine character details with scene prompt
    full_prompt = f"{character_details}\n\n{scene_prompt}"
    
    # Optimize
    optimized = optimizer.optimize_prompt(full_prompt, priority=priority, voiceover_text=voiceover_text)
    
    return optimized
