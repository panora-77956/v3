# Content Policy Filter for Google Labs API

## Overview

This document describes the content policy filter implemented to prevent HTTP 400 errors when submitting prompts to Google Labs Flow API that contain references to minors (children/teenagers under 18 years old).

## Problem

Google Labs has strict content policies that prohibit generating content featuring minors. When prompts contain keywords or descriptions related to children, the API returns:

```
[ERROR] HTTP 400: Request contains an invalid argument.
```

In Vietnamese, the error message from Google Labs states:
```
Câu lệnh này có thể vi phạm chính sách của chúng tôi về việc tạo nội dung 
gây hại liên quan đến trẻ vị thành niên.
```

Translation: "This prompt may violate our policy on creating harmful content related to minors."

## Solution

The content policy filter automatically detects and "ages up" character descriptions to ensure compliance with Google's policies.

### How It Works

1. **Detection**: Scans prompt text for keywords indicating minors in both Vietnamese and English
2. **Replacement**: Automatically replaces child/minor references with young adult equivalents
3. **Age Adjustment**: Changes specific ages under 18 to age 20
4. **Warning**: Logs all modifications so users know what was changed

### Examples

| Original (Vietnamese) | Sanitized |
|----------------------|-----------|
| cô bé (little girl) | cô gái trẻ (young woman) |
| cậu bé (little boy) | chàng trai trẻ (young man) |
| 12 tuổi (12 years old) | 20 tuổi (20 years old) |
| trẻ em (children) | người trẻ tuổi (young people) |

| Original (English) | Sanitized |
|-------------------|-----------|
| little girl | young woman |
| child | young adult |
| 12 years old | 20 years old |
| teenager | young adult |

## Implementation

### Files Modified

1. **`services/google/content_policy_filter.py`** (NEW)
   - Core filter implementation
   - Keyword detection for Vietnamese and English
   - Age pattern detection and replacement
   - Prompt sanitization for dict and string formats

2. **`services/google/labs_flow_client.py`**
   - Integrated filter into `start_one()` method
   - Automatically sanitizes prompts before API submission
   - Emits warnings when content is modified

3. **`ui/text2video_panel_impl.py`**
   - Added `content_policy_warning` event handler
   - Displays warnings in console when prompts are sanitized

### Usage

The filter is **automatically applied** to all prompts sent to Google Labs API. No manual intervention is required.

When a prompt is sanitized, you'll see warnings in the console:

```
[CONTENT POLICY] ⚠️  Field 'character_details' aged up: 2 minor reference(s) replaced
[INFO] Prompt automatically sanitized to comply with Google's content policies
```

### Manual Usage (for testing)

```python
from services.google.content_policy_filter import sanitize_prompt_for_google_labs

# Sanitize a prompt dict
prompt = {
    "character_details": "Cô bé 12 tuổi với mái tóc đen",
    "key_action": "Cô bé quẹt diêm"
}

sanitized_prompt, warnings = sanitize_prompt_for_google_labs(prompt, enable_age_up=True)

print(sanitized_prompt)
# Output: {
#     "character_details": "cô gái trẻ 20 tuổi với mái tóc đen",
#     "key_action": "cô gái trẻ quẹt diêm"
# }

print(warnings)
# Output: ["Field 'character_details' aged up: 2 minor reference(s) replaced", ...]
```

## Configuration

The filter is enabled by default with these settings:

- **`enable_age_up`**: `True` - Automatically age up characters
- **`min_age`**: `18` - Minimum age for characters
- **`strict_mode`**: `False` - Sanitize instead of raising exceptions

To disable the filter (not recommended), you would need to modify the code in `labs_flow_client.py`:

```python
# Change this line:
sanitized_prompt_data, policy_warnings = sanitize_prompt_for_google_labs(
    original_prompt_data, 
    enable_age_up=True  # Change to False to disable
)
```

## Testing

Run the test suite to verify the filter works correctly:

```bash
python test_content_policy_fix.py
```

This test uses the actual prompt from the problem statement that triggered the HTTP 400 error and verifies it's properly sanitized.

## Limitations

1. **Context-Dependent**: The filter uses keyword matching and may not catch all implicit references to minors
2. **Story Impact**: Aging up characters changes the story (e.g., "The Little Match Girl" becomes "The Young Match Woman")
3. **Language Support**: Currently supports Vietnamese and English keywords only

## Best Practices

1. **Write Adult Characters**: When creating prompts, describe characters as adults (18+) from the start
2. **Avoid Age References**: Don't specify ages unless necessary, and keep them 20+
3. **Review Warnings**: Check the console warnings to see what was changed
4. **Save Sanitized Prompts**: The sanitized prompts are saved in the `02_Prompts` folder

## Troubleshooting

### Still Getting HTTP 400 Errors?

If you still get HTTP 400 errors after the fix:

1. Check console for `[CONTENT POLICY]` warnings - the filter may have detected content
2. Review the sanitized prompt JSON in `02_Prompts/scene_XX.json`
3. Manually review your prompt for other policy violations (violence, adult content, etc.)
4. Try simplifying the prompt or removing complex scenarios

### Filter Not Working?

1. Verify the filter is imported correctly:
   ```bash
   python -c "from services.google.content_policy_filter import ContentPolicyFilter; print('OK')"
   ```

2. Check for import errors in console logs

3. Ensure you're using the latest version of the code

## Future Improvements

Potential enhancements for the filter:

- [ ] Add configuration UI to enable/disable filter
- [ ] Support additional languages (Japanese, Korean, Chinese, etc.)
- [ ] Machine learning-based detection for implicit references
- [ ] Policy compliance scoring before API submission
- [ ] Custom age-up mappings per user preference

## References

- Google Labs Content Policies: https://labs.google/policies
- Issue Report: [Link to original issue]
- Test Case: `test_content_policy_fix.py`

---

**Last Updated**: 2025-11-08
**Version**: 1.0
