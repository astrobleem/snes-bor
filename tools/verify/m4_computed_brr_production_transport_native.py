"""Isolated native twelve-source producer feeding production TAD from BW-RAM.

The private fixture replaces the dormant SA-1 worker while gameplay is paused.
It does not install a production workspace lease or a continuous mixer owner.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from _source_leaf_fixture import run_fixture, REQUEST
from _harness import Reporter
from m4_sound_mix_sa1_native import Code
from m4_projectile_audio_fixture import configure
from m4_source_audio_native_verify import verify
from m4_input_controller_native import offset
from source_frame_audio_rom import pack


ASM=r'''
ComputedAudioWait:
.a16
.i16
 php
 rep #$31
 pha
 phx
 phy
 lda.l REQUEST
 cmp #$B4AD
 bne ComputedAudioWaitDone
 lda #0
 sta.l REQUEST
 jsl ComputedAudioFixture
 bcs ComputedAudioWaitBad
 lda #1
 sta.l INDEX
 bra ComputedAudioWaitDone
ComputedAudioWaitBad:
.a16
.i16
 lda #1
 sta.l ERROR
ComputedAudioWaitDone:
.a16
.i16
 ply
 plx
 pla
 plp
 jml REALWAIT
ComputedAudioFixture:
.a16
.i16
 php
 rep #$31
 pha
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
 ; Private ownership replacement only, never a production lease.
 lda #$60
 sta.w $2200
 lda #0
 sta.w $2201
 sta.w $2228
 lda #$A0
 sta.w $2202
 lda #$80
 sta.w $2226
 lda #$FF
 sta.w $2229
 lda #2
 sta.w $2222
 lda #3
 sta.w $2223
 rep #$30
.a16
.i16
 lda #0
 ldx #0
ComputedAudioClearTail:
 sta.l $422200,x
 inx
 inx
 cpx #144
 bne ComputedAudioClearTail
 ldx #0
ComputedAudioPhases:
 lda.l $E2F000,x
 sta.l $422300,x
 inx
 inx
 cpx #48
 bne ComputedAudioPhases
 ldx #0
ComputedAudioWorker:
 lda.l $3B8000,x
 sta.l $003500,x
 inx
 inx
 cpx #WORKERBYTES
 bne ComputedAudioWorker
 lda #0
 sta.l $0030F0
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
ComputedAudioJobWait:
 lda.l $0030F0
 cmp #$B4AB
 bne ComputedAudioJobWait
ComputedAudioProduced:
.a16
.i16
 nop
 lda.l $413FF2
 cmp #$DEAD
 beq ComputedAudioBad
 lda #$4086
 sta.l OFFERGENERATION
 lda #$1234
 sta.l OFFERGENERATION+2
 lda #$2200
 sta.l OFFEROFFSET
 lda #108
 sta.l OFFERBYTES
 lda #12
 sta.l OFFERBLOCKS
 lda #1
 sta.l OFFERCHUNKS
 lda #2
 sta.l OFFERSTATE
 lda #$B66C
 sta.l OFFERREADY
 lda #$4086
 ldx #$1234
 jsl STARTCOMPUTED
 bcs ComputedAudioBad
ComputedAudioPublished:
 nop
 plb
 pld
 ply
 plx
 pla
 plp
 clc
 rtl
ComputedAudioBad:
.a16
.i16
 plb
 pld
 ply
 plx
 pla
 plp
 sec
 rtl
'''


def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('rom','producer','audio','output'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
 producer=(a.producer/'proof.sfc').read_bytes();pr=json.loads((a.producer/'report.json').read_text())
 audio_report=json.loads((a.audio/'report.json').read_text());expected=(a.audio/'native.brr').read_bytes()
 if pr['status']!='PASS' or not pr['source_CHR_workspace_audio'] or hashlib.sha256(producer).hexdigest()!=pr['ROM_sha256']:
  raise ValueError('COMPUTED_AUDIO_PRODUCER_IDENTITY')
 if len(expected)!=108 or audio_report['frames']!=192 or audio_report['active_channels']!=12:
  raise ValueError('COMPUTED_AUDIO_BOUNDED_JOB_DOMAIN')
 assets=out/'expected-assets';assets.mkdir(exist_ok=True);(assets/'expected.brr').write_bytes(expected)
 row=dict(sound_index=0,source_path='private-proof/computed-twelve-source-buffer',source_sha256=audio_report['mixed_sha256'],brr_path='expected.brr',brr_sha256=hashlib.sha256(expected).hexdigest(),brr_bytes=len(expected),normalized_sample_rate=11025,normalized_frames=192,audio_adaptation=dict(policy='ACCEPTED_COMPAT',output='mono 11025 uniform gain 64; native predictive BRR'))
 manifest=dict(namespace=[row['source_path']],compiled=[row],source_frame_table_sha256=hashlib.sha256(b'private computed buffer offer').hexdigest())
 (assets/'report.json').write_text(json.dumps(manifest,indent=2)+'\n');packed=out/'expected-descriptor';pack(assets,packed)
 row,audio_transform,audio_before,closeout=configure(out,assets,row['source_path'],isolate=True,prefill=True,generic_rom=packed)
 # Extract the measured relocated native workers without altering arithmetic.
 gather=producer[0xa400:0xa580];encoder=producer[0xa600:0xa7f1]
 if gather[-4:]!=bytes.fromhex('5c 00 a9 01') or encoder[-4:]!=bytes.fromhex('5c 00 ab 01'):
  raise ValueError('COMPUTED_AUDIO_WORKER_LAYOUT')
 gather=gather[:-4]+bytes.fromhex('5c 00 90 3b')
 encoder=encoder[:-4]+bytes.fromhex('5c 00 91 3b')
 encoder=encoder.replace(bytes.fromhex('a9 b6 b4 8f f0 3f 41'),bytes.fromhex('ea ea ea ea ea ea ea'))
 finish=Code(0x9100);finish.emit('c2 30 a9 00 00 a2 00 00');finish.label('padding');finish.emit('9f 6c 22 42 e8 e8');finish.word(0xe0,36);finish.branch(0xd0,'padding');finish.emit('a9 ab b4 8f f0 30 00');finish.label('stop');finish.jump('stop');finish=finish.finish()
 glue=Code(0x9000);glue.emit('e2 20 a9 00 48 ab a9 80 8d 30 22 a9 20 8d 0b 22 c2 20 a9 00 88 8d 32 22 e2 20 a9 3b 8d 34 22 c2 20');glue.word(0xa9,len(encoder));glue.emit('8d 38 22 a9 00 35 8d 35 22 5c 00 35 00');glue=glue.finish()
 def transform(raw,sy):
  audio_transform(raw,sy)
  # Only verified empty ROM windows are used. The descriptor lives below
  # E banks; its unused expected payload remains at E0, outside these tables.
  if any(raw[0x210000:0x3f0000]):raise ValueError('COMPUTED_AUDIO_ROM_TABLE_RESERVATION')
  raw[0x210000:0x3f0000]=producer[0x210000:0x3f0000]
  for address,data in ((59*32768,gather),(59*32768+0x800,encoder),(59*32768+0x1000,glue),(59*32768+0x1100,finish)):
   if any(raw[address:address+len(data)]):raise ValueError('COMPUTED_AUDIO_ROM_WORKER_RESERVATION')
   raw[address:address+len(data)]=data
  at=offset(sy['Core_Nmi_WaitFrame'])
  if raw[at:at+4]!=b'\x5c'+sy['Tad_StreamWaitFrame'].to_bytes(3,'little'):raise ValueError('COMPUTED_AUDIO_WAIT_LAYOUT')
  raw[at+1:at+4]=sy['ComputedAudioWait'].to_bytes(3,'little')
 audio_closeout=closeout
 def closeout(m,sy,completed):
  diagnostic=dict(completed=completed,SCPU=m.get_cpu_state('Snes'),SA1=m.get_cpu_state('Sa1'),registers=m.read_memory('SnesMemory',0x2200,0x40).hex(),native_status=m.read_memory('SnesMemory',0x413ff0,10).hex(),IRAM_status=m.read_memory('SnesMemory',0x0030f0,2).hex(),SCPU_trace=m.trace_log(48),SA1_trace=m.trace_log(12,'Sa1'))
  (out/'native-dispatch-diagnostic.json').write_text(json.dumps(diagnostic,indent=2)+'\n');audio_closeout(m,sy,completed)
  control=m.read_memory('SnesMemory',sy['SourceComputedAudio_Ready'],26);(out/'computed-buffer-control.json').write_text(json.dumps(dict(hex=control.hex(),state=int.from_bytes(control[6:8],'little'),status=int.from_bytes(control[20:22],'little'),generation=control[2:6].hex(),consumer_generation=control[16:20].hex()),indent=2)+'\n')
 def before(m,sy):
  audio_before(m,sy)
  m.write_u16(REQUEST+6,0)
  m.write_u16(sy['SourceComputedAudio_Ready'],0)
  m.write_u16(sy['SourceComputedAudio_State'],0)
  for name in ('SourceVMRun4086_Ready','SourceVMRun4086_Busy','VmSourceFrame_Pending'):
   m.write_u16(sy[name],0)
  m.write_u16(sy['Game_State'],3)
  m.write_memory('SnesMemory',0x413ff2,'0000')
 lua=r'''
emu.addMemoryCallback(function()
 local bytes={};for j=0,107 do bytes[#bytes+1]=string.format('%02x',emu.read(0x422200+j,emu.memType.snesMemory))end
 emu.log('COMPUTEDBRR|'..table.concat(bytes))
 local pcm={};for j=0,383 do pcm[#pcm+1]=string.format('%02x',emu.read(0x422000+j,emu.memType.snesMemory))end
 emu.log('COMPUTEDPCM|'..table.concat(pcm))
 local tail={};for j=108,143 do tail[#tail+1]=string.format('%02x',emu.read(0x422200+j,emu.memType.snesMemory))end;emu.log('COMPUTEDTAIL|'..table.concat(tail))
end,emu.callbackType.exec,COMPUTEDPRODUCED,COMPUTEDPRODUCED,emu.cpuType.snes,emu.memType.snesMemory)
for name,address in pairs({invalid=COMPUTEDINVALID,produced=COMPUTEDPRODUCED,published=PUBLISHED,bad=PRIVATEBAD,waitbad=WAITBAD,leafafter=AFTER})do
 emu.addMemoryCallback(function()local state=emu.getState();emu.log('COMPUTEDRETURN|'..name..'|'..tostring(state['cpu.ps'])..'|'..tostring(state['cpu.a']))end,emu.callbackType.exec,address,address,emu.cpuType.snes,emu.memType.snesMemory)
end
'''
 r=Reporter('M4-NATIVE-COMPUTED-BRR-PRODUCTION-TRANSPORT',kind='GATE')
 env={'MESEN_VOICE_CAPTURE_PATH':str(out/'voice0.raw'),'MESEN_VOICE_CAPTURE_VOICE':'0','MESEN_VOICE_CAPTURE_ARM_FILE':str(out/'voice0.raw.arm')}
 raw,log=run_fixture(a.rom,out,[dict(native_source_voices=12)],'ComputedAudioFixture','SourceAudio_Status',0xb4ad,[],lua,r,append=ASM.replace('WORKERBYTES',str(len(gather))),bindings=dict(STARTCOMPUTED='SourceComputedAudio_Start',OFFERGENERATION='SourceComputedAudio_Generation',OFFEROFFSET='SourceComputedAudio_Offset',OFFERBYTES='SourceComputedAudio_Bytes',OFFERBLOCKS='SourceComputedAudio_Blocks',OFFERCHUNKS='SourceComputedAudio_Chunks',OFFERSTATE='SourceComputedAudio_State',OFFERREADY='SourceComputedAudio_Ready',REALWAIT='Tad_StreamWaitFrame',COMPUTEDINVALID='SourceComputedAudio_Start__invalid'),probes=dict(COMPUTEDPRODUCED='ComputedAudioProduced',PUBLISHED='ComputedAudioPublished',PRIVATEBAD='ComputedAudioBad',WAITBAD='ComputedAudioWaitBad'),batch_size=1,frame_limit=200,rom_transform=transform,before_start=before,closeout=closeout,emulator_env=env,link_pcm=False)
 proof=verify(out,assets,require_dsp_trace=True)
 def captured(tag):return [bytes.fromhex(line.split(tag+'|',1)[1])for line in log.splitlines()if tag+'|'in line]
 brr=captured('COMPUTEDBRR');pcm=captured('COMPUTEDPCM')
 control=json.loads((out/'computed-buffer-control.json').read_text())
 r.check('generic buffer retires only its admitted generation after DSP completion',control['state']==4 and control['status']==4 and control['generation']==control['consumer_generation'])
 r.check('native produced BRR matches authority before transport',brr==[expected])
 r.check('native produced source mixture matches pinned C',len(pcm)==1 and hashlib.sha256(pcm[0]).hexdigest()==audio_report['mixed_sha256'])
 result=dict(schema='BYOR_COMPUTED_BRR_PRODUCTION_TRANSPORT_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',checks=r.results,proof=proof,ROM_sha256=hashlib.sha256(raw).hexdigest(),producer_component_ROM=pr['ROM_sha256'],native_source_voices=12,native_output_samples=192,buffer_pointer='422200',native_producer_to_production_TAD=True,generic_computed_buffer_admission=True,native_transport_tail_zeroed=True,PCM_media_linked=False,computed_buffer_control=control,source_workspace_lease_installed=False,SA1_worker_replaced_in_private_paused_fixture=True,continuous_mixing=False,joint_hybrid_graphics=False,motu_gameplay_proven=False,no_color_reduction=True)
 (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
 if result['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
