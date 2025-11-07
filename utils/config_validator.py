# -*- coding: utf-8 -*-
"""
Configuration Validator
Validates configuration files and settings on startup
Provides helpful error messages for common issues
"""

import os
import json
from typing import Dict, List, Tuple
from pathlib import Path


class ConfigValidationError(Exception):
    """Raised when configuration validation fails"""
    pass


class ConfigValidator:
    """Validates application configuration"""

    def __init__(self, config_path: str = None):
        """
        Initialize validator
        
        Args:
            config_path: Path to config.json (defaults to ./config.json)
        """
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'config.json'
            )
        self.config_path = config_path
        self.errors = []
        self.warnings = []

    def validate_all(self) -> Tuple[bool, List[str], List[str]]:
        """
        Run all validation checks
        
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []

        # Check if config file exists
        if not os.path.exists(self.config_path):
            self.errors.append(
                f"Configuration file not found: {self.config_path}\n"
                "Please create config.json from config.json.template"
            )
            return False, self.errors, self.warnings

        # Load and parse config
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            self.errors.append(
                f"Invalid JSON in config.json: {e}\n"
                f"Please fix the JSON syntax error at line {e.lineno}"
            )
            return False, self.errors, self.warnings
        except Exception as e:
            self.errors.append(f"Could not read config.json: {e}")
            return False, self.errors, self.warnings

        # Validate structure
        self._validate_structure(config)

        # Validate API keys
        self._validate_api_keys(config)

        # Validate paths
        self._validate_paths(config)

        # Check for deprecated settings
        self._check_deprecated(config)

        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings

    def _validate_structure(self, config: Dict):
        """Validate configuration structure"""
        required_keys = ['tokens', 'google_keys', 'elevenlabs_keys']

        for key in required_keys:
            if key not in config:
                self.warnings.append(
                    f"Missing key '{key}' in config.json. "
                    f"This may cause issues with {key.replace('_', ' ')}."
                )

    def _validate_api_keys(self, config: Dict):
        """Validate API keys"""
        # Check Google API keys
        google_keys = config.get('google_keys', [])
        if not google_keys or len(google_keys) == 0:
            self.warnings.append(
                "No Google API keys configured. "
                "Text generation features will not work.\n"
                "Add API keys in Settings → Google API Keys"
            )
        else:
            # Validate key format (basic check)
            for i, key in enumerate(google_keys):
                if not isinstance(key, str) or len(key) < 20:
                    self.warnings.append(
                        f"Google API key #{i+1} appears invalid (too short). "
                        f"Valid keys should be 39+ characters."
                    )

        # Check Labs tokens
        tokens = config.get('tokens', [])
        if not tokens or len(tokens) == 0:
            self.warnings.append(
                "No Labs tokens configured. "
                "Video generation features will not work.\n"
                "Add tokens in Settings → Google Labs Accounts"
            )

        # Check ElevenLabs keys
        elevenlabs_keys = config.get('elevenlabs_keys', [])
        if not elevenlabs_keys or len(elevenlabs_keys) == 0:
            self.warnings.append(
                "No ElevenLabs API keys configured. "
                "Voice generation will fall back to Google TTS.\n"
                "Add API keys in Settings → ElevenLabs Keys (optional)"
            )

    def _validate_paths(self, config: Dict):
        """Validate file paths"""
        download_root = config.get('download_root', '')

        if download_root:
            # Validate download root exists or can be created
            try:
                Path(download_root).mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError) as e:
                self.errors.append(
                    f"Cannot create download directory '{download_root}': {e}\n"
                    "Please check permissions or choose a different location."
                )
        else:
            self.warnings.append(
                "No download_root configured. "
                "Downloads will be saved to default location './downloads'."
            )

    def _check_deprecated(self, config: Dict):
        """Check for deprecated settings"""
        # Add checks for deprecated keys here as the app evolves
        deprecated_keys = {
            'old_api_key': 'Use google_keys instead',
            'project_root': 'Use download_root instead',
        }

        for old_key, suggestion in deprecated_keys.items():
            if old_key in config:
                self.warnings.append(
                    f"Deprecated setting '{old_key}' found in config. "
                    f"{suggestion}"
                )

    def get_summary(self) -> str:
        """Get validation summary as formatted string"""
        lines = []

        if self.errors:
            lines.append("❌ ERRORS:")
            for i, error in enumerate(self.errors, 1):
                lines.append(f"  {i}. {error}")
            lines.append("")

        if self.warnings:
            lines.append("⚠️  WARNINGS:")
            for i, warning in enumerate(self.warnings, 1):
                lines.append(f"  {i}. {warning}")
            lines.append("")

        if not self.errors and not self.warnings:
            lines.append("✅ Configuration is valid!")

        return "\n".join(lines)


def validate_config(config_path: str = None, verbose: bool = True) -> bool:
    """
    Convenience function to validate configuration
    
    Args:
        config_path: Path to config.json
        verbose: Print validation results
    
    Returns:
        True if valid, False otherwise
    """
    validator = ConfigValidator(config_path)
    is_valid, errors, warnings = validator.validate_all()

    if verbose:
        print("\n" + "=" * 70)
        print("CONFIGURATION VALIDATION")
        print("=" * 70)
        print(validator.get_summary())
        print("=" * 70 + "\n")

    return is_valid


# Example usage
if __name__ == '__main__':
    # Test the validator
    is_valid = validate_config()

    if not is_valid:
        print("⚠️  Please fix configuration errors before running the application.")
        exit(1)
    else:
        print("✅ Configuration validated successfully!")
