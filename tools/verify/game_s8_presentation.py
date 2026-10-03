#!/usr/bin/env python3
"""Prepared Normal hardware presentation probe; no emulator without --run.

Main runs serially AFTER FP integration. BOR_TEST_ROM and three accepted
artifact hashes are required. Legal startup, then explicit source-predecessor
handoffs to 3B/4B/6B; this is NOT campaign progression or visual acceptance.
Screenshots require repeated committed/unblanked hardware observations, never
Game_State=PLAYING alone. No production changes, HP writes or fake rendering.
FP-agent contract: current StageFp_BG2* symbols, resolved from supplied .sym.
"""
import argparse
import base64
from dataclasses import asdict
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import struct
import subprocess
from contextlib import contextmanager
from unittest.mock import patch
from game_s8_water_observer import script as water_script, parse as water_events, check as check_water

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/verify'),str(ROOT/'tools/bor_compile'),str(ROOT/'tools/audio'),str(ROOT)]
from game_s8_stage_bounds import Proof, selected_rom_path, symbols, sha, require_idle_emulator

STAGES=('1a','3a','3b','3c','4a')  # unaffected control + every active source occurrence
# Symbolic handoff to FP owner: zero means no unfinished publication/fault;
# Loaded/Active must both be nonzero for a hardware-visible Normal foreground.
QUIET=('Stage_LoadPending','Nmi_FrameBusy','Msu1_StreamBusy','StreamScroll_ColPending',
       'StreamScrollFp_ColPending','StageWater_Pending','StageWater_Held',
       'StageFp_BG2Booting','StageFp_BG2DmaPending','StageFp_BG2Fault')
ACTIVE=('StageFp_BG2Loaded','StageFp_BG2Active')
# Keep the capture nudge short: long enough to sample a changed actor frame,
# but not long enough for a fast player to reach the authored 1A exit.
CAPTURE_MOVE_FIELDS=6


def plan():
    from compiler import Source,stage,project
    from stage_water import bind
    from shipped_content import STAGE_CONFIGS
    rows=[]
    for name in STAGES:
        path='data/normal/'+name+'.txt'
        physical,cfg=next((i,c) for i,c in enumerate(STAGE_CONFIGS)
                         if c['source_level'].replace('\\','/').lower()==path)
        source=Source(ROOT/cfg['pak']); ir=stage(source,cfg['source_level'])
        normal=next(s for s in project(source).sets if s.name=='Normal')
        ordinal=next(i for i,e in enumerate(normal.entries) if e.source_path.replace('\\','/').lower()==path)
        rows.append(dict(name=name,source=path,stage=physical,ordinal=ordinal,set='Normal',
                         set_id=normal.source_id,campaign=3,water=asdict(bind(source,ir,physical)),
                         frontpanels=[d.values[0] for d in source.lines(cfg['source_level']) if d.name=='frontpanel']))
    return rows


