"""Native lossless SA-1 bitmap-to-VRAM DMA without per-tile CPU copying."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from types import SimpleNamespace
from unittest.mock import patch
from actor_s5_entity_fixture import symbols
from _harness import McpSession,MESEN_EXE,_free_tcp_port
from m4_sa1_character_conversion_native import pattern_tiles,encode
from sa1_character_conversion import bitmap_bytes,type1_descriptor


def build(folder,columns=16):
    pixels=pattern_tiles();input_data=bytearray();expected=bytearray();descriptors=[]
    for bpp in (8,4,2):
        tiles=pixels&((1<<bpp)-1)
        raw=bitmap_bytes(tiles,bpp,columns)
        descriptors.append(type1_descriptor(0x420000+len(input_data),bpp,columns,len(pixels),len(expected)))
        input_data.extend(raw);expected.extend(b''.join(encode(t,bpp) for t in tiles))
    asm='''
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
    lda #$20
    sta.w $2200
    rep #$20
.a16
    lda #0
    sta.l $413FF0
    sta.l $413FF2
    ldx #0
CopyInput:
    lda.l $048000,x
    sta.l $420000,x
    inx
    inx
    cpx #%d
    bne CopyInput
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
'''%len(input_data)
    for d in descriptors:
        bpp=d['bpp']
        for addr,value in [(0x2231,d['cdma']),(0x2232,d['source']&255),(0x2233,(d['source']>>8)&255),(0x2234,d['source']>>16),
                           (0x2235,d['iram']&255),(0x2236,d['iram']>>8)]:
            asm+='    lda #$%02X\n    sta.w $%04X\n'%(value,addr)
        asm+='''
WaitChr%d:
    lda.w $2300
    and #$20
    beq WaitChr%d
    lda #$20
    sta.w $2202
    rep #$20
.a16
    lda #%d
    sta.w $2116
    lda #$1801
    sta.w $4370
    lda #$0042
    sta.w $4374
    lda #%d
    sta.w $4372
    lda #%d
    sta.w $4375
Character%dStart:
    sep #$20
.a8
    lda #$80
    sta.w $420B
    nop
Character%dDone:
    lda #$80
    sta.w $2231
'''%(bpp,bpp,d['vram_word_address'],d['source']&65535,d['bytes'],bpp,bpp)
    asm+='''
    rep #$20
.a16
    lda #$B4AD
    sta.l $413FF2
    stp
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
    sep #$20
.a8
    lda #$FF
    sta.l $00222A
    lda #$80
    sta.l $002227
    lda #$B0
    sta.l $002230
    rep #$20
.a16
    lda #$B4AC
    sta.l $413FF0
    stp
CharacterWorkerEnd:
'''
    source=folder/'type1.pasm';source.write_text(asm)
    process=subprocess.run([r'C:\Users\chad\.dotnet\dotnet.exe',r'E:\gh\poppy-astrobleem\src\Poppy.CLI\bin\Release\net10.0\poppy.dll',str(source),
                            '--output',str(folder/'type1.bin'),'--symbols',str(folder/'type1.sym'),'--no-pansy'],capture_output=True,text=True)
    (folder/'poppy.log').write_text(process.stdout+process.stderr)
    if process.returncode:raise ValueError('CHARACTER_TYPE1_ASSEMBLY')
    sy=symbols(folder/'type1.sym');raw=(folder/'type1.bin').read_bytes()
    rom=bytearray([255])*262144;rom[:len(raw)]=raw;rom[:4]=bytes.fromhex('5c 00 80 01')
    rom[0x20000:0x20000+len(input_data)]=input_data
    rom[0x7fc0:0x7fd5]=b'M4 SA1 TYPE1'.ljust(21);rom[0x7fd5:0x7fdc]=bytes([0x23,0x35,8,8,1,0x33,0])
    rom[0x7ffc:0x7ffe]=struct.pack('<H',0x8000)
    return bytes(rom),bytes(input_data),bytes(expected),sy,descriptors


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--columns',type=int,choices=(1,2,4,8,16,32),default=16);a=p.parse_args()
    folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
    rom,chunky,expected,sy,descriptors=build(folder,a.columns);path=folder/'proof.sfc';path.write_bytes(rom)
    script="local function sample(a,v) local s=emu.getState();emu.log('CHARCONV|'..a..'|'..s.masterClock) end\n"
    for bpp in (8,4,2):
        for phase in ('Start','Done'):
            address=sy[f'Character{bpp}{phase}']&65535
            script+=f'emu.addMemoryCallback(sample,emu.callbackType.exec,{address},{address},emu.cpuType.snes,emu.memType.snesPrgRom)\n'
    lua=folder/'observer.lua';lua.write_text(script)
    class Observed(McpSession):
        def __enter__(self):
            import mesen_mcp.session as module
            def launch(argv,**kwargs):return subprocess.Popen([*argv,'--donotsavesettings',str(lua)],**kwargs)
            with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
    with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log') as m:
        for _ in range(30):
            m.tool('run_frames',{'count':1});marker=m.read_memory('SnesMemory',0x413ff0,4)
            if marker==bytes.fromhex('ac b4 ad b4'):break
        actual=m.read_memory('SnesVideoRam',0,len(expected))
        retained=m.read_memory('SnesMemory',0x420000,len(chunky))
        (folder/'cpu-state.json').write_text(json.dumps(dict(snes=m.get_cpu_state(),sa1=m.get_cpu_state('Sa1')),indent=2))
    events=[list(map(int,line.split('CHARCONV|',1)[1].split('|'))) for line in (folder/'mesen.log').read_text().splitlines() if 'CHARCONV|' in line]
    result=dict(schema='BYOR_NATIVE_SA1_TYPE1_V1',rom_sha256=hashlib.sha256(rom).hexdigest(),descriptors=descriptors,
                chunky_bwram_unchanged=retained==chunky,vram_exact=actual==expected,marker_hex=marker.hex(),events=events,
                packed_bytes=len(expected),conversion_master_clocks_by_bpp={str(bpp):events[i*2+1][1]-events[i*2][1] for i,bpp in enumerate((8,4,2))} if len(events)==6 else None,
                no_color_reduction=True,scope='128 lossless source-neutral tiles per format with S-CPU type-1 character DMA. No SCREEN, source palette, VBlank cadence, live world or production contention admission.')
    timings=result['conversion_master_clocks_by_bpp']
    result['transfer_timing_verified']=timings is not None and all(timings[str(d['bpp'])]>=d['bytes']*8 for d in descriptors)
    result['pass']=result['chunky_bwram_unchanged'] and result['vram_exact'] and result['transfer_timing_verified'] and len(events)==6 and marker==bytes.fromhex('ac b4 ad b4')
    (folder/'packed.chr').write_bytes(actual);(folder/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    if not result['pass']:raise SystemExit(1)


if __name__=='__main__':main()
