#!/usr/bin/env python3
"""Focused G15 Batch L1A BORVID1 append-only packaging gate."""
import hashlib
import os
import struct
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import build_rom  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "tools", "bor_converter"))
import pack_msu_roster  # noqa: E402

FIXTURE = bytes.fromhex("00112233445566778899AABBCCDDEEFF")


def parse_generated(path):
    text = open(path, encoding="ascii").read()
    count = int(next(line.split("=", 1)[1] for line in text.splitlines()
                     if line.startswith("SceneVideo_Count")))
    records = []
    for line in text.splitlines():
        if ".db " not in line:
            continue
        values = [int(token.strip().lstrip("$"), 16)
                  for token in line.split(".db ", 1)[1].split(",")]
        records.append(bytes(values))
    return count, records, text


def pack(scene_entries=None):
    spawns = [open(path, "rb").read() for path in build_rom.SPAWN_TABLES]
    vm_blob = open(build_rom.VM_MODULE, "rb").read()
    return pack_msu_roster.pack_roster(
        build_rom.ROSTER_PREFIXES,
        bgs=build_rom.BG_SCREENS,
        fps=build_rom.FP_SCREENS,
        spawns=spawns,
        vm_blob=vm_blob,
        playable_count=build_rom.PLAYABLE_ROSTER_COUNT,
        scene_video_entries=scene_entries,
    )


def main():
    baseline, baseline_meta = pack()
    entry = {
        "scene_id": 1, "flags": 0, "width": 256, "height": 192,
        "fps_num": 25, "fps_den": 1, "frame_count": 126,
        "payload": FIXTURE,
    }
    fixture, fixture_sidecar = pack([entry])
    fixture_again, _ = pack([entry])

    with tempfile.TemporaryDirectory(prefix="g15_l1b_") as temp:
        baseline_meta_path = os.path.join(temp, "baseline.pasm")
        fixture_meta_path = os.path.join(temp, "fixture.pasm")
        pack_msu_roster.write_scene_video_metadata(
            baseline_meta_path, baseline_meta["scene_video"])
        pack_msu_roster.write_scene_video_metadata(
            fixture_meta_path, fixture_sidecar["scene_video"])
        baseline_generated = parse_generated(baseline_meta_path)
        fixture_generated = parse_generated(fixture_meta_path)

    section_start = len(baseline)
    header = struct.unpack_from("<8sHHI", fixture, section_start)
    values = struct.unpack_from("<HHHHHHIII", fixture, section_start + 16)
    metadata = [{
        "scene_id": values[0], "flags": values[1], "width": values[2],
        "height": values[3], "fps_num": values[4], "fps_den": values[5],
        "frame_count": values[6], "payload_offset": values[7],
        "payload_size": values[8],
    }]
    expected_record = struct.pack("<HHHHHHIII", *values)
    checks = [
        ("baseline has BORMSU1 magic", baseline[:8] == b"BORMSU1\0"),
        ("zero-entry sidecar is empty", baseline_meta["scene_video"] == []),
        ("zero-entry generated count is zero", baseline_generated[0] == 0
         and baseline_generated[1] == []),
        ("fixture preserves legacy prefix", fixture[:section_start] == baseline),
        ("section starts at legacy end", fixture[section_start:section_start + 8] == b"BORVID1\0"),
        ("header fields parse", header == (b"BORVID1\0", 1, 1, 24)),
        ("entry metadata matches", fixture_sidecar["scene_video"] == metadata),
        ("generated count is one", fixture_generated[0] == 1),
        ("generated record matches BORVID1", fixture_generated[1] == [expected_record]),
        ("generated metadata is deterministic", fixture_generated[2] ==
         pack_msu_roster.scene_video_metadata_pasm(fixture_sidecar["scene_video"])),
        ("payload offset is absolute", values[7] == section_start + 16 + 24),
        ("fixture payload matches", fixture[values[7]:values[7] + values[8]] == FIXTURE),
        ("payload is in file bounds", values[7] + values[8] <= len(fixture)),
        ("fixture rebuild is deterministic", fixture_again == fixture),
    ]
    for name, ok in checks:
        print(("PASS" if ok else "FAIL") + ": " + name)
    print("legacy_prefix_bytes:", len(baseline))
    print("fixture_payload_offset:", values[7])
    print("fixture_payload_size:", values[8])
    print("fixture_size:", len(fixture))
    print("baseline_sha256:", hashlib.sha256(baseline).hexdigest())
    print("fixture_sha256:", hashlib.sha256(fixture).hexdigest())
    return 0 if all(ok for _, ok in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
