# -*- coding: utf-8 -*-
"""
otzaria_fetch.py
------------------
Pulls individual book files out of the Otzaria library zip
(github.com/zevisvei/otzaria-library, released as one ~1.3GB
otzaria_latest.zip) WITHOUT downloading the whole archive: it range-fetches
just the end-of-central-directory record, then the central directory, to
list every entry's name/offset/size, and then range-fetches + inflates only
the one entry asked for.

Usage:
    python3 otzaria_fetch.py list [substring]        # search entry names
    python3 otzaria_fetch.py get "<exact entry name>" [out_file]

The Otzaria library aggregates Sefaria + Dicta texts (Tanakh, Mishnah,
Tosefta, Talmud Bavli/Yerushalmi, Rishonim, Acharonim, Kabbalah, ...) as
plain text/HTML-tagged files, one per book/commentary. See its README:
https://github.com/Sivan22/otzaria
"""

import struct
import sys
import zlib

import requests

RELEASE_URL = "https://github.com/Sivan22/otzaria-library/releases/download/latest/otzaria_latest.zip"

_session = requests.Session()
_final_url = None
_entries = None  # name -> {method, comp_size, local_offset}


def _resolve_final_url():
    global _final_url
    if _final_url is None:
        r = _session.head(RELEASE_URL, allow_redirects=True, timeout=60)
        r.raise_for_status()
        _final_url = r.url
    return _final_url


def _ranged_get(start, end):
    url = _resolve_final_url()
    r = _session.get(url, headers={"Range": f"bytes={start}-{end}"}, timeout=180)
    r.raise_for_status()
    return r.content


def _load_central_directory():
    """Fetch just the EOCD + central directory (a couple MB) to list all
    entries, without downloading the archive's actual (gigabyte-scale)
    file data."""
    global _entries
    if _entries is not None:
        return _entries

    url = _resolve_final_url()
    head = _session.head(url, timeout=60)
    size = int(head.headers["Content-Length"])

    tail_len = 65557 + 22
    tail = _ranged_get(max(0, size - tail_len), size - 1)
    idx = tail.rfind(b"PK\x05\x06")
    if idx == -1:
        raise RuntimeError("EOCD signature not found - zip format assumption broken")
    (_, _, _, _, _, cd_size, cd_offset, _) = struct.unpack("<IHHHHIIH", tail[idx:idx + 22])

    cd_data = _ranged_get(cd_offset, cd_offset + cd_size - 1)

    entries = {}
    pos = 0
    while pos < len(cd_data):
        if cd_data[pos:pos + 4] != b"PK\x01\x02":
            break
        fields = struct.unpack("<IHHHHHHIIIHHHHHII", cd_data[pos:pos + 46])
        method, comp_size, fname_len, extra_len, comment_len, local_offset = (
            fields[4], fields[8], fields[10], fields[11], fields[12], fields[16],
        )
        name = cd_data[pos + 46:pos + 46 + fname_len].decode("utf-8", errors="replace")
        entries[name] = {"method": method, "comp_size": comp_size, "local_offset": local_offset}
        pos += 46 + fname_len + extra_len + comment_len

    _entries = entries
    return entries


def list_entries(substring=None):
    entries = _load_central_directory()
    names = sorted(entries)
    if substring:
        names = [n for n in names if substring in n]
    return names


def fetch_entry_text(name, encoding="utf-8"):
    entries = _load_central_directory()
    if name not in entries:
        raise KeyError(f"not found in Otzaria library: {name!r}")
    e = entries[name]

    header = _ranged_get(e["local_offset"], e["local_offset"] + 30 + 1024)
    if header[:4] != b"PK\x03\x04":
        raise ValueError(f"bad local file header for {name!r}")
    fname_len, extra_len = struct.unpack("<HH", header[26:30])
    data_start = e["local_offset"] + 30 + fname_len + extra_len

    raw = _ranged_get(data_start, data_start + e["comp_size"] - 1)
    if e["method"] == 0:
        data = raw
    elif e["method"] == 8:
        data = zlib.decompress(raw, -15)
    else:
        raise ValueError(f"unsupported zip compression method {e['method']} for {name!r}")
    return data.decode(encoding, errors="replace")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "list":
        substring = sys.argv[2] if len(sys.argv) > 2 else None
        for name in list_entries(substring):
            print(name)
    elif cmd == "get":
        name = sys.argv[2]
        text = fetch_entry_text(name)
        if len(sys.argv) > 3:
            with open(sys.argv[3], "w", encoding="utf-8") as f:
                f.write(text)
            print(f"wrote {len(text)} chars to {sys.argv[3]}")
        else:
            print(text)
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