def preflight(args,rows):
    if not os.environ.get('BOR_TEST_ROM','').strip():raise ValueError('explicit candidate BOR_TEST_ROM required')
    rom=selected_rom_path()
    paths=dict(rom=rom,msu=rom.with_suffix('.msu'),symbols=Path(args.symbols).resolve(),
               environment=Path(args.environment).resolve())
    hashes={k:sha(p) for k,p in paths.items()}
    for key in paths:
        wanted=getattr(args,key+'_sha256')
        if not wanted or hashes[key]!=wanted.lower():raise ValueError(key+' hash missing/mismatched')
    s=symbols(paths['symbols'])
    for name in (*QUIET,*ACTIVE,'StageFp_BG2Map','StageFp_BG2Char','StageFp_BG2BootLoad',
                 'StageWater_RockY','StageWater_Frame','StageWater_Enabled','StageWater_Rocking',
                 'StageWater_Nmi','StageWater_Nmi__done','StageWater_Reset','StageWater_Buffer',
                 'StageWater_ActiveOffset','StageWater_WriteOffset','StageWater_ModeMap','StageWater_RockMap',
                 'StageWater_HeightMap','Pause_Step','PAUSE_STEP_WAIT','StreamCache_Slot2Tile',
                 'Font_TilesData','FONT_TILE_BYTES','FONT_TILES_VRAM_WORD','StageWater_ApplyOamY',
                 'StageWater_ApplyOamY__done','Nmi_HdmaEnable','Nmi_Bg1ScrollX','Nmi_Bg1ScrollY',
                 'Nmi_Bg2ScrollX','Nmi_Bg2ScrollY','Nmi_Busy','STREAM_CACHE_SLOTS'):
        if name not in s:raise ValueError('FP/water integration contract missing: '+name)
    rom_bytes=paths['rom'].read_bytes();msu=paths['msu'].read_bytes()
    def cell(name,index=0):
        addr=s[name];return rom_bytes[((addr>>16)&127)*32768+(addr&32767)+index]
    env=json.loads(paths['environment'].read_text());media={}
    for row in rows:
        sid=row['set_id']
        if not cell('BorSet_ContentAvailable',sid) or cell('BorSet_CampaignMap',sid)!=3:
            raise ValueError('source Normal is not available in this candidate')
        for table,key in (('Mode','amplitude'),('Rock','rocking'),('Height','background_height')):
            if cell('StageWater_'+table+'Map',row['stage'])!=int(row['water'][key]):
                raise ValueError('actual ROM water metadata differs from source')
        fp=next((r for r in env['frontpanel_media'] if r['physical']==row['stage']),None)
        water=next((r for r in env['water_media'] if r['physical']==row['stage']),None)
        if fp is None and water is None: raise ValueError('missing materialized BG1 provenance')
        directory=Path((fp or water)['bg'])
        if not directory.is_absolute(): directory=ROOT/directory
        record=struct.unpack_from('<I',msu,12)[0]+row['stage']*40
        width=struct.unpack_from('<H',msu,record+2)[0]
        if msu[record]!=1 or msu[record+4]!=28: raise ValueError('water proof requires actual 28-row streaming BG1')
        offsets=struct.unpack_from('<III',msu,record+12)
        blobs={}
        for name,offset in zip(('palette','tilemap','tiles'),offsets):
            data=(directory/(name+'.bin')).read_bytes()
            if name=='palette':
                hud_palette=(ROOT/'out/hud/hud_palette.bin').read_bytes()
                data=merge_bg_hud_palette(data,hud_palette)
            if msu[offset:offset+len(data)]!=data: raise ValueError('actual MSU BG1 differs from final materialization: '+name)
            blobs[name]=data
        hud_offset=struct.unpack_from('<I',msu,record+24)[0]
        hud_tiles=(ROOT/'out/hud/hud_tiles.bin').read_bytes()
        if len(hud_tiles)!=msu[record+5]*16 or msu[hud_offset:hud_offset+len(hud_tiles)]!=hud_tiles:
            raise ValueError('actual MSU BG3 HUD tiles differ from final materialization')
        media[row['stage']]=dict(blobs,width=width)
    from source_actor_numeric import verify_source
    verify_source(ROOT/'out/bor_compile_s6/BOR.C')
    return s,media,dict(paths={k:str(p) for k,p in paths.items()},hashes=hashes,
                       bor_c_sha256=sha(ROOT/'out/bor_compile_s6/BOR.C'))


def merge_bg_hud_palette(bg_palette,hud_palette):
    """Match pack_bg_blob: BG1 palette 0 is reserved for the BG3 HUD."""
    if len(bg_palette)!=256 or len(hud_palette)!=32:
        raise ValueError('packed BG/HUD palette sizes')
    if any(bg_palette[:32]):
        raise ValueError('BG1 palette 0 is not reserved for HUD')
    return hud_palette+bg_palette[32:]


