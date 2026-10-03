#!/usr/bin/env python3
"""Set Dark Reader (chromium extension) background + text colors from CLI.

Matches Dark Reader's global dark theme to your Hyprland/system colorscheme.

Extension ID: eimadpbcbfnmbkopoojfekhnkhdbieeh (Chrome Web Store, Dark Reader)
What it changes: the `theme` key in chrome.storage.local ->
    theme.darkSchemeBackgroundColor and theme.darkSchemeTextColor
    (optionally lightScheme* too with --light-bg/--light-text), and with
    --mode the theme.mode switch that decides WHICH of those two pairs is
    actually used by the page (Dark Reader: 1 = dark, 0 = light).

NEW IN THIS COPY (the original darkreader-theme.py is untouched):
    --mode dark   -> writes theme.mode = 1, requires --bg and --text
    --mode light  -> writes theme.mode = 0, requires --light-bg and
                     --light-text
    Omitting --mode leaves theme.mode alone, so you can retune both colour
    pairs without changing which one is active.

Two methods (stdlib only, no pip packages required):

  1. live (DEFAULT, recommended) .. talks to your RUNNING chromium over the
     Chrome DevTools Protocol and calls chrome.storage.local.set() inside
     Dark Reader's own service worker. Pages re-theme instantly, no restart.
     Requires chromium to expose a debug port (one-time setting, see --help
     and the NOTES section below).

  2. offline .. patches chromium's LevelDB log files directly
     (~/.config/chromium/<Profile>/Local Extension Settings/<id>/000003.log
     and the Sync copy). Requires chromium FULLY CLOSED (no chromium
     process holding the files). Same-length hex swap + CRC32C fix.
     If the `theme` record has already been flushed into an .ldb SSTable
     (LevelDB compaction - the record is then invisible to a log-only
     patch), a fresh override record with a higher sequence number is
     APPENDED to the current log instead, and the effective value is
     re-read and verified afterwards.

Usage:
    darkreader-theme.py --bg "#111c18" --text "#c1c497"
    darkreader-theme-mode.py --mode light --light-bg "#dfe4c4" \
        --light-text "#1c2d28"
    darkreader-theme-mode.py --mode dark --bg "$BG" --text "$FG"
    darkreader-theme-mode.py --light-bg "$BG" --light-text "$FG"
    darkreader-theme.py --scheme "Osaka Jade Bamboo"
    darkreader-theme.py --list
    darkreader-theme.py --bg "#1e1e2e" --text "#cdd6f4" --method offline
    darkreader-theme.py --bg "#1e1e2e" --text "#cdd6f4" --dry-run

Hyprland hook example (call from your wallpaper/theme switch script):
    python3 ~/Documents/darkreader-theme.py --bg "$BG" --text "$FG"
"""

import argparse
import base64
import binascii
import hashlib
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import urllib.request
from pathlib import Path

EXT_ID = "eimadpbcbfnmbkopoojfekhnkhdbieeh"
DEFAULT_PORT = 9222
DEFAULT_PROFILE = "Default"
HEX_RE = re.compile(r"^#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")

# Dark Reader's ThemeMode enum, as stored in chrome.storage.local theme.mode:
#   1 = dark (uses darkScheme* colours), 0 = light (uses lightScheme* colours).
# Verified against the installed bundle:
#   function getBgPole(theme) {
#       const isDarkScheme = theme.mode === 1;
#       const prop = isDarkScheme ? "darkSchemeBackgroundColor"
#                                : "lightSchemeBackgroundColor";
MODE_VALUE = {"dark": 1, "light": 0}
MODE_NAME = {1: "dark", 0: "light"}

BLOCK_SIZE = 32768
HEADER_SIZE = 7
MASK_DELTA = 0xA282EAD8


# --------------------------------------------------------------------------
# color helpers
# --------------------------------------------------------------------------

def normalize_hex(value: str) -> str:
    value = value.strip()
    if not value.startswith("#"):
        value = "#" + value
    if not HEX_RE.match(value):
        raise ValueError(
            f"bad color {value!r}: expected hex like #1e1e2e or #abc")
    if len(value) == 4:  # expand #abc -> #aabbcc
        value = "#" + "".join(c * 2 for c in value[1:])
    return value.lower()


def load_schemes(drconf: Path) -> dict:
    """Parse a Dark Reader color-schemes.drconf file -> {name: dict}."""
    schemes = {}
    if not drconf.exists():
        return schemes
    text = drconf.read_text(encoding="utf-8", errors="replace")
    # blocks separated by ==== lines; each has a name, DARK bg/text, LIGHT bg/text
    blocks = re.split(r"=+", text)
    for block in blocks:
        lines = [ln.strip() for ln in block.strip().splitlines() if ln.strip()]
        if not lines:
            continue
        name = lines[0]
        dark_bg = dark_tx = light_bg = light_tx = None
        section = None
        for ln in lines[1:]:
            up = ln.upper()
            if up == "DARK":
                section = "dark"
            elif up == "LIGHT":
                section = "light"
            elif ln.lower().startswith("background:"):
                col = ln.split(":", 1)[1].strip()
                if section == "dark":
                    dark_bg = col
                else:
                    light_bg = col
            elif ln.lower().startswith("text:"):
                col = ln.split(":", 1)[1].strip()
                if section == "dark":
                    dark_tx = col
                else:
                    light_tx = col
        if dark_bg or dark_tx:
            schemes[name] = {"dark_bg": dark_bg, "dark_text": dark_tx,
                             "light_bg": light_bg, "light_text": light_tx}
    return schemes


# --------------------------------------------------------------------------
# CRC32C (Castagnoli) + LevelDB masking, pure stdlib
# --------------------------------------------------------------------------

def _crc32c_table():
    poly = 0x82F63B78  # reflected 0x1EDC6F41
    tab = []
    for i in range(256):
        crc = i
        for _ in range(8):
            crc = (crc >> 1) ^ poly if crc & 1 else crc >> 1
        tab.append(crc & 0xFFFFFFFF)
    return tab


