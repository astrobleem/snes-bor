import copy
import hashlib
import re
import unittest
from pathlib import Path

from compiler import ROOT, Source, project, stage
from source_actor_numeric import verify_source
from stage_water import (ADAPTATION, FRAMES, ROCK, WaterMetadata, bind, composite,
                         emit_tables, phases, raster, scale_x, scale_y, wave)


class StageWaterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Source(ROOT / 'Beats of Rage Original [v.3.0 Build 4086].pak')
        cls.stages = [stage(cls.source, e.source_path)
                      for e in project(cls.source).sets[1].entries if e.kind == 'STAGE']
        cls.rows = [bind(cls.source, ir, n) for n, ir in enumerate(cls.stages)]

    def test_current_pin_and_render_calls(self):
        path = ROOT / 'out/bor_compile_s6/BOR.C'
        verify_source(path)
        text = path.read_text()
        self.assertIn('if(i<2) i = 2;', text)
        self.assertIn('time/(GAME_SPEED/30)', text)
        self.assertIn('time/(GAME_SPEED/8)', text)
        self.assertIn('inta*256, 10, texture', text)
        self.assertIn('inta,0, texture, time, 5', text)
        numbers = re.search(r'rockoffs\[32\] = \{([^}]+)', text)[1]
        self.assertEqual(tuple(map(int, re.findall(r'\d+', numbers))), ROCK)

    def test_complete_normal_source_inventory_and_identity_independence(self):
        self.assertEqual(len(self.rows), 14)
        self.assertEqual([(n, r.amplitude, r.rocking, r.background_height)
                          for n, r in enumerate(self.rows) if r.active],
                         [(4,15,True,80), (5,0,True,81), (6,0,True,81), (7,2,False,80)])
        for n, r in enumerate(self.rows):
            self.assertEqual(r.adaptation, ADAPTATION)
            renamed = copy.deepcopy(self.stages[n])
            renamed.source_path = 'DATA/UNRELATED.TXT'
            b = bind(self.source, renamed, 200)
            self.assertEqual((b.amplitude,b.rocking,b.background_height),
                             (r.amplitude,r.rocking,r.background_height))
            if r.texture_path:
                self.assertEqual(hashlib.sha256(self.source.read(r.texture_path)).hexdigest(),
                                 r.texture_sha256)

    def test_last_assignment_clamp_and_rejections(self):
        ir = copy.deepcopy(self.stages[4])
        ir.environment['rock'].append(0)
        ir.environment['water'].append(dict(ir.environment['water'][0], mode=0))
        r = bind(self.source, ir, 0)
        self.assertEqual((r.amplitude,r.rocking), (2,False))
        for bad in (3,16,255):
            ir.environment['water'][-1]['mode'] = bad
            with self.assertRaisesRegex(ValueError, 'AMPLITUDE'):
                bind(self.source, ir, 0)
        with self.assertRaisesRegex(ValueError, 'PHYSICAL'):
            bind(self.source, self.stages[4], 256)
        with self.assertRaisesRegex(ValueError, 'SOURCE'):
            bind(self.source, self.stages[4], 0, dialect='openbor')
        ir = copy.deepcopy(self.stages[4])
        ir.scroll = 'down'
        with self.assertRaisesRegex(ValueError, 'SCROLL'):
            bind(self.source, ir, 0)

    def test_full_clock_cycle_integer_divisors_and_bounds(self):
        self.assertEqual(phases(0), (0,2,-8))
        # BOR's integer 200/30 is SIX, not an ideal 30Hz clock.
        self.assertEqual(phases(2)[2], scale_x(1)-8)
        self.assertEqual(phases(8)[1], scale_y(ROCK[1]))
        for f in range(FRAMES):
            tick = f*10//3
            phase, y, dx = phases(f)
            self.assertEqual(phase, tick % 256)
            self.assertEqual(y, scale_y(ROCK[tick//25 % 32]))
            self.assertTrue(-8 <= dx <= 7)
        t = FRAMES*10//3
        self.assertEqual((t % 256, (t//25)%32, (t//6)%20), (0,0,0))
        self.assertEqual((min(wave(15)),max(wave(15))), (-12,12))
        self.assertEqual((min(wave(2)),max(wave(2))), (-2,1))

    def test_hdma_boundaries_easy_gate_and_plane_precedence(self):
        for row in self.rows:
            for campaign in (0,1,2,4,255):
                self.assertIsNone(raster(row,0,campaign=campaign))
        self.assertIsNone(raster(self.rows[0],0))
        water, y = raster(self.rows[7], 30, 100, 9)
        self.assertEqual(len(water), 673)
        self.assertEqual(water[-1], 0)
        self.assertEqual(y,9)
        xs = [int.from_bytes(water[i*3+1:i*3+3], 'little') for i in range(224)]
        self.assertEqual(xs[:75], [100]*75)
        self.assertEqual(xs[150:], [100]*74)
        self.assertNotEqual(xs[75:150], [100]*75)
        boat, y = raster(self.rows[4], 0, 0, 0)
        self.assertEqual(y,2)
        self.assertEqual(set(boat[::3][:-1]), {1})
        # Plane overrides wave even though source water amplitude is 15.
        self.assertEqual(len(set(int.from_bytes(boat[i*3+1:i*3+3], 'little')
                                 for i in range(150))), 1)
        self.assertEqual(boat[:3], b'\x01\xf8\xff')

    def test_nmi_lease_stays_out_of_dma_dependent_world_service(self):
        water = (ROOT / 'src/core/stage_water.pasm').read_text()
        begin = water[water.index('StageWater_Begin:'):
                      water.index('StageWater_Begin__done:')]
        self.assertNotIn('sta.l Nmi_FrameBusy', begin)
        oam_begin = water[water.index('StageWater_OamBegin:'):
                          water.index('StageWater_ApplyOamY:')]
        self.assertIn('sta.l Nmi_FrameBusy', oam_begin)

        game_state = (ROOT / 'src/core/game_state.pasm').read_text()
        playing = game_state[game_state.index('Game_State_Play__playing:'):
                            game_state.index('Game_State_Play__stageclear:')]
        ordered = ('jsr Core_StreamScroll_Play',
                   'jsr Core_StreamScrollFp_Play', 'jsl Spawn_Play',
                   'jsl StageWater_OamBegin', 'jsr Core_Oam_Play',
                   'jsl StageWater_End')
        self.assertEqual(sorted(playing.index(item) for item in ordered),
                         [playing.index(item) for item in ordered])

    def test_emitted_abi_and_rom_budget(self):
        text = emit_tables(self.rows)
        fields = dict(re.findall(r'(StageWater_\w+):\n((?:    \.db [^\n]+\n)+)',text))
        counts = {k: len(re.findall(r'\d+',v)) for k,v in fields.items()}
        self.assertEqual(counts['StageWater_ModeMap'],256)
        self.assertEqual(counts['StageWater_PhaseFrames'],5760)
        self.assertEqual(counts['StageWater_RowPhases'],224)
        self.assertEqual(sum(counts.values()),19008)
        with self.assertRaisesRegex(ValueError,'DUPLICATE'):
            emit_tables([self.rows[4],self.rows[4]])

    def test_real_texture_bake_under_panels_and_unchanged_other_stages(self):
        import numpy as np
        from composite_scene import PakIndex, load_level, composite_level
        idx = PakIndex(self.source.path)
        for ordinal in (0,4,7):
            row = self.rows[ordinal]
            level = load_level(idx,row.source_path)
            original = composite_level(idx,level)
            baked = composite(idx,level,row)
            self.assertEqual(original.shape,baked.shape)
            self.assertTrue(np.array_equal(original[:80], baked[:80]))
            self.assertTrue(np.array_equal(original[160:], baked[160:]))
            if row.texture_path:
                self.assertGreater(np.count_nonzero(original != baked), 0)
            else:
                self.assertTrue(np.array_equal(original,baked))
            # All opaque panel pixels survive the texture insertion.
            x = 0
            for name in level.ordered_panels():
                rgb,mask = idx.image(name)
                h = min(240,len(rgb))
                if not level.frontpanel:
                    self.assertTrue(np.array_equal(baked[:h,x:x+rgb.shape[1]][mask[:h]],
                                                   rgb[:h][mask[:h]]))
                x += rgb.shape[1]

    def test_runtime_double_buffer_and_register_contract(self):
        text = (ROOT/'src/core/stage_water.pasm').read_text()
        self.assertIn('eor #674',text)
        self.assertIn('cmp #224',text)
        self.assertIn('ora #$40',text)
        self.assertIn('and #$BF',text)
        self.assertNotRegex(text,r'(?i)\$0043[07][0-9a-f]')
        self.assertNotRegex(text,r'(?i)\b(?:stz|inc|dec|ldx|ldy)\.l\b')
        # Table offsets and terminators never cross active/inactive boundaries.
        for active in (0,674):
            inactive = active ^ 674
            self.assertTrue(set(range(active,active+673)).isdisjoint(
                range(inactive,inactive+673)))
            self.assertLessEqual(32+inactive+673,1380)

    def test_wram_binding_widths_and_relative_branch_reach(self):
        import sys
        sys.path.insert(0,str(ROOT/'tools/rom_audit'))
        from check_width_directives import flatten, scan
        path = ROOT/'src/core/stage_water.pasm'
        self.assertEqual(scan(flatten(str(path)))[0], [])
        text = path.read_text()
        self.assertIn('StageWater_Work = $7FB220',text)
        self.assertIn('StageWater_WorkEnd = $7FB784',text)
        self.assertEqual(0x7FB784-0x7FB220,1380)
        self.assertGreaterEqual(0x7FB220,0x7FB202)
        self.assertLessEqual(0x7FB784,0x7FB800)
        # Source-only length/branch audit; no assembler or CPU emulator is run.
        pc, aw, iw = 0, 2, 2
        labels, branches = {}, []
        shorts = {'beq','bne','bcc','bcs','bmi','bpl','bra'}
        implied = {'php','pha','phx','phy','cld','plx','ply','pla','plp','rtl',
                   'inx','dex','tax','clc','sec'}
        for raw in text.splitlines():
            line = raw.split(';',1)[0].strip()
            if not line or ' = ' in line:
                continue
            if line.endswith(':'):
                labels[line[:-1]] = pc
                continue
            if line in ('.a8','.a16'):
                aw = 1 if line == '.a8' else 2
                continue
            if line in ('.i8','.i16'):
                iw = 1 if line == '.i8' else 2
                continue
            op, _, arg = line.partition(' ')
            if op in shorts:
                branches.append((pc,arg))
                size = 2
            elif op in ('rep','sep'):
                size = 2
            elif op in implied or arg == 'a':
                size = 1
            elif op.endswith('.l'):
                size = 4
            elif op in ('jsl','jml'):
                size = 4
            elif op == 'jmp':
                size = 3
            elif arg.startswith('#'):
                size = 1+(iw if op in ('ldx','cpx','ldy','cpy') else aw)
            else:
                self.fail('Unhandled source-lint instruction: '+line)
            pc += size
        for offset,target in branches:
            self.assertIn(target,labels)
            self.assertTrue(-128 <= labels[target]-offset-2 <= 127,
                            (offset,target,labels[target]-offset-2))
        self.assertLess(pc+19008,0x8000)


if __name__ == '__main__':
    unittest.main()
