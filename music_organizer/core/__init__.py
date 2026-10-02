#!/usr/bin/env python3
"""Core module - metadata and file processing."""

from .metadata import (
    clean_metadata,
    clean_noise_words,
    fill_missing_metadata,
    get_easy_tag,
    metadata_changed,
    normalize_spaces,
    read_metadata,
    write_metadata,
)
from .formatter import (
    format_metadata_block,
    validate_report,
    write_report,
)
from .workflow import (
    build_filename,
    build_unique_candidate,
    ensure_music_dirs,
    find_music_files,
    has_missing_core,
    process_file,
    process_files_batch,
    safe_move,
)

__all__ = [
    "clean_metadata",
    "clean_noise_words",
    "fill_missing_metadata",
    "get_easy_tag",
    "metadata_changed",
    "normalize_spaces",
    "read_metadata",
    "write_metadata",
    "format_metadata_block",
    "validate_report",
    "write_report",
    "build_filename",
    "build_unique_candidate",
    "ensure_music_dirs",
    "find_music_files",
    "has_missing_core",
    "process_file",
    "process_files_batch",
    "safe_move",
]