_CRC32C_TAB = _crc32c_table()


def crc32c(data: bytes, crc: int = 0xFFFFFFFF) -> int:
    for b in data:
        crc = _CRC32C_TAB[(crc ^ b) & 0xFF] ^ (crc >> 8)
    return (crc ^ 0xFFFFFFFF) & 0xFFFFFFFF


def mask_crc(crc: int) -> int:
    rot = (((crc >> 15) | (crc << 17)) & 0xFFFFFFFF)
    return (rot + MASK_DELTA) & 0xFFFFFFFF


def record_checksum(rec_type: int, payload: bytes) -> int:
    return mask_crc(crc32c(bytes([rec_type]) + payload))


# --------------------------------------------------------------------------
# LevelDB log walk (read-only verify + targeted CRC repair)
# --------------------------------------------------------------------------

def iter_log_records(data: bytes):
    """Yield (block_start, hdr_off, rec_type, length, payload_off)."""
    n = len(data)
    for bstart in range(0, n, BLOCK_SIZE):
        pos = bstart
        bend = min(bstart + BLOCK_SIZE, n)
        while pos + HEADER_SIZE <= bend:
            hdr = data[pos:pos + HEADER_SIZE]
            if hdr == b"\x00" * HEADER_SIZE:
                break  # block trailer padding
            checksum, length, rtype = struct.unpack("<IH B", hdr)
            if rtype == 0:  # kZeroType filler
                break
            if pos + HEADER_SIZE + length > bend:
                break  # torn write at EOF; stop this block
            yield (bstart, pos, rtype, length, pos + HEADER_SIZE)
            pos += HEADER_SIZE + length


def verify_log_checksums(path: Path):
    data = path.read_bytes()
    ok = bad = 0
    for (_, hdr_off, rtype, length, pay_off) in iter_log_records(data):
        stored, _, _ = struct.unpack(
            "<IH B", data[hdr_off:hdr_off + HEADER_SIZE])
        payload = data[pay_off:pay_off + length]
        if stored == record_checksum(rtype, payload):
            ok += 1
        else:
            bad += 1
    return ok, bad


def repair_ranges(path: Path, ranges):
    """Recompute checksums for records overlapping byte `ranges`.

    ranges: list of (start, end) offsets that were modified (same-length edit).
    Returns number of repaired record headers.
    """
    data = bytearray(path.read_bytes())
    fixed = 0
    for (_, hdr_off, rtype, length, pay_off) in iter_log_records(bytes(data)):
        rec_start, rec_end = hdr_off, pay_off + length
        if any(s < rec_end and rec_start < e for (s, e) in ranges):
            payload = bytes(data[pay_off:pay_off + length])
            new_crc = record_checksum(rtype, payload)
            struct.pack_into("<I", data, hdr_off, new_crc)
            fixed += 1
    path.write_bytes(bytes(data))
    return fixed


THEME_KEY = b"\x01\x05theme"  # tag=PUT(1), keylen=5, key="theme"

BG_KEY = "darkSchemeBackgroundColor"
TX_KEY = "darkSchemeTextColor"
LBG_KEY = "lightSchemeBackgroundColor"
LTX_KEY = "lightSchemeTextColor"
MODE_KEY = "mode"
THEME_FIELDS = (BG_KEY, TX_KEY, LBG_KEY, LTX_KEY, MODE_KEY)
FIELD_SHORT = {BG_KEY: "bg", TX_KEY: "text", LBG_KEY: "light-bg",
               LTX_KEY: "light-text", MODE_KEY: "mode"}


def requested_fields(bg=None, text=None, light_bg=None, light_text=None,
                     mode=None):
    """Build the {theme field: wanted value} map for the requested subset.

    Anything left as None is simply not touched, so one call can patch the
    light scheme only, the mode only, or everything at once.
    """
    req = {}
    for key, val in ((BG_KEY, bg), (TX_KEY, text), (LBG_KEY, light_bg),
                     (LTX_KEY, light_text), (MODE_KEY, mode)):
        if val is not None:
            req[key] = val
    return req


def fmt_fields(fields: dict) -> str:
    """Human readable `bg=#.. text=#.. mode=0` for a field map."""
    return " ".join(f"{FIELD_SHORT[k]}={fields[k]}"
                    for k in THEME_FIELDS
                    if k in fields and fields[k] is not None)


def _field_pattern(key: str) -> bytes:
    """Same-length matcher for one theme field (offline patch constraint)."""
    if key == MODE_KEY:
        return rb'"mode":[0-9]'
    return rb'"' + key.encode() + rb'":"#[0-9a-fA-F]{6}"'


def _field_replacement(key: str, value) -> bytes:
    """Same-length replacement for one theme field."""
    if key == MODE_KEY:
        return f'"{key}":{value}'.encode()
    return f'"{key}":"{value}"'.encode()


def _patch_theme_json(blob: bytes, req: dict):
    """Same-length field swap inside one Dark Reader theme JSON blob.

    Only fields present in `req` are touched. Returns (new_blob, missing)
    where `missing` lists requested fields that were not found in this blob
    (nothing is written for those, and the caller decides how to report).
    """
    new_blob = blob
    missing = []
    for key, value in req.items():
        new_blob, n = re.subn(_field_pattern(key),
                              _field_replacement(key, value),
                              new_blob, count=1)
        if n == 0:
            missing.append(key)
    if len(new_blob) != len(blob):
        raise RuntimeError("length changed during patch (bug): refusing")
    return new_blob, missing


