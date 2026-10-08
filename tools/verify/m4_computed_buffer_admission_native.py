"""Reject stale/malformed completed-BRR offers without starting transport."""
import argparse
import hashlib
import json
from pathlib import Path
from _source_leaf_fixture import run_fixture, REQUEST
from _harness import Reporter
from m4_input_controller_native import offset


def cases():
 return [
  ('disabled',{'ready':0},'',2),('writing',{'state':1},'',2),
  ('already_consuming',{'state':3},'',2),('zero_generation',{'generation':0,'generation_hi':0},'',2),
  ('stale_low',{},' lda #$4087\n',2),('stale_high',{},' ldx #$1235\n',2),
  ('zero_blocks',{'blocks':0},'',2),('too_many_blocks',{'blocks':6145},'',2),
  ('wrong_length',{'bytes':109},'',2),('meaningful_extent',{'offset':0xD795},'',2),
  ('padded_extent',{'offset':0xD794},'',2),('zero_chunks',{'chunks':0},'',2),
  ('too_many_chunks',{'chunks':385},'',2),('wrong_chunk_count',{'chunks':2},'',2),
  ('intermediate_end',{},' pha\n lda #$91\n sta.l $422200\n pla\n',2),
  ('final_loop',{},' pha\n lda #$A7\n sta.l $422263\n pla\n',2),
  ('nonzero_padding',{},' pha\n lda #1\n sta.l $42226C\n pla\n',2),
  ('busy',{'active':1},'',3),
 ]


def assembly(rows):
 code=r'''
ComputedAdmissionWait:
.a16
.i16
 php
 rep #$31
 pha
 phx
 phy
 lda.l REQUEST
 cmp #$B4AD
 bne ComputedAdmissionWaitDone
 lda #0
 sta.l REQUEST
 jsl ComputedAdmissionFixture
 bcc ComputedAdmissionWaitGood
 lda #1
 sta.l ERROR
 bra ComputedAdmissionWaitDone
ComputedAdmissionWaitGood:
.a16
.i16
 lda #1
 sta.l INDEX
ComputedAdmissionWaitDone:
.a16
.i16
 ply
 plx
 pla
 plp
 jml REALWAIT
ComputedAdmissionFixture:
.a16
.i16
 php
 rep #$31
 pha
 phx
 phy
 lda #0
 sta.l STREAMENABLE
 sep #$20
.a8
 lda #$60
 sta.w $2200
 lda #$80
 sta.w $2226
 lda #0
 sta.w $2228
 sta.w $2230
 rep #$30
.a16
.i16
'''
 addresses=dict(ready='OFFERREADY',state='OFFERSTATE',generation='OFFERGEN',generation_hi='OFFERGEN+2',offset='OFFEROFFSET',bytes='OFFERBYTES',blocks='OFFERBLOCKS',chunks='OFFERCHUNKS',active='STREAMACTIVE')
 for i,(name,changes,mutation,status)in enumerate(rows):
  state=dict(ready=0xB66C,state=2,generation=0x4086,generation_hi=0x1234,offset=0x2200,bytes=108,blocks=12,chunks=1,active=0);state.update(changes)
  code+=f'ComputedAdmissionCase{i}:\n.a16\n.i16\n nop\n ldx #0\nComputedAdmissionCopy{i}:\n lda.l $3B8000,x\n sta.l $422200,x\n inx\n inx\n cpx #144\n bne ComputedAdmissionCopy{i}\n'
  for field,value in state.items():code+=f' lda #{value}\n sta.l {addresses[field]}\n'
  code+=' lda #$5A5A\n sta.l SOURCEINDEX\n lda #$3456\n sta.l SOURCESTATUS\n lda #$CDEF\n sta.l CONSUMERGEN\n lda #$89AB\n sta.l CONSUMERGEN+2\n lda #$4086\n ldx #$1234\n'+mutation+' jsl STARTCOMPUTED\n'
  code+=f' bcs ComputedAdmissionRejected{i}\n jmp ComputedAdmissionBad\nComputedAdmissionRejected{i}:\n.a16\n.i16\n nop\n'
  for field,value in [('OFFERSTATUS',status),('OFFERSTATE',state['state']),('SOURCEINDEX',0x5A5A),('SOURCESTATUS',0x3456),('CONSUMERGEN',0xCDEF),('CONSUMERGEN+2',0x89AB),('STREAMACTIVE',state['active'])]:
   label=f'ComputedAdmissionCheck{i}_{field.replace("+", "_")}'
   code+=f' lda.l {field}\n cmp #{value}\n beq {label}\n jmp ComputedAdmissionBad\n{label}:\n.a16\n.i16\n'
 code+=''' lda #0
 sta.l OFFERREADY
 sta.l STREAMACTIVE
 ply
 plx
 pla
 plp
 clc
 rtl
ComputedAdmissionBad:
.a16
.i16
 ply
 plx
 pla
 plp
 sec
 rtl
'''
 return code


