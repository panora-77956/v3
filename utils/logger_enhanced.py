# -*- coding: utf-8 -*-
"""
Enhanced Logging System for Video Super Ultra
Provides structured logging with rotation, formatting, and multiple handlers
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from datetime import datetime
from pathlib import Path


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }

    def format(self, record):
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"

        # Format the message
        result = super().format(record)

        # Reset levelname for next use
        record.levelname = levelname

        return result


def setup_logger(
    name: str = 'videoultra',
    level: int = logging.INFO,
    log_dir: str = None,
    console_output: bool = True,
    file_output: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Setup enhanced logger with file rotation and console output
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files (defaults to ./logs)
        console_output: Enable console output
        file_output: Enable file output
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create formatters
    console_format = ColoredFormatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )

    file_format = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)

    # File handler with rotation
    if file_output:
        if log_dir is None:
            log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')

        # Create log directory if it doesn't exist
        Path(log_dir).mkdir(parents=True, exist_ok=True)

        # Create log file with date
        log_file = os.path.join(
            log_dir,
            f'videoultra_{datetime.now().strftime("%Y%m%d")}.log'
        )

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger instance
    
    Args:
        name: Module name (uses __name__ if not provided)
    
    Returns:
        Logger instance
    """
    if name is None:
        # Get caller's module name
        import inspect
        frame = None
        caller_frame = None
        try:
            frame = inspect.currentframe()
            caller_frame = frame.f_back
            name = caller_frame.f_globals.get('__name__', 'videoultra')
        finally:
            # Clean up frame references to prevent memory leaks
            del frame
            del caller_frame

    logger = logging.getLogger(name)

    # If logger doesn't have handlers, set it up
    if not logger.handlers:
        return setup_logger(name)

    return logger


class LoggerAdapter:
    """
    Adapter for existing code using print() statements
    Provides backward compatibility while adding logging
    """

    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or get_logger()

    def __call__(self, message: str, level: str = 'INFO'):
        """Allow LoggerAdapter to be called like print()"""
        level = level.upper()
        if level == 'DEBUG':
            self.logger.debug(message)
        elif level == 'INFO':
            self.logger.info(message)
        elif level == 'WARNING' or level == 'WARN':
            self.logger.warning(message)
        elif level == 'ERROR':
            self.logger.error(message)
        elif level == 'CRITICAL':
            self.logger.critical(message)
        else:
            self.logger.info(message)

    def debug(self, message: str):
        self.logger.debug(message)

    def info(self, message: str):
        self.logger.info(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def error(self, message: str):
        self.logger.error(message)

    def critical(self, message: str):
        self.logger.critical(message)

    def exception(self, message: str):
        """Log exception with traceback"""
        self.logger.exception(message)


# Initialize default logger
_default_logger = None

def init_logging(level: int = logging.INFO, **kwargs):
    """
    Initialize the default logging system
    
    Args:
        level: Logging level
        **kwargs: Additional arguments for setup_logger
    """
    global _default_logger
    _default_logger = setup_logger('videoultra', level=level, **kwargs)
    return _default_logger


def get_default_logger() -> logging.Logger:
    """Get the default logger, initializing if necessary"""
    global _default_logger
    if _default_logger is None:
        _default_logger = setup_logger('videoultra')
    return _default_logger


# Example usage:
if __name__ == '__main__':
    # Setup logging
    logger = setup_logger('test', level=logging.DEBUG)

    # Test different log levels
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")

    # Test exception logging
    try:
        raise ValueError("Test exception")
    except Exception as e:
        logger.exception("An error occurred")

    print("\n✓ Logger test complete. Check logs/ directory for output.")
