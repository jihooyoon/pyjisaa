#!/usr/bin/env python3
"""pyjisaa — Ji's Shopify App Event Analyzer (Python port of jisrot).

Usage:
    python main.py              Launch GUI
    python main.py reset        Reset persisted state and launch GUI
"""

import sys


def main() -> None:
    """Entry point — parse CLI args and launch the GUI."""
    reset_default = len(sys.argv) > 1 and sys.argv[1].lower() == "reset"

    from gui import run
    run(reset_default=reset_default)


if __name__ == "__main__":
    main()
