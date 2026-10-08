import json
from copy import deepcopy
from pathlib import Path
import unittest
import numpy as np
from compiler import Source
from source_hybrid_scene import derive


class HybridScene(unittest.TestCase):
    def test_live_background_palette_replays_every_scrolled_source_pixel(self):
        root=Path(__file__).resolve().parents[2]
        scene=deepcopy(json.loads((root/'docs/receipts/byor-motu-hybrid-source-pose-native.json').read_text())['source_scene'])
        scene['camera']=[1500,0]
        for actor in scene['actors']:actor['position'][0]+=1500
        r,a=derive(Source(root/'Masters of the Universe [v.3.0 Build 4086].pak'),
                   'data/levels/guile2.txt',scene,3,20,fixed_background_policy='scanline_live')
        self.assertIsNotNone(a)
        self.assertEqual(r['background_palette_capability'],'RASTER_BG_SCANLINE_LIVENESS')
        self.assertEqual(r['ordinary_actor_palette_capability'],'STATIC_OBJ_PALETTE')
        self.assertEqual(r['fixed_bg_colors'],3)
        self.assertLessEqual(r['bg_schedule']['peak_bytes'],30)
        palette=np.zeros(256,dtype=np.uint16);palette[:4]=r['low_component_palette']
        for entry in r['bg_schedule']['initial']:palette[entry['slot']]=entry['color']or 0
        reserved=set(r['obj_palette_cgram_reserved']);updates={v['scanline']:v for v in r['bg_schedule']['trace']}
        for y in range(224):
            if y in updates:
                entry=updates[y];slots=list(range(entry['cgram_start'],entry['cgram_start']+len(entry['values'])))
                self.assertFalse(set(slots)&reserved)
                palette[slots]=[c or 0 for c in entry['values']]
            self.assertTrue(np.array_equal(palette[a['high'][y]]+palette[a['low'][y]],a['bg'][y]))

    def test_palette_ownership_and_decoded_obj_geometry_preserve_source_pixels(self):
        root=Path(__file__).resolve().parents[2]
        scene=json.loads((root/'docs/receipts/byor-motu-hybrid-source-pose-native.json').read_text())['source_scene']
        r,a=derive(Source(root/'Masters of the Universe [v.3.0 Build 4086].pak'),
                   'data/levels/guile2.txt',scene,3,20)
        self.assertIsNotNone(a)
        self.assertLessEqual(r['obj_geometry']['oam_entries'],128)
        self.assertLessEqual(r['obj_geometry']['peak_sprites'],32)
        self.assertLessEqual(r['obj_geometry']['peak_slivers'],34)
        self.assertLessEqual(r['obj_chr_bytes'],8192)
        self.assertLessEqual(r['bg_schedule']['peak_bytes'],30)
        reserved=set(r['obj_palette_cgram_reserved']);palette=np.zeros(256,dtype=np.uint16)
        palette[:4]=[0,32,1024,1056]
        for e in r['bg_schedule']['initial']:palette[e['slot']]=e['color'] or 0
        for alias in r['bg_exact_obj_palette_aliases']:
            self.assertIn(alias['slot'],reserved)
            self.assertEqual(int(palette[alias['slot']]),alias['color'])
        updates={e['scanline']:e for e in r['bg_schedule']['trace']}
        for y in range(224):
            if y in updates:
                e=updates[y];slots=range(e['cgram_start'],e['cgram_start']+len(e['values']))
                self.assertFalse(set(slots)&reserved)
                palette[list(slots)]=[c or 0 for c in e['values']]
            self.assertTrue(np.array_equal(palette[a['high'][y]]+palette[a['low'][y]],a['bg'][y]))
        # Independently decode the published OAM and 4bpp atlas. Hardware OBJ
        # order is reversed here so the lowest OAM index wins overlapping pixels.
        output=a['bg'].copy();roi=np.repeat(np.repeat(a['promoted'],8,axis=0),8,axis=1)
        data=a['obj_chr'];oam=a['oam']
        for i in reversed(range(r['native_obj_entries'])):
            x=int(oam[i*4])|(((int(oam[512+i//4])>>((i%4)*2))&1)<<8)
            if x>=256:x-=512
            y=int(oam[i*4+1]);y=y if y<224 else y-256
            base=int(oam[i*4+2]);bank=(int(oam[i*4+3])>>1)&7
            for yy in range(32):
                for xx in range(16):
                    wx=x+xx;wy=y+yy
                    if not 0<=wx<256 or not 0<=wy<224 or roi[wy,wx]:continue
                    tile=base+(yy//8)*16+xx//8;index=0
                    for plane in range(4):
                        raw=int(data[tile*32+(plane//2)*16+(yy%8)*2+plane%2])
                        index|=((raw>>(7-xx%8))&1)<<plane
                    if index:output[wy,wx]=palette[128+bank*16+index]
        self.assertTrue(np.array_equal(output,a['expected']))

    def test_invalid_bank_counts_fail_explicitly(self):
        for count in (0,8):
            with self.assertRaisesRegex(ValueError,'HYBRID_OBJ_BANK_COUNT'):
                derive(None,None,None,count)


if __name__=='__main__':unittest.main()
