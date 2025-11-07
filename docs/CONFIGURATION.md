# Configuration Guide

This document explains how to configure the Video Super Ultra V7 application using config files and environment variables.

## Configuration Methods

The application supports three configuration methods with the following priority order (highest to lowest):

1. **Environment Variables** (highest priority)
2. **`.env` file** (requires python-dotenv)
3. **`config.json`** (lowest priority, backward compatible)

## Config File Structure

The configuration is stored in `~/.veo_image2video_cfg.json` with the following structure:

```json
{
  "tokens": [],
  "google_keys": [],
  "elevenlabs_keys": [],
  "default_project_id": "",
  "download_root": "~/VeoProjects"
}
```

### Configuration Fields

- **`tokens`** (array): Legacy token storage (deprecated)
- **`google_keys`** (array): List of Google API keys for image generation
- **`elevenlabs_keys`** (array): List of ElevenLabs API keys for text-to-speech
- **`default_project_id`** (string): Default Google project ID
- **`download_root`** (string): Root directory for downloaded projects

## Environment Variables

### Supported Variables

- **`GOOGLE_API_KEYS`**: Comma-separated list of Google API keys
  - Example: `GOOGLE_API_KEYS="key1,key2,key3"`
  
- **`ELEVENLABS_API_KEYS`**: Comma-separated list of ElevenLabs API keys
  - Example: `ELEVENLABS_API_KEYS="key4,key5"`
  
- **`DEFAULT_PROJECT_ID`**: Default Google project ID
  - Example: `DEFAULT_PROJECT_ID="my-project-123"`
  
- **`DOWNLOAD_ROOT`**: Root directory for downloads
  - Example: `DOWNLOAD_ROOT="/home/user/MyVideos"`

### Usage Examples

#### Option 1: Direct Environment Variables

```bash
export GOOGLE_API_KEYS="AIza...abc,AIza...def"
export ELEVENLABS_API_KEYS="sk_...123,sk_...456"
export DEFAULT_PROJECT_ID="my-project"
export DOWNLOAD_ROOT="/custom/path"
python main_image2video.py
```

#### Option 2: Using .env File (Recommended)

1. Create a `.env` file in the project root:

```bash
# .env file
GOOGLE_API_KEYS=AIza...abc,AIza...def
ELEVENLABS_API_KEYS=sk_...123,sk_...456
DEFAULT_PROJECT_ID=my-project
DOWNLOAD_ROOT=/custom/path
```

2. Run the application (it will automatically load `.env`):

```bash
python main_image2video.py
```

#### Option 3: Traditional config.json (Backward Compatible)

Edit `~/.veo_image2video_cfg.json`:

```json
{
  "tokens": [],
  "google_keys": ["AIza...abc", "AIza...def"],
  "elevenlabs_keys": ["sk_...123", "sk_...456"],
  "default_project_id": "my-project",
  "download_root": "/custom/path"
}
```

## Security Best Practices

### DO's ✅

1. **Use environment variables or .env files for API keys** (not config.json)
2. **Add `.env` to `.gitignore`** (already configured)
3. **Never commit API keys to version control**
4. **Use separate API keys for development and production**
5. **Rotate API keys regularly**

### DON'Ts ❌

1. **Don't commit `.env` files to git**
2. **Don't share API keys in screenshots or logs**
3. **Don't store API keys in config.json if using version control**

## Configuration Validation

The application automatically validates configuration on load:

- **Missing keys**: Will be filled with safe defaults
- **Invalid types**: Will cause validation error and use defaults
- **Malformed JSON**: Will be caught and defaults will be used
- **Empty config**: Safe defaults will be applied

### Default Values

If no configuration is found, these defaults are used:

```python
{
    "tokens": [],
    "google_keys": [],
    "elevenlabs_keys": [],
    "default_project_id": "",
    "download_root": "~/VeoProjects"
}
```

## Troubleshooting

### Application won't start

- Check if `~/.veo_image2video_cfg.json` exists and is valid JSON
- Delete the config file to force regeneration with defaults
- Check environment variables for typos

### API keys not working

1. Verify environment variables are set:
   ```bash
   echo $GOOGLE_API_KEYS
   echo $ELEVENLABS_API_KEYS
   ```

2. Check `.env` file format (no spaces around `=`):
   ```bash
   # Correct
   GOOGLE_API_KEYS=key1,key2
   
   # Incorrect
   GOOGLE_API_KEYS = key1,key2
   ```

3. Ensure python-dotenv is installed:
   ```bash
   pip install python-dotenv
   ```

### Config validation errors

Check application logs for specific error messages. Common issues:

- **Type mismatch**: Ensure arrays are arrays, strings are strings
- **Missing required keys**: Will be auto-filled with defaults
- **Invalid JSON**: Check for trailing commas, quotes, brackets

## Migration Guide

### From config.json to .env

1. Copy API keys from `~/.veo_image2video_cfg.json`
2. Create `.env` file in project root
3. Add keys in environment variable format
4. Test the application
5. Optionally remove keys from config.json (keep empty arrays)

Example:

**Before** (config.json):
```json
{
  "google_keys": ["AIza...abc", "AIza...def"]
}
```

**After** (.env):
```
GOOGLE_API_KEYS=AIza...abc,AIza...def
```

## Additional Resources

- [Google Cloud API Keys](https://cloud.google.com/docs/authentication/api-keys)
- [ElevenLabs API Documentation](https://elevenlabs.io/docs)
- [python-dotenv Documentation](https://pypi.org/project/python-dotenv/)

## Support

For issues or questions about configuration:

1. Check this documentation
2. Review application logs
3. Verify environment variable format
4. Create an issue on GitHub with sanitized logs (remove API keys!)
