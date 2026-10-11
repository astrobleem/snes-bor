import unittest
import numpy as np
from raster_geometry_hint import construct
from raster_slot_greedy import demand
from test_raster_retile import fixture


def canvas(source,allow_hint=False):
    image=np.full((len(source['trace']),256),-1,dtype=np.int32);banks=image.copy()
    for p,words in zip(source['pieces'],demand(source,allow_geometry_hint=allow_hint)[2]):
        for y,x in zip(*np.where(words>=0)):
            image[p['y']+y,p['x']+x]=words[y,x];banks[p['y']+y,p['x']+x]=p['bank']
    return image,banks


class GeometryHintTests(unittest.TestCase):
    def test_every_bank_word_and_palette_transition_survives(self):
        source=fixture();hint=construct(source,(3,7))
        self.assertEqual(source['trace'],hint['trace'])
        for a,b in zip(canvas(source),canvas(hint,True)):np.testing.assert_array_equal(a,b)
        self.assertTrue(hint['geometry_search_hint']['source_operands_and_banks_exact'])
        self.assertFalse(hint['hardware_geometry_admitted'])
        self.assertFalse(hint['native_presentation_proven'])

    def test_default_consumers_reject_search_hints(self):
        hint=construct(fixture())
        with self.assertRaisesRegex(ValueError,'GREEDY_VALIDATED_SOURCE'):demand(hint)
        hint['native_presentation_proven']=True
        with self.assertRaisesRegex(ValueError,'GREEDY_VALIDATED_SOURCE'):demand(hint,allow_geometry_hint=True)

    def test_invalid_origin_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'GEOMETRY_HINT_ORIGIN'):construct({},(0,8))


if __name__=='__main__':unittest.main()
