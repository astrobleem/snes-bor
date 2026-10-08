"""Source-authority palette decoding; no production asset generation."""
from pathlib import Path
import tempfile
import unittest

from PIL import Image
from compiler import Source
from source_palette import read_palette,model_palettes,select_model_palette
from source_profile import document,discover


class SourcePaletteTests(unittest.TestCase):
    def test_model_png_palette_and_alternate_indices_are_source_owned(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/'data').mkdir()
            base=[0,0,0,255,0,0,0,255,0]+[0]*759
            alt=[0,0,0,0,0,255,255,255,255]+[0]*759
            for name,palette in [('first.png',base),('alt.png',alt)]:
                image=Image.new('P',(2,1));image.putpalette(palette);image.putdata([1,2]);image.save(root/'data'/name)
            (root/'data/models.txt').write_text('load Hero data/hero.txt\n')
            (root/'data/levels.txt').write_text('set Test\n')
            (root/'data/hero.txt').write_text('type player\nalternatepal data/alt.png\nanim idle\nframe data/first.png\n')
            source=Source(root)
            docs={k:document(source,n) for k,(n,_) in source.index.items() if k.endswith('.txt')}
            model=discover(source,docs)['models'][0]
            result=model_palettes(source,model)
            self.assertEqual(result['base']['rgb555'][:3],[0,31,31<<5])
            self.assertEqual(result['alternates'][0]['map'],1)
            self.assertEqual(result['alternates'][0]['rgb555'][:3],[0,31<<10,32767])
            self.assertEqual(result['base']['inference'],'first frame of first animation')
            self.assertNotEqual(result['base']['colors_sha256'],result['alternates'][0]['colors_sha256'])
            self.assertFalse((root/'data/pal.act').exists())

    def test_source_unsigned_map_selection(self):
        base=dict(source_path='base');alternate=dict(map=1,source_path='alt')
        palettes=dict(base=base,alternates=[alternate])
        self.assertEqual(select_model_palette(palettes,1),(alternate,1))
        for index in [0,-1,-2147483648,2,4294967295]:
            self.assertEqual(select_model_palette(palettes,index),(base,0))
        with self.assertRaisesRegex(ValueError,'MODEL_PALETTE_MAP_UINT32_DOMAIN'):
            select_model_palette(palettes,4294967296)

    def test_act_extent_fails_before_palette_substitution(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'bad.act';path.write_bytes(bytes(767))
            with self.assertRaisesRegex(ValueError,'MODEL_PALETTE_ACT_EXTENT'):
                read_palette(Source(temp),'bad.act')

    def test_palette_none_keeps_per_frame_policy_explicit(self):
        result=model_palettes(None,dict(source_path='hero.txt',animations=[],
            properties={'palette':[dict(line=2,values=['none'])]}))
        self.assertEqual(result['policy'],'SOURCE_PER_FRAME')
        self.assertIsNone(result['base'])


if __name__=='__main__':
    unittest.main()
