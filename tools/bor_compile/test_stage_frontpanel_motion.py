"""Source-only motion/ABI tests; no assembler, pack or emulator."""
import sys
import unittest
import tempfile
import copy
import json
from unittest.mock import patch
from pathlib import Path
from compiler import ROOT
sys.path[:0] = [str(ROOT),str(ROOT/'tools/bg_converter'),str(ROOT/'tools/rom_audit')]
import build_rom
import stage_water
import stage_frontpanel_bg2 as fp


class FrontpanelMotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        sources,cls.normal = stage_water.normal_stage_inputs(build_rom.STAGE_CONFIGS)
        def clean(index,level,row,source_path):
            m = json.loads((Path(build_rom.STAGE_CONFIGS[row.physical]['bg'])/'manifest.json').read_text())
            m.update(frontpanel=None,normal_frontpanel_removed=True,unique_tiles=1)
            return m,dict(zip(('tiles.bin','tilemap.bin','palette.bin'),
                (bytes(32),b'\0\0\1'*m['width_tiles']*28,bytes(256))))
        with patch.object(fp,'encode_clean_background',side_effect=clean):
            cls.configs,_ = fp.materialize_normal(build_rom.STAGE_CONFIGS,sources,cls.normal,
                ROOT/'out/bor_compile_s6/BOR.C',cls.temp.name)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_all_normal_fp_directions_and_resource_seams(self):
        normal = copy.deepcopy(self.normal)
        text,rows = fp.motion_tables(self.configs,normal)
        self.assertEqual([r['physical'] for r in rows],[22,27,28,30,33,34,35])
        self.assertTrue(all(r['adapter'].startswith('ACCEPTED_COMPAT') for r in rows))
        for r in rows:
            self.assertEqual(r['window_columns'],33)
            self.assertLessEqual(r['working_set']['34'],256)
        modes = list(map(int,text.split('.db ')[1].splitlines()[0].split(',')))
        self.assertEqual(modes[:22],[0]*22)
        self.assertEqual(sum(modes),7)
        normal[22].scroll = 'down'
        text,_ = fp.motion_tables(self.configs,normal)
        self.assertEqual(int(text.split('.db ')[1].splitlines()[0].split(',')[22]),2)

    def test_generated_max_camera_and_zero_period_fail_closed(self):
        import json
        path = Path(self.configs[22]['frontpanel'])/'manifest.json'
        real = Path.read_text
        for update,error in ((dict(owner_width_tiles=5884),'COORDINATE_OVERFLOW'),
                             (dict(target_cycle_width=0),'BG2_PERIOD')):
            altered = json.loads(real(path))
            altered.update(update)
            def read(p,*a,**kw):
                return json.dumps(altered) if p == path else real(p,*a,**kw)
            with patch.object(Path,'read_text',read),self.assertRaisesRegex(ValueError,error):
                fp.motion_tables(self.configs,self.normal)

    def test_full_bg2_commit_fence_without_hdma(self):
        code = (ROOT/'src/core/stage_frontpanel_bg2.pasm').read_text()
        producer,nmi = code.split('StageFp_BG2CommitDispatch:',1)
        self.assertNotIn('sta.l $00435',code)
        self.assertNotIn('sta.l $002108',producer)
        self.assertIn('sta.l $002108',nmi)
        self.assertIn('sta.l Nmi_Bg2ScrollY',nmi)
        patch_text = (ROOT/'docs/s8_frontpanel_bg2_hooks.patch').read_text()
        self.assertIn('-    jsr Core_StreamScrollFp_CommitColumn\n+    jsl StageFp_BG2CommitDispatch',patch_text)
        core = (ROOT/'src/core/nmi.pasm').read_text()
        commit = core.split('Core_Nmi_Play__do_commit:',1)[1]
        call = 'jsl StageFp_BG2CommitDispatch' if 'jsl StageFp_BG2CommitDispatch' in commit else 'jsr Core_StreamScrollFp_CommitColumn'
        self.assertLess(commit.index('jsr Core_Dma_ProcessQueue'),commit.index(call))
        self.assertLess(commit.index('sta $2100'),commit.index(call))
        self.assertLess(commit.index(call),commit.index('lda.l Nmi_HdmaEnable'))

    def test_integer_ratio_matches_bitwise_division_for_full_admitted_domain(self):
        for camera in range(46812):
            numerator,remainder = camera,0
            for _ in range(16):
                bit = numerator >> 15
                numerator = (numerator << 1)&65535
                remainder = remainder*2+bit
                if remainder >= 5:
                    remainder -= 5
                    numerator |= 1
            result = (numerator*7+[0,1,2,4,5][remainder])&65535
            self.assertEqual(result,camera*7//5)

    def test_resident_camera_and_two_page_addressing(self):
        for lo in range(130):
            hi = lo+32
            for fine in range(8):
                camera = lo*8+fine
                committed = max(lo*8,min(camera,(hi-31)*8))
                self.assertEqual(committed,camera)
                visible = range(committed//8,(committed+255)//8+1)
                slots = [c%64 for c in visible]
                self.assertEqual(len(slots),len(set(slots)))
                self.assertTrue(all(lo <= c <= hi for c in visible))
            for col in (lo,hi):
                for row in range(28):
                    word = 0x6C00+row*32+(col&31)+(1024 if col&32 else 0)
                    self.assertTrue(0x6C00 <= word < 0x7400)

    def test_widths_branch_reach_and_memory_boundaries(self):
        from check_width_directives import flatten,scan
        path = ROOT/'src/core/stage_frontpanel.pasm'
        self.assertEqual(scan(flatten(str(path)))[0],[])
        text = path.read_text()
        self.assertIn('StageFp_Work = $7FB784',text)
        self.assertLessEqual(0x7FB784+28,0x7FB800)
        self.assertIn('StageWater_WorkEnd = $7FB784',(ROOT/'src/core/stage_water.pasm').read_text())
        pc,aw,iw = 0,2,2
        labels,branches = {},[]
        shorts = {'beq','bne','bcc','bcs','bmi','bpl','bra'}
        implied = {'php','pha','phx','phy','cld','plx','ply','pla','plp','rtl','rts',
                   'inx','dex','tax','txa','clc','sec'}
        for raw in text.splitlines():
            line = raw.split(';',1)[0].strip()
            if not line or ' = ' in line: continue
            if line.endswith(':'):
                labels[line[:-1]] = pc
                continue
            if line in ('.a8','.a16'):
                aw = 1 if line == '.a8' else 2
                continue
            if line in ('.i8','.i16'):
                iw = 1 if line == '.i8' else 2
                continue
            op,_,arg = line.partition(' ')
            if op in shorts:
                branches.append((pc,arg)); size = 2
            elif op == '.db': size = len(arg.split(','))
            elif op in ('rep','sep'): size = 2
            elif op in implied or arg == 'a': size = 1
            elif op.endswith('.l') or op in ('jsl','jml'): size = 4
            elif op in ('jmp','jsr'): size = 3
            elif arg.startswith('#'): size = 1+(iw if op in ('ldx','cpx','ldy','cpy') else aw)
            else: self.fail('Unhandled instruction '+line)
            pc += size
        for offset,target in branches:
            self.assertTrue(-128 <= labels[target]-offset-2 <= 127,(target,labels[target]-offset-2))


if __name__ == '__main__': unittest.main()
