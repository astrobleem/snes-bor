"""Private B4EP sound9 -> real TAD stream proof, with source-derived payload.

Uses ASAD namespace descriptors when supplied; otherwise replaces one reserved
stream asset in the private ROM. Neither mode registers a foreign profile or
a production sound owner.
"""
import hashlib,json,math,struct
from pathlib import Path
from m4_input_controller_native import offset
from _harness import run_frames_exact

SERVICE=r'''
 jsl EFFECTRUN
 bcs ScriptedProjectileFixtureBad
 cmp #9
 bne ScriptedProjectileFixtureBad
 lda.l FRAMEDATA
 tax
 lda.l $3A0010,x
 cmp #SOUNDINDEX
 bne ScriptedProjectileFixtureBad
 lda.l $3A0012,x
 bne ScriptedProjectileFixtureBad
 phd
 phb
 lda #0
 tcd
 sep #$20
.a8
 pha
 plb
 lda #1
 sta.l STREAMSOURCE
 jsl ScriptedProjectileAudioNear
 rep #$30
.a16
.i16
 plb
 pld
ScriptedProjectileAfterAudio:
.a16
.i16
 nop
 lda #9
 sta.l SOUNDTICKET
 jsl SOUNDACK
 bcs ScriptedProjectileFixtureBad
 jsl EFFECTRUN
 bcs ScriptedProjectileFixtureBad
 cmp #0
 bne ScriptedProjectileFixtureBad
 jsl TIMEDCONTINUE
 bcs ScriptedProjectileFixtureBad
'''

NEAR=r'''
ScriptedProjectileAudioNear:
.a8
.i16
 pea NEARRELAY
 lda #NEARBANK
 pha
 pea NEARTARGET
 rtl
'''

IDLE=r'''
ScriptedProjectileAudioIdleWait:
.a16
.i16
 rep #$31
 php
 phb
 phd
 phx
 phy
 lda.l WAITCOUNTER
 pha
 cld
 lda #0
 tcd
 sep #$20
.a8
 pha
 plb
 rep #$30
.a16
.i16
ScriptedProjectileAudioIdleLoop:
.a16
.i16
 lda 1,s
 cmp.l WAITCOUNTER
 bne ScriptedProjectileAudioIdleDone
 sep #$20
.a8
 lda.l STREAMENABLE
 beq ScriptedProjectileAudioIdleNoPump
 lda.l STREAMACTIVE
 beq ScriptedProjectileAudioIdleNoPump
 jsl TADLATE
ScriptedProjectileAudioIdleNoPump:
.a8
.i16
 rep #$30
.a16
.i16
 bra ScriptedProjectileAudioIdleLoop
ScriptedProjectileAudioIdleDone:
.a16
.i16
 pla
 ply
 plx
 pld
 plb
 plp
 cmp.l WAITCOUNTER
 jml WAITRETURN
'''

ARM_GUARD=r'''
ScriptedProjectileAudioArmGuard:
.a8
.i16
 lda.l ARMPHASE
 cmp #1
 bne ScriptedProjectileAudioArmGuardDone
 jml ARMREAL
ScriptedProjectileAudioArmGuardDone:
.a8
.i16
 rtl
'''

