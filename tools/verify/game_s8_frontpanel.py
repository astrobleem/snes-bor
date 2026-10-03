#!/usr/bin/env python3
"""Prepared full Normal BG2 probe. No emulator without --run.

PowerShell, AFTER main's complete candidate build and serialized emulator slot:
  $env:BOR_TEST_ROM='build/s8_candidate/bor.sfc'
  python tools/verify/game_s8_frontpanel.py --run --rom-sha256 ROM_HASH `
    --msu-sha256 MSU_HASH --symbols src/main.sym --symbols-sha256 SYM_HASH `
    --environment src/generated/stage_environment_materialization.json `
    --environment-sha256 ENV_HASH --output out/s8_fp_native_unique

Explicit hashes are mandatory; --preflight checks them without starting Mesen.
Cold native Normal selection, then controller-only 1A camera motion. Other
stages use the explicit source-predecessor fixture through REAL Stage_Load.
No HP, camera, actor, queue, FP state, VRAM, CGRAM or CPU-register writes.
No pause tests: Curie's separate presentation probe owns that coverage.
VRAM/CGRAM pixel correctness and integer target motion are separate verdicts;
screenshots/transparent expected-FP overlays remain manual composite review.
"""
import argparse
import base64
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'tools/verify'),str(ROOT/'tools/bor_compile'),
               str(ROOT/'tools/bg_converter'),str(ROOT/'tools/bor_converter'),str(ROOT)]
import numpy as np
import snes_tiles as st
from game_s8_stage_bounds import Proof, symbols, sha, require_idle_emulator

STAGES = ('1a','3b','4b','6b')
EVENTS = dict(load='Stage_Load',boot='StageFp_BG2BootLoad',resolve='StageFp_BG2Resolve',
    producer_done='StageFp_BG2PlayDispatch__done',commit='StageFp_BG2CommitDispatch',
    skipped='Core_Nmi_Play__frame_skipped')
BYTE_STATE = ('Stage_LoadPending','Nmi_FrameBusy','Nmi_Busy','Msu1_StreamBusy',
    'StreamScrollFp_ColPending','StageFp_BG2DmaPending','StageFp_BG2Booting',
    'StageFp_BG2Fault','StageFp_BG2Loaded','StageFp_BG2Active')
QUIET = ('Stage_LoadPending','Nmi_FrameBusy','Msu1_StreamBusy','StreamScrollFp_ColPending',
         'StageFp_BG2DmaPending','StageFp_BG2Booting','StageFp_BG2Fault')
FIXTURE_WRITES = {'Game_CampaignOrdinal':1,'Game_StageIndex':2,'Stage_LoadPending':1,'Game_State':2}


def pc(address):
    return ((address >> 16)&0x7F)*0x8000+(address&0x7FFF)


def source_plan():
    import build_rom
    from compiler import Source,project,stage
    from stage_frontpanel import sequence_directives
    cache,rows = {},[]
    for name in STAGES:
        physical,cfg = next((i,c) for i,c in enumerate(build_rom.STAGE_CONFIGS)
            if c['source_level'].replace('\\','/').lower() == 'data/normal/'+name+'.txt')
        path = (ROOT/cfg['pak']).resolve()
        if path not in cache: cache[path] = Source(path)
        source = cache[path]
        normal = next(s for s in project(source).sets if s.name == 'Normal')
        ir = stage(source,cfg['source_level'])
        ordinal = next(i for i,e in enumerate(normal.entries)
            if e.source_path.replace('\\','/').lower() == ir.source_path.replace('\\','/').lower())
        rows.append(dict(name=name,stage=physical,ordinal=ordinal,set='Normal',set_id=normal.source_id,
            campaign=3,source_path=ir.source_path,source_level_sha256=hashlib.sha256(source.read(ir.source_path)).hexdigest(),
            sequence=sequence_directives(source,ir),direction=ir.scroll))
    return rows


