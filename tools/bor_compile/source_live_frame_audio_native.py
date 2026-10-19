"""Captured source SOUND admission to the existing prepared TAD stream.

This private capability admits one active source voice at a time. A request
requiring another voice remains pending before logical or physical mutation.
The compiler supplies a waveform mixed by the pinned C source, including its
original sample phase, then resampled for the existing physical stream rate.
It is not a general twelve-voice mixer or a replacement source sound selector.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct

TRANSPORT = 0x7E8100
CONTROL = 0x7E8120
CHANNELS = 0x7E8140
REQUEST = 0x7E8320
END = 0x7E8340
TABLE = 0x33A000
ROW_BYTES = 32
MAGIC = 0xB6D9


def prepare(source, assets, *, cpu_base=0xF50000):
    """Validate one offline C-mixed source asset and build sparse ROM inputs."""
    from source_single_voice_audio import parse_pcm_wav, PINNED_SOUNDMIX_SHA256
    from source_frame_effects_4086 import derive, pack, unpack
    sha=lambda b:hashlib.sha256(b).hexdigest()
    assets=Path(assets)
    report=json.loads((assets/'report.json').read_text())
    # Frame SOUND indices are the immutable B4FE media-prefix indices. Global
    # and model sound namespaces outside captured frame events are separate
    # providers, and are not silently admitted by this capability.
    namespace=unpack(pack(derive(source)))['media']
    identity=report['source_identity'];index=identity['sample_index']
    if (report['status']!='PASS' or not 0<=index<len(namespace)
            or identity['source_path'].lower()!=namespace[index].lower()
            or report['pinned_source_inputs']['soundmix_bytes_sha256']!=PINNED_SOUNDMIX_SHA256):
        raise ValueError('LIVE_AUDIO_SOURCE_AUTHORITY')
    raw=source.read(namespace[index]);wav=parse_pcm_wav(raw)
    if sha(raw)!=identity['source_wav_sha256']:
        raise ValueError('LIVE_AUDIO_SOURCE_ASSET_IDENTITY')
    cache=report['original_cache_metadata']
    for name in ['channels','sample_width_bytes','bits','sample_rate_hz','frames']:
        if cache[name]!=wav[name]:raise ValueError('LIVE_AUDIO_ORIGINAL_CACHE_'+name)
    call=report['source_call'];channel=report['source_channel'];initial=channel['initial']
    volume=call['raw_left_volume']
    if (call['raw_right_volume']!=volume or not 0<=volume<=65535 or call['priority']!=0
            or call['speed']!=100 or initial['left']!=min(volume,64)
            or initial['right']!=min(volume,64) or channel['selected']!=11
            or channel['play_id']!=1 or initial['phase_q12']!=((44%wav['frames'])<<12)
            or channel['mix_output_rate_hz']!=44100 or initial['period_q12']!=wav['sample_rate_hz']*4096//44100
            or channel['final']['active']!=0):
        raise ValueError('LIVE_AUDIO_SOURCE_CHANNEL_PROFILE')
    mapping=report['phase_time_mapping']
    if (mapping['prepared_stream_rate_hz']!=11025
            or not mapping['phase_is_baked_into_full_mixed_waveform']
            or mapping['leading_44_normalized_frame_trim_applied']):
        raise ValueError('LIVE_AUDIO_SOURCE_PHASE_MAPPING')
    brr=(assets/'prepared.brr').read_bytes()
    if (sha(brr)!=report['prepared_brr']['sha256'] or len(brr)!=report['prepared_brr']['bytes']
            or not brr or len(brr)%9 or any(brr[i]&3 for i in range(0,len(brr)-9,9))
            or brr[-9]&3!=1 or not 0xE00000<=cpu_base<0x1000000):
        raise ValueError('LIVE_AUDIO_PREPARED_BRR')
    chunks=(len(brr)+143)//144
    payload=brr+bytes(chunks*144-len(brr))
    if cpu_base+len(payload)>0x1000000 or chunks>65535:
        raise ValueError('LIVE_AUDIO_ROM_CAPACITY')
    table=bytearray(struct.pack('<4s4H',b'LVA1',1,len(namespace),ROW_BYTES,volume))
    table.extend(bytes(len(namespace)*ROW_BYTES))
    row=struct.pack('<5I',wav['frames'],wav['sample_rate_hz'],initial['period_q12'],
                    initial['phase_q12'],channel['final']['phase_q12'])
    row+=cpu_base.to_bytes(3,'little')+b'\x01'
    row+=len(brr).to_bytes(3,'little')+b'\x00'
    row+=struct.pack('<HBB',chunks,wav['bits'],wav['channels'])
    assert len(row)==ROW_BYTES
    table[12+index*ROW_BYTES:12+(index+1)*ROW_BYTES]=row
    config=dict(samples=len(namespace),compiled_indices=[index],table_cpu=TABLE,
                payload_cpu=cpu_base,payload_bytes=len(payload),payload_sha256=sha(payload),
                table_sha256=sha(table),asset_report_sha256=sha((assets/'report.json').read_bytes()),
                source_wav_sha256=sha(raw),source_call=call,initial_channel=initial,
                final_channel=channel['final'],physical_rate=11025,
                source_mix_rate=44100,polyphony_bound=False,
                required_pending_before_mutation='any active source voice or physical backend')
    return bytes(table),payload,config


def emit(sy, *, table=TABLE, samples=30):
    """Return C=1 fault, A=1 pending, A=0 actual physical admission.

    Installer owns the retired-video range through END, initial channel state,
    current source setting, immutable source-derived rows and IRQ installation.
    Rows are 32 bytes: original sample length/frequency/period/initial phase/
    final phase (five DWORDs), BRR pointer24+flags8, BRR bytes24+reserved8,
    transport chunk count16, source bits8/channels8. Flags bit0 admits the row.
    The header is LVA1, version1, count16, stride32, raw effect volume16.
    """
    from source_sound_admission_native import emit as admission
    if (not 1 <= samples <= 1023 or not 0 <= table <= 0xFFFFFF-12-samples*ROW_BYTES
            or (table & 65535) < 0x8000 or (table & 65535)+12+samples*ROW_BYTES > 0x10000):
        raise ValueError('LIVE_FRAME_AUDIO_TABLE_DOMAIN')
    code=[];serial=0
    def put(text):code.extend(text.strip().splitlines())
    def label(name):put('LiveFrameAudio_'+name+':\n.a16\n.i16')
    def branch(op,target='Fault'):
        nonlocal serial
        serial+=1;guard='LiveFrameAudio_Branch'+str(serial)
        put(f' '+{'bne':'beq','beq':'bne','bcc':'bcs','bcs':'bcc'}[op]+f' {guard}\n jmp LiveFrameAudio_{target}\n{guard}:\n.a16\n.i16')
    def require(address,value):put(f' lda.l {address}\n cmp #{value}');branch('bne')
    def copy(source,target):put(f' lda.l {source}\n sta.l {target}')
    def store(address,value):put(f' lda #{value}\n sta.l {address}')

    label('Admit');put(' php\n rep #$39\n phx\n phy\n phb\n phd')
    put(f' jsl {sy["SourceForeignWork_Check"]}');branch('bcs')
    require(CONTROL,MAGIC)
    # Validate the actual captured frame/effect transaction before touching
    # admission state. Never infer a sound from the actor's current animation.
    for name,value in [('SourceUpdateFrame4086_Ready',0xB4E3),
                       ('SourceUpdateFrame4086_State',1),
                       ('SourceUpdateFrame4086_Pending',2),
                       ('SourceFrameEffectPlan4086_Ready',0xB4F2),
                       ('SourceFrameEffectPlan4086_State',1),
                       ('SourceFrameEffectPlan4086_Service',9),
                       ('SourceFrameEffectPlan4086_Acknowledged',0)]:
        require(sy[name],value)
    for frame,plan in [('Slot','Slot'),('Handle','Handle'),('Request','Frame')]:
        put(f' lda.l {sy["SourceUpdateFrame4086_"+frame]}\n cmp.l {sy["SourceFrameEffectPlan4086_"+plan]}');branch('bne')
    put(f' lda.l {sy["SourceUpdateFrame4086_FrameData"]}\n cmp #$8000');branch('bcc')
    put(' clc\n adc #24');branch('bcs')
    put(f' cmp.l {sy["SourceUpdateFrame4086_TableEnd"]}');branch('bcc','FrameBounds');branch('bne')
    label('FrameBounds')
    put(f' lda.l {sy["SourceUpdateFrame4086_Bank"]}\n cmp #64');branch('bcs')
    put(' sep #$20\n.a8')
    put(f' lda.l {sy["SourceUpdateFrame4086_Bank"]}\n pha\n plb\n rep #$20\n.a16')
    put(f' lda.l {sy["SourceUpdateFrame4086_FrameData"]}\n clc\n adc #16\n tax\n lda.w $0002,x');branch('bne')
    put(' lda.w $0000,x\n cmp #'+str(samples));branch('bcs')
    put(f' sta.l {CONTROL}+16\n asl a\n asl a\n asl a\n asl a\n asl a\n sta.l {CONTROL}+18\n tax')
    require(table,0x564C);require(table+2,0x3141);require(table+4,1)
    require(table+6,samples);require(table+8,ROW_BYTES)
    # Sparse compiler rows remain unsupported before channel writes.
    put(f' lda.l {table+12}+22,x\n and #$FF00');branch('beq','Pending')
    put(' cmp #$0100');branch('bne')
    # An already admitted identical ticket is an idempotent replay, not a new
    # source play. A different captured ticket must acquire an idle backend.
    put(f' lda.l {CONTROL}+2\n cmp #1');branch('bne','Fresh')
    for name,off in [('SourceUpdateFrame4086_Slot',4),('SourceUpdateFrame4086_Handle',6),
                     ('SourceUpdateFrame4086_Request',8),('SourceFrameEffectPlan4086_Index',10),
                     ('SourceForeignWork_Generation',12)]:
        put(f' lda.l {sy[name]}\n cmp.l {CONTROL}+{off}');branch('bne','Fresh')
    put(f' lda.l {sy["SourceForeignWork_Generation"]+2}\n cmp.l {CONTROL}+14');branch('bne','Fresh')
    put(' jmp LiveFrameAudio_Complete')
    label('Fresh')
    # Source supports polyphony. This physical capability does not: retain any
    # concurrent request until a mixer is bound, rather than dropping a voice.
    put(f' lda.l {sy["AudioSemantic_FootDieStreamActive"]}\n and #255');branch('bne','Pending')
    put(' ldx #0')
    label('IdleChannels')
    put(f' lda.l {CHANNELS},x\n ora.l {CHANNELS+2},x');branch('bne','Pending')
    put(' txa\n clc\n adc #40\n tax\n cpx #480');branch('bcc','IdleChannels')
    put(f' lda.l {CONTROL}+18\n tax')
    # The only installed gain capability is the compiler-verified source
    # default. A future mutable setting requires its matching waveform/mixer.
    put(f' lda.l {table+10}\n cmp.l {CONTROL}+28');branch('bne','Pending')
    put(f' lda.l {table+12}+30,x\n cmp #$0108');branch('beq','Mono')
    put(' cmp #$0110');branch('bne','Pending')
    label('Mono')
    # Bound the actual immutable source before any channel becomes active.
    put(f' lda.l {table+12}+22,x\n and #255\n cmp #$E0');branch('bcc')
    put(f' lda.l {table+12}+26,x\n and #$FF00');branch('bne')
    put(f' lda.l {table+12}+24,x\n ora.l {table+12}+26,x');branch('beq')
    put(f' lda.l {table+12}+28,x');branch('beq')
    put(f' lda.l {table+12},x\n sta.l {REQUEST}+8\n lda.l {table+14},x\n sta.l {REQUEST}+6')
    put(f' lda.l {table+20},x\n sta.l {REQUEST}+12\n lda.l {table+22},x\n sta.l {REQUEST}+14')
    # Initial and final source phases are immutable compiler authority, not a
    # PCM observer's override of the live logical channel.
    copy(CONTROL+16,REQUEST+4)
    copy(table+10,REQUEST+16);copy(table+10,REQUEST+20)
    store(REQUEST+18,0);store(REQUEST+22,0)
    store(REQUEST,0xB63B);store(REQUEST+2,0);store(REQUEST+30,0xB63C)
    store(sy['SourceSoundChannels4086_Priority'],0)
    store(sy['SourceSoundChannels4086_Priority']+2,0)
    # Fresh initialized source channels always offer highest free slot 11.
    # Native admission computes that decision and the original phase itself.
    put(f' lda.l {sy["SourceForeignWork_Generation"]}\n tax\n lda.l {sy["SourceForeignWork_Generation"]+2}\n tay\n jsl SoundAdmission_Run');branch('bcs')
    require(REQUEST+2,2);require(REQUEST+28,11)
    put(f' lda.l {CONTROL}+16\n asl a\n asl a\n asl a\n asl a\n asl a\n tax')
    for off,meta in [(32,12),(34,14)]:
        put(f' lda.l {CHANNELS+11*40+off}\n cmp.l {table+12+meta},x');branch('bne')
    # Pin an actual immutable BRR source into the existing prepared stream
    # owner. No ASAD table alias with the B4FE table is needed.
    put(f' lda.l {table+12+20},x\n sta.l {sy["SourceAudio_BaseLo"]}')
    put(f' lda.l {table+12+24},x\n sta.l {sy["AudioStream_SourceLength"]}')
    put(f' lda.l {table+12+26},x\n and #255\n sta.l {sy["SourceAudio_LengthHi"]}')
    put(f' lda.l {table+12+28},x\n sta.l {sy["AudioStream_SourceChunks"]}')
    put(f' lda.l {table+12+22},x\n and #255\n sta.l {sy["SourceAudio_BaseBank"]}')
    copy(CONTROL+16,sy['SourceAudio_Index'])
    # Every queued voice begins with the native producer's seven-packet
    # prefill protocol; no debugger grants or acknowledgement writes.
    put(' sep #$20\n.a8\n lda #2')
    put(f' sta.l {sy["AudioStream_TransportOnly"]}\n lda #1\n sta.l {sy["AudioStream_SerialPermit"]}')
    put(' sep #$20\n.a8\n lda #$FF')
    put(f' sta.l {sy["AudioStream_SourceId"]}\n jsl {sy["SourceAudio_StartPreparedNear"]}\n rep #$30\n.a16\n.i16')
    store(sy['SourceAudio_Status'],1)
    put(f' lda.l {sy["AudioSemantic_StreamRequestCount"]}\n inc a\n sta.l {sy["AudioSemantic_StreamRequestCount"]}')
    for name,off in [('SourceUpdateFrame4086_Slot',4),('SourceUpdateFrame4086_Handle',6),
                     ('SourceUpdateFrame4086_Request',8),('SourceFrameEffectPlan4086_Index',10),
                     ('SourceForeignWork_Generation',12)]:copy(sy[name],CONTROL+off)
    copy(sy['SourceForeignWork_Generation']+2,CONTROL+14)
    store(CONTROL+2,1)
    label('Complete');put(' lda #0\n jmp LiveFrameAudio_Return')
    label('Pending');put(' lda #1')
    label('Return');put(' pld\n plb\n ply\n plx\n plp\n clc\n rtl')
    label('Fault');put(' pld\n plb\n ply\n plx\n plp\n sec\n rtl')
    return '\n'.join(code)+'\n'+admission(REQUEST,CHANNELS,sy,samples=samples)
