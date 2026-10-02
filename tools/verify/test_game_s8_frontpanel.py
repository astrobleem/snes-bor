"""Offline only: no session, ROM build, shared asset generation, or emulator."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import struct
import hashlib
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np
import game_s8_frontpanel as probe


class FrontpanelProbeTests(unittest.TestCase):
    def test_session_preserves_cold_launch_observer_and_restores_reset(self):
        calls=[]
        def reset():calls.append('reset')
        m=SimpleNamespace(reset_emulator=reset)
        @contextlib.contextmanager
        def opened(*args,**kwargs):
            calls.append(('open',kwargs['stderr_log']))
            try:yield m
            finally:calls.append('close')
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            with patch('game_s8_frontpanel.journal_script',return_value='-- observer'), \
                 patch('_harness.open_session',side_effect=opened), \
                 patch('game_s8_frontpanel.observer_status',return_value=dict(phase='ready',frames=2,callbacks=0)):
                with probe.session({},folder) as live:
                    live.reset_emulator()
                    self.assertNotIn('reset',calls)
                self.assertIs(m.reset_emulator,reset)
                m.reset_emulator()
                self.assertEqual(calls,[('open',folder/'mesen.log'),'close','reset'])

    def test_lua_integer_fields_have_explicit_decimal_format(self):
        symbols={label:0x018000 for label in probe.EVENTS.values()}
        for name in ('Game_StageIndex','Nmi_FrameBusy','StageFp_BG2Booting',
                     'StageFp_BG2DmaPending','StreamScrollFp_ColPending',
                     'StageFp_BG2Fault','StageFp_BG2TileBuf','StageFp_BG2ColBuf'):
            symbols[name]=0x7EE020
        script=probe.journal_script(symbols,Path('events.txt'))
        self.assertIn("string.format('%.0f',rd(a,i==1 and 2 or 1))",script)

    def fixture(self,lo=31):
        tile=np.arange(64,dtype=np.uint8).reshape(8,8)%4
        tile=np.array([0,5,10,15],dtype=np.uint8)[tile]
        tiles=probe.st.encode_tileset([tile],bpp=4)
        entries=[(0,0,bool(x&1),bool(y&1)) for y in range(28) for x in range(3)]
        palette=bytearray(32);palette[12:14]=b'\xff\x7f'
        palette[20:22]=b'\x1f\0';palette[30:32]=b'\xe0\x03'
        media=dict(width=3,period=3,tiles=tiles,tilemap=probe.st.encode_tilemap_column_major(entries,3,28),
            palette=bytes(palette),slot_map=[255,0],font_tiles=bytes(range(16)))
        s=dict(StageFp_BG2Map=0x6C00,StageFp_BG2Char=0x3000,FONT_TILES_VRAM_WORD=0x2900)
        vram=bytearray(65536);cgram=bytearray(512);cgram[:32]=palette
        vram[0x5200:0x5210]=media['font_tiles'];vram[0x6000:0x6020]=tiles
        for col in range(lo,lo+33):
            for row in range(28):
                _,_,hf,vf=entries[row*3+col%3]
                word=0|0x2000|(0x4000 if hf else 0)|(0x8000 if vf else 0)
                addr=(0x6C00+(col&31)+(1024 if col&32 else 0)+row*32)*2
                vram[addr:addr+2]=word.to_bytes(2,'little')
        return vram,cgram,media,s

    def test_pixel_oracle_all_rows_page_boundary_cycle_flips_and_font(self):
        v,c,m,s=self.fixture()
        proof,image=probe.pixel_oracle(v,c,m,31,63,31*8+7,s)
        self.assertEqual(proof['resident_pixels'],59136)
        self.assertGreater(proof['upper_opaque_pixels'],0)
        self.assertEqual(image.shape,(224,256,4))
        self.assertEqual(set(np.unique(image[:,:,3])),{0,255})

    def test_corrupt_palette_font_priority_slot_and_tile_fail(self):
        for name in ('palette','font','priority','slot','tile'):
            with self.subTest(name=name):
                v,c,m,s=self.fixture()
                if name=='palette':c[12]^=1
                if name=='font':v[0x5200]^=1
                if name=='priority':v[(0x6C00+31)*2+1]^=0x20
                if name=='slot':v[(0x6C00+31)*2]^=1
                if name=='tile':v[0x6000]^=1
                with self.assertRaises(AssertionError):probe.pixel_oracle(v,c,m,31,63,248,s)

    def test_camera_bounds_fail_closed(self):
        v,c,m,s=self.fixture()
        for lo,hi,x in ((31,62,248),(31,63,247),(31,63,257)):
            with self.assertRaises(AssertionError):probe.pixel_oracle(v,c,m,lo,hi,x,s)

    def event(self,kind,busy=0,boot=0,dma=0,column=0,fault=0,buffers=None):
        a,b=buffers or ('00'*64,'00'*56)
        return f'{kind} 22 {busy} {boot} {dma} {column} {fault} {a} {b}\n'

    def test_lease_journal_pending_skip_and_commit(self):
        e=self.event
        text=e('boot',boot=1)+e('resolve',busy=1)+e('producer_done',busy=1,dma=1)+e('skipped',dma=1)+e('commit',dma=1)
        proof=probe.check_journal(text,[22])
        self.assertEqual(proof['committed_pending'],1)
        self.assertEqual(proof['skipped_nmi_verdict'],'OBSERVED_PASS')
        proof=probe.check_journal(text.replace(e('skipped',dma=1),''),[22])
        self.assertEqual(proof['skipped_nmi_verdict'],'NOT_OBSERVED_NOT_CLAIMED')

    def test_missing_lease_pending_overwrite_unfinished_and_empty_trace_fail(self):
        e=self.event
        traces=[e('boot')+e('resolve'),
            e('boot')+e('resolve',busy=1,dma=1),
            e('boot')+e('resolve',busy=1)+e('producer_done',busy=1,dma=1)+e('commit',dma=1,buffers=('11'*64,'00'*56)),
            e('boot')+e('resolve',busy=1)+e('producer_done',busy=1,dma=1),
            e('boot')+e('resolve',busy=1)+e('producer_done',busy=1,column=1)+e('commit',column=1),
            e('boot'), 'OVERFLOW\n']
        for text in traces:
            with self.subTest(text=text[:40]),self.assertRaises(AssertionError):probe.check_journal(text,[22])

    def test_lua_is_read_only_and_fixture_allowlist_excludes_render_state(self):
        names=list(probe.EVENTS.values())+['Game_StageIndex','Nmi_FrameBusy','StageFp_BG2Booting',
            'StageFp_BG2DmaPending','StreamScrollFp_ColPending','StageFp_BG2Fault','StageFp_BG2TileBuf','StageFp_BG2ColBuf']
        symbols={n:0x7E1000+i*128 for i,n in enumerate(names)}
        symbols.update({n:0x128000+i*128 for i,n in enumerate(probe.EVENTS.values())})
        text=probe.journal_script(symbols,Path('events.txt'))
        self.assertNotIn('emu.write',text);self.assertNotIn('breakExecution',text)
        self.assertIn('OVERFLOW',text)
        self.assertIn('emu.callbackType.exec,address,address,emu.cpuType.snes,emu.memType.snesPrgRom',text)
        self.assertIn('[589824]="load"',text)
        self.assertNotIn('[1212416]=',text)  # CPU $128000 is not a PRG-ROM offset
        self.assertIn("heartbeat('loaded')",text);self.assertIn("heartbeat('ready')",text)
        self.assertIn('emu.eventType.endFrame',text)
        self.assertEqual(set(probe.FIXTURE_WRITES),{'Game_CampaignOrdinal','Game_StageIndex','Stage_LoadPending','Game_State'})

    def test_observer_rejects_non_rom_symbols_and_reports_heartbeat(self):
        symbols={n:0x7E1000 for n in probe.EVENTS.values()}
        with self.assertRaisesRegex(ValueError,'LoROM'):probe.journal_script(symbols,Path('events.txt'))
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'events.status'
            self.assertIsNone(probe.observer_status(path))
            path.write_text('loaded 0 0\n')
            self.assertEqual(probe.observer_status(path),dict(phase='loaded',frames=0,callbacks=0))
            path.write_text('ready 120 87\n')
            self.assertEqual(probe.observer_status(path)['callbacks'],87)

    def test_seam_arm_uses_camera_not_lagging_presentation(self):
        boundary=146
        self.assertFalse(probe.seam_capture_due(dict(camera=20,request=28,scroll=32),boundary))
        self.assertTrue(probe.seam_capture_due(dict(camera=36,request=45,scroll=45),boundary))
        # NativeFP01 triggered at displayed136, but camera106 already implies148.
        bad=dict(camera=106,request=140,scroll=136)
        self.assertTrue(probe.seam_capture_due(bad,boundary))
        with self.assertRaisesRegex(AssertionError,'crossed boundary'):probe.require_seam_side(bad,boundary,True)
        # The failed before/after151 pair must remain rejected, not tolerated.
        with self.assertRaises(AssertionError):probe.require_seam_side(dict(camera=108,request=151,scroll=151),boundary,True)
        probe.require_seam_side(dict(camera=84,request=117,scroll=117),boundary,True)
        probe.require_seam_side(dict(camera=108,request=151,scroll=151),boundary,False)
        with self.assertRaises(AssertionError):probe.require_seam_side(dict(scroll=145),boundary,False)

    def test_neutral_override_precedes_settle_and_is_released_on_error(self):
        events=[]
        m=SimpleNamespace(hold_input=lambda value,port:events.append(('hold',value,port)),
                          release_input=lambda port:events.append(('release',port)))
        with probe.neutral_input(m):events.append(('settle',))
        self.assertEqual(events,[('hold',0,0),('settle',),('release',0)])
        events.clear()
        with self.assertRaises(RuntimeError):
            with probe.neutral_input(m):raise RuntimeError('fixture')
        self.assertEqual(events,[('hold',0,0),('release',0)])

    def test_default_no_emulator_and_hash_fail_before_session(self):
        with patch.object(probe,'source_plan',return_value=[]),patch.object(probe,'run') as run,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(probe.main([]),0);run.assert_not_called()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name in ('rom.sfc','rom.msu','symbols.sym','environment.json'):(root/name).write_bytes(b'fixture')
            args=SimpleNamespace(symbols=root/'symbols.sym',environment=root/'environment.json',
                rom_sha256='0'*64,msu_sha256='0'*64,symbols_sha256='0'*64,environment_sha256='0'*64)
            with patch.dict(os.environ,{'BOR_TEST_ROM':str(root/'rom.sfc')}),self.assertRaisesRegex(ValueError,'hash'):
                probe.preflight(args,[])

    def test_packed_fp_header_range_and_bpp_guard(self):
        msu=bytearray(512);msu[:8]=b'BORMSU1\0';msu[10]=1
        struct.pack_into('<I',msu,12,16);struct.pack_into('<I',msu,16+28,64)
        struct.pack_into('<HBBH2xII',msu,64,1,28,4,1,112,196)
        result=probe.packed_fp(msu,0)
        self.assertEqual((result['width'],len(result['tiles'])),(1,32))
        msu[67]=0
        with self.assertRaisesRegex(ValueError,'ABI'):probe.packed_fp(msu,0)

    def test_actual_source_selection_and_four_image_1a(self):
        rows=probe.source_plan()
        self.assertEqual([r['name'] for r in rows],['1a','3b','4b','6b'])
        self.assertEqual([r['stage'] for r in rows],[22,27,30,34])
        self.assertEqual(len(rows[0]['sequence']),4)
        self.assertEqual([x['line'] for x in rows[0]['sequence']],[8,9,10,11])

    def test_full_preflight_binds_rom_msu_metadata_and_rejects_stale_fp(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); fpdir=root/'fp';oracle=root/'oracle';bg=root/'bg'
            for path in (fpdir,oracle,bg):path.mkdir()
            _,_,media,_=self.fixture()
            row=dict(stage=22,direction='right',sequence=[dict(source_path='front.gif',line=1,sha256='source')],
                     source_level_sha256='level')
            manifest=dict(indexed_oracle=str(oracle),target_cycle_width=24)
            (fpdir/'manifest.json').write_text(json.dumps(manifest))
            (oracle/'manifest.json').write_text(json.dumps(dict(sequence_inputs=dict(
                sequence=row['sequence'],source_level_sha256='level'))))
            msu=bytearray(12000);msu[:8]=b'BORMSU1\0';msu[10]=23
            struct.pack_into('<I',msu,12,16);record=16+22*40
            struct.pack_into('<I',msu,record+28,4096)
            struct.pack_into('<HBBH2xII',msu,4096,3,28,4,1,4144,4396)
            blobs=dict(zip(('palette.bin','tilemap.bin','tiles.bin'),
                (media['palette'],media['tilemap'],media['tiles'])))
            for name,offset in [('palette.bin',4112),('tilemap.bin',4144),('tiles.bin',4396)]:
                msu[offset:offset+len(blobs[name])]=blobs[name]
            clean=dict(zip(('palette.bin','tilemap.bin','tiles.bin'),(bytes(256),bytes(84),bytes(32))))
            struct.pack_into('<III',msu,record+12,8000,8256,8340)
            for name,offset in [('palette.bin',8000),('tilemap.bin',8256),('tiles.bin',8340)]:
                (bg/name).write_bytes(clean[name]);msu[offset:offset+len(clean[name])]=clean[name]
            # Exercise the real packer, including its nonzero HUD palette merge.
            from pack_msu_roster import pack_bg_blob,build_bg_record
            import build_rom
            hud=root/'hud';hud.mkdir()
            (bg/'manifest.json').write_text(json.dumps(dict(streaming=True,width_tiles=1,height_tiles=28,unique_tiles=1)))
            (hud/'manifest.json').write_text(json.dumps(dict(tile_count=1)))
            (hud/'hud_palette.bin').write_bytes(bytes(range(32)))
            (hud/'hud_tiles.bin').write_bytes(bytes(range(16)))
            packed,info=pack_bg_blob(str(bg),str(hud))
            msu[8000:8000+len(packed)]=packed
            msu[record:record+40]=build_bg_record(info,8000,fp_offset=4096)
            names=set(probe.EVENTS.values())|set(probe.BYTE_STATE)|set(('StageFp_ModeMap','StageFp_PeriodMap',
                'StageFp_BG2SlotMap','StageFp_BG2TileBuf','StageFp_BG2ColBuf','StageFp_BG2Map',
                'StageFp_BG2Char','StageFp_Request','StreamScrollFp_StagedLo','StreamScrollFp_StagedHi',
                'Font_PaletteData','Font_TilesData','FONT_TILE_BYTES','FONT_TILES_VRAM_WORD',
                'Nmi_Bg2ScrollX','Nmi_Bg2ScrollY','StageFp_BG2ColdInit','StageFp_BG2SceneReset',
                'Bg_LoadSceneFp_Streaming','StageFp_BG2BootDispatch','Core_StreamScrollFp_Play','StageFp_BG2PlayDispatch'))
            s={n:0x8000+i*640 for i,n in enumerate(sorted(names))}
            s['FONT_TILE_BYTES']=16
            rom=bytearray(65536)
            for caller,target in [('Bg_LoadSceneFp_Streaming','StageFp_BG2BootDispatch'),('Core_StreamScrollFp_Play','StageFp_BG2PlayDispatch')]:
                at=probe.pc(s[caller]);rom[at:at+5]=b'\x08\x22'+s[target].to_bytes(3,'little')
            from stage_frontpanel_bg2 import layout_proof
            slots=layout_proof()['slots']
            struct.pack_into(f'<{len(slots)}H',rom,probe.pc(s['StageFp_BG2SlotMap']),*slots)
            struct.pack_into('<H',rom,probe.pc(s['StageFp_PeriodMap'])+44,3)
            rom[probe.pc(s['StageFp_ModeMap'])+22]=1
            at=probe.pc(s['Font_PaletteData']);rom[at:at+8]=media['palette'][8:16]
            at=probe.pc(s['Font_TilesData']);rom[at:at+16]=media['font_tiles']
            paths=dict(rom=root/'candidate.sfc',msu=root/'candidate.msu',symbols=root/'candidate.sym',environment=root/'env.json')
            paths['rom'].write_bytes(rom);paths['msu'].write_bytes(msu)
            paths['symbols'].write_text('\n'.join(f'00:{value:04X} {name}' for name,value in s.items()))
            paths['environment'].write_text(json.dumps(dict(frontpanel_media=[dict(physical=22,frontpanel=str(fpdir),bg=str(bg),
                full_fp_blob_sha256={n:hashlib.sha256(b).hexdigest() for n,b in blobs.items()})])))
            args=SimpleNamespace(symbols=paths['symbols'],environment=paths['environment'],
                **{name+'_sha256':probe.sha(path) for name,path in paths.items()})
            screens=list(build_rom.BG_SCREENS);screens[22]=(str(bg),str(hud))
            with patch.dict(os.environ,{'BOR_TEST_ROM':str(paths['rom'])}),patch.object(build_rom,'BG_SCREENS',screens):
                _,actual,_=probe.preflight(args,[row])
                self.assertEqual(actual[22]['period'],3)
                for offset in (8002,8032,8256,8340,8372):
                    bad=bytearray(msu);bad[offset]^=1
                    with self.subTest(offset=offset),self.assertRaisesRegex(ValueError,'FP-free binding'):
                        probe.check_clean_bg_binding(bad,record,bg,hud)
                bad=bytearray(msu);bad[record+16]^=1
                with self.assertRaisesRegex(ValueError,'schema'):probe.check_clean_bg_binding(bad,record,bg,hud)
                msu[4396]^=1;paths['msu'].write_bytes(msu);args.msu_sha256=probe.sha(paths['msu'])
                with self.assertRaisesRegex(ValueError,'predates/differs'):probe.preflight(args,[row])


if __name__=='__main__':unittest.main()