def packed_fp(msu,physical):
    if msu[:8] != b'BORMSU1\0' or physical >= msu[10]: raise ValueError('MSU stage directory')
    directory = struct.unpack_from('<I',msu,12)[0]
    record = directory+physical*40
    offset = struct.unpack_from('<I',msu,record+28)[0]
    if not offset: raise ValueError('missing packed FP')
    w,h,bpp,n,map_offset,tiles_offset = struct.unpack_from('<HBBH2xII',msu,offset)
    end = tiles_offset+n*32
    if (h,bpp) != (28,4) or not (0 < offset < map_offset < tiles_offset < end <= min(len(msu),0x1000000)):
        raise ValueError('packed FP ABI/address range')
    if map_offset != offset+48 or tiles_offset != map_offset+w*28*3: raise ValueError('packed FP offsets')
    return dict(width=w,count=n,offset=offset,palette=msu[offset+16:offset+48],
                tilemap=msu[map_offset:tiles_offset],tiles=msu[tiles_offset:end])


def preflight(args,rows):
    import build_rom
    import os
    from stage_frontpanel_bg2 import layout_proof
    if not os.environ.get('BOR_TEST_ROM','').strip(): raise ValueError('explicit BOR_TEST_ROM required')
    rom_path = Path(os.environ['BOR_TEST_ROM'])
    if not rom_path.is_absolute(): rom_path = ROOT/rom_path
    rom_path = rom_path.resolve(strict=True)
    paths = dict(rom=rom_path,msu=rom_path.with_suffix('.msu'),symbols=Path(args.symbols).resolve(),
                 environment=Path(args.environment).resolve())
    hashes = {k:sha(p) for k,p in paths.items()}
    for k in paths:
        wanted = getattr(args,k+'_sha256')
        if not wanted or not re.fullmatch('[0-9a-fA-F]{64}',wanted) or hashes[k] != wanted.lower():
            raise ValueError(k+' hash missing/mismatched')
    s = symbols(paths['symbols'])
    required = (*EVENTS.values(),*BYTE_STATE,'StageFp_ModeMap','StageFp_PeriodMap',
        'StageFp_BG2SlotMap','StageFp_BG2TileBuf','StageFp_BG2ColBuf','StageFp_BG2Map',
        'StageFp_BG2Char','StageFp_Request','StreamScrollFp_StagedLo','StreamScrollFp_StagedHi',
        'Font_PaletteData','Font_TilesData','FONT_TILE_BYTES','FONT_TILES_VRAM_WORD',
        'Nmi_Bg2ScrollX','Nmi_Bg2ScrollY','StageFp_BG2ColdInit','StageFp_BG2SceneReset')
    for name in required:
        if name not in s: raise ValueError('missing FP integration symbol: '+name)
    rom,msu = paths['rom'].read_bytes(),paths['msu'].read_bytes()
    for caller,target in [('Bg_LoadSceneFp_Streaming','StageFp_BG2BootDispatch'),
                           ('Core_StreamScrollFp_Play','StageFp_BG2PlayDispatch')]:
        at = pc(s[caller])
        if rom[at:at+5] != b'\x08\x22'+s[target].to_bytes(3,'little'):
            raise ValueError('missing actual hook: '+caller)
    env = json.loads(paths['environment'].read_text())
    media = {}
    expected_slots = tuple(layout_proof()['slots'])
    slot_map = struct.unpack_from(f'<{len(expected_slots)}H',rom,pc(s['StageFp_BG2SlotMap']))
    if slot_map != expected_slots:
        raise ValueError('ROM slot mapping differs from audited VRAM layout')
    for row in rows:
        report = next(r for r in env['frontpanel_media'] if r['physical'] == row['stage'])
        path = Path(report['frontpanel'])
        m = json.loads((path/'manifest.json').read_text())
        # Bind the source sequence/level, not merely a filename or target hash.
        oracle = json.loads((Path(m['indexed_oracle'])/'manifest.json').read_text())
        inputs = oracle['sequence_inputs']
        if inputs['sequence'] != row['sequence'] or inputs['source_level_sha256'] != row['source_level_sha256']:
            raise ValueError('FP source identity/provenance mismatch')
        packed = packed_fp(msu,row['stage'])
        for key,name in [('tiles','tiles.bin'),('tilemap','tilemap.bin'),('palette','palette.bin')]:
            if hashlib.sha256(packed[key]).hexdigest() != report['full_fp_blob_sha256'][name]:
                raise ValueError('candidate MSU predates/differs from generated FP: '+name)
        period = struct.unpack_from('<H',rom,pc(s['StageFp_PeriodMap'])+row['stage']*2)[0]
        mode = rom[pc(s['StageFp_ModeMap'])+row['stage']]
        if period*8 != m['target_cycle_width'] or mode != (2 if row['direction']=='down' else 1):
            raise ValueError('ROM FP mode/period mismatch')
        font = rom[pc(s['Font_PaletteData']):pc(s['Font_PaletteData'])+8]
        if packed['palette'][8:16] != font: raise ValueError('FP font palette conflict in actual ROM/MSU')
        # Final clean BG1, not the intermediate water composite with baked FP.
        record = struct.unpack_from('<I',msu,12)[0]+row['stage']*40
        clean = Path(report['bg'])
        check_clean_bg_binding(msu,record,clean,ROOT/build_rom.BG_SCREENS[row['stage']][1])
        media[row['stage']] = dict(packed,manifest=m,period=period,slot_map=slot_map,font=font,
            font_tiles=rom[pc(s['Font_TilesData']):pc(s['Font_TilesData'])+s['FONT_TILE_BYTES']])
    return s,media,dict(paths={k:str(v) for k,v in paths.items()},hashes=hashes)


