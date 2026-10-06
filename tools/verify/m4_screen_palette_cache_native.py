"""Feed a compiled BG schedule with cached native RGB8 SCREEN colors."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
from unittest.mock import patch
import numpy as np
import m4_bg_components_native as bg
from actor_s5_entity_fixture import symbols
from _harness import McpSession
from compiler import Source
from source_screen_components import derive as pixels
from source_screen_palette import derive,projection_tables


def combine(raw,report,assets,source,stage,scene,folder,unroll_bindings=False,active_repeat=False):
    high=np.fromfile(assets/'indices.bin',dtype=np.uint8).reshape(224,256)+3
    low=np.fromfile(assets/'low_indices.bin',dtype=np.uint8).reshape(224,256)
    image=np.fromfile(assets/'expected.rgb555',dtype='<u2').reshape(224,256)
    records,*_=pixels(source,stage,scene,high,low,image)
    pairs,bindings,expected,detail=derive(records,report,json.loads((assets/'initial.json').read_text()))
    prefix=raw[0x8000:0x8400];end=prefix.find(bytes([255])*32);code=bytearray(prefix[:end])
    marker=code.find(bytes.fromhex('a9 0f 8d 00 21'))
    if end<0 or marker<0 or code[-3]!=0x4c:raise ValueError('SCREEN_CACHE_BOOT_CONTRACT')
    for old,new in [('a9 08 8d 72 43 a9 90 8d 73 43 a9 05 8d 74 43','a9 08 8d 72 43 a9 00 8d 73 43 a9 43 8d 74 43'),
                    ('a9 00 8d 72 43 a9 80 8d 73 43 a9 06 8d 74 43','a9 00 8d 72 43 a9 20 8d 73 43 a9 43 8d 74 43')]:
        if code.count(bytes.fromhex(old))!=1:raise ValueError('SCREEN_CACHE_DMA_BINDING_NOT_UNIQUE')
        code=code.replace(bytes.fromhex(old),bytes.fromhex(new))
    cold=bytes.fromhex('a9 80 8d 26 22 c2 20 a9 00 00 8f f0 3f 41 8f f2 3f 41 e2 20')
    target=struct.unpack_from('<H',code,len(code)-2)[0]
    restart=bytes.fromhex('a9 20 8d 00 22 c2 20 a9 00 00 8f f0 3f 41 e2 20') if active_repeat else b''
    release=bytes.fromhex('9c 00 22') if active_repeat else b''
    code[-2:]=struct.pack('<H',target+len(cold)+4+len(restart))
    if active_repeat:
        irq_setup=code.find(bytes.fromhex('a9 10 8d 00 42 58'))
        if irq_setup<0:raise ValueError('SCREEN_CACHE_ACTIVE_IRQ_SETUP')
        # Release only after unblank and IRQ/HDMA activation. Later fields
        # write zero again without a reset edge, so the worker runs once.
        code[irq_setup+5:irq_setup+5]=release
    code[marker:marker]=bytes.fromhex('22 00 00 c9')+restart
    code[11:11]=cold
    asm='''
.snes
.bank 18
.org $8000
ScreenCacheHost:
.a8
.i16
    php
    rep #$30
.a16
    pha
    phx
    phy
    phb
    lda #0
    sep #$20
.a8
    pha
    plb
    lda #$FF
    sta.w $2229
    lda #$80
    sta.w $2226
    lda #0
    sta.w $2228
    lda #$20
    sta.w $2200
    rep #$20
.a16
    lda #0
    sta.l $413FF0
    sta.l $413FF2
    ldx #0
ScreenCacheCopy:
    sep #$20
.a8
    lda.l $C98000,x
    sta.l $003300,x
    rep #$20
.a16
    inx
    cpx #(ScreenCacheWorkerEnd-ScreenCacheWorker)
    bne ScreenCacheCopy
    sep #$20
.a8
    lda #0
    sta.w $2203
    lda #$33
    sta.w $2204
    lda #0
    sta.w $2200
    rep #$20
.a16
ScreenCacheWait:
    lda.l $413FF0
    cmp #$B4BF
    bne ScreenCacheWait
    sep #$20
.a8
    lda #0
    sta.w $2121
    rep #$20
.a16
    lda #$2200
    sta.w $4370
    lda #$0043
    sta.w $4374
    lda #0
    sta.w $4372
    lda #512
    sta.w $4375
    sep #$20
.a8
    lda #$80
    sta.w $420B
    nop
    rep #$20
.a16
    lda #$B4B2
    sta.l $413FF2
    plb
    ply
    plx
    pla
    plp
    rtl
.bank 19
.org $8000
ScreenCacheWorker:
.a16
.i16
    sei
    clc
    xce
    rep #$30
    ldx #$37FF
    txs
    lda #$3000
    tcd
    sep #$20
.a8
    lda #$FF
    sta.l $00222A
    lda #$80
    sta.l $002227
    lda #$C8
    pha
    plb
    rep #$20
.a16
    lda #0
    sta $20
    ldy #0
ScreenCacheStart:
    nop
ScreenCachePair:
    sep #$20
.a8
    ldx.w $0000,y
    lda.l $C40000,x
    sta $00
    ldx.w $0002,y
    lda.l $C50000,x
    ora $00
    sta $00
    lda.l $C60000,x
    sta $01
    ldx.w $0004,y
    lda.l $C70000,x
    ora $01
    sta $01
    rep #$20
.a16
    ldx $20
    lda $00
    sta.l $420000,x
    inx
    inx
    stx $20
    tya
    clc
    adc #6
    tay
    cpy #%d
    bcs ScreenCachePairsDone
    brl ScreenCachePair
ScreenCachePairsDone:
.a16
.i16
    ldx #0
    ldy #0
ScreenCacheBinding:
    lda.w $8002,y
    beq ScreenCacheConstant
    phx
    ldx.w $8000,y
    lda.l $420000,x
    and #$FBDF
    plx
    bra ScreenCacheWrite
ScreenCacheConstant:
    lda.w $8000,y
ScreenCacheWrite:
    sta.l $430000,x
    inx
    inx
    cpx #512
    bne ScreenCacheNoGap
    ldx #$2000
ScreenCacheNoGap:
    iny
    iny
    iny
    iny
    cpy #%d
    bcc ScreenCacheBinding
ScreenCacheDone:
    lda #$B4BF
    sta.l $413FF0
    stp
ScreenCacheWorkerEnd:
'''%(len(pairs),len(bindings))
    if unroll_bindings:
        first=asm.index('ScreenCachePairsDone:\n')
        last=asm.index('ScreenCacheWorkerEnd:\n',first)
        asm=asm[:first]+'''ScreenCachePairsDone:
.a16
.i16
    jml $CA0000
ScreenCacheWorkerEnd:
'''+asm[last+len('ScreenCacheWorkerEnd:\n'):]
        asm+='''
.bank 20
.org $8000
ScreenCacheUnrollStart:
.a16
.i16
    sep #$20
.a8
    lda #$42
    pha
    plb
    rep #$20
.a16
'''
        used=7;bank=20
        for index,(value,native) in enumerate(struct.iter_unpack('<HH',bindings)):
            size=13 if native else 7
            if used+size>0x7f00:
                if bank!=20:raise ValueError('SCREEN_CACHE_UNROLL_BANK_CAPACITY')
                asm+='    jml $CA8000\n.bank 21\n.org $8000\nScreenCacheUnrollSecond:\n.a16\n.i16\n'
                bank=21;used=0
            destination=0x430000+index*2 if index<256 else 0x432000+(index-256)*2
            if native:asm+='    ldx #%d\n    lda.w $0000,x\n    and #$FBDF\n'%value
            else:asm+='    lda #%d\n'%value
            asm+='    sta.l $%06X\n'%destination;used+=size
        asm+='''ScreenCacheUnrollDone:
.a16
.i16
    lda #$B4BF
    sta.l $413FF0
    stp
'''
    source_asm=folder/'cache.pasm';source_asm.write_text(asm)
    process=subprocess.run([r'C:\Users\chad\.dotnet\dotnet.exe',r'E:\gh\poppy-astrobleem\src\Poppy.CLI\bin\Release\net10.0\poppy.dll',str(source_asm),
                            '--output',str(folder/'cache.bin'),'--symbols',str(folder/'cache.sym'),'--no-pansy'],capture_output=True,text=True)
    (folder/'poppy.log').write_text(process.stdout+process.stderr)
    if process.returncode:raise ValueError('SCREEN_CACHE_ASSEMBLY')
    sy=symbols(folder/'cache.sym');binary=(folder/'cache.bin').read_bytes()
    if sy['ScreenCacheWorkerEnd']-sy['ScreenCacheWorker']>0x400:raise ValueError('SCREEN_CACHE_IRAM_CAPACITY')
    rom=bytearray([255])*1048576;rom[:len(raw)]=raw;rom[0x8000:0x8400]=bytes([255])*1024;rom[0x8000:0x8000+len(code)]=code
    rom[0x90000:len(binary)]=binary[0x90000:];rom[0x40000:0x80000]=projection_tables()
    rom[0x80000:0x80000+len(pairs)]=pairs;rom[0x88000:0x88000+len(bindings)]=bindings
    # No precomputed effect high colors survive as an alternative source.
    rom[0x29008:0x291e0]=bytes(472)
    rom[0x30000:0x30000+detail['payload_bytes']]=bytes(detail['payload_bytes'])
    rom[0x7fd5:0x7fdc]=bytes([0x23,0x35,10,8,1,0x33,0])
    (folder/'expected-cache.rgb555').write_bytes(expected)
    detail.update(rom_source_pairs_sha256=hashlib.sha256(pairs).hexdigest(),bank0_production_growth=0,
                  unrolled_bindings=unroll_bindings,active_display_repeat=active_repeat)
    return bytes(rom),sy,detail


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','stage'):p.add_argument('--'+name,required=True)
    for name in ('scene','components','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--unroll-bindings',action='store_true')
    p.add_argument('--active-repeat',action='store_true',help='Repeat once while the displayed scene runs palette IRQ and dummy HDMA')
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    base=bg.compile_rom;detail={};report=json.loads(a.components.read_text());assets=a.components.parent
    def compile_cache(*args,**kwargs):
        raw,trace,resources=base(*args,**kwargs)
        raw,sy,data=combine(raw,report,assets,Source(a.source),a.stage,json.loads(a.scene.read_text()),folder,a.unroll_bindings,a.active_repeat)
        detail.update(symbols=sy,inputs=data);resources.update(native_screen_palette_cache=True)
        return raw,trace,resources
    class Extra(McpSession):
        def __enter__(self):
            sy=detail['symbols'];script='local screen_cache_active=0\n'
            script+='emu.addMemoryCallback(function(a,v) if v==15 then screen_cache_active=1 end end,emu.callbackType.write,0x2100,0x2100,emu.cpuType.snes,emu.memType.snesMemory)\n'
            for name in ('ScreenCacheStart','ScreenCachePairsDone','ScreenCacheUnrollDone' if a.unroll_bindings else 'ScreenCacheDone'):
                address=0x3300+sy[name]-sy['ScreenCacheWorker']
                if name=='ScreenCacheUnrollDone':address=0xca0000+((sy[name]>>16)-20)*32768+(sy[name]&65535)-32768
                script+=f"emu.addMemoryCallback(function(a,v) local s=emu.getState();emu.log('SCREENCACHE|'..a..'|'..s.masterClock..'|'..s['ppu.frameCount']..'|'..s['ppu.scanline']..'|'..screen_cache_active) end,emu.callbackType.exec,{address},{address},emu.cpuType.sa1,emu.memType.sa1Memory)\n"
            with (folder/'observer.lua').open('a') as f:f.write(script)
            super().__enter__()
            try:
                for _ in range(80):
                    self.tool('run_frames',{'count':1});marker=self.read_memory('SnesMemory',0x413ff0,4)
                    if marker==bytes.fromhex('bf b4 b2 b4'):break
                if marker!=bytes.fromhex('bf b4 b2 b4'):raise ValueError('NATIVE_SCREEN_CACHE_NOT_READY')
            except Exception:
                (folder/'cache-failure.json').write_text(json.dumps(dict(snes=self.get_cpu_state(),sa1=self.get_cpu_state('Sa1'),marker=marker.hex()),indent=2))
                super().__exit__(*sys.exc_info());raise
            return self
        def __exit__(self,*args):
            (folder/'native-cache.rgb555').write_bytes(self.read_memory('SnesMemory',0x420000,detail['inputs']['native_cache_bytes']))
            return super().__exit__(*args)
    argv=['m4_bg_components_native','--report',str(a.components),'--assets',str(assets),'--output',str(folder),'--timer','160']
    with patch.object(bg,'compile_rom',compile_cache),patch.object(bg,'McpSession',Extra),patch.object(sys,'argv',argv):
        try:bg.main()
        except SystemExit as error:
            if error.code!=1:raise
    r=json.loads((folder/'result.json').read_text())
    events=[list(map(int,l.split('SCREENCACHE|',1)[1].split('|'))) for l in (folder/'mesen.log').read_text().splitlines() if 'SCREENCACHE|' in l]
    cache_exact=(folder/'native-cache.rgb555').read_bytes()==(folder/'expected-cache.rgb555').read_bytes()
    count=6 if a.active_repeat else 3
    complete=len(events)==count
    first=3 if a.active_repeat else 0
    active_exact=not a.active_repeat or (complete and all(e[4]==1 for e in events[3:]) and all(e[4]==0 for e in events[:3]))
    r.update(cache_inputs=detail['inputs'],native_cache_identity_verified=cache_exact,native_job_events=events,
             native_job_master_clocks=events[first+2][1]-events[first][1] if complete else None,
             native_colour_pair_master_clocks=events[first+1][1]-events[first][1] if complete else None,
             active_display_repeat_verified=active_exact,
             scope='Native SCREEN color-pair cache binds CGRAM colors of a source-derived fixed context. Optional repeated job runs during active palette IRQ and dummy channel-0 HDMA. No moving-world underlay, online scheduling or production cadence/audio admission.')
    r['pass']=r['pass'] and cache_exact and complete and active_exact
    (folder/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r[k] for k in ['pass','native_cache_identity_verified','native_job_master_clocks','native_colour_pair_master_clocks','scope']}))
    if not r['pass']:raise SystemExit(1)


if __name__=='__main__':main()
