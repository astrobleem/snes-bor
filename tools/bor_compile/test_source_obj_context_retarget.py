import copy,unittest
from unittest.mock import patch
import numpy as np
from source_obj_context_retarget import retarget


class RetargetTests(unittest.TestCase):
    def fixture(self):
        layer=dict(kind='actor:source-effect',sha256='frame',source_dimensions=[8,8],source_flip=False,requested_map=0,selected_map=0,palette_asset_sha256='palette',alpha=1)
        piece=dict(actor=0,bank=0,x=0,y=0,local_x=0,local_y=0,width=8,height=8,rows={0:[31]},allowed_banks=[0,1,2,4,5,6,7])
        state={b:[None]*15 for b in range(8)};trace=[]
        for y in range(224):
            row=dict(scanline=y,resident_before=copy.deepcopy(state),updates=[])
            if not y:row['updates']=[dict(bank=0,slot=1,old=None,color=31)];state[0][0]=31
            trace.append(row)
        seed=dict(status='JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN',compiled_pixel_identity_verified=True,pieces=[piece],piece_pixel_masks=[dict(width=8,height=8,pixels_hex='01'+'00'*31)],trace=trace,metadata=dict(layers=[layer]))
        actors=[]
        for left,color,metadata in [(8,992,dict(kind='actor:source-player')),(0,31,copy.deepcopy(layer))]:
            pixels=np.full((8,8),-1,dtype=np.int32);pixels[0,0]=color
            actors.append(dict(pixels=pixels,left=left,top=0,metadata=metadata))
        background=np.zeros((224,256,3),dtype=np.uint8);expected=background.copy();expected[0,0,0]=248;expected[0,8,1]=248
        return seed,actors,background,expected

    def run_fixture(self,seed,actors,background,expected,mapping=None):
        with patch('source_obj_context_retarget.prepare',return_value=(actors,{},expected)),patch('source_obj_context_retarget.compose_rgb8',return_value=(background,{})):
            return retarget(None,None,{},seed,{0:1}if mapping is None else mapping,[[3],[0,1,2,4,5,6,7]],time_limit=3)

    def test_additional_actor_and_source_effect_replay_without_input_mutation(self):
        seed,actors,background,expected=self.fixture();before=copy.deepcopy(seed)
        result=self.run_fixture(seed,actors,background,expected)
        self.assertEqual(seed,before)
        self.assertEqual(result['status'],'JOINT_ENCODING_FIXED_OAM_SLOT_SCHEDULE_PROVEN')
        self.assertEqual(result['source_visible_opaque_pixels'],2)
        self.assertTrue(all(p['bank']==3 for p in result['pieces']if p['actor']==0))
        self.assertFalse(result['live_compositor_admitted'])

    def test_wrong_source_identity_and_uncovered_visible_pixel_fail_explicitly(self):
        seed,actors,background,expected=self.fixture()
        actors[1]['metadata']['sha256']='other'
        with self.assertRaisesRegex(ValueError,'SOURCE_ACTOR_IDENTITY'):self.run_fixture(seed,actors,background,expected)
        actors[1]['metadata']['sha256']='frame';actors[1]['pixels'][0,1]=31
        with self.assertRaisesRegex(ValueError,'PIXEL_AND_TRANSPARENCY_IDENTITY'):self.run_fixture(seed,actors,background,expected)
        with self.assertRaisesRegex(ValueError,'ACTOR_MAP'):self.run_fixture(seed,actors,background,expected,{0:2})


if __name__=='__main__':unittest.main()
