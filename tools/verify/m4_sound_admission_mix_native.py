"""Source admission feeding native PCM; private paused ownership, no SPC."""
import argparse,hashlib,io,json,os,re,struct,subprocess,wave
from pathlib import Path
from compiler import Source
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_frame_audio import stream_wav
from source_pcm8_packed_native import build
from source_sound_admission_native import emit
from source_sound_pcm8_descriptors_native import emit as descriptors
from actor_s5_entity_fixture import symbols
from _source_leaf_fixture import run_fixture
from _harness import Reporter
from m4_animation_init_native import luav
from m4_sound_admission_native import LUA,W,BASE
PHASE=0x43f800;ACTIVE=0x43f840;LENGTHS=0x43f880;BASES=0x43f8b0;METADATA=0x3a8000

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('rom','source','assets','authority-scaffold','output'):p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--indices',nargs=2,type=int,default=(3,15));p.add_argument('--jobs',type=int,default=2);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 if len(set(a.indices))!=2:raise ValueError('ADMISSION_DISTINCT_SOURCE_FIXTURE')
 if not 1<=a.jobs<=1024:raise ValueError('ADMISSION_MIX_JOBS')
 frames=176;source=Source(a.source);manifest=json.loads((a.assets/'report.json').read_text());inputs=[];identities=[]
 for index in a.indices:
  row=next(r for r in manifest['compiled']if r['sound_index']==index);raw=source.read(row['source_path']);assert hashlib.sha256(raw).hexdigest()==row['source_sha256'];wav,meaningful,policy=stream_wav(raw,11025);assert hashlib.sha256(wav).hexdigest()==row['canonical_wav_sha256']
  with wave.open(io.BytesIO(wav),'rb')as f:pcm=f.readframes(f.getnframes())
  inputs.append(pcm);identities.append(dict(sound_index=index,path=row['source_path'],source_sha256=row['source_sha256'],normalized_pcm_sha256=hashlib.sha256(pcm).hexdigest(),normalized_frames=len(pcm),policy=policy))
 authority=a.authority_scaffold.read_text();engine=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/source/gamelib/soundmix.c']).decode('latin1')
 bodies={n:extract(engine,n)for n in ('clearmixbuffer','mixaudio','update_sample','sound_play_sample')}
 for body in bodies.values():assert body in authority
 assert '#define JOB_FRAMES 176' in authority and authority.count('vchannel[channel].fp_samplepos=pos;')==1
 authority=authority.replace('vchannel[channel].fp_samplepos=pos;','')
 (a.output/'source.c').write_text(authority);env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
 r=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-bt=nt','source.c','-fe=source.exe'],cwd=a.output,env=env,capture_output=True,text=True);(a.output/'authority-build.log').write_text(r.stdout+r.stderr)
 if r.returncode:raise ValueError('ADMISSION_MIX_AUTHORITY_BUILD')
 payload=struct.pack('<I',a.jobs)+b''.join(struct.pack('<II',len(pcm),0)+pcm for pcm in inputs)
 expected=subprocess.check_output([str(a.output/'source.exe')],input=payload,cwd=a.output);assert len(expected)==frames*4*a.jobs+24;states=struct.unpack('<6I',expected[-24:]);assert states[0::3]==(11,10)
 channels=[dict(values=[128],initial_Q12=0)for _ in range(12)]
 for i,pcm in enumerate(inputs):channels[11-i]=dict(values=list(pcm),initial_Q12=((11-i)*4%len(pcm))*4096)
 packed,entries,worker=build(frames,64,channels,batches=a.jobs,source_bank=0xe1)
 for old,new in ((0x435000,PHASE),(0x435002,PHASE+2),(0x435100,ACTIVE),(0x435102,ACTIVE+2),(0x03a460,LENGTHS),(0x03a462,LENGTHS+2),(0x03a490,BASES),(0x03a492,BASES+2)):
  assert old.to_bytes(3,'little')in worker;worker=worker.replace(old.to_bytes(3,'little'),new.to_bytes(3,'little'))
 metadata=bytearray(struct.pack('<4sHH',b'PC8D',1,30)+bytes(30*8))
 for i,index in enumerate(a.indices):
  n=11-i;pointer=struct.unpack_from('<I',packed,0x1a490+4*n)[0]
  struct.pack_into('<II',metadata,8+index*8,len(inputs[i])*2,pointer)
 sy=symbols(Path('src/main.sym'));asm='''SoundAdmissionMixFixture:
.a16
.i16
 php
 rep #$39
 phx
 phy
 phd
 phb
 lda #0
 tcd
 sep #$20
.a8
 pha
 plb
 lda #$60
 sta.w $2200
 lda #0
 sta.w $2201
 sta.w $2228
 lda #$A0
 sta.w $2202
 lda #$80
 sta.w $2226
 sta.w $2231
 lda #$FF
 sta.w $2229
 lda #2
 sta.w $2222
 lda #3
 sta.w $2223
 rep #$30
.a16
.i16
'''
 for i,(index,pcm)in enumerate(zip(a.indices,inputs)):
  for off,value in ((2,0),(4,index),(6,len(pcm)>>16),(8,len(pcm)&65535)):asm+=f' lda #{value}\n sta.l {W}+{off}\n'
  asm+=f' ldx #1\n ldy #0\n jsl SoundAdmission_Run\n bcc SoundAdmissionMixNext{i}\n jmp SoundAdmissionMixBad\nSoundAdmissionMixNext{i}:\n.a16\n.i16\n jsl SoundPCM8Descriptor_Run\n bcc SoundAdmissionMixBind{i}\n jmp SoundAdmissionMixBad\nSoundAdmissionMixBind{i}:\n.a16\n.i16\n'
 asm+=' jsl SoundPCM8Descriptor_Run\n bcc SoundAdmissionDescriptorFirstGood\n jmp SoundAdmissionMixBad\nSoundAdmissionDescriptorFirstGood:\n.a16\n.i16\n'
 asm+=' jsl SoundAdmission_Run\n bcc SoundAdmissionMixReplayGood\n jmp SoundAdmissionMixBad\nSoundAdmissionMixReplayGood:\n.a16\n.i16\n'
 for i in range(12):
  for off in (0,2):asm+=f' lda.l {BASE}+{40*i+32+off}\n sta.l {PHASE}+{4*i+off}\n lda.l {BASE}+{40*i+off}\n sta.l {ACTIVE}+{4*i+off}\n'
 asm+=''' lda #0
 sta.l $413FF0
 ldx #0
SoundAdmissionMixCopy:
 lda.l SoundAdmissionMixWorker+2555904,x
 sta.l $003500,x
 inx
 inx
 cpx #WORKERBYTES
 bne SoundAdmissionMixCopy
 sep #$20
.a8
 lda #0
 sta.w $2203
 lda #$35
 sta.w $2204
 lda #0
 sta.w $2205
 sta.w $2200
 rep #$30
.a16
.i16
SoundAdmissionMixWait:
 lda.l $413FF0
 cmp #$B4AB
 bne SoundAdmissionMixWait
'''.replace('WORKERBYTES',str((len(worker)+1)&~1))
 for i in range(12):
  for off in (0,2):asm+=f' lda.l {PHASE}+{4*i+off}\n sta.l {BASE}+{40*i+32+off}\n lda.l {ACTIVE}+{4*i+off}\n sta.l {BASE}+{40*i+off}\n'
  asm+=f' lda.l {ACTIVE}+{4*i}\n sta.l $7EFF88+{8*i+6}\n'
 asm+=''' plb
 pld
 ply
 plx
 plp
 clc
 rtl
SoundAdmissionMixBad:
.a16
.i16
 plb
 pld
 ply
 plx
 plp
 sec
 rtl
SoundAdmissionMixWorker:
 .db '''+','.join(str(v)for v in worker+bytes(len(worker)%2))+'\n'+emit(W,BASE,sy)+descriptors(W,BASE,LENGTHS,BASES,METADATA,sy)
 def transform(raw,linked):
  start=0x210000;end=start+sum(len(c['values'])*2 for c in channels);assert raw[start:end]==bytes(end-start)
  raw[start:end]=packed[start:end]
 lua='local mixSymbols='+luav({k:v for k,v in sy.items()if k.startswith(('SourceForeignWork_','StageFp_','StreamScrollFp_'))or k=='DmaQueue'})+'\nfor k,v in pairs(mixSymbols)do sy[k]=v end\n'+LUA
 lua=lua.replace(' before={};for i=0,479',f' for j=0,95 do put({LENGTHS}+j,0,1)end\n before={{}};for i=0,479')
 lua=lua.replace('{active,1,25-i,priority,9,-7,8,2,12345,9}','{0,0,0,0,0,0,0,0,0,0}').replace('put(0x7eff8c+8*i,25-i)','put(0x7eff8c+8*i,0)')
 lua+='\nemu.addMemoryCallback(function()local b={};for i=0,'+str(frames*4-1)+' do b[#b+1]=string.format("%02x",emu.read(0x420000+i,mt))end;emu.log("ADMISSIONMIXPCM|"..table.concat(b))end,emu.callbackType.exec,'+str(entries['done'])+','+str(entries['done'])+',emu.cpuType.sa1,emu.memType.sa1Memory)\n'
 lua+='\nlocal mixJobClock=0;emu.addMemoryCallback(function()mixJobClock=emu.getState().masterClock end,emu.callbackType.exec,'+str(entries['entry'])+','+str(entries['entry'])+',emu.cpuType.sa1,emu.memType.sa1Memory)\n'
 lua+='emu.addMemoryCallback(function()emu.log("ADMISSIONMIXCOST|"..(emu.getState().masterClock-mixJobClock))end,emu.callbackType.exec,'+str(entries['done'])+','+str(entries['done'])+',emu.cpuType.sa1,emu.memType.sa1Memory)\n'
 for k,v in dict(BASE=BASE,W=W).items():lua=re.sub(r'\b'+k+r'\b',str(v),lua)
 observed={}
 def closeout(m,linked,completed):observed.update(channels=m.read_memory('SnesMemory',BASE,480),playid=m.read_memory('SnesMemory',W+24,4))
 reporter=Reporter('M4-SOUND-ADMISSION-MIX',kind='GATE');row=dict(mask=0,pattern=0,priority=0,fault=0,length=len(inputs[0]),period=4096,left=64,right=64,selected=-1)
 raw,log=run_fixture(a.rom,a.output,[row],'SoundAdmissionMixFixture','SourceSoundChannels4086_Ready',0xb63a,[(58,0,bytes(metadata))],lua,reporter,append=asm,batch_size=1,frame_limit=2000,rom_transform=transform,closeout=closeout,link_pcm=False)
 actual=b''.join(bytes.fromhex(l.split('ADMISSIONMIXPCM|')[1])for l in log.splitlines()if'ADMISSIONMIXPCM|'in l)
 wanted=bytearray(480)
 for i,index in enumerate(a.indices):struct.pack_into('<10I',wanted,(11-i)*40,states[1+i*3],0,index,0,i+1,64,64,1,states[2+i*3],4096)
 reporter.check('bank 0 remains byte-identical',raw[:32768]==a.rom.read_bytes()[:32768])
 reporter.check('source-admitted channels feed exact native PCM and retain source phase, activity and replay identity',actual==expected[:-24]and observed.get('channels')==wanted and observed.get('playid')==struct.pack('<I',2))
 (a.output/'expected.bin').write_bytes(expected[:-24]+wanted+struct.pack('<I',2));(a.output/'observed.bin').write_bytes(actual+observed.get('channels',b'')+observed.get('playid',b''))
 clocks=[int(l.split('ADMISSIONMIXCOST|')[1])for l in log.splitlines()if'ADMISSIONMIXCOST|'in l]
 reporter.check('native cost trace covers each mixer job',len(clocks)==a.jobs)
 report=dict(worker_source_descriptors_follow_native_admission=True,descriptor_metadata_sha256=hashlib.sha256(metadata).hexdigest(),descriptor_metadata_complete_namespace=False,private_worker_source_descriptors=[LENGTHS,BASES+48],batch_master_clocks=clocks,schema='BYOR_SOURCE_ADMISSION_PCM_JOIN_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',jobs=a.jobs,frames_per_job=frames,native_worker_bytes=len(worker),PCM_bytes=len(actual),PCM_sha256=hashlib.sha256(actual).hexdigest(),source_identities=identities,source_functions_sha256={n:hashlib.sha256(b.encode('latin1')).hexdigest()for n,b in bodies.items()},rom_sha256=hashlib.sha256(raw).hexdigest(),logical_source_channels=[11,10],source_phase_overridden=False,source_frame_ack_bound=False,BRR_SPC_transport_bound=False,production_memory_lease=False,private_channel_controls=[W,BASE+480],private_worker_phases=[PHASE,ACTIVE+48],no_PCM_files_copied=True,no_color_reduction=True,motu_gameplay_proven=False)
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');reporter.finish()
if __name__=='__main__':main()
