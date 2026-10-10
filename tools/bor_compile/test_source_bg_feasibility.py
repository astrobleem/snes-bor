"""Source alpha and lossless BG context checks independent of native output."""
import tempfile
from pathlib import Path
import unittest
from PIL import Image
from compiler import Source
from source_bg_feasibility import probe,rgb555
import numpy as np
from source_profile import document,discover


class BgFeasibilityTests(unittest.TestCase):
    def test_rgb555_widens_byte_channels_before_shifting(self):
        pixels=np.array([[[255,255,255],[0,255,0],[0,0,255],[255,0,0],[0,0,0]]],dtype=np.uint8)
        np.testing.assert_array_equal(rgb555(pixels),[[32767,992,31744,31,0]])
        np.testing.assert_array_equal(rgb555(pixels),rgb555(pixels.astype(np.int32)))

    def test_screen_blend_preserves_source_black_and_transparency(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'data').mkdir()
            palette=[0,0,0,0,0,0,255,0,0]+[0]*759
            fx=Image.new('P',(2,2));fx.putpalette(palette);fx.putdata([1,2,0,2]);fx.save(root/'data/fx.png')
            bg=Image.new('P',(8,8),1);bg.putpalette([0,0,0,0,255,0]+[0]*762);bg.save(root/'data/bg.png')
            (root/'data/models.txt').write_text('load Effect data/effect.txt\n')
            (root/'data/effect.txt').write_text('type none\nalpha 1\nanim idle\nframe data/fx.png\n')
            (root/'data/levels.txt').write_text('set Test\n')
            s=Source(root);docs={k:document(s,n) for k,(n,_) in s.index.items() if k.endswith('.txt')}
            model=discover(s,docs)['models'][0]
            r=probe(s,model,'data/fx.png','data/bg.png',position=(0,0),size=(8,8),capacity=15,bounded=True,prefetch_budget=0)
            self.assertEqual(r['full_frame_colors'],2) # green plus screen(red,green)=yellow
            self.assertTrue(r['pixel_identity_verified'])
            self.assertEqual(r['peak_hblank_writes'],0)
            self.assertTrue(r['no_color_reduction'])
            model['properties']['alpha'][0]['values']=['0']
            with self.assertRaisesRegex(ValueError,'SCREEN_BLEND_SOURCE_REQUIRED'):
                probe(s,model,'data/fx.png','data/bg.png')


if __name__=='__main__':unittest.main()
