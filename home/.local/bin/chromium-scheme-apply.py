#!/usr/bin/env python3
"""Push ~/.config/current_theme/chromium.theme colors into the Scheme New Tab
extension.

chromium.theme format:
    line 1 = background hex   (e.g. #16242d)
    line 2 = text hex         (e.g. #d6e2ee)

The extension reads chromium.theme live when "Allow access to file URLs" is
enabled; colors.json (written here) is its fallback and is picked up on the
next new tab or within ~15s while a tab is open.

Usage:
    chromium-scheme-apply.py                # read chromium.theme
    chromium-scheme-apply.py --bg "#111c18" --text "#c1c497"
    chromium-scheme-apply.py --check        # show current values only
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

THEME_FILE = Path.home() / ".config/current_theme/chromium.theme"
NEWTAB_DIR = Path.home() / ".dotfiles/chromium/scheme-newtab"

HEX_RE = re.compile(r"^#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")


def normalize_hex(value: str) -> str:
    value = value.strip()
    if not value.startswith("#"):
        value = "#" + value
    if not HEX_RE.match(value):
        raise ValueError(f"bad color {value!r}: expected hex like #16242d")
    if len(value) == 4:
        value = "#" + "".join(c * 2 for c in value[1:])
    return value.lower()


def read_theme_file() -> tuple:
    lines = THEME_FILE.read_text().splitlines()
    if len(lines) < 2:
        raise ValueError(f"{THEME_FILE} must hold bg on line 1, text on line 2")
    return normalize_hex(lines[0]), normalize_hex(lines[1])


def write_newtab(bg: str, text: str) -> Path:
    NEWTAB_DIR.mkdir(parents=True, exist_ok=True)
    path = NEWTAB_DIR / "colors.json"
    payload = {
        "bg": bg,
        "text": text,
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Apply chromium.theme colors to the Scheme New Tab "
                    "extension (colors.json fallback).")
    ap.add_argument("--bg", help="override background hex")
    ap.add_argument("--text", help="override text hex")
    ap.add_argument("--check", action="store_true",
                    help="print resolved colors and exit")
    a = ap.parse_args(argv)

    try:
        if a.bg and a.text:
            bg, text = normalize_hex(a.bg), normalize_hex(a.text)
        elif a.bg or a.text:
            print("error: --bg and --text must be given together",
                  file=sys.stderr)
            return 2
        else:
            bg, text = read_theme_file()
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if a.check:
        print(f"bg={bg} text={text}")
        return 0

    try:
        c = write_newtab(bg, text)
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    print(f"chromium-scheme-apply: bg={bg} text={text}")
    print(f"  wrote {c}")
    print("  Scheme New Tab picks this up on the next new tab (or ~15s while "
          "open).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
