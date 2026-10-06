"""Drive component BG pixels from native SCREEN arithmetic and type-1 DMA."""
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
from source_screen_components import derive,projection_tables,tile_cache
from sa1_character_conversion import type1_descriptor


def combine(raw,report,assets,source,stage,scene,folder,sleep_host=False):
    high=np.fromfile(assets/'indices.bin',dtype=np.uint8).reshape(224,256)+3
    low=np.fromfile(assets/'low_indices.bin',dtype=np.uint8).reshape(224,256)
    expected=np.fromfile(assets/'expected.rgb555',dtype='<u2').reshape(224,256)
    records,lookup,high_boot,low_boot,detail=derive(source,stage,scene,high,low,expected)
    prefix=raw[0x8000:0x8400];end=prefix.find(bytes([255])*32)
    code=bytearray(prefix[:end]);marker=code.find(bytes.fromhex('a9 0f 8d 00 21'))
    if end<0 or marker<0 or code[-3]!=0x4c:raise ValueError('SCREEN_FEED_BOOT_CONTRACT')
    target=struct.unpack_from('<H',code,len(code)-2)[0]
    if target<0x8000+marker:raise ValueError('SCREEN_FEED_BOOT_BACKEDGE')
    # Battery-backed BW-RAM may contain a prior proof's completion marker.
    # Clear it at cold entry, before the original multi-field CHR load.
    cold=bytes.fromhex('a9 80 8d 26 22 c2 20 a9 00 00 8f f0 3f 41 8f f2 3f 41 e2 20')
    code[-2:]=struct.pack('<H',target+4+len(cold));code[marker:marker]=bytes.fromhex('22 00 00 ed')
    code[11:11]=cold
    if len(code)>1024:raise ValueError('SCREEN_FEED_BOOT_OVERLAP')
    helper='''
.snes
.bank 90
.org $8000
ScreenFeedHost:
.a8
.i16
    php
    rep #$30
.a16
    pha
    phx
    phy
    phb
    phd
    lda #0
    tcd
    sep #$20
.a8
    lda #0
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
'''
    for name,rom_bank,bw_bank,size in [('High',0xf0,0x42,len(high_boot)),('Low',0xf1,0x43,len(low_boot))]:
        helper+='''
    ldx #0
ScreenCopy%s:
    lda.l $%02X0000,x
    sta.l $%02X0000,x
    inx
    inx
    cpx #%d
    bne ScreenCopy%s
'''%(name,rom_bank,bw_bank,size,name)
    helper+='''
    ldx #0
ScreenCopyWorker:
    sep #$20
.a8
    lda.l $ED8000,x
    sta.l $003300,x
    rep #$20
.a16
    inx
    cpx #(ScreenWorkerEnd-ScreenWorker)
    bne ScreenCopyWorker
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
ScreenWaitWorker:
    lda.l $413FF0
    cmp #$B4AF
    beq ScreenWorkerReady
    cmp #$B4E0
    bne ScreenWaitWorker
    stp
ScreenWorkerReady:
    sep #$20
.a8
    lda #$80
    sta.w $2115
'''
    descriptors=[type1_descriptor(0x420000,8,1,len(high_boot)//64,0),
                 type1_descriptor(0x430000,2,1,len(low_boot)//16,report['low_chr_vram_base'])]
    for d in descriptors:
        bpp=d['bpp']
        for addr,value in [(0x2231,d['cdma']),(0x2232,d['source']&255),(0x2233,(d['source']>>8)&255),(0x2234,d['source']>>16),
                           (0x2235,d['iram']&255),(0x2236,d['iram']>>8)]:
            helper+='    lda #$%02X\n    sta.w $%04X\n'%(value,addr)
        helper+='''
ScreenWaitChr%d:
    lda.w $2300
    and #$20
    beq ScreenWaitChr%d
    lda #$20
    sta.w $2202
    rep #$20
.a16
    lda #%d
    sta.w $2116
    lda #$1801
    sta.w $4370
    lda #%d
    sta.w $4374
    lda #0
    sta.w $4372
    lda #%d
    sta.w $4375
ScreenTransfer%dStart:
    sep #$20
.a8
    lda #$80
    sta.w $420B
    nop
ScreenTransfer%dDone:
    lda #$80
    sta.w $2231
'''%(bpp,bpp,d['vram_word_address'],d['source']>>16,d['bytes'],bpp,bpp)
    helper+='''
    rep #$20
.a16
    lda #$B4B2
    sta.l $413FF2
    sep #$20
.a8
    lda #1
    sta.w $420C
    rep #$30
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    rtl
.bank 91
.org $8000
ScreenWorker:
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
    lda #$EC
    pha
    plb
    lda #$B0
    sta.l $002230
    lda #$42
    sta $18
    lda #$43
    sta $1B
    ldy #0
ScreenWorkerStart:
ScreenWorkerPixel:
.a8
.i16
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
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    ora.w $000A,y
    rep #$20
.a16
    and #$00FF
    tax
    sep #$20
.a8
    lda.l $ECFF00,x
    sta $02
    lda.w $000B,y
    sta $03
    rep #$20
.a16
    lda.w $0006,y
    sta $16
    lda.w $0008,y
    sta $19
    lda.w $000C,y
    sta $10
    sep #$20
.a8
    lda.w $000E,y
    sta $12
    phy
    rep #$20
.a16
    lda $00
    and #$1FFF
    tay
    sep #$20
.a8
    lda [$10],y
    bne ScreenWorkerColorAdmitted
    rep #$20
.a16
    lda #$B4E0
    sta.l $413FF0
    stp
ScreenWorkerColorAdmitted:
.a8
.i16
    sta [$16]
    lda [$19]
    and $03
    ora $02
    sta [$19]
    ply
    rep #$20
.a16
    tya
    clc
    adc #16
    tay
    cpy #%d
    bcs ScreenWorkerDone
    sep #$20
.a8
    brl ScreenWorkerPixel
ScreenWorkerDone:
.a16
.i16
    lda #$B4AF
    sta.l $413FF0
    stp
ScreenWorkerEnd:
'''%len(records)
    if sleep_host:
        helper=helper.replace('    lda #0\n    sta.w $2200\n    rep #$20\n.a16\nScreenWaitWorker:',
            '    lda #$80\n    sta.w $2201\n    lda #0\n    sta.w $2200\n    rep #$20\n.a16\nScreenWaitWorker:')
        helper=helper.replace('    bne ScreenWaitWorker\n    stp','    beq ScreenHostFault\n    wai\n    brl ScreenWaitWorker\nScreenHostFault:\n    stp')
        helper=helper.replace('ScreenWorkerReady:\n    sep #$20\n.a8',
            'ScreenWorkerReady:\n    sep #$20\n.a8\n    lda #$80\n    sta.w $2202\n    lda #0\n    sta.w $2201')
        helper=helper.replace('    sta.l $413FF0\n    stp',
            '    sta.l $413FF0\n    sep #$20\n.a8\n    lda #$80\n    sta.l $002209\n    stp')
    asm=folder/'feed.pasm';asm.write_text(helper)
    process=subprocess.run([r'C:\Users\chad\.dotnet\dotnet.exe',r'E:\gh\poppy-astrobleem\src\Poppy.CLI\bin\Release\net10.0\poppy.dll',str(asm),
                            '--output',str(folder/'feed.bin'),'--symbols',str(folder/'feed.sym'),'--no-pansy'],capture_output=True,text=True)
    (folder/'poppy.log').write_text(process.stdout+process.stderr)
    if process.returncode:raise ValueError('SCREEN_FEED_ASSEMBLY')
    sy=symbols(folder/'feed.sym');worker_size=sy['ScreenWorkerEnd']-sy['ScreenWorker']
    if worker_size>0x300:raise ValueError('SCREEN_FEED_IRAM_CODE_BUFFER_OVERLAP')
    binary=(folder/'feed.bin').read_bytes();rom=bytearray([255])*4194304
    rom[:len(raw)]=raw;rom[0x8000:0x8400]=bytes([255])*1024;rom[0x8000:0x8000+len(code)]=code
    rom[0x2d0000:len(binary)]=binary[0x2d0000:]
    rom[0x40000:0x80000]=projection_tables();rom[0x80000:0x80000+len(lookup)]=lookup
    rom[0x2c0000:0x2c0000+len(records)]=records
    rom[0x2cff00:0x2cff10]=bytes(v<<(group*2) for group in range(4) for v in range(4))
    rom[0x300000:0x300000+len(high_boot)]=high_boot;rom[0x310000:0x310000+len(low_boot)]=low_boot
    rom[0x7fd5:0x7fdc]=bytes([0x23,0x35,12,8,1,0x33,0])
    detail.update(descriptors=descriptors,worker_bytes=worker_size,record_bytes=len(records),palette_lookup_bytes=len(lookup),sleep_host=sleep_host,
                  packed_native_input_sha256=hashlib.sha256(records).hexdigest(),projection_tables_sha256=hashlib.sha256(projection_tables()).hexdigest())
    return bytes(rom),sy,detail


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','stage'):p.add_argument('--'+name,required=True)
    for name in ('scene','components','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--sleep-host',action='store_true')
    a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    compile_base=bg.compile_rom;detail={};report=json.loads(a.components.read_text());assets=a.components.parent
    def compile_feed(*args,**kwargs):
        raw,trace,resources=compile_base(*args,**kwargs)
        raw,sy,data=combine(raw,report,assets,Source(a.source),a.stage,json.loads(a.scene.read_text()),folder,a.sleep_host)
        detail.update(symbols=sy,inputs=data);resources.update(native_screen_feed=True)
        return raw,trace,resources
    class Extra(McpSession):
        def __enter__(self):
            sy=detail['symbols'];script='local screen_feed_seen={}\n'
            for name in ('ScreenWorkerStart','ScreenWorkerDone'):
                address=0x3300+sy[name]-sy['ScreenWorker']
                script+=f"emu.addMemoryCallback(function(a,v) if not screen_feed_seen[a] then local s=emu.getState();emu.log('SCREENFEED|'..a..'|'..s.masterClock);screen_feed_seen[a]=true end end,emu.callbackType.exec,{address},{address},emu.cpuType.sa1,emu.memType.sa1Memory)\n"
            for bpp in (8,2):
                for phase in ('Start','Done'):
                    address=0x2d0000+(sy[f'ScreenTransfer{bpp}{phase}']&65535)-32768
                    script+=f"emu.addMemoryCallback(function(a,v) local s=emu.getState();emu.log('SCREENFEED|'..a..'|'..s.masterClock) end,emu.callbackType.exec,{address},{address},emu.cpuType.snes,emu.memType.snesPrgRom)\n"
            with (folder/'observer.lua').open('a') as f:f.write(script)
            super().__enter__()
            try:
                for _ in range(80):
                    self.tool('run_frames',{'count':1})
                    marker=self.read_memory('SnesMemory',0x413ff0,4)
                    if marker==bytes.fromhex('af b4 b2 b4'):break
                    if marker[:2]==bytes.fromhex('e0 b4'):raise ValueError('NATIVE_SCREEN_PALETTE_ADMISSION_FAULT')
                if marker!=bytes.fromhex('af b4 b2 b4'):raise ValueError('NATIVE_SCREEN_FEED_NOT_READY')
            except Exception:
                (folder/'feed-failure.json').write_text(json.dumps(dict(snes=self.get_cpu_state(),sa1=self.get_cpu_state('Sa1'),marker=marker.hex()),indent=2))
                super().__exit__(*sys.exc_info())
                raise
            return self
        def __exit__(self,*args):
            data=detail['inputs']
            (folder/'native-high.chunky').write_bytes(self.read_memory('SnesMemory',0x420000,data['high_tiles']*64))
            (folder/'native-low.chunky').write_bytes(self.read_memory('SnesMemory',0x430000,data['low_tiles']*16))
            (folder/'native-marker.bin').write_bytes(self.read_memory('SnesMemory',0x413ff0,4))
            return super().__exit__(*args)
    argv=['m4_bg_components_native','--report',str(a.components),'--assets',str(assets),'--output',str(folder),'--timer','160']
    with patch.object(bg,'compile_rom',compile_feed),patch.object(bg,'McpSession',Extra),patch.object(sys,'argv',argv):
        try:bg.main()
        except SystemExit as error:
            if error.code!=1:raise
    result=json.loads((folder/'result.json').read_text())
    events=[list(map(int,line.split('SCREENFEED|',1)[1].split('|'))) for line in (folder/'mesen.log').read_text().splitlines() if 'SCREENFEED|' in line]
    result.update(source_screen_inputs=detail['inputs'],native_events=events,
                  native_screen_component_job_clocks=events[1][1]-events[0][1] if len(events)==6 else None,
                  no_color_reduction=True,scope='Native SCREEN projected into component indices, type-1 converted and displayed on a fixed source-derived underlay. Forced-blank startup; no moving world, online palette admission or source-cadence compositor claim.')
    original_high=tile_cache(np.fromfile(assets/'indices.bin',dtype=np.uint8).reshape(224,256)+3,8)[0]
    original_low=tile_cache(np.fromfile(assets/'low_indices.bin',dtype=np.uint8).reshape(224,256),2)[0]
    result['native_chunky_identity_verified']=((folder/'native-high.chunky').read_bytes()==original_high and (folder/'native-low.chunky').read_bytes()==original_low)
    result['pass']=result['pass'] and len(events)==6 and result['native_chunky_identity_verified']
    (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['pass','native_screen_component_job_clocks','scope','no_color_reduction']}))
    if not result['pass']:raise SystemExit(1)


if __name__=='__main__':main()
