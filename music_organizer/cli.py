#!/usr/bin/env python3
"""Command-line interface for Music Organizer."""

import argparse
import json
from pathlib import Path

from . import config
from .core import (
    ensure_music_dirs,
    find_music_files,
    process_files_batch,
    validate_report,
    write_report,
)
from .core.metadata import load_metadata_overrides


def main():
    """Main CLI entry point."""
    
    # Load configuration from config.json (once at startup)
    config.load_config()
    
    parser = argparse.ArgumentParser(
        description="Clean metadata, update tags, and rename music files using metadata."
    )
    parser.add_argument(
        "folder",
        type=Path,
        nargs="?",
        default=config.DEFAULT_ROOT / "ip",
        help="Folder containing music files (default: music/ip)",
    )
    parser.add_argument(
        "--pattern",
        default=config.CONFIG.get("application", {}).get("default_pattern", "{album} - {title}"),
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
        default=str(config.DEFAULT_ROOT),
        help="Root folder containing ip/op/nc subfolders (default: music).",
    )
    parser.add_argument(
        "--source-nc",
        action="store_true",
        help="Read input files from music/nc for missing-metadata follow-up process.",
    )
    parser.add_argument(
        "--log-file",
        default="",
        help="Optional path to write detailed logs to a file.",
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

        if args.log_file:
            config.LOGGER.set_file_logging(Path(args.log_file))
            config.LOGGER.info(f"Detailed logging enabled: {args.log_file}")

        music_root = Path(args.music_root)
        ip_dir, op_dir, nc_dir = ensure_music_dirs(music_root)
        input_dir = nc_dir if args.source_nc else Path(args.folder)
        if args.folder == config.DEFAULT_ROOT / "ip" and not args.source_nc:
            input_dir = ip_dir

        overrides = load_metadata_overrides(args.metadata_json, args.metadata_inline_json)
        report_path = Path(args.report_file) if args.report_file else music_root / "music_organizer_report.json"
        effective_dry_run = True if not args.apply else args.dry_run

        files = find_music_files(input_dir)
        if not files:
            print(f"No supported music files were found in: {input_dir}")
            return 0

        summary = process_files_batch(
            files,
            args.pattern,
            dry_run=effective_dry_run,
            write_back=not args.no_write_metadata,
            overrides=overrides,
            apply_changes=args.apply,
            op_dir=op_dir,
            nc_dir=nc_dir,
        )

        if args.report_file:
            write_report(report_path, summary)
            print(f"Report written: {report_path}")

        processed = summary["totals"]["processed"]
        print(f"Done. {processed} file(s) processed.")
        return 0

    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        return 1
    except Exception as exc:  # pragma: no cover
        print(f"Unexpected error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
