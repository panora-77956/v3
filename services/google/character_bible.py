# -*- coding: utf-8 -*-
"""
Character Bible System for Text2Video
Ensures character consistency across all video scenes with detailed physical descriptions and unique identifiers.
"""

import json
import re
from typing import Dict, List, Optional, Any


class CharacterBible:
    """
    Character Bible System that maintains detailed character descriptions
    with 5 unique consistency anchors per character.
    """
    
    def __init__(self):
        self.characters: List[Dict[str, Any]] = []
    
    def add_character(self, character_data: Dict[str, Any]) -> None:
        """Add a character to the bible"""
        self.characters.append(character_data)
    
    def get_character(self, name: str) -> Optional[Dict[str, Any]]:
        """Get character by name"""
        for char in self.characters:
            if char.get("name", "").lower() == name.lower():
                return char
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {"characters": self.characters}
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CharacterBible':
        """Create from dictionary"""
        bible = cls()
        bible.characters = data.get("characters", [])
        return bible
    
    @classmethod
    def from_json(cls, json_str: str) -> 'CharacterBible':
        """Create from JSON string"""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")


def create_character_bible(video_concept: str, script: str, 
                           existing_bible: Optional[List[Dict]] = None) -> CharacterBible:
    """
    Generate a detailed character bible from video concept and script.
    
    Args:
        video_concept: The main video concept/idea
        script: The screenplay/script text
        existing_bible: Optional existing character bible from LLM generation
        
    Returns:
        CharacterBible object with detailed character descriptions
    """
    bible = CharacterBible()
    
    # If we have existing bible from LLM, enhance it with consistency anchors
    if existing_bible and isinstance(existing_bible, list):
        for char_data in existing_bible:
            enhanced_char = _enhance_character_with_anchors(char_data, script)
            bible.add_character(enhanced_char)
    else:
        # Extract characters from script if no bible provided
        characters = _extract_characters_from_script(script, video_concept)
        for char in characters:
            bible.add_character(char)
    
    return bible


def _enhance_character_with_anchors(char_data: Dict[str, Any], script: str) -> Dict[str, Any]:
    """
    Enhance existing character data with detailed physical descriptions and consistency anchors.
    
    Args:
        char_data: Existing character data (name, role, key_trait, etc.)
        script: Script text for context
        
    Returns:
        Enhanced character dictionary with full physical blueprint
    """
    name = char_data.get("name", "Character")
    role = char_data.get("role", "")
    visual_identity = char_data.get("visual_identity", "")
    
    # Create detailed physical blueprint
    enhanced = {
        "name": name,
        "role": role,
        "key_trait": char_data.get("key_trait", ""),
        "motivation": char_data.get("motivation", ""),
        "default_behavior": char_data.get("default_behavior", ""),
        "archetype": char_data.get("archetype", ""),
        "fatal_flaw": char_data.get("fatal_flaw", ""),
        "goal_external": char_data.get("goal_external", ""),
        "goal_internal": char_data.get("goal_internal", ""),
        
        # Physical Blueprint (from visual_identity + defaults)
        "physical_blueprint": {
            "age_range": _extract_age(visual_identity, role),
            "race_ethnicity": _extract_ethnicity(visual_identity),
            "height": _extract_height(visual_identity),
            "build": _extract_build(visual_identity, role),
            "skin_tone": _extract_skin_tone(visual_identity),
        },
        
        # Hair DNA
        "hair_dna": {
            "color": _extract_hair_color(visual_identity),
            "length": _extract_hair_length(visual_identity),
            "style": _extract_hair_style(visual_identity),
            "texture": _extract_hair_texture(visual_identity),
        },
        
        # Eye Signature
        "eye_signature": {
            "color": _extract_eye_color(visual_identity),
            "shape": _extract_eye_shape(visual_identity),
            "expression": _extract_eye_expression(char_data.get("key_trait", "")),
        },
        
        # Facial Map
        "facial_map": {
            "nose": _extract_nose(visual_identity),
            "lips": _extract_lips(visual_identity),
            "jawline": _extract_jawline(visual_identity),
            "distinguishing_marks": _extract_marks(visual_identity),
        },
        
        # 5 Unique Consistency Anchors
        "consistency_anchors": _generate_consistency_anchors(name, role, visual_identity, char_data),
        
        # Scene Reminder Phrases
        "scene_reminders": _generate_scene_reminders(name, role, char_data),
        
        # Original visual identity for reference
        "visual_identity": visual_identity,
    }
    
    return enhanced


