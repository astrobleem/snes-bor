import copy,unittest
from unittest.mock import patch
import numpy as np
from raster_retile import retile
from raster_slot_greedy import demand
from test_raster_slot_greedy import source_schedule


def fixture():
    source=source_schedule()
    for p in source['pieces']:p.update(actor=0,local_x=p['x'],local_y=p['y'])
    return source


def canvas(source):
    image=np.full((len(source['trace']),256),-1,dtype=np.int32)
    classes=image.copy()
    for p,words in zip(source['pieces'],demand(source)[2]):
        for y,x in zip(*np.where(words>=0)):
            image[p['y']+y,p['x']+x]=words[y,x];classes[p['y']+y,p['x']+x]=p['bank']//4
    return image,classes


class RetileTests(unittest.TestCase):
    def test_cross_bank_retile_preserves_every_word_and_opaque_zero(self):
        source=fixture();result=retile(source,(3,7),0,5)
        for a,b in zip(canvas(source),canvas(result)):np.testing.assert_array_equal(a,b)
        self.assertTrue(result['operand_retile']['source_operand_identity_verified'])
        self.assertFalse(result['operand_retile']['native_timing_admitted'])
        self.assertTrue(np.any(canvas(result)[0]==0))
        self.assertTrue(all(p['width']==p['height']==8 for p in result['pieces']))

    def test_math_class_and_explicit_bank_restrictions_survive(self):
        source=fixture();source['pieces'][1]['bank']=5
        for row in source['trace']:
            row['resident_before'][5]=row['resident_before'][1];row['resident_before'][1]=[None]*15
            for e in row['updates']:
                if e['bank']==1:e['bank']=5
        result=retile(source,(3,7),0,5)
        for a,b in zip(canvas(source),canvas(result)):np.testing.assert_array_equal(a,b)
        bad=fixture();bad['pieces'][0]['allowed_banks']=[0];bad['pieces'][1]['allowed_banks']=[1]
        with self.assertRaisesRegex(ValueError,'RETILE_NO_COMPATIBLE_BANK'):retile(bad,(3,7))

    def test_invalid_origin_and_failed_bank_search_cannot_claim_schedule(self):
        for origin in ((8,0),(-1,0),(0,),('0',0)):
            with self.assertRaisesRegex(ValueError,'RETILE_DOMAIN'):retile({},origin)
        with patch('raster_retile.assign_banks',return_value=dict(status='SOLVER_LIMIT')):
            result=retile(fixture())
        self.assertEqual(result['status'],'RETILE_BANK_ASSIGNMENT_NO_CANDIDATE')
        self.assertFalse(result['universal_raster_rejected'])
        self.assertNotIn('compiled_pixel_identity_verified',result)

    def test_geometry_overflow_is_reported_before_bank_search(self):
        source=fixture();source['pieces']=[];source['piece_pixel_masks']=[]
        for x in range(0,256,8):
            for bank,lx in((0,0),(1,1)):
                image=np.zeros((8,8),dtype=np.uint8);image[0,lx]=1
                flat=image.flatten()
                source['pieces'].append(dict(actor=0,local_x=x,local_y=0,x=x,y=0,width=8,height=8,bank=bank))
                source['piece_pixel_masks'].append(dict(width=8,height=8,pixels_hex=(flat[::2]|flat[1::2]<<4).tobytes().hex()))
        for row in source['trace']:
            row['resident_before'][5]=row['resident_before'][1];row['resident_before'][1]=[None]*15
            for e in row['updates']:
                if e['bank']==1:e['bank']=5
        for p in source['pieces']:
            if p['bank']==1:p['bank']=5
        with patch('raster_retile.assign_banks')as solve:
            result=retile(source)
        solve.assert_not_called()
        self.assertEqual(result['status'],'RETILE_HARDWARE_GEOMETRY_LIMIT')
        self.assertEqual(result['geometry']['peak_sprites'],64)
        self.assertFalse(result['universal_raster_rejected'])


if __name__=='__main__':unittest.main()
