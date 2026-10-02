#!/usr/bin/env python3
"""
Music Organizer - Wrapper module for CLI and GUI entry points.

This module provides backward compatibility by wrapping the reorganized
package structure. It imports from the music_organizer package and exposes
the same top-level functions and classes.

For new code, prefer importing from the music_organizer package directly.
"""

import sys
from pathlib import Path

# For backward compatibility, expose package globals and functions
from music_organizer import config
from music_organizer.cli import main
from music_organizer.gui import MusicRenamerGUI, run_gui
from music_organizer.analysis.audio_quality import AudioQualityAnalyzer, analyze_file
from music_organizer.logging.logger import setup_logging, get_logger
from music_organizer.core.formatter import format_metadata_block, validate_report, write_report
from music_organizer.core.metadata import (
    clean_metadata, clean_noise_words, fill_missing_metadata, get_easy_tag,
    metadata_changed, normalize_spaces, read_metadata, write_metadata,
    apply_external_metadata, load_metadata_overrides
)
from music_organizer.core.workflow import (
    build_filename, build_unique_candidate, ensure_music_dirs,
    find_music_files, has_missing_core, process_file,
    process_files_batch, safe_move
)

# Re-expose as module-level for backward compatibility
CONFIG = config.CONFIG
SUPPORTED_EXTENSIONS = config.SUPPORTED_EXTENSIONS
NOISE_WORDS = config.NOISE_WORDS
METADATA_KEYS = config.METADATA_KEYS
YEAR_IN_ALBUM = config.YEAR_IN_ALBUM
DEFAULT_ROOT = config.DEFAULT_ROOT
LOGGER = config.LOGGER
AUDIO_ANALYZER = config.AUDIO_ANALYZER


if __name__ == "__main__":
    if len(sys.argv) > 1:
        raise SystemExit(main())
    config.load_config()
    run_gui()
