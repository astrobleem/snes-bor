"""Synthetic integration tests for the fast warm-world materializer.

These fixtures exercise the host/native/endFrame joins, tuple reconstruction,
accepted audio packet coverage, and RGB24 screenshot calibration without
launching or changing an emulator.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
VERIFY = Path(__file__).resolve().parent
sys.path.insert(0, str(VERIFY))

from m4_warm_world_fast_capture import materialize
from warm_field_pixels import full_frame_records, reference_record
from warm_field_state import schema


def make_contract(payload_bytes=288):
    return {
        "symbols": {
            "SourceClock4086_Ready": 0x7FFA00,
            "SourceClock4086_TimeLo": 0x7FFA08,
            "SourceClock4086_Due": 0x7FFA10,
            "SourceWorldTick4086_Ready": 0x7FFA80,
            "SourceWorldTick4086_TimeLo": 0x7FFA88,
            "SourceWorldTick4086_State": 0x7FFA84,
            "SourceWorldTick4086_Phase": 0x7FFA8C,
            "SourceWorldTick4086_Pending": 0x7FFA90,
            "SourceWorldTick4086_Fault": 0x7FFA92,
            "SourceInputController_Raw1": 0x7FF8F4,
            "SourceInputController_Raw2": 0x7FF8F6,
            "VmSourceInput_Data": 0x7FF8C8,
            "TadPrivate_stream_frame": 0x7E8200,
            "TadPrivate_stream_chunks_accepted": 0x7E8210,
            "SourceAudio_Status": 0x7E8102,
            "VmSourceWorld_Time": 0x7E72E0,
            "TAD_STREAM_RING_ADDR": 0x0200,
        },
        "config": {"audio": {"payload_cpu": 0xC00000, "payload_bytes": payload_bytes}},
    }


def _set_range(packed, ranges, name, raw):
    offset = 0
    for entry in ranges:
        if entry["name"] == name:
            if len(raw) != entry["length"]:
                raise AssertionError((name, len(raw), entry["length"]))
            packed[offset:offset + len(raw)] = raw
            return
        offset += entry["length"]
    raise AssertionError("missing range " + name)


def field_data(contract, frame, accepted=0):
    ranges = schema(contract)["ranges"]
    packed = bytearray()
    for r in ranges:
        packed.extend(bytes(r["length"]))
    actor = bytes((frame + i) & 0xFF for i in range(80))
    side = bytes((frame * 3 + i) & 0xFF for i in range(64))
    pin = bytearray(actor + side + frame.to_bytes(4, "little"))
    _set_range(packed, ranges, "actor_hex", actor)
    _set_range(packed, ranges, "side_hex", side)
    _set_range(packed, ranges, "latest_hex", bytes(pin))
    _set_range(packed, ranges, "render_pin_hex", bytes(pin))
    _set_range(packed, ranges, "display_pin_hex", bytes(pin))
    _set_range(packed, ranges, "cold_pin_hex", bytes(pin[:146]))
    _set_range(packed, ranges, "chunks_accepted", accepted.to_bytes(2, "little"))
    _set_range(packed, ranges, "constructor_ready_word", (0xB4B8).to_bytes(2, "little"))
    # Set a known source time and its owner-row counterpart using the schema's
    # symbol-derived offset (never a guessed C-structure offset).
    clock = bytearray(64)
    clock_range = next(r for r in ranges if r["name"] == "clock")
    src_time = next(f for f in schema(contract)["fields"] if f["name"] == "source_time")
    clock[src_time["offset"]:src_time["offset"] + 4] = (0x12345678 + frame).to_bytes(4, "little")
    _set_range(packed, ranges, "clock", bytes(clock))
    return f"WARMFIELDDATA|{frame}|{90000 + frame}|{packed.hex()}"


def pixel_log(frames):
    rows = []
    prior_full = None
    previous = None
    for ordinal, (frame, pixels) in enumerate(frames, 1):
        if previous is not None and pixels == previous:
            rows.append(reference_record(ordinal, frame, prior_full))
        else:
            rows.extend(full_frame_records(ordinal, frame, 2, 1, pixels))
            prior_full = ordinal
        previous = pixels
    return rows


class WarmWorldFastCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.build = root / "build"
        self.folder = root / "capture"
        self.build.mkdir()
        self.folder.mkdir()
        self.contract = make_contract()
        (self.build / "contract.json").write_text(json.dumps(self.contract), encoding="utf-8")
        self.payload = bytes((i * 5 + 3) & 0xFF for i in range(288))
        (self.build / "bor.sfc").write_bytes(self.payload)
        self.host_rows = [
            dict(index=0, frame=10, frames_advanced=1, scripted_input=None,
                 calibration_png="calibration-0.png"),
            dict(index=1, frame=11, frames_advanced=1, scripted_input=None),
            dict(index=2, frame=12, frames_advanced=1, scripted_input=None,
                 calibration_png="calibration-2.png"),
        ]
        # Existing WARMFIELD events are the source endFrame callbacks, one PPU
        # frame before the MCP's post-step frameCount.
        lines = [f"WARMFIELD|{1000+i}|{9+i}|46264|{'00'*146}|{'00'*146}"
                 for i in range(3)]
        lines.extend(field_data(self.contract, 9 + i, accepted=1) for i in range(3))
        packet0 = self.payload[:144]
        lines.append(f"WARMARMPACKET|0|9|{packet0.hex()}")
        lines.extend(pixel_log([(9, (0x112233, 0x445566)),
                                (10, (0x112233, 0x445566)),
                                (11, (0x112233, 0x445566))]))
        (self.folder / "mesen.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
        Image.fromarray(np.array([[[0x11, 0x22, 0x33], [0x44, 0x55, 0x66]]], dtype=np.uint8)).save(
            self.folder / "calibration-0.png")
        Image.fromarray(np.array([[[0x11, 0x22, 0x33], [0x44, 0x55, 0x66]]], dtype=np.uint8)).save(
            self.folder / "calibration-2.png")

    def tearDown(self):
        self.temp.cleanup()

    def test_materializes_complete_tuples_with_exact_host_frame_join(self):
        proof = materialize(self.build, self.folder, self.host_rows)
        progress = json.loads((self.folder / "progress.json").read_text(encoding="utf-8"))
        self.assertEqual([r["frame"] for r in progress], [10, 11, 12])
        self.assertEqual([r["source_time"] for r in progress], [0x12345681, 0x12345682, 0x12345683])
        self.assertEqual([r["pixel_full_ordinal"] for r in progress], [1, 1, 1])
        self.assertTrue(all(r["capture_evidence"] == "native_complete_field" for r in progress))
        self.assertTrue(proof["all_owned_fields_have_exact_pixels"])
        self.assertTrue(proof["calibration"][0]["exact_rgb24"])
        self.assertEqual(proof["owned_fields"], 3)
        packets = json.loads((self.folder / "audio-packets.json").read_text(encoding="utf-8"))
        self.assertEqual(packets[0]["mismatched_bytes"], 0)
        self.assertEqual(packets[0]["aram"], 0x0200)

    def test_pre_owner_host_fields_are_kept_separate_from_owned_tuple_join(self):
        host_rows = [dict(index=i, frame=9 + i, frames_advanced=1, scripted_input=None)
                     for i in range(4)]
        host_rows[-1]["calibration_png"] = "calibration-3.png"
        lines = [f"WARMFIELD|{1000+i}|{10+i}|46264|{'00'*146}|{'00'*146}"
                 for i in range(2)]
        lines.extend(field_data(self.contract, 10 + i, accepted=1) for i in range(2))
        lines.append(f"WARMARMPACKET|0|10|{self.payload[:144].hex()}")
        lines.extend(pixel_log([(10, (0x112233, 0x445566)),
                                (11, (0x223344, 0x556677))]))
        (self.folder / "mesen.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
        Image.fromarray(np.array([[[0x22, 0x33, 0x44], [0x55, 0x66, 0x77]]], dtype=np.uint8)).save(
            self.folder / "calibration-3.png")
        proof = materialize(self.build, self.folder, host_rows)
        progress = json.loads((self.folder / "progress.json").read_text(encoding="utf-8"))
        self.assertEqual([r["capture_evidence"] for r in progress],
                         ["pre_owner_no_native_data", "pre_owner_no_native_data",
                          "native_complete_field", "native_complete_field"])
        self.assertEqual(proof["owned_fields"], 2)
        self.assertEqual(proof["full_rgb24_images"], 2)

    def test_missing_native_field_is_rejected(self):
        lines = [line for line in (self.folder / "mesen.log").read_text(encoding="utf-8").splitlines()
                 if not line.startswith("WARMFIELDDATA|10|")]
        (self.folder / "mesen.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "WARM_FIELD_FRAME_SET"):
            materialize(self.build, self.folder, self.host_rows)

    def test_wrapped_or_reordered_native_clock_cannot_authorize_publication(self):
        lines = (self.folder / "mesen.log").read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if line.startswith("WARMFIELDDATA|10|"):
                parts = line.split("|")
                parts[2] = "0"
                lines[i] = "|".join(parts)
        (self.folder / "mesen.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "FAST_NATIVE_FIELD_CLOCK_ORDER_OR_WRAP"):
            materialize(self.build, self.folder, self.host_rows)

    def test_missing_first_native_tuple_for_observed_owner_field_is_rejected(self):
        lines = [line for line in (self.folder / "mesen.log").read_text(encoding="utf-8").splitlines()
                 if not line.startswith("WARMFIELDDATA|9|")]
        (self.folder / "mesen.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "WARM_FIELD_FRAME_SET"):
            materialize(self.build, self.folder, self.host_rows)

    def test_host_frame_sequence_and_owner_field_coverage_are_strict(self):
        with self.assertRaisesRegex(ValueError, "FAST_HOST_FRAME_SEQUENCE"):
            materialize(self.build, self.folder, [self.host_rows[0],
                dict(self.host_rows[1], frame=12), self.host_rows[2]])
        lines = [line for line in (self.folder / "mesen.log").read_text(encoding="utf-8").splitlines()
                 if not (line.startswith("WARMFIELD|") and line.split("|")[2] == "10")]
        (self.folder / "mesen.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "FAST_OWNER_FIELD_COVERAGE"):
            materialize(self.build, self.folder, self.host_rows)

    def test_missing_pixel_tuple_is_rejected(self):
        lines = [line for line in (self.folder / "mesen.log").read_text(encoding="utf-8").splitlines()
                 if "WARMPIXREF|00000002|" not in line]
        (self.folder / "mesen.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "MISSING_OR_EXTRA_ORDINAL"):
            materialize(self.build, self.folder, self.host_rows)

    def test_missing_new_packet_rejects_accepted_counter_without_stale_reuse(self):
        lines = [line for line in (self.folder / "mesen.log").read_text(encoding="utf-8").splitlines()
                 if not line.startswith("WARMARMPACKET|")]
        (self.folder / "mesen.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "WARM_FIELD_PACKET_COVERAGE"):
            materialize(self.build, self.folder, self.host_rows)

    def test_mismatched_packet_payload_cannot_be_reported_as_exact(self):
        lines = (self.folder / "mesen.log").read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if line.startswith("WARMARMPACKET|"):
                header, payload = line.rsplit("|", 1)
                payload = ("00" if payload[:2] != "00" else "01") + payload[2:]
                lines[i] = header + "|" + payload
                break
        (self.folder / "mesen.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "FAST_NATIVE_AUDIO_PACKET_MISMATCH"):
            materialize(self.build, self.folder, self.host_rows)

    def test_rgb24_calibration_mismatch_cannot_be_accepted(self):
        Image.fromarray(np.array([[[0x11, 0x22, 0x34], [0x44, 0x55, 0x66]]], dtype=np.uint8)).save(
            self.folder / "calibration-0.png")
        with self.assertRaisesRegex(ValueError, "FAST_PIXEL_MCP_CALIBRATION:0"):
            materialize(self.build, self.folder, self.host_rows)


if __name__ == "__main__":
    unittest.main()
