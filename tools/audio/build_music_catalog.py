#!/usr/bin/env python3
"""Decode every shipped-reachable BOR music asset and build MSU-1 PCM.

The PAKs remain local source inputs. Output is generated under the selected
distribution directory and is intentionally not committed; the catalog records
source, decoded, and MSU PCM hashes for reproducibility.
"""
from __future__ import annotations

import hashlib
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "bor_converter"))
from pak_extract import extract  # noqa: E402
sys.path.insert(0, str(ROOT / "tools" / "audio"))
from convert_bor_music import convert  # noqa: E402
from decode_bor_music import decode_bor  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT / "distribution")
    ap.add_argument("--catalog", type=Path, default=ROOT / "build" / "audio_music_catalog.json")
    args = ap.parse_args()
    output = args.output
    catalog_path = args.catalog
    manifest = json.loads((ROOT / "tools/audio/audio_manifest.json").read_text(encoding="utf-8"))
    rows = []
    for family in manifest["families"]:
        pak = ROOT / family["pak"]
        for asset in family["assets"]:
            if asset["kind"] != "music" or asset.get("msu_track_id") is None:
                continue
            source = extract(str(pak), asset["source_path"])
            source_hash = hashlib.sha256(source).hexdigest()
            bor = output / f"track-{asset['msu_track_id']:02d}.bor"
            pcm = output / f"bor-{asset['msu_track_id']}.pcm"
            bor.parent.mkdir(parents=True, exist_ok=True)
            bor.write_bytes(source)
            header, decoded = decode_bor(source)
            loop_arguments = [r.get("loop_argument") for r in asset["references"]
                              if r.get("reachability") == "shipped-reachable"
                              and r.get("loop_argument") is not None]
            offsets = [int(value) for value in loop_arguments] or [0]
            if any(value < 0 for value in offsets):
                raise SystemExit(f"negative BOR loop offset: {asset['source_path']}")
            if len(set(offsets)) != 1:
                raise SystemExit(f"conflicting BOR loop offsets: {asset['source_path']}")
            offset = offsets[0]
            repeat = True  # level music() and boss music() call the engine with loop=1
            meta = convert(bor, pcm, repeat=repeat, bor_loop_offset_bytes=offset)
            if hashlib.sha256(bor.read_bytes()).hexdigest() != source_hash:
                raise SystemExit(f"source extraction drift: {asset['source_path']}")
            rows.append({"track_id": asset["msu_track_id"], "track_key": asset["track_key"],
                         "source_hash": source_hash, "decoded_pcm_hash": hashlib.sha256(decoded).hexdigest(),
                         "msu_pcm_hash": hashlib.sha256(pcm.read_bytes()).hexdigest(),
                         "source_rate_hz": header.frequency, "source_channels": header.channels,
                         "source_sample_count": len(decoded) // (2 * header.channels),
                         "msu_sample_count": meta["msu_sample_count"],
                         "duration_seconds": meta["duration_seconds"],
                         "authored_loop_directive": loop_arguments,
                         "original_bor_loop": {"kind": "encoded-byte-offset", "offset_bytes": offset},
                         "repeat": repeat,
                         "bor_loop_offset_bytes": meta["bor_loop_offset_bytes"],
                         "decoded_source_loop_frame": meta["source_loop_frame"],
                         "msu_loop_frame": meta["msu_loop_frame"],
                         "msu_pcm_path": f"distribution/bor-{asset['msu_track_id']}.pcm"})
            bor.unlink()
    rows.sort(key=lambda row: row["track_id"])
    catalog_path.write_text(json.dumps({"format": "MSU-1 PCM: MSU1 header + signed 16-bit LE stereo 44100 Hz", "tracks": rows}, indent=2) + "\n", encoding="utf-8")
    print(f"decoded {len(rows)} shipped-reachable tracks -> {catalog_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
