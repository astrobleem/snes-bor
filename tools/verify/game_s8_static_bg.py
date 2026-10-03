#!/usr/bin/env python3
"""Bounded Normal 1A -> real Stage_Load -> 5A diagnostic. No timer replay.

Use the FP probe's identical four hash selectors and BOR_TEST_ROM, with a NEW
--output directory. No emulator without --run. Captures precede oracle verdicts.
Only the four authorized source-predecessor fixture fields are written.
"""
import argparse
import base64
import json
from pathlib import Path
import struct
import sys
import game_s8_frontpanel as fp


def packed_static(msu, stage):
    if msu[:8] != b'BORMSU1\0' or stage >= msu[10]:
        raise ValueError('MSU directory')
    at=struct.unpack_from('<I',msu,12)[0]+stage*40
    mode,w,h,hud,n,pal,tmap,tiles,htiles,front,spawn,scount=struct.unpack_from('<BxHBB2xH2xIIIIIIH2x',msu,at)
    if (mode,w,h,front)!=(0,32,32,0) or not 0<n<=1024:
        raise ValueError('expected narrow static no-FP binding')
    spans={'palette':(pal,256),'tilemap':(tmap,w*h*2),'tiles':(tiles,n*32),'hud':(htiles,hud*16)}
    if (tmap,tiles,htiles)!=(pal+256,tmap+w*h*2,tiles+n*32):
        raise ValueError('noncontiguous static regions')
    if any(a<0 or a+size>len(msu) for a,size in spans.values()):raise ValueError('static bounds')
    return {k:msu[a:a+size] for k,(a,size) in spans.items()}


def difference(actual,expected):
    if len(actual)!=len(expected):raise ValueError('comparison length')
    bad=[i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b]
    return dict(equal=not bad,bytes=len(expected),mismatch_count=len(bad),first_offsets=bad[:32])


def oracle(vram,cgram,media,rom,s):
    if len(vram)!=65536 or len(cgram)!=512:raise ValueError('capture sizes')
    regions={}
    for key,base in [('tiles',0),('tilemap',0x6000),('hud',0x5000)]:
        regions[key]=difference(vram[base*2:base*2+len(media[key])],media[key])
    # Backdrop color 0 may be dynamic; report separately, never silently skip it.
    regions['packed_palette_1_127']=difference(cgram[2:256],media['palette'][2:])
    regions['backdrop_0']=difference(cgram[:2],media['palette'][:2])
    font=rom[fp.pc(s['Font_PaletteData']):fp.pc(s['Font_PaletteData'])+8]
    regions['required_font_palette_4_7']=difference(cgram[8:16],font)
    start=fp.pc(s['Font_TilesData']);size=s['FONT_TILE_BYTES']
    base=s['FONT_TILES_VRAM_WORD']*2
    regions['font_chr']=difference(vram[base:base+size],rom[start:start+size])
    return regions


def run(args,s,artifacts,media,report):
    import _harness as h
    import build_rom
    fp.require_idle_emulator()
    folder=args.output.resolve();folder.mkdir(parents=True,exist_ok=False)
    report.update(status='FAIL',writes=[],captures=[],native_executed=False)
    try:
        with fp.session(s,folder,report) as m:
            reporter=h.Reporter('S8-STATIC');report['checks']=reporter.results
            p=fp.Proof(m,s,reporter,report)
            p.native_start(fp.source_plan()[0])
            with fp.neutral_input(m):
                p.wait(lambda:p.val('StageFp_BG2Loaded',1)==1 and not p.val('StageFp_BG2Booting',1),900)
                entries=build_rom.CAMPAIGN_ENTRY_MAPS['BOR_NORMAL_1A_INTERNAL']
                ordinal=next(i for i,e in enumerate(entries) if e[0]=='stage' and e[1]==report['stage'])
                previous=entries[ordinal-1]
                if previous[0]!='stage':raise ValueError('source predecessor is not stage')
                for name,value,size in [('Game_CampaignOrdinal',ordinal-1,1),('Game_StageIndex',previous[1],2),
                                        ('Stage_LoadPending',1,1),('Game_State',s['GAME_STATE_STAGECLEAR'],2)]:
                    if fp.FIXTURE_WRITES.get(name)!=size:raise ValueError('fixture authority')
                    report['writes'].append(dict(name=name,value=value,size=size))
                    (m.write_u8 if size==1 else m.write_u16)(s[name],value)
                p.wait(lambda:p.val('Game_StageIndex')==report['stage'] and p.val('Game_State')==s['GAME_STATE_PLAYING']
                       and not p.val('Stage_LoadPending',1),900)
                # Bounded, neutral samples retain even bad PPU state, not a wait for pixel correctness.
                for fields in (3,30):
                    p.tick(fields)
                    snap=dict(ppu=m.get_ppu_state(),stage=p.val('Game_StageIndex'),state=p.val('Game_State'),
                              flags={n:p.val(n,1) for n in fp.BYTE_STATE})
                    vram=bytes(h.read_block(m,0,65536,'snesVideoRam'))
                    cgram=bytes(h.read_block(m,0,512,'snesCgRam'))
                    stem='5a_'+str(fields)
                    (folder/(stem+'_vram.bin')).write_bytes(vram)
                    (folder/(stem+'_cgram.bin')).write_bytes(cgram)
                    shot=m.take_screenshot(format='base64');encoded=shot.get('base64') or shot.get('data')
                    (folder/(stem+'.png')).write_bytes(base64.b64decode(encoded.split(',',1)[-1]))
                    checks=oracle(vram,cgram,media,Path(artifacts['paths']['rom']).read_bytes(),s)
                    report['captures'].append(dict(label=stem,hardware=snap,regions=checks))
        report['artifacts_after']={k:fp.sha(v) for k,v in artifacts['paths'].items()}
        if report['artifacts_after']!=artifacts['hashes']:raise ValueError('artifacts changed')
        report['status']='DIAGNOSTIC_CAPTURED_NOT_VISUAL_ACCEPTANCE'
    except Exception as exc:report['error']=f'{type(exc).__name__}: {exc}'
    finally:(folder/'report.json').write_text(json.dumps(report,indent=2,default=str)+'\n')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true');parser.add_argument('--preflight',action='store_true')
    for key in ('rom','msu','symbols','environment'):parser.add_argument('--'+key+'-sha256')
    parser.add_argument('--symbols',default=str(fp.ROOT/'src/main.sym'))
    parser.add_argument('--environment',default=str(fp.ROOT/'src/generated/stage_environment_materialization.json'))
    parser.add_argument('--output',type=Path,default=fp.ROOT/'out/s8_static5a_native_01')
    args=parser.parse_args(argv);report=dict(status='PLAN_ONLY',native_executed=False)
    try:
        if args.run or args.preflight:
            import build_rom
            stage,cfg=next((i,c) for i,c in enumerate(build_rom.STAGE_CONFIGS)
                          if c['source_level'].replace('\\','/').lower()=='data/normal/5a.txt')
            s,_,artifacts=fp.preflight(args,fp.source_plan())
            media=packed_static(Path(artifacts['paths']['msu']).read_bytes(),stage)
            report.update(stage=stage,source=cfg['source_level'],artifacts=artifacts,status='PREFLIGHT_PASS_NOT_NATIVE')
            if args.run:run(args,s,artifacts,media,report)
    except Exception as exc:report.update(status='FAIL',error=f'{type(exc).__name__}: {exc}')
    print(json.dumps(report,indent=2,default=str));return int(report['status']=='FAIL')


if __name__=='__main__':sys.exit(main())
