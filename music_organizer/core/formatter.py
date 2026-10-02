#!/usr/bin/env python3
"""Report and display formatting module for Music Organizer."""

import json
import re
from pathlib import Path
from typing import Dict, Optional

from .. import config


def write_report(report_file: Path, summary: dict):
    """Write summary report to JSON file."""
    report_file.parent.mkdir(parents=True, exist_ok=True)
    with report_file.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)


def validate_report(summary: dict):
    """Validate report structure and content."""
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
        if "audioQuality" not in item:
            raise ValueError(f"Report file entry {idx} missing key: audioQuality")

        audio_quality = item.get("audioQuality", {})
        if audio_quality and not isinstance(audio_quality, dict):
            raise ValueError(f"Report file entry {idx} has invalid audioQuality value")
        if audio_quality and audio_quality.get("success") and "quality_score" not in audio_quality:
            raise ValueError(f"Report file entry {idx} missing quality_score in audioQuality")


def format_metadata_block(path: Path, metadata: dict, label: str = "Metadata", audio_quality: dict = None) -> str:
    """Format metadata block for display."""
    lines = [f"--- {path.name} ({label}) ---"]
    for key in config.METADATA_KEYS:
        value = metadata.get(key, "")
        lines.append(f"  {key.capitalize():8}: {value if value else '(not available)'}")
    
    # Add audio quality info if available
    if audio_quality and audio_quality.get("success"):
        lines.append("--- Audio Quality ---")
        lines.append(f"  Score:      {audio_quality['quality_score']}/10 ({audio_quality['quality_tier'].upper()})")
        lines.append(f"  Codec:      {audio_quality['codec'] or 'Unknown'} {'(Lossless)' if audio_quality['is_lossless'] else '(Lossy)'}")
        if audio_quality['bitrate']:
            lines.append(f"  Bitrate:    {audio_quality['bitrate']} kbps")
        if audio_quality['sample_rate']:
            lines.append(f"  Sample:     {audio_quality['sample_rate']} Hz")
        if audio_quality['channels']:
            ch_type = "Mono" if audio_quality['channels'] == 1 else "Stereo" if audio_quality['channels'] == 2 else f"{audio_quality['channels']}Ch"
            lines.append(f"  Channels:   {ch_type}")
        if audio_quality.get('loudness_mean') is not None:
            lines.append(f"  Loudness:   {audio_quality['loudness_mean']} dB RMS")
        if audio_quality.get('loudness_peak') is not None:
            lines.append(f"  Peak:       {audio_quality['loudness_peak']} dB")
        if audio_quality.get('clipping_ratio') is not None:
            lines.append(f"  Clipping:   {round(audio_quality['clipping_ratio'] * 100, 3)}%")
        if audio_quality.get('dynamic_range') is not None:
            lines.append(f"  Dyn Range:  {audio_quality['dynamic_range']}")
        if audio_quality.get('bass_score') is not None:
            lines.append(f"  Bass Score: {audio_quality['bass_score']}/10")
        if audio_quality.get('treble_score') is not None:
            lines.append(f"  Treble:     {audio_quality['treble_score']}/10")
        if audio_quality.get('sound_score') is not None:
            lines.append(f"  Sound:      {audio_quality['sound_score']}/10")
    
    return "\n".join(lines)
