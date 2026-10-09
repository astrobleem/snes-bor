"""Measure native Q12 position advancement plus twelve-channel PCM8 mixing.

The isolated case stays inside each 257-byte source allocation. Completion,
looping, arbitrary ROM-bank crossing, PCM16, BRR and playback remain unbound.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from types import SimpleNamespace
from unittest.mock import patch
from _harness import McpSession,MESEN_EXE,_free_tcp_port,run_frames_exact
from m4_sound_mix_sa1_native import Code,build as kernel_build


def build(frames,period,volume,busy,pcm_dma=False,expanded_byte_sum=False,warmup=0,unroll=1,input_channels=None,packed_mono=False,phase_address=0x435000,output_address=0x420000,*,completion=False,sample_length=257,active_mode=1,batches=1,channel_count=12,fixed_loop_bias=False):
 if fixed_loop_bias and(not completion or active_mode!=2):raise ValueError('FIXED_BIAS_REQUIRES_IMMUTABLE_LOOPING_CHANNELS')
 if batches not in (1,2)or batches>1 and not completion:raise ValueError('GATHER_BATCH_DOMAIN')
 if completion and(not expanded_byte_sum or pcm_dma or input_channels is not None or not 0<frames<=184 or warmup!=0 or not 1<=sample_length<=257 or active_mode not in(1,2) or not 0<period<=4096):raise ValueError('COMPLETING_GATHER_DOMAIN')
 if unroll not in(1,4,8)or frames%unroll:raise ValueError('GATHER_UNROLL_DOMAIN')
 if unroll!=1 and not expanded_byte_sum:raise ValueError('GATHER_UNROLL_REQUIRES_FACTORED_BYTES')
 if pcm_dma and expanded_byte_sum:raise ValueError('EXPANDED_BYTE_SUM_DMA_UNBOUND')
 count=len(input_channels)if input_channels is not None else channel_count
 if not 1<=count<=12:raise ValueError('ACTIVE_CHANNEL_COUNT_DOMAIN')
 if not 0x400000<=phase_address<=0x440000-count*4 or not 0x400000<=output_address<=0x440000-frames*(2 if packed_mono else 4):raise ValueError('AUDIO_WORKSPACE_RANGE')
 if input_channels is not None and(not expanded_byte_sum or period!=4096):raise ValueError('SOURCE_INPUT_REQUIRES_INTEGER_STRIDE_PROJECTION')
 if packed_mono and not expanded_byte_sum:raise ValueError('PACKED_MONO_REQUIRES_FACTORED_BYTES')
 if not completion and input_channels is None and 44*4096+(frames+warmup)*period>=257*4096:raise ValueError('GATHER_MIX_SOURCE_COMPLETION_UNBOUND')
 source_stride=1024 if expanded_byte_sum else 512
 if input_channels is not None:
  size=max(len(row['values'])*2 for row in input_channels)
  source_stride=max(1024,1<<(size-1).bit_length())
  if source_stride*count>65536:raise ValueError('BOUNDED_SOURCE_ROM_BANK_CAPACITY')
  if any((row['initial_Q12']>>12)+frames>=len(row['values'])for row in input_channels):raise ValueError('BOUNDED_SOURCE_STRIDE_CACHE_END')
 raw,_,_=kernel_build(frames,busy,12,volume,True,True);rom=bytearray(raw)
 for channel in range(count):
  values=input_channels[channel]['values']if input_channels is not None else[(i*37+channel*13)&255 for i in range(257)]
  data=struct.pack('<'+'H'*len(values),*values)if expanded_byte_sum else bytes(values)
  rom[0x20000+channel*source_stride:0x20000+channel*source_stride+len(data)]=data
 phase=b''.join(struct.pack('<I',input_channels[channel]['initial_Q12']if input_channels is not None else ((channel*4)%sample_length)*4096+warmup*period)for channel in range(count));rom[0x1a400:0x1a430]=phase+bytes(48-len(phase))
 c=Code(0x3500);c.emit('78 18 fb c2 30 a2 ff 37 9a a9 e0 34 5b e2 20 a9 ff 8d 2a 22 a9 80 8d 27 22 a9 00 48 ab c2 20')
 acc_stride=2 if expanded_byte_sum else 4
 count_base=0x3200+frames*2
 if batches>1:c.word(0xa9,batches);c.emit('85 14')
 c.label('entry');c.emit('a9 00 00 a2 00 00');c.label('clear');c.emit('9d 00 32 e8 e8');c.word(0xe0,frames*(4 if completion and not fixed_loop_bias else acc_stride));c.branch(0xd0,'clear');c.emit('85 06')
 if expanded_byte_sum:c.emit('e2 20 8d 50 22 c2 20')
 q16_fraction=expanded_byte_sum and bool(period&4095)
 c.label('channel')
 if completion:
  c.emit('a6 06 bf 00 51 43 85 12');c.branch(0xd0,'channel_live');c.jump('next_channel');c.label('channel_live')
 c.emit('a6 06 bf '+phase_address.to_bytes(3,'little').hex(' ')+' 29 ff 0f'+(' 0a 0a 0a 0a'if q16_fraction else'')+' 85 00 bf '+phase_address.to_bytes(3,'little').hex(' ')+' eb 29 ff 00 4a 4a 4a 4a 85 02 bf '+(phase_address+2).to_bytes(3,'little').hex(' ')+' 0a 0a 0a 0a 05 02 85 02 8a')
 if expanded_byte_sum:c.emit('a5 02 0a 85 02 a6 06 8a')
 c.emit('0a '*(source_stride.bit_length()-3));c.emit('85 04')
 if pcm_dma:
  # SA-1 normal DMA: source ROM, destination internal RAM. Writing the
  # destination middle byte starts it; the SA-1 CPU stalls until completion.
  c.emit('8d 32 22 e2 20 a9 c2 8d 34 22 a9 80 8d 30 22 a9 20 8d 0b 22 c2 20 a9 01 01 8d 38 22 a9 c0 36 8d 35 22')
 else:c.emit('18 65 02 85 02')
 if completion:
  c.emit('a5 04 18');c.word(0x69,sample_length*2);c.emit('85 10')
 c.emit('a0 00 00');c.word(0xa9,frames//unroll);c.emit('85 08')
 if expanded_byte_sum:c.emit('a6 02')
 c.label('sample')
 for item in range(unroll):
  if expanded_byte_sum:
   c.emit('bf 00 00 c2 18 79 00 32 99 00 32')
   if completion and not fixed_loop_bias:c.emit('b9 '+count_base.to_bytes(2,'little').hex(' ')+' 1a 99 '+count_base.to_bytes(2,'little').hex(' '))
   c.emit('c8 c8')
  else:
   c.emit('a6 02 e2 20 bf '+('c0 36 00'if pcm_dma else'00 00 c2')+' c2 20 29 ff 00 0a aa bf 00 30 00 18 79 00 32 99 00 32')
   c.branch(0x90,'no_sum_carry');c.emit('98 aa fe 02 32');c.label('no_sum_carry');c.emit('c8 c8 c8 c8')
  if period&4095:
   carry='no_phase_carry_'+str(item)
   c.emit('a5 00 18');c.word(0x69,(period&4095)<<(4 if q16_fraction else 0));c.emit('85 00'+(''if q16_fraction else' c9 00 10'));c.branch(0x90,carry);c.emit((''if q16_fraction else'29 ff 0f 85 00')+(' e8 e8'if expanded_byte_sum else' e6 02'));c.label(carry)
  if period>>12==1:c.emit('e8 e8'if expanded_byte_sum else'e6 02')
  elif period>>12:
   c.emit('8a 18'if expanded_byte_sum else'a5 02 18');c.word(0x69,(period>>12)*(2 if expanded_byte_sum else 1));c.emit('aa'if expanded_byte_sum else'85 02')
  if completion:
   inside='inside_sample_'+str(item)
   c.emit('e4 10');c.branch(0x90,inside);c.emit('8a 38');c.word(0xe9,sample_length*2);c.emit('aa')
   c.emit('a5 12 c9 02 00');c.branch(0xf0,inside);c.emit('a9 00 00 85 12');c.jump('samples_done')
   c.label(inside)
 c.emit('c6 08')
 if unroll==1:
  if completion:c.branch(0xf0,'samples_done');c.jump('sample');c.label('samples_done')
  else:c.branch(0xd0,'sample')
 else:c.branch(0xf0,'samples_done');c.jump('sample');c.label('samples_done')
 c.emit(('8a'if expanded_byte_sum else'a5 02')+(''if pcm_dma else' 38 e5 04')+(' 4a'if expanded_byte_sum else'')+' 85 0a')
 if q16_fraction:c.emit('a5 00 4a 4a 4a 4a 85 0c a5 0a')
 c.emit('29 0f 00 eb 0a 0a 0a 0a 05 '+('0c'if q16_fraction else'00')+' a6 06 9f '+phase_address.to_bytes(3,'little').hex(' ')+' a5 0a 4a 4a 4a 4a 9f '+(phase_address+2).to_bytes(3,'little').hex(' ')+(' a5 12 9f 00 51 43 a9 00 00 9f 02 51 43'if completion else''))
 if completion:c.label('next_channel')
 c.emit('a5 06 18 69 04 00 85 06');c.word(0xc9,count*4)
 c.branch(0xf0,'gather_mix_done');c.jump('channel')
 c.label('gather_mix_done');c.emit('a0 00 00')
 c.label('clip')
 if expanded_byte_sum:
  c.emit('b9 00 32 8d 51 22');c.word(0xa9,volume);c.emit('8d 53 22 ea ea ea')
  if completion and not fixed_loop_bias:
   c.emit('b9 '+count_base.to_bytes(2,'little').hex(' ')+' 85 0c 29 07 00 eb 0a 0a 0a 0a 0a 85 0e a5 0c 4a 4a 4a 85 10 ad 06 23 38 e5 0e 85 0a ad 08 23 e5 10')
  else:
   c.emit('ad 06 23 38');c.word(0xe9,(count*8192)&65535);c.emit('85 0a ad 08 23');c.word(0xe9,(count*8192)>>16)
 else:c.emit('b9 00 32 38 e9 00 80 85 0a b9 02 32 e9 01 00')
 c.branch(0xf0,'positive');c.emit('c9 ff ff');c.branch(0xf0,'negative');c.branch(0x30,'low');c.emit('a9 ff 7f');c.branch(0x80,'store')
 c.label('low');c.emit('a9 00 80');c.branch(0x80,'store');c.label('positive');c.emit('a5 0a 18 6a');c.branch(0x80,'store');c.label('negative');c.emit('a5 0a 38 6a')
 c.label('store');c.emit('48 98'+(' 0a'if expanded_byte_sum and not packed_mono else'')+' aa 68')
 c.emit('9f '+output_address.to_bytes(3,'little').hex(' ')+(''if packed_mono else' 9f '+(output_address+2).to_bytes(3,'little').hex(' '))+(' c8 c8'if expanded_byte_sum else' c8 c8 c8 c8'));c.word(0xc0,frames*acc_stride);c.branch(0xd0,'clip')
 c.label('done')
 if batches>1:c.emit('c6 14');c.branch(0xf0,'final_done');c.jump('entry');c.label('final_done')
 c.emit('a9 ab b4 8f f0 3f 41');c.label('stop');c.jump('stop');worker=c.finish()
 if 0x3500+len(worker)>(0x36c0 if pcm_dma else 0x37c0):raise ValueError('GATHER_MIX_IRAM_STACK_GAP')
 rom[0x9000:0x9000+len(worker)]=worker
 main=bytearray(rom[0x8000:0x8400]);main=main[:main.index(bytes([255])*32)]
 needle=bytes.fromhex('bf 00 90 01 9f 20 34 00 e8 e0');at=main.index(needle);main[at+5:at+7]=struct.pack('<H',0x3500);main[at+len(needle):at+len(needle)+2]=struct.pack('<H',len(worker))
 at=main.index(bytes.fromhex('a9 20 8d 03 22'));main[at+1]=0
 at=main.index(bytes.fromhex('a9 34 8d 04 22'));main[at+1]=0x35
 # Additional immutable descriptor copy; all initial source phase values
 # come from the same actual channel policy as the pinned C authority.
 extra=bytearray.fromhex('c2 20 a2 00 00 bf 00 a4 03 9f '+phase_address.to_bytes(3,'little').hex(' ')+' e8 e8 e0 30 00 d0 f1 e2 20')
 if completion:
  rom[0x1a430:0x1a460]=b''.join(struct.pack('<I',active_mode)for _ in range(count))+bytes(48-count*4)
  extra+=bytearray.fromhex('a2 00 00 bf 30 a4 03 9f 00 51 43 e8 e8 e0 30 00 d0 f1')
 if main[-3]!=0x4c:raise ValueError('GATHER_MIX_HOST_WAIT_LAYOUT')
 main[-2:]=struct.pack('<H',struct.unpack('<H',main[-2:])[0]+len(extra))
 insert=main.index(bytes.fromhex('bf 00 90 01'))-3;main[insert:insert]=extra;rom[0x8000:0x8400]=main+bytes([255])*(1024-len(main))
 entries={name:0x3500+c.labels[name]for name in('entry','gather_mix_done','done')}
 return bytes(rom),entries,worker


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--authority',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--period',type=int,choices=(1024,2457,4055,4096),default=4096);p.add_argument('--volume',type=int,choices=(0,1,32,37,64),default=37);p.add_argument('--busy-host',action='store_true');p.add_argument('--pcm-dma',action='store_true');p.add_argument('--expanded-byte-sum',action='store_true');p.add_argument('--unroll',type=int,choices=(1,4,8),default=1);p.add_argument('--completion',action='store_true');p.add_argument('--sample-length',type=int,choices=(17,257),default=257);p.add_argument('--active-mode',type=int,choices=(1,2),default=1);p.add_argument('--batches',type=int,choices=(1,2),default=1);p.add_argument('--channels',type=int,choices=(1,2,4,6,8,12),default=12);p.add_argument('--fixed-loop-bias',action='store_true');a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 authority=json.loads(a.authority.read_text());assert authority['status']=='PASS'and authority['right_volume_policy']=='equal to left';frames=authority['output_frames'];
 if a.completion and authority.get('warmup_frames',0)!=(a.batches-1)*frames:raise ValueError('COMPLETING_AUTHORITY_BLOCK_COUNT')
 case=authority['inputs'].index([a.channels,8,a.volume,a.period,a.sample_length,a.active_mode]);expected=authority['actual'][case];rom,entries,worker=build(frames,a.period,a.volume,a.busy_host,a.pcm_dma,a.expanded_byte_sum,0 if a.batches>1 else authority.get('warmup_frames',0),a.unroll,completion=a.completion,sample_length=a.sample_length,active_mode=a.active_mode,batches=a.batches,channel_count=a.channels,fixed_loop_bias=a.fixed_loop_bias)
 path=a.output/'proof.sfc';path.write_bytes(rom);lua=a.output/'observer.lua';lua.write_text('\n'.join(f"emu.addMemoryCallback(function()local s=emu.getState();emu.log('GATHERMIX|{n}|'..s.masterClock)end,emu.callbackType.exec,{v},{v},emu.cpuType.sa1,emu.memType.sa1Memory)"for n,v in entries.items()))
 class Observed(McpSession):
  def __enter__(self):
   import mesen_mcp.session as module
   def launch(argv,**kwargs):return subprocess.Popen([*argv,str(lua)],**kwargs)
   with patch.object(module,'subprocess',SimpleNamespace(Popen=launch,DEVNULL=subprocess.DEVNULL,PIPE=subprocess.PIPE)):return super().__enter__()
 with Observed(rom=path,mesen=MESEN_EXE,port=_free_tcp_port(),stderr_log=a.output/'mesen.log')as m:
  for _ in range(60):
   run_frames_exact(m,1)
   if m.read_memory('SnesMemory',0x413ff0,32)[:2]==b'\xab\xb4':break
  data=m.read_memory('SnesMemory',0x420000,frames*4);actual=list(struct.unpack('<'+'H'*(frames*2),data));phase=list(struct.unpack('<'+'I'*a.channels,m.read_memory('SnesMemory',0x435000,a.channels*4)));states=list(struct.unpack('<'+'I'*a.channels,m.read_memory('SnesMemory',0x435100,a.channels*4)))if a.completion else None;(a.output/'mixed-s16.bin').write_bytes(data)
 events=[l.split('GATHERMIX|',1)[1].split('|')for l in(a.output/'mesen.log').read_text().splitlines()if'GATHERMIX|'in l]
 costs={n:int(v)for n,v in events};elapsed=int(events[-1][1])-int(events[0][1])if len(events)==3*a.batches else None;expected_phase=expected[frames*2+1::2];ok=actual==expected[:frames*2]and phase==expected_phase and elapsed is not None
 report=dict(schema='BYOR_SOURCE_PCM8_GATHER_MIX_NATIVE_V1',status='PASS'if ok else'FAIL',source_case=authority['inputs'][case],output_frames=frames,stereo_output_samples=frames*2,PCM_mismatches=sum(x!=y for x,y in zip(actual,expected)),actual_phases=phase,expected_phases=expected_phase,master_clocks=elapsed,milliseconds=elapsed/21477.27 if elapsed else None,worker_bytes=len(worker),gain_lookup_IRAM_bytes=0 if a.expanded_byte_sum else 512,accumulator_IRAM_bytes=frames*(2 if a.expanded_byte_sum else 4),zero_extended_PCM8_ROM_words=a.expanded_byte_sum,uniform_gain_factored_after_byte_sum=a.expanded_byte_sum,source_position_advance_native=True,inputs_gathered_native=True,busy_host_BWRAM_reads=a.busy_host,PCM_DMA_prefetch=a.pcm_dma,PCM_cache_IRAM_bytes=257 if a.pcm_dma else 0,PCM_DMA_setup_and_transfer_in_timing=a.pcm_dma,all_channels_stay_inside_source_sample=True,sample_completion_proven=False,looping_proven=False,source_PCM16_proven=False,source_ROM_bank_crossing_proven=False,BRR_encoding_proven=False,mixed_stream_transport_proven=False,production_memory_lease=False,joint_graphics_contention_proven=False,complete_backend_admitted=False,rom_sha256=hashlib.sha256(rom).hexdigest(),authority_sha256=hashlib.sha256(a.authority.read_bytes()).hexdigest(),motu_gameplay_proven=False,no_color_reduction=True)
 if a.completion:
  expected_states=expected[frames*2::2];ok=ok and states==expected_states;report.update(status='PASS'if ok else'FAIL',all_channels_stay_inside_source_sample=False,sample_completion_proven=ok and a.active_mode==1,looping_proven=ok and a.active_mode==2,actual_active_states=states,expected_active_states=expected_states,per_frame_active_bias_count_native=not a.fixed_loop_bias,accumulator_IRAM_bytes=frames*(2 if a.fixed_loop_bias else 4))
 report.update(immutable_loop_count_bias=a.fixed_loop_bias,active_input_channels=a.channels,native_batches=a.batches,persistent_phase_and_active_resume_proven=ok and a.batches>1,batch_master_clocks=[int(events[i+2][1])-int(events[i][1])for i in range(0,len(events),3)]if len(events)==3*a.batches else [])
 report['unroll']=a.unroll
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
 if not ok:raise SystemExit(1)


if __name__=='__main__':main()