def check_clean_bg_binding(msu,record,clean,hud):
    """Independent packed-format oracle: CGRAM0..15 is HUD-merged.

    Offsets remain record +12 palette, +16 tilemap, +20 tiles, +24 HUD CHR.
    Compare every palette/map/tile/HUD byte; never ignore the reserved palette.
    """
    clean,hud=Path(clean),Path(hud)
    bg_info=json.loads((clean/'manifest.json').read_text())
    hud_info=json.loads((hud/'manifest.json').read_text())
    palette=(clean/'palette.bin').read_bytes()
    hud_palette=(hud/'hud_palette.bin').read_bytes()
    tilemap=(clean/'tilemap.bin').read_bytes()
    tiles=(clean/'tiles.bin').read_bytes()
    hud_tiles=(hud/'hud_tiles.bin').read_bytes()
    if len(palette)!=256 or len(hud_palette)!=32 or any(palette[:32]):
        raise ValueError('invalid clean/HUD palette merge inputs')
    width,height,count=bg_info['width_tiles'],bg_info['height_tiles'],bg_info['unique_tiles']
    hud_count=hud_info['tile_count']
    if (bg_info.get('streaming') is not True or height!=28 or len(tilemap)!=width*height*3
            or len(tiles)!=count*32 or len(hud_tiles)!=hud_count*16):
        raise ValueError('invalid final FP-free BG blob lengths')
    expected=hud_palette+palette[32:]+tilemap+tiles+hud_tiles
    base=struct.unpack_from('<I',msu,record+12)[0]
    header=struct.pack('<BxHBB2xH2xIIII',1,width,height,hud_count,count,
                       base,base+256,base+256+len(tilemap),base+256+len(tilemap)+len(tiles))
    if msu[record:record+28]!=header:
        raise ValueError('candidate BG1 record differs from final FP-free binding schema')
    actual=msu[base:base+len(expected)]
    if actual!=expected:
        first=next((i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b),min(len(actual),len(expected)))
        raise ValueError(f'candidate BG1 is not final FP-free binding: packed byte +{first}, MSU ${base+first:X}')


def decode(data,bpp,hf=False,vf=False):
    tile = st.decode_4bpp_tile(data) if bpp == 4 else st.decode_2bpp_tile(data)
    if hf: tile = tile[:,::-1]
    if vf: tile = tile[::-1,:]
    return tile