def _extract_characters_from_script(script: str, concept: str) -> List[Dict[str, Any]]:
    """
    Extract characters from script when no bible is provided.
    This is a fallback method that creates basic character entries.
    """
    characters = []
    
    # Simple extraction: Look for dialogue patterns (CHARACTER: dialogue)
    # More flexible pattern to catch names like "Dr. Smith", "Mary-Jane", etc.
    # Note: \- and \. are escaped for clarity, though - in character class doesn't need escaping at end
    dialogue_pattern = r'^([A-Z][a-zA-Z\s\-\.]+):\s*(.+)$'
    names = set()
    
    for line in script.split('\n'):
        match = re.match(dialogue_pattern, line.strip())
        if match:
            name = match.group(1).strip().title()
            names.add(name)
    
    # If no dialogues found, create a generic character
    if not names:
        names.add("Main Character")
    
    # Create basic character entries
    for name in names:
        char = {
            "name": name,
            "role": "Main" if name == list(names)[0] else "Supporting",
            "key_trait": "determined",
            "motivation": "achieve goal",
            "default_behavior": "focused",
            "visual_identity": f"{name} - consistent appearance",
            "archetype": "Protagonist" if name == list(names)[0] else "Supporting",
            "fatal_flaw": "none",
            "goal_external": "complete objective",
            "goal_internal": "grow",
            "physical_blueprint": {
                "age_range": "25-35",
                "race_ethnicity": "diverse",
                "height": "average",
                "build": "average",
                "skin_tone": "medium",
            },
            "hair_dna": {
                "color": "dark brown",
                "length": "medium",
                "style": "neat",
                "texture": "straight",
            },
            "eye_signature": {
                "color": "brown",
                "shape": "almond",
                "expression": "focused",
            },
            "facial_map": {
                "nose": "average",
                "lips": "medium",
                "jawline": "defined",
                "distinguishing_marks": "none",
            },
            "consistency_anchors": [
                f"1. Consistent facial features for {name}",
                f"2. Same clothing style throughout",
                f"3. Maintains {name}'s demeanor",
                f"4. Recognizable silhouette",
                f"5. Consistent voice/presence",
            ],
            "scene_reminders": [
                f"Remember {name}'s appearance",
                f"Keep {name}'s style consistent",
                f"Maintain {name}'s character traits",
            ],
        }
        characters.append(char)
    
    return characters


def _generate_consistency_anchors(name: str, role: str, visual_identity: str, 
                                   char_data: Dict[str, Any]) -> List[str]:
    """
    Generate 5 unique consistency anchors for the character.
    These are specific, unchanging visual identifiers that persist across all scenes.
    """
    anchors = []
    
    # Parse visual_identity for specific details
    vi_lower = visual_identity.lower()
    
    # Try to extract specific visual details from visual_identity
    potential_anchors = []
    
    # Check for accessories
    if "glasses" in vi_lower or "spectacles" in vi_lower:
        potential_anchors.append("Wears distinctive glasses/spectacles")
    if "necklace" in vi_lower:
        potential_anchors.append("Gold/silver necklace always visible")
    if "watch" in vi_lower:
        potential_anchors.append("Wears watch on left/right wrist")
    if "ring" in vi_lower:
        potential_anchors.append("Distinctive ring on finger")
    if "earring" in vi_lower:
        potential_anchors.append("Wears earrings")
    
    # Check for marks/tattoos
    if "tattoo" in vi_lower:
        potential_anchors.append("Visible tattoo on wrist/arm")
    if "scar" in vi_lower:
        potential_anchors.append("Small scar visible on face/hand")
    if "beauty mark" in vi_lower or "mole" in vi_lower:
        potential_anchors.append("Beauty mark/mole in specific location")
    if "freckle" in vi_lower:
        potential_anchors.append("Freckles pattern on face")
    
    # Check for clothing
    if "shirt" in vi_lower:
        color = _extract_color_near_word(visual_identity, "shirt")
        potential_anchors.append(f"{color or 'Specific color'} shirt")
    if "dress" in vi_lower:
        potential_anchors.append("Signature dress style")
    if "jacket" in vi_lower:
        potential_anchors.append("Distinctive jacket always worn")
    if "apron" in vi_lower:
        potential_anchors.append("Apron worn (specific color/style)")
    
    # Hair specific
    if "ponytail" in vi_lower:
        potential_anchors.append("Hair always in ponytail")
    if "bun" in vi_lower:
        potential_anchors.append("Hair tied in bun")
    if "braid" in vi_lower:
        potential_anchors.append("Hair in braid style")
    if "tucked" in vi_lower or "behind ear" in vi_lower:
        potential_anchors.append("Hair tucked behind left ear")
    
    # Use found anchors, or create generic ones
    if potential_anchors:
        # Take up to 5 unique anchors
        anchors = potential_anchors[:5]
    
    # Fill remaining slots with generic but specific anchors
    generic_anchors = [
        f"Consistent facial structure for {name}",
        f"Same body proportions throughout",
        f"Maintains specific posture/stance",
        f"Recognizable silhouette and outline",
        f"Consistent skin tone and complexion",
        f"Same eye color and shape",
        f"Identical hair color and style",
        f"Same clothing color palette",
        f"Consistent height relative to surroundings",
        f"Maintains specific mannerisms",
    ]
    
    while len(anchors) < 5:
        for anchor in generic_anchors:
            if anchor not in anchors:
                anchors.append(anchor)
                if len(anchors) >= 5:
                    break
    
    # Number the anchors
    return [f"{i+1}. {anchor}" for i, anchor in enumerate(anchors[:5])]