def configure(folder,source_audio,sound_path,isolate=False,idle_pump=False,spc_driver=None,prefill=False,arm_guard=False,generic_rom=None,external_observer=None,prefill_chunks=None):
    r=json.loads((source_audio/'report.json').read_text())
    row=next(x for x in r['compiled']if x['source_path'].lower()==sound_path.lower())
    assert row['normalized_sample_rate']==11025 and (generic_rom or row['brr_bytes']<=32768)
    payload=(source_audio/row['brr_path']).read_bytes()
    assert hashlib.sha256(payload).hexdigest()==row['brr_sha256']
    prefill_target=min(7,max(0,math.ceil(len(payload)/144)-1))
    if prefill_chunks is not None:
        if not prefill or not isinstance(prefill_chunks,int)or not 1<=prefill_chunks<=7:raise ValueError('SOURCE_AUDIO_PREFILL_CHUNK_DOMAIN')
        prefill_target=min(prefill_target,prefill_chunks)
    observations=[];received=[]
    def transform(raw,sy):
        # Candidate linking relocates stream assets; main.sym's legacy data
        # symbol can alias live bank13 code. Never replace that nominal bank.
        # Use the verified empty tail of the fixture's reserved bank60, then
        # patch only this private ROM's real long-read operand.
        if generic_rom:
            from source_frame_audio_rom import install
            manifest=json.loads((generic_rom/'report.json').read_text())
            assert manifest['source_frame_table_sha256']==r['source_frame_table_sha256']
            assert manifest['namespace']==r['namespace']
            table=(generic_rom/'descriptors.bin').read_bytes();data=(generic_rom/'payload.bin').read_bytes()
            assert hashlib.sha256(table).hexdigest()==manifest['descriptor_sha256']
            assert hashlib.sha256(data).hexdigest()==manifest['payload_sha256']
            install(raw,table,data,offset(sy['SourceAudio_Table']),cpu_base=manifest['cpu_window_base'])
        else:
            assert len(payload)<=16384 and len(payload)%9==0
            at=60*32768+16384
            padded_length=math.ceil(len(payload)/144)*144
            assert raw[at:at+padded_length]==bytes(padded_length)
            raw[at:at+len(payload)]=payload
            instruction=offset(sy['Tad_StreamReadSourceByte__source1'])
            assert raw[instruction]==0xbf
            raw[instruction+1:instruction+4]=bytes.fromhex('00 c0 3c')
            for name,value in [('AudioStream_SourceLengthTable',len(payload)),('AudioStream_SourceChunkTable',math.ceil(len(payload)/144))]:
                at=offset(sy[name])+2;raw[at:at+2]=struct.pack('<H',value)
        assert raw[offset(sy['Tad_ProcessMaybeStream__return'])]==0x6b
        if spc_driver:
            driver=spc_driver.read_bytes();start=60*32768+24832
            assert generic_rom or at+padded_length<=start
            assert len(driver)<=7936 and raw[start:start+len(driver)]==bytes(len(driver))
            raw[start:start+len(driver)]=driver
            pointer=sy['Tad_AudioDriver_Bin'];size=sy['Tad_AudioDriver_SIZE']
            needle=bytes([0xa9,pointer>>16,0xa2,pointer&255,(pointer>>8)&255,0xa0,size&255,size>>8])
            assert raw.count(needle)==1
            at=raw.index(needle);raw[at:at+8]=bytes([0xa9,60,0xa2,0,0xe1,0xa0,len(driver)&255,len(driver)>>8])
        if idle_pump:
            entry=offset(sy['Core_Nmi_WaitFrame']);end=offset(sy['Core_Nmi_WaitFrame__loop'])+6
            assert raw[entry:entry+3]==bytes.fromhex('c2 31 af')and raw[end]==0x60
            raw[entry:entry+4]=bytes([0x5c])+sy['ScriptedProjectileAudioIdleWait'].to_bytes(3,'little')
        if arm_guard:
            at=offset(sy['Tad_StreamServiceFootdie__pending'])+6
            assert raw[at:at+4]==bytes([0x22])+sy['Tad_StreamArmFootdieFrame'].to_bytes(3,'little')
            raw[at+1:at+4]=sy['ScriptedProjectileAudioArmGuard'].to_bytes(3,'little')
    def before(m,sy):
        # Isolate voice0 from MSU music in this bounded audio observer.
        m.write_memory('SnesMemory',0x2007,'00')
        for name,value in [('AudioStream_Enable',1),('AudioStream_TransportOnly',2 if prefill and prefill_target else 0),('AudioStream_SerialPermit',1),('AudioSemantic_FootDieStreamActive',0)]:m.write_memory('SnesMemory',sy[name],f'{value:02x}')
        m.write_u16(sy['AudioSemantic_FootDieStreamFrame'],0xffff)
        (folder/'voice0.raw.arm').touch()
        m.record_audio(folder/'source-energy.wav')
    def observe(m,sy):
        b=m.read_memory('SnesMemory',sy['TadPrivate_stream_frame'],64)
        def word(name):
            at=sy[name]-sy['TadPrivate_stream_frame'];return int.from_bytes(b[at:at+2],'little')
        nmi=m.read_memory('SnesMemory',sy['Nmi_HdmaEnable'],32)
        audio=m.get_audio_state();voice=next(v for v in audio['voices']if v['voice']==0)
        high=m.read_memory('SnesMemory',sy['SourceAudio_OffsetHi'],32)if generic_rom else bytes(32)
        observations.append(dict(field=len(observations),transport=b.hex(),chunks_accepted=word('TadPrivate_stream_chunks_accepted'),chunks_expected=word('AudioStream_SourceChunks'),consumer_chunk=word('TadPrivate_stream_consumer_chunk'),source_offset=word('TadPrivate_stream_source_offset')+(int.from_bytes(high[:2],'little')<<16),producer_done=b[sy['TadPrivate_stream_producer_done']-sy['TadPrivate_stream_frame']],nmi=nmi.hex(),voice0=voice))
        previous=observations[-2]['chunks_accepted']if len(observations)>1 else 0
        current=observations[-1]['chunks_accepted']
        for chunk in range(previous,current):
            slot=chunk%8;aram=sy['TAD_STREAM_RING_ADDR']+slot*144
            actual=m.read_memory('SpcRam',aram,144)
            expected=bytearray(payload[chunk*144:(chunk+1)*144].ljust(144,b'\0'))
            if slot==7 and(chunk+1)*144<len(payload):expected[135]|=3
            meaningful=min(144,len(payload)-chunk*144)
            received.append(dict(chunk=chunk,field=len(observations)-1,aram=aram,sha256=hashlib.sha256(actual).hexdigest(),expected_sha256=hashlib.sha256(expected).hexdigest(),mismatched_bytes=sum(a!=b for a,b in zip(actual,expected)),meaningful_bytes=meaningful,meaningful_mismatched_bytes=sum(a!=b for a,b in zip(actual[:meaningful],expected[:meaningful])),padding_mismatched_bytes=sum(a!=b for a,b in zip(actual[meaningful:],expected[meaningful:])),observer_gap=current-previous))
    if external_observer is not None:external_observer['sample']=observe
    def closeout(m,sy,completed):
        if generic_rom:
            diagnostic={name:m.read_memory('SnesMemory',sy[name],32).hex()for name in ('SourceAudio_Status','SourceAudio_BaseLo','SourceAudio_Table','AudioSemantic_FootDieStreamActive')}
            (folder/'audio-admission.json').write_text(json.dumps(diagnostic,indent=2)+'\n')
        if completed and external_observer is None:
            if isolate:m.write_u16(sy['Game_State'],3)
            done_field=None
            limit=max(400,math.ceil(row['normalized_frames']/(32000*1411/4096)*60.1)+100)
            assert limit<=2000
            for i in range(limit):
                if prefill:
                    control=m.read_memory('SnesMemory',sy['TadPrivate_stream_frame'],64)
                    accepted=int.from_bytes(control[sy['TadPrivate_stream_chunks_accepted']-sy['TadPrivate_stream_frame']:][:2],'little')
                    pending=control[sy['TadPrivate_stream_pending']-sy['TadPrivate_stream_frame']]
                    # Permit only an idle producer. Regranting while a chunk
                    # is in flight can prefill an eighth chunk before mode
                    # switches, then overwrite the head on the first KON.
                    if not pending:
                        if accepted<prefill_target:m.write_memory('SnesMemory',sy['AudioStream_SerialPermit'],'01')
                        else:m.write_memory('SnesMemory',sy['AudioStream_TransportOnly'],'00')
                run_frames_exact(m,1)
                observe(m,sy)
                if observations[-1]['producer_done']and observations[-1]['chunks_accepted']>=observations[-1]['chunks_expected']:
                    if done_field is None:done_field=i
                    if i-done_field>=16:break
        m.stop_audio()
        (folder/'audio-fingerprint.json').write_text(json.dumps(m.audio_fingerprint(folder/'source-energy.wav'),indent=2)+'\n')
        (folder/'audio-state.json').write_text(json.dumps(m.get_audio_state(),indent=2,default=lambda x:x.hex()if isinstance(x,bytes)else str(x))+'\n')
        (folder/'audio-stream-trace.json').write_text(json.dumps(dict(source_binding_instrumented=True,generic_asad_namespace=bool(generic_rom),legacy_gameplay_paused=isolate,idle_wait_audio_pump=idle_pump,initial_seven_chunk_prefill=prefill and prefill_target==7,prefill_chunks=prefill_target if prefill else 0,already_armed_table_guard=arm_guard,spc_driver_sha256=hashlib.sha256(spc_driver.read_bytes()).hexdigest()if spc_driver else None,source=row,received_chunks=received,observations=observations),indent=2)+'\n')
    return row,transform,before,closeout

