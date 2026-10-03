"""Full FP source/media/ownership checks, no production build or emulator."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import struct
import re
import unittest
from unittest.mock import patch
import numpy as np

from compiler import ROOT
sys.path[:0] = [str(ROOT),str(ROOT/'tools/bg_converter'),str(ROOT/'tools/bor_converter'),str(ROOT/'tools/rom_audit')]
import stage_frontpanel as fp
import stage_frontpanel_bg2 as full
import snes_tiles as st


def source_lint(path):
    from check_width_directives import flatten,scan
    widths = scan(flatten(str(path)))[0]
    pc,aw,iw = 0,2,2
    labels,branches = {},[]
    shorts = {'beq','bne','bcc','bcs','bmi','bpl','bra'}
    implied = {'php','pha','phx','phy','cld','plx','ply','pla','plp','rtl','rts',
               'inx','dex','iny','dey','tax','txa','clc','sec','xba'}
    for raw in path.read_text().splitlines():
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
        elif op in ('jmp','jsr','brl'): size = 3
        elif arg.startswith('#'): size = 1+(iw if op in ('ldx','cpx','ldy','cpy') else aw)
        elif re.fullmatch(r'\$[0-9A-Fa-f]{4}',arg): size = 3
        else: raise AssertionError('Unhandled instruction '+line)
        pc += size
    return widths,[(target,labels[target]-offset-2) for offset,target in branches
                  if not -128 <= labels[target]-offset-2 <= 127],pc


class FullFrontpanelTests(unittest.TestCase):
    def test_relocated_easy_commit_is_instruction_identical_and_long_return_safe(self):
        patch_text = (ROOT/'docs/s8_frontpanel_bg2_hooks.patch').read_text()
        old = '\n'.join(line[1:] for line in patch_text.splitlines() if line.startswith('-') and not line.startswith('---'))
        old = old.split('Core_StreamScrollFp_CommitColumn:',1)[1].split('Core_StreamScrollFp_Play:',1)[0]
        expected = ('Core_StreamScrollFp_CommitColumn:'+old).replace('Core_StreamScrollFp_CommitColumn','StageFp_BG2LegacyCommit')
        expected = expected.replace('    rts','    rtl')
        actual = (ROOT/'src/core/stage_frontpanel_legacy.pasm').read_text()
        def instructions(text):
            return [line.split(';',1)[0].strip() for line in text.splitlines()
                    if line.split(';',1)[0].strip() and not line.strip().startswith('.')]
        self.assertEqual(instructions(actual),instructions(expected))
        widths,branches,size = source_lint(ROOT/'src/core/stage_frontpanel_legacy.pasm')
        self.assertEqual((widths,branches,size),([],[],84))
        self.assertIn('+    jsl StageFp_BG2LegacyCommit\n+    rts',patch_text)
        self.assertIn('jsl StageFp_BG2LegacyCommit',(ROOT/'src/core/stage_frontpanel_bg2.pasm').read_text())
        self.assertEqual(16+20+4+(5-84),-39)

    def media_fixture(self, root, count=1, width=34, entries=None):
        from convert_frontpanel import normal_font_palette_binding
        font,binding = normal_font_palette_binding()
        palette = bytearray(32)
        palette[8:16] = b''.join(v.to_bytes(2,'little') for v in font)
        manifest = dict(full_fp_adapter=full.ADAPTER,layer='BG2_frontpanel',streaming=True,
            bpp=4,height_tiles=28,width_tiles=width,owner_width_tiles=width,
            unique_tiles=count,target_cycle_width=width*8,font_palette_binding=binding)
        blobs = dict(zip(fp.FILES,(bytes(count*32),st.encode_tilemap_column_major(
            entries or [(0,0,False,False)]*width*28,width,28),bytes(palette))))
        for name,data in blobs.items(): (root/name).write_bytes(data)
        (root/'manifest.json').write_text(json.dumps(manifest))
        return manifest,blobs

    def test_tile_domain_and_staging_union_actual_boundaries(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for count in (0,1,768,769):
                self.media_fixture(root,count=count)
                if 1 <= count <= 768: full.validate_bg2(root)
                else:
                    with self.assertRaisesRegex(ValueError,'BG2_ABI'): full.validate_bg2(root)
            # 34 columns own 257 distinct tiles; each 33-column window fits.
            counts = [8]*19+[7]*15
            starts = np.cumsum([0]+counts[:-1])
            entries = [(int(starts[x]+y%counts[x]),0,False,False) for y in range(28) for x in range(34)]
            self.media_fixture(root,count=257,entries=entries)
            with self.assertRaisesRegex(ValueError,'RESIDENT_UNION_CAPACITY'): full.validate_bg2(root)
            from convert_frontpanel import verify_window_budget
            ring = [entries[y*34+x%34] for y in range(28) for x in range(68)]
            self.assertLessEqual(verify_window_budget(ring,68,28,33)[0],256)
            self.assertEqual(verify_window_budget(ring,68,28,34)[0],257)

    def test_pack_header_easy_bytes_and_bg2_address_limit(self):
        import build_rom
        from pack_msu_roster import build_fp_blob
        cfg = next(c for c in build_rom.STAGE_CONFIGS[:22] if c.get('frontpanel'))
        path = Path(cfg['frontpanel'])
        m = json.loads((path/'manifest.json').read_text())
        blob,info = build_fp_blob(str(path),m['width_tiles'],0x120000)
        expected = struct.pack('<HBxH2xII',m['width_tiles'],m['height_tiles'],m['unique_tiles'],
            info['tilemap_offset'],info['tiles_offset'])+b''.join((path/n).read_bytes()
                for n in ('palette.bin','tilemap.bin','tiles.bin'))
        self.assertEqual(blob,expected)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            self.media_fixture(path)
            blob,info = build_fp_blob(str(path),34,0x120000)
            self.assertEqual(blob[2:4],bytes((28,4)))
            self.assertEqual(info['blob_size'],16+32+34*28*3+32)
            with self.assertRaisesRegex(ValueError,'unbound'): build_fp_blob(str(path),33,0)
            with self.assertRaisesRegex(ValueError,'24-bit'): build_fp_blob(str(path),34,0xFFFFFF)
            palette = bytearray((path/'palette.bin').read_bytes())
            palette[8] ^= 1
            (path/'palette.bin').write_bytes(palette)
            with self.assertRaisesRegex(ValueError,'FONT_PALETTE'): build_fp_blob(str(path),34,0)

    def test_clean_bg_runtime_domain_and_reference_guard(self):
        m = dict(normal_frontpanel_removed=True,frontpanel=None,width_tiles=32,
                 height_tiles=28,streaming=True,unique_tiles=1)
        blobs = dict(zip(fp.FILES,(bytes(32),b'\0\0\1'*32*28,bytes(256))))
        full.validate_clean_background(m,blobs,32)
        with patch('stage_water.runtime_tile_id_limit',return_value=0),self.assertRaisesRegex(ValueError,'BG1_ABI'):
            full.validate_clean_background(m,blobs,32)
        blobs['tilemap.bin'] = b'\1\0\1'*32*28
        with self.assertRaisesRegex(ValueError,'BG1_REFERENCE'): full.validate_clean_background(m,blobs,32)

    def test_source_widths_and_branch_reach(self):
        widths,branches,size = source_lint(ROOT/'src/core/stage_frontpanel_bg2.pasm')
        self.assertEqual(widths,[])
        self.assertEqual(branches,[])
        self.assertLess(size,0x6000)

    def test_discontiguous_vram_and_font_boundary(self):
        p = full.layout_proof()
        self.assertEqual(p['slots'][1:129],list(range(0,128)))
        self.assertEqual(p['slots'][129:193],list(range(128,192)))
        self.assertEqual(p['slots'][193:],list(range(192,255)))
        self.assertEqual(p['map_base'],0x6C00)
        self.assertEqual(p['blank_tile'],255)
        self.assertEqual(0x3000+271*16,0x40F0)
        self.assertLessEqual(0x7EE100+34*28*2+257*2+34*2,0x7EF000)
        real = Path.read_bytes
        def enlarged(path):
            return bytes(3586) if path == ROOT/'src/assets/font_tiles.bin' else real(path)
        with patch.object(Path,'read_bytes',enlarged),self.assertRaisesRegex(ValueError,'FONT_VRAM_OVERLAP'):
            full.layout_proof()

    def test_4bpp_lowering_exact_palette_flip_and_transparency_pixels(self):
        tile = np.arange(64,dtype=np.uint8).reshape(8,8)%4
        tiles_bin = st.encode_tileset([tile],bpp=2)
        source = [(0,1+i%3,bool(i&1),bool(i&2)) for i in range(28*4)]
        blobs = dict(zip(fp.FILES,(tiles_bin,st.encode_tilemap_column_major(source,4,28),bytes(32))))
        lowered = fp.lower_bg2(blobs,4,4)
        dest = st.decode_tilemap_column_major(lowered['tilemap_bin'],4,28)
        data = lowered['tiles_bin']
        for old,new in zip(source,dest):
            _,pal,hf,vf = old
            expected = tile
            if hf: expected = expected[:,::-1]
            if vf: expected = expected[::-1,:]
            expected = np.where(expected == 0,0,pal*4+expected)
            tid,pal,hf,vf = new
            actual = st.decode_4bpp_tile(data[tid*32:tid*32+32])
            if hf: actual = actual[:,::-1]
            if vf: actual = actual[::-1,:]
            self.assertEqual(pal,0)
            np.testing.assert_array_equal(actual,expected)

    def test_queue_and_display_ownership_are_explicit(self):
        code = (ROOT/'src/core/stage_frontpanel_bg2.pasm').read_text()
        play = code.split('StageFp_BG2PlayDispatch:',1)[1].split('StageFp_BG2CommitDispatch:',1)[0]
        self.assertLess(play.index('sta.l Nmi_FrameBusy'),play.index('jsr StageFp_BG2Resolve'))
        self.assertIn('ora.l StageFp_BG2DmaPending',play)
        commit = code.split('StageFp_BG2CommitDispatch:',1)[1]
        self.assertIn('sta.l StageFp_BG2DmaPending',commit)
        self.assertIn('jsr StageFp_BG2WriteColumn',commit)
        self.assertNotIn('$00435',code)  # no HDMA needed for dedicated BG2
        self.assertIn('lda.l StageFp_BG2Refs,x',code.split('StageFp_BG2Allocate:')[1])


if __name__ == '__main__': unittest.main()
