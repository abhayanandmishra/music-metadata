#!/usr/bin/env python3
"""
Logging System for Music Organizer

Provides structured logging with multiple levels and output destinations.
Supports console output, file logging, and log rotation.

Log levels: DEBUG, INFO, WARN, ERROR
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional


class MusicOrganizerLogger:
    """Configured logger for Music Organizer with file and console output."""
    
    LOG_FORMAT = "[%(asctime)s] [%(levelname)-5s] [%(name)s] %(message)s"
    LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern - only one logger instance."""
        if cls._instance is None:
            cls._instance = super(MusicOrganizerLogger, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize logger (once)."""
        if self._initialized:
            return
        
        self.logger = logging.getLogger("music_organizer")
        self.logger.setLevel(logging.DEBUG)
        
        # Console handler (stderr for errors, stdout for info)
        self._setup_console_handler()
        
        # File handler (optional, added via set_file_logging)
        self.file_handler = None
        self.log_file = None
        
        self._initialized = True
    
    def _setup_console_handler(self):
        """Setup separate console handlers for stdout and stderr."""

        class _BelowError(logging.Filter):
            def filter(self, record):
                return record.levelno < logging.ERROR

        class _ErrorOnly(logging.Filter):
            def filter(self, record):
                return record.levelno >= logging.ERROR

        formatter = logging.Formatter(self.LOG_FORMAT, self.LOG_DATE_FORMAT)

        info_handler = logging.StreamHandler(sys.stdout)
        info_handler.setLevel(logging.INFO)
        info_handler.addFilter(_BelowError())
        info_handler.setFormatter(formatter)

        error_handler = logging.StreamHandler(sys.stderr)
        error_handler.setLevel(logging.ERROR)
        error_handler.addFilter(_ErrorOnly())
        error_handler.setFormatter(formatter)

        self.logger.addHandler(info_handler)
        self.logger.addHandler(error_handler)
    
    def set_file_logging(self, log_file: Path, level: str = "DEBUG"):
        """
        Enable file logging to specified path.
        
        Args:
            log_file: Path to log file
            level: Log level (DEBUG, INFO, WARN, ERROR)
        """
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Remove previous file handler if exists
        if self.file_handler:
            self.logger.removeHandler(self.file_handler)
            self.file_handler.close()
        
        # Create new file handler
        self.file_handler = logging.FileHandler(log_file, encoding="utf-8")
        self.file_handler.setLevel(getattr(logging, level.upper(), logging.DEBUG))
        formatter = logging.Formatter(self.LOG_FORMAT, self.LOG_DATE_FORMAT)
        self.file_handler.setFormatter(formatter)
        self.logger.addHandler(self.file_handler)
        self.log_file = log_file
    
    def set_console_level(self, level: str):
        """Set console output level (DEBUG, INFO, WARN, ERROR)."""
        for handler in self.logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    def debug(self, message: str, *args, **kwargs):
        """Log DEBUG message."""
        self.logger.debug(message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """Log INFO message."""
        self.logger.info(message, *args, **kwargs)
    
    def warn(self, message: str, *args, **kwargs):
        """Log WARN message."""
        self.logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """Log ERROR message."""
        self.logger.error(message, *args, **kwargs)
    
    def close(self):
        """Close file handlers gracefully."""
        if self.file_handler:
            self.file_handler.close()
            self.logger.removeHandler(self.file_handler)


def get_logger() -> MusicOrganizerLogger:
    """Get the global logger instance."""
    return MusicOrganizerLogger()


def setup_logging(
    console_level: str = "INFO",
    log_file: Optional[Path] = None,
    file_level: str = "DEBUG"
) -> MusicOrganizerLogger:
    """
    Setup logging with specified configuration.
    
    Args:
        console_level: Console log level (DEBUG, INFO, WARN, ERROR)
        log_file: Optional path to log file
        file_level: File log level (DEBUG, INFO, WARN, ERROR)
    
    Returns:
        Configured logger instance
    """
    logger = get_logger()
    logger.set_console_level(console_level)
    
    if log_file:
        logger.set_file_logging(log_file, file_level)
    
    return logger
