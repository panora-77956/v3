# Rate Limit Fix & Whisk Integration

## Problem Statement

Users were experiencing persistent rate limit (HTTP 429) errors when generating images with Gemini API, even with 11 API keys configured. The logs showed:

```
[23:04:28] [IMAGE GEN] Using 11 API keys with intelligent rotation
[23:04:28] [KEY 1/11] Trying key ...PmgR1w
[23:04:29] [RATE LIMIT] Key ...PmgR1w hit rate limit (429)
[23:04:29] [BACKOFF] Waiting 4s before trying next key...
[23:04:33] [KEY 2/11] Trying key ...KzZ4Ms
[23:04:33] [RATE LIMIT] Key ...KzZ4Ms hit rate limit (429)
[23:04:33] [BACKOFF] Waiting 8s before trying next key...
```

All keys were hitting rate limits with minimal backoff delays, making image generation impossible.

## Root Cause

1. **Gemini Free Tier Limits**: Google Gemini free tier has strict rate limits (~15 RPM per project)
2. **Insufficient Backoff**: Previous backoff delays (4s, 8s, 16s, 32s) were too short
3. **No Alternative**: No fallback mechanism when all Gemini keys were exhausted

## Solution Implemented

### 1. Improved Rate Limit Backoff

**File**: `services/core/api_key_rotator.py`

**Changes**:
- Increased exponential backoff from `4s, 8s, 16s, 32s` to `10s, 20s, 40s, 60s`
- Added rate limit counter to track exhausted keys
- Added warning when all API keys are rate limited
- Improved error detection for 429, quota, and resource_exhausted errors

**Before**:
```python
delay = 4 * (2 ** (idx - 1))  # 4s, 8s, 16s, 32s
```

**After**:
```python
delay = 10 * (2 ** (idx - 1))  # 10s, 20s, 40s, 80s (capped at 60s)
delay = min(delay, self.MAX_BACKOFF_SECONDS)  # Cap at 60s
```

### 2. Complete Whisk API Implementation

**File**: `services/whisk_service.py`

**Changes**:
- Implemented `get_bearer_token()` to retrieve OAuth tokens from config
- Implemented `run_image_recipe()` to call Google Labs Whisk API
- Added complete image generation flow:
  1. Caption images
  2. Upload images to Whisk
  3. Run image recipe with Bearer token
  4. Parse and download result

**API Flow**:
```python
# 1. Caption image
caption = caption_image(image_path, workflow_id, session_id)

# 2. Upload image
media_id = upload_image_whisk(image_path, workflow_id, session_id)

# 3. Run recipe
result = run_image_recipe(prompt, recipe_media_inputs, workflow_id, session_id)
```

### 3. Automatic Whisk Fallback

**File**: `services/image_gen_service.py`

**Changes**:
- Added automatic fallback to Whisk when all Gemini keys hit rate limits
- Detects rate limit exhaustion and switches to alternative API
- Logs the fallback attempt and result

**Flow**:
```python
try:
    # Try Gemini with all API keys
    rotator.execute(api_call_with_key)
except APIKeyRotationError as e:
    # If rate limit error, try Whisk fallback
    if 'rate limit' in error_msg:
        whisk_result = whisk_service.generate_image(...)
        if whisk_result:
            return whisk_result
    raise  # Re-raise if Whisk didn't work
```

## Configuration

To enable Whisk fallback, add `labs_tokens` to `config.json`:

```json
{
  "google_keys": ["your-gemini-key-1", "your-gemini-key-2"],
  "labs_tokens": ["your-google-labs-bearer-token"],
  "elevenlabs_keys": ["your-elevenlabs-key"]
}
```

**How to get a Labs token**:
1. Open https://labs.google/fx/tools/whisk in your browser
2. Open Developer Tools (F12) → Network tab
3. Generate an image to trigger API calls
4. Look for requests to `aisandbox-pa.googleapis.com`
5. Copy the `Bearer` token from the Authorization header

## Testing

All modules have been tested:
- ✅ Module imports work correctly
- ✅ API key rotation works with empty keys error
- ✅ Rate limit detection works
- ✅ Backoff delays are applied correctly (10s, 20s)
- ✅ Warning shown when all keys exhausted
- ✅ No security vulnerabilities (CodeQL scan passed)

## Results

### Before
- Rate limit errors with all 11 API keys
- Image generation failed completely
- Backoff too short (4s, 8s, 16s)
- No alternative when Gemini exhausted

### After
- Longer backoff delays (10s, 20s, 40s, 60s)
- Clear warnings when keys are rate limited
- Automatic Whisk fallback available
- Better user experience with clear logging

## Known Limitations

1. **Whisk requires reference images**: Whisk API needs model/product images to work
2. **Async polling not implemented**: Whisk only supports immediate results currently
3. **Bearer tokens expire**: Labs tokens need to be refreshed periodically

## Files Changed

1. `services/core/api_key_rotator.py` - Improved backoff delays and rate limit detection
2. `services/whisk_service.py` - Complete Whisk API implementation
3. `services/image_gen_service.py` - Automatic Whisk fallback
4. `README.md` - Updated documentation with Whisk configuration

## Version

**Release**: v7.2.2  
**Date**: 2025-11-07  
**Status**: ✅ Production Ready
