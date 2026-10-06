"""Measure native SA-1 type-2 packing and S-CPU VRAM delivery for 2/4/8bpp."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from actor_s5_entity_fixture import symbols
from _harness import McpSession,MESEN_EXE,_free_tcp_port
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bor_compile'))
from bg_component_residency import encode


def pattern_tiles(count=128):
    rng=np.random.default_rng(4086)
    pixels=rng.integers(0,256,(count,8,8),dtype=np.uint8)
    pixels[:4]=np.arange(256,dtype=np.uint8).reshape(4,8,8)
    return pixels


def build(folder,count=128):
    pixels=pattern_tiles(count)
    expected=b''.join(encode(tile,bpp) for bpp in (8,4,2) for tile in pixels)
    worker='''
.bank 1
.org $9000
CharacterWorker:
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
    lda #0
    pha
    plb
    rep #$20
.a16
    lda #0
    sta $02
'''
    for bpp,fmt in ((8,0),(4,1),(2,2)):
        worker+='''
    sep #$20
.a8
    lda #0
    sta.w $2230
    lda #$A0
    sta.w $2230
    lda #%d
    sta.w $2231
    lda #0
    sta.w $2235
    lda #$36
    sta.w $2236
    rep #$20
.a16
    lda #0
    sta $04
    ldx #0
Character%dStart:
.a16
.i16
Character%dTile:
    ldy #4
Character%dRows:
'''%(fmt,bpp,bpp,bpp)
        input_base=0x048000+(8,4,2).index(bpp)*pixels.size
        for reg in range(0x2240,0x2250,2):
            worker+='    lda.l $%06X,x\n    sta.w $%04X\n    inx\n    inx\n'%(input_base,reg)
        worker+='''
    dey
    beq Character%dRowsDone
    brl Character%dRows
Character%dRowsDone:
    phx
    lda $04
    and #1
'''%(bpp,bpp,bpp)
        worker+='    asl a\n'*(3+{2:1,4:2,8:3}[bpp])
        worker+='''
    clc
    adc #$3600
    tay
    clc
    adc #%d
    sta $08
    ldx $02
Character%dCopy:
    lda.w $0000,y
    sta.l $420000,x
    inx
    inx
    iny
    iny
    cpy $08
    bne Character%dCopy
    stx $02
    plx
    lda $04
    inc a
    sta $04
    cmp #%d
    beq Character%dDone
    brl Character%dTile
Character%dDone:
'''%(bpp*8,bpp,bpp,count,bpp,bpp,bpp)
    worker+='''
    sep #$20
.a8
    lda #0
    sta.w $2230
    rep #$20
.a16
    lda #$B4AC
    sta.l $413FF0
CharacterWorkerDone:
    stp
CharacterWorkerEnd:
'''
    main='''
.snes
.bank 1
.org $8000
Main:
.a16
.i16
    sei
    clc
    xce
    rep #$30
    ldx #$1FFF
    txs
    sep #$20
.a8
    lda #0
    sta.w $4200
    sta.w $420C
    lda #$80
    sta.w $2100
    lda #$FF
    sta.w $2229
    lda #$80
    sta.w $2226
    lda #0
    sta.w $2228
    rep #$20
.a16
    lda #0
    sta.l $413FF0
    sta.l $413FF2
    sep #$20
.a8
    lda #$20
    sta.w $2200
    rep #$20
.a16
    ldx #0
CopyWorker:
    sep #$20
.a8
    lda.l CharacterWorker,x
    sta.l $003200,x
    rep #$20
.a16
    inx
    cpx #(CharacterWorkerEnd-CharacterWorker)
    bne CopyWorker
    sep #$20
.a8
    lda #0
    sta.w $2203
    lda #$32
    sta.w $2204
    lda #0
    sta.w $2200
    rep #$20
.a16
WaitWorker:
    lda.l $413FF0
    cmp #$B4AC
    bne WaitWorker
    sep #$20
.a8
    lda #$80
    sta.w $2115
    rep #$20
.a16
    lda #0
    sta.w $2116
    lda #$1801
    sta.w $4370
    lda #$0042
    sta.w $4374
    lda #0
    sta.w $4372
    lda #%d
    sta.w $4375
CharacterVramStart:
    sep #$20
.a8
    lda #$80
    sta.w $420B
    rep #$20
.a16
CharacterVramDone:
    lda #$B4AD
    sta.l $413FF2
    stp
'''%len(expected)
    asm=folder/'conversion.pasm';asm.write_text(main+worker)
    process=subprocess.run([r'C:\Users\chad\.dotnet\dotnet.exe',r'E:\gh\poppy-astrobleem\src\Poppy.CLI\bin\Release\net10.0\poppy.dll',str(asm),
                            '--output',str(folder/'conversion.bin'),'--symbols',str(folder/'conversion.sym'),'--no-pansy'],capture_output=True,text=True)
    (folder/'poppy.log').write_text(process.stdout+process.stderr)
    if process.returncode:raise ValueError('CHARACTER_CONVERSION_ASSEMBLY')
    sy=symbols(folder/'conversion.sym');raw=(folder/'conversion.bin').read_bytes()
    worker_size=sy['CharacterWorkerEnd']-sy['CharacterWorker']
    if worker_size>1024:raise ValueError('CHARACTER_WORKER_BUFFER_OVERLAP')
    rom=bytearray([255])*262144;rom[:len(raw)]=raw
    rom[:4]=bytes.fromhex('5c 00 80 01')
    for i,bpp in enumerate((8,4,2)):
        start=0x20000+i*pixels.size
        rom[start:start+pixels.size]=(pixels&((1<<bpp)-1)).tobytes()
    rom[0x7fc0:0x7fd5]=b'M4 SA1 CHARACTER'.ljust(21);rom[0x7fd5:0x7fdc]=bytes([0x23,0x35,8,8,1,0x33,0])
    rom[0x7ffc:0x7ffe]=struct.pack('<H',0x8000)
    return bytes(rom),pixels,expected,sy


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--debug',action='store_true');a=p.parse_args()
    folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    rom,pixels,expected,sy=build(folder);path=folder/'proof.sfc';path.write_bytes(rom)
    script='''local seen={}
local function sample(a,v)
 if not seen[a] then local s=emu.getState();emu.log('CHARCONV|'..a..'|'..s.masterClock);seen[a]=true end
end
'''
    for bpp in (8,4,2):
        for phase in ('Start','Done'):
            address=0x3200+sy[f'Character{bpp}{phase}']-sy['CharacterWorker']
            script+=f'emu.addMemoryCallback(sample,emu.callbackType.exec,{address},{address},emu.cpuType.sa1,emu.memType.sa1Memory)\n'
    for name in ('CharacterVramStart','CharacterVramDone'):
        address=32768+(sy[name]&65535)-32768
        script+=f'emu.addMemoryCallback(sample,emu.callbackType.exec,{address},{address},emu.cpuType.snes,emu.memType.snesPrgRom)\n'
    if a.debug:
        script+='''local hits=0
emu.addMemoryCallback(function(a,v)
 if hits<240 then
  hits=hits+1;local s=emu.getState();local r={a}
  for _,k in ipairs({'pc','a','x','y','sp','d','dbr','ps'}) do r[#r+1]=s['cart.coprocessor.cpu.'..k] or -1 end
  r[#r+1]=emu.read(2,emu.memType.sa1InternalRam);r[#r+1]=emu.read(8,emu.memType.sa1InternalRam)
  emu.log('CONVDEBUG|'..table.concat(r,','))
 end
end,emu.callbackType.exec,0x3200,0x343c,emu.cpuType.sa1,emu.memType.sa1Memory)
'''
    lua=folder/'observer.lua';lua.write_text(script)
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,'--donotsavesettings',str(lua)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
    with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        for _ in range(50):
            m.tool('run_frames',{'count':1})
            marker=m.read_memory('SnesMemory',0x413ff0,4)
            if marker==bytes.fromhex('ac b4 ad b4'):break
        actual=m.read_memory('SnesMemory',0x420000,len(expected))
        vram=m.read_memory('SnesVideoRam',0,len(expected))
        (folder/'iram.bin').write_bytes(m.read_memory('Sa1InternalRam',0,2048))
        (folder/'cpu-state.json').write_text(json.dumps(dict(snes=m.get_cpu_state(),sa1=m.get_cpu_state('Sa1')),indent=2))
    events=[list(map(int,line.split('CHARCONV|',1)[1].split('|'))) for line in (folder/'mesen.log').read_text().splitlines() if 'CHARCONV|' in line]
    result=dict(schema='BYOR_NATIVE_SA1_CHARACTER_CONVERSION_V1',rom_sha256=hashlib.sha256(rom).hexdigest(),
                packed_bytes=len(expected),tiles_per_bpp=len(pixels),bpp=[8,4,2],bwram_exact=actual==expected,vram_exact=vram==expected,
                marker_hex=marker.hex(),events=events,no_color_reduction=True,
                scope='Native type-2 SA-1 conversion and forced-blank VRAM DMA. No SCREEN input, palette, display cadence, production IRQ/audio or live world admission.')
    result['conversion_master_clocks_by_bpp']={str(bpp):events[i*2+1][1]-events[i*2][1] for i,bpp in enumerate((8,4,2))} if len(events)==8 else None
    result['pass']=result['bwram_exact'] and result['vram_exact'] and len(events)==8 and marker==bytes.fromhex('ac b4 ad b4')
    (folder/'packed.chr').write_bytes(actual);(folder/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    if not result['pass']:raise SystemExit(1)


if __name__=='__main__':main()