def quiescent(snapshot,stage,s,fp=True,paused=False):
    ppu=snapshot['ppu']
    return (snapshot['state']==s['GAME_STATE_PAUSED' if paused else 'GAME_STATE_PLAYING'] and snapshot['stage']==stage
            and not ppu['forcedBlank'] and ppu['brightness']>0 and ppu['bgMode']==1
            and ppu['mainScreenLayers'] & 0x15 == 0x15
            and bool(ppu['mainScreenLayers']&2)==fp
            and not any(snapshot['pending'].values()) and snapshot['dma_active']==0
            and all(bool(v)==fp for v in snapshot['active'].values()))


@contextmanager
def session(s,folder):
    import _harness as h
    log=folder/'water_events.txt';log.write_text('')
    Path(str(log)+'.arm').write_text('0')
    script=folder/'water_read_only.lua';script.write_text(water_script(s,log))
    original=subprocess.Popen
    def launch(argv,**kwargs):
        if '--mcp' not in argv: raise AssertionError('unexpected native process')
        return original([*argv,'--debug.scriptwindow.allowioosaccess=true',str(script)],**kwargs)
    context=h.open_session(__file__,stderr_log=folder/'mesen.log')
    try:
        with patch('subprocess.Popen',launch): m=context.__enter__()
        # Fresh process has already reset; avoid unloading the read-only Lua.
        with patch.object(m,'reset_emulator',lambda:None): yield m
    finally: context.__exit__(None,None,None)


