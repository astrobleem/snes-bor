import copy,unittest
import numpy as np
from m4_authored_obj_alpha_rows_native import compile_row
from raster_slot_greedy import demand
from raster_math_windows import compile_mask
from raster_obj_math_cover import apply_math,MODES
from test_raster_slot_greedy import source_schedule


class NativeAlphaRowCompileTests(unittest.TestCase):
    def test_exact_static_row_words_windows_and_math_modes(self):
        source=source_schedule();source['pieces'][1]['bank']=5
        for row in source['trace']:
            row['resident_before'][5]=row['resident_before'][1];row['resident_before'][1]=[None]*15
            for e in row['updates']:
                if e['bank']==1:e['bank']=5
        _,_,words=demand(source);state={b:[None]*15 for b in range(8)};states=[]
        for row in source['trace']:
            for e in row['updates']:state[e['bank']][e['slot']-1]=e['color']
            states.append(copy.deepcopy(state))
        background=np.full((16,256),10<<5,dtype=np.uint16)
        descriptor=compile_mask([16<=x<=24 for x in range(256)])
        for mode in MODES:
            complete=background.copy()
            for p,image in zip(source['pieces'],words):
                for x,c in enumerate(image[0]):
                    if c<0:continue
                    xx=p['x']+x
                    complete[0,xx]=apply_math(int(c),int(background[0,xx]),mode)if p['bank']>=4 and 16<=xx<=24 else c
            raw,expected,palette,oam,bgchr,mapping,objchr,report=compile_row(source,0,background,complete,states,{0:mode},{0:descriptor})
            self.assertEqual(len(raw),262144)
            self.assertEqual(report['source_obj_pixels'],30)
            np.testing.assert_array_equal(expected[0],complete[0])
            np.testing.assert_array_equal(expected[1:],background[1:])
            self.assertEqual(palette[2*(128+5*16+2):2*(128+5*16+3)],b'\x01\x00')
            self.assertEqual((oam[7]>>1)&7,5)
            self.assertIn([0x2131,0x10|{'add':0,'half-add':0x40,'subtract':0x80,'half-subtract':0xc0}[mode]],report['expected_register_writes'])


if __name__=='__main__':unittest.main()
