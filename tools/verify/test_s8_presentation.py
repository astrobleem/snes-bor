"""Offline water/pause proof checks. Synthetic packets test the verifier only;
they are never injected into the runtime or reported as native evidence.
"""
import copy
from dataclasses import asdict
from pathlib import Path
import unittest

from game_s8_presentation import plan, quiescent, frozen, bg1_guard, merge_bg_hud_palette, ROOT
from game_s8_water_observer import check, parse, script
from game_s8_stage_bounds import symbols
from stage_water import WaterMetadata, raster


class PresentationTests(unittest.TestCase):
    def test_actual_source_coverage(self):
        rows=plan()
        self.assertEqual([(r['name'],r['water']['amplitude'],r['water']['rocking']) for r in rows],
                         [('1a',0,False),('3a',15,True),('3b',0,True),('3c',0,True),('4a',2,False)])

    def test_playing_alone_and_stale_bg2_are_not_visible_proof(self):
        s={'GAME_STATE_PLAYING':0,'GAME_STATE_PAUSED':3}
        snap=dict(state=0,stage=22,ppu=dict(forcedBlank=False,brightness=15,bgMode=1,mainScreenLayers=23),
                  pending={'dma':0},dma_active=0,active={'loaded':1,'active':1})
        self.assertTrue(quiescent(snap,22,s))
        for key,value in (('forcedBlank',True),('brightness',0),('mainScreenLayers',0)):
            bad=copy.deepcopy(snap);bad['ppu'][key]=value
            self.assertFalse(quiescent(bad,22,s))
        bad=copy.deepcopy(snap);bad['pending']['dma']=1
        self.assertFalse(quiescent(bad,22,s))
        bad=copy.deepcopy(snap);bad['active']={'loaded':0,'active':0}
        self.assertFalse(quiescent(bad,22,s,fp=False)) # stale enabled hardware BG2
        bad['ppu']['mainScreenLayers']=21
        self.assertTrue(quiescent(bad,22,s,fp=False))

    def test_pause_guards_every_owned_state_not_screenshots(self):
        keys=('water_frame','rock_y','camera','scroll','active_offset','table','hdma','bg1_map','bg2_map','cgram','font')
        before=dict.fromkeys(keys,0);frozen(before,dict(before))
        for key in keys:
            with self.assertRaisesRegex(AssertionError,key):frozen(before,dict(before,**{key:1}))

    def fixtures(self):
        row=WaterMetadata(29,'DATA/NORMAL/4A.TXT',2,False,80)
        base=0x7fb240;rows=[dict(stage=29,name='4a',water=asdict(row))];events=[]
        for phase in (0,40):
            data,y=raster(row,phase,128)
            common=dict(stage=29,state=3,phase=phase,active=0,x=128,y=y,pending=0,held=0,shadow_before=1,shadow=65,
                        table=data.hex(),dma=(bytes((2,13))+base.to_bytes(3,'little')+bytes(6)).hex())
            events.append(dict(common,event='commit'))
            scan=dict(common,event='raster',mask=64,base=128,bus_y=y,arm=2,
                      bus=b''.join(data[i+1:i+3] for i in range(0,672,3)).hex())
            events.append(scan);events.append(dict(scan,state=0,arm=3))
            events.append(dict(event='frame',stage=29,state=0,enabled=1,mask=64))
        events.append(dict(event='oam',stage=29,before=100,after=100,rock=0))
        return events,rows,base

    def test_actual_bus_required_not_just_enabled_table(self):
        events,rows,base=self.fixtures()
        self.assertEqual(check(events,rows,base)[29]['rasters'],4)
        for key,value in (('bus','00'),('mask',0),('bus_y',3),('dma','00'*11),('table','00'*673)):
            bad=copy.deepcopy(events);bad[1][key]=value
            with self.assertRaises(AssertionError):check(bad,rows,base)
        with self.assertRaises(AssertionError):check([e for e in events if e['event']!='raster'],rows,base)

    def test_pause_and_oam_coverage_mandatory(self):
        events,rows,base=self.fixtures()
        for e in events:
            if e['event']=='raster':e['state']=0
        with self.assertRaises(AssertionError):check(events,rows,base)
        events,rows,base=self.fixtures();events[-1]['after']=99
        with self.assertRaisesRegex(AssertionError,'OAM'):check(events,rows,base)

    def test_script_read_only_explicit_callbacks(self):
        lua=script(symbols(ROOT/'src/main.sym'),Path('events.txt'))
        self.assertNotIn('emu.write',lua)
        self.assertNotIn('setState',lua)
        self.assertIn('emu.cpuType.snes,emu.memType.snesPrgRom',lua)
        self.assertIn('emu.callbackType.write,0x210d,0x210d,emu.cpuType.snes,emu.memType.snesMemory',lua)
        self.assertIn('field.bus_y=hardware_y',lua)
        self.assertEqual(parse('raster|stage=29|bus=00ff')[0]['bus'],'00ff')

    def test_bg1_cgram_and_resident_media_guard(self):
        vram=bytearray(65536);palette=bytes(256);tiles=bytes(32)+bytes([7])*32
        # one viewport column, slot1 for every row, with actual tile1 bytes.
        for row in range(28):vram[0xc000+row*64:0xc002+row*64]=b'\1\0'
        vram[32:64]=tiles[32:64]
        media=dict(width=1,palette=palette,tiles=tiles)
        layer=dict(tilemapAddr=0x6000,chrAddr=0)
        self.assertEqual(bg1_guard(vram,bytes(512),b'\xff\xff\1\0',layer,media,0),28)
        vram[32]=8
        with self.assertRaisesRegex(AssertionError,'VRAM'):bg1_guard(vram,bytes(512),b'\xff\xff\1\0',layer,media,0)

    def test_packed_bg_palette_merges_hud_only_into_reserved_slot_zero(self):
        bg=bytes(32)+bytes(range(32,256))
        hud=bytes(range(32))
        packed=merge_bg_hud_palette(bg,hud)
        self.assertEqual(packed[:32],hud)
        self.assertEqual(packed[32:],bg[32:])
        with self.assertRaisesRegex(ValueError,'reserved for HUD'):
            merge_bg_hud_palette(bytes([1])+bytes(255),hud)
        with self.assertRaisesRegex(ValueError,'sizes'):
            merge_bg_hud_palette(bytes(255),hud)


if __name__=='__main__':unittest.main()
