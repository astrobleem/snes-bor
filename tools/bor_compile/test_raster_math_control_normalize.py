import copy,hashlib,json,unittest
import numpy as np
from raster_math_control_normalize import normalize
from raster_math_windows import compile_mask,evaluate
from raster_obj_math_cover import apply_math
from raster_obj_compact import unpack
from raster_slot_greedy import demand
import test_raster_slot_layout as fixtures


class MathControlNormalizeTests(unittest.TestCase):
    def inputs(self):
        source=fixtures.SlotLayoutTests().schedule();source['pieces'][1]['bank']=5
        for row in source['trace']:
            row['resident_before'][5],row['resident_before'][1]=row['resident_before'][1],row['resident_before'][5]
            for event in row['updates']:
                if event['bank']==1:event['bank']=5
        source['trace'][0]['updates'].append(dict(bank=5,slot=3,old=None,color=50))
        for y in(1,2):source['trace'][y]['resident_before'][5][2]=50
        source['trace'][2]['updates'][-1]['old']=50
        image=unpack(source['piece_pixel_masks'][1]);image[0,:5]=3;flat=image.flatten()
        source['piece_pixel_masks'][1]['pixels_hex']=(flat[::2]|flat[1::2]<<4).tobytes().hex()
        window=dict(bounds=[[9,9],[11,11]],wobjsel_color_bits=0xf0,wobjlog_color_bits=4)
        source.update(color_math='additive',scanline_math_controls_source_bound=True,selected_modes={'0':'add','1':'subtract','2':'half-subtract'},compiled_color_window_descriptors={'0':window,'2':compile_mask([False]*256)})
        background=np.full((16,256),10,dtype=np.uint16);expected=background.copy();_,_,pixels=demand(source)
        for piece,image in zip(source['pieces'],pixels):
            for ly,lx in zip(*np.where(image>=0)):
                y,x=int(piece['y']+ly),int(piece['x']+lx);color=int(image[ly,lx]);d=source['compiled_color_window_descriptors'].get(str(y));enabled=d is None or evaluate(d,x)
                expected[y,x]=apply_math(color,int(background[y,x]),source['selected_modes'].get(str(y),'add'))if piece['bank']>=4 and enabled else color
        source['source_rgb555_sha256']=hashlib.sha256(expected.astype('<u2').tobytes()).hexdigest()
        return source,background,expected

    def test_fixed_negative_windows_and_opaque_zero_preserve_complete_context(self):
        source,bg,expected=self.inputs();result=normalize(source,bg,expected,'negative')
        self.assertEqual(result['pieces'],source['pieces']);self.assertEqual(result['trace'],source['trace']);self.assertEqual(result['piece_pixel_masks'],source['piece_pixel_masks'])
        self.assertEqual(result['math_control_normalization']['union_fallback_rows'],[])
        self.assertEqual({d['wobjsel_color_bits']for d in result['compiled_color_window_descriptors'].values()},{0xf0})
        self.assertEqual({d['wobjlog_color_bits']for d in result['compiled_color_window_descriptors'].values()},{4})
        self.assertEqual(result['selected_modes']['1'],'add')
        self.assertEqual(expected[2,8],0);self.assertNotEqual(unpack(result['piece_pixel_masks'][1])[2,0],0)
        self.assertTrue(result['math_control_normalization']['complete_source_pixel_identity_verified'])
        self.assertFalse(result['math_control_normalization']['native_timing_admitted'])

    def test_failed_positive_union_keeps_verified_inverted_descriptor(self):
        source,bg,expected=self.inputs();result=normalize(source,bg,expected,'positive')
        self.assertEqual(result['math_control_normalization']['union_fallback_rows'],[0])
        self.assertEqual(result['compiled_color_window_descriptors']['0'],source['compiled_color_window_descriptors']['0'])
        self.assertTrue(result['math_control_normalization']['complete_source_pixel_identity_verified'])

    def test_stale_context_and_false_input_pixel_identity_fail_explicitly(self):
        source,bg,expected=self.inputs();wrong=expected.copy();wrong[0,0]^=1
        with self.assertRaisesRegex(ValueError,'CONTEXT_IDENTITY'):normalize(source,bg,wrong)
        with self.assertRaisesRegex(ValueError,'INPUT_PIXEL_IDENTITY'):normalize(source,bg+1,expected)


if __name__=='__main__':unittest.main()