def bg1_guard(vram,cgram,slot_map,layer,media,scroll):
    """Actual visible-map slots point at bytes from final, source-bound BG1.

    This is a resident-media/map guard, not a complete source-image renderer.
    """
    if cgram[32:256]!=media['palette'][32:256]: raise AssertionError('BG1 CGRAM differs from materialized palette')
    count=0
    for col in range(scroll//8,min(scroll//8+32,media['width'])):
        for row in range(28):
            address=layer['tilemapAddr']*2+(2048 if col&32 else 0)+(row*32+(col&31))*2
            entry=struct.unpack_from('<H',vram,address)[0];slot=entry&1023
            if slot==0: continue # reserved blank; all-zero pixels checked below
            if slot*2+2>len(slot_map): raise AssertionError('BG1 map references non-BG1 cache slot')
            tile=struct.unpack_from('<H',slot_map,slot*2)[0]
            expected=media['tiles'][tile*32:tile*32+32]
            start=layer['chrAddr']*2+slot*32
            if len(expected)!=32 or vram[start:start+32]!=expected:
                actual=vram[start:start+32]
                mismatch=next((i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b),None)
                raise AssertionError(f'BG1 map/cache/actual VRAM media mismatch: '
                    f'col={col} row={row} entry=${entry:04X} slot={slot} source_tile={tile} '
                    f'vram_word=${layer["chrAddr"]+slot*16:04X} mismatch_byte={mismatch} '
                    f'actual_len={len(actual)} expected_len={len(expected)}')
            count+=1
    if not count or any(vram[layer['chrAddr']*2:layer['chrAddr']*2+32]):
        raise AssertionError('BG1 empty map or reserved blank corrupted')
    return count


def frozen(before,after):
    for key in ('water_frame','rock_y','camera','scroll','active_offset','table','hdma','bg1_map','bg2_map','cgram','font'):
        if before[key]!=after[key]: raise AssertionError('paused presentation changed: '+key)


def run(args,rows,s,media,report):
    import _harness as h
    import build_rom
    from PIL import Image
    require_idle_emulator()
    folder=args.output.resolve();folder.mkdir(parents=True,exist_ok=False)
    report.update(status='FAIL',native_executed=False,scope='bounded source-stage presentation fixture; no campaign/visual acceptance',
                  samples=[],writes=[],checks=[],captures=[])
    try:
        if Path(h.rom_path(__file__)).resolve()!=Path(report['artifacts']['paths']['rom']):
            raise AssertionError('session ROM differs from approved candidate')
        with session(s,folder) as m:
            report['native_executed']=True
            r=h.Reporter('S8-PRESENTATION');report['checks']=r.results
            p=Proof(m,s,r,report)
            p.native_start(rows[0])
            entries=build_rom.CAMPAIGN_ENTRY_MAPS['BOR_NORMAL_1A_INTERNAL']
            def state():
                queue=bytes(p.read(m,s['DmaQueue'],s['DMA_QUEUE_SLOTS']*s['DMA_QUEUE_SLOT_SIZE']))
                return dict(ppu=m.get_ppu_state(),state=p.val('Game_State'),stage=p.val('Game_StageIndex'),
                            camera=[p.val('Screen_PosX'),p.val('Screen_PosY')],
                            pending={n:p.val(n,1) for n in QUIET},active={n:p.val(n,1) for n in ACTIVE},
                            dma_active=sum(bool(queue[i*s['DMA_QUEUE_SLOT_SIZE']+4]&s['DMA_OPT_ACTIVE'])
                                           for i in range(s['DMA_QUEUE_SLOTS'])),
                            water_frame=p.val('StageWater_Frame'),rock_y=p.val('StageWater_RockY'),
                            water_enabled=p.val('StageWater_Enabled',1),rocking=p.val('StageWater_Rocking',1))
            def settled(row,paused=False):
                good=0;previous=None
                for _ in range(900):
                    snap=state();report['samples'].append(snap)
                    frame=snap['ppu']['frameCount']
                    if quiescent(snap,row['stage'],s,bool(row['frontpanels']),paused) and frame!=previous:good+=1
                    else:good=0
                    previous=frame
                    if good>=3:return snap
                    p.tick()
                raise AssertionError('no three completed/unblanked transfer boundaries: '+row['name'])
            def fixture(name,value,size):
                allowed={'Game_CampaignOrdinal':1,'Game_StageIndex':2,'Stage_LoadPending':1,'Game_State':2,'Spawn_Index':1}
                if allowed.get(name)!=size:raise AssertionError('forbidden presentation write')
                report['writes'].append(dict(name=name,value=value,size=size,reason='explicit source-stage presentation fixture'))
                (m.write_u16 if size==2 else m.write_u8)(s[name],value)
            def region(label,address,length,kind,stem):
                raw=bytes(p.read(m,address,length,kind))
                path=folder/(stem+'_'+label+'.bin');path.write_bytes(raw)
                return raw,dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),address=address,length=length)
            def pause_state():
                snap=state();ppu=snap['ppu']
                vram=bytes(p.read(m,0,65536,'snesVideoRam'))
                cgram=bytes(p.read(m,0,512,'snesCgRam'))
                active=p.val('StageWater_ActiveOffset')
                def digest(data): return hashlib.sha256(data).hexdigest()
                snap.update(scroll=[p.val('Nmi_Bg1ScrollX'),p.val('Nmi_Bg1ScrollY'),
                                    p.val('Nmi_Bg2ScrollX'),p.val('Nmi_Bg2ScrollY')],
                    active_offset=active,
                    table=digest(bytes(p.read(m,s['StageWater_Buffer']+active,673))),
                    hdma=bytes(p.read(m,0x4360,32))[:5].hex(),
                    bg1_map=digest(vram[ppu['layers'][0]['tilemapAddr']*2:ppu['layers'][0]['tilemapAddr']*2+4096]),
                    bg2_map=digest(vram[ppu['layers'][1]['tilemapAddr']*2:ppu['layers'][1]['tilemapAddr']*2+4096]),
                    cgram=digest(cgram),font=digest(vram[s['FONT_TILES_VRAM_WORD']*2:
                                                     s['FONT_TILES_VRAM_WORD']*2+s['FONT_TILE_BYTES']]))
                return snap
            def arm(value):
                Path(str(folder/'water_events.txt')+'.arm').write_text(str(value))
            for row in rows:
                arm(0);p.tick(2)
                if row['ordinal']:
                    prev=entries[row['ordinal']-1]
                    p.need(row['name']+' authored predecessor is stage',prev[0]=='stage')
                    for name,value,size in [('Game_CampaignOrdinal',row['ordinal']-1,1),('Game_StageIndex',prev[1],2),
                                            ('Stage_LoadPending',1,1),('Game_State',s['GAME_STATE_STAGECLEAR'],2)]:
                        fixture(name,value,size)
                settled(row)
                # Do not exhaust a live queue merely to quiet presentation:
                # static 3C could otherwise clear before its proof window.
                baseline_font=None
                for shot in range(3):
                    if shot:
                        report.setdefault('inputs',[]).append(dict(stage=row['name'],button='RIGHT',fields=CAPTURE_MOVE_FIELDS))
                        h.exact_input_edge(m,m.BTN_RIGHT,CAPTURE_MOVE_FIELDS,port=0)
                    snap=settled(row);stem=f"{row['name']}_{shot}"
                    layers=snap['ppu']['layers']
                    if row['frontpanels']:
                        p.need(stem+' BG2 map/CHR committed',layers[1]['tilemapAddr']==s['StageFp_BG2Map']
                               and layers[1]['chrAddr']==s['StageFp_BG2Char'])
                    p.need(stem+' source water/rock mode',bool(snap['water_enabled'])==bool(row['water']['amplitude'] or row['water']['rocking'])
                           and bool(snap['rocking'])==row['water']['rocking'])
                    cgram,cg=region('cgram',0,512,'snesCgRam',stem)
                    vram,vr=region('vram',0,65536,'snesVideoRam',stem)
                    p.need(stem+' CGRAM initialized',any(cgram) and not any(cgram[i]&0x80 for i in range(1,512,2)))
                    for index in ((0,1) if row['frontpanels'] else (0,)):
                        start=layers[index]['tilemapAddr']*2
                        p.need(stem+f' BG{index+1} nonempty map',any(vram[start:start+2048]))
                    font_start=s['FONT_TILES_VRAM_WORD']*2
                    font=vram[font_start:font_start+s['FONT_TILE_BYTES']]
                    p.need(stem+' font/HUD VRAM guard',any(font) and (baseline_font is None or font==baseline_font))
                    baseline_font=font
                    slots=bytes(p.read(m,s['StreamCache_Slot2Tile'],s['STREAM_CACHE_SLOTS']*2))
                    resident=bg1_guard(vram,cgram,slots,layers[0],media[row['stage']],p.val('Nmi_Bg1ScrollX'))
                    if row['water']['rocking']:
                        # StageWater_ClearGuard zeroes both BG1 map rows28..31.
                        p.need(stem+' rocking lower guard rows clear',not any(vram[0xc700:0xc800]) and not any(vram[0xcf00:0xd000]))
                    result=m.take_screenshot(format='base64')
                    encoded=result.get('base64') or result.get('data')
                    if not encoded:raise AssertionError('screenshot API omitted PNG payload')
                    png=base64.b64decode(encoded.split(',',1)[-1]);path=folder/(stem+'.png');path.write_bytes(png)
                    im=Image.open(io.BytesIO(png)).convert('RGB')
                    crop=im.crop((0,32,im.width,min(224,im.height)))
                    pixels=list(crop.getdata());nonblack=sum(max(c)>8 for c in pixels)
                    p.need(stem+' actual nonblack playfield pixels',len(set(pixels))>16 and nonblack>len(pixels)//20)
                    report['captures'].append(dict(stage=row,hardware=snap,png=str(path),png_sha256=hashlib.sha256(png).hexdigest(),
                                                   cgram=cg,vram=vr,resident_bg1_tiles=resident,
                                                   nonblack_pixels=nonblack,unique_colors=len(set(pixels))))
                # Register snapshots include raster-phase-dependent scroll;
                # they are evidence, not a naive equality-to-camera oracle.
                arm(1)
                initial=p.val('StageWater_Frame')
                for _ in range(args.motion_fields):
                    p.tick()
                    p.need(row['name']+' remains in actual source stage during effect',
                           p.val('Game_State')==s['GAME_STATE_PLAYING'] and p.val('Game_StageIndex')==row['stage'])
                active=bool(row['water']['amplitude'] or row['water']['rocking'])
                p.need(row['name']+' active clock progresses / control stays inert',
                       (p.val('StageWater_Frame')!=initial)==active)
                report.setdefault('inputs',[]).append(dict(stage=row['name'],button='START',purpose='pause'))
                h.exact_input_edge(m,m.BTN_START,1,port=0)
                p.wait(lambda:p.val('Game_State')==s['GAME_STATE_PAUSED'] and p.val('Pause_Step',1)==s['PAUSE_STEP_WAIT'],600)
                settled(row,paused=True)
                before=pause_state();arm(2)
                for _ in range(args.pause_fields):p.tick()
                after=pause_state();frozen(before,after)
                p.need(row['name']+' stays paused and hardware remains visible',
                       quiescent(after,row['stage'],s,bool(row['frontpanels']),paused=True))
                shot=m.take_screenshot(format='base64')
                png=base64.b64decode((shot.get('base64') or shot.get('data') or '').split(',',1)[-1])
                if not png: raise AssertionError('paused screenshot missing')
                paused_path=folder/(row['name']+'_paused.png');paused_path.write_bytes(png)
                report.setdefault('pause_checks',[]).append(dict(stage=row['name'],before=before,after=after,
                                                               screenshot=str(paused_path)))
                report['inputs'].append(dict(stage=row['name'],button='START',purpose='resume Continue'))
                h.exact_input_edge(m,m.BTN_START,1,port=0)
                p.wait(lambda:p.val('Game_State')==s['GAME_STATE_PLAYING'],600)
                arm(3);settled(row)
                resumed=p.val('StageWater_Frame')
                for _ in range(60):p.tick()
                p.need(row['name']+' resumes same source effect without clock reset',
                       p.val('Game_StageIndex')==row['stage'] and p.val('Game_State')==s['GAME_STATE_PLAYING']
                       and (not active or 0<(p.val('StageWater_Frame')-after['water_frame'])%5760<240)
                       and ((p.val('StageWater_Frame')!=resumed)==active))
                settled(row)
                arm(0);p.tick(2)
            events=water_events((folder/'water_events.txt').read_text())
            report['water_bus_proof']=check_water(events,rows,s['StageWater_Buffer'])
            report['status']='WATER_ROCK_PAUSE_HARDWARE_PASS_MANUAL_REVIEW_REQUIRED'
    except Exception as exc:report['error']=f'{type(exc).__name__}: {exc}'
    finally:
        journal=folder/'water_events.txt'
        if journal.exists(): report['water_journal']=dict(path=str(journal),sha256=sha(journal))
        (folder/'report.json').write_text(json.dumps(report,indent=2))


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run',action='store_true')
    ap.add_argument('--preflight',action='store_true')
    for name in ('rom','msu','symbols','environment'):ap.add_argument('--'+name+'-sha256')
    ap.add_argument('--symbols',default=str(ROOT/'src/main.sym'))
    ap.add_argument('--environment',default=str(ROOT/'src/generated/stage_environment_materialization.json'))
    ap.add_argument('--output',type=Path,default=ROOT/'out/s8_presentation')
    ap.add_argument('--motion-fields',type=int,default=180)
    ap.add_argument('--pause-fields',type=int,default=60)
    args=ap.parse_args(argv);report=dict(status='FAIL',native_executed=False)
    try:
        rows=plan()
        if not 120<=args.motion_fields<=600 or not 30<=args.pause_fields<=180:
            raise ValueError('bounded coverage requires motion120..600 and pause30..180 fields')
        if args.run or args.preflight:
            s,media,artifacts=preflight(args,rows);report['artifacts']=artifacts
            if args.run:run(args,rows,s,media,report)
            else:report.update(status='PREFLIGHT_ONLY_NOT_RUN',stages=rows)
        else:report.update(status='PREPARED_NOT_RUN',stages=rows,fp_required_symbols=[*QUIET,*ACTIVE])
    except Exception as exc:report['error']=f'{type(exc).__name__}: {exc}'
    print(json.dumps(report if not args.run else dict(status=report['status'],error=report.get('error'),output=str(args.output)),indent=2))
    return int(report['status']=='FAIL')


if __name__=='__main__':raise SystemExit(main())