def patch_theme_record_colors(data: bytes, req: dict):
    """Replace fields inside standalone `theme` records only.

    Returns (new_data, n_records_touched, ranges, missing) where `ranges`
    are the byte spans that changed and `missing` the requested fields that
    no record contained. customThemes inner entries are NOT touched: we only
    edit JSON blobs that immediately follow the THEME_KEY marker (the global
    theme value).
    """
    out = bytearray(data)
    touched = 0
    ranges = []
    missing = set()
    search_from = 0
    while True:
        i = bytes(out).find(THEME_KEY, search_from)
        if i < 0:
            break
        vstart = i + len(THEME_KEY)
        # value length is a varint32 right after the key; JSON starts with {
        j = bytes(out).find(b'{"brightness"', vstart, vstart + 32)
        if j < 0:
            search_from = i + 1
            continue
        # find end of this JSON object: it ends with  }  followed by \x01 (next
        # k/v tag) or end-of-batch. Scan for the '"textStroke":0,...}' tail.
        tail = bytes(out).find(b'"useFont":false}', j)
        if tail < 0:
            search_from = i + 1
            continue
        jend = tail + len(b'"useFont":false}')
        blob = bytes(out[j:jend])
        new_blob, absent = _patch_theme_json(blob, req)
        if absent:                    # never half-patch a record
            missing.update(absent)
            search_from = i + 1
            continue
        out[j:jend] = new_blob
        touched += 1
        ranges.append((j, jend))
        search_from = jend
    return bytes(out), touched, ranges, missing


# --------------------------------------------------------------------------
# LevelDB introspection (read-only): find where the `theme` record really
# lives, and what value chromium would load.  Needed because LevelDB moves
# records out of the write-ahead .log into .ldb SSTables once the memtable
# (write buffer) fills - a log-only patch then silently does nothing.
# --------------------------------------------------------------------------

FIELD_RE = {key: re.compile((r'"' + key + r'":"(#[0-9a-fA-F]{6})"').encode())
            for key in THEME_FIELDS if key != MODE_KEY}
MODE_FIELD_RE = re.compile(rb'"mode":([0-9])')
TABLE_MAGIC = 0xDB4775248B80FB57
K_TYPE_VALUE = 1
K_TYPE_DELETION = 0


def field_of(value, key):
    """Effective value of ONE Dark Reader theme field, or None.

    None means 'not present / not parseable', which is deliberately not the
    same as a value that merely differs from what we asked for.
    """
    if not value:
        return None
    if key == MODE_KEY:
        m = MODE_FIELD_RE.search(value)
        return int(m.group(1)) if m else None
    m = FIELD_RE[key].search(value)
    return m.group(1).decode().lower() if m else None


def fields_of(value, req):
    """{key: effective value} for the keys in `req` (None where absent)."""
    return {k: field_of(value, k) for k in req}


def _varint(buf, i):
    v = s = 0
    while True:
        if i >= len(buf):
            raise ValueError("varint truncated")
        x = buf[i]
        i += 1
        v |= (x & 0x7F) << s
        if not x & 0x80:
            return v, i
        s += 7


def _put_varint(v: int) -> bytes:
    out = bytearray()
    while v >= 0x80:
        out.append((v & 0x7F) | 0x80)
        v >>= 7
    out.append(v)
    return bytes(out)


def _snappy_decompress(src: bytes) -> bytes:
    """Snappy raw-block decoder (stdlib only)."""
    out = bytearray()
    n, i = _varint(src, 0)
    while i < len(src):
        tag = src[i]
        i += 1
        t = tag & 0x03
        if t == 0:                                   # literal
            ln = tag >> 2
            if ln < 60:
                ln += 1
            else:
                nb = ln - 59
                ln = int.from_bytes(src[i:i + nb], "little") + 1
                i += nb
            out += src[i:i + ln]
            i += ln
        else:                                        # copy
            if t == 1:
                ln = 4 + ((tag >> 2) & 0x07)
                off = ((tag & 0xE0) << 3) | src[i]
                i += 1
            elif t == 2:
                ln = (tag >> 2) + 1
                off = int.from_bytes(src[i:i + 2], "little")
                i += 2
            else:
                ln = (tag >> 2) + 1
                off = int.from_bytes(src[i:i + 4], "little")
                i += 4
            if off == 0 or off > len(out):
                raise ValueError("bad snappy copy offset")
            for _ in range(ln):
                out.append(out[-off])
    if len(out) != n:
        raise ValueError(f"snappy size mismatch ({len(out)} != {n})")
    return bytes(out)


def _read_block(data: bytes, off: int, size: int) -> bytes:
    payload = data[off:off + size]
    ctype = data[off + size]
    if ctype == 0:
        return payload
    if ctype == 1:
        return _snappy_decompress(payload)
    raise ValueError(f"unknown block compression type {ctype}")


def _block_entries(payload: bytes):
    """Yield (key, value) of a decompressed block (skips restart array)."""
    if len(payload) < 8:
        return
    restarts = struct.unpack("<I", payload[-4:])[0]
    end = len(payload) - 4 - 4 * restarts
    if end < 0:
        return
    pos, last = 0, b""
    while pos < end:
        sh, pos = _varint(payload, pos)
        ns, pos = _varint(payload, pos)
        vl, pos = _varint(payload, pos)
        key = last[:sh] + payload[pos:pos + ns]
        pos += ns
        val = payload[pos:pos + vl]
        pos += vl
        last = key
        yield key, val


def _split_ikey(key: bytes):
    """Internal key -> (user_key, sequence, type)."""
    if len(key) < 8:
        return key, 0, K_TYPE_VALUE
    footer = struct.unpack("<Q", key[-8:])[0]
    return key[:-8], footer >> 8, footer & 0xFF


