#!/usr/bin/env python3
"""G11 hardening: validate soundwork/tad/build/* against the committed
reconstruction oracle (soundwork/tad/project/reconstruction_oracle.json).

This is a fast, no-compiler-required sanity check -- it does not recompile
anything (see rebuild.py --check for that). It exists so a reviewer or a
future session can confirm the shipped audio blob still matches its own
documented provenance (hashes, song/SFX ID ordering, TAD IO version)
without needing tad-compiler.exe installed at all.

Usage:
    python soundwork/tad/verify_project.py
"""
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORACLE_PATH = HERE / "project" / "reconstruction_oracle.json"
VENDOR_DRIVER_INC = HERE / "vendor" / "tad-driver.inc"
ENUMS_INC = HERE / "build" / "audio-enums.inc"


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ok = True

    if not ORACLE_PATH.exists():
        print(f"FAIL: oracle manifest missing: {ORACLE_PATH}")
        return 1
    oracle = json.loads(ORACLE_PATH.read_text())

    # 1. File hashes
    for rel_path, expected_hash in oracle["hashes"].items():
        p = HERE / rel_path
        if not p.exists():
            print(f"FAIL: {rel_path} does not exist")
            ok = False
            continue
        actual = sha256_of(p)
        if actual != expected_hash:
            print(f"FAIL: {rel_path} hash mismatch\n  expected {expected_hash}\n  actual   {actual}")
            ok = False
        else:
            print(f"OK: {rel_path} hash matches ({actual[:12]}...)")

    # 2. TAD_IO_VERSION
    driver_text = VENDOR_DRIVER_INC.read_text()
    m = re.search(r"TAD_IO_VERSION\s*=\s*(\d+)", driver_text)
    if not m:
        print(f"FAIL: could not find TAD_IO_VERSION in {VENDOR_DRIVER_INC}")
        ok = False
    else:
        real_version = int(m.group(1))
        expected_version = oracle["tad_io_version"]
        if real_version != expected_version:
            print(f"FAIL: TAD_IO_VERSION drift -- oracle says {expected_version}, vendor driver says {real_version}")
            ok = False
        else:
            print(f"OK: TAD_IO_VERSION matches ({real_version})")

    # 3. Song/SFX ID ordering (audio-enums.inc)
    enums_text = ENUMS_INC.read_text()
    song_m = re.search(r"\.enum\s+Song\b(.*?)\.endenum", enums_text, re.S)
    sfx_m = re.search(r"\.enum\s+SFX\b(.*?)\.endenum", enums_text, re.S)
    if not song_m or not sfx_m:
        print(f"FAIL: could not parse Song/SFX enums from {ENUMS_INC}")
        ok = False
    else:
        real_songs = dict(re.findall(r"(\w+)\s*=\s*(\d+)", song_m.group(1)))
        real_sfx = dict(re.findall(r"(\w+)\s*=\s*(\d+)", sfx_m.group(1)))
        for name, expected_id in oracle["song_ids"].items():
            actual_id = real_songs.get(name)
            if actual_id is None or int(actual_id) != expected_id:
                print(f"FAIL: song id drift for {name} -- oracle {expected_id}, real {actual_id}")
                ok = False
        for name, expected_id in oracle["sfx_ids"].items():
            actual_id = real_sfx.get(name)
            if actual_id is None or int(actual_id) != expected_id:
                print(f"FAIL: sfx id drift for {name} -- oracle {expected_id}, real {actual_id}")
                ok = False
        if ok:
            print(f"OK: song ids {real_songs} match oracle")
            print(f"OK: sfx ids {real_sfx} match oracle")

    if ok:
        print("\nVERIFY_PROJECT: PASS")
        return 0
    print("\nVERIFY_PROJECT: FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
