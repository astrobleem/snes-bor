"""Focused S8 geometry/lifecycle, ownership, and isolated assembly checks.

No emulator. The link fixture stubs ONLY the explicitly external pit-damage
callback; assembly success is not evidence that production integration exists.
"""
import copy
from fractions import Fraction as F
import math
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import unittest

from compiler import ROOT, Source, project, stage
from source_actor_numeric import verify_source
from stage_bounds import Bounds, Pit, encode, emit_pasm, from_ir, grounded, import_q8, snapshot_checks


RUNTIME = ROOT/'src/core/stage_bounds.pasm'


class StageBoundsTests(unittest.TestCase):
    def test_pinned_source_formulas_and_lifecycle(self):
        path = ROOT/'out/bor_compile_s6/BOR.C'
        verify_source(path)
        text = path.read_text()
        for evidence in ('int checkhole(int x, int z)',
                         'x > level->width-(PLAYER_MAX_Z-z)',
                         'level->width-30-(PLAYER_MAX_Z-self->z)',
                         'self->base = -1000;', 'ent_unlink(self);',
                         'self->a -= self->z - (PANEL_Z-1);',
                         'self->z = PANEL_Z-1;', 'self->a < PIT_DEPTH',
                         'self->takedamage(self,10000,0,ATK_NORMAL)',
                         '!checkhole(e->x, e->z)'):
            self.assertIn(evidence, text)

    def test_real_normal_metadata_and_no_ir_mutation(self):
        source = Source(ROOT/'Beats of Rage Original [v.3.0 Build 4086].pak')
        normal = project(source).sets[1]
        flagged = []
        for entry in normal.entries:
            if entry.kind != 'STAGE':
                continue
            ir = stage(source, entry.source_path)
            before = copy.deepcopy(ir)
            b = from_ir(ir)
            self.assertEqual(ir, before)
            if b.blocked or b.endhole:
                flagged.append((entry.source_path.replace('\\', '/').lower(), b))
        self.assertEqual(flagged, [('data/normal/1c.txt', Bounds(640, True, False)),
                                   ('data/normal/5a.txt', Bounds(320, False, True))])

    def test_exact_source_boundary_projection_all_depths_and_width_residues(self):
        # Independent Fraction source oracle, not a second intercept formula.
        for width in (*range(320, 330), 640, 6876):
            b = Bounds(width, True, True)
            for y in range(256):
                source_depth_float = F(5*y, 4)
                source_depth_int = int(source_depth_float)
                max_x = math.floor(F(4, 5)*(width-30-(232-source_depth_float)))
                for x in range(max(0, max_x-2), max_x+3):
                    self.assertEqual(b.clamp(x, y), min(x, max_x))
                first_x = math.ceil(F(4, 5)*(width-232+source_depth_int+1))
                for x in range(max(0, first_x-2), first_x+3):
                    source_x = int(F(5*x, 4))
                    self.assertEqual(b.hole(x, y),
                                     2 if source_x > width-(232-source_depth_int) else 0)

    def test_strict_endhole_before_regular_hole_depth_cutoff(self):
        b = Bounds(320, False, True)
        self.assertEqual(b.hole(199, 128), 0)  # source x248,z160 <=248
        self.assertEqual(b.hole(200, 128), 2)  # source x250 >248, z<195
        self.assertEqual(b.hole(256, 186), 0)  # source x320,z232; strict >
        self.assertEqual(b.hole(257, 186), 2)
        self.assertEqual(Bounds(320).hole(65535, 128), 0)

    def test_disabled_and_record_abi(self):
        rows = [None, Bounds(640, True), Bounds(320, endhole=True)]
        data = encode(rows)
        self.assertEqual(len(data), 48)
        self.assertEqual(data[:16], bytes(16))
        self.assertEqual(struct.unpack_from('<8H', data, 16), rows[1].words())
        self.assertEqual(struct.unpack_from('<H', data, 32)[0], 2)
        self.assertIn('StageBounds_DataBank = $120000', emit_pasm(rows, bank=18))
        self.assertEqual(Bounds(640).clamp(65535, 10), 65535)
        for b in (Bounds(0), Bounds(90000)):
            with self.assertRaises(ValueError):
                b.words()
        with self.assertRaises(ValueError):
            encode([])

    def test_entry_preserves_screen_position_and_changes_panel_order(self):
        for y in range(256):
            p = Pit.enter(y)
            self.assertEqual(p.screen_y, y)
            self.assertEqual(p.base, -20000)
            self.assertEqual(p.depth, 123)
            self.assertFalse(p.linked)
            self.assertFalse(p.shadow)
            self.assertEqual(p.obj_priority, 0)

    def test_grounded_boolean_and_velocity_handoff(self):
        for a in range(-32, 33):
            self.assertEqual(grounded(0, 0, a), abs(F(a, 256)*F(5, 4)) < F(1, 10))
        self.assertFalse(grounded(1, 0, 0))
        self.assertFalse(grounded(0, -800, 0))
        for v in (-32768, -1536, -256, -1, 0, 1, 256, 1536, 32767):
            self.assertEqual(import_q8(v), int(F(v*25, 256)))
            p = Pit.enter(160, velocity_q8=v)
            before = p.height
            p.tick()
            self.assertEqual(p.height, max(-20000, before+import_q8(v)))

    def test_clock200_partition_and_recommended_snapshots(self):
        # ~60Hz consumer: carry odd source ticks across frames; total gravity
        # events is floor(total_clock200/2), never sum(floor(frame_delta/2)).
        clock = consumed = 0
        direct, framed = Pit.enter(160), Pit.enter(160)
        for delta in (3, 3, 4)*15:
            clock += delta
            due = clock//2-consumed
            for _ in range(due):
                framed.tick()
            consumed += due
        for _ in range(clock//2):
            direct.tick()
        self.assertEqual(framed, direct)
        self.assertEqual(consumed, 75)
        checks = snapshot_checks(Bounds(320, endhole=True), 160)
        self.assertEqual((checks['endhole_last_safe_x'], checks['endhole_first_x']), (231, 232))
        self.assertEqual(checks['entering']['height'], -920)
        self.assertEqual(checks['retired']['damage_calls'], 1)

    def test_gravity_matches_rational_source_until_terminal_event(self):
        for y in (128, 156, 160, 186, 255):
            p = Pit.enter(y)
            source_a = F(154) - F(y*5, 4)
            velocity = F(0)
            ticks = 0
            while not p.dead:
                source_a = max(-1000, source_a+velocity)
                velocity = max(-6, velocity-F(1, 10))
                p.tick()
                self.assertEqual(p.height, source_a*20)
                self.assertEqual(p.velocity, velocity*20)
                self.assertEqual(p.dead, source_a < -250)
                ticks += 1
                self.assertLess(ticks, 200)
            terminal = copy.deepcopy(p)
            p.tick()
            self.assertEqual(p, terminal)
        p = Pit(-5000)
        p.tick()
        self.assertFalse(p.dead)
        p.tick()
        self.assertTrue(p.dead)

    def test_wram_row_ownership(self):
        main = (ROOT/'src/main.pasm').read_text()
        stride = int(re.search(r'^CHAR_ZP_LEN\s*=\s*(\d+)', main, re.M)[1])
        self.assertEqual(stride, 133)
        # Current parallel owners end at +87 inclusive. Fail if a new owner
        # claims our bytes, including changes by concurrent integration work.
        for path in (ROOT/'src').rglob('*.pasm'):
            if path == RUNTIME:
                continue
            for name, value in re.findall(r'^(\w+)\s*=\s*StageEnv_Actors\s*\+\s*(\d+)',
                                          path.read_text(), re.M):
                self.assertFalse(88 <= int(value) <= 101, (path, name, value))
        occupied = [set(range(0x550f+i*stride+88, 0x550f+i*stride+102)) for i in range(6)]
        self.assertEqual(len(set.union(*occupied)), 84)
        self.assertLess(max(set.union(*occupied)), 0x5830)

    def test_new_module_width_directives(self):
        sys.path.insert(0, str(ROOT/'tools/rom_audit'))
        from check_width_directives import scan, flatten
        violations, count = scan(flatten(str(RUNTIME)))
        self.assertGreater(count, 20)
        self.assertEqual(violations, [])

    def test_isolated_assembly(self):
        dotnet = os.environ.get('DOTNET', r'C:\Users\chad\.dotnet\dotnet.exe')
        poppy = os.environ.get('POPPY_DLL', r'E:\gh\poppy-astrobleem\src\Poppy.CLI\bin\Release\net10.0\poppy.dll')
        if not Path(dotnet).is_file() or not Path(poppy).is_file():
            self.skipTest('Poppy toolchain unavailable')
        names = ('CHAR_POS_X', 'CHAR_POS_Y', 'CHAR_THROW_ZPOS', 'CHAR_THROW_ZVEL',
                 'CHAR_GRAB_TARGET', 'CHAR_GRABBED_BY', 'CHAR_ZP_LEN',
                 'Game_StageIndex', 'OamSetSprite_Y', 'OamSetSprite_Attr',
                 'StageEnv_Actors', 'StageEnv_BaseFraction', 'StageEnv_BaseInteger')
        definitions = []
        texts = '\n'.join((ROOT/p).read_text() for p in
                          ('src/main.pasm', 'src/core/game_state.pasm', 'src/core/oam.pasm',
                           'src/core/stage_environment.pasm'))
        for name in names:
            definitions.append(re.search(r'^'+name+r'\s*=.*$', texts, re.M)[0])
        fixture = '\n'.join(['.snes', '.bank 13', '.org $8000', *definitions,
                              emit_pasm([None, Bounds(640, True), Bounds(320, endhole=True)], bank=13),
                              '.bank 12', '.org $8000',
                              f'.include "{RUNTIME.as_posix()}"',
                              'StageBounds_ApplyPitDamage_Long:', '    rtl'])
        with tempfile.TemporaryDirectory(prefix='s8_bounds_') as tmp:
            path = Path(tmp)/'bounds.pasm'
            path.write_text(fixture)
            result = subprocess.run([dotnet, poppy, str(path), '-o', str(Path(tmp)/'bounds.bin')],
                                    capture_output=True, text=True, timeout=60, cwd=tmp)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            blob = (Path(tmp)/'bounds.bin').read_bytes()
            # Real nonzero-bank relocations, including the Poppy arithmetic
            # expression path that requires explicit DataBank on +offset.
            self.assertIn(bytes.fromhex('bf00800d'), blob)  # flags LDA long,X
            self.assertIn(bytes.fromhex('7f02800d'), blob)  # clamp ADC long,X
            self.assertIn(bytes.fromhex('7f04800d'), blob)  # hole ADC long,X


if __name__ == '__main__':
    unittest.main()