def pixel_oracle(vram,cgram,media,lo,hi,scroll,s):
    """Compare every actual resident pixel/priority, then produce target overlay.

    Independent of cache slot choice: compare indexed pixel values after flips.
    CGRAM0 is dynamic backdrop; FP index0 is transparent and is not compared.
    """
    if len(vram)!=65536 or len(cgram)!=512 or hi-lo!=32: raise AssertionError('capture/window ABI')
    if cgram[8:32] != media['palette'][8:32]: raise AssertionError('actual final CGRAM4..15 differs')
    start = s['FONT_TILES_VRAM_WORD']*2
    if vram[start:start+len(media['font_tiles'])] != media['font_tiles']: raise AssertionError('actual font CHR corrupted')
    entries = st.decode_tilemap_column_major(media['tilemap'],media['width'],28)
    plane = np.zeros((224,33*8),dtype=np.uint8)
    for col in range(lo,hi+1):
        for row in range(28):
            word_address = s['StageFp_BG2Map']+(col&31)+(1024 if col&32 else 0)+row*32
            word = int.from_bytes(vram[word_address*2:word_address*2+2],'little')
            tid = word&1023
            if tid not in media['slot_map'] or word&0x3C00 != 0x2000:
                raise AssertionError('BG2 physical tile/palette/high-priority ownership')
            address = (s['StageFp_BG2Char']+tid*16)*2
            actual = decode(vram[address:address+32],4,bool(word&0x4000),bool(word&0x8000))
            eid,pal,hf,vf = entries[row*media['width']+col%media['period']]
            expected = decode(media['tiles'][eid*32:eid*32+32],4,hf,vf)
            if pal != 0 or not np.array_equal(actual,expected):
                raise AssertionError(f'FP pixel mismatch world column {col}, row {row}')
            plane[row*8:row*8+8,(col-lo)*8:(col-lo+1)*8] = expected
    if not lo*8 <= scroll <= (hi-31)*8: raise AssertionError('presented camera outside residency')
    plane = plane[:,scroll-lo*8:scroll-lo*8+256]
    if plane.shape != (224,256): raise AssertionError('visible FP coverage')
    colors = np.frombuffer(cgram,dtype='<u2')[plane]
    rgba = np.zeros((224,256,4),dtype=np.uint8)
    for channel,shift in enumerate((0,5,10)):
        v = (colors>>shift)&31
        rgba[:,:,channel] = (v<<3)|(v>>2)
    rgba[:,:,3] = np.where(plane!=0,255,0)
    return dict(resident_pixels=33*28*64,opaque_visible_pixels=int(np.count_nonzero(plane)),
                upper_opaque_pixels=int(np.count_nonzero(plane[:168])),
                palette4_7=list(struct.unpack('<4H',cgram[8:16]))),rgba


def journal_script(s,path):
    """Read-only Lua execution callbacks. No game-memory writes or breakpoints."""
    for label in EVENTS.values():
        if s[label]&65535<0x8000:raise ValueError('observer target is not LoROM code: '+label)
    addresses = ','.join('['+str(pc(s[label]))+']='+json.dumps(event) for event,label in EVENTS.items())
    values = ','.join(str(s[n]) for n in ('Game_StageIndex','Nmi_FrameBusy','StageFp_BG2Booting',
        'StageFp_BG2DmaPending','StreamScrollFp_ColPending','StageFp_BG2Fault'))
    return '''
local output=OUTPUT
local status=STATUS
local events={EVENTS}
local addresses={VALUES}
local count=0
local frames=0
local function heartbeat(phase)
 local f=assert(io.open(status,'w'));f:write(phase,' ',frames,' ',count,'\\n');f:close()
end
heartbeat('loaded')
local function rd(a,n)
 local v=0;for i=0,n-1 do v=v+emu.read(a+i,emu.memType.snesMemory)*256^i end;return v
end
local function bytes(a,n)
 local out={};for i=0,n-1 do out[#out+1]=string.format('%02x',rd(a+i,1)) end
 return table.concat(out)
end
for address,event in pairs(events) do
 local label=event
 emu.addMemoryCallback(function()
  count=count+1
  if count>100000 then
   if count==100001 then local f=assert(io.open(output,'a'));f:write('OVERFLOW\\n');f:close() end
   return
  end
  local row={label}
  for i,a in ipairs(addresses) do row[#row+1]=string.format('%.0f',rd(a,i==1 and 2 or 1)) end
  row[#row+1]=bytes(TILEBUF,64);row[#row+1]=bytes(COLBUF,56)
  local f=assert(io.open(output,'a'));f:write(table.concat(row,' '),'\\n');f:close()
 end,emu.callbackType.exec,address,address,emu.cpuType.snes,emu.memType.snesPrgRom)
end
heartbeat('ready')
emu.addEventCallback(function() frames=frames+1;heartbeat('ready') end,emu.eventType.endFrame)
'''.replace('OUTPUT',json.dumps(path.as_posix())).replace('STATUS',json.dumps(path.with_suffix('.status').as_posix())).replace('EVENTS',addresses).replace('VALUES',values).replace(
        'TILEBUF',str(s['StageFp_BG2TileBuf'])).replace('COLBUF',str(s['StageFp_BG2ColBuf']))


