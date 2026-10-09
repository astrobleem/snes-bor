"""Live SPC consumption of actually admitted native source PCM/BRR jobs."""
import argparse,hashlib,json,math,re,sys
from pathlib import Path
from unittest.mock import patch
import m4_sound_admission_mix_native as parent
from _harness import Reporter
from m4_projectile_audio_fixture import configure
from m4_source_audio_native_verify import verify
from source_frame_audio_rom import pack
from m4_input_controller_native import offset
from actor_s5_entity_fixture import symbols
from m4_live_mix_spc_native import ASM as LIVEASM


def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('rom','source','assets','authority-scaffold','producer','output'):p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--startup-jobs',type=int,choices=(2,4,8),default=2);p.add_argument('--prefill-chunks',type=int,choices=range(1,8),default=1);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
 pr=json.loads((a.producer/'report.json').read_text());assert pr['status']=='PASS'and pr['native_codec_bound']and pr['descriptor_metadata_complete_namespace'];expected=(a.producer/'native.brr').read_bytes();assert hashlib.sha256(expected).hexdigest()==pr['BRR_sha256'];assert pr['jobs']>a.startup_jobs
 assets=a.output/'expected-assets';assets.mkdir(exist_ok=True);(assets/'expected.brr').write_bytes(expected)
 row=dict(sound_index=0,source_path='private-admitted-native-mixture',source_sha256=pr['PCM_mono_sha256'],brr_path='expected.brr',brr_sha256=pr['BRR_sha256'],brr_bytes=len(expected),normalized_sample_rate=11025,normalized_frames=pr['jobs']*176,audio_adaptation='ACCEPTED_COMPAT mono/11025/predictive BRR')
 (assets/'report.json').write_text(json.dumps(dict(namespace=[row['source_path']],compiled=[row],source_frame_table_sha256=hashlib.sha256(b'private admitted mix').hexdigest()),indent=2)+'\n')
 packed=a.output/'expected-descriptor';pack(assets,packed)
 _,audio_transform,audio_before,audio_closeout=configure(a.output,assets,row['source_path'],isolate=True,prefill=True,generic_rom=packed,prefill_chunks=a.prefill_chunks)
 sy=symbols(Path('src/main.sym'));reporter=Reporter('M4-SOURCE-ADMISSION-LIVE-SPC',kind='GATE');original=parent.run_fixture
 control={};captured={}
 def fixture(rom,folder,rows,apply,ready,magic,tables,lua,ignored,**kw):
  asm=kw['append'];startup=a.startup_jobs*99
  # Clear the full final transfer packet as native storage ownership.
  clear=f''' lda #0
 ldx #0
AdmissionLiveClear:
 sta.l $430000,x
 inx
 inx
 cpx #{math.ceil(len(expected)/144)*144}
 bne AdmissionLiveClear
'''
  needle=' lda #0\n sta.l 4452352';assert asm.count(needle)==1
  asm=asm.replace(needle,clear+needle)
  # A bounded initial watermark parks the producer after the first lead jobs.
  needle=' lda #0\n sta.l $413FF0';assert asm.count(needle)==1
  asm=asm.replace(needle,f' lda #0\n sta.l $43F006\n lda #{startup}\n sta.l $43F008\n'+needle)
  needle=' lda.l $413FF0\n cmp #$B4AB\n bne SoundAdmissionMixWait';assert asm.count(needle)==1
  asm=asm.replace(needle,f' lda.l $43F006\n cmp #{startup}\n bcc SoundAdmissionMixWait')
  # The original tail copies the phase snapshot back while the producer is
  # parked. Then actual prepared transport owns the first sample epoch.
  needle=' plb\n pld\n ply\n plx\n plp\n clc\n rtl\nSoundAdmissionMixBad:';assert asm.count(needle)==1
  start=f'''AdmissionLiveStart:
.a16
.i16
 nop
 lda #0
 sta.l {sy['SourceAudio_BaseLo']}
 sta.l {sy['SourceAudio_LengthHi']}
 lda #{len(expected)}
 sta.l {sy['AudioStream_SourceLength']}
 lda #{math.ceil(len(expected)/144)}
 sta.l {sy['AudioStream_SourceChunks']}
 lda #$FFFF
 sta.l {sy['SourceAudio_Index']}
 lda #1
 sta.l {sy['SourceAudio_Status']}
 sep #$20
.a8
 lda #$43
 sta.l {sy['SourceAudio_BaseBank']}
 lda #$FF
 sta.l {sy['AudioStream_SourceId']}
 jsl {sy['SourceAudio_StartPreparedNear']}
 rep #$30
.a16
.i16
'''
  asm=asm.replace(needle,start+needle)
  # Capture codec history before patching its final stop to publish readiness
  # and synchronize the complete logical rows without observer writes.
  prefix='SoundAdmissionMixEncoder:\n .db ';assert asm.count(prefix)==1
  begin=asm.index(prefix)+len(prefix);end=asm.index('\n',begin)
  data=bytes(map(int,asm[begin:end].split(',')));needle=bytes.fromhex('c2 20 a9 ab b4 8f f0 3f 41');assert data.count(needle)==0 # Final marker is after the restore-JML split.
  # Tail bytes after the JML are a separate .db line in the generated blob.
  anchor=' .dl SoundAdmissionMixRestoreExchange+2555904\n .db ';begin=asm.index(anchor)+len(anchor);end=asm.index('\n',begin);tail=bytes(map(int,asm[begin:end].split(',')))
  assert tail.count(needle)==1 and tail[-3]==0x4c
  tail=tail.replace(needle,bytes.fromhex('c2 20 af 04 f0 43 8f 06 f0 43 a9 ab b4 8f f0 3f 41'))
  tail=tail[:-3];asm=asm[:begin]+','.join(map(str,tail))+'\n .db $5C\n .dl AdmissionLiveFinal+2555904'+'\n .db 0'+asm[end:]
  # Patched encoder grew by nine bytes; update the two code-DMA length immediates.
  old=pr['encoder_worker_bytes'];assert asm.count(f' lda #{old}\n sta.w $2238')==1
  asm=asm.replace(f' lda #{old}\n sta.w $2238',f' lda #{old+9}\n sta.w $2238')
  sync=''
  for i in range(12):
   for off in (0,2):sync+=f' lda.l {parent.PHASE}+{4*i+off}\n sta.l {parent.BASE}+{40*i+32+off}\n lda.l {parent.ACTIVE}+{4*i+off}\n sta.l {parent.BASE}+{40*i+off}\n'
  gate=f'''SoundAdmissionMixRestoreExchange:
.a16
.i16
 rep #$30
{sync} lda.l $43F004
 sta.l $43F006
AdmissionLiveProducerWait:
 lda.l $43F004
 cmp.l $43F008
 bcs AdmissionLiveProducerWait
'''
  asm=asm.replace('SoundAdmissionMixRestoreExchange:\n.a16\n.i16\n',gate)
  asm+=f'''AdmissionLiveFinal:
.a16
.i16
 rep #$30
{sync}AdmissionLiveStop:
 jmp AdmissionLiveStop
AdmissionLiveWait:
.a16
.i16
 php
 rep #$31
 pha
 phx
 phy
 lda.l $7FFD80
 cmp #$B63A
 bne AdmissionLiveWaitUpdate
 lda #0
 sta.l $7FFD80
AdmissionLiveInvoke:
.a16
.i16
 nop
 jsl SoundAdmissionMixFixture
 bcc AdmissionLiveInvokeGood
 lda #1
 sta.l $7FFD84
 bra AdmissionLiveWaitUpdate
AdmissionLiveInvokeGood:
.a16
.i16
 lda #1
 sta.l $7FFD82
AdmissionLiveWaitUpdate:
.a16
.i16
 lda.l {sy['TadPrivate_stream_source_offset']}
 clc
 adc #1440
 sta.l $43F008
 ply
 plx
 pla
 plp
 jml {sy['Tad_StreamWaitFrame']}
'''
  # Use the existing measured host read guard, with this mixture's length.
  readguard=LIVEASM[LIVEASM.index('LiveMixReadGuard:'):].replace('BRRBYTES',str(len(expected))).replace('FILLROWS',str(sy['SourceAudio_FillHdmaRows']))
  asm+=readguard
  original_transform=kw['rom_transform']
  def transform(raw,linked):
   audio_transform(raw,linked);original_transform(raw,linked)
   at=offset(linked['Vm_SourceFrameGate']);raw[at:at+5]=a.rom.read_bytes()[at:at+5]
   at=offset(linked['Core_Nmi_WaitFrame']);assert raw[at:at+4]==b'\x5c'+linked['Tad_StreamWaitFrame'].to_bytes(3,'little');raw[at+1:at+4]=linked['AdmissionLiveWait'].to_bytes(3,'little')
   needle=b'\x22'+linked['SourceAudio_FillHdmaRows'].to_bytes(3,'little');assert raw.count(needle)==1;at=raw.index(needle);raw[at+1:at+4]=linked['LiveMixReadGuard'].to_bytes(3,'little')
  def before(m,linked):
   audio_before(m,linked);m.write_u16(sy['Game_State'],3);m.write_u16(0x7fbfe0,0)
   for n in ('SourceVMRun4086_Ready','SourceVMRun4086_Busy','VmSourceFrame_Pending'):m.write_u16(sy[n],0)
  def closeout(m,linked,completed):
   audio_closeout(m,linked,completed)
   kw_original_closeout(m,linked,completed)
   captured['brr']=m.read_memory('SnesMemory',0x430000,len(expected));captured['rows']=m.read_memory('SnesMemory',parent.BASE,480)
   control.update(jobs=int.from_bytes(m.read_memory('SnesMemory',0x43f002,2),'little'),ready_bytes=int.from_bytes(m.read_memory('SnesMemory',0x43f006,2),'little'),phase=m.read_memory('SnesMemory',parent.PHASE,48).hex(),active=m.read_memory('SnesMemory',parent.ACTIVE,48).hex(),packet_waits=int.from_bytes(m.read_memory('SnesMemory',0x7fbfe0,2),'little'),guard=m.read_memory('SnesMemory',0x413ff2,2).hex())
  kw_original_closeout=kw['closeout']
  kw.update(append=asm,rom_transform=transform,before_start=before,closeout=closeout,emulator_env=dict(MESEN_VOICE_CAPTURE_PATH=str(a.output/'voice0.raw'),MESEN_VOICE_CAPTURE_VOICE='0',MESEN_VOICE_CAPTURE_ARM_FILE=str(a.output/'voice0.raw.arm')))
  lua=re.sub(r'\bINIT\b','ADMISSIONINIT',lua)
  kw.setdefault('probes',{}).update(ADMISSIONBAD='SoundAdmissionMixBad',ADMISSIONINIT='AdmissionLiveInvoke',ADMISSIONSTART='AdmissionLiveStart',LIVEGATE='AdmissionLiveProducerWait',LIVEPACKET='LiveMixReadGuard')
  lua+='''\nlocal admissionStarted=false;local lastLateJob=-1
emu.addMemoryCallback(function()emu.log("ADMITTEDINVOKE")end,emu.callbackType.exec,ADMISSIONINIT,ADMISSIONINIT,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()emu.log("ADMITTEDBAD|"..word(0x43f012))end,emu.callbackType.exec,ADMISSIONBAD,ADMISSIONBAD,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()admissionStarted=true;emu.log("ADMITTEDLIVESTART|"..emu.getState().masterClock.."|"..word(0x43f002))end,emu.callbackType.exec,ADMISSIONSTART,ADMISSIONSTART,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()local j=word(0x43f002);if admissionStarted and j~=lastLateJob then lastLateJob=j;emu.log("ADMITTEDLATEJOB|"..j)end end,emu.callbackType.exec,LIVEGATE,LIVEGATE,emu.cpuType.sa1,emu.memType.sa1Memory)
'''
  raw,log=original(rom,folder,rows,apply,ready,magic,tables,lua,reporter,**kw)
  captured.update(raw=raw,log=log)
  # Both collectors read the completed native state after real DSP consumption.
  parent_expected=(a.producer/'expected.bin').read_bytes();captured['expected_rows']=parent_expected[-484:-4]
  return raw,log
 args=['m4_sound_admission_mix_native.py','--rom',str(a.rom),'--source',str(a.source),'--assets',str(a.assets),'--authority-scaffold',str(a.authority_scaffold),'--output',str(a.output/'producer-build'),'--complete-namespace','--encode-brr','--private-audio-wait-hook','--jobs',str(pr['jobs']),'--indices',*[str(r['sound_index'])for r in pr['source_identities']]]
 # Keep the completed PCM/BRR join gate alongside the live DSP gate.
 with patch.object(parent,'run_fixture',fixture),patch.object(sys,'argv',args):
  try:parent.main()
  except SystemExit as e:
   if e.code:reporter.check('completed producer PCM/BRR gate passes',False)
 joined=json.loads((a.output/'producer-build'/'report.json').read_text())
 reporter.check('completed producer PCM/BRR gate passes',joined['status']=='PASS')
 try:proof=verify(a.output,assets,require_dsp_trace=True)
 except AssertionError as e:proof=dict(status='FAIL',error=str(e))
 starts=[l.split('ADMITTEDLIVESTART|')[1].split('|')for l in captured.get('log','').splitlines()if'ADMITTEDLIVESTART|'in l];late=[l for l in captured.get('log','').splitlines()if'ADMITTEDLATEJOB|'in l]
 reporter.check('actual logical source admission precedes live SPC start; later native jobs complete',len(starts)==1 and int(starts[0][1])==a.startup_jobs and len(late)>0 and control.get('jobs')==pr['jobs'])
 reporter.check('completed native BRR, source rows and readiness match admitted authority',captured.get('brr')==expected and captured.get('rows')==captured.get('expected_rows')and control.get('ready_bytes')==len(expected)and control.get('packet_waits')==0 and control.get('guard')=='0000')
 reporter.check('production SPC consumes every admitted mixture block exactly',proof['status']=='PASS')
 (a.output/'native-live.brr').write_bytes(captured.get('brr',b''))
 result=dict(schema='BYOR_SOURCE_ADMISSION_LIVE_SPC_NATIVE_V1',status='PASS'if all(ok for _,ok in reporter.results)else'FAIL',checks=reporter.results,proof=proof,control=control,start=starts,late_job_observations=len(late),producer_gate_sha256=hashlib.sha256((a.output/'producer-build'/'report.json').read_bytes()).hexdigest(),native_job_peak_master_clocks=joined['peak_job_master_clocks'],encoder_IRAM_bytes=pr['encoder_worker_bytes']+9,gather_IRAM_bytes=pr['gather_worker_bytes'],private_bank0_wait_hook_operand_bytes=3,production_bank0_code_added=0,producer_authority_sha256=hashlib.sha256((a.producer/'report.json').read_bytes()).hexdigest(),ROM_sha256=hashlib.sha256(captured.get('raw',b'')).hexdigest(),source_identities=pr['source_identities'],actual_logical_admission=True,production_SPC_driver_override=False,source_frame_ack_bound=False,production_memory_lease=False,joint_graphics_bound=False,motu_gameplay_proven=False,no_color_reduction=True,no_PCM_files_copied=True,startup_jobs=a.startup_jobs,prefill_chunks=a.prefill_chunks)
 (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');reporter.finish()
if __name__=='__main__':main()