def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('rom','audio','output'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
 payload=(a.audio/'native.brr').read_bytes();ar=json.loads((a.audio/'report.json').read_text())
 if len(payload)!=108 or hashlib.sha256(payload).hexdigest()!=ar['brr_sha256']:raise ValueError('ADMISSION_NATIVE_PAYLOAD_IDENTITY')
 rows=cases();probes={f'CASE{i}':f'ComputedAdmissionCase{i}'for i in range(len(rows))}
 lua=''
 for i,(name,_,_,_)in enumerate(rows):lua+=f"emu.addMemoryCallback(function()emu.log('COMPUTEDCASE|{i}|{name}')end,emu.callbackType.exec,CASE{i},CASE{i},emu.cpuType.snes,emu.memType.snesMemory)\n"
 def transform(raw,sy):
  at=offset(sy['Core_Nmi_WaitFrame'])
  if raw[at:at+4]!=b'\x5c'+sy['Tad_StreamWaitFrame'].to_bytes(3,'little'):raise ValueError('ADMISSION_WAIT_LAYOUT')
  raw[at+1:at+4]=sy['ComputedAdmissionWait'].to_bytes(3,'little')
 def before(m,sy):
  m.write_memory('SnesMemory',0x2007,'00');m.write_u16(REQUEST+6,0)
  for n in ('SourceVMRun4086_Ready','SourceVMRun4086_Busy','VmSourceFrame_Pending'):m.write_u16(sy[n],0)
  m.write_u16(sy['Game_State'],3)
 def closeout(m,sy,completed):
  (out/'audio-state.json').write_text(json.dumps(m.get_audio_state(),indent=2)+'\n')
  (out/'consumer-control.bin').write_bytes(m.read_memory('SnesMemory',sy['SourceComputedAudio_Ready'],26))
 bindings=dict(REALWAIT='Tad_StreamWaitFrame',STARTCOMPUTED='SourceComputedAudio_Start',OFFERREADY='SourceComputedAudio_Ready',OFFERSTATE='SourceComputedAudio_State',OFFERGEN='SourceComputedAudio_Generation',OFFEROFFSET='SourceComputedAudio_Offset',OFFERBYTES='SourceComputedAudio_Bytes',OFFERBLOCKS='SourceComputedAudio_Blocks',OFFERCHUNKS='SourceComputedAudio_Chunks',OFFERSTATUS='SourceComputedAudio_Status',CONSUMERGEN='SourceComputedAudio_ConsumerGeneration',SOURCEINDEX='SourceAudio_Index',SOURCESTATUS='SourceAudio_Status',STREAMACTIVE='AudioSemantic_FootDieStreamActive',STREAMENABLE='AudioStream_Enable')
 r=Reporter('M4-COMPUTED-BUFFER-ADMISSION',kind='GATE')
 raw,log=run_fixture(a.rom,out,[dict(cases=len(rows))],'ComputedAdmissionFixture','VmSourceFrame_Pending',0xB4AD,[(59,0,payload+bytes(36))],lua,r,append=assembly(rows),bindings=bindings,probes=probes,batch_size=1,frame_limit=200,rom_transform=transform,before_start=before,closeout=closeout,link_pcm=False)
 observed=[v.split('COMPUTEDCASE|',1)[1].split('|')for v in log.splitlines()if'COMPUTEDCASE|'in v]
 r.check('all stale and malformed native cases execute in order',observed==[[str(i),v[0]]for i,v in enumerate(rows)])
 state=json.loads((out/'audio-state.json').read_text());voice=next(v for v in state['voices']if v['voice']==0)
 r.check('rejected offers do not activate the reserved DSP voice',voice['envelope']==0)
 report=dict(schema='BYOR_COMPUTED_BUFFER_NATIVE_REJECTIONS_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',cases=[dict(name=n,expected_status=s)for n,_,_,s in rows],checks=r.results,ROM_sha256=hashlib.sha256(raw).hexdigest(),active_identity_preserved=True,consumer_generation_preserved=True,no_color_reduction=True,production_workspace_lease=False,motu_gameplay_proven=False,PCM_media_linked=False,scope='Private paused native rejection cases with compiler-owned payload. Actual consumer code rejects each offer without changing active source identity, admitted generation or stream state.')
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
 if report['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
