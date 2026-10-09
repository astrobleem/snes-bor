"""Captured source-frame SOUND admission and acknowledgement.

The installer supplies retained controls and a live PCM backend lease. This
emitter has no actor-name logic, RAM allocation, or implicit frame completion.
"""

def emit(control,request,metadata,sy,*,samples=30):
    if not 1<=samples<=32767 or not 0<=control<=0xffffff-32 or not 0<=request<=0xffffff-32 or max(control,request)<min(control+32,request+32):
        raise ValueError('FRAME_SOUND_ADMISSION_DOMAIN')
    # 32B owner: tag0=B63D,state2(0new/1admitted/2acked/4fault),
    # slot4,handle6,frame8,cursor10,generation12DW,sample16.
    # The request is the existing 32B SoundAdmission owner. Installer supplies
    # prepared period, both gains, play-id and backend lease.
    out=[];serial=0
    def put(s):out.extend(s.strip().splitlines())
    def label(n):put('FrameSound_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;k='FrameSound_Guard'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+k+'\n jmp FrameSound_'+n+'\n'+k+':\n.a16\n.i16')
    def require(at,value):put(f' lda.l {at}\n cmp #{value}');branch('bne')
    label('Admit');put(' php\n rep #$39\n phx\n phy')
    put(f' jsl {sy["SourceForeignWork_Check"]}');branch('bcs')
    require(control,0xb63d)
    put(f' lda.l {control}+2\n cmp #1');branch('beq','Replay');put(' cmp #0');branch('bne')
    put(' jsr FrameSound_CheckPending');branch('bcs')
    # Checked captured immutable B4FE frame: sound is a signed int32 at +16.
    put(f' lda.l {sy["SourceUpdateFrame4086_FrameData"]}\n cmp #$8000');branch('bcc')
    put(' clc\n adc #24');branch('bcs')
    put(f' cmp.l {sy["SourceUpdateFrame4086_TableEnd"]}');branch('bcc','Bounds');branch('bne')
    label('Bounds');put(f' lda.l {sy["SourceUpdateFrame4086_Bank"]}\n cmp #64');branch('bcs')
    put(f' lda.l {sy["SourceUpdateFrame4086_FrameData"]}\n clc\n adc #18\n tax\n phb\n sep #$20\n.a8\n lda.l {sy["SourceUpdateFrame4086_Bank"]}\n pha\n plb\n rep #$20\n.a16\n lda.w $0000,x\n plb\n cmp #0');branch('bne')
    put(' dex\n dex\n phb\n sep #$20\n.a8\n');put(f' lda.l {sy["SourceUpdateFrame4086_Bank"]}\n pha\n plb\n rep #$20\n.a16\n lda.w $0000,x\n plb\n cmp #{samples}');branch('bcs')
    put(f' sta.l {request}+4\n sta.l {control}+16\n asl a\n asl a\n asl a\n tax')
    # PC8D metadata stores word byte count, so divide its 32-bit count by two.
    require(metadata,0x4350);require(metadata+2,0x4438);require(metadata+4,1);require(metadata+6,samples)
    put(f' lda.l {metadata}+8,x\n pha\n lda.l {metadata}+10,x\n lsr a\n sta.l {request}+6\n pla\n ror a\n sta.l {request}+8\n lda #0\n sta.l {request}+2\n lda #0\n sta.l {sy["SourceSoundChannels4086_Priority"]}\n sta.l {sy["SourceSoundChannels4086_Priority"]}+2')
    put(' lda 3,s\n tax\n lda 1,s\n tay\n jsl SoundAdmission_Run');branch('bcs')
    put(f' lda.l {request}+2\n cmp #1');branch('beq','Stamp');put(' cmp #2');branch('bne')
    put(' jsl SoundPCM8Descriptor_Run');branch('bcs')
    label('Stamp')
    for src,dst in ((sy['SourceUpdateFrame4086_Slot'],4),(sy['SourceUpdateFrame4086_Handle'],6),(sy['SourceUpdateFrame4086_Request'],8),(sy['SourceFrameEffectPlan4086_Index'],10),(sy['SourceForeignWork_Generation'],12),(sy['SourceForeignWork_Generation']+2,14)):
        put(f' lda.l {src}\n sta.l {control}+{dst}')
    put(f' lda #1\n sta.l {control}+2\n jmp FrameSound_Good')
    label('Replay');put(' jsr FrameSound_CheckPending');branch('bcs');put(' jsr FrameSound_CheckStamp');branch('bcs');put(' jmp FrameSound_Good')
    label('Ack');put(' php\n rep #$39\n phx\n phy')
    put(f' jsl {sy["SourceForeignWork_Check"]}');branch('bcs');require(control,0xb63d)
    put(f' lda.l {control}+2\n cmp #1');branch('bne');put(' jsr FrameSound_CheckPending');branch('bcs');put(' jsr FrameSound_CheckStamp');branch('bcs')
    put(f' lda.l {request}+2\n cmp #1');branch('beq','AckReady');put(' cmp #2');branch('bne')
    label('AckReady');put(f' lda #9\n sta.l {sy["SourceFrameEffectPlan4086_Acknowledged"]}\n jsl {sy["SourceFrameEffectPlan4086_Ack"]}');branch('bcs')
    put(f' lda #2\n sta.l {control}+2')
    label('Good');put(' lda #0\n ply\n plx\n plp\n clc\n rtl')
    label('Bad');put(f' lda #4\n sta.l {control}+2\n ply\n plx\n plp\n sec\n rtl')
    label('CheckPending')
    for src,value in ((sy['SourceUpdateFrame4086_Ready'],0xb4e3),(sy['SourceUpdateFrame4086_State'],1),(sy['SourceUpdateFrame4086_Pending'],2),(sy['SourceFrameEffectPlan4086_Ready'],0xb4f2),(sy['SourceFrameEffectPlan4086_State'],1),(sy['SourceFrameEffectPlan4086_Service'],9),(sy['SourceFrameEffectPlan4086_Acknowledged'],0)):
        put(f' lda.l {src}\n cmp #{value}');branch('bne','CheckBad')
    for src,dst in ((sy['SourceFrameEffectPlan4086_Slot'],sy['SourceUpdateFrame4086_Slot']),(sy['SourceFrameEffectPlan4086_Handle'],sy['SourceUpdateFrame4086_Handle']),(sy['SourceFrameEffectPlan4086_Frame'],sy['SourceUpdateFrame4086_Request'])):
        put(f' lda.l {src}\n cmp.l {dst}');branch('bne','CheckBad')
    put(' clc\n rts')
    label('CheckStamp')
    for src,dst in ((sy['SourceUpdateFrame4086_Slot'],4),(sy['SourceUpdateFrame4086_Handle'],6),(sy['SourceUpdateFrame4086_Request'],8),(sy['SourceFrameEffectPlan4086_Index'],10),(sy['SourceForeignWork_Generation'],12),(sy['SourceForeignWork_Generation']+2,14),(request+4,16)):
        put(f' lda.l {src}\n cmp.l {control}+{dst}');branch('bne','CheckBad')
    put(' clc\n rts')
    label('CheckBad');put(' sec\n rts')
    return '\n'.join(out)+'\n'