def _generate_scene_reminders(name: str, role: str, char_data: Dict[str, Any]) -> List[str]:
    """
    Generate scene reminder phrases to include in every scene prompt.
    """
    key_trait = char_data.get("key_trait", "")
    visual = char_data.get("visual_identity", "")
    
    reminders = [
        f"Character {name} maintains consistent appearance",
        f"Same face, body, and features as previous scenes",
        f"Keep {name}'s visual identity: {visual[:50]}..." if visual else f"Keep {name}'s appearance",
    ]
    
    if key_trait:
        reminders.append(f"{name} exhibits {key_trait} trait")
    
    reminders.append(f"No changes to {name}'s outfit or hair between scenes")
    
    return reminders


# Helper extraction functions
def _extract_age(visual_identity: str, role: str) -> str:
    """Extract age range from visual identity or infer from role"""
    vi_lower = visual_identity.lower()
    if "young" in vi_lower or "teen" in vi_lower:
        return "18-25"
    if "old" in vi_lower or "elder" in vi_lower or "senior" in vi_lower:
        return "60-70"
    if "middle" in vi_lower:
        return "40-50"
    return "25-35"  # default


def _extract_ethnicity(visual_identity: str) -> str:
    """Extract ethnicity/race from visual identity"""
    vi_lower = visual_identity.lower()
    if "asian" in vi_lower or "việt" in vi_lower or "vietnamese" in vi_lower:
        return "Asian/Vietnamese"
    if "african" in vi_lower or "black" in vi_lower:
        return "African"
    if "latin" in vi_lower or "hispanic" in vi_lower:
        return "Latin/Hispanic"
    if "caucasian" in vi_lower or "white" in vi_lower:
        return "Caucasian"
    return "diverse"


def _extract_height(visual_identity: str) -> str:
    """Extract height from visual identity"""
    vi_lower = visual_identity.lower()
    if "tall" in vi_lower:
        return "tall (175-185cm)"
    if "short" in vi_lower:
        return "short (155-165cm)"
    return "average (165-175cm)"


def _extract_build(visual_identity: str, role: str) -> str:
    """Extract body build from visual identity"""
    vi_lower = visual_identity.lower()
    if "slim" in vi_lower or "thin" in vi_lower:
        return "slim"
    if "muscular" in vi_lower or "athletic" in vi_lower:
        return "athletic"
    if "heavy" in vi_lower or "large" in vi_lower:
        return "heavy-set"
    return "average"


def _extract_skin_tone(visual_identity: str) -> str:
    """Extract skin tone from visual identity"""
    vi_lower = visual_identity.lower()
    if "pale" in vi_lower or "fair" in vi_lower or "light" in vi_lower:
        return "fair/light"
    if "dark" in vi_lower:
        return "dark"
    if "tan" in vi_lower or "bronze" in vi_lower:
        return "tan/bronze"
    return "medium"


def _extract_hair_color(visual_identity: str) -> str:
    """Extract hair color from visual identity"""
    vi_lower = visual_identity.lower()
    colors = ["black", "brown", "blonde", "red", "gray", "white", "silver"]
    for color in colors:
        if color in vi_lower:
            return color
    return "dark brown"


def _extract_hair_length(visual_identity: str) -> str:
    """Extract hair length from visual identity"""
    vi_lower = visual_identity.lower()
    if "long" in vi_lower:
        return "long (shoulder length or below)"
    if "short" in vi_lower:
        return "short (above ears)"
    return "medium (ear to shoulder)"


