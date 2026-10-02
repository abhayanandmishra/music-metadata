#!/usr/bin/env python3
"""Metadata handling module for Music Organizer."""

import json
import re
import shutil
from pathlib import Path
from typing import Dict, Optional

from mutagen import File

from .. import config


def safe_value(value):
    """Extract string value from various types."""
    if value is None:
        return ""
    if isinstance(value, list):
        return str(value[0]).strip() if value else ""
    return str(value).strip()


def first_non_empty(*values):
    """Return first non-empty value from arguments."""
    for value in values:
        text = safe_value(value)
        if text:
            return text
    return ""


def get_easy_tag(tags, *candidates):
    """Return first non-empty value from a list of easy-tag candidate keys."""
    if tags is None:
        return ""
    for key in candidates:
        try:
            value = tags.get(key)
        except Exception:
            value = None
        text = safe_value(value)
        if text:
            return text
    return ""


def set_easy_tag(tags, value, *candidates):
    """Set/delete metadata across multiple candidate tag keys safely."""
    if tags is None:
        return False

    text = normalize_spaces(value)
    touched = False
    for key in candidates:
        try:
            if text:
                tags[key] = [text]
                touched = True
            elif key in tags:
                del tags[key]
                touched = True
        except Exception:
            # Not all formats expose all keys; keep trying aliases.
            continue
    return touched


def normalize_spaces(value: str) -> str:
    """Normalize whitespace in string."""
    return re.sub(r"\s+", " ", str(value or "")).strip()


def sanitize_field(value, fallback="unknown"):
    """Sanitize field value for use in filenames."""
    value = normalize_spaces(value)
    if not value:
        value = fallback
    value = re.sub(r"[\\/:*?\"<>|]", "_", value)
    value = value.rstrip(". ")
    return value


def sanitize_final(value):
    """Final sanitization before using as filename."""
    value = normalize_spaces(value)
    value = re.sub(r"[\\/:*?\"<>|]", "_", value)
    value = value.rstrip(". ")
    return value


def clean_noise_words(value):
    """Remove noise words from metadata field."""
    text = normalize_spaces(value)
    if not text:
        return ""
    
    # Sort noise words by length (longest first) to match complete phrases before components
    sorted_noise = sorted(config.NOISE_WORDS, key=len, reverse=True)
    
    for noise in sorted_noise:
        escaped = re.escape(noise)
        # Skip single-char specials; handle them separately below
        if len(noise) == 1 and noise in "()[]":
            continue
        
        # Try word boundary match first (for simple words)
        text = re.sub(rf"\b{escaped}\b", "", text, flags=re.IGNORECASE)
        # Also try literal match for phrases with special characters
        text = re.sub(rf"(?:^|\s){escaped}(?:\s|$)", " ", text, flags=re.IGNORECASE)
    
    # Clean up orphaned brackets and parentheses
    text = re.sub(r"\s*[\(\)[\]]\s*", " ", text)  # Remove brackets with surrounding spaces
    text = re.sub(r"^[\(\)[\]]+\s*", "", text)     # Remove leading brackets
    text = re.sub(r"\s*[\(\)[\]]+$", "", text)     # Remove trailing brackets
    
    # Normalize separators and spacing
    text = re.sub(r"\s*-\s*-\s*", " - ", text)     # Collapse multiple dashes
    text = re.sub(r"\s+-\s+", " - ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip(" -_.")


def clean_separators(text):
    """Clean up extra separators in text."""
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"(?:\s*[-_]\s*){2,}", " - ", text)
    return text.strip(" -_.")


def clean_track(value: str) -> str:
    """Extract and clean track number."""
    value = normalize_spaces(value)
    if not value:
        return ""
    match = re.match(r"(\d{1,3})", value)
    return match.group(1) if match else value


def clean_album(value: str) -> str:
    """Clean album name by removing noise words and years."""
    value = clean_noise_words(value)
    value = config.YEAR_IN_ALBUM.sub("", value)
    value = re.sub(r"\s{2,}", " ", value)
    return value.strip(" -_.")


def clean_metadata(metadata: dict) -> dict:
    """Clean metadata values using cleaning rules."""
    cleaned = dict(metadata)
    cleaned["artist"] = clean_noise_words(cleaned.get("artist", ""))
    cleaned["title"] = clean_noise_words(cleaned.get("title", ""))
    cleaned["album"] = clean_album(cleaned.get("album", ""))
    cleaned["track"] = clean_track(cleaned.get("track", ""))
    cleaned["genre"] = clean_noise_words(cleaned.get("genre", ""))
    cleaned["year"] = re.sub(r"[^0-9]", "", cleaned.get("year", ""))[:4]
    cleaned["original"] = normalize_spaces(cleaned.get("original", ""))
    # Clean additional metadata fields
    cleaned["comments"] = clean_noise_words(cleaned.get("comments", ""))
    cleaned["albumartist"] = clean_noise_words(cleaned.get("albumartist", ""))
    cleaned["publisher"] = clean_noise_words(cleaned.get("publisher", ""))
    cleaned["composer"] = clean_noise_words(cleaned.get("composer", ""))
    return cleaned


