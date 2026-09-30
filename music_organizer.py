#!/usr/bin/env python3
import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox

from mutagen import File

# Global configuration loaded at startup
CONFIG = {}
SUPPORTED_EXTENSIONS = set()
NOISE_WORDS = set()
METADATA_KEYS = ()
YEAR_IN_ALBUM = None
DEFAULT_ROOT = Path("music")


def load_config():
    """Load configuration from config.json. Falls back to defaults if file missing."""
    global CONFIG, SUPPORTED_EXTENSIONS, NOISE_WORDS, METADATA_KEYS, YEAR_IN_ALBUM, DEFAULT_ROOT
    
    config_path = Path(__file__).parent / "config.json"
    
    if config_path.exists():
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
            print(f"Warning: Failed to load config.json ({e}). Using defaults.", file=sys.stderr)
            _set_defaults()
            return False
    else:
        # Config file not found, use hardcoded defaults
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


def safe_value(value):
    if value is None:
        return ""
    if isinstance(value, list):
        return str(value[0]).strip() if value else ""
    return str(value).strip()


def first_non_empty(*values):
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
    return re.sub(r"\s+", " ", str(value or "")).strip()


def sanitize_field(value, fallback="unknown"):
    value = normalize_spaces(value)
    if not value:
        value = fallback
    value = re.sub(r"[\\/:*?\"<>|]", "_", value)
    value = value.rstrip(". ")
    return value


def sanitize_final(value):
    value = normalize_spaces(value)
    value = re.sub(r"[\\/:*?\"<>|]", "_", value)
    value = value.rstrip(". ")
    return value


def clean_noise_words(value):
    text = normalize_spaces(value)
    if not text:
        return ""
    
    # Sort noise words by length (longest first) to match complete phrases before components
    sorted_noise = sorted(NOISE_WORDS, key=len, reverse=True)
    
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
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"(?:\s*[-_]\s*){2,}", " - ", text)
    return text.strip(" -_.")


def clean_track(value: str) -> str:
    value = normalize_spaces(value)
    if not value:
        return ""
    match = re.match(r"(\d{1,3})", value)
    return match.group(1) if match else value


def clean_album(value: str) -> str:
    value = clean_noise_words(value)
    value = YEAR_IN_ALBUM.sub("", value)
    value = re.sub(r"\s{2,}", " ", value)
    return value.strip(" -_.")


def clean_metadata(metadata: dict) -> dict:
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
    audio = File(path, easy=True)
    if audio is None or audio.tags is None:
        return {
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

    tags = audio.tags
    return {
        "artist": get_easy_tag(tags, "artist"),
        "title": get_easy_tag(tags, "title"),
        "album": get_easy_tag(tags, "album"),
        "track": get_easy_tag(tags, "tracknumber", "track"),
        "genre": get_easy_tag(tags, "genre"),
        "year": first_non_empty(get_easy_tag(tags, "date"), get_easy_tag(tags, "year")),
        "original": path.stem,
        "comments": get_easy_tag(tags, "comments", "comment", "description"),
        "albumartist": get_easy_tag(tags, "albumartist", "album artist"),
        "publisher": get_easy_tag(tags, "publisher", "organization", "label"),
        "composer": get_easy_tag(tags, "composer"),
    }


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


def write_report(report_file: Path, summary: dict):
    report_file.parent.mkdir(parents=True, exist_ok=True)
    with report_file.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)


def validate_report(summary: dict):
    required_top = {"createdAt", "folder", "dryRun", "writeMetadata", "pattern", "files", "errors", "totals"}
    missing = required_top - set(summary.keys())
    if missing:
        raise ValueError(f"Report missing top-level keys: {sorted(missing)}")

    files = summary.get("files", [])
    totals = summary.get("totals", {})
    if totals.get("processed") != len(files):
        raise ValueError("Report totals.processed does not match files length")

    error_count = len(summary.get("errors", []))
    if totals.get("errors") != error_count:
        raise ValueError("Report totals.errors does not match errors length")

    for idx, item in enumerate(files):
        for key in ("file", "originalName", "originalMetadata", "cleanedMetadata", "metadataUpdated", "renamed", "newName", "errors", "status"):
            if key not in item:
                raise ValueError(f"Report file entry {idx} missing key: {key}")


