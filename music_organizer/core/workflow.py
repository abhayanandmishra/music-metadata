#!/usr/bin/env python3
"""File processing workflow module for Music Organizer."""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from .. import config
from .metadata import (
    clean_metadata, fill_missing_metadata, normalize_spaces, sanitize_field,
    sanitize_final, clean_noise_words, clean_separators, metadata_changed,
    read_metadata, write_metadata
)


def build_filename(template: str, metadata: dict) -> str:
    """Build filename from template and metadata."""
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
    """Build unique filename candidate avoiding collisions."""
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
    """Find all music files in directory."""
    if not directory.exists():
        raise FileNotFoundError(f"Folder does not exist: {directory}")
    return [
        path
        for path in sorted(directory.rglob("*"))
        if path.is_file() and path.suffix.lower() in config.SUPPORTED_EXTENSIONS
    ]


def ensure_music_dirs(root: Path):
    """Ensure music directories exist."""
    ip = root / "ip"
    op = root / "op"
    nc = root / "nc"
    ip.mkdir(parents=True, exist_ok=True)
    op.mkdir(parents=True, exist_ok=True)
    nc.mkdir(parents=True, exist_ok=True)
    return ip, op, nc


def has_missing_core(metadata: dict) -> bool:
    """Check if metadata is missing core fields."""
    return not normalize_spaces(metadata.get("album", "")) or not normalize_spaces(metadata.get("title", ""))


def safe_move(src: Path, dst: Path) -> Path:
    """Safely move file, handling existing target."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    candidate = dst
    index = 2
    while candidate.exists():
        candidate = dst.with_name(f"{dst.stem}_{index}{dst.suffix}")
        index += 1
    shutil.move(str(src), str(candidate))
    return candidate


def process_file(path: Path, overrides: dict = None) -> Tuple[dict, dict, Optional[dict]]:
    """Process single file: read, clean, fill missing metadata, analyze quality."""
    original = read_metadata(path)
    cleaned = clean_metadata(original)
    from ..core.metadata import apply_external_metadata
    cleaned = apply_external_metadata(path, cleaned, overrides or {})
    completed = fill_missing_metadata(path, cleaned)
    
    # Analyze audio quality
    audio_quality = None
    if config.AUDIO_ANALYZER and config.AUDIO_ANALYZER.ffmpeg_available:
        audio_quality = config.AUDIO_ANALYZER.analyze(path)
    
    return original, completed, audio_quality


def process_files_batch(
    files: list,
    pattern: str,
    dry_run: bool = False,
    write_back: bool = True,
    overrides: dict = None,
    apply_changes: bool = False,
    op_dir: Optional[Path] = None,
    nc_dir: Optional[Path] = None,
) -> Dict:
    """Process batch of files and return summary."""
    from .formatter import format_metadata_block, validate_report, write_report
    
    used_names = {}
    processed = 0
    summary = {
        "createdAt": datetime.now().isoformat(timespec="seconds"),
        "folder": str(files[0].parent) if files else "",
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
            "audioQuality": {},
            "metadataUpdated": False,
            "renamed": False,
            "newName": path.name,
            "errors": [],
            "status": "pending",
        }

        original, completed, audio_quality = process_file(path, overrides=overrides)
        file_report["originalMetadata"] = {k: original.get(k, "") for k in config.METADATA_KEYS}
        file_report["cleanedMetadata"] = {k: completed.get(k, "") for k in config.METADATA_KEYS}
        file_report["audioQuality"] = audio_quality or {}

        # Print all metadata first with audio quality
        print(format_metadata_block(path, original, label="Original", audio_quality=audio_quality))
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

    successful_audio = [f for f in summary["files"] if f.get("audioQuality", {}).get("success")]

    summary["totals"] = {
        "processed": processed,
        "metadataUpdated": sum(1 for f in summary["files"] if f["metadataUpdated"]),
        "renamed": sum(1 for f in summary["files"] if f["renamed"]),
        "op": sum(1 for f in summary["files"] if f.get("status") == "op"),
        "nc": sum(1 for f in summary["files"] if f.get("status") == "nc"),
        "errors": len(summary["errors"]),
        "audioQualityAnalyzed": len(successful_audio),
        "audioQualityAverage": round(
            (sum(f.get("audioQuality", {}).get("quality_score", 0) for f in successful_audio) / len(successful_audio))
            if successful_audio else 0.0,
            1,
        ),
    }

    validate_report(summary)
    return summary
