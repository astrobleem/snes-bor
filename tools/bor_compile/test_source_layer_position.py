import unittest
from source_layer_position_4086 import placements,legacy_layer

class SourceLayerPositionTests(unittest.TestCase):
    def test_frontpanel_uses_its_own_width_and_source_parallax(self):
        spec=legacy_layer('frontpanel',(700,245),ordinal=2,front_count=5)
        self.assertEqual(placements(**spec,camera=(1000,0),viewport=(256,224)),[(0,0)])
    def test_background_c_remainder_and_repeat_boundary(self):
        spec=legacy_layer('background',(800,400))
        self.assertEqual(placements(**spec,camera=(1600,0),viewport=(256,224)),[(0,0)])
        self.assertEqual(placements(**spec,camera=(1602,0),viewport=(256,224)),[(-1,0)])
    def test_panel_does_not_repeat_past_its_single_authored_span(self):
        spec=legacy_layer('panel',(2544,245))
        self.assertEqual(placements(**spec,camera=(2544,0),viewport=(256,224)),[])
    def test_negative_repeat_requires_source_load_normalization(self):
        spec=legacy_layer('panel',(100,100));spec['repeat']=(-1,1)
        with self.assertRaisesRegex(ValueError,'LAYER_REPEAT_REQUIRES_LOAD_NORMALIZATION'):
            placements(**spec,camera=(0,0),viewport=(256,224))

if __name__=='__main__':unittest.main()