def fill_missing_metadata(path: Path, metadata: dict) -> dict:
    """Separate process for files with missing metadata.
    Uses filename and folder clues to fill gaps."""
    fixed = dict(metadata)
    stem = clean_noise_words(path.stem)
    parts = [part.strip() for part in re.split(r"\s+-\s+", stem) if part.strip()]

    if not fixed.get("album"):
        if len(parts) >= 2:
            fixed["album"] = parts[0]
        else:
            fixed["album"] = clean_noise_words(path.parent.name)

    if not fixed.get("title"):
        if len(parts) >= 2:
            fixed["title"] = parts[1]
        elif parts:
            fixed["title"] = parts[0]

    if not fixed.get("artist") and len(parts) >= 3:
        fixed["artist"] = parts[2]

    return fixed


def apply_external_metadata(path: Path, metadata: dict, overrides: dict) -> dict:
    """Apply CLI/JSON metadata only for missing fields."""
    if not overrides:
        return dict(metadata)

    candidates = [
        path.name,
        path.stem,
        str(path),
        str(path.resolve()),
        "_default",
    ]

    patch = {}
    for key in candidates:
        if key in overrides and isinstance(overrides[key], dict):
            patch.update(overrides[key])

    updated = dict(metadata)
    for field in ("artist", "title", "album", "track", "genre", "year"):
        if not normalize_spaces(updated.get(field, "")) and normalize_spaces(patch.get(field, "")):
            updated[field] = patch[field]
    return updated


def load_metadata_overrides(json_file: str = "", inline_json: str = "") -> dict:
    """Load metadata overrides from JSON file or inline JSON."""
    overrides = {}

    if json_file:
        file_path = Path(json_file)
        if not file_path.exists():
            raise FileNotFoundError(f"Metadata JSON file not found: {file_path}")
        with file_path.open("r", encoding="utf-8") as f:
            content = json.load(f)
        if not isinstance(content, dict):
            raise ValueError("Metadata JSON must be an object keyed by filename/stem/path.")
        overrides.update(content)

    if inline_json:
        content = json.loads(inline_json)
        if not isinstance(content, dict):
            raise ValueError("Inline metadata JSON must be an object.")
        overrides.update(content)

    return overrides


def read_metadata(path: Path):
    """Read metadata from audio file."""
    audio = File(path, easy=True)
    metadata = {
        "artist": "",
        "title": "",
        "album": "",
        "track": "",
        "genre": "",
        "year": "",
        "original": path.stem,
        "comments": "",
        "albumartist": "",
        "publisher": "",
        "composer": "",
    }
    
    if audio is None or audio.tags is None:
        return metadata

    tags = audio.tags
    metadata["artist"] = get_easy_tag(tags, "artist")
    metadata["title"] = get_easy_tag(tags, "title")
    metadata["album"] = get_easy_tag(tags, "album")
    metadata["track"] = get_easy_tag(tags, "tracknumber", "track")
    metadata["genre"] = get_easy_tag(tags, "genre")
    metadata["year"] = first_non_empty(get_easy_tag(tags, "date"), get_easy_tag(tags, "year"))
    metadata["comments"] = get_easy_tag(tags, "comments", "comment", "description")
    metadata["albumartist"] = get_easy_tag(tags, "albumartist", "album artist")
    metadata["publisher"] = get_easy_tag(tags, "publisher", "organization", "label")
    metadata["composer"] = get_easy_tag(tags, "composer")
    
    return metadata


def write_metadata(path: Path, metadata: dict):
    """Write cleaned metadata and keep a backup for recovery on failures."""
    audio = File(path, easy=True)
    if audio is None:
        raise ValueError(f"Unsupported or unreadable file: {path}")

    backup = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, backup)

    try:
        if audio.tags is None:
            audio.add_tags()

        set_easy_tag(audio.tags, metadata.get("artist", ""), "artist")
        set_easy_tag(audio.tags, metadata.get("title", ""), "title")
        set_easy_tag(audio.tags, metadata.get("album", ""), "album")
        set_easy_tag(audio.tags, metadata.get("track", ""), "tracknumber", "track")
        set_easy_tag(audio.tags, metadata.get("genre", ""), "genre")
        set_easy_tag(audio.tags, metadata.get("year", ""), "date", "year")
        set_easy_tag(audio.tags, metadata.get("comments", ""), "comments", "comment", "description")
        set_easy_tag(audio.tags, metadata.get("albumartist", ""), "albumartist", "album artist")
        set_easy_tag(audio.tags, metadata.get("publisher", ""), "publisher", "organization", "label")
        set_easy_tag(audio.tags, metadata.get("composer", ""), "composer")

        audio.save()
        if path.stat().st_size <= 0:
            raise IOError("File size became zero after metadata save.")
    except Exception:
        shutil.copy2(backup, path)
        raise
    finally:
        if backup.exists():
            backup.unlink()


def metadata_changed(left: dict, right: dict) -> bool:
    """Check if metadata has changed between two dicts."""
    for key in ("artist", "title", "album", "track", "genre", "year", "comments", "albumartist", "publisher", "composer"):
        if normalize_spaces(left.get(key, "")) != normalize_spaces(right.get(key, "")):
            return True
    return False
