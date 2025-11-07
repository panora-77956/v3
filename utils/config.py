
import json
import os
import logging
from typing import Tuple

# Try to import python-dotenv for .env file support (optional)
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ModuleNotFoundError:
    DOTENV_AVAILABLE = False

# Setup logger
logger = logging.getLogger(__name__)

def _atomic_write_json(path, data):
    import json, os, tempfile
    d = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(prefix=".tmp_cfg_", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


CFG_PATH = os.path.join(os.path.expanduser("~"), ".veo_image2video_cfg.json")


def get_default_config() -> dict:
    """Return default configuration with safe values"""
    return {
        "tokens": [],
        "google_keys": [],
        "elevenlabs_keys": [],
        "default_project_id": "",
        "download_root": os.path.join(os.path.expanduser("~"), "VeoProjects")
    }


def validate_config(cfg: dict) -> Tuple[bool, str]:
    """
    Validate config structure. Returns (is_valid, error_message)
    
    Args:
        cfg: Configuration dictionary to validate
        
    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is empty.
        
    Note:
        - None values are accepted for string fields to handle legacy configs
    """
    if not isinstance(cfg, dict):
        return False, "Config must be a dictionary"
    
    defaults = get_default_config()
    required_keys = set(defaults.keys())
    
    # Check for missing keys
    missing_keys = required_keys - set(cfg.keys())
    if missing_keys:
        logger.warning(f"Config missing keys: {missing_keys}, will use defaults")
    
    # Validate types for existing keys
    for key, default_value in defaults.items():
        if key in cfg:
            expected_type = type(default_value)
            actual_value = cfg[key]
            
            # Allow None for string fields (backward compatibility with legacy configs)
            if expected_type == str and actual_value is None:
                continue
                
            # Check type match
            if not isinstance(actual_value, expected_type):
                return False, f"Config key '{key}' has wrong type: expected {expected_type.__name__}, got {type(actual_value).__name__}"
    
    return True, ""


def load() -> dict:
    """
    Load config with defaults and validation.
    
    Returns:
        Configuration dictionary with validated structure and safe defaults.
    """
    defaults = get_default_config()
    cfg = defaults.copy()
    
    # Try to load existing config
    if os.path.exists(CFG_PATH):
        try:
            with open(CFG_PATH, "r", encoding="utf-8") as f:
                loaded_cfg = json.load(f)
                
            # Validate loaded config
            is_valid, error_msg = validate_config(loaded_cfg)
            if not is_valid:
                logger.error(f"Config validation failed: {error_msg}. Using defaults.")
            else:
                # Merge loaded config with defaults (loaded values take precedence)
                cfg.update(loaded_cfg)
                logger.info("Config loaded successfully")
                
        except json.JSONDecodeError as e:
            logger.error(f"Config JSON decode error: {e}. Using defaults.")
        except Exception as e:
            logger.error(f"Error loading config: {e}. Using defaults.")
    else:
        logger.info("Config file not found, using defaults")
    
    return cfg


def _parse_comma_separated_env(env_value: str) -> list:
    """
    Parse comma-separated environment variable into list of non-empty strings.
    
    Args:
        env_value: Comma-separated string from environment variable
        
    Returns:
        List of stripped, non-empty strings
    """
    return [k.strip() for k in env_value.split(",") if k.strip()]


def load_with_env() -> dict:
    """
    Load config merged with environment variables.
    Environment variables take precedence over JSON config.
    
    Supported environment variables:
    - GOOGLE_API_KEYS: Comma-separated list of Google API keys
    - ELEVENLABS_API_KEYS: Comma-separated list of ElevenLabs API keys
    - DEFAULT_PROJECT_ID: Default project ID
    - DOWNLOAD_ROOT: Download root directory
    
    Returns:
        Configuration dictionary with env vars merged in.
    """
    # Load .env file if available
    if DOTENV_AVAILABLE:
        load_dotenv()
        logger.info(".env file loaded (if present)")
    
    # Load base config from JSON
    cfg = load()
    
    # Override with environment variables if present
    google_keys_env = os.getenv("GOOGLE_API_KEYS")
    if google_keys_env:
        cfg["google_keys"] = _parse_comma_separated_env(google_keys_env)
        logger.info(f"Loaded {len(cfg['google_keys'])} Google API keys from environment")
    
    elevenlabs_keys_env = os.getenv("ELEVENLABS_API_KEYS")
    if elevenlabs_keys_env:
        cfg["elevenlabs_keys"] = _parse_comma_separated_env(elevenlabs_keys_env)
        logger.info(f"Loaded {len(cfg['elevenlabs_keys'])} ElevenLabs API keys from environment")
    
    default_project_id_env = os.getenv("DEFAULT_PROJECT_ID")
    if default_project_id_env:
        cfg["default_project_id"] = default_project_id_env
        logger.info("Loaded DEFAULT_PROJECT_ID from environment")
    
    download_root_env = os.getenv("DOWNLOAD_ROOT")
    if download_root_env:
        cfg["download_root"] = download_root_env
        logger.info("Loaded DOWNLOAD_ROOT from environment")
    
    return cfg


def save(cfg: dict) -> dict:
    """
    Save config with validation.
    
    Args:
        cfg: Configuration dictionary to save
        
    Returns:
        The saved configuration dictionary
    """
    # Validate before saving
    is_valid, error_msg = validate_config(cfg)
    if not is_valid:
        logger.error(f"Cannot save invalid config: {error_msg}")
        return cfg
    
    try:
        _atomic_write_json(CFG_PATH, cfg)
        logger.info("Config saved successfully")
    except Exception as e:
        logger.error(f"Error saving config: {e}")
    
    return cfg