BINDINGS=dict(FRAMEDATA='SourceUpdateFrame4086_FrameData',STREAMSOURCE='AudioStream_SourceId',SOUNDTICKET='SourceFrameEffectPlan4086_Acknowledged',SOUNDACK='SourceFrameEffectPlan4086_Ack',STREAMREQUESTS='AudioSemantic_StreamRequestCount',STREAMCHUNKS='AudioStream_SourceChunks',STREAMLENGTH='AudioStream_SourceLength',NMISKIPPED='Core_Nmi_Play__frame_skipped',NMICOMMIT='Core_Nmi_Play__do_commit',NMIHARDWAREFRAME='Nmi_FrameCounter')
IDLE_BINDINGS=dict(WAITCOUNTER='Nmi_FrameCounter',STREAMENABLE='AudioStream_Enable',STREAMACTIVE='AudioSemantic_FootDieStreamActive',TADLATE='Tad_StreamLatePump')
ARM_BINDINGS=dict(ARMPHASE='TadPrivate_stream_arm_phase',ARMREAL='Tad_StreamArmFootdieFrame')

WAIT_CONTEXT_BINDINGS=dict(WAITENTRY='Tad_StreamWaitFrame',WAITEXIT='Core_Nmi_WaitFrame__return',WAITFRAME='Nmi_FrameCounter')
WAIT_CONTEXT_OBSERVER=r'''
local waitcpu=nil
emu.addMemoryCallback(function()
 if not sourceaudioactive then return end
 local st=emu.getState();waitcpu={counter=word(WAITFRAME)}
 for _,k in ipairs({'x','y','d','dbr','sp','ps'})do waitcpu[k]=st['cpu.'..k]end
end,emu.callbackType.exec,WAITENTRY,WAITENTRY,emu.cpuType.snes,mt)
emu.addMemoryCallback(function()
 if not waitcpu then return end
 local st=emu.getState();local faults=0
 for _,k in ipairs({'x','y','d','dbr','sp'})do if waitcpu[k]~=st['cpu.'..k]then faults=faults+1 end end
 local now=word(WAITFRAME);local diff=(waitcpu.counter-now)&65535
 local flags=(waitcpu.counter>=now and 1 or 0)|(diff==0 and 2 or 0)|((diff&32768)~=0 and 128 or 0)
 if (st['cpu.ps']&179)~=flags or (st['cpu.ps']&76)~=(waitcpu.ps&76)then faults=faults+1 end
 if st['cpu.a']~=waitcpu.counter or now==waitcpu.counter then faults=faults+1 end
 emu.log('SOURCEAUDIOWAITCTX|'..now..'|'..faults);waitcpu=nil
end,emu.callbackType.exec,WAITEXIT,WAITEXIT,emu.cpuType.snes,mt)
'''

OBSERVER=r'''
local sourceaudioactive=false
emu.addMemoryCallback(function()
 sourceaudioactive=true
 emu.log('SOURCEAUDIOREQUEST|'..word(STREAMREQUESTS)..'|'..word(STREAMLENGTH)..'|'..word(STREAMCHUNKS))
end,emu.callbackType.exec,AFTERAUDIO,AFTERAUDIO,emu.cpuType.snes,mt)
for _,entry in ipairs({{NMISKIPPED,1},{NMICOMMIT,0}})do
 local skipped=entry[2]
 emu.addMemoryCallback(function()if sourceaudioactive then emu.log('SOURCEAUDIONMI|'..word(NMIHARDWAREFRAME)..'|'..skipped)end end,emu.callbackType.exec,entry[1],entry[1],emu.cpuType.snes,mt)
end
'''
