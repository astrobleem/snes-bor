"""Retained logical source sound admission, with caller-owned backend state.

A production installer must supply the sample metadata and exclusive channel
lease. This emitter neither allocates RAM nor acknowledges a source frame.
"""

def emit(work,channels,sy,*,samples=30):
    if not 1<=samples<=32767 or not 0<=work<=0xffffff-32 or not 0<=channels<=0xffffff-480 or max(work,channels)<min(work+32,channels+480):
        raise ValueError('SOUND_ADMISSION_DOMAIN')
    # Caller 32B: tag0,state2,sample4,length high6/low8,phase scratch10,
    # prepared period12DW,left16DW,right20DW,play-id24DW,selected28,
    # backend lease30. Full channels use the pinned 40-byte C layout.
    # State 2 replay is serial caller ownership, not a second sample play.
    lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('SoundAdmission_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;l='SoundAdmission_Guard'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc',bmi='bpl')[op]+' '+l+'\n jmp SoundAdmission_'+n+'\n'+l+':\n.a16\n.i16')
    def require(at,v):put(f' lda.l {at}\n cmp #{v}');branch('bne')
    label('Run');put(' php\n rep #$39\n phx\n phy')
    put(f' jsl {sy["SourceForeignWork_Check"]}');branch('bcs')
    require(work,0xb63b);require(work+30,0xb63c)
    put(f' lda.l {work}+2\n cmp #2');branch('beq','Replay')
    put(' cmp #1');branch('beq','Rejected');put(' cmp #0');branch('bne')
    put(f' lda.l {work}+4\n cmp #{samples}');branch('bcs')
    put(f' lda.l {work}+6\n cmp #16');branch('bcs')
    put(f' ora.l {work}+8');branch('beq')
    put(f' lda.l {work}+26\n cmp #$7FFF');branch('bcs')
    put(f' lda.l {work}+4\n sta.l {sy["SourceSoundChannels4086_Sample"]}\n jsl {sy["SourceSoundChannels4086_Offer"]}');branch('bcs')
    put(f' lda.l {sy["SourceSoundChannels4086_Status"]}');branch('beq','Offered');put(' cmp #1');branch('beq','Reject');put(' jmp SoundAdmission_Bad')
    label('Offered');put(f' lda.l {sy["SourceSoundChannels4086_Selected"]}\n cmp #12');branch('bcs');put(f' sta.l {work}+28')
    # At most 44 source frames; bounded subtraction is the literal modulus.
    put(' asl a\n asl a')
    put(f' ldx #0\n pha\n lda.l {work}+6');branch('bne','PhaseReady')
    put(' pla')
    label('Modulo');put(f' cmp.l {work}+8');branch('bcc','PhaseHave');put(f' sec\n sbc.l {work}+8\n jmp SoundAdmission_Modulo')
    label('PhaseHave');put(' pha')
    label('PhaseReady');put(' pla')
    # Store complete 32-bit Q12 (44<<12 exceeds a word).
    put(f' sta.l {work}+10\n lda.l {work}+28\n asl a\n asl a\n asl a\n pha\n asl a\n asl a\n clc\n adc 1,s\n tax\n pla')
    # full channelstruct: active,paused,sample,priority,playid,volumes,
    # channels,phase,period. Existing compact rows mirror admission metadata.
    for off,val in ((0,1),(2,0),(4,0),(6,0),(10,0),(28,1),(30,0)):
        put(f' lda #{val}\n sta.l {channels}+{off},x')
    put(f' lda.l {work}+4\n sta.l {channels}+8,x')
    for src,dst in ((sy['SourceSoundChannels4086_Priority'],12),(sy['SourceSoundChannels4086_Priority']+2,14),(work+12,36),(work+14,38)):
        put(f' lda.l {src}\n sta.l {channels}+{dst},x')
    put(f' lda.l {work}+24\n clc\n adc #1\n sta.l {work}+24\n sta.l {channels}+16,x\n lda.l {work}+26\n adc #0\n sta.l {work}+26\n sta.l {channels}+18,x')
    for src,dst in ((16,20),(20,24)):
        put(f' lda.l {work}+{src+2}');branch('bmi','VolumeZero'+str(src));branch('bne','VolumeMax'+str(src))
        put(f' lda.l {work}+{src}\n cmp #65');branch('bcc','VolumeStore'+str(src))
        label('VolumeMax'+str(src));put(' lda #64\n jmp SoundAdmission_VolumeStore'+str(src))
        label('VolumeZero'+str(src));put(' lda #0')
        label('VolumeStore'+str(src));put(f' sta.l {channels}+{dst},x\n lda #0\n sta.l {channels}+{dst+2},x')
    put(f' lda.l {work}+10\n and #15');put(' asl a\n'*12);put(f' sta.l {channels}+32,x\n lda.l {work}+10\n lsr a\n lsr a\n lsr a\n lsr a\n sta.l {channels}+34,x')
    put(f' lda.l {work}+28\n asl a\n asl a\n asl a\n tax')
    for src,dst in ((sy['SourceSoundChannels4086_Priority'],0),(sy['SourceSoundChannels4086_Priority']+2,2),(work+4,4)):
        put(f' lda.l {src}\n sta.l $7EFF88+{dst},x')
    put(f' lda #1\n sta.l $7EFF8E,x\n lda #2\n sta.l {work}+2')
    label('Replay');put(f' lda.l {work}+28\n cmp #12');branch('bcs');put(' jmp SoundAdmission_Good')
    label('Reject');put(f' lda #1\n sta.l {work}+2')
    label('Rejected');put(' lda #$FFFF')
    label('Good');put(' ply\n plx\n plp\n clc\n rtl')
    label('Bad');put(f' lda #4\n sta.l {work}+2\n lda #$FFFF\n ply\n plx\n plp\n sec\n rtl')
    return '\n'.join(lines)+'\n'