def table_lookup(path: Path, wanted: set):
    """Look up select user keys in a .ldb SSTable without decompressing
    every block - the index says which data block can hold each key.

    Returns (records, max_seq): records is {key: [(seq, itype, value)]},
    max_seq is the highest sequence seen in the index keys.
    """
    records, max_seq = {}, 0
    data = path.read_bytes()
    if len(data) < 48:
        return records, max_seq
    footer = data[-48:]
    if struct.unpack("<Q", footer[40:])[0] != TABLE_MAGIC:
        return records, max_seq
    p = 0
    _, p = _varint(footer, p)          # metaindex handle: offset
    _, p = _varint(footer, p)          # metaindex handle: size
    io, p = _varint(footer, p)         # index handle: offset
    isize, p = _varint(footer, p)      # index handle: size
    index = _read_block(data, io, isize)
    entries = list(_block_entries(index))
    prev_uk = None
    for k, v in entries:
        uk, seq, _t = _split_ikey(k)
        # skip LevelDB's kMaxSequenceNumber sentinel keys (2^56-1)
        if seq < (1 << 56) - 1:
            max_seq = max(max_seq, seq)
        covers = [w for w in wanted
                  if (prev_uk is None or prev_uk < w) and uk >= w]
        if covers:
            bo, q = _varint(v, 0)
            bs, q = _varint(v, q)
            try:
                blk = _read_block(data, bo, bs)
            except ValueError:
                blk = b""
            for key, val in _block_entries(blk):
                u, s, t = _split_ikey(key)
                if u in wanted:
                    records.setdefault(u, []).append(
                        (s, t, None if t == K_TYPE_DELETION else val))
        prev_uk = uk
    return records, max_seq


def _manifest_edits(path: Path):
    """Yield (field, value) pairs of every VersionEdit in a MANIFEST."""
    data = path.read_bytes()
    for _b, _o, rtype, length, pay in iter_log_records(data):
        payload = data[pay:pay + length]
        if rtype != 1:
            continue
        i = 0
        try:
            while i < len(payload):
                field, i = _varint(payload, i)
                if field in (2, 3, 4, 9):
                    # log_number / next_file_number / last_sequence /
                    # prev_log_number
                    v, i = _varint(payload, i)
                    yield field, v
                elif field == 1:                       # comparator name
                    n, i = _varint(payload, i)
                    i += n
                elif field == 5:                       # compact pointer
                    n, i = _varint(payload, i)
                    i += n
                    _, i = _varint(payload, i)
                elif field == 6:                       # deleted file
                    _, i = _varint(payload, i)
                    _, i = _varint(payload, i)
                elif field == 7:                       # new file
                    _, i = _varint(payload, i)
                    _, i = _varint(payload, i)
                    _, i = _varint(payload, i)
                    n, i = _varint(payload, i)
                    i += n
                    n, i = _varint(payload, i)
                    i += n
                else:
                    break
        except ValueError:
            break


def manifest_info(d: Path):
    """(last_sequence, log_number) from the CURRENT MANIFEST, or (None, None)."""
    cur = d / "CURRENT"
    try:
        name = cur.read_text().strip()
    except OSError:
        return None, None
    mf = d / name
    if not mf.exists():
        return None, None
    last_seq = log_num = None
    for field, v in _manifest_edits(mf):
        if field == 4:
            last_seq = v
        elif field == 2:
            log_num = v
    return last_seq, log_num


def iter_log_batches(data: bytes):
    """Yield (seq, [(tag, key, value), ...]) for every WriteBatch in a log.

    tag 1 = put, tag 2 = delete (value None), tag 3 = log data.
    """
    for _b, _o, rtype, length, pay in iter_log_records(data):
        payload = data[pay:pay + length]
        if rtype != 1 or len(payload) < 12:
            continue
        seq, count = struct.unpack("<QI", payload[:12])
        i = 12
        entries = []
        for _ in range(count):
            if i >= len(payload):
                entries = []
                break
            tag = payload[i]
            i += 1
            try:
                if tag in (1, 2):
                    kl, i = _varint(payload, i)
                    k = payload[i:i + kl]
                    i += kl
                    vl, i = _varint(payload, i)
                    v = payload[i:i + vl]
                    i += vl
                    entries.append((tag, k, v if tag == 1 else None))
                elif tag == 3:
                    kl, i = _varint(payload, i)
                    i += kl
                    entries.append((tag, b"", None))
                else:
                    entries = []
                    break
            except ValueError:
                entries = []
                break
        if entries:
            yield seq, entries


def scan_theme_records(d: Path, keys=(b"theme", b"syncSettings")):
    """Locate select keys in one LevelDB directory (.log files + .ldb).

    Returns dict: theme = [{file, seq, value, in}], sync_settings,
    max_seq, manifest_last_sequence, manifest_log_number, errors.
    """
    wanted = set(keys)
    res = {"theme": [], "sync_settings": None, "max_seq": 0,
           "manifest_last_sequence": None, "manifest_log_number": None,
           "errors": []}
    last_seq, log_num = manifest_info(d)
    res["manifest_last_sequence"] = last_seq
    res["manifest_log_number"] = log_num
    if last_seq:
        res["max_seq"] = max(res["max_seq"], last_seq)
    for log in sorted(d.glob("*.log")):
        try:
            data = log.read_bytes()
        except OSError as e:
            res["errors"].append(f"{log.name}: {e}")
            continue
        for seq, entries in iter_log_batches(data):
            res["max_seq"] = max(res["max_seq"],
                                 seq + max(len(entries) - 1, 0))
            for idx, (tag, k, v) in enumerate(entries):
                if k not in wanted:
                    continue
                if k == b"syncSettings":
                    res["sync_settings"] = v
                elif tag in (1, 2):
                    res["theme"].append({"file": log, "seq": seq + idx,
                                         "value": v, "in": "log"})
    for tbl in sorted(d.glob("*.ldb")):
        try:
            records, mseq = table_lookup(tbl, wanted)
        except Exception as e:            # unreadable table: report, keep going
            res["errors"].append(f"{tbl.name}: {e}")
            continue
        res["max_seq"] = max(res["max_seq"], mseq)
        for u, lst in records.items():
            if u == b"syncSettings":
                res["sync_settings"] = lst[-1][2]
            elif u == b"theme":
                for seq, itype, val in lst:
                    res["theme"].append({"file": tbl, "seq": seq,
                                         "value": val, "in": "table"})
    return res


def effective_theme(scan):
    """The theme record chromium would actually load (highest sequence)."""
    recs = scan["theme"]
    if not recs:
        return None
    return max(recs, key=lambda r: r["seq"])


