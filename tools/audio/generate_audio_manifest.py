#!/usr/bin/env python3
"""Generate the source-backed BOR/TMNT audio manifest.

The PAK files are the authority.  This scanner deliberately does not infer
meaning from filenames: only explicit ``sound``/``diesound`` and
``music``/``bossmusic`` directives become references.  The manifest also
lists unreferenced media so content coverage cannot silently shrink.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import struct
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "bor_converter"))
from pak_extract import read_entries, extract  # noqa: E402
sys.path.insert(0, str(ROOT / "tools" / "audio"))
from decode_bor_music import parse_header  # noqa: E402
from shipped_content import shipped_characters, shipped_levels  # noqa: E402
from engine_audio_semantics import ENGINE_GLOBAL_AUDIO, ENGINE_REVISION, ENGINE_SOURCE  # noqa: E402

SHIPPED_CHARACTERS = shipped_characters()

PAKS = [
    ("bor-original", ROOT / "Beats of Rage Original [v.3.0 Build 4086].pak"),
    ("tmnt", ROOT / "Teenage Mutant Ninja Turtles [v.3.0 Build 4153].pak"),
]
PAK_ALIASES = {
    ("tmnt", "DATA\\SOUNDS\\TURTLEDIE.WAV"): "DATA\\SOUNDS\\TURTLE~1.WAV",
}
SOUND_RE = re.compile(r"^\s*(sound|diesound)\s+(\S+)", re.I)
MUSIC_RE = re.compile(r"^\s*(music|bossmusic)\s+(\S+)(?:\s+([+-]?\d+))?(?:\s|$)", re.I)


def norm(value: str) -> str:
    return value.replace("/", "\\").upper()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def wav_metadata(data: bytes) -> dict:
    try:
        with wave.open(io.BytesIO(data)) as w:
            return {
                "container": "WAV", "codec": "PCM",
                "channels": w.getnchannels(), "sample_width_bytes": w.getsampwidth(),
                "sample_rate_hz": w.getframerate(), "sample_count": w.getnframes(),
                "duration_seconds": round(w.getnframes() / w.getframerate(), 9),
            }
    except wave.Error:
        # Some TMNT assets are WAVE_FORMAT_MPEG (tag 0x55), not PCM.  Retain
        # the source facts without pretending a PCM decoder measured them.
        if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
            raise
        pos = 12
        fmt = None
        data_bytes = None
        while pos + 8 <= len(data):
            tag, size = data[pos:pos + 4], struct.unpack_from("<I", data, pos + 4)[0]
            body = data[pos + 8:pos + 8 + size]
            pos += 8 + size + (size & 1)
            if tag == b"fmt " and len(body) >= 16:
                fmt = struct.unpack_from("<HHIIHH", body)
            elif tag == b"data":
                data_bytes = len(body)
        if fmt is None:
            raise
        codec, channels, rate, byte_rate, block_align, bits = fmt
        return {"container": "WAV", "codec_tag": f"0x{codec:04x}",
                "channels": channels, "sample_width_bytes": None,
                "sample_rate_hz": rate, "sample_count": None,
                "duration_seconds": None, "compressed_data_bytes": data_bytes,
                "byte_rate": byte_rate, "block_align": block_align, "bits_per_sample": bits}


def media_metadata(name: str, data: bytes) -> dict:
    suffix = Path(name).suffix.lower()
    if suffix == ".wav":
        return wav_metadata(data)
    if suffix == ".bor":
        header = parse_header(data)
        return {"container": "OpenBOR BOR ADPCM", "identifier": "BOR music",
                "version": f"0x{header.version:08x}", "artist": header.artist,
                "title": header.title, "sample_rate_hz": header.frequency,
                "channels": header.channels, "datastart": header.datastart,
                "encoded_bytes": len(data) - header.datastart}
    return {"container": suffix.lstrip(".").upper() or "unknown"}


def classify(asset: dict) -> str:
    if asset["kind"] == "missing-source":
        return "unknown-needs-source-research"
    if asset.get("packed_runtime"):
        return "implemented-and-gated"
    if asset["references"]:
        return "present-not-implemented"
    return "unused-by-shipped-content"


def scan_family(family: str, pak: Path) -> dict:
    if not pak.exists():
        raise SystemExit(f"missing source PAK: {pak}")
    entries = read_entries(str(pak))
    by_name = {norm(e.name): e for e in entries}
    assets = {}
    for e in entries:
        p = norm(e.name)
        if not p.startswith("DATA\\SOUNDS\\") and not p.startswith("DATA\\MUSIC\\"):
            continue
        suffix = Path(p).suffix.lower()
        kind = "sfx" if p.startswith("DATA\\SOUNDS\\") and suffix == ".wav" else \
            "music" if p.startswith("DATA\\MUSIC\\") and suffix == ".bor" else "other-audio"
        data = extract(str(pak), e.name)
        assets[p] = {
            "family": family,
            "kind": kind,
            "source_path": p,
            "source_filename": Path(p).name,
            "source_hash": sha256(data),
            "source_size_bytes": len(data),
            "format": media_metadata(p, data),
            "references": [],
            "converter_representation": None,
            "packed_runtime": None,
            "tad_sfx_id": 1 if family == "bor-original" and p == "DATA\\SOUNDS\\BEAT1.WAV" else None,
            "msu_track_id": None,
        }
    for e in entries:
        if not e.name.upper().endswith(".TXT"):
            continue
        text = extract(str(pak), e.name).decode("latin1")
        # TEST.TXT is a converter fixture, not a shipped stage in build_rom.py.
        if norm(e.name) == "DATA\\LEVELS\\TEST.TXT":
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            sound_match = SOUND_RE.match(line)
            music_match = MUSIC_RE.match(line)
            if sound_match:
                directive, raw_path = sound_match.groups()
                loop_arg = None
            elif music_match:
                directive, raw_path, loop_arg = music_match.groups()
            else:
                continue
            source_path = norm(raw_path)
            if not source_path.startswith("DATA\\"):
                source_path = "DATA\\" + source_path
            requested_path = source_path
            resolved_path = PAK_ALIASES.get((family, source_path), source_path)
            asset = assets.get(resolved_path)
            ref = {
                "source_file": norm(e.name),
                "line": line_no,
                "directive": directive.lower(),
                "loop_argument": loop_arg,
                "semantic_event": "death" if directive.lower() == "diesound" else
                    "boss-music" if directive.lower() == "bossmusic" else
                    "music-selection" if directive.lower() == "music" else "animation-or-event-sound",
                "requested_source_path": requested_path,
                "resolved_source_path": resolved_path if asset is not None else None,
            }
            upper_source = norm(e.name)
            if "\\CHARS\\" in upper_source:
                suffix = upper_source.split("\\CHARS\\", 1)[1].rsplit("\\", 1)[0]
                ref["reachability"] = "shipped-reachable" if suffix in SHIPPED_CHARACTERS[family] else "unshipped-source-content"
            elif "\\LEVELS\\" in upper_source or "\\EASY\\" in upper_source:
                ref["reachability"] = "shipped-reachable" if Path(upper_source).name in shipped_levels(family) else "unshipped-source-content"
            else:
                ref["reachability"] = "shipped-reachable" if "\\SCENES\\ENDING.TXT" in upper_source else "unshipped-source-content"
            if asset is None:
                # Keep the unresolved reference visible; the verifier reports it.
                assets[requested_path] = {
                    "family": family, "kind": "missing-source", "source_path": requested_path,
                    "source_filename": Path(source_path).name, "source_hash": None,
                    "source_size_bytes": None, "format": None, "references": [ref],
                    "converter_representation": None, "packed_runtime": None,
                    "tad_sfx_id": None, "msu_track_id": None,
                }
            else:
                asset["references"].append(ref)
    # Engine-global samples are source-backed references, not inferred from
    # filenames or from the SNES implementation under test.
    beat1 = assets.get("DATA\\SOUNDS\\BEAT1.WAV")
    if family == "bor-original":
        for semantic in ENGINE_GLOBAL_AUDIO:
            asset = assets.get(semantic["asset"])
            if asset is None:
                continue
            asset["references"].append({
                "source_file": f"OpenBOR {ENGINE_REVISION}: {ENGINE_SOURCE}",
                "line": None,
                "directive": "engine-global-default",
                "semantic_event": semantic["event"],
                "engine_global_sample": f"global_sample_list.{semantic['global']}",
                "source_evidence": "load_special_sounds() maps the global sample; reachability reason is recorded in engine_audio_semantics.py",
                "reachability": "shipped-reachable" if semantic["reachable"] else "content-inapplicable",
                "snes_reachable": semantic["reachable"],
                "reachability_reason": semantic["reason"],
            })
    if family == "bor-original" and beat1 is not None:
        beat1["converter_representation"] = "soundwork/tad/project/samples/beat1.wav"
        beat1["packed_runtime"] = "TAD SFX::sfx_hit; Character_HitApply"
    for asset in assets.values():
        refs = asset["references"]
        reachable = [r for r in refs if r.get("reachability") == "shipped-reachable"]
        asset["raw_reference_count"] = len(refs)
        asset["shipped_reachable_reference_count"] = len(reachable)
        asset["shipped_reachable"] = bool(reachable)
        asset["implementation_classification"] = classify(asset)
    return {"family": family, "pak": pak.name, "pak_hash": sha256(pak.read_bytes()),
            "assets": sorted(assets.values(), key=lambda a: (a["kind"], a["source_path"]))}


def write_docs(manifest: dict, path: Path) -> None:
    lines = ["# Audio Inventory", "", "Generated from the local BOR/TMNT PAK archives by `tools/audio/generate_audio_manifest.py`.", "", "This is not an audio-complete claim. `implemented-and-gated` requires a real source reference and live runtime proof.", ""]
    for family in manifest["families"]:
        assets = family["assets"]
        sfx = [a for a in assets if a["kind"] == "sfx"]
        music = [a for a in assets if a["kind"] == "music"]
        ref_sfx = [a for a in sfx if a["references"]]
        ref_music = [a for a in music if a["references"]]
        reach_sfx = sum(1 for a in sfx for r in a["references"] if r.get("reachability") == "shipped-reachable")
        reach_music = sum(1 for a in music for r in a["references"] if r.get("reachability") == "shipped-reachable")
        lines += [f"## {family['family']}", "", f"PAK: `{family['pak']}`", f"- SFX WAV assets: {len(sfx)} total; {len(ref_sfx)} raw-referenced; {reach_sfx} shipped-reachable references; {len(sfx)-len(ref_sfx)} unused.", f"- BOR music assets: {len(music)} total; {len(ref_music)} raw-referenced; {reach_music} shipped-reachable references; {len(music)-len(ref_music)} unused.", ""]
        lines.append("| Asset | References | Classification | Runtime mapping |")
        lines.append("|---|---:|---|---|")
        for a in assets:
            if a["kind"] not in ("sfx", "music"):
                continue
            lines.append(f"| `{a['source_path']}` | {len(a['references'])} | `{a['implementation_classification']}` | `{a['packed_runtime'] or 'none'}` |")
        lines.append("")
    lines += ["## Architecture boundary", "", "TAD/SPC700 handles short gameplay/UI SFX. MSU-1 PCM handles the authored soundtrack pipeline. `distribution/bor-N.pcm` files are deterministic generated artifacts from the catalog, not placeholder proof clips.", "", "G11 remains DONE for one real landed-hit SFX path using BOR `BEAT1.WAV`; this pass does not reopen G11 or start G12."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT / "tools/audio/audio_manifest.json")
    ap.add_argument("--docs", type=Path, default=ROOT / "docs/audio_inventory.md")
    args = ap.parse_args()
    manifest = {"schema_version": 1, "source_of_truth": "local OpenBOR PAK archives", "families": [scan_family(f, p) for f, p in PAKS]}
    next_track = 1
    for family in manifest["families"]:
        for asset in family["assets"]:
            if asset["kind"] == "music" and any(r.get("reachability") == "shipped-reachable" for r in asset["references"]):
                asset["msu_track_id"] = next_track
                asset["track_key"] = f"{asset['family']}:{asset['source_path']}"
                next_track += 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    write_docs(manifest, args.docs)
    print(f"wrote {args.output} and {args.docs}")
    for family in manifest["families"]:
        a = family["assets"]
        print(f"{family['family']}: sfx={sum(x['kind']=='sfx' for x in a)} referenced_sfx={sum(x['kind']=='sfx' and bool(x['references']) for x in a)} music={sum(x['kind']=='music' for x in a)} referenced_music={sum(x['kind']=='music' and bool(x['references']) for x in a)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
