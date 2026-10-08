"""Native type-1 chunk reuse without source-world/physics RAM overwrite."""
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
from m4_sa1_character_conversion_type1_native import build as template
from sa1_character_conversion import bitmap_bytes,reused_workspace_descriptors


def build(folder):
 template(folder,16);asm=(folder/'type1.pasm').read_text()
 jobs=[dict(bpp=8,columns=16,tile_count=896,vram_byte_address=0),dict(bpp=2,columns=16,tile_count=512,vram_byte_address=57344)]
 ds=reused_workspace_descriptors(0x420000,0xd800,jobs);data=bytearray();expected=bytearray();starts=[]
 for job in jobs:
  pixels=pattern_tiles(job['tile_count'])&((1<<job['bpp'])-1);starts.append(len(data));data.extend(bitmap_bytes(pixels,job['bpp'],16));expected.extend(b''.join(encode(t,job['bpp'])for t in pixels))
 begin=asm.index('    ldx #0\nCopyInput:');end=asm.index('    ldx #0\nCopyWorker:',begin)
 asm=asm[:begin]+'''    ldx #0
    lda #$4086
PhysicsSentinelInit:
.a16
.i16
    sta.l $42D800,x
    inx
    inx
    cpx #2048
    bne PhysicsSentinelInit
'''+asm[end:]
 begin=asm.index('    lda #$80\n    sta.w $2115\n')+len('    lda #$80\n    sta.w $2115\n');end=asm.index('    rep #$20\n.a16\n    lda #$B4AD',begin);body=''
 for i,d in enumerate(ds):
  source=0xc20000+starts[d['job']]+d['job_byte_offset']
  body+=f'''    rep #$20
.a16
WorkspaceChunk{i}BeforeCopy:
.i16
    nop
    ldx #0
WorkspaceChunk{i}Copy:
    lda.l ${source:06X},x
    sta.l $420000,x
    inx
    inx
    cpx #{d['bytes']}
    bne WorkspaceChunk{i}Copy
WorkspaceChunk{i}AfterCopy:
    nop
    sep #$20
.a8
'''
  for address,value in [(0x2231,d['cdma']),(0x2232,d['source']&255),(0x2233,(d['source']>>8)&255),(0x2234,d['source']>>16),(0x2235,d['iram']&255),(0x2236,d['iram']>>8)]:body+=f'    lda #${value:02X}\n    sta.w ${address:04X}\n'
  body+=f'''WorkspaceChunk{i}Ready:
    lda.w $2300
    and #$20
    beq WorkspaceChunk{i}Ready
    lda #$20
    sta.w $2202
    rep #$20
.a16
    lda #{d['vram_word_address']}
    sta.w $2116
    lda #$1801
    sta.w $4370
    lda #$0042
    sta.w $4374
    lda #0
    sta.w $4372
    lda #{d['bytes']}
    sta.w $4375
WorkspaceChunk{i}Start:
    sep #$20
.a8
    lda #$80
    sta.w $420B
    nop
WorkspaceChunk{i}Done:
    lda #$80
    sta.w $2231
'''
 asm=asm[:begin]+body+asm[end:];(folder/'reuse.pasm').write_text(asm)
 proc=subprocess.run(['C:/Users/chad/.dotnet/dotnet.exe','E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll',str(folder/'reuse.pasm'),'--output',str(folder/'reuse.bin'),'--symbols',str(folder/'reuse.sym'),'--no-pansy'],capture_output=True,text=True);(folder/'build.log').write_text(proc.stdout+proc.stderr)
 if proc.returncode:raise ValueError('CHARCONV_REUSE_BUILD:'+proc.stdout+proc.stderr)
 raw=(folder/'reuse.bin').read_bytes();rom=bytearray([255])*262144;rom[:len(raw)]=raw;rom[:4]=bytes.fromhex('5c 00 80 01');rom[0x20000:0x20000+len(data)]=data;rom[0x7fc0:0x7fd5]=b'M4 SA1 REUSE'.ljust(21);rom[0x7fd5:0x7fdc]=bytes([0x23,0x35,8,8,1,0x33,0]);rom[0x7ffc:0x7ffe]=struct.pack('<H',0x8000)
 return bytes(rom),bytes(expected),symbols(folder/'reuse.sym'),ds


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();folder=a.output.resolve();folder.mkdir(parents=True,exist_ok=True)
 rom,expected,sy,ds=build(folder);path=folder/'proof.sfc';path.write_bytes(rom)
 script='''local mt=emu.memType.snesMemory
local function heap_hash()local h=2166136261;for _,r in ipairs({{0x40b000,0x410000},{0x414000,0x420000},{0x430000,0x440000}})do for a=r[1],r[2]-1 do h=((h~emu.read(a,mt))*16777619)&0xffffffff end end;return h end
local baseline=0
'''
 script+=f"emu.addMemoryCallback(function()baseline=heap_hash()end,emu.callbackType.exec,{sy['WorkspaceChunk0BeforeCopy']},{sy['WorkspaceChunk0BeforeCopy']},emu.cpuType.snes,mt)\n"
 end=sy['WorkspaceChunk2Done']+5
 # The completion marker is written only after conversion disable.
 script+=f"emu.addMemoryCallback(function()emu.log('WORKSPACEHEAP|'..baseline..'|'..heap_hash())end,emu.callbackType.exec,{end},{end},emu.cpuType.snes,mt)\n"
 for i in range(len(ds)):
  for phase in ('BeforeCopy','AfterCopy','Start','Done'):
   address=sy[f'WorkspaceChunk{i}{phase}'];script+=f"emu.addMemoryCallback(function()emu.log('WORKSPACECHUNK|{i}|{phase}|'..emu.getState().masterClock)end,emu.callbackType.exec,{address},{address},emu.cpuType.snes,mt)\n"
 lua=folder/'observer.lua';lua.write_text(script)
 class Observed(McpSession):
  def __enter__(self):
   import mesen_mcp.session as module
   def launch(argv,**kwargs):return subprocess.Popen([*argv,'--donotsavesettings',str(lua)],**kwargs)
   with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
 with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=folder/'mesen.log')as m:
  for _ in range(60):
   m.tool('run_frames',{'count':1});marker=m.read_memory('SnesMemory',0x413ff0,4)
   if marker==bytes.fromhex('ac b4 ad b4'):break
  actual=m.read_memory('SnesVideoRam',0,len(expected));sentinel=m.read_memory('SnesMemory',0x42d800,2048)
 logs=(folder/'mesen.log').read_text();events=[];heaps=[]
 for line in logs.splitlines():
  if 'WORKSPACECHUNK|'in line:
   n,phase,time=line.split('WORKSPACECHUNK|',1)[1].split('|');events.append(dict(chunk=int(n),phase=phase,master_clock=int(time)))
  if 'WORKSPACEHEAP|'in line:heaps.append(list(map(int,line.split('WORKSPACEHEAP|',1)[1].split('|'))))
 timing=[]
 for i,d in enumerate(ds):
  row={e['phase']:e['master_clock']for e in events if e['chunk']==i}
  if len(row)==4:timing.append(dict(chunk=i,copy_master_clocks=row['AfterCopy']-row['BeforeCopy'],dma_master_clocks=row['Done']-row['Start'],bytes=d['bytes']))
 good=actual==expected and sentinel==bytes.fromhex('8640')*1024 and len(heaps)==1 and heaps[0][0]==heaps[0][1]and len(timing)==len(ds)and all(t['dma_master_clocks']>=t['bytes']*8 for t in timing)and marker==bytes.fromhex('ac b4 ad b4')
 r=dict(schema='BYOR_SA1_REUSED_WORKSPACE_NATIVE_V1',status='PASS'if good else'FAIL',rom_sha256=hashlib.sha256(rom).hexdigest(),expected_chr_sha256=hashlib.sha256(expected).hexdigest(),actual_chr_sha256=hashlib.sha256(actual).hexdigest(),vram_exact=actual==expected,descriptors=ds,workspace=['420000','42D800'],physics_sentinel=['42D800','42E000'],physics_sentinel_preserved=sentinel==bytes.fromhex('8640')*1024,source_heap_hashes=heaps,source_heap_preserved=len(heaps)==1 and heaps[0][0]==heaps[0][1],packed_bytes=len(expected),timings=timing,events=events,marker_hex=marker.hex(),source_or_native_physics_state_installed=False,live_rgb8_compositor_bound=False,production_irq_nmi_audio_budget_admitted=False,no_color_reduction=True)
 (folder/'packed.chr').write_bytes(actual);(folder/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],r['packed_bytes'],'lossless CHR bytes',timing,heaps)
 if not good:raise SystemExit(1)


if __name__=='__main__':main()