def current_log_file(d: Path, manifest_log_number):
    """The .log LevelDB will append to after recovery (newest eligible one)."""
    logs = sorted(d.glob("*.log"),
                  key=lambda p: p.name)
    if not logs:
        return None
    if manifest_log_number is not None:
        eligible = [l for l in logs
                    if int(l.name.split(".")[0]) >= manifest_log_number]
        if not eligible:
            return None
        return eligible[-1]
    return logs[-1]


def append_theme_record(log: Path, value: bytes, new_seq: int) -> int:
    """Append a standalone WriteBatch(put key='theme') to a LevelDB .log.

    The record gets `new_seq`, which is higher than every sequence already
    persisted (including copies inside .ldb SSTables), so on the next
    chromium start LevelDB replays it into the memtable and it wins over the
    flushed copy. Only bytes are appended - existing data is never rewritten,
    so a failure here cannot corrupt what is already on disk.
    """
    payload = struct.pack("<QI", new_seq, 1)
    payload += b"\x01" + _put_varint(len(b"theme")) + b"theme"
    payload += _put_varint(len(value)) + value
    rec = struct.pack("<IHB", record_checksum(K_TYPE_VALUE, payload),
                      len(payload), K_TYPE_VALUE) + payload
    size = log.stat().st_size
    rem = BLOCK_SIZE - (size % BLOCK_SIZE)
    with open(log, "ab") as f:
        if len(rec) > rem:
            # zero-fill to the next 32KiB block: log::Reader drops a
            # kZeroType/length=0 header and resumes at the next block, which
            # is exactly where our record starts.
            f.write(b"\x00" * rem)
        f.write(rec)
    return len(rec)


# --------------------------------------------------------------------------
# chromium state helpers
# --------------------------------------------------------------------------

