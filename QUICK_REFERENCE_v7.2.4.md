# Quick Reference: New Features (v7.2.4)

## Issue #1: Prompt Auto-Save ✅

### What Changed?
Prompts are now automatically saved to your computer when generating videos.

### Where Are Prompts Saved?
```
Your Project Download Folder/
  ├── prompts/           ⬅️ NEW FOLDER
  │   ├── scene_1_20251109_003924.json  (metadata)
  │   ├── scene_1_20251109_003924.txt   (exact prompt text)
  │   ├── scene_2_20251109_003925.json  (metadata)
  │   ├── scene_2_20251109_003925.txt   (exact prompt text)
  │   └── ...
  └── videos/
      └── ...
```

### What's In Each File?

**JSON file** (`.json`) - Contains metadata:
- **timestamp**: When the video was generated
- **scene_num**: Scene number (if applicable)
- **model_key**: Which AI model was used
- **aspect_ratio**: Video aspect ratio (9:16, 16:9, etc.)
- **original_prompt_data**: Your original prompt input
- **complete_prompt_text**: The full prompt sent to Google Labs Flow API

**TXT file** (`.txt`) - Contains exact prompt:
- The **exact text prompt** sent to Google Labs Flow API
- Easy to read and copy
- Same content as `complete_prompt_text` in JSON, but in plain text format

### How To Use Saved Prompts?
1. **Reference**: Check what prompts were used for each video
2. **Debug**: If a video didn't turn out as expected, review the actual prompt sent
3. **Reuse**: Copy prompts from `.txt` files to generate similar videos later
4. **Learn**: Understand how your inputs are transformed into full prompts
5. **Compare**: Open `.txt` files side-by-side to see prompt differences between scenes

---

## Issue #2: Multi-Account "Not Found" Fix ✅

### What Changed?
When using 2+ Google accounts in parallel mode, videos from account 2 onwards are now properly tracked.

### What Was The Problem?
- Account 1: Videos found ✅
- Account 2+: Videos showed "not found" ❌ (but were actually being created)

### What's Fixed?
- Account 1: Videos found ✅
- Account 2+: Videos found ✅ (now includes project context in API calls)

### What You'll See?
Better logging when checking video status:
```
[INFO] Checking 3 operations for Account 2 (project: 87b19267...)
[INFO] Got 3 results from Account 2
```

If operations are missing, you'll see:
```
[WARN] Missing 1 operation: projects/.../operations/xyz123
```

### Configuration Required?
**NO** - This works automatically with your existing multi-account setup.

---

## Issue #3: Style Consistency ✅

### What Changed?
**Nothing** - existing implementation already works correctly!

### How It Works?
When generating multiple scenes in one session:
1. A `style_seed` is generated **once** at the start
2. All scenes in that session use the **same** `style_seed`
3. This ensures visual style consistency across all scenes

### What You'll See In Prompts?
```
🎲 STYLE SEED FOR CONSISTENCY:
Use style seed: 67890
This seed ensures visual style consistency across all scenes.
DO NOT vary the visual style - the seed locks it in place.
```

### Tips For Best Results?
1. Generate all related scenes in **one session** (don't split into multiple sessions)
2. Use the same **style settings** (anime, realistic, etc.) for all scenes
3. Keep **character descriptions** identical across scenes

---

## FAQ

### Q: Will prompts slow down video generation?
**A:** No, prompt saving is very fast (< 10ms) and happens in the background.

### Q: Can I disable prompt auto-save?
**A:** Currently no, but it fails silently if there's an issue - won't break your videos.

### Q: What if prompts folder takes up too much space?
**A:** Each prompt file is ~5-10KB. You can safely delete old prompts anytime.

### Q: Do I need to update my config?
**A:** No, all features work automatically with your existing configuration.

### Q: Will this fix work with my existing accounts?
**A:** Yes! Just ensure each account in your config has a `project_id` set.

### Q: How do I know if multi-account fix is working?
**A:** Check the logs - you should see messages like "Checking N operations for Account 2 (project: ...)".

---

## Troubleshooting

### Prompts Not Saving?
1. Check if download folder is configured in Settings
2. Check folder permissions (must be writable)
3. Look for "[WARN] Failed to save prompt" in logs

### Account 2+ Still Showing "Not Found"?
1. Verify each account has a unique `project_id` in config
2. Check logs for "batch_check_fallback" messages
3. Ensure OAuth tokens are valid for each account

### Style Still Inconsistent?
1. Generate all scenes in **one session** (don't restart between scenes)
2. Use same style settings for all scenes
3. Check prompt files - verify `style_seed` is same across scenes

---

## Need Help?

See full documentation: `FIX_MULTI_ACCOUNT_PROMPT_SAVE.md`

**Version:** 7.2.4  
**Date:** 2025-11-09
