"""Offline contract tests for the candidate capacity-scan native profile parser."""
from __future__ import annotations
import json
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
for item in (ROOT / "tools/verify", ROOT / "tools/bor_compile"):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

import m4_capacity_scan_native as adapter
import m4_home_borrow_bitmap_native as home_bitmap
from test_early_capacity import ProbeVM


def _words(raw: bytes) -> list[int]:
    return [int.from_bytes(raw[i:i+2], "little") for i in range(0, len(raw), 2)]


def _dp_bytes(vm: ProbeVM, seed: bytes) -> bytes:
    result = bytearray(seed)
    for at, value in vm.dp.items():
        result[at:at+2] = value.to_bytes(2, "little")
    return bytes(result)


def _valid_rows(*, homes=False):
    # The no-home case deliberately carries sentinels in predictor scratch
    # $76/$78. Since no home is inspected, those caller-owned words must survive.
    maps = [0xFFFF] * 1024
    refs = [0] * 768
    if homes:
        maps[0] = 5
        refs[5] = 0x8000
    else:
        maps[0] = 0xFFFF
    seed = bytearray((i * 37 + 11) & 255 for i in range(128))
    seed[0x70:0x72] = (0xAAAA).to_bytes(2, "little")
    seed[0x72:0x74] = (0xBBBB).to_bytes(2, "little")
    seed[0x74:0x76] = (0xCCCC).to_bytes(2, "little")
    seed[0x76:0x78] = (0x1234).to_bytes(2, "little")
    seed[0x78:0x7A] = (0x5678).to_bytes(2, "little")
    entry = [0x1357, 0x2468, 0, 0x42, 0x3400, 0x1FFE, 0x40]
    vm = ProbeVM(maps, refs)
    vm.A, vm.X, vm.Y = entry[:3]
    vm.dp = {i: int.from_bytes(seed[i:i+2], "little") for i in range(0, 128, 2)}
    carry = vm.run()
    negative = vm.A < (49 if vm.dp[0x74] >= 49 else vm.dp[0x70])
    overflow = bool(entry[6] & 0x40) if vm.dp[0x74] >= 49 else False
    out_ps = ((entry[6] & 0x3C) | int(carry) | (2 if vm.Z else 0)
              | (0x80 if negative else 0) | (0x40 if overflow else 0))
    returned = [vm.A, vm.X, vm.Y, entry[3], entry[4], (entry[5] + 2) & 0xFFFF,
                out_ps]
    final_dp = _dp_bytes(vm, bytes(seed))
    entry_data = "2|" + "|".join(map(str, entry)) + "|" + b"".join(x.to_bytes(2,"little") for x in maps).hex() + "|" + b"".join(x.to_bytes(2,"little") for x in refs).hex() + "|" + bytes(seed).hex()
    return_data = "2|100|" + "|".join(map(str, returned)) + "|" + final_dp.hex()
    rows = [f"NB_CS_ENTRY|1000|10|200|{entry_data}",
            f"NB_CS_RETURN|1100|10|205|{return_data}"]
    return rows, entry, returned, bytes(seed), final_dp, vm