def observer_status(path):
    if not path.exists():return None
    parts=path.read_text().split()
    if len(parts)!=3:return None
    return dict(phase=parts[0],frames=int(parts[1]),callbacks=int(parts[2]))


def seam_capture_due(snap,boundary):
    # Display may lag the CPU camera by multiple pending columns. Never use
    # displayed scroll alone to decide when to release the movement input.
    # A release drains accepted input/time commands, which can advance a seam
    # by ~56px even though no more directions are held. Arm the before-capture
    # a wider 96px ahead so the committed sample remains truly pre-seam.
    return max(snap['camera']*7//5,snap['request'],snap['scroll'])>=boundary-96


def require_seam_side(snap,boundary,before):
    if before:
        if max(snap['camera']*7//5,snap['request'],snap['scroll'])>=boundary:
            raise AssertionError('before-seam capture crossed boundary while settling')
    elif snap['scroll']<boundary:raise AssertionError('after-seam capture has not crossed boundary')


@contextmanager
def neutral_input(m):
    # release_input alone restores physical/live input; a persistent zero
    # override ensures no new RIGHT polls while pending simulation drains.
    m.hold_input(0,port=0)
    try:yield
    finally:m.release_input(port=0)


def check_journal(text,stages):
    pending = None
    pending_dma = False
    counts = dict(committed_pending=0,dma_commits=0,skipped_pending=0,producer_leases=0)
    boots,loads = [],[]
    for line in text.splitlines():
        parts = line.split()
        if len(parts)!=9: raise AssertionError('incomplete/overflow FP event journal')
        event = parts[0]
        stage,busy,boot,dma,column,fault = map(int,parts[1:7])
        buffers = tuple(parts[7:])
        if len(buffers[0])!=128 or len(buffers[1])!=112: raise AssertionError('incomplete buffer journal')
        if event=='load': loads.append(stage)
        if event=='boot': boots.append(stage)
        if stage not in stages: continue
        if fault: raise AssertionError('FP runtime fault in event journal')
        if event=='resolve' and not boot:
            if busy!=1 or dma or pending is not None: raise AssertionError('producer lease/pending fence violated')
            counts['producer_leases'] += 1
        if event=='producer_done' and dma:
            if pending is not None and buffers!=pending: raise AssertionError('queued buffers rewritten before commit')
            pending = buffers
            pending_dma = True
        if event=='producer_done' and column and pending is None:
            # Cache-hit-only columns still have an immutable publication buffer.
            pending = buffers
        if event in ('skipped','commit') and pending is not None:
            if buffers!=pending: raise AssertionError('published DMA/column buffer changed before NMI')
            if event=='commit':
                if busy: raise AssertionError('commit entered with producer lease held')
                counts['committed_pending'] += 1
                counts['dma_commits'] += int(pending_dma)
                pending = None
                pending_dma = False
            else: counts['skipped_pending'] += 1
    if pending is not None: raise AssertionError('unfinished DMA at end of probe')
    if not counts['dma_commits'] or not counts['producer_leases']:
        raise AssertionError('pending DMA/lease path was not exercised')
    for stage in stages:
        if stage not in boots: raise AssertionError('real BG2 boot loader not observed')
    return dict(counts,boot_stages=boots,stage_load_entries=loads,
        skipped_nmi_verdict='OBSERVED_PASS' if counts['skipped_pending'] else 'NOT_OBSERVED_NOT_CLAIMED')


@contextmanager
def session(s,folder,report=None):
    from _harness import open_session
    from unittest.mock import patch
    script = folder/'fp_read_only.lua'
    script.write_text(journal_script(s,folder/'events.txt'))
    (folder/'events.txt').write_text('')
    original = subprocess.Popen
    def launch(argv,**kw):
        if '--mcp' not in argv: raise AssertionError('unexpected native process launch')
        return original([*argv,'--debug.scriptwindow.allowioosaccess=true',str(script)],**kw)
    context = open_session(__file__,stderr_log=folder/'mesen.log')
    try:
        if report is not None:report['native_attempted']=True
        with patch('subprocess.Popen',launch): m = context.__enter__()
        if report is not None:report['native_executed']=True
        from _harness import run_frames_exact
        for _ in range(30):
            status=observer_status(folder/'events.status')
            if report is not None:report['observer_heartbeat']=status
            if status and status['phase']=='ready' and status['frames']>0:break
            run_frames_exact(m,1)
        else:raise AssertionError('Lua observer not loaded/registered or no end-frame heartbeat; inspect events.status')
        # Fresh process launch is already cold. The startup helper's second
        # reset destroys the debugger/Lua callbacks (same seam as bounds).
        with patch.object(m,'reset_emulator',lambda:None): yield m
    finally: context.__exit__(None,None,None)


def run(args,rows,s,media,report):
    import _harness as h
    import build_rom
    from PIL import Image
    require_idle_emulator()
    if Path(h.rom_path(__file__)).resolve()!=Path(report['artifacts']['paths']['rom']):
        raise ValueError('session ROM differs from hashed candidate')
    folder = args.output.resolve()
    folder.mkdir(parents=True,exist_ok=False)
    report.update(status='FAIL',native_executed=False,captures=[],writes=[],motion=[])
    try:
        with session(s,folder,report) as m:
            report['native_executed'] = True
            reporter = h.Reporter('S8-FP');report['checks'] = reporter.results
            p = Proof(m,s,reporter,report)
            p.native_start(rows[0])
            status=observer_status(folder/'events.status')
            report['observer_startup']=status
            p.need('observer execution callbacks live after real Normal startup',
                   bool(status and status['callbacks']>0) and (folder/'events.txt').stat().st_size>0)
            p.need('observer saw Normal BG2 boot',any(line.startswith('boot '+str(rows[0]['stage'])+' ')
                   for line in (folder/'events.txt').read_text().splitlines()))
            def snapshot():
                return dict(stage=p.val('Game_StageIndex'),state=p.val('Game_State'),ppu=m.get_ppu_state(),
                    camera=p.val('Screen_PosX'),request=p.val('StageFp_Request'),scroll=p.val('Nmi_Bg2ScrollX'),
                    pending_column=p.val('StreamScrollFp_PendCol'),
                    lo=p.val('StreamScrollFp_StagedLo'),hi=p.val('StreamScrollFp_StagedHi'),
                    flags={n:p.val(n,1) for n in BYTE_STATE})
            def settled(row):
                previous=None;position=None;good=0
                for _ in range(args.settle_fields):
                    snap=snapshot();q=snap['ppu'];flags=snap['flags'];layer=q['layers'][1]
                    expected_request=(0 if row['direction']=='down'
                                      else snap['camera']*7//5)
                    valid=(snap['stage']==row['stage'] and snap['state']==s['GAME_STATE_PLAYING']
                        and not q['forcedBlank'] and q['brightness']>0 and q['bgMode']==1
                        and q['mainScreenLayers']&0x16==0x16 and not any(flags[n] for n in QUIET)
                        and flags['StageFp_BG2Loaded']==1 and flags['StageFp_BG2Active']==1
                        and snap['request']==expected_request
                        and snap['pending_column']==65535
                        and layer['tilemapAddr']==s['StageFp_BG2Map'] and layer['chrAddr']==s['StageFp_BG2Char']
                        and layer['hscroll']==snap['scroll']%1024 and layer['vscroll']==0)
                    current=tuple(snap[n] for n in ('camera','request','scroll','lo','hi'))
                    good=good+1 if valid and q['frameCount']!=previous and current==position else 0
                    previous=q['frameCount']
                    position=current
                    if good>=3:return snap
                    p.tick()
                raise AssertionError('no coherent, unblanked committed FP window: '+row['name'])
            def capture(row,label,before_boundary=None):
                with neutral_input(m):snap=settled(row)
                if before_boundary is not None:
                    report.setdefault('seam_attempts',[]).append(dict(boundary=before_boundary,neutral_settled=snap))
                    require_seam_side(snap,before_boundary,True)
                vram=bytes(h.read_block(m,0,65536,'snesVideoRam'))
                cgram=bytes(h.read_block(m,0,512,'snesCgRam'))
                proof,rgba=pixel_oracle(vram,cgram,media[row['stage']],snap['lo'],snap['hi'],snap['scroll'],s)
                adapted=0 if row['direction']=='down' else snap['camera']*7//5
                p.need(label+' integer request',snap['request']==adapted)
                p.need(label+' resident motion clamp',snap['scroll']==max(snap['lo']*8,min(adapted,(snap['hi']-31)*8)))
                stem=row['name']+'_'+label
                (folder/(stem+'_vram.bin')).write_bytes(vram)
                (folder/(stem+'_cgram.bin')).write_bytes(cgram)
                Image.fromarray(rgba).save(folder/(stem+'_expected_fp.png'))
                result=m.take_screenshot(format='base64')
                encoded=result.get('base64') or result.get('data')
                if not encoded:raise AssertionError('screenshot omitted PNG')
                png=base64.b64decode(encoded.split(',',1)[-1]);(folder/(stem+'.png')).write_bytes(png)
                report['captures'].append(dict(stage=row['name'],label=label,hardware=snap,pixels=proof,
                    screenshot=str(folder/(stem+'.png')),screenshot_sha256=hashlib.sha256(png).hexdigest(),
                    expected_fp_overlay=str(folder/(stem+'_expected_fp.png'))))
                return snap
            capture(rows[0],'postload')
            period=media[rows[0]['stage']]['period']*8
            stride=media[rows[0]['stage']]['manifest']['source_stride']
            report['source_seam']=dict(first_clipped_width=stride,source_cycle=stride*len(rows[0]['sequence']),
                target_cycle=period,adapter='ACCEPTED_COMPAT integer camera and 8px cycle rounding')
            # Capture every image boundary and full-cycle wrap after actual RIGHT input.
            boundaries=[round(period*i/len(rows[0]['sequence'])) for i in range(1,len(rows[0]['sequence'])+1)]
            elapsed=0
            for index,boundary in enumerate(boundaries):
                before=None
                attempt=0
                while elapsed<args.motion_fields:
                    snap=snapshot()
                    report['motion'].append({k:snap[k] for k in ('camera','request','scroll','lo','hi')})
                    if snap['scroll']>=boundary:
                        attempt+=1
                        after=capture(rows[0],f'seam{index+1}_after_attempt{attempt}')
                        report.setdefault('crossing_attempts',[]).append(dict(
                            boundary=boundary,observed=snap['scroll'],settled=after['scroll']))
                        # Encounter/camera clamps can backtrack while neutral input
                        # drains pending work. Keep evidence and continue bounded
                        # controller motion; never invent a monotonic camera.
                        if after['scroll']>=boundary:break
                    if before is None and seam_capture_due(snap,boundary):
                        before=capture(rows[0],f'seam{index+1}_before',before_boundary=boundary)
                    # Ordinary attacks may clear encounter pressure; never seed HP/queue/camera.
                    buttons=m.BTN_RIGHT | (m.BTN_Y if elapsed%16<8 else 0)
                    h.exact_input_edge(m,buttons,1,port=0);elapsed+=1
                else:raise AssertionError('controller-only camera did not reach authored cycle seam')
                require_seam_side(after,boundary,False)
                p.need('captured both sides of seam '+str(index+1),before is not None and before['scroll']<boundary<=after['scroll'])
            entries=build_rom.CAMPAIGN_ENTRY_MAPS['BOR_NORMAL_1A_INTERNAL']
            for row in rows[1:]:
                settled(rows[0] if row==rows[1] else rows[rows.index(row)-1])
                previous=entries[row['ordinal']-1]
                p.need('fixture predecessor is authored stage',previous[0]=='stage')
                writes=[('Game_CampaignOrdinal',row['ordinal']-1,1),('Game_StageIndex',previous[1],2),
                    ('Stage_LoadPending',1,1),('Game_State',s['GAME_STATE_STAGECLEAR'],2)]
                for name,value,size in writes:
                    if FIXTURE_WRITES.get(name)!=size:raise AssertionError('forbidden fixture write')
                    report['writes'].append(dict(name=name,value=value,size=size,reason='real Stage_Load source-predecessor fixture'))
                    (m.write_u8 if size==1 else m.write_u16)(s[name],value)
                capture(row,'postload_upper_rows')
            # Finish only after the pending fence is drained; Lua never writes game state.
            settled(rows[-1])
        report['lease']=check_journal((folder/'events.txt').read_text(),[r['stage'] for r in rows])
        # The predecessor fixture enters real Stage_Load; boot callbacks prove destination.
        if len(report['lease']['stage_load_entries'])<3:raise AssertionError('real Stage_Load fixture path not observed')
        after={name:sha(path) for name,path in report['artifacts']['paths'].items()}
        report['artifacts_after']=after
        if after!=report['artifacts']['hashes']:raise AssertionError('candidate artifacts changed during native probe')
        report.update(status='TARGET_PIXEL_AND_ADAPTED_MOTION_PASS',pixel_correctness='ACTUAL_VRAM_CGRAM_TARGET_PASS',
            motion_correctness='ACCEPTED_COMPAT_INTEGER_RATIO_AND_CYCLE_SEAMS_PASS',
            screenshot_composite='CAPTURED_MANUAL_REVIEW_PENDING',paused_presentation='OUT_OF_SCOPE_CURIE')
    except Exception as exc:report['error']=f'{type(exc).__name__}: {exc}'
    finally:(folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--run',action='store_true');parser.add_argument('--preflight',action='store_true')
    for name in ('rom','msu','symbols','environment'):parser.add_argument('--'+name+'-sha256')
    parser.add_argument('--symbols',default=str(ROOT/'src/main.sym'))
    parser.add_argument('--environment',default=str(ROOT/'src/generated/stage_environment_materialization.json'))
    parser.add_argument('--output',type=Path,default=ROOT/'out/s8_frontpanel_native')
    parser.add_argument('--motion-fields',type=int,default=6000)
    parser.add_argument('--settle-fields',type=int,default=900)
    args=parser.parse_args(argv)
    report=dict(status='PLAN_ONLY',native_executed=False,scope=__doc__)
    try:
        rows=source_plan();report['plan']=rows
        if args.run or args.preflight:
            s,media,artifacts=preflight(args,rows);report['artifacts']=artifacts
            report['status']='PREFLIGHT_PASS_NOT_NATIVE'
            if args.run:run(args,rows,s,media,report)
    except Exception as exc:report.update(status='FAIL',error=f'{type(exc).__name__}: {exc}')
    print(json.dumps(report,indent=2))
    return 1 if report['status']=='FAIL' else 0


if __name__=='__main__':sys.exit(main())
