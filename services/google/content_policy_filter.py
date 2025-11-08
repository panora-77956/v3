# -*- coding: utf-8 -*-
"""
Google Labs Content Policy Filter
Sanitizes prompts to comply with Google's content policies, especially regarding minors.

This module detects and rewrites prompts that may violate Google's policies about
creating content featuring minors (children/teenagers under 18).
"""

import re
from typing import Dict, List, Tuple, Any

# Keywords that indicate child/minor characters (Vietnamese + English)
MINOR_KEYWORDS_VI = [
    "cô bé", "cậu bé", "em bé", "bé gái", "bé trai",
    "trẻ em", "trẻ con", "thiếu nhi", "nhi đồng",
    "học sinh", "tiểu học", "cấp 1", "cấp 2",
    "trẻ vị thành niên", "vị thành niên", "thiếu niên",
    "con nít", "trẻ nhỏ", "trẻ thơ",
    # Context-specific: characters described as children
    "bé", "nhỏ tuổi", "thơ ấu", "tuổi thơ"
]

MINOR_KEYWORDS_EN = [
    "little girl", "little boy", "child", "kid", "children",
    "young girl", "young boy", "toddler", "infant", "baby",
    "minor", "underage", "teenager", "teen", "adolescent",
    "school child", "elementary", "middle school",
    "juvenile", "youth"
]

# Age-related patterns (detect specific ages under 18)
AGE_PATTERN_VI = re.compile(
    r'\b(\d{1,2})\s*(?:tuổi|năm)\b',
    re.IGNORECASE
)

AGE_PATTERN_EN = re.compile(
    r'\b(\d{1,2})\s*(?:years?\s*old|year-old|yo)\b',
    re.IGNORECASE
)

# Replacement mappings for age-up
AGE_UP_REPLACEMENTS_VI = {
    "cô bé": "cô gái trẻ",
    "cậu bé": "chàng trai trẻ",
    "em bé": "người trẻ",
    "bé gái": "cô gái trẻ",
    "bé trai": "chàng trai trẻ",
    "trẻ em": "người trẻ tuổi",
    "trẻ con": "người trẻ",
    "thiếu nhi": "thanh niên",
    "nhi đồng": "thanh niên",
    "học sinh": "sinh viên",
    "tiểu học": "đại học",
    "cấp 1": "trường đại học",
    "cấp 2": "trường đại học",
    "trẻ vị thành niên": "thanh niên",
    "vị thành niên": "thanh niên",
    "thiếu niên": "thanh niên",
    "con nít": "người trẻ",
    "trẻ nhỏ": "người trẻ tuổi",
    "trẻ thơ": "người trẻ",
    "bé": "người",
    "nhỏ tuổi": "trẻ tuổi",
    "thơ ấu": "trẻ trung",
    "tuổi thơ": "tuổi trẻ"
}

AGE_UP_REPLACEMENTS_EN = {
    "little girl": "young woman",
    "little boy": "young man",
    "child": "young adult",
    "kid": "young person",
    "children": "young people",
    "young girl": "young woman",
    "young boy": "young man",
    "toddler": "young adult",
    "infant": "young adult",
    "baby": "young person",
    "minor": "young adult",
    "underage": "young adult",
    "teenager": "young adult",
    "teen": "young adult",
    "adolescent": "young adult",
    "school child": "young student",
    "elementary": "university",
    "middle school": "university",
    "juvenile": "young person",
    "youth": "young adult"
}


class ContentPolicyViolation(Exception):
    """Raised when content cannot be sanitized to comply with policies"""
    pass


