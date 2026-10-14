import pathlib
import random
import tempfile
import unittest
import json
import hashlib
import struct
from phase_occupancy import (compile_occupancy,tile_maybe_covered,
                             slow_from_phase_masks,export)


def make_phase(src,px):
    h=len(src);w=len(src[0]);cols=(w+px+7)//8
    data=bytearray(h*cols*12)
    for y in range(h):
        for x in range(w):
            if not src[y][x]:continue
            off=y*cols*12+((x+px)//8)*12
            word=struct.unpack_from('<H',data,off)[0]
            word |= 257*(1<<(7-(x+px)%8))
            struct.pack_into('<H',data,off,word)
    return bytes(data),cols*12


class TableTests(unittest.TestCase):
    def test_all_alignment_phases_with_sampled_screen_translations(self):
        rng=random.Random(4086)
        total=0
        # Includes sizes of all three *cropped* MOTU sprite source masks,
        # as well as cases that cross a ROM/PPU tile boundary or viewport edge.
        for w,h in [(75,118),(114,116),(64,179),(1,1),(8,8),(17,41)]:
            # Sparse/mid/dense images, always using source transparency as mask.
            src=[[int(rng.random()<.2) for x in range(w)] for y in range(h)]
            for px in range(8):
                raw,stride=make_phase(src,px)
                table,g=compile_occupancy(raw,rows=h,row_stride=stride)
                self.assertEqual(len(table),8*g['cols']*g['tile_rows'])
                for q in range(8):
                    for k in range(2):
                        bx=rng.randrange(-15,10)
                        by=rng.randrange(-16,9)
                        ox=bx*8+px
                        oy=by*8+q
                        for test_tile in range(100):
                            ty=rng.randrange(28)
                            tx=rng.randrange(32)
                            actual=tile_maybe_covered(table,g,origin_x=ox,origin_y=oy,screen_tx=tx,screen_ty=ty)
                            slow=slow_from_phase_masks(raw,rows=h,row_stride=stride,
                                origin_x=ox,origin_y=oy,screen_tx=tx,screen_ty=ty)
                            self.assertEqual(actual,slow,(w,h,ox,oy,tx,ty))
                            total+=1
        print('reference comparisons',total)
    def test_ignoring_foreground_is_safe_superset(self):
        rng=random.Random(21)
        src=[[int(rng.random()<.4) for _ in range(33)] for __ in range(39)]
        # Source presence is calculated separately from full-screen foreground.
        # A fully occluded tile is allowed to be a conservative false positive.
        for px in range(8):
            raw,stride=make_phase(src,px)
            table,g=compile_occupancy(raw,rows=len(src),row_stride=stride)
            for q in range(8):
                ox=-16+px;oy=40+q
                for screen_ty in range(5,15):
                    for screen_tx in range(0,8):
                        source_present=False;effective_visible=False
                        for py in range(screen_ty*8,screen_ty*8+8):
                            for pixel_x in range(screen_tx*8,screen_tx*8+8):
                                sy=py-oy;sx=pixel_x-ox
                                pixel=0<=sy<len(src) and 0<=sx<len(src[0]) and src[sy][sx]
                                # A deterministic varying foreground mask; in other
                                # cases it may cover *every* actor pixel.
                                front=((pixel_x*3+py*11+q)%5)<3
                                source_present |= bool(pixel)
                                effective_visible |= bool(pixel and not front)
                        pred=tile_maybe_covered(table,g,origin_x=ox,origin_y=oy,
                            screen_tx=screen_tx,screen_ty=screen_ty)
                        self.assertEqual(pred,source_present)
                        self.assertFalse(effective_visible and not pred)
    def test_export_hashes_capacity_and_no_asset_changes(self):
        with tempfile.TemporaryDirectory() as t:
            root=pathlib.Path(t);phase=root/'phase';phase.mkdir()
            manifest={'schema':'ASTRA_OPAQUE_PHASE_ASSETS_V1','backdrop_tiles':596,'frames':{}}
            raw,stride=make_phase([[1,0,0,1] for _ in range(6)],0)
            entries=[]
            for px in range(8):
                raw,stride=make_phase([[1,0,0,1] for _ in range(6)],px)
                name=f'walk{px}.bin'; (phase/name).write_bytes(raw)
                entries.append(dict(phase=px,path=name,row_stride=stride,row_count=6,
                                    sha256=hashlib.sha256(raw).hexdigest()))
            manifest['frames']['walk']={'phases':entries}
            (phase/'manifest.json').write_text(json.dumps(manifest))
            before={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in phase.iterdir()}
            result=export(phase,root/'out')
            after={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in phase.iterdir()}
            self.assertEqual(before,after)
            self.assertEqual(result['maximum_required_pairs'],600)
            with self.assertRaises(ValueError):export(phase,root/'out')
            with self.assertRaises(ValueError):export(phase,root/'out2',capacity=599)
    def test_expected_current_source_bounds_table_volume(self):
        # From documented cropped bounds; the user-local manifest is authority.
        total=0
        for width,height in ((75,118),(114,116),(64,179)):
            tile_rows=(height+14)//8
            total+=sum(8*tile_rows*((width+px+7)//8) for px in range(8))
        self.assertEqual(total,39616)
    def test_bad_coverage_word_fails(self):
        with self.assertRaisesRegex(ValueError,'PHASE_MASK_NOT_DUPLICATED'):
            compile_occupancy(b'\x01\x00'+bytes(10),rows=1,row_stride=12)

if __name__=='__main__':unittest.main()
