#!/usr/bin/env python3
"""
Usage
-----
  python3 ~/.config/yazi/regen-icons.py [--dry-run]

Backs up ~/.config/yazi/theme.toml to theme.toml.bak-<timestamp> before writing.
Revert with:  cp ~/.config/yazi/theme.toml.bak-<timestamp> ~/.config/yazi/theme.toml
"""

import argparse
import os
import re
import shutil
import sys
import time

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    sys.exit("error: Python 3.11+ required (tomllib missing)")

HOME = os.path.expanduser("~")
KITTY_CONF = os.path.join(HOME, ".config", "kitty", "kitty-colors.conf")
YAZI_THEME = os.path.join(HOME, ".config", "yazi", "theme.toml")
PRESET_URL = (
    "https://raw.githubusercontent.com/sxyazi/yazi/shipped/yazi-config/preset/theme-dark.toml"
)

# Delimiters around the generated block, so re-runs can find and replace it
# without disturbing anything else in theme.toml.
GEN_HEADER_START = "# >>> regen-icons.py (generated block, do not edit) >>>\n"
GEN_HEADER_END = "# <<< regen-icons.py <<<\n"

# yazi color name -> ANSI index. Verified against yazi v26.9.1
# yazi-tty/src/sequence/style.rs (SetFg): gray=37(7), darkgray=90(8), white=97(15).
NAMES = [
    "black", "red", "green", "yellow", "blue", "magenta", "cyan", "gray",
    "darkgray", "lightred", "lightgreen", "lightyellow",
    "lightblue", "lightmagenta", "lightcyan", "white",
]

# Fallback palette (xterm defaults) if kitty config cannot be read.
FALLBACK = [
    "#000000", "#cd0000", "#00cd00", "#cdcd00", "#0000ee", "#cd00cd", "#00cdcd", "#c0c0c0",
    "#808080", "#ff0000", "#00ff00", "#ffff00", "#5c5cff", "#ff00ff", "#00ffff", "#ffffff",
]