class ContentPolicyFilter:
    """
    Filter to detect and sanitize content that may violate Google's content policies.
    
    Main focus: Detecting and age-up characters described as minors (under 18)
    to comply with Google's policies about creating content featuring children.
    """
    
    def __init__(self, enable_age_up: bool = True, min_age: int = 18, strict_mode: bool = False):
        """
        Initialize content policy filter.
        
        Args:
            enable_age_up: If True, automatically age up minor characters
            min_age: Minimum age for characters (default 18)
            strict_mode: If True, raise exception instead of sanitizing
        """
        self.enable_age_up = enable_age_up
        self.min_age = min_age
        self.strict_mode = strict_mode
        self.violations_found = []
    
    def detect_minor_references(self, text: str) -> List[Tuple[str, str]]:
        """
        Detect references to minors in text.
        
        Returns:
            List of (keyword, language) tuples found in text
        """
        found = []
        text_lower = text.lower()
        
        # Check Vietnamese keywords
        for keyword in MINOR_KEYWORDS_VI:
            if keyword in text_lower:
                found.append((keyword, "vi"))
        
        # Check English keywords
        for keyword in MINOR_KEYWORDS_EN:
            if keyword in text_lower:
                found.append((keyword, "en"))
        
        # Check age patterns
        for match in AGE_PATTERN_VI.finditer(text):
            age = int(match.group(1))
            if age < self.min_age:
                found.append((match.group(0), "vi_age"))
        
        for match in AGE_PATTERN_EN.finditer(text):
            age = int(match.group(1))
            if age < self.min_age:
                found.append((match.group(0), "en_age"))
        
        return found
    
    def age_up_text(self, text: str) -> str:
        """
        Age up characters in text by replacing minor-related keywords.
        
        Args:
            text: Text to process
        
        Returns:
            Text with minor references replaced with adult equivalents
        """
        result = text
        
        # Replace Vietnamese keywords (case-insensitive, preserve case)
        for keyword, replacement in AGE_UP_REPLACEMENTS_VI.items():
            # Case-insensitive replacement preserving original case
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            result = pattern.sub(replacement, result)
        
        # Replace English keywords (case-insensitive, preserve case)
        for keyword, replacement in AGE_UP_REPLACEMENTS_EN.items():
            pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
            result = pattern.sub(replacement, result)
        
        # Age up specific ages (e.g., "12 tuổi" -> "20 tuổi")
        def age_replacer_vi(match):
            age = int(match.group(1))
            if age < self.min_age:
                # Age up to 20 (safe minimum adult age)
                return f"20 {match.group(0).split()[-1]}"
            return match.group(0)
        
        result = AGE_PATTERN_VI.sub(age_replacer_vi, result)
        
        def age_replacer_en(match):
            age = int(match.group(1))
            if age < self.min_age:
                # Age up to 20 (safe minimum adult age)
                suffix = match.group(0).split(str(age))[-1]
                return f"20{suffix}"
            return match.group(0)
        
        result = AGE_PATTERN_EN.sub(age_replacer_en, result)
        
        return result
    
    def sanitize_prompt_dict(self, prompt_data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """
        Sanitize a prompt dictionary (JSON prompt structure).
        
        Args:
            prompt_data: Prompt dictionary to sanitize
        
        Returns:
            Tuple of (sanitized_prompt_data, list_of_warnings)
        """
        warnings = []
        sanitized = prompt_data.copy()
        
        # Fields to check and sanitize
        fields_to_check = [
            "character_details",
            "key_action",
            "setting_details",
            "objective",
        ]
        
        # Check Task_Instructions if present
        if "Task_Instructions" in sanitized and isinstance(sanitized["Task_Instructions"], list):
            new_instructions = []
            for instruction in sanitized["Task_Instructions"]:
                violations = self.detect_minor_references(str(instruction))
                if violations:
                    if self.enable_age_up:
                        sanitized_instruction = self.age_up_text(str(instruction))
                        new_instructions.append(sanitized_instruction)
                        warnings.append(
                            f"Task instruction aged up: '{instruction[:50]}...' -> '{sanitized_instruction[:50]}...'"
                        )
                    else:
                        new_instructions.append(instruction)
                        warnings.append(f"Minor references detected in Task_Instructions: {violations}")
                else:
                    new_instructions.append(instruction)
            sanitized["Task_Instructions"] = new_instructions
        
        # Check and sanitize each field
        for field in fields_to_check:
            if field in sanitized and sanitized[field]:
                text = str(sanitized[field])
                violations = self.detect_minor_references(text)
                
                if violations:
                    if self.enable_age_up:
                        sanitized_text = self.age_up_text(text)
                        sanitized[field] = sanitized_text
                        warnings.append(
                            f"Field '{field}' aged up: {len(violations)} minor reference(s) replaced"
                        )
                    else:
                        warnings.append(
                            f"Field '{field}' contains minor references: {violations}"
                        )
        
        # Check localization prompts
        if "localization" in sanitized and isinstance(sanitized["localization"], dict):
            for lang, lang_data in sanitized["localization"].items():
                if isinstance(lang_data, dict) and "prompt" in lang_data:
                    text = str(lang_data["prompt"])
                    violations = self.detect_minor_references(text)
                    
                    if violations:
                        if self.enable_age_up:
                            sanitized_text = self.age_up_text(text)
                            sanitized["localization"][lang]["prompt"] = sanitized_text
                            warnings.append(
                                f"Localization '{lang}' aged up: {len(violations)} reference(s)"
                            )
                        else:
                            warnings.append(
                                f"Localization '{lang}' contains minor references"
                            )
        
        # Store violations for reporting
        self.violations_found = warnings
        
        return sanitized, warnings
    
    def sanitize_prompt_text(self, text: str) -> Tuple[str, List[str]]:
        """
        Sanitize a plain text prompt.
        
        Args:
            text: Text prompt to sanitize
        
        Returns:
            Tuple of (sanitized_text, list_of_warnings)
        """
        warnings = []
        violations = self.detect_minor_references(text)
        
        if violations:
            if self.enable_age_up:
                sanitized_text = self.age_up_text(text)
                warnings.append(
                    f"Text prompt aged up: {len(violations)} minor reference(s) replaced"
                )
                return sanitized_text, warnings
            else:
                warnings.append(f"Text contains minor references: {violations}")
                return text, warnings
        
        return text, warnings
    
    def check_compliance(self, prompt_data: Any) -> bool:
        """
        Check if prompt complies with content policies.
        
        Args:
            prompt_data: Prompt to check (string or dict)
        
        Returns:
            True if compliant, False if violations detected
        """
        if isinstance(prompt_data, str):
            violations = self.detect_minor_references(prompt_data)
            return len(violations) == 0
        elif isinstance(prompt_data, dict):
            # Check all fields
            all_text = []
            for key, value in prompt_data.items():
                if isinstance(value, str):
                    all_text.append(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            all_text.append(item)
            
            for text in all_text:
                violations = self.detect_minor_references(text)
                if violations:
                    return False
            return True
        
        return True


def sanitize_prompt_for_google_labs(prompt_data: Any, enable_age_up: bool = True) -> Tuple[Any, List[str]]:
    """
    Convenience function to sanitize prompts for Google Labs API.
    
    Args:
        prompt_data: Prompt to sanitize (string or dict)
        enable_age_up: If True, automatically age up minor characters
    
    Returns:
        Tuple of (sanitized_prompt, list_of_warnings)
    """
    filter = ContentPolicyFilter(enable_age_up=enable_age_up)
    
    if isinstance(prompt_data, str):
        return filter.sanitize_prompt_text(prompt_data)
    elif isinstance(prompt_data, dict):
        return filter.sanitize_prompt_dict(prompt_data)
    else:
        return prompt_data, []


# Example usage and testing
if __name__ == '__main__':
    # Test Vietnamese content
    test_text_vi = """
    Cô Bé Bán Diêm: Một cô bé 12 tuổi với mái tóc đen rối bời, 
    gương mặt xanh xao, đôi mắt to tròn. Cô bé đang ôm chặt hộp diêm.
    """
    
    filter = ContentPolicyFilter(enable_age_up=True)
    sanitized, warnings = filter.sanitize_prompt_text(test_text_vi)
    
    print("=" * 60)
    print("VIETNAMESE TEST")
    print("=" * 60)
    print("Original:", test_text_vi)
    print("\nSanitized:", sanitized)
    print("\nWarnings:", warnings)
    
    # Test English content
    test_text_en = """
    The Little Match Girl: A little girl, 12 years old, with dark messy hair,
    pale face, and large round eyes. The child is holding a matchbox.
    """
    
    sanitized_en, warnings_en = filter.sanitize_prompt_text(test_text_en)
    
    print("\n" + "=" * 60)
    print("ENGLISH TEST")
    print("=" * 60)
    print("Original:", test_text_en)
    print("\nSanitized:", sanitized_en)
    print("\nWarnings:", warnings_en)
    
    # Test dict/JSON prompt
    test_dict = {
        "character_details": "Cô Bé Bán Diêm (12 tuổi): Mái tóc đen rối bời",
        "key_action": "Cô bé quẹt diêm",
        "Task_Instructions": [
            "Character: cô bé đang run rẩy",
            "Scene: một cậu bé đi ngang qua"
        ]
    }
    
    sanitized_dict, warnings_dict = filter.sanitize_prompt_dict(test_dict)
    
    print("\n" + "=" * 60)
    print("DICT/JSON TEST")
    print("=" * 60)
    print("Original:", test_dict)
    print("\nSanitized:", sanitized_dict)
    print("\nWarnings:", warnings_dict)
    
    print("\n✅ Content policy filter tests completed!")