def _extract_hair_style(visual_identity: str) -> str:
    """Extract hair style from visual identity"""
    vi_lower = visual_identity.lower()
    styles = ["ponytail", "bun", "braided", "straight", "curly", "wavy", "spiky"]
    for style in styles:
        if style in vi_lower:
            return style
    return "natural/neat"


def _extract_hair_texture(visual_identity: str) -> str:
    """Extract hair texture from visual identity"""
    vi_lower = visual_identity.lower()
    if "curly" in vi_lower:
        return "curly"
    if "wavy" in vi_lower:
        return "wavy"
    return "straight"


def _extract_eye_color(visual_identity: str) -> str:
    """Extract eye color from visual identity"""
    vi_lower = visual_identity.lower()
    colors = ["brown", "blue", "green", "hazel", "gray", "black"]
    for color in colors:
        if f"{color} eye" in vi_lower or f"eye {color}" in vi_lower:
            return color
    return "brown"


def _extract_eye_shape(visual_identity: str) -> str:
    """Extract eye shape from visual identity"""
    vi_lower = visual_identity.lower()
    if "almond" in vi_lower:
        return "almond"
    if "round" in vi_lower:
        return "round"
    if "narrow" in vi_lower:
        return "narrow"
    return "almond"


def _extract_eye_expression(key_trait: str) -> str:
    """Extract eye expression from key trait"""
    trait_lower = key_trait.lower()
    if "kind" in trait_lower or "warm" in trait_lower:
        return "warm/kind"
    if "stern" in trait_lower or "serious" in trait_lower:
        return "serious/focused"
    if "playful" in trait_lower or "mischief" in trait_lower:
        return "playful"
    return "alert/attentive"


def _extract_nose(visual_identity: str) -> str:
    """Extract nose description from visual identity"""
    vi_lower = visual_identity.lower()
    if "small nose" in vi_lower:
        return "small"
    if "large nose" in vi_lower or "prominent nose" in vi_lower:
        return "prominent"
    return "average"


def _extract_lips(visual_identity: str) -> str:
    """Extract lips description from visual identity"""
    vi_lower = visual_identity.lower()
    if "full lips" in vi_lower or "thick lips" in vi_lower:
        return "full"
    if "thin lips" in vi_lower:
        return "thin"
    return "medium"


def _extract_jawline(visual_identity: str) -> str:
    """Extract jawline description from visual identity"""
    vi_lower = visual_identity.lower()
    if "strong jaw" in vi_lower or "defined jaw" in vi_lower:
        return "strong/defined"
    if "soft jaw" in vi_lower or "rounded jaw" in vi_lower:
        return "soft/rounded"
    return "average"


def _extract_marks(visual_identity: str) -> str:
    """Extract distinguishing marks from visual identity"""
    vi_lower = visual_identity.lower()
    marks = []
    if "scar" in vi_lower:
        marks.append("scar")
    if "beauty mark" in vi_lower or "mole" in vi_lower:
        marks.append("beauty mark")
    if "tattoo" in vi_lower:
        marks.append("tattoo")
    if "freckle" in vi_lower:
        marks.append("freckles")
    
    return ", ".join(marks) if marks else "none"


def _extract_color_near_word(text: str, word: str) -> Optional[str]:
    """Extract color mentioned near a specific word"""
    # Note: 'gray' and 'grey' are both included to match different spellings
    colors = ["red", "blue", "green", "yellow", "white", "black", "gray", "grey", "purple", 
              "orange", "pink", "brown", "violet", "cyan", "magenta", "navy", "maroon", 
              "beige", "tan", "gold", "silver", "crimson", "indigo", "teal"]
    text_lower = text.lower()
    
    # Find position of word
    if word.lower() in text_lower:
        idx = text_lower.find(word.lower())
        # Check nearby text (20 chars before and after)
        nearby = text_lower[max(0, idx-20):min(len(text_lower), idx+len(word)+20)]
        for color in colors:
            if color in nearby:
                return color
    
    return None


