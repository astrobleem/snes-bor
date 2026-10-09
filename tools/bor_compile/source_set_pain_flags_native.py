"""Pinned painflags and unfrozen macro, after the real frame child completes."""

def emit(work,requirements,palette,sy):
    lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('SetPainFlags_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;k='SetPainFlags_Guard'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+k+'\n jmp SetPainFlags_'+n+'\n'+k+':\n.a16\n.i16')
    def require(src,v):put(f' lda.l {src}\n cmp #{v}');branch('bne')
    def offset(stride,dst):
        put(' lda $00')
        for _ in range(2):put(' asl a')
        if stride in (16,32):
            for _ in range(stride.bit_length()-3):put(' asl a')
        elif stride in (20,24,40,96):
            if stride==20:put(' sta $0E\n asl a\n asl a\n clc\n adc $0E')
            elif stride==24:put(' asl a\n sta $0E\n asl a\n clc\n adc $0E')
            elif stride==40:put(' asl a\n sta $0E\n asl a\n asl a\n clc\n adc $0E')
            else:put(' asl a\n asl a\n asl a\n sta $0E\n asl a\n clc\n adc $0E')
        put(f' sta ${dst:02X}')
    label('Run');put(' php\n rep #$39\n phx\n phy\n phd\n tsc\n sec\n sbc #16\n tcs\n inc a\n tcd')
    put(f' jsl {sy["SourceForeignWork_Check"]}');branch('bcs');require(work,0xb6b5)
    put(f' lda.l {work}+2\n cmp #6');branch('beq','Replay');put(' cmp #3');branch('beq','Begin');put(' cmp #5');branch('bne')
    label('Begin');put(' jsl SetPainBegin_Run');branch('bcs');put(' cmp #2');branch('bne');require(work+2,5)
    label('Replay')
    for src,v in ((sy['SourceAnimationInit4086_State'],2),(sy['SourceUpdateFrame4086_State'],2),(sy['SourceUpdateFrame4086_Pending'],0),(sy['SourceSelf4086_Active'],0),(sy['SourcePhysicsState4086_Ready'],0xb61c),(sy['SourceDamageEffectsState4086_Ready'],0xb62f),(sy['SourceFreeze4086_Ready'],0xb5df)):
        require(src,v)
    for src,dst in ((sy['SourceAnimationInit4086_Slot'],work+4),(sy['SourceAnimationInit4086_Number'],work+14),(sy['SourceAnimationInit4086_Handle'],work+16)):
        put(f' lda.l {src}\n cmp.l {dst}');branch('bne')
    put(f' lda.l {work}+4\n cmp #128');branch('bcs');put(' sta $00')
    for stride,dst in ((32,2),(40,4),(16,6),(24,8),(20,10),(96,12)):offset(stride,dst)
    put(' ldx $0A\n lda.l $437E10,x\n cmp #$B5FB');branch('bne');put(' ldx $08\n lda.l $7EF114,x\n cmp #$B62F');branch('bne')
    put(f' lda.l {work}+2\n cmp #6');branch('beq','Good')
    # Literal source writes precede the conditional colourmap child.
    put(' ldx $02\n lda #0')
    for off in (0,2,8,10,12,14,16,18,20,22):put(f' sta.l $43EB00+{off},x')
    put(' lda #1\n sta.l $43EB04,x\n lda #0\n sta.l $43EB06,x')
    for scratch,base,off in ((6,0x42d800,0),(8,0x7ef100,0),(10,0x437e00,0),(12,0x40c000,88)):
        put(f' ldx ${scratch:02X}\n sta.l {base}+{off},x\n sta.l {base}+{off+2},x')
    put(' ldx $04\n lda.l $42E000,x\n ora.l $42E002,x');branch('beq','ClearFreeze')
    w=palette['controls'];put(f' lda $00\n sta.l {w}+4\n lda #4\n sta.l {w}+24\n lda #0\n sta.l {w}+2')
    # The local stack owns scratch; restore the original generation registers.
    put(' lda 21,s\n tax\n lda 19,s\n tay\n jsl CurrentPalette_Run');branch('bcs')
    label('ClearFreeze');put(' ldx $04\n lda #0')
    for off in (0,2,4,6):put(f' sta.l $42E000+{off},x')
    put(f' lda.l {work}+12\n cmp #{requirements["grabbed"]}');branch('bne','FlagsDone')
    put(' ldx $02\n lda #0\n sta.l $43EB04,x\n sta.l $43EB06,x')
    label('FlagsDone');put(f' lda #6\n sta.l {work}+2')
    label('Good');put(' tsc\n clc\n adc #16\n tcs\n pld\n lda #1\n ply\n plx\n plp\n clc\n rtl')
    label('Bad');put(f' lda #4\n sta.l {work}+2\n tsc\n clc\n adc #16\n tcs\n pld\n ply\n plx\n plp\n sec\n rtl')
    return '\n'.join(lines)+'\n'
