"""Isolated native source mixing while production SPC transport consumes BRR.

Private paused ownership and a monotonic readiness watermark, not production
source event admission or a reusable memory lease.
"""
import argparse, hashlib, json, math, re, struct
from pathlib import Path
from _source_leaf_fixture import run_fixture, REQUEST
from _harness import Reporter
from m4_input_controller_native import offset
from m4_projectile_audio_fixture import configure
from m4_source_audio_native_verify import verify
from m4_sound_mix_sa1_native import Code
from source_frame_audio_rom import pack


ASM = r'''
LiveMixWait:
.a16
.i16
 php
 rep #$31
 pha
 phx
 phy
 lda.l REQUEST
 cmp #$B4AD
 bne LiveMixWaitUpdate
 lda #0
 sta.l REQUEST
 jsl LiveMixFixture
 lda #1
 sta.l INDEX
LiveMixWaitUpdate:
.a16
.i16
 lda.l SOURCECURSOR
 clc
 adc #1440
 sta.l $43F008
 ply
 plx
 pla
 plp
 jml REALWAIT
LiveMixFixture:
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
 ; This private fixture pauses the dormant worker, not a production lease.
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
 ; End any prior type-1 character conversion before raw S-CPU BW-RAM
 ; accesses. Merely parking the SA-1 does not clear the conversion view.
 lda #$80
 sta.w $2231
 lda #2
 sta.w $2222
 lda #3
 sta.w $2223
 rep #$30
.a16
.i16
 lda #0
 sta.l $43F000
 sta.l $43F002
 sta.l $43F004
 sta.l $43F006
 sta.l $413FF0
 sta.l $413FF2
 sta.l $7FBFE0
 lda #1188
 sta.l $43F008
 lda #0
 ldx #0
LiveMixClear:
 sta.l $430000,x
 inx
 inx
 cpx #PADDEDBYTES
 bne LiveMixClear
 ldx #0
LiveMixState:
 lda.l $E0F000,x
 sta.l $435000,x
 lda.l $E0F030,x
 sta.l $435100,x
 inx
 inx
 cpx #48
 bne LiveMixState
 ldx #0
LiveMixWorker:
 lda.l $3B8000,x
 sta.l $003500,x
 inx
 inx
 cpx #WORKERBYTES
 bne LiveMixWorker
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
LiveMixPrefillWait:
 lda.l $43F006
 cmp #1188
 bcc LiveMixPrefillWait
LiveMixStart:
 nop
 lda #0
 sta.l SOURCEBASE
 sta.l SOURCELENGTHHI
 lda #BRRBYTES
 sta.l SOURCELENGTH
 lda #CHUNKS
 sta.l SOURCECHUNKS
 lda #$FFFF
 sta.l SOURCEINDEX
 lda #1
 sta.l SOURCESTATUS
 sep #$20
.a8
 lda #$43
 sta.l SOURCEBANK
 lda #$FF
 sta.l SOURCEID
 jsl STARTPREPARED
 rep #$30
.a16
.i16
 plb
 pld
 ply
 plx
 pla
 plp
 clc
 rtl
; Verify the meaningful portion before the unchanged driver reads a packet.
LiveMixReadGuard:
.a8
.i16
 php
 rep #$20
.a16
 pha
 txa
 clc
 adc #144
 cmp #BRRBYTES
 bcc LiveMixRequired
 lda #BRRBYTES
LiveMixRequired:
 cmp.l $43F006
 bcc LiveMixReady
 beq LiveMixReady
 pha
 lda.l $7FBFE0
 inc a
 sta.l $7FBFE0
 pla
LiveMixReadWait:
 cmp.l $43F006
 bcc LiveMixReady
 beq LiveMixReady
 bra LiveMixReadWait
LiveMixReady:
 pla
 plp
 jml FILLROWS
'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for k in ('rom', 'producer', 'output'):
        p.add_argument('--'+k, type=Path, required=True)
    p.add_argument('--startup-jobs',type=int,choices=(2,4,8,12),default=12)
    p.add_argument('--no-prefill',action='store_true')
    p.add_argument('--prefill-chunks',type=int,choices=range(1,8),default=7)
    p.add_argument('--force-incoming-conversion',action='store_true')
    a = p.parse_args(); out = a.output.resolve(); out.mkdir(parents=True, exist_ok=True)
    pr = json.loads((a.producer/'report.json').read_text())
    assert pr['status']=='PASS' and pr['full_asset_lifetimes_and_native_codec_bound']
    producer = (a.producer/'proof.sfc').read_bytes()
    assert hashlib.sha256(producer).hexdigest()==pr['rom_sha256']
    expected = (a.producer/'native.brr').read_bytes()
    assert hashlib.sha256(expected).hexdigest()==pr['BRR_sha256']
    if pr['frames_per_job']!=176 or pr['jobs']!=108:
        raise ValueError('LIVE_MIX_PROVEN_COMPONENT_DOMAIN')
    assets = out/'expected-assets'; assets.mkdir(exist_ok=True)
    (assets/'expected.brr').write_bytes(expected)
    row = dict(sound_index=0, source_path='private-live-generated-mix',
               source_sha256=pr['PCM_sha256'], brr_path='expected.brr',
               brr_sha256=pr['BRR_sha256'], brr_bytes=len(expected),
               normalized_sample_rate=11025, normalized_frames=108*176,
               audio_adaptation='ACCEPTED_COMPAT mono/11025 Hz/predictive BRR')
    manifest = dict(namespace=[row['source_path']], compiled=[row],
                    source_frame_table_sha256=hashlib.sha256(b'private live mix').hexdigest())
    (assets/'report.json').write_text(json.dumps(manifest, indent=2)+'\n')
    packed = out/'expected-descriptor'; pack(assets, packed)
    _, audio_transform, audio_before, audio_closeout = configure(
        out, assets, row['source_path'], isolate=True, prefill=not a.no_prefill, generic_rom=packed,prefill_chunks=a.prefill_chunks if not a.no_prefill else None)
    # Retain measured arithmetic. Immutable predictor/quantizer tables move
    # to E1..FE; the two channel PCM allocations use E0 and FF respectively.
    gw = producer[0x9000:0x9000+pr['gather_worker_bytes']]
    ew = producer[0x9800:0x9800+pr['encoder_worker_bytes']]
    def sub(data, before, after, count=1):
        before=bytes.fromhex(before); after=bytes.fromhex(after)
        if data.count(before)!=count:raise ValueError('LIVE_MIX_RELOCATION:'+before.hex())
        return data.replace(before, after)
    gw = sub(gw, 'a5 06 4a 4a 18 69 e0 00', 'a6 06 bf 90 f0 e0 ea ea')
    gw = sub(gw, '5c 00 a0 01', '5c 00 90 3b')
    for before, after in (('a9 c3 85 24','a9 e3 85 24'),
                          ('e2 20 a9 c1','e2 20 a9 e1'), ('a9 de','a9 fe'),
                          ('bf 00 00 c3','bf 00 00 e3'),
                          ('85 0a 18 69 d1','85 0a 18 69 f1'),
                          ('a5 0a 18 69 c4','a5 0a 18 69 e4'),
                          ('5c 00 a1 01','5c 00 92 3b')):
        ew = sub(ew, before, after)
    ew = sub(ew, 'c2 20 a9 ab b4 8f f0 3f 41',
                  'c2 20 af 04 f0 43 8f 06 f0 43 a9 ab b4 8f f0 3f 41')
    if ew[-3]!=0x4c:raise ValueError('LIVE_MIX_FINAL_STOP')
    ew = ew[:-3]+bytes.fromhex('5c 00 93 3b')
    def exchange(c, src, size):
        c.emit('e2 20 a9 00 48 ab a9 80 8d 30 22 a9 20 8d 0b 22 c2 20')
        c.word(0xa9,src); c.emit('8d 32 22 e2 20 a9 3b 8d 34 22 c2 20')
        c.word(0xa9,size); c.emit('8d 38 22 a9 00 35 8d 35 22 5c 00 35 00')
    encode=Code(0x9000); exchange(encode,0x8800,len(ew))
    gate=Code(0x9200); gate.emit('c2 30 af 04 f0 43 8f 06 f0 43')
    gate.label('wait'); gate.emit('af 04 f0 43 cf 08 f0 43'); gate.branch(0xb0,'wait')
    exchange(gate,0x8000,len(gw))
    stop=Code(0x9300); stop.label('stop'); stop.jump('stop')
    def transform(raw,sy):
        audio_transform(raw,sy)
        if any(raw[0x210000:0x3f0000]):raise ValueError('LIVE_MIX_ROM_TABLE_RESERVATION')
        raw[0x210000:0x3f0000]=producer[0x10000:0x1f0000]
        # The expected static BRR bytes installed by configure are replaced
        # by actual source PCM; transport will read native BW-RAM instead.
        raw[0x200000:0x210000]=producer[0x200000:0x210000]
        raw[0x3f0000:0x400000]=producer[0x210000:0x220000]
        raw[0x20f090:0x20f098]=struct.pack('<II',0xe0,0xff)
        for at,data in ((0x1d8000,gw),(0x1d8800,ew),
                        (0x1d9000,encode.finish()),(0x1d9200,gate.finish()),
                        (0x1d9300,stop.finish())):
            if any(raw[at:at+len(data)]):raise ValueError('LIVE_MIX_WORKER_ROM_RESERVATION')
            raw[at:at+len(data)]=data
        at=offset(sy['Core_Nmi_WaitFrame'])
        assert raw[at:at+4]==b'\x5c'+sy['Tad_StreamWaitFrame'].to_bytes(3,'little')
        raw[at+1:at+4]=sy['LiveMixWait'].to_bytes(3,'little')
        needle=b'\x22'+sy['SourceAudio_FillHdmaRows'].to_bytes(3,'little')
        assert raw.count(needle)==1
        at=raw.index(needle); raw[at+1:at+4]=sy['LiveMixReadGuard'].to_bytes(3,'little')
    def before(m,sy):
        audio_before(m,sy); m.write_u16(REQUEST+6,0)
        for name in ('SourceVMRun4086_Ready','SourceVMRun4086_Busy','VmSourceFrame_Pending'):
            m.write_u16(sy[name],0)
        m.write_u16(sy['Game_State'],3)
        if a.force_incoming_conversion:
            # Explicit inherited-register stress input. Both CPU register
            # domains are used; S-CPU cannot write SA-1-only DCNT ($2230).
            m.write_memory('SnesMemory',0x2200,'60')
            m.write_memory('SnesMemory',0x2201,'00')
            m.write_memory('Sa1Memory',0x2230,'b0')
            m.write_memory('Sa1Memory',0x2231,'02')
            m.write_memory('Sa1Memory',0x2232,'000042')
            m.write_memory('Sa1Memory',0x2235,'003200')
    def closeout(m,sy,completed):
        diagnostic=dict(SCPU=m.get_cpu_state('Snes'),SA1=m.get_cpu_state('Sa1'),registers=m.read_memory('SnesMemory',0x2200,0x40).hex(),control=m.read_memory('SnesMemory',0x43f000,16).hex(),IRAM=m.read_memory('SnesMemory',0x003500,48).hex(),SCPU_trace=m.trace_log(16),SA1_trace=m.trace_log(16,'Sa1'))
        (out/'dispatch-diagnostic.json').write_text(json.dumps(diagnostic,indent=2)+'\n')
        audio_closeout(m,sy,completed)
        actual=m.read_memory('SnesMemory',0x430000,len(expected))
        (out/'native-live.brr').write_bytes(actual)
        control=dict(jobs=int.from_bytes(m.read_memory('SnesMemory',0x43f002,2),'little'),
                     ready_bytes=int.from_bytes(m.read_memory('SnesMemory',0x43f006,2),'little'),
                     premature_packet_waits=int.from_bytes(m.read_memory('SnesMemory',0x7fbfe0,2),'little'),
                     phase=m.read_memory('SnesMemory',0x435000,8).hex(),
                     active=m.read_memory('SnesMemory',0x435100,8).hex(),
                     clipping_guard=m.read_memory('SnesMemory',0x413ff2,2).hex())
        (out/'live-control.json').write_text(json.dumps(control,indent=2)+'\n')
    lua=r'''
