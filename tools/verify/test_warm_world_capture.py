"""Offline tests for the warm-world capture evidence parser and input ABI."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m4_warm_world_capture as warm


ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "out" / "byor-motu-warm-presentation-v1" / "native-v6"
CONTRACT = BUILD / "contract.json"


def hex_pin(generation=1, fill=0x3C):
    raw = bytearray([fill] * warm.PIN_BYTES)
    raw[4:8] = generation.to_bytes(4, "little")
    raw[144:148] = (0).to_bytes(4, "little")
    return raw.hex()


def input_snapshot(rows, count, tick, ready=0xB4C2):
    raw = bytearray(32)
    raw[0:2] = ready.to_bytes(2, "little")
    raw[2:4] = count.to_bytes(2, "little")
    raw[4:8] = tick.to_bytes(4, "little")
    for port, row in enumerate(rows[:2]):
        for index, value in enumerate(row):
            raw[8 + port * 12 + index * 4:12 + port * 12 + index * 4] = value.to_bytes(4, "little")
    return raw.hex()


def warmpoint(name="LiveTick_ReturnGood", seed=0):
    # 31 source-observed DWORD/WORD values after the event name, in the
    # documented WARMPOINT ABI: clock/frame, CPU context, work/control, clock
    # and world owner state.
    values = [seed + i for i in range(31)]
    return "WARMPOINT|" + name + "|" + "|".join(map(str, values))


class WarmCaptureParserTests(unittest.TestCase):
    def parse(self, lines):
        with tempfile.TemporaryDirectory() as td:
            log = Path(td) / "mesen.log"
            log.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return warm._parse_events(log)

    def test_parses_full_warmpoint_and_endframe_clock_pin_row(self):
        display = hex_pin(1, 0x51)
        cold = hex_pin(1, 0x51)[:warm.COLD_PIN_BYTES * 2]
        parsed = self.parse([
            warmpoint(seed=100),
            f"WARMFIELD|123456|77|46264|{display}|{cold}",
            f"WARMMAINREADY|120000|75|46264|0|{display}|{cold}",
        ])
        self.assertEqual(parsed["malformed_events"], [])
        point = parsed["warm_points"][0]
        self.assertEqual(point["master_clock"], 100)
        self.assertEqual(point["frame"], 101)
        self.assertEqual(point["cpu_pb"], 110)
        self.assertEqual(point["work_owner"], 111)
        self.assertEqual(point["world_state"], 127)
        self.assertEqual(parsed["field_events"], [dict(
            master_clock=123456, frame=77, constructor_ready=46264,
            display_pin_hex=display, cold_pin_hex=cold)])
        ready = parsed["warm_ready"][0]
        self.assertEqual(ready["display_epoch"], 0)
        self.assertEqual(ready["display_generation"], 1)
        self.assertTrue(ready["display_matches_cold"])

    def test_generation_is_read_from_pin_dword_not_epoch(self):
        generation_zero = hex_pin(0)
        parsed = self.parse([
            f"WARMMAINREADY|10|1|46264|0|{generation_zero}|{generation_zero}",
        ])
        row = parsed["warm_ready"][0]
        self.assertEqual(row["display_epoch"], 0)
        self.assertEqual(row["display_generation"], 0)

    def test_input_refresh_held_press_release_and_unowned_second_player(self):
        # Use the actual source oracle rather than a duplicate button mapping.
        from source_input_controller import refresh
        samples = []
        old = [0]
        for tick, raw in enumerate((0x0100, 0x0100, 0x0000), 1):
            expected = refresh(old, [raw])
            row = expected[0]
            snap = input_snapshot([row, (0xDEAD, 0xBEEF, 0xCAFE)], 1, tick)
            samples.append(f"WARMINPUT|{tick * 100}|{tick}|{raw}|0|{snap}")
            old = [row[0]]
        parsed = self.parse(samples)
        rows = parsed["input_samples"]
        self.assertEqual(len(rows), 3)
        self.assertEqual([r["exact"] for r in rows], [True, True, True])
        self.assertEqual([r["actual_rows"][0] for r in rows],
                         [tuple(row) for row in (refresh([0], [0x0100])[0],
                                                 refresh([8], [0x0100])[0],
                                                 refresh([8], [0])[0])])
        self.assertTrue(all(r["unowned_raw_port2_not_qualified"] for r in rows))

    def test_input_count_two_is_not_owned_or_qualified(self):
        snap = input_snapshot([(0x100, 0x100, 0), (0, 0, 0)], 2, 1)
        parsed = self.parse([f"WARMINPUT|100|1|256|0|{snap}"])
        row = parsed["input_samples"][0]
        self.assertFalse(row["exact"])
        self.assertEqual(row["source_players"], 2)

    def test_malformed_rows_and_truncation_are_retained_as_diagnostics(self):
        parsed = self.parse([
            "WARMPOINT|too|short",
            "WARMFIELD|clock|frame|ready|pin|cold",
            "WARMINPUT|1|2|3|4|not-hex",
            "WARMTRUNCATED|1",
        ])
        self.assertEqual(len(parsed["malformed_events"]), 3)
        self.assertTrue(parsed["truncated"])


class WarmCaptureInputScriptTests(unittest.TestCase):
    def load(self, value, fields=12):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "input.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            return warm.load_input_script(path, fields)

    def test_duration_expansion_and_case_insensitive_buttons(self):
        actions = self.load([{"field": 3, "buttons": ["rIgHt"], "duration": 2}])
        self.assertIs(actions[3], actions[4])
        self.assertEqual(actions[3]["buttons"], ["Right"])
        self.assertEqual(actions[3]["source_snes_mask"], 0x0100)
        self.assertEqual(actions[3]["mcp_names"], ["BTN_RIGHT"])

    def test_rejects_overlapping_duration_ranges(self):
        with self.assertRaisesRegex(ValueError, "OVERLAPPING_RANGE"):
            self.load([{"field": 2, "buttons": ["Left"], "duration": 3},
                       {"field": 4, "buttons": ["Right"]}])

    def test_rejects_duration_past_capture_domain_and_invalid_buttons(self):
        with self.assertRaisesRegex(ValueError, "RANGE"):
            self.load([{"field": 10, "buttons": ["Right"], "duration": 3}], fields=12)
        with self.assertRaisesRegex(ValueError, "UNKNOWN_BUTTON"):
            self.load([{"field": 1, "buttons": ["Turbo"]}])
        with self.assertRaisesRegex(ValueError, "DUPLICATE_BUTTON"):
            self.load([{"field": 1, "buttons": ["Left", "left"]}])


class WarmCaptureObserverTests(unittest.TestCase):
    @unittest.skipUnless(CONTRACT.is_file(), "native-v6 offline contract is not present")
    def test_observer_uses_exact_renderer_range_and_excludes_helpers(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as td:
            script, report = warm._observer(Path(td), contract)
            lua = script.read_text(encoding="utf-8")
        allow = report["renderer_write_allowlist"]
        self.assertEqual(allow["warm_ranges"], [contract["config"]["warm"]["renderer_range"]])
        self.assertEqual(allow["rejected_helper_bank"], "0x2B")
        self.assertIn("pc>=", lua)
        self.assertIn("pc<", lua)
        self.assertNotIn("if bank==0x2e then return true end", lua)
        self.assertIn("not liveAllowed(pc)", lua)
        self.assertIn("liveAllowed(pc)~=liveAllowed(actual)", lua)


if __name__ == "__main__":
    unittest.main()
