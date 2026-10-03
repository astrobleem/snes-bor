"""FP-only tests; actual conversion writes exclusively to temporary outputs."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

from compiler import ROOT
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'tools/bg_converter'))
import build_rom
import stage_water
import stage_frontpanel as fp
import convert_frontpanel as cv
import numpy as np


class FrontpanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.configs = copy.deepcopy(build_rom.STAGE_CONFIGS)
        cls.sources,cls.normal = stage_water.normal_stage_inputs(cls.configs)
        cls.cfg = cls.configs[22]
        cls.source = cls.sources[str(Path(cls.cfg['pak']).resolve())]
        cls.sequence = fp.sequence_directives(cls.source,cls.normal[22])
        cls.paths = [r['source_path'] for r in cls.sequence]
        cls.index = cv.PakIndex(cls.cfg['pak'])

    def test_authored_order_and_pixels_repeat(self):
        self.assertEqual([Path(p.replace('\\','/')).stem.lower() for p in self.paths],
                         ['f00','f01','f02','f03'])
        images,provenance,stride = cv.frontpanel_sequence_geometry(self.index,self.paths)
        self.assertEqual(stride,183)
        actual = cv.composite_frontpanel_sequence(self.index,self.paths,stride*8)
        for n in range(8):
            rgb,mask = images[n%4]
            expected = np.full((240,stride,3),cv.TRANS_RGB,dtype=np.uint8)
            expected[mask[:240]] = rgb[:240][mask[:240]]
            np.testing.assert_array_equal(actual[:,n*stride:(n+1)*stride],expected)
        shifted = cv.composite_frontpanel_sequence(self.index,self.paths,320,scroll_x=190)
        np.testing.assert_array_equal(shifted,actual[:,190:510])
        self.assertEqual([r['sha256'] for r in provenance],[r['sha256'] for r in self.sequence])

    def test_actual_converter_and_cache_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            linked,rows = fp.materialize_normal(self.configs,self.sources,self.normal,
                ROOT/'out/bor_compile_s6/BOR.C',tmp)
            self.assertEqual([r['physical'] for r in rows],[22,27,28,30,33,34,35])
            self.assertEqual(linked[:22],self.configs[:22])
            path = Path(linked[22]['frontpanel'])
            manifest,hashes,resources = fp.validate_materialized(path,self.sequence,408)
            self.assertEqual(manifest['source_cycle_width'],732)
            self.assertEqual(manifest['target_cycle_width'],584)
            self.assertLessEqual(manifest['unique_tiles'],768)
            self.assertLessEqual(resources['worst_unique_tiles'],256)
            self.assertEqual(manifest['sequence_inputs']['sequence'],self.sequence)
            self.assertEqual(manifest['sequence_blob_sha256'],hashes)
            font,binding = cv.normal_font_palette_binding()
            for row in rows:
                data = (Path(row['frontpanel'])/'palette.bin').read_bytes()
                self.assertEqual(data[8:16],b''.join(w.to_bytes(2,'little') for w in font))
                self.assertEqual(json.loads((Path(row['frontpanel'])/'manifest.json').read_text())['font_palette_binding'],binding)
                # Actual post-Core_Text_Init CGRAM is identical to encoder's oracle.
                final = data[:8]+b''.join(w.to_bytes(2,'little') for w in font)+data[16:]
                self.assertEqual(final,data)
            again,cached = fp.materialize_normal(self.configs,self.sources,self.normal,
                ROOT/'out/bor_compile_s6/BOR.C',tmp)
            self.assertEqual(again,linked)
            self.assertTrue(cached[0]['reused'])
            # Corruption must preserve the rejected output and create a retry.
            (path/'palette.bin').write_bytes(bytes(31))
            retry,reports = fp.materialize_normal(self.configs,self.sources,self.normal,
                ROOT/'out/bor_compile_s6/BOR.C',tmp)
            self.assertNotEqual(retry[22]['frontpanel'],str(path.as_posix()))
            self.assertFalse(reports[0]['reused'])
            self.assertEqual((path/'palette.bin').stat().st_size,31)

    def test_runtime_tile_domain_and_resident_cap(self):
        limits = cv.frontpanel_runtime_limits()
        self.assertEqual(limits['tile_ids'],768)
        entries = [(0,1,False,False)]*(32*28)
        for count in (1,768):
            cv.verify_sequence_resources(entries,count,32,limits)
        for count in (0,769,65535):
            with self.assertRaisesRegex(ValueError,'TILE2SLOT'):
                cv.verify_sequence_resources(entries,count,32,limits)
        entries[21*32+1] = (1,1,False,False)
        with self.assertRaisesRegex(ValueError,'RESIDENT'):
            cv.verify_sequence_resources(entries,2,32,dict(limits,usable_slots=1))

    def test_selection_is_declaration_driven_not_stage_name(self):
        renamed = copy.deepcopy(self.normal[22])
        renamed.source_path = 'DATA/LEVELS/NOT_1A.TXT'
        self.assertEqual(fp.sequence_directives(self.source,renamed),self.sequence)
        renamed.directives = [d for d in renamed.directives if d.name != 'frontpanel']
        self.assertEqual(fp.sequence_directives(self.source,renamed),[])

    def test_scalar_default_matches_accepted_easy_bytes(self):
        cfg = self.configs[0]
        old = Path(cfg['frontpanel'])
        meta = json.loads((old/'manifest.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            cv.convert_frontpanel_streaming(cfg['pak'],meta['level_entry'],tmp,
                meta['width_tiles'],frontpanel_y=meta['frontpanel_y'],verbose=False)
            for name in fp.FILES:
                self.assertEqual((Path(tmp)/name).read_bytes(),(old/name).read_bytes(),name)
            self.assertNotIn('frontpanel_sequence',json.loads((Path(tmp)/'manifest.json').read_text()))

    def test_normal_font_palette_pixel_oracle(self):
        font,_ = cv.normal_font_palette_binding()
        trans = cv.st.rgb_to_bgr555(*cv.TRANS_RGB)
        raw = np.full((1,8,8),font[1],dtype=np.uint16)
        raw[0,0,0] = trans
        palettes,indexed,ids,_ = cv.quantize_normal_frontpanel(raw,trans)
        self.assertEqual(palettes[0],font)
        self.assertEqual(indexed[0,0,0],0)
        self.assertEqual(ids[0],0)  # exact fixed-font color wins the tie
        actual_cgram = [0]*4+font+list(palettes[1])+list(palettes[2])
        for y in range(8):
            for x in range(8):
                if x or y:
                    self.assertEqual(actual_cgram[(int(ids[0])+1)*4+int(indexed[0,y,x])],font[1])


if __name__ == '__main__':
    unittest.main()