local liveStart=nil;local lateJobs=0;local samples={};local unsafeReads=0;local waitLogged=false
local function word(a)return emu.read(a,emu.memType.snesMemory)+256*emu.read(a+1,emu.memType.snesMemory)end
emu.addMemoryCallback(function()liveStart=emu.getState().masterClock;emu.log('LIVEMIX|start|'..liveStart..'|'..word(0x43f002))end,emu.callbackType.exec,LIVESTART,LIVESTART,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function()if liveStart then lateJobs=lateJobs+1 end;emu.log('LIVEMIX|job|'..emu.getState().masterClock..'|'..word(0x43f002))end,emu.callbackType.exec,0x3b9200,0x3b9200,emu.cpuType.sa1,emu.memType.sa1Memory)
emu.addMemoryCallback(function()local x=emu.getState()['cpu.x'];local required=math.min(x+144,10692);local ready=word(0x43f006);if ready<required then unsafeReads=unsafeReads+1 end;emu.log('LIVEMIX|packet|'..emu.getState().masterClock..'|'..x..'|'..ready)end,emu.callbackType.exec,FILLENTRY,FILLENTRY,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function()if not waitLogged then waitLogged=true;emu.log('LIVEMIX|wait|'..emu.getState().masterClock)end end,emu.callbackType.exec,READWAIT,READWAIT,emu.cpuType.snes,emu.memType.snesMemory)
'''
    observer=(a.producer/'observer.lua').read_text()
    points={name:int(re.search(r'ENDBRR\|'+name+r'\|.*?exec,(\d+)',observer).group(1))for name in ('gather_entry','encode_entry','encode_done')}
    for name,address in points.items():
        capture="local bytes={};for j=0,351 do bytes[#bytes+1]=string.format('%02x',emu.read(0x420000+j,emu.memType.snesMemory))end;emu.log('LIVEPCM|'..table.concat(bytes))"if name=='encode_entry'else''
        # Shared IRAM entry addresses can also be crossed by the other kernel.
        selector=224 if name=='gather_entry'else 0
        lua+=f"emu.addMemoryCallback(function()if emu.read(0x350a,emu.memType.sa1Memory)=={selector} then emu.log('LIVECOST|{name}|'..emu.getState().masterClock);{capture} end end,emu.callbackType.exec,{address},{address},emu.cpuType.sa1,emu.memType.sa1Memory)\n"
    asm=ASM.replace('lda #1188','lda #'+str(a.startup_jobs*99)).replace('cmp #1188','cmp #'+str(a.startup_jobs*99))
    for key,value in dict(PADDEDBYTES=math.ceil(len(expected)/144)*144,WORKERBYTES=(len(gw)+1)&~1,BRRBYTES=len(expected),CHUNKS=math.ceil(len(expected)/144)).items():
        asm=re.sub(r'\b'+key+r'\b',str(value),asm)
    bindings=dict(REALWAIT='Tad_StreamWaitFrame',SOURCECURSOR='TadPrivate_stream_source_offset',
                  SOURCEBASE='SourceAudio_BaseLo',SOURCELENGTHHI='SourceAudio_LengthHi',
                  SOURCELENGTH='AudioStream_SourceLength',SOURCECHUNKS='AudioStream_SourceChunks',
                  SOURCEINDEX='SourceAudio_Index',SOURCESTATUS='SourceAudio_Status',
                  SOURCEBANK='SourceAudio_BaseBank',SOURCEID='AudioStream_SourceId',
                  STARTPREPARED='SourceAudio_StartPreparedNear',FILLROWS='SourceAudio_FillHdmaRows',
                  FILLENTRY='SourceAudio_FillHdmaRows')
    r=Reporter('M4-LIVE-SOURCE-MIX-SPC',kind='GATE')
    env=dict(MESEN_VOICE_CAPTURE_PATH=str(out/'voice0.raw'),MESEN_VOICE_CAPTURE_VOICE='0',MESEN_VOICE_CAPTURE_ARM_FILE=str(out/'voice0.raw.arm'))
    raw,log=run_fixture(a.rom,out,[dict(source_mixed_jobs=108)],'LiveMixFixture','SourceAudio_Status',0xb4ad,[],lua,r,append=asm,bindings=bindings,probes=dict(LIVESTART='LiveMixStart',READWAIT='LiveMixReadWait'),batch_size=1,frame_limit=200,rom_transform=transform,before_start=before,closeout=closeout,emulator_env=env,link_pcm=False)
    try:proof=verify(out,assets,require_dsp_trace=True)
    except AssertionError as error:
        trace=json.loads((out/'audio-stream-trace.json').read_text())
        active=[v for v in trace['observations']if v['voice0']['envelope']]
        dsp=json.loads((out/'voice0.raw.json').read_text())if(out/'voice0.raw.json').exists()else None
        proof=dict(status='FAIL',verification_error=str(error),received_packets=len(trace['received_chunks']),observed_active_fields=len(active),expected_source_frames=108*176,effective_rate_hz=32000*1411/4096,DSP_capture_metadata=dsp)
    control=json.loads((out/'live-control.json').read_text())
    events=[l.split('LIVEMIX|')[1].split('|')for l in log.splitlines()if'LIVEMIX|'in l]
    starts=[v for v in events if v[0]=='start']; packets=[v for v in events if v[0]=='packet']
    late=[v for v in events if v[0]=='job' and starts and int(v[1])>int(starts[0][1])]
    pcm=b''.join(bytes.fromhex(l.split('LIVEPCM|')[1])for l in log.splitlines()if'LIVEPCM|'in l)
    costs=[l.split('LIVECOST|')[1].split('|')for l in log.splitlines()if'LIVECOST|'in l]
    cost_trace=[v[0]for v in costs]==['gather_entry','encode_entry','encode_done']*108
    job_costs=[int(costs[i+2][1])-int(costs[i][1])for i in range(0,len(costs),3)]if cost_trace else []
    r.check('native producer completes after live SPC admission',len(starts)==1 and int(starts[0][2])<108 and len(late)>0 and control['jobs']==108)
    r.check('every meaningful packet is ready before production driver reads it',len(packets)==75 and all(int(v[3])>=min(int(v[2])+144,len(expected))for v in packets))
    r.check('native produced stream matches completed source codec authority',(out/'native-live.brr').read_bytes()==expected)
    r.check('every live mixed PCM sample matches pinned source authority',len(pcm)==108*176*2 and hashlib.sha256(pcm).hexdigest()==pr['PCM_sha256'])
    r.check('bounded worker timing trace covers every live job',cost_trace)
    r.check('no premature packet wait or clipping fault',control['premature_packet_waits']==0 and control['clipping_guard']=='0000')
    r.check('final phase and active source state match authority',bytes.fromhex(control['phase'])==struct.pack('<2I',*pr['expected_phases'])and bytes.fromhex(control['active'])==struct.pack('<2I',*pr['expected_active']))
    r.check('production SPC consumes the complete source mixture',proof['status']=='PASS')
    result=dict(schema='BYOR_LIVE_SOURCE_MIX_SPC_NATIVE_V1',status='PASS'if all(ok for _,ok in r.results)else'FAIL',checks=r.results,proof=proof,control=control,start=starts,late_native_jobs=len(late),packet_count=len(packets),ROM_sha256=hashlib.sha256(raw).hexdigest(),producer_report_sha256=hashlib.sha256((a.producer/'report.json').read_bytes()).hexdigest(),source_identities=pr['source_identities'],native_mixing_during_live_transport=True,production_driver_override=False,private_readiness_guard=True,private_paused_memory_owner=True,source_event_admission_bound=False,production_memory_lease=False,joint_graphics_bound=False,complete_backend_admitted=False,motu_gameplay_proven=False,no_color_reduction=True,no_PCM_files_copied=True)
    result.update(PCM_observed_bytes=len(pcm),PCM_sha256=hashlib.sha256(pcm).hexdigest(),peak_job_master_clocks=max(job_costs)if job_costs else None,job_master_clocks=job_costs)
    result.pop('production_driver_override')
    result.update(production_SPC_driver_override=False,host_transport_read_wrapper_installed=True,native_mixing_during_live_transport=result['status']=='PASS',startup_jobs=a.startup_jobs,SPC_prefill=not a.no_prefill)
    result['prefill_chunks']=0 if a.no_prefill else a.prefill_chunks
    result['forced_incoming_type1_conversion']=a.force_incoming_conversion
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],'late jobs',len(late),'packets',len(packets),'waits',control['premature_packet_waits'])
    if result['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
