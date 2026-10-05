"""Source pixel fidelity and the measured multi-pose residency regression."""
import io
import json
import struct
import unittest
from PIL import Image
from compiler import ROOT,Source


class BonusVisualTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=json.loads((ROOT/'src/generated/production_source_visual.json').read_text())
        cls.source=Source(ROOT/'Beats of Rage Original [v.3.0 Build 4086].pak')

    def test_source_sized_new_identities_have_no_legacy_fallback(self):
        summary=self.catalog['summary']
        self.assertEqual(summary['legacy_fixed_entries'],0)
        self.assertEqual(summary['blocker_count'],0)
        for roster,count in ((47,9),(48,504)):
            entries=[e for e in self.catalog['entries'] if e['roster']==roster]
            self.assertEqual(len(entries),count)
            for e in entries:
                image=Image.open(io.BytesIO(self.source.read(e['source_path'])))
                self.assertEqual(e['dimensions'],list(image.size))

    def test_shared_layout_is_lossless_under_existing_rgb555_adapter(self):
        entries={e['source_path']:e for e in self.catalog['entries'] if e['roster']==28 and e['map']==0}
        palette=self.source.read('DATA/PAL.ACT')
        for path,e in entries.items():
            image=Image.open(io.BytesIO(self.source.read(path)));width,height=image.size
            actual=[None]*(width*height)
            for p in e['pieces']:
                data=bytes.fromhex(e['blocks'][p['resource']]['data'])
                colors=struct.unpack('<16H',bytes.fromhex(e['palettes'][p['palette']]['data']))
                x0,y0=p['source_xy'];w,h=p['size']
                for y in range(h):
                    for x in range(w):
                        offset=((y//8)*(w//8)+x//8)*32+(y%8)*2;mask=1<<(7-x%8)
                        index=sum((1<<plane) for plane,o in enumerate((0,1,16,17)) if data[offset+o]&mask)
                        if not index or x0+x>=width or y0+y>=height:continue
                        cell=(y0+y)*width+x0+x
                        if actual[cell] is not None:self.assertEqual(actual[cell],colors[index])
                        actual[cell]=colors[index]
            expected=[]
            for index in image.getdata():
                r,g,b=palette[index*3:index*3+3]
                expected.append(((r>>3)|((g>>3)<<5)|((b>>3)<<10)) if index else None)
            self.assertEqual(actual,expected,path)
            self.assertEqual(e['dimensions'],list(image.size))
            self.assertEqual(e['palette_cluster']['cgram_aliases'],0)

    def test_measured_live_biker_and_two_death_poses_fit_without_compromise(self):
        entries=self.catalog['entries']
        poses={e['source_path']:e for e in entries if e['roster']==28 and e['map']==0}
        self.assertEqual(len(poses),2)
        biker=next(e for p,e in poses.items() if p.upper().endswith('/BIKER.GIF') or p.upper().endswith('\\BIKER.GIF'))
        motor=next(e for p,e in poses.items() if p.upper().endswith('/MOTOR.GIF') or p.upper().endswith('\\MOTOR.GIF'))
        player=next(e for e in entries if e['roster']==22 and e['role']=='walk' and e['frame']==4 and e['map']==0)
        blocks=set().union(*(e['blocks'] for e in (biker,motor,player)))
        pieces=biker['piece_count']+2*motor['piece_count']+player['piece_count']
        self.assertLessEqual(len(blocks),64)
        self.assertLessEqual(pieces,128)
        self.assertEqual(len(set(biker['palettes'])|set(motor['palettes'])),2)


if __name__=='__main__':unittest.main()