def chromium_running() -> bool:
    try:
        r = subprocess.run(["pgrep", "-x", "chromium"],
                           capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return True
        r = subprocess.run(["pgrep", "-f", "/usr/lib/chromium/chromium"],
                           capture_output=True, text=True)
        return r.returncode == 0 and bool(r.stdout.strip())
    except FileNotFoundError:
        return False


def ext_settings_dirs(profile=DEFAULT_PROFILE, data_dir=None):
    base = Path(data_dir or Path.home() / ".config/chromium" / profile)
    return {
        "local": base / "Local Extension Settings" / EXT_ID,
        "sync": base / "Sync Extension Settings" / EXT_ID,
    }


# --------------------------------------------------------------------------
# live method: minimal CDP client on stdlib sockets (no extra packages)
# --------------------------------------------------------------------------

class CDPError(RuntimeError):
    pass


def _ws_handshake(sock: socket.socket, host: str, port: int, path: str):
    key = base64.b64encode(os.urandom(16)).decode()
    req = (f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\n"
           f"Upgrade: websocket\r\nConnection: Upgrade\r\n"
           f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n")
    sock.sendall(req.encode())
    resp = b""
    while b"\r\n\r\n" not in resp:
        chunk = sock.recv(4096)
        if not chunk:
            raise CDPError("websocket handshake: connection closed")
        resp += chunk
    head = resp.split(b"\r\n\r\n", 1)[0].decode("latin1")
    if " 101 " not in head.splitlines()[0]:
        raise CDPError(f"websocket handshake failed: {head.splitlines()[0]}")
    accept = hashlib.sha1(
        (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()
    if base64.b64encode(accept).decode() not in head:
        raise CDPError("websocket handshake: bad accept key")


def _ws_send_text(sock: socket.socket, text: str):
    raw = text.encode("utf-8")
    mask = os.urandom(4)
    hdr = bytearray([0x81])
    if len(raw) < 126:
        hdr.append(0x80 | len(raw))
    elif len(raw) < 65536:
        hdr.append(0x80 | 126)
        hdr += struct.pack("!H", len(raw))
    else:
        hdr.append(0x80 | 127)
        hdr += struct.pack("!Q", len(raw))
    hdr += mask
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(raw))
    sock.sendall(bytes(hdr) + masked)


def _ws_recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise CDPError("websocket: connection closed mid-frame")
        buf += chunk
    return buf


def _ws_recv_text(sock: socket.socket) -> str:
    fragments = []
    while True:
        h = _ws_recv_exact(sock, 2)
        fin, opcode = h[0] >> 7, h[0] & 0x0F
        masked, ln = (h[1] >> 7), h[1] & 0x7F
        if ln == 126:
            ln = struct.unpack("!H", _ws_recv_exact(sock, 2))[0]
        elif ln == 127:
            ln = struct.unpack("!Q", _ws_recv_exact(sock, 8))[0]
        if masked:
            mask = _ws_recv_exact(sock, 4)
        payload = _ws_recv_exact(sock, ln) if ln else b""
        if masked:
            payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        if opcode == 0x8:
            raise CDPError("websocket closed by browser")
        if opcode == 0x1 or opcode == 0x0:
            fragments.append(payload)
            if fin:
                return b"".join(fragments).decode("utf-8")
        elif opcode == 0x9:  # ping -> pong
            sock.sendall(b"\x8a\x00")
        # ignore continuation/control otherwise


def cdp_targets(port: int):
    url = f"http://127.0.0.1:{port}/json"
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        raise CDPError(
            f"cannot reach chromium debug port {port} ({e}). "
            "Start chromium with:  chromium --remote-debugging-port=9222") from e


def cdp_evaluate(ws_url: str, expression: str, timeout=15):
    from urllib.parse import urlparse
    u = urlparse(ws_url)
    host, port, path = u.hostname or "127.0.0.1", u.port or 80, u.path or "/"
    if u.query:
        path += "?" + u.query
    sock = socket.create_connection((host, port), timeout=timeout)
    try:
        sock.settimeout(timeout)
        _ws_handshake(sock, host, port, path)
        _ws_send_text(sock, json.dumps(
            {"id": 1, "method": "Runtime.evaluate",
             "params": {"expression": expression, "awaitPromise": True,
                        "returnByValue": True}}))
        while True:
            msg = json.loads(_ws_recv_text(sock))
            if msg.get("id") == 1:
                if "error" in msg:
                    raise CDPError(f"CDP error: {msg['error']}")
                res = msg.get("result", {}).get("result", {})
                if res.get("subtype") == "error":
                    raise CDPError(
                        f"JS error: {res.get('description', res)}")
                return res.get("value")
    finally:
        sock.close()


LIVE_JS = """(async () => {
  const get = (k) => new Promise(r => chrome.storage.local.get(k, r));
  const set = (o) => new Promise(r => chrome.storage.local.set(o, r));
  const cur = (await get('theme')).theme;
  if (!cur) return JSON.stringify({error: 'no theme key in storage'});
  const next = Object.assign({}, cur, __PATCH__);
  await set({theme: next});
  const verify = (await get('theme')).theme;
  return JSON.stringify({bg: verify.darkSchemeBackgroundColor,
                         text: verify.darkSchemeTextColor,
                         engine: verify.engine, mode: verify.mode});
})()"""


def find_extension_target(targets):
    cands = [t for t in targets if EXT_ID in (t.get("url") or "")]
    if not cands:
        return None
    for t in cands:  # prefer background service worker
        if t.get("type") in ("service_worker", "background_page"):
            return t
    return cands[0]


def apply_live(req: dict, port: int, dry_run=False):
    targets = cdp_targets(port)
    tgt = find_extension_target(targets)
    if not tgt:
        raise CDPError(
            f"Dark Reader target ({EXT_ID}) not found among "
            f"{len(targets)} debugger targets. Is the extension installed "
            "and enabled in this profile?")
    expr = LIVE_JS.replace("__PATCH__", json.dumps(req))
    if dry_run:
        return {"dry_run": True,
                "target": {k: tgt.get(k) for k in ("type", "url", "title")}}
    raw = cdp_evaluate(tgt["webSocketDebuggerUrl"], expr)
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return {"raw": raw}


def _backup_log(log: Path, entry: dict, do_backup: bool):
    if not do_backup:
        return
    bak = log.with_suffix(log.suffix + ".bak")
    if not bak.exists():
        shutil.copy2(log, bak)
        entry["backup"] = str(bak)


def _patch_log_in_place(log: Path, req, dry_run, do_backup):
    """Same-length patch of theme records already inside a .log file."""
    ok, bad = verify_log_checksums(log)
    if bad and ok == 0:
        raise RuntimeError(
            f"{log}: CRC self-check failed ({bad} bad, {ok} ok) -- "
            "refusing to patch (would corrupt). Use --method live.")
    raw = log.read_bytes()
    new_data, touched, ranges, missing = patch_theme_record_colors(raw, req)
    entry = {"file": str(log), "crc_ok": ok, "crc_bad": bad,
             "theme_records": touched}
    if missing:
        entry["missing"] = [FIELD_SHORT[k] for k in sorted(missing)]
    if touched == 0:
        entry["status"] = (
            "no patchable theme JSON in this log"
            + (f" (no {', '.join(entry['missing'])} field found)"
               if missing else "")
            + "; append an override record instead")
        entry["fallback_append"] = True
        return entry
    if dry_run:
        entry["status"] = (f"would patch {touched} record(s) -> "
                           f"{fmt_fields(req)}")
        return entry
    _backup_log(log, entry, do_backup)
    log.write_bytes(new_data)
    fixed = repair_ranges(log, ranges)
    ok2, bad2 = verify_log_checksums(log)
    entry["repaired_headers"] = fixed
    entry["verify_after"] = {"ok": ok2, "bad": bad2}
    entry["status"] = (f"patched {touched} record(s) -> {fmt_fields(req)}"
                       if bad2 == 0 else "PATCHED BUT CRC STILL BAD")
    return entry


def _append_override(d: Path, eff, scan, req, dry_run, do_backup):
    """The winning `theme` record lives in an .ldb SSTable (which offline
    patching cannot edit): append a newer record to the current .log."""
    logf = current_log_file(d, scan.get("manifest_log_number"))
    if logf is None:
        return {"file": str(d),
                "status": f"cannot append override: no writable .log in "
                          f"{d} (winner: {eff['file'].name} seq={eff['seq']})"
                          " -- use --method live"}
    new_value, missing = _patch_theme_json(eff["value"], req)
    if missing:
        return {"file": str(d),
                "status": f"cannot append override: stored theme JSON in "
                          f"{eff['file'].name} has no patchable "
                          f"{', '.join(FIELD_SHORT[k] for k in missing)} "
                          "field(s) -- use --method live"}
    new_seq = int(scan.get("max_seq") or 0) + 1
    entry = {"file": str(logf)}
    old = f"{eff['file'].name} seq={eff['seq']}"
    if dry_run:
        entry["status"] = (f"would append override theme record "
                           f"(seq={new_seq}) -> {fmt_fields(req)}; winning "
                           f"value is in {old} (.ldb SSTables cannot be "
                           f"edited in place)")
        return entry
    _backup_log(logf, entry, do_backup)
    nbytes = append_theme_record(logf, new_value, new_seq)
    entry["status"] = (f"appended override theme record ({nbytes} bytes, "
                       f"seq={new_seq}) -> {fmt_fields(req)}; stale value was "
                       f"in {old} (offline patch cannot edit .ldb SSTables)")
    ok, bad = verify_log_checksums(logf)
    entry["verify_after"] = {"ok": ok, "bad": bad}
    if bad:
        entry["status"] += " -- LOG CRC CHECK FAILED"
    return entry


def apply_offline(req: dict, profile=DEFAULT_PROFILE, data_dir=None,
                  dry_run=False, do_backup=True):
    if not dry_run and chromium_running():
        raise RuntimeError(
            "chromium is RUNNING. Offline patching while it runs will be "
            "ignored/overwritten and can corrupt the profile.\n"
            "Close chromium fully (check `pgrep -a chromium`) and retry, "
            "or use --method live with --remote-debugging-port.")
    dirs = ext_settings_dirs(profile, data_dir)
    present = {k: d for k, d in dirs.items() if d.is_dir()}
    if not present:
        raise RuntimeError(
            f"no extension settings dir under {dirs['local']} "
            f"(profile={profile!r}). Is Dark Reader installed in this "
            "chromium profile?")

    scans = {k: scan_theme_records(d) for k, d in present.items()}
    # Dark Reader only reads storage.sync when storage.local holds
    # syncSettings=true; otherwise storage.local is authoritative.
    sync_on = scans.get("local", {}).get("sync_settings") == b"true"
    required = "sync" if sync_on else "local"

    report = {"files": [], "verify": [], "warnings": [], "required": required,
              "ldb_warning": False}
    for kind, d in present.items():
        scan = scans[kind]
        eff = effective_theme(scan)
        if eff is None:
            report["files"].append(
                {"file": str(d),
                 "status": "no theme record in logs or SSTables "
                           "(nothing to patch)"})
            continue
        src = f"{eff['file'].name} seq={eff['seq']} ({eff['in']})"
        if eff["value"] is None:
            report["files"].append(
                {"file": str(d),
                 "status": f"theme record is DELETED in {src}; nothing "
                           f"to patch"})
            continue
        have = fields_of(eff["value"], req)
        if have == req:
            eff_mode = field_of(eff["value"], MODE_KEY)
            mode_note = (f", mode={MODE_NAME.get(eff_mode, eff_mode)}"
                         if MODE_KEY not in have and eff_mode is not None
                         else "")
            report["files"].append(
                {"file": str(d),
                 "status": f"already up to date ({fmt_fields(have)}"
                           f"{mode_note} in {src})"})
            continue
        if eff["in"] == "log":
            entry = _patch_log_in_place(eff["file"], req, dry_run, do_backup)
            report["files"].append(entry)
            if entry.pop("fallback_append", False):
                report["files"].append(
                    _append_override(d, eff, scan, req, dry_run, do_backup))
        else:
            report["files"].append(
                _append_override(d, eff, scan, req, dry_run, do_backup))

    if dry_run:
        report["ldb_warning"] = any(d.glob("*.ldb") for d in present.values())
        return report

    # Re-read the store and check that the value chromium will load is the
    # one we wanted - this is what catches "patch silently did nothing".
    for kind, d in present.items():
        eff = effective_theme(scan_theme_records(d))
        got = fields_of(eff["value"], req) if eff and eff["value"] else None
        if got and all(v is not None for v in got.values()):
            eff_mode = field_of(eff["value"], MODE_KEY)
            report["verify"].append(
                f"{kind}: effective theme = {fmt_fields(got)}"
                + (f" (mode={MODE_NAME.get(eff_mode, eff_mode)})"
                   if eff_mode is not None else "")
                + f" (from {eff['file'].name} seq={eff['seq']})")
        else:
            report["verify"].append(
                f"{kind}: effective theme = MISSING "
                f"(from {eff['file'].name if eff else 'nowhere'})")
        if kind == required and got != req:
            held = (f"{eff['file'].name} seq={eff['seq']}" if eff else "nowhere")
            if eff and eff["value"] is None:
                detail = f"the theme record is DELETED in {held}"
            elif got and all(v is not None for v in got.values()):
                detail = f"it is {fmt_fields(got)}, held in {held}"
            else:
                detail = f"no theme record exists (last seen: {held})"
            raise RuntimeError(
                f"Dark Reader's effective theme does not match "
                f"{fmt_fields(req)}: {detail}.\nThe offline patch could not "
                "override it (a compressed .ldb SSTable may win).\n"
                "Fix: run again, or use --method live (start chromium with "
                "--remote-debugging-port=9222).")
        if kind == required:
            # Colours written for a scheme that is not the active one have no
            # effect - say so instead of silently doing nothing visible.
            eff_mode = field_of(eff["value"], MODE_KEY) if eff and \
                eff["value"] else None
            light_only = (LBG_KEY in req or LTX_KEY in req) and \
                BG_KEY not in req and MODE_KEY not in req
            if light_only and eff_mode == 1:
                report["warnings"].append(
                    "light colours were written but Dark Reader is still in "
                    "DARK mode (mode=1), so they have NO effect - rerun with "
                    "--mode light (which also needs --light-text)")
            elif (BG_KEY in req and TX_KEY in req) and MODE_KEY not in req \
                    and eff_mode == 0:
                report["warnings"].append(
                    "dark colours were written but Dark Reader is in LIGHT "
                    "mode (mode=0), so they have NO effect - rerun with "
                    "--mode dark")
    return report


# --------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------

def build_parser():
    ap = argparse.ArgumentParser(
        description="Set Dark Reader background/text colors in chromium.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""NOTES / ONE-TIME SETUP
  live method (recommended): chromium must expose --remote-debugging-port.
    1. Close chromium completely.
    2. Launch once as:  chromium --remote-debugging-port=9222
       (for Hyprland autostart add the flag to your exec-once chromium line,
       e.g.  hl.exec_cmd("chromium --remote-debugging-port=9222 &") )
    3. Then run:  %(prog)s --bg "#111c18" --text "#c1c497"
    No extra packages needed (CDP client is stdlib sockets).

  offline method: no flags or packages, but chromium must be CLOSED:
       %(prog)s --method offline --bg "#111c18" --text "#c1c497"

  scheme lookup: --scheme reads your color-schemes.drconf DARK section:
       %(prog)s --scheme "Osaka Jade Bamboo"   # uses #111c18 / #c1c497
       %(prog)s --list                          # show known scheme names

  dark vs light scheme (--mode):
    Dark Reader keeps TWO colour pairs in its `theme` record and `mode`
    decides which one the page gets:  mode=1 dark -> darkScheme*,
    mode=0 light -> lightScheme*. Colours alone never switch the mode, so
    a light palette must be written together with the mode that uses it:
       %(prog)s --mode light --light-bg "#dfe4c4" --light-text "#1c2d28"
       %(prog)s --mode dark  --bg "$BG" --text "$FG"
    Omit --mode to only retune colours; the script warns you afterwards if
    the scheme you wrote is not the active one.
""")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--bg", help="dark background hex, e.g. #111c18")
    src.add_argument("--scheme",
                     help='scheme name from --list (e.g. "Gruvbox")')
    ap.add_argument("--text", help="dark text hex, e.g. #c1c497")
    ap.add_argument("--light-bg", default=None, help="light bg hex")
    ap.add_argument("--light-text", default=None, help="light text hex")
    ap.add_argument("--mode", choices=["dark", "light"], default=None,
                    help="which colour scheme Dark Reader uses: dark writes "
                         "theme.mode=1 (needs --bg/--text), light writes "
                         "theme.mode=0 (needs --light-bg/--light-text). "
                         "Omit to leave the current mode untouched.")
    ap.add_argument("--list", action="store_true",
                    help="list schemes in the .drconf and exit")
    ap.add_argument("--drconf", default=str(Path.home() /
                    "Documents/color-schemes.drconf"),
                    help="path to color-schemes.drconf")
    ap.add_argument("--method", choices=["auto", "live", "offline"],
                    default="auto",
                    help="auto tries live, falls back to offline "
                         "(default: auto)")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT,
                    help="remote-debugging port (default 9222)")
    ap.add_argument("--profile", default=DEFAULT_PROFILE,
                    help="chromium profile dir (default Default)")
    ap.add_argument("--chrome-data", default=None,
                    help="override chromium config dir "
                         "(default ~/.config/chromium/<profile>)")
    ap.add_argument("--dry-run", action="store_true",
                    help="show what would change, write nothing")
    ap.add_argument("--no-backup", action="store_true",
                    help="offline: skip .bak backup")
    return ap


def main(argv=None):
    ap = build_parser()
    a = ap.parse_args(argv)

    if a.list:
        schemes = load_schemes(Path(a.drconf))
        if not schemes:
            print(f"no schemes found in {a.drconf}")
            return 1
        for name, s in schemes.items():
            print(f"{name}: dark bg={s['dark_bg']} text={s['dark_text']}", end="")
            if s["light_bg"]:
                print(f" | light bg={s['light_bg']} text={s['light_text']}",
                      end="")
            print()
        return 0

    if a.scheme:
        schemes = load_schemes(Path(a.drconf))
        if a.scheme not in schemes:
            print(f'unknown scheme {a.scheme!r}. Use --list. '
                  f'File: {a.drconf}', file=sys.stderr)
            return 2
        s = schemes[a.scheme]
        bg, text = s["dark_bg"], s["dark_text"]
        if not bg or not text:
            print(f"scheme {a.scheme!r} has no DARK colors", file=sys.stderr)
            return 2
        light_bg = light_text = None     # a .drconf scheme only has dark cols
    else:
        bg, text = a.bg, a.text
        light_bg, light_text = a.light_bg, a.light_text

    # --mode must come with the colours of the scheme it activates: telling
    # Dark Reader to go light while leaving lightScheme* at its defaults is
    # never what the user meant.
    mode = MODE_VALUE[a.mode] if a.mode else None
    if mode == MODE_VALUE["light"] and not (light_bg and light_text):
        ap.error("--mode light requires --light-bg and --light-text")
    if mode == MODE_VALUE["dark"] and not (bg and text):
        ap.error("--mode dark requires --bg and --text")

    try:
        bg = normalize_hex(bg) if bg else None
        text = normalize_hex(text) if text else None
        light_bg = normalize_hex(light_bg) if light_bg else None
        light_text = normalize_hex(light_text) if light_text else None
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    req = requested_fields(bg, text, light_bg, light_text, mode)
    if not req:
        ap.error("nothing to do: pass --bg/--text, --light-bg/--light-text, "
                 "--scheme, or --mode")

    method = a.method
    if method == "auto":
        try:
            cdp_targets(a.port)
            method = "live"
        except CDPError:
            method = "offline"
            print(f"(debug port {a.port} unreachable -> using offline "
                  f"method; close chromium first)", file=sys.stderr)

    try:
        if method == "live":
            res = apply_live(req, a.port, dry_run=a.dry_run)
            if a.dry_run:
                print(f"[dry-run] would set via {res['target']}: "
                      f"{fmt_fields(req)}")
            else:
                print(f"Dark Reader updated live: {fmt_fields(req)} -> {res}")
                print("Open tabs re-theme automatically; if a tab looks stale, "
                      "reload it.")
                eff_mode = res.get("mode") if isinstance(res, dict) else None
                if eff_mode == 1:
                    print("NOTE: Dark Reader is in DARK mode, so the dark* "
                          "colours are the ones in use.", file=sys.stderr)
                elif eff_mode == 0:
                    print("NOTE: Dark Reader is in LIGHT mode, so the "
                          "light* colours are the ones in use.",
                          file=sys.stderr)
        else:
            rep = apply_offline(req, a.profile, a.chrome_data,
                                dry_run=a.dry_run,
                                do_backup=not a.no_backup)
            for f in rep["files"]:
                print(f"{f['file']}: {f['status']}"
                      + (f"  [backup {f['backup']}]"
                         if f.get("backup") else ""))
            for line in rep.get("verify", []):
                print(f"verify: {line}")
            for line in rep.get("warnings", []):
                print(f"warning: {line}", file=sys.stderr)
            if rep.get("ldb_warning"):
                print("NOTE: *.ldb SSTable files present; --dry-run cannot "
                      "verify which value wins. Run without --dry-run to "
                      "confirm (or use --method live).", file=sys.stderr)
            if not a.dry_run:
                print("Done. Start chromium to see the new colors.")
    except (CDPError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
