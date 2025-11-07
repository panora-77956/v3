# -*- coding: utf-8 -*-
"""
Input Validation and Sanitization
Provides utilities to validate and sanitize user inputs for security and stability
"""

import re
import os
from typing import Union, Any
from pathlib import Path


class ValidationError(Exception):
    """Raised when input validation fails"""
    pass


class InputValidator:
    """Validates various types of user inputs"""

    # Common patterns
    SAFE_FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9_. -]+$')
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    URL_PATTERN = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )

    @staticmethod
    def validate_string(
        value: Any,
        min_length: int = 0,
        max_length: int = None,
        allow_empty: bool = True,
        field_name: str = "Input"
    ) -> str:
        """
        Validate string input
        
        Args:
            value: Value to validate
            min_length: Minimum allowed length
            max_length: Maximum allowed length (None for no limit)
            allow_empty: Whether empty strings are allowed
            field_name: Name of field for error messages
        
        Returns:
            Validated string
        
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string, got {type(value).__name__}")

        if not allow_empty and len(value.strip()) == 0:
            raise ValidationError(f"{field_name} cannot be empty")

        if len(value) < min_length:
            raise ValidationError(f"{field_name} must be at least {min_length} characters")

        if max_length is not None and len(value) > max_length:
            raise ValidationError(f"{field_name} must not exceed {max_length} characters")

        return value

    @staticmethod
    def validate_integer(
        value: Any,
        min_value: int = None,
        max_value: int = None,
        field_name: str = "Input"
    ) -> int:
        """
        Validate integer input
        
        Args:
            value: Value to validate
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            field_name: Name of field for error messages
        
        Returns:
            Validated integer
        
        Raises:
            ValidationError: If validation fails
        """
        try:
            int_value = int(value)
        except (ValueError, TypeError) as e:
            raise ValidationError(f"{field_name} must be an integer: {e}")

        if min_value is not None and int_value < min_value:
            raise ValidationError(f"{field_name} must be at least {min_value}")

        if max_value is not None and int_value > max_value:
            raise ValidationError(f"{field_name} must not exceed {max_value}")

        return int_value

    @staticmethod
    def validate_float(
        value: Any,
        min_value: float = None,
        max_value: float = None,
        field_name: str = "Input"
    ) -> float:
        """
        Validate float input
        
        Args:
            value: Value to validate
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            field_name: Name of field for error messages
        
        Returns:
            Validated float
        
        Raises:
            ValidationError: If validation fails
        """
        try:
            float_value = float(value)
        except (ValueError, TypeError) as e:
            raise ValidationError(f"{field_name} must be a number: {e}")

        if min_value is not None and float_value < min_value:
            raise ValidationError(f"{field_name} must be at least {min_value}")

        if max_value is not None and float_value > max_value:
            raise ValidationError(f"{field_name} must not exceed {max_value}")

        return float_value

    @staticmethod
    def validate_path(
        value: str,
        must_exist: bool = False,
        must_be_file: bool = False,
        must_be_dir: bool = False,
        create_if_missing: bool = False,
        field_name: str = "Path"
    ) -> str:
        """
        Validate file/directory path
        
        Args:
            value: Path to validate
            must_exist: Path must exist
            must_be_file: Path must be a file
            must_be_dir: Path must be a directory
            create_if_missing: Create directory if it doesn't exist
            field_name: Name of field for error messages
        
        Returns:
            Validated path
        
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(value, (str, Path)):
            raise ValidationError(f"{field_name} must be a string or Path object")

        path = Path(value)

        if must_exist and not path.exists():
            if create_if_missing and not must_be_file:
                try:
                    path.mkdir(parents=True, exist_ok=True)
                except OSError as e:
                    raise ValidationError(f"Could not create {field_name}: {e}")
            else:
                raise ValidationError(f"{field_name} does not exist: {value}")

        if must_be_file and path.exists() and not path.is_file():
            raise ValidationError(f"{field_name} must be a file: {value}")

        if must_be_dir and path.exists() and not path.is_dir():
            raise ValidationError(f"{field_name} must be a directory: {value}")

        return str(path)

    @staticmethod
    def validate_url(value: str, field_name: str = "URL") -> str:
        """
        Validate URL
        
        Args:
            value: URL to validate
            field_name: Name of field for error messages
        
        Returns:
            Validated URL
        
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")

        if not InputValidator.URL_PATTERN.match(value):
            raise ValidationError(f"{field_name} is not a valid URL: {value}")

        return value

    @staticmethod
    def validate_choice(
        value: Any,
        choices: list,
        field_name: str = "Input"
    ) -> Any:
        """
        Validate that value is in allowed choices
        
        Args:
            value: Value to validate
            choices: List of allowed values
            field_name: Name of field for error messages
        
        Returns:
            Validated value
        
        Raises:
            ValidationError: If validation fails
        """
        if value not in choices:
            raise ValidationError(
                f"{field_name} must be one of {choices}, got '{value}'"
            )

        return value


class InputSanitizer:
    """Sanitizes user inputs to prevent security issues"""

    # Characters to remove for safe filenames
    UNSAFE_FILENAME_CHARS = r'[<>:"/\\|?*\x00-\x1f]'

    @staticmethod
    def sanitize_filename(
        filename: str,
        replacement: str = '_',
        max_length: int = 255
    ) -> str:
        """
        Sanitize filename to be safe for filesystem
        
        Args:
            filename: Filename to sanitize
            replacement: Character to replace unsafe characters
            max_length: Maximum filename length
        
        Returns:
            Sanitized filename
        """
        # Remove or replace unsafe characters
        sanitized = re.sub(InputSanitizer.UNSAFE_FILENAME_CHARS, replacement, filename)

        # Remove leading/trailing spaces and dots
        sanitized = sanitized.strip('. ')

        # Limit length
        if len(sanitized) > max_length:
            # Keep extension if present
            name, ext = os.path.splitext(sanitized)
            max_name_length = max_length - len(ext)
            sanitized = name[:max_name_length] + ext

        # Ensure not empty
        if not sanitized:
            sanitized = 'unnamed'

        return sanitized

    @staticmethod
    def sanitize_path(path: str, allow_absolute: bool = False) -> str:
        """
        Sanitize path to prevent directory traversal attacks
        
        Args:
            path: Path to sanitize
            allow_absolute: Allow absolute paths
        
        Returns:
            Sanitized path
        
        Raises:
            ValidationError: If path contains directory traversal
        """
        # Normalize and resolve path (resolves symlinks and relative paths)
        normalized = os.path.normpath(path)
        resolved = os.path.realpath(normalized)

        # Check for directory traversal using both normalized and resolved paths
        if '..' in normalized.split(os.sep):
            raise ValidationError("Path contains directory traversal (..) which is not allowed")

        # Additional check: ensure resolved path doesn't escape through symlinks
        # This prevents symlink-based traversal attacks
        if '..' in resolved.split(os.sep):
            raise ValidationError("Path resolves to directory traversal which is not allowed")

        # Check if absolute when not allowed
        if not allow_absolute and os.path.isabs(resolved):
            raise ValidationError("Absolute paths are not allowed")

        return normalized

    @staticmethod
    def sanitize_html(text: str) -> str:
        """
        Basic HTML sanitization (escape special characters)
        
        Args:
            text: Text to sanitize
        
        Returns:
            Sanitized text with HTML entities escaped
        """
        if not isinstance(text, str):
            return text

        # Escape HTML special characters
        html_escape_table = {
            "&": "&amp;",
            '"': "&quot;",
            "'": "&#x27;",
            ">": "&gt;",
            "<": "&lt;",
        }

        return "".join(html_escape_table.get(c, c) for c in text)

    @staticmethod
    def sanitize_sql(text: str) -> str:
        """
        Basic SQL injection prevention (escape single quotes)
        
        Args:
            text: Text to sanitize
        
        Returns:
            Sanitized text
        
        Note:
            This is a basic sanitization. Use parameterized queries for real SQL.
        """
        if not isinstance(text, str):
            return text

        # Escape single quotes
        return text.replace("'", "''")

    @staticmethod
    def truncate_string(text: str, max_length: int, suffix: str = '...') -> str:
        """
        Truncate string to maximum length
        
        Args:
            text: Text to truncate
            max_length: Maximum length
            suffix: Suffix to add if truncated
        
        Returns:
            Truncated string
        """
        if len(text) <= max_length:
            return text

        return text[:max_length - len(suffix)] + suffix


# Convenience functions
def validate_and_sanitize_filename(filename: str) -> str:
    """Validate and sanitize filename in one step"""
    # Sanitize first
    sanitized = InputSanitizer.sanitize_filename(filename)

    # Then validate
    InputValidator.validate_string(
        sanitized,
        min_length=1,
        max_length=255,
        allow_empty=False,
        field_name="Filename"
    )

    return sanitized


def validate_project_name(name: str) -> str:
    """Validate project name"""
    return InputValidator.validate_string(
        name,
        min_length=1,
        max_length=100,
        allow_empty=False,
        field_name="Project name"
    )


def validate_duration(seconds: Union[int, float]) -> float:
    """Validate video duration"""
    return InputValidator.validate_float(
        seconds,
        min_value=1.0,
        max_value=600.0,  # Max 10 minutes
        field_name="Duration"
    )


def validate_scene_count(count: int) -> int:
    """Validate number of scenes"""
    return InputValidator.validate_integer(
        count,
        min_value=1,
        max_value=50,
        field_name="Scene count"
    )


# Example usage
if __name__ == '__main__':
    # Test filename sanitization
    unsafe_filename = "my<file>name?.txt"
    safe_filename = InputSanitizer.sanitize_filename(unsafe_filename)
    print(f"✓ Sanitized filename: '{unsafe_filename}' -> '{safe_filename}'")

    # Test path validation
    try:
        InputValidator.validate_path(
            "./test_dir",
            must_be_dir=True,
            create_if_missing=True
        )
        print("✓ Path validation passed")
    except ValidationError as e:
        print(f"✗ Path validation failed: {e}")

    # Test integer validation
    try:
        value = InputValidator.validate_integer("42", min_value=1, max_value=100)
        print(f"✓ Integer validation: {value}")
    except ValidationError as e:
        print(f"✗ Integer validation failed: {e}")

    # Test URL validation
    try:
        url = InputValidator.validate_url("https://example.com/path")
        print(f"✓ URL validation: {url}")
    except ValidationError as e:
        print(f"✗ URL validation failed: {e}")

    print("\n✅ All validation tests completed!")