def format_metadata_block(path: Path, metadata: dict, label: str = "Metadata") -> str:
    lines = [f"--- {path.name} ({label}) ---"]
    for key in METADATA_KEYS:
        value = metadata.get(key, "")
        lines.append(f"  {key.capitalize():8}: {value if value else '(not available)'}")
    return "\n".join(lines)


def build_filename(template: str, metadata: dict) -> str:
    values = {
        "artist": sanitize_field(metadata.get("artist", "")),
        "title": sanitize_field(metadata.get("title", "")),
        "album": sanitize_field(metadata.get("album", "")),
        "track": sanitize_field(metadata.get("track", "")),
        "genre": sanitize_field(metadata.get("genre", "")),
        "year": sanitize_field(metadata.get("year", "")),
        "original": sanitize_field(
            metadata.get("original", ""),
            fallback=metadata.get("original", "unnamed"),
        ),
    }

    formatted = template.format(**values)
    cleaned = clean_noise_words(formatted)
    cleaned = clean_separators(cleaned)
    cleaned = sanitize_final(cleaned)
    if not cleaned:
        return values["original"] or metadata.get("original", "") or "unnamed"
    return cleaned


def build_unique_candidate(path: Path, candidate_base: str, used_names: dict):
    extension = path.suffix.lower()
    candidate = f"{candidate_base}{extension}"
    count = used_names.get(candidate, 0)

    while True:
        if count > 0:
            base_name, ext = os.path.splitext(candidate)
            candidate = f"{base_name}_{count + 1}{ext}"
        new_path = path.with_name(candidate)
        if (not new_path.exists() or new_path == path) and candidate not in used_names:
            break
        count += 1

    used_names[candidate] = used_names.get(candidate, 0) + 1
    return candidate


def find_music_files(directory: Path):
    if not directory.exists():
        raise FileNotFoundError(f"Folder does not exist: {directory}")
    return [
        path
        for path in sorted(directory.rglob("*"))
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    ]


def ensure_music_dirs(root: Path):
    ip = root / "ip"
    op = root / "op"
    nc = root / "nc"
    ip.mkdir(parents=True, exist_ok=True)
    op.mkdir(parents=True, exist_ok=True)
    nc.mkdir(parents=True, exist_ok=True)
    return ip, op, nc


def has_missing_core(metadata: dict) -> bool:
    return not normalize_spaces(metadata.get("album", "")) or not normalize_spaces(metadata.get("title", ""))


def safe_move(src: Path, dst: Path) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    candidate = dst
    index = 2
    while candidate.exists():
        candidate = dst.with_name(f"{dst.stem}_{index}{dst.suffix}")
        index += 1
    shutil.move(str(src), str(candidate))
    return candidate


def metadata_changed(left: dict, right: dict) -> bool:
    for key in ("artist", "title", "album", "track", "genre", "year", "comments", "albumartist", "publisher", "composer"):
        if normalize_spaces(left.get(key, "")) != normalize_spaces(right.get(key, "")):
            return True
    return False


def process_file(path: Path, overrides: dict = None):
    original = read_metadata(path)
    cleaned = clean_metadata(original)
    cleaned = apply_external_metadata(path, cleaned, overrides or {})
    completed = fill_missing_metadata(path, cleaned)
    return original, completed


