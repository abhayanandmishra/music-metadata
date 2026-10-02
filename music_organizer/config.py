#!/usr/bin/env python3
"""Configuration management for Music Organizer."""

import json
import re
from pathlib import Path
from typing import Optional

from .logging.logger import get_logger

# Global configuration loaded at startup
CONFIG = {}
SUPPORTED_EXTENSIONS = set()
NOISE_WORDS = set()
METADATA_KEYS = ()
YEAR_IN_ALBUM = None
DEFAULT_ROOT = Path("music")
LOGGER = None
AUDIO_ANALYZER = None


def load_config():
    """Load configuration from config.json. Falls back to defaults if file missing."""
    global CONFIG, SUPPORTED_EXTENSIONS, NOISE_WORDS, METADATA_KEYS, YEAR_IN_ALBUM, DEFAULT_ROOT, LOGGER, AUDIO_ANALYZER
    
    from .logging.logger import setup_logging
    from .analysis.audio_quality import AudioQualityAnalyzer
    
    # Initialize logger
    LOGGER = setup_logging(console_level="INFO")
    LOGGER.info("Music Organizer starting up...")
    
    # Initialize audio analyzer
    AUDIO_ANALYZER = AudioQualityAnalyzer()
    if not AUDIO_ANALYZER.ffmpeg_available:
        LOGGER.warn("ffmpeg not available - audio quality analysis disabled")
    
    # Find config.json - check multiple locations
    config_path = None
    possible_paths = [
        Path(__file__).parent / "config.json",  # In package (preferred)
        Path(__file__).parent.parent / "config.json",  # Root directory (fallback)
    ]
    
    for path in possible_paths:
        if path.exists():
            config_path = path
            break
    
    if config_path and config_path.exists():
        try:
            with config_path.open("r", encoding="utf-8") as f:
                CONFIG = json.load(f)
            
            # Load audio settings
            audio_config = CONFIG.get("audio", {})
            SUPPORTED_EXTENSIONS = set(audio_config.get("supported_extensions", [
                ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wav", ".wma"
            ]))
            NOISE_WORDS = set(audio_config.get("noise_words", [
                "(Ghantalele.com)", "Ghantalele", "pagalnew", "raagtune", "320 kbps", "290 kbps", "128 kbps",
                "official", "lyrics", "Ghantalele.com", "Downloaded from"
            ]))
            
            # Load metadata settings
            metadata_config = CONFIG.get("metadata", {})
            METADATA_KEYS = tuple(metadata_config.get("keys", [
                "artist", "title", "album", "track", "genre", "year", "original", "comments", "albumartist", "publisher", "composer"
            ]))
            regex_pattern = metadata_config.get("year_pattern_regex", r"(?:\(|\[)?\b(?:19|20)\d{2}\b(?:\)|\])?")
            YEAR_IN_ALBUM = re.compile(regex_pattern)
            
            # Load directory settings
            dir_config = CONFIG.get("directories", {})
            music_root = dir_config.get("music_root", "music")
            DEFAULT_ROOT = Path(music_root)
            
            return True
        except (json.JSONDecodeError, IOError) as e:
            LOGGER.warn(f"Failed to load config.json ({e}). Using defaults.")
            _set_defaults()
            return False
    else:
        # Config file not found, use hardcoded defaults
        LOGGER.info("Config file not found, using hardcoded defaults")
        _set_defaults()
        return False


def _set_defaults():
    """Set hardcoded defaults when config.json is unavailable."""
    global CONFIG, SUPPORTED_EXTENSIONS, NOISE_WORDS, METADATA_KEYS, YEAR_IN_ALBUM, DEFAULT_ROOT
    
    SUPPORTED_EXTENSIONS = {
        ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wav", ".wma"
    }
    NOISE_WORDS = {
        "(Ghantalele.com)", "Ghantalele", "pagalnew", "raagtune", "320 kbps", "290 kbps", "128 kbps",
        "official", "lyrics", "Ghantalele.com", "Downloaded from"
    }
    METADATA_KEYS = ("artist", "title", "album", "track", "genre", "year", "original", "comments", "albumartist", "publisher", "composer")
    YEAR_IN_ALBUM = re.compile(r"(?:\(|\[)?\b(?:19|20)\d{2}\b(?:\)|\])?")
    DEFAULT_ROOT = Path("music")
