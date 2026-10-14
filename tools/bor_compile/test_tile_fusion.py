from __future__ import annotations
import random
import unittest
from tile_fusion import fuse, tile_routine, row_reference, source_stream_reference, TransformError
from assemble_sanity import audit_asm
from baseline_row_kernel import emit as original_emit

class TileFusionTests(unittest.TestCase):
    def test_scalar_exact_opaque_foreground_all_masks(self):
        rng=random.Random(6231)
        for _ in range(10000):
            bg=rng.randbytes(80)
            actor=[(rng.randrange(256),rng.randbytes(10)) for _ in range(8)]
            fg=rng.randbytes(8)
            observed=row_reference(bg,actor,fg)
            for r,(m,pixels) in enumerate(actor):
                mask=m & (~fg[r]&255)
                for plane in range(5):
                    pos=plane*16+2*r
                    for b in range(2):
                        original=bg[pos+b]
                        expected=original ^ ((original^pixels[2*plane+b])&mask)
                        self.assertEqual(observed[pos+b],expected)
    def test_y_clipping_matches_direct_source_index(self):
        rng=random.Random(9931)
        for n in (1,2,7,8,9,15,24,118,179):
            rows=[(rng.randrange(256),rng.randbytes(10)) for _ in range(n)]
            for sy in range(-15,n+10):
                bg=rng.randbytes(80);fg=rng.randbytes(8)
                expected=[rows[y] if 0<=y<n else (0,bytes(10)) for y in range(sy,sy+8)]
                self.assertEqual(source_stream_reference(rows,12,sy,fg,bg),row_reference(bg,expected,fg))
    def test_source_pointer_clamping_in_generator(self):
        asm='\n'.join(tile_routine())
        # The original skips pointer advancement while source y is negative.
        for x in ['bmi AstraTileNegative','adc $48','adc #10','adc #0',
                  ' inc $56',' inc $54','AstraTileRow:',' cmp #8',' rtl']:
            self.assertIn(x,asm)
        self.assertEqual(asm.count(' php'),1)
        self.assertEqual(asm.count(' phy'),1)
        self.assertEqual(asm.count(' ply'),1)
        self.assertEqual(asm.count(' jsl AstraOpaqueRow'),0)
        self.assertEqual(asm.count(' jsr OnlineRowMask'),0)
        self.assertEqual(asm.count(' jsr OnlineStepRow'),0)
        self.assertEqual(asm.count(' sta.l $42D6C0,x'),3)
        for label in ['AstraTileMixed:','AstraTileCopyBack:','AstraTileCopySource:']:
            self.assertIn(label,asm)
    def test_all_three_plane_paths_byte_operations_match_proven_row_kernel(self):
        fused=tile_routine()
        original=original_emit().assembly.splitlines()
        pieces=(('AstraMixed:','AstraCopyBack:','AstraTileMixed:','AstraTileCopyBack:'),
                ('AstraCopyBack:','AstraCopySource:','AstraTileCopyBack:','AstraTileCopySource:'),
                ('AstraCopySource:','AstraDone:','AstraTileCopySource:','AstraTilePixelDone:'))
        for os,oe,fs,fe in pieces:
            old=original[original.index(os)+1:original.index(oe)]
            new=fused[fused.index(fs)+1:fused.index(fe)]
            def normalized(seq):
                return [x.strip() for x in seq if x.strip() not in ('.a16','.i16')
                        and not x.lstrip().startswith(('brl ', 'bne '))]
            self.assertEqual(normalized(new),normalized(old))

    def test_emitted_branch_reach_and_layout(self):
        report=audit_asm()
        self.assertEqual(report["start"],0xE200)
        self.assertGreater(report["bytes"],200)
        self.assertLess(report["end"],0xF000)

    def test_fail_closed_transform_on_exact_synthetic_anchor(self):
        prefix=['OnlineComposeTile:', '.a16','.i16', ' lda $18',' asl a',' tax',
                ' lda.l $42C000,x',' sta $2C',' jsr OnlineRowPointers']
        lines=[*prefix,' lda #0',' sta $1E','OnlineRow:','.a16','.i16',
               ' jsr OnlineRowMask',' lda $1E',' asl a',' tax',' jsl AstraOpaqueRow',
               ' jsr OnlineStepRow',' inc $1E',' lda $1E',' cmp #8',' bcc OnlineRow',
               'OnlineEncode:','.a16','.i16','OnlineTransfer:', '.org $E000', '.org $F000']
        result=fuse(lines)
        self.assertEqual(result.count(' jsl AstraOpaqueTile'),1)
        self.assertEqual(result.count('AstraOpaqueTile:'),1)
        self.assertIn('AstraTileRow:',result)
        self.assertLess(result.index('AstraOpaqueTile:'),result.index('.org $F000'))
        with self.assertRaises(TransformError):fuse(result)
        with self.assertRaises(TransformError):fuse([x for x in lines if x!=' jsr OnlineRowMask'])
        with self.assertRaises(TransformError):fuse([x for x in lines if x!='OnlineComposeTile:'])

if __name__=='__main__':unittest.main()
