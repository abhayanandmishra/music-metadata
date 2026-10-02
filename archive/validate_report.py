#!/usr/bin/env python3
"""Double-click friendly report validator for Music Organizer."""

import json
import sys
from pathlib import Path

from music_organizer.core.formatter import validate_report


def main():
    default_report = Path("music") / "music_organizer_report.json"

    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
    else:
        target = default_report

    try:
        if not target.exists():
            raise FileNotFoundError(f"Report file not found: {target}")

        with target.open("r", encoding="utf-8") as f:
            payload = json.load(f)

        validate_report(payload)
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
