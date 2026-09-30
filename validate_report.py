#!/usr/bin/env python3
"""Double-click friendly report validator for Music Organizer."""

import importlib.util
import json
import sys
from pathlib import Path


def load_music_organizer_module(script_path: Path):
    spec = importlib.util.spec_from_file_location("music_organizer", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load script: {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate(report_path: Path):
    script_path = Path(__file__).with_name("music_organizer.py")
    module = load_music_organizer_module(script_path)

    if not report_path.exists():
        raise FileNotFoundError(f"Report file not found: {report_path}")

    with report_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    module.validate_report(payload)


def main():
    default_report = Path("music") / "music_organizer_report.json"

    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
    else:
        target = default_report

    try:
        validate(target)
        message = f"Report is valid: {target}"
        print(message)
    except Exception as exc:
        message = f"Report validation failed: {exc}"
        print(message)

    # Keep console open for non-technical users when launched by double-click.
    if len(sys.argv) == 1:
        input("\nPress Enter to close...")


if __name__ == "__main__":
    main()