def rename_files(
    folder: Path,
    pattern: str,
    dry_run: bool = False,
    write_back: bool = True,
    overrides: dict = None,
    report_file: Path = None,
    apply_changes: bool = False,
    op_dir: Path = None,
    nc_dir: Path = None,
):
    files = find_music_files(folder)
    if not files:
        print(f"No supported music files were found in: {folder}")
        return 0

    used_names = {}
    processed = 0
    summary = {
        "createdAt": datetime.now().isoformat(timespec="seconds"),
        "folder": str(folder),
        "dryRun": dry_run,
        "writeMetadata": write_back,
        "pattern": pattern,
        "files": [],
        "errors": [],
    }

    for path in files:
        file_report = {
            "file": str(path),
            "originalName": path.name,
            "originalMetadata": {},
            "cleanedMetadata": {},
            "metadataUpdated": False,
            "renamed": False,
            "newName": path.name,
            "errors": [],
            "status": "pending",
        }

        original, completed = process_file(path, overrides=overrides)
        file_report["originalMetadata"] = {k: original.get(k, "") for k in METADATA_KEYS}
        file_report["cleanedMetadata"] = {k: completed.get(k, "") for k in METADATA_KEYS}

        # Print all metadata first.
        print(format_metadata_block(path, original, label="Original"))
        print(format_metadata_block(path, completed, label="Cleaned"))

        if metadata_changed(original, completed):
            if dry_run or not apply_changes:
                print("  Would update metadata tags")
            elif write_back:
                try:
                    write_metadata(path, completed)
                    print("  Updated metadata tags")
                    file_report["metadataUpdated"] = True
                except Exception as exc:
                    print(f"  Metadata update failed: {exc}")
                    msg = f"Metadata update failed: {exc}"
                    file_report["errors"].append(msg)
                    summary["errors"].append({"file": str(path), "error": msg})
            elif write_back:
                file_report["metadataUpdated"] = True

        new_name = build_filename(pattern, completed)
        candidate = build_unique_candidate(path, new_name, used_names)
        file_report["newName"] = candidate

        unresolved = has_missing_core(completed)
        if unresolved:
            file_report["status"] = "nc"

        if not apply_changes:
            if unresolved:
                print(f"  Would route to nc: {candidate}")
            elif path.name == candidate:
                print(f"  Would route unchanged to op: {path.name} (no change needed)")
            else:
                print(f"  Would route renamed to op: {candidate}")

            processed += 1
            summary["files"].append(file_report)
            print()
            continue

        if path.name == candidate:
            try:
                if unresolved:
                    # Missing core metadata — route to nc
                    if nc_dir:
                        moved = safe_move(path, nc_dir / path.name)
                        print(f"  Moved to nc (missing metadata): {moved.name}\n")
                    else:
                        print(f"  No rename needed, missing metadata: {path.name}\n")
                    file_report["status"] = "nc"
                else:
                    # Metadata complete, filename already correct — route to op
                    if op_dir:
                        moved = safe_move(path, op_dir / path.name)
                        print(f"  Moved to op (no rename needed): {moved.name}\n")
                    else:
                        print(f"  No rename needed: {path.name}\n")
                    file_report["status"] = "op"
            except Exception as exc:
                msg = f"Move failed: {exc}"
                print(f"  {msg}\n")
                file_report["errors"].append(msg)
                summary["errors"].append({"file": str(path), "error": msg})
            processed += 1
            summary["files"].append(file_report)
            continue

        if dry_run:
            print(f"  Would rename: {path.name} -> {candidate}\n")
            file_report["renamed"] = False
        else:
            try:
                new_path = path.with_name(candidate)
                path.rename(new_path)
                if unresolved and nc_dir:
                    moved = safe_move(new_path, nc_dir / new_path.name)
                    print(f"  Routed to nc: {moved.name}\n")
                    file_report["status"] = "nc"
                elif op_dir:
                    moved = safe_move(new_path, op_dir / new_path.name)
                    print(f"  Renamed+Moved to op: {path.name} -> {moved.name}\n")
                    file_report["status"] = "op"
                else:
                    print(f"  Renamed: {path.name} -> {candidate}\n")
                    file_report["status"] = "op"
                file_report["renamed"] = True
            except Exception as exc:
                msg = f"Rename failed: {exc}"
                print(f"  {msg}\n")
                file_report["errors"].append(msg)
                summary["errors"].append({"file": str(path), "error": msg})
        processed += 1
        summary["files"].append(file_report)

    summary["totals"] = {
        "processed": processed,
        "metadataUpdated": sum(1 for f in summary["files"] if f["metadataUpdated"]),
        "renamed": sum(1 for f in summary["files"] if f["renamed"]),
        "op": sum(1 for f in summary["files"] if f.get("status") == "op"),
        "nc": sum(1 for f in summary["files"] if f.get("status") == "nc"),
        "errors": len(summary["errors"]),
    }

    validate_report(summary)

    if report_file:
        write_report(report_file, summary)
        print(f"Report written: {report_file}")

    print(f"Done. {processed} file(s) processed.")
    return processed


