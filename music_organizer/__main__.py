#!/usr/bin/env python3
"""Entry point for python -m music_organizer"""

import sys

from . import config
from .cli import main as cli_main


if __name__ == "__main__":
    # Load configuration
    config.load_config()
    
    # If arguments provided, run CLI; otherwise try to run GUI
    if len(sys.argv) > 1:
        sys.exit(cli_main())
    else:
        try:
            from .gui import run_gui
            run_gui()
        except ImportError as e:
            if "tkinter" in str(e):
                print(f"Error: {e}")
                print("\nGUI requires tkinter. Install it with:")
                print("  Ubuntu/Debian: sudo apt-get install python3-tk")
                print("  macOS: brew install python-tk")
                print("  Windows: tkinter comes with Python")
                print("\nOr use CLI mode instead: python -m music_organizer --help")
                sys.exit(1)
            raise