class CapacityScanAdapterProfileTests(unittest.TestCase):
    def profile(self, rows):
        with tempfile.TemporaryDirectory(prefix="capacity-scan-adapter-") as td:
            root = Path(td)
            (root / "native").mkdir()
            (root / "native/mesen.log").write_text("\n".join(rows) + "\n", encoding="utf-8")
            result = adapter.profile(root)
            self.assertEqual(json.loads((root / "capacity-scan-profile.json").read_text()), result)
            return result

    def test_correct_register_dp_and_caller_rts_delta_accept(self):
        rows, entry, returned, seed, final_dp, vm = _valid_rows()
        result = self.profile(rows)
        self.assertEqual(result["classification"], "CAPACITY_SCAN_NATIVE_PROFILE")
        self.assertEqual(len(result["calls"]), 1)
        self.assertEqual(result["calls"][0]["exact_result"], True)
        self.assertEqual(returned[5], (entry[5] + 2) & 0xFFFF)
        self.assertEqual(final_dp[0x76:0x7A], seed[0x76:0x7A])
        self.assertEqual(returned[2], 0)  # zero-home path, incoming Y was zero
        self.assertEqual(result["calls"][0]["homes"], 0)

    def test_home_path_sets_terminal_y_and_expected_scratch(self):
        rows, entry, returned, seed, final_dp, vm = _valid_rows(homes=True)
        result = self.profile(rows)
        self.assertEqual(returned[2], 0)
        self.assertEqual(result["calls"][0]["homes"], 1)
        self.assertEqual(int.from_bytes(final_dp[0x76:0x78], "little"), 5)
        self.assertEqual(int.from_bytes(final_dp[0x78:0x7A], "little"), 1 << 5)

    def test_rejects_return_dp_and_each_register_context_mismatch(self):
        rows, entry, returned, seed, final_dp, vm = _valid_rows()
        bad_dp = bytearray(final_dp); bad_dp[0x76] ^= 1
        for field, values in (
            ("DP", [bad_dp.hex()]),
            ("A", [str(returned[0] ^ 1)]),
            ("X", [str(returned[1] ^ 1)]),
            ("Y", [str(returned[2] ^ 1)]),
            ("DBR", [str(returned[3] ^ 1)]),
            ("D", [str(returned[4] ^ 1)]),
            ("SP", [str((returned[5] + 1) & 0xFFFF)]),
        ):
            with self.subTest(field=field):
                bad = rows[:]
                pieces = bad[1].split("|")
                if field == "DP": pieces[-1] = values[0]
                else:
                    index = {"A": 6, "X": 7, "Y": 8, "DBR": 9, "D": 10, "SP": 11}[field]
                    pieces[index] = values[0]
                bad[1] = "|".join(pieces)
                with self.assertRaisesRegex(ValueError, "CAPACITY_SCAN:"):
                    self.profile(bad)

    def test_rejects_changed_entry_d_or_mx_and_return_condition_flags(self):
        rows, entry, returned, seed, final_dp, vm = _valid_rows()
        for label, mutate in (
            ("entry-D", lambda p: p.__setitem__(9, str(0x3402))),
            ("entry-MX", lambda p: p.__setitem__(11, str(0x20))),
            ("return-C", lambda p: p.__setitem__(12, str(returned[6] ^ 1))),
            ("return-Z", lambda p: p.__setitem__(12, str(returned[6] ^ 2))),
            ("return-N", lambda p: p.__setitem__(12, str(returned[6] ^ 0x80))),
        ):
            with self.subTest(label=label):
                bad = rows[:]
                p = bad[0].split("|") if label.startswith("entry") else bad[1].split("|")
                mutate(p)
                bad[0 if label.startswith("entry") else 1] = "|".join(p)
                with self.assertRaisesRegex(ValueError, "CAPACITY_SCAN:"):
                    self.profile(bad)

    def test_rejects_no_open_call_and_no_entrant_return(self):
        rows, *_ = _valid_rows()
        with self.assertRaisesRegex(ValueError, "CAPACITY_SCAN:OPEN_CALL"):
            self.profile(rows[:1])
        with self.assertRaisesRegex(ValueError, "CAPACITY_SCAN:RETURN_WITHOUT_ENTRY"):
            self.profile(rows[1:])

    def test_outer_snes_queue_guard_exact_capacity_lease(self):
        """Execute the emitted outer SCPU guard with Lua 5.1, without Mesen."""
        import shutil
        lua = shutil.which("lua")
        if lua is None:
            self.skipTest("Lua 5.1 interpreter is unavailable")

        static_native = ROOT / "out/byor-motu-capacity-scan-static-v2/candidate/native"
        self.assertTrue((static_native / "publisher.bin").is_file())
        from actor_s5_entity_fixture import symbols
        sy = symbols(static_native / "publisher.sym")
        start = adapter.overlay.START
        code_end = sy["CsCodeEnd"]
        old_pc_guard = (
            f"or pc<{sy['NbCapacityPredict']} or pc>={sy['NbCodeEnd']}"
        )
        outer = (
            f"if 'snes'~='snes' or pc<{sy['NbBegin']} or pc>={sy['NbCodeEnd']} "
            "then nbLog('FAULT','QUEUE_OWNER:snes|'..a) end"
        )
        stub = home_bitmap.authorize_empty_queue_builder(outer, sy)
        early_owner = (
            f"if 'snes'~='snes' or pc<{sy['NbCapacityPredict']} or "
            f"pc>={sy['NbCodeEnd']} then nbLog('FAULT','EARLY_BITMAP_OWNER:snes|'..a) end"
        )
        stub += "\n" + early_owner + "\n" + early_owner + "\n"

        with tempfile.TemporaryDirectory(prefix="capacity-outer-guard-") as td:
            root = Path(td)
            script = root / "observer.lua"
            script.write_text(stub, encoding="utf-8")
            (root / "publisher.bin").write_bytes((static_native / "publisher.bin").read_bytes())

            def fake_accepted_observer(path, contract):
                path.write_text(stub, encoding="utf-8")

            contract = {
                "capacity_scan": True,
                "native_symbols": dict(sy, CsCodeEnd=code_end),
            }
            with patch.object(adapter.accepted, "observer", fake_accepted_observer):
                adapter.observer(script, contract)

            emitted = script.read_text(encoding="utf-8")
            guard_lines = [
                line for line in emitted.splitlines()
                if "QUEUE_OWNER:snes" in line
            ]
            self.assertEqual(len(guard_lines), 1)
            self.assertIn("QUEUE_OWNER:snes", guard_lines[0])
            # The adapter must leave the independent SA-1 rejection in the
            # inherited observer unchanged; its extra CS allowance is SCPU-only.
            inherited = home_bitmap_path_text()
            self.assertIn("for cpu in ('snes','sa1'):", inherited)
            self.assertIn("f\"if '{cpu}'~='snes' or pc<", inherited)
            guard = guard_lines[0].replace("(a&0x7ff)", "(a % 2048)")
            self.assertNotIn("&", guard)

            import re
            cs_pcs = [int(x) for x in re.findall(r"pc==(\d+)", guard)]
            self.assertEqual(cs_pcs, [3782673, 3782762])
            # Each case is (cpu, pc, bus-address, csActive, bbLive, metadata,
            # expected fault). Metadata is addressed by the real $42D words.
            good_meta = {
                0x42D600: 1, 0x42D606: 0, 0x42D608: 0,
                0x42D60A: 0, 0x42D660: 0, 0x42D674: 0,
                0x42D70C: 0,
            }
            cases = [
                ("valid_first_store", "snes", cs_pcs[0], 0x3480, True, False, good_meta, False),
                ("valid_second_store_last_byte", "snes", cs_pcs[1], 0x34CB, True, False, good_meta, False),
                ("wrong_pc", "snes", cs_pcs[0] + 1, 0x3480, True, False, good_meta, True),
                ("wrong_cpu", "sa1", cs_pcs[0], 0x3480, True, False, good_meta, True),
                ("inactive_lifetime", "snes", cs_pcs[0], 0x3480, False, False, good_meta, True),
                ("address_below_bitmap", "snes", cs_pcs[0], 0x347F, True, False, good_meta, True),
                ("address_at_end", "snes", cs_pcs[0], 0x34CC, True, False, good_meta, True),
            ]
            for name, word, expected in (
                ("owner", 0x42D600, 0), ("records", 0x42D606, 1),
                ("pair_a", 0x42D608, 1), ("pair_b", 0x42D60A, 1),
                ("queue", 0x42D70C, 1), ("retry", 0x42D660, 1),
                ("pressure", 0x42D674, 1),
            ):
                bad = dict(good_meta); bad[word] = expected
                cases.append(("bad_" + name, "snes", cs_pcs[0], 0x3480,
                              True, False, bad, True))
            # The old builder allowance remains available while its original
            # bitmap lease is live; the new CS clause does not widen it.
            old_meta = dict(good_meta); old_meta[0x42D70C] = 0
            cases.append(("existing_builder_lease", "snes", sy["BhBitmapLeaseBegin"],
                          0x3500, False, True, old_meta, False))

            lua_case_rows = []
            for name, cpu, pc, address, active, live, metadata, expected_fault in cases:
                values = ",".join(f"[{key}]={value}" for key, value in metadata.items())
                lua_case_rows.append(
                    "{name=%r,cpu=%r,pc=%d,a=%d,active=%s,live=%s,meta={%s},fault=%s}"
                    % (name, cpu, pc, address, str(active).lower(), str(live).lower(),
                       values, str(expected_fault).lower())
                )
            lua_program = "\n".join([
                "local cases={" + ",\n".join(lua_case_rows) + "}",
                "local failures=0",
                "for _,c in ipairs(cases) do",
                " local faults={}; local a=c.a; local pc=c.pc; local csActive=c.active; local bbLive=c.live",
                " local function nbLog(kind,msg) faults[#faults+1]=msg end",
                " local function nbWord(at) return c.meta[at] or 0 end",
                " if c.cpu=='snes' then",
                "  " + guard,
                " else faults[#faults+1]='BITMAP_QUEUE_WRITE_OWNER' end",
                " local got=#faults>0",
                " if got~=c.fault then io.stderr:write(c.name..' expected fault='..tostring(c.fault)..' got='..tostring(got)..'\\n'); failures=failures+1 end",
                "end",
                "if failures>0 then os.exit(1) end",
                "print('OUTER_QUEUE_GUARD_CASES_PASS '..#cases)",
            ])
            run = subprocess.run([lua, "-"], input=lua_program, text=True,
                                 capture_output=True, check=False)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn("OUTER_QUEUE_GUARD_CASES_PASS", run.stdout)


def home_bitmap_path_text() -> str:
    """Return source for the unchanged SA-1 write-owner path assertion."""
    return (ROOT / "tools/verify/m4_home_borrow_bitmap_native.py").read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