def main():
    # Load configuration from config.json (once at startup)
    load_config()
    
    parser = argparse.ArgumentParser(
        description="Clean metadata, update tags, and rename music files using metadata."
    )
    parser.add_argument(
        "folder",
        type=Path,
        nargs="?",
        default=DEFAULT_ROOT / "ip",
        help="Folder containing music files (default: music/ip)",
    )
    parser.add_argument(
        "--pattern",
        default=CONFIG.get("application", {}).get("default_pattern", "{album} - {title}"),
        help=(
            "Naming pattern. Available fields: {artist}, {title}, {album}, "
            "{track}, {genre}, {year}, {original}"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show metadata updates and routing plan without changing files",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply metadata updates and move files to op/nc folders.",
    )
    parser.add_argument(
        "--no-write-metadata",
        action="store_true",
        help="Do not write cleaned metadata tags back to files",
    )
    parser.add_argument(
        "--metadata-json",
        default="",
        help=(
            "Path to JSON file with metadata patches keyed by filename/stem/path. "
            "Only missing metadata fields are filled from this source."
        ),
    )
    parser.add_argument(
        "--metadata-inline-json",
        default="",
        help=(
            "Inline JSON object in the same format as --metadata-json. "
            "Useful for CLI-driven missing metadata fixes."
        ),
    )
    parser.add_argument(
        "--report-file",
        default="",
        help="Write a JSON report of metadata updates, routes, and errors to this file.",
    )
    parser.add_argument(
        "--music-root",
        default=str(DEFAULT_ROOT),
        help="Root folder containing ip/op/nc subfolders (default: music).",
    )
    parser.add_argument(
        "--source-nc",
        action="store_true",
        help="Read input files from music/nc for missing-metadata follow-up process.",
    )
    parser.add_argument(
        "--validate-report",
        default="",
        help="Validate an existing report JSON file and exit.",
    )
    args = parser.parse_args()

    try:
        if args.validate_report:
            with Path(args.validate_report).open("r", encoding="utf-8") as f:
                payload = json.load(f)
            validate_report(payload)
            print(f"Report is valid: {args.validate_report}")
            return 0

        music_root = Path(args.music_root)
        ip_dir, op_dir, nc_dir = ensure_music_dirs(music_root)
        input_dir = nc_dir if args.source_nc else Path(args.folder)
        if args.folder == DEFAULT_ROOT / "ip" and not args.source_nc:
            input_dir = ip_dir

        overrides = load_metadata_overrides(args.metadata_json, args.metadata_inline_json)
        report_path = Path(args.report_file) if args.report_file else music_root / "music_organizer_report.json"
        effective_dry_run = True if not args.apply else args.dry_run

        rename_files(
            input_dir,
            args.pattern,
            dry_run=effective_dry_run,
            write_back=not args.no_write_metadata,
            overrides=overrides,
            report_file=report_path,
            apply_changes=args.apply,
            op_dir=op_dir,
            nc_dir=nc_dir,
        )
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        return 1
    except Exception as exc:  # pragma: no cover
        print(f"Unexpected error: {exc}")
        return 1

    return 0


class MusicRenamerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Music Organizer")
        self.geometry("980x720")
        self.minsize(880, 620)

        app_config = CONFIG.get("application", {})
        default_pattern = app_config.get("default_pattern", "{album} - {title}")
        default_dry_run = app_config.get("default_dry_run", True)
        default_write_metadata = app_config.get("write_metadata_default", True)

        self.folder_var = tk.StringVar(value="")
        self.pattern_var = tk.StringVar(value=default_pattern)
        self.search_var = tk.StringVar(value="")
        self.dry_run_var = tk.BooleanVar(value=default_dry_run)
        self.write_metadata_var = tk.BooleanVar(value=default_write_metadata)

        self.files = []
        self.records = {}
        self.filtered = []
        self.current_path = None

        self.build_ui()

    def build_ui(self):
        pad = {"padx": 10, "pady": 6}
        title_label = tk.Label(self, text="Music Organizer", font=("Segoe UI", 16, "bold"))
        title_label.pack(anchor="w", **pad)

        folder_frame = tk.Frame(self)
        folder_frame.pack(fill="x", **pad)
        tk.Label(folder_frame, text="Folder:").pack(anchor="w")

        folder_row = tk.Frame(folder_frame)
        folder_row.pack(fill="x")
        tk.Entry(folder_row, textvariable=self.folder_var).pack(side="left", fill="x", expand=True)
        tk.Button(folder_row, text="Browse", command=self.browse_folder).pack(side="left", padx=(8, 0))
        tk.Button(folder_row, text="Scan", command=self.scan_files).pack(side="left", padx=(8, 0))

        settings = tk.Frame(self)
        settings.pack(fill="x", **pad)
        tk.Label(settings, text="Default Name Pattern:").grid(row=0, column=0, sticky="w")
        tk.Entry(settings, textvariable=self.pattern_var).grid(row=0, column=1, sticky="ew", padx=(8, 0))
        settings.columnconfigure(1, weight=1)

        tk.Checkbutton(
            settings,
            text="Dry run",
            variable=self.dry_run_var,
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))
        tk.Checkbutton(
            settings,
            text="Write cleaned metadata",
            variable=self.write_metadata_var,
        ).grid(row=1, column=1, sticky="w", pady=(6, 0))

        search_frame = tk.Frame(self)
        search_frame.pack(fill="x", **pad)
        tk.Label(search_frame, text="Search / Filter:").pack(side="left")
        tk.Entry(search_frame, textvariable=self.search_var).pack(side="left", fill="x", expand=True, padx=(8, 0))
        self.search_var.trace_add("write", lambda *_: self.refresh_file_list())

        body = tk.PanedWindow(self, orient="horizontal", sashrelief="raised")
        body.pack(fill="both", expand=True, **pad)

        list_frame = tk.Frame(body)
        tk.Label(list_frame, text="Music Files").pack(anchor="w")
        self.file_list = tk.Listbox(list_frame, exportselection=False)
        self.file_list.pack(fill="both", expand=True)
        self.file_list.bind("<<ListboxSelect>>", self.on_file_select)
        body.add(list_frame, minsize=300)

        edit_frame = tk.Frame(body)
        tk.Label(edit_frame, text="Editable Metadata").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        self.meta_vars = {key: tk.StringVar(value="") for key in METADATA_KEYS if key != "original"}
        row = 1
        for key in ("artist", "title", "album", "track", "genre", "year", "albumartist", "composer", "publisher", "comments"):
            tk.Label(edit_frame, text=f"{key.capitalize()}:").grid(row=row, column=0, sticky="w", pady=4)
            tk.Entry(edit_frame, textvariable=self.meta_vars[key]).grid(row=row, column=1, sticky="ew", pady=4)
            row += 1

        edit_frame.columnconfigure(1, weight=1)

        tk.Button(edit_frame, text="Apply Clean", command=self.apply_clean_selected).grid(row=row, column=0, pady=(8, 0), sticky="w")
        tk.Button(edit_frame, text="Save Metadata", command=self.save_selected_metadata).grid(row=row, column=1, pady=(8, 0), sticky="w")
        row += 1
        tk.Button(edit_frame, text="Process Selected", command=self.rename_selected).grid(row=row, column=0, pady=(8, 0), sticky="w")
        tk.Button(edit_frame, text="Process All", command=self.process_all).grid(row=row, column=1, pady=(8, 0), sticky="w")
        row += 1

        compare_frame = tk.Frame(edit_frame)
        compare_frame.grid(row=row, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        compare_frame.columnconfigure(0, weight=1)
        compare_frame.columnconfigure(1, weight=1)

        tk.Label(compare_frame, text="Original (Read-only)").grid(row=0, column=0, sticky="w", padx=(0, 6))
        tk.Label(compare_frame, text="Current (Read-only)").grid(row=0, column=1, sticky="w", padx=(6, 0))

        self.original_box = tk.Text(compare_frame, height=10, wrap="word")
        self.original_box.grid(row=1, column=0, sticky="nsew", padx=(0, 6), pady=(4, 0))
        self.current_box = tk.Text(compare_frame, height=10, wrap="word")
        self.current_box.grid(row=1, column=1, sticky="nsew", padx=(6, 0), pady=(4, 0))
        self.original_box.configure(state="disabled")
        self.current_box.configure(state="disabled")

        body.add(edit_frame)

        output_header = tk.Frame(self)
        output_header.pack(fill="x", padx=10, pady=(4, 0))
        tk.Label(output_header, text="Output:").pack(side="left")
        tk.Button(output_header, text="Clear", command=self.clear_output).pack(side="right")
        self.output = tk.Text(self, height=11, wrap="word")
        self.output.pack(fill="both", expand=False, padx=10, pady=(0, 10))
        self.output.configure(state="disabled")

    def browse_folder(self):
        directory = filedialog.askdirectory(title="Select music folder")
        if directory:
            self.folder_var.set(directory)
            self.scan_files()

    def clear_output(self):
        self.output.configure(state="normal")
        self.output.delete("1.0", tk.END)
        self.output.configure(state="disabled")

    def _set_readonly_text(self, widget: tk.Text, content: str):
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, content)
        widget.configure(state="disabled")

    def clear_metadata_views(self):
        self._set_readonly_text(self.original_box, "")
        self._set_readonly_text(self.current_box, "")

    def refresh_metadata_views(self):
        if not self.current_path or self.current_path not in self.records:
            self.clear_metadata_views()
            return

        original = self.records[self.current_path].get("original", {})
        current = self.records[self.current_path].get("current", {})
        original_text = format_metadata_block(self.current_path, original, "Original")
        current_text = format_metadata_block(self.current_path, current, "Current")
        self._set_readonly_text(self.original_box, original_text)
        self._set_readonly_text(self.current_box, current_text)

    def log(self, text):
        self.output.configure(state="normal")
        self.output.insert(tk.END, text + "\n")
        self.output.see(tk.END)
        self.output.configure(state="disabled")

    def scan_files(self):
        folder = self.folder_var.get().strip()
        if not folder:
            messagebox.showwarning("Folder required", "Please select a folder first.")
            return

        folder_path = Path(folder)
        if not folder_path.exists():
            messagebox.showerror("Folder not found", f"Folder does not exist: {folder_path}")
            return

        self.output.configure(state="normal")
        self.output.delete("1.0", tk.END)
        self.output.configure(state="disabled")
        self.clear_metadata_views()

        self.files = find_music_files(folder_path)
        self.records.clear()

        for path in self.files:
            original, completed = process_file(path)
            self.records[path] = {"original": original, "current": completed}

        self.refresh_file_list()
        self.log(f"Loaded {len(self.files)} file(s).")

    def refresh_file_list(self):
        query = self.search_var.get().strip().lower()
        self.file_list.delete(0, tk.END)
        self.filtered = []

        for path in self.files:
            record = self.records.get(path, {})
            metadata = record.get("current", {})
            haystack = " ".join(
                [path.name]
                + [str(metadata.get(k, "")) for k in ("artist", "title", "album", "genre", "year")]
            ).lower()
            if query and query not in haystack:
                continue

            self.filtered.append(path)
            self.file_list.insert(tk.END, path.name)

    def on_file_select(self, _event=None):
        selection = self.file_list.curselection()
        if not selection:
            self.current_path = None
            self.clear_metadata_views()
            return

        index = selection[0]
        self.current_path = self.filtered[index]
        current = self.records[self.current_path]["current"]

        for key in self.meta_vars:
            self.meta_vars[key].set(current.get(key, ""))

        self.refresh_metadata_views()
        self.log(format_metadata_block(self.current_path, self.records[self.current_path]["original"], "Original"))
        self.log(format_metadata_block(self.current_path, current, "Current"))

    def apply_clean_selected(self):
        if not self.current_path:
            self.log("Select a file first.")
            return

        metadata = {key: self.meta_vars[key].get().strip() for key in self.meta_vars}
        metadata["original"] = self.current_path.stem
        metadata = fill_missing_metadata(self.current_path, clean_metadata(metadata))
        self.records[self.current_path]["current"] = metadata

        for key in self.meta_vars:
            self.meta_vars[key].set(metadata.get(key, ""))
        self.refresh_metadata_views()
        self.log(f"Applied cleaning rules to: {self.current_path.name}")

    def save_selected_metadata(self):
        if not self.current_path:
            self.log("Select a file first.")
            return

        metadata = {key: self.meta_vars[key].get().strip() for key in self.meta_vars}
        metadata["original"] = self.current_path.stem
        metadata = fill_missing_metadata(self.current_path, clean_metadata(metadata))

        try:
            write_metadata(self.current_path, metadata)
            self.records[self.current_path]["current"] = metadata
            self.refresh_metadata_views()
            self.log(f"Saved metadata for: {self.current_path.name}")
        except Exception as exc:
            self.log(f"Metadata save failed: {exc}")
            messagebox.showerror("Metadata save failed", str(exc))

    def rename_selected(self):
        if not self.current_path:
            self.log("Select a file first.")
            return

        pattern = self.pattern_var.get().strip() or "{album} - {title}"
        metadata = {key: self.meta_vars[key].get().strip() for key in self.meta_vars}
        metadata["original"] = self.current_path.stem
        metadata = fill_missing_metadata(self.current_path, clean_metadata(metadata))

        original = self.records.get(self.current_path, {}).get("original", {})
        changed = metadata_changed(original, metadata)

        if changed:
            if self.dry_run_var.get():
                self.log("Would update metadata tags")
            elif self.write_metadata_var.get():
                try:
                    write_metadata(self.current_path, metadata)
                    self.log(f"Updated metadata tags for: {self.current_path.name}")
                except Exception as exc:
                    self.log(f"Metadata update failed: {exc}")
                    messagebox.showerror("Metadata update failed", str(exc))
                    return

        self.records[self.current_path]["current"] = metadata
        for key in self.meta_vars:
            self.meta_vars[key].set(metadata.get(key, ""))

        candidate = build_filename(pattern, metadata) + self.current_path.suffix.lower()

        if self.current_path.name == candidate:
            self.refresh_metadata_views()
            self.log(f"No rename needed for: {self.current_path.name}")
            return

        if self.dry_run_var.get():
            self.refresh_metadata_views()
            self.log(f"Would rename: {self.current_path.name} -> {candidate}")
            return

        try:
            new_path = self.current_path.with_name(candidate)
            if new_path.exists():
                self.log(f"Rename skipped (target exists): {candidate}")
                return

            old_path = self.current_path
            old_path.rename(new_path)
            record = self.records.pop(old_path)
            self.current_path = new_path
            record["current"]["original"] = new_path.stem
            self.records[new_path] = record
            self.files = [new_path if p == old_path else p for p in self.files]
            self.refresh_file_list()
            self.refresh_metadata_views()
            self.log(f"Renamed: {new_path.name}")
        except Exception as exc:
            self.log(f"Rename failed: {exc}")
            messagebox.showerror("Rename failed", str(exc))

    def process_all(self):
        folder = self.folder_var.get().strip()
        if not folder:
            messagebox.showwarning("Folder required", "Please select a folder first.")
            return

        try:
            music_root = DEFAULT_ROOT
            _, op_dir, nc_dir = ensure_music_dirs(music_root)
            report_path = music_root / "music_organizer_report.json"
            is_dry_run = self.dry_run_var.get()
            processed = rename_files(
                Path(folder),
                self.pattern_var.get().strip() or "{album} - {title}",
                dry_run=is_dry_run,
                write_back=self.write_metadata_var.get(),
                report_file=report_path,
                apply_changes=not is_dry_run,
                op_dir=op_dir if not is_dry_run else None,
                nc_dir=nc_dir if not is_dry_run else None,
            )
            self.log(f"Processed {processed} file(s). Report: {report_path}")
            self.scan_files()
        except Exception as exc:
            self.log(f"Process failed: {exc}")
            messagebox.showerror("Process failed", str(exc))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        raise SystemExit(main())
    load_config()  # Load config for GUI mode
    MusicRenamerGUI().mainloop()