def inject_character_consistency(scene_prompt: str, bible: CharacterBible, 
                                  character_names: Optional[List[str]] = None) -> str:
    """
    Inject character consistency details into a scene prompt.
    
    Args:
        scene_prompt: Original scene prompt
        bible: CharacterBible object
        character_names: Optional list of character names appearing in this scene
        
    Returns:
        Enhanced scene prompt with character consistency details
    """
    if not bible.characters:
        return scene_prompt
    
    # If no specific characters mentioned, use all characters
    if not character_names:
        characters_to_inject = bible.characters
    else:
        characters_to_inject = [
            char for char in bible.characters 
            if char.get("name", "").lower() in [n.lower() for n in character_names]
        ]
    
    if not characters_to_inject:
        return scene_prompt
    
    # Build character consistency block
    consistency_parts = []
    
    for char in characters_to_inject:
        name = char.get("name", "Character")
        char_block = [f"\n[{name} - CONSISTENT APPEARANCE]"]
        
        # Physical blueprint
        pb = char.get("physical_blueprint", {})
        if pb:
            char_block.append(f"Physical: {pb.get('age_range', '')} {pb.get('race_ethnicity', '')}, {pb.get('height', '')}, {pb.get('build', '')} build, {pb.get('skin_tone', '')} skin")
        
        # Hair DNA
        hair = char.get("hair_dna", {})
        if hair:
            char_block.append(f"Hair: {hair.get('color', '')} {hair.get('length', '')} {hair.get('style', '')} {hair.get('texture', '')}")
        
        # Eye signature
        eyes = char.get("eye_signature", {})
        if eyes:
            char_block.append(f"Eyes: {eyes.get('color', '')} {eyes.get('shape', '')} with {eyes.get('expression', '')} expression")
        
        # Consistency anchors (top 3 for scene prompts to avoid bloat)
        anchors = char.get("consistency_anchors", [])
        if anchors:
            char_block.append(f"Key identifiers: {', '.join([a.split('. ', 1)[1] if '. ' in a else a for a in anchors[:3]])}")
        
        consistency_parts.append(" | ".join(char_block))
    
    # Inject at the beginning of the prompt
    enhanced_prompt = "\n".join(consistency_parts) + "\n\n" + scene_prompt
    
    return enhanced_prompt


def extract_consistency_anchors(bible: CharacterBible) -> Dict[str, List[str]]:
    """
    Extract consistency anchors for all characters in the bible.
    
    Args:
        bible: CharacterBible object
        
    Returns:
        Dictionary mapping character names to their consistency anchors
    """
    result = {}
    for char in bible.characters:
        name = char.get("name", "Character")
        anchors = char.get("consistency_anchors", [])
        result[name] = anchors
    
    return result


def format_character_bible_for_display(bible: CharacterBible) -> str:
    """
    Format character bible for display in UI.
    
    Args:
        bible: CharacterBible object
        
    Returns:
        Formatted string for display
    """
    if not bible.characters:
        return "(No characters in bible)"
    
    parts = []
    parts.append("=== CHARACTER BIBLE ===\n")
    
    for i, char in enumerate(bible.characters, 1):
        name = char.get("name", "Character")
        role = char.get("role", "")
        
        parts.append(f"\n{i}. Character: {name} ({role})")
        parts.append("-" * 60)
        
        # Physical Blueprint
        pb = char.get("physical_blueprint", {})
        if pb:
            parts.append(f"Physical Blueprint: {pb.get('age_range', '')}, {pb.get('race_ethnicity', '')}, {pb.get('height', '')}, {pb.get('build', '')} build, {pb.get('skin_tone', '')} skin")
        
        # Hair DNA
        hair = char.get("hair_dna", {})
        if hair:
            parts.append(f"Hair DNA: {hair.get('color', '')} color, {hair.get('length', '')} length, {hair.get('style', '')} style, {hair.get('texture', '')} texture")
        
        # Eye Signature
        eyes = char.get("eye_signature", {})
        if eyes:
            parts.append(f"Eye Signature: {eyes.get('color', '')} color, {eyes.get('shape', '')} shape, {eyes.get('expression', '')} expression")
        
        # Facial Map
        face = char.get("facial_map", {})
        if face:
            parts.append(f"Facial Map: {face.get('nose', '')} nose, {face.get('lips', '')} lips, {face.get('jawline', '')} jawline, marks: {face.get('distinguishing_marks', '')}")
        
        # Consistency Anchors
        anchors = char.get("consistency_anchors", [])
        if anchors:
            parts.append("Consistency Anchors:")
            for anchor in anchors:
                parts.append(f"  {anchor}")
        
        # Scene Reminders
        reminders = char.get("scene_reminders", [])
        if reminders:
            parts.append("Scene Reminders:")
            for reminder in reminders[:3]:  # Show top 3
                parts.append(f"  • {reminder}")
        
        # Key Trait & Motivation
        if char.get("key_trait"):
            parts.append(f"Key Trait: {char.get('key_trait')}")
        if char.get("motivation"):
            parts.append(f"Motivation: {char.get('motivation')}")
        
        parts.append("")  # Empty line between characters
    
    return "\n".join(parts)
