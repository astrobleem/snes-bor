"""Native real-source PCM gathering, exact C mixing and predictive BRR chain.

Integer-rate stride partitioning preserves pinned C samples at 11025 Hz and
normal source pitch. Completion, looping and arbitrary pitch remain unbound.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
from types import SimpleNamespace
from unittest.mock import patch
import wave
from compiler import Source
from source_mixed_brr_quality import compact_encode
from m4_sound_gather_mix_sa1_native import build as gather_build
from m4_brr_filter1_sa1_native import build as encode_build
from _harness import McpSession,MESEN_EXE,_free_tcp_port,run_frames_exact


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--assets',type=Path,required=True);p.add_argument('--authority',type=Path,required=True);p.add_argument('--case',choices=('six-voice-stress','twelve-voice-stress'),required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--code-dma',action='store_true');a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
 authority=json.loads(a.authority.read_text());frames=authority['frames'];case=next(r for r in authority['results']if r['name']==a.case)
 if not case['actual_C_final_channels']or frames%16 or frames>208:raise ValueError('BOUNDED_C_CHANNEL_AUTHORITY_REQUIRED')
 data=(a.authority.parent/(a.case+'.mixed')).read_bytes();expected_pcm=struct.unpack('<'+'h'*frames,data)
 if hashlib.sha256(data).hexdigest()!=case['mixed_pcm_sha256']:raise ValueError('C_MIXTURE_HASH')
 manifest=json.loads((a.assets/'report.json').read_text());source=Source(a.source);inputs=[];ratios=[];channels=[]
 for state in case['actual_C_final_channels']:
  if not state['active']:continue
  index=case['sound_indices'][state['fixture_sample_index']];row=next(r for r in manifest['compiled']if r['sound_index']==index);wav=source.read(row['source_path'])
  if hashlib.sha256(wav).hexdigest()!=row['source_sha256']:raise ValueError('SOURCE_PCM_HASH')
  with wave.open(io.BytesIO(wav),'rb')as w:
   if w.getnchannels()!=1 or w.getsampwidth()!=1:raise ValueError('PCM8_MONO_DOMAIN')
   frequency=w.getframerate();pcm=w.readframes(w.getnframes())
  ratio=frequency//11025
  if ratio not in(1,2,4)or frequency!=ratio*11025 or state['Q12_period']!=ratio*4096:raise ValueError('NORMAL_PITCH_INTEGER_STRIDE_DOMAIN')
  initial=state['slot']*4
  if initial%ratio or state['Q12_position']!=(initial+frames*ratio)*4096:raise ValueError('SOURCE_COMPLETION_UNBOUND')
  values=list(pcm[::ratio][:257])
  if len(values)!=257 or initial//ratio+frames>=257:raise ValueError('SOURCE_STRIDE_CACHE_BOUND')
  inputs.append(dict(values=values,initial_Q12=(initial//ratio)*4096));ratios.append(ratio);channels.append(dict(slot=state['slot'],sound_index=index,source_sha256=row['source_sha256'],source_frequency=frequency,stride=ratio,actual_C_final_Q12=state['Q12_position']))
 gather_rom,gather_entries,gather_worker=gather_build(frames,4096,64,True,expanded_byte_sum=True,unroll=8,input_channels=inputs,packed_mono=True)
 encode_rom,encode_entries,encode_worker=encode_build(expected_pcm,True,True,True,worker_base=0x3500,input_bank=0x42)
 rom=bytearray(encode_rom);rom[:0x10000]=gather_rom[:0x10000];rom[0x20000:0x23000]=gather_rom[0x20000:0x23000]
 # The source descriptor was in C1's future predictor table. Relocate it to
 # unused C2 ROM tail before joining the jobs, preserving both authorities.
 rom[0x2f000:0x2f030]=gather_rom[0x1a400:0x1a430]
 main=bytearray(rom[0x8000:0x8400]);at=main.index(bytes.fromhex('bf 00 a4 03'));main[at:at+4]=bytes.fromhex('bf 00 f0 05');rom[0x8000:0x8400]=main
 done=gather_entries['done']-0x3500;gather_worker=gather_worker[:done]+bytes.fromhex('5c 00 a0 01');rom[0x9000:0x9000+len(gather_worker)]=gather_worker
 # The boot copy length may include the old stop bytes; they are unreachable.
 rom[0x9800:0x9800+len(encode_worker)]=encode_worker
 glue=bytes.fromhex('c2 30 a2 00 00 bf 00 98 01 9f 00 35 00 e8 e8 e0')+struct.pack('<H',len(encode_worker)+(len(encode_worker)&1))+bytes.fromhex('d0 f1 5c 00 35 00')
 if a.code_dma:
  glue=bytes.fromhex('e2 20 a9 00 48 ab a9 80 8d 30 22 a9 20 8d 0b 22 c2 20 a9 00 98 8d 32 22 e2 20 a9 c0 8d 34 22 c2 20 a9')+struct.pack('<H',len(encode_worker))+bytes.fromhex('8d 38 22 a9 00 35 8d 35 22 5c 00 35 00')
 rom[0xa000:0xa000+len(glue)]=glue;rom[0x7fd7]=11;path=out/'proof.sfc';path.write_bytes(rom);lua=out/'observer.lua'
 points=[('gather_entry',gather_entries['entry']),('gather_done',gather_entries['done']),('encode_entry',encode_entries['entry']),('encode_done',encode_entries['done'])]
 lua.write_text('local stage=0\n'+'\n'.join(f"emu.addMemoryCallback(function()if stage=={i} then stage=stage+1;local s=emu.getState();emu.log('JOINTBRR|{name}|'..s.masterClock)end end,emu.callbackType.exec,{address},{address},emu.cpuType.sa1,emu.memType.sa1Memory)"for i,(name,address)in enumerate(points)))
 class Observed(McpSession):
  def __enter__(self):
   import mesen_mcp.session as module
   def launch(argv,**kwargs):return subprocess.Popen([*argv,str(lua)],**kwargs)
   with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
 expected_brr=compact_encode(expected_pcm,True)
 with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=out/'mesen.log')as m:
  for _ in range(60):
   run_frames_exact(m,1)
   if m.read_memory('SnesMemory',0x413ff0,32)[:2]==b'\xab\xb4':break
  actual_pcm=m.read_memory('SnesMemory',0x420000,len(data));actual_brr=m.read_memory('SnesMemory',0x430000,len(expected_brr));phases=struct.unpack('<'+'I'*len(inputs),m.read_memory('SnesMemory',0x435000,len(inputs)*4));guard=m.read_memory('SnesMemory',0x413ff2,2)==b'\xad\xde';repairs=struct.unpack('<H',m.read_memory('SnesMemory',0x003028,2))[0]
 events=[l.split('JOINTBRR|',1)[1].split('|')for l in(out/'mesen.log').read_text().splitlines()if'JOINTBRR|'in l];clocks={n:int(c)for n,c in events};trace_ok=[e[0]for e in events]==[p[0]for p in points]
 reconstructed=[phase*ratio for phase,ratio in zip(phases,ratios)];expected_phases=[c['actual_C_final_Q12']for c in channels]
 ok=actual_pcm==data and actual_brr==expected_brr and reconstructed==expected_phases and not guard and trace_ok
 costs=dict(gather_mix=clocks['gather_done']-clocks['gather_entry'],code_exchange=clocks['encode_entry']-clocks['gather_done'],encode=clocks['encode_done']-clocks['encode_entry'],total=clocks['encode_done']-clocks['gather_entry'])if trace_ok else None
 report=dict(schema='BYOR_REAL_SOURCE_MIX_BRR_JOINT_NATIVE_V1',status='PASS'if ok else'FAIL',case=a.case,frames=frames,active_channels=len(inputs),channels=channels,PCM_byte_mismatches=sum(x!=y for x,y in zip(actual_pcm,data)),BRR_byte_mismatches=sum(x!=y for x,y in zip(actual_brr,expected_brr)),actual_reconstructed_source_Q12=reconstructed,expected_source_Q12=expected_phases,clipping_guard=guard,clip_repairs=repairs,master_clocks=costs,milliseconds={k:v/21477.27 for k,v in costs.items()}if costs else None,gather_worker_bytes=len(gather_worker),encoder_worker_bytes=len(encode_worker),rom_sha256=hashlib.sha256(rom).hexdigest(),mixed_sha256=hashlib.sha256(actual_pcm).hexdigest(),brr_sha256=hashlib.sha256(actual_brr).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),stride_projection='lossless selected original PCM8 samples at source-derived integer rate; source Q12 reconstructed exactly',output_rate_policy='ACCEPTED_COMPAT 11025',normal_pitch_only=True,sample_completion_bound=False,looping_bound=False,SPC_transport_bound=False,joint_graphics_bound=False,production_memory_lease=False,motu_gameplay_proven=False,no_color_reduction=True)
 report['code_exchange_normal_SA1_DMA']=a.code_dma
 (out/'mixed.bin').write_bytes(actual_pcm);(out/'native.brr').write_bytes(actual_brr);(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
 if not ok:raise SystemExit(1)


if __name__=='__main__':main()