def hex_to_rgb(h):
    h = h.strip().lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_lab(rgb):
    """sRGB -> CIE L*a*b* (D65), for perceptual nearest-colour matching."""
    def lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (lin(c) for c in rgb)
    x = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = 0.0193339 * r + 0.1191920 * g + 0.9503041 * b
    x, y, z = x / 0.95047, y / 1.00000, z / 1.08883

    def f(t):
        return t ** (1 / 3) if t > 216 / 24389 else ((841 / 108) * t + 4 / 29)

    fx, fy, fz = f(x), f(y), f(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def relative_luminance(rgb):
    """WCAG relative luminance."""
    def lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    """WCAG contrast ratio between two RGB colors."""
    la, lb = relative_luminance(a), relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# Minimum contrast an icon color must keep against the terminal background.
# 3.0 == WCAG AA for large text / graphical objects. Without this, dark icons
# (e.g. devicon #41535b) map onto a dark palette entry and become invisible.
MIN_CONTRAST = 3.0


def read_kitty_palette():
    """Pull color0..color15 (and background) out of the kitty config."""
    try:
        with open(KITTY_CONF, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        print(f"warn: cannot read {KITTY_CONF} ({exc}); using xterm fallback palette")
        return list(FALLBACK), "#000000", True

    found = {}
    for m in re.finditer(r"^\s*color(\d{1,2})\s+(\S+)", text, re.M):
        idx = int(m.group(1))
        if 0 <= idx <= 15 and m.group(2).startswith("#"):
            found[idx] = m.group(2)[:7].lower()

    bg = None
    m = re.search(r"^\s*background\s+(#[0-9a-fA-F]{6})", text, re.M)
    if m:
        bg = m.group(1).lower()

    used_fallback = False
    if len(found) < 16:
        missing = sorted(set(range(16)) - set(found))
        print(f"warn: kitty config defines only {len(found)}/16 colors "
              f"(missing {missing}); filling from xterm defaults")
        found = {i: found.get(i, FALLBACK[i]) for i in range(16)}
        used_fallback = True
    if bg is None:
        print("warn: no `background` in kitty config; assuming #000000")
        bg, used_fallback = "#000000", True

    return [found[i] for i in range(16)], bg, used_fallback


def fetch_preset_icon_block(dest):
    """Download the shipped dark theme and return its [icon] section."""
    import urllib.request

    print(f"fetching preset theme: {PRESET_URL}")
    with urllib.request.urlopen(PRESET_URL, timeout=30) as resp:
        text = resp.read().decode("utf-8")
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write(text)

    block = text[text.index("[icon]"):]
    if not block.rstrip().endswith("}"):
        sys.exit("error: [icon] is not the final section of the preset; aborting")
    return block


def remap(block, palette, bg_hex):
    """Replace every fg = "#rrggbb" with the nearest named palette color.

    Candidates are the palette entries that stay legible against the terminal
    background; among those, pick the perceptually nearest (CIE L*a*b*).
    """
    labs = [rgb_to_lab(hex_to_rgb(c)) for c in palette]
    bg = hex_to_rgb(bg_hex)

    readable, rejected = [], []
    for i, c in enumerate(palette):
        ratio = contrast(hex_to_rgb(c), bg)
        (readable if ratio >= MIN_CONTRAST else rejected).append((i, ratio))

    if not readable:
        print("warn: no palette entry clears the contrast floor; ignoring it")
        readable = [(i, contrast(hex_to_rgb(c), bg)) for i, c in enumerate(palette)]

    stats, changed, nudged = {}, 0, 0

    def sub(m):
        nonlocal changed, nudged
        original = m.group(1)
        lab = rgb_to_lab(hex_to_rgb(original))
        # plain CIE76 distance; ties resolve to the lowest ANSI index for stability
        best = min(readable, key=lambda e: (
            (lab[0] - labs[e[0]][0]) ** 2
            + (lab[1] - labs[e[0]][1]) ** 2
            + (lab[2] - labs[e[0]][2]) ** 2,
            e[0],
        ))[0]
        name = NAMES[best]
        stats[name] = stats.get(name, 0) + 1
        changed += 1
        return f'fg = "{name}"'

    out = re.sub(r'fg\s*=\s*"(#[0-9a-fA-F]{6})"', sub, block)
    return out, stats, changed, readable, rejected


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="write to /tmp instead of touching theme.toml")
    args = ap.parse_args()

    palette, bg, used_fallback = read_kitty_palette()
    print(f"\nKitty background: {bg}")
    print("Kitty palette used for matching:")
    for i in range(0, 16, 8):
        print("  " + "  ".join(f"color{i + j}:{palette[i + j]}" for j in range(8)))

    preset_path = "/tmp/yazi-explore/theme-dark.toml"
    os.makedirs(os.path.dirname(preset_path), exist_ok=True)
    block = fetch_preset_icon_block(preset_path)

    rules = len(re.findall(r'text\s*=', block))
    new_block, stats, changed, readable, rejected = remap(block, palette, bg)
    print(f"\nicon rules: {rules}   colors remapped: {changed}")
    print(f"contrast floor {MIN_CONTRAST}:1 vs background")
    for i, ratio in readable:
        print(f"  usable   {NAMES[i]:<13} {palette[i]}  {ratio:5.2f}:1")
    for i, ratio in rejected:
        print(f"  EXCLUDED {NAMES[i]:<13} {palette[i]}  {ratio:5.2f}:1  (too low contrast)")
    print("distribution:")
    for i, name in enumerate(NAMES):
        if name in stats:
            print(f"  {name:<13} {palette[i]}  x{stats[name]}")

    if args.dry_run:
        out = "/tmp/yazi-explore/theme-new.toml"
        print(f"\n[dry-run] would write {out}")
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(new_block)
        return

    # Keep the user's existing theme.toml content, but replace any previously
    # generated [icon] block (from its header comment to EOF) so re-running is
    # idempotent and can repair a theme.toml that was truncated by another tool
    # such as yazi-pad.
    existing = ""
    if os.path.exists(YAZI_THEME):
        with open(YAZI_THEME, encoding="utf-8") as fh:
            existing = fh.read()
        marker = existing.find(GEN_HEADER_START)
        if marker != -1:
            print(f"\nreplacing generated [icon] block at byte {marker}")
            existing = existing[:marker].rstrip("\n") + "\n"
        elif "[icon]" in existing:
            sys.exit("error: theme.toml has a hand-written [icon] section. Back it up\n"
                     "       and delete it, then re-run -- the generator owns [icon].")

    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = f"{YAZI_THEME}.bak-{stamp}"

    header = (
        GEN_HEADER_START
        + "# Generated by regen-icons.py -- do not edit by hand.\n"
        + "# Every icon color is a Kitty ANSI palette name so icons follow the\n"
        + "# active Kitty theme. Re-run the script after changing Kitty themes.\n"
        + f"# Source: yazi shipped preset theme-dark.toml ([icon], {rules} rules)\n"
        + GEN_HEADER_END
    )
    # Generated block goes FIRST so it can never end up nested inside another
    # section's body (e.g. [indicator]), which would confuse tools that edit
    # theme.toml section-by-section such as yazi-pad.
    content = header + new_block.rstrip("\n") + "\n"
    if existing.strip():
        content += "\n" + existing.strip("\n") + "\n"

    # Validate BEFORE writing, so a bad file is never left on disk.
    parsed = tomllib.loads(content)
    icon = parsed.get("icon", {})
    missing = [k for k in ("globs", "dirs", "files", "exts", "conds") if k not in icon]
    if missing:
        sys.exit(f"error: generated theme is missing icon keys: {missing}")

    shutil.copy2(YAZI_THEME, backup)
    print(f"\nbackup: {backup}")

    with open(YAZI_THEME, "w", encoding="utf-8") as fh:
        fh.write(content)

    # Confirm what actually landed on disk.
    with open(YAZI_THEME, "rb") as fh:
        written = tomllib.load(fh)
    wicon = written.get("icon", {})
    total = sum(len(v) for v in wicon.values() if isinstance(v, list))
    print(f"wrote {YAZI_THEME}")
    print(f"verified: valid TOML, icon keys {list(wicon)}, {total} rules parsed")
    if "indicator" in written:
        print(f"preserved: [indicator] {written['indicator']}")
    if used_fallback:
        print("\nnote: some palette entries came from the xterm fallback")


if __name__ == "__main__":
    main()
