"""Canonical player_think entry prefix with mandatory real helper continuations.

State 2 continues the still-required controller body; state 4 returns from
player_think. Matching ENDLEVEL candidates reject until completion is owned.
"""


def emit(work,state,search,combo,charge,pain,symbols):
    spans=((work,32),(state,64),(search,24),(combo,96),(charge,24),(pain,24))
    for i,(a,n)in enumerate(spans):
        if not 0<=a<=0x1000000-n:raise ValueError('PLAYER_EARLY_EXTENT')
        if any(a<b+m and b<a+n for b,m in spans[i+1:]):raise ValueError('PLAYER_EARLY_OVERLAP')
    lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('PlayerEarly_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;skip='PlayerEarly_Skip'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+skip+'\n jmp PlayerEarly_'+n+'\n'+skip+':\n.a16\n.i16')
    def offset(dest,stride):
        put(' lda #0')
        for bit in range(stride.bit_length()-1,-1,-1):
            put(' asl a')
            if stride&(1<<bit):put(f' clc\n adc.l {work}+4')
        put(f' sta.l {work}+{dest}')
    def state_read():
        put(f' lda.l {work}+4\n sta.l {state}+4\n jsl SourcePlayerState_Read');branch('bcs')
    label('Begin');put(f' php\n rep #$39\n phx\n phy\n lda.l {work}\n cmp #$B688');branch('bne')
    put(f' lda.l {work}+2');branch('beq','Ready');put(' cmp #2');branch('beq','Ready');put(' cmp #4');branch('bne')
    label('Ready');put(f' lda #1\n sta.l {work}+2');state_read()
    for dest,stride in ((18,80),(20,64),(22,24),(24,32),(26,96)):offset(dest,stride)
    put(f' lda.l {work}+22\n tax\n lda.l $42F404,x\n sta.l {work}+8\n lda.l $42F406,x\n sta.l {work}+10')
    put(f' lda.l {work}+18\n tax\n clc\n adc #$4000\n cmp.l $414000,x');branch('bne')
    put(' lda.l $414002,x\n cmp #$41');branch('bne')
    put(' lda.l $414028,x\n cmp #1');branch('bne')
    put(' lda.l $41402A,x\n ora.l $41402E,x');branch('bne')
    put(' lda.l $41402C,x\n cmp #4');branch('bcs')
    put(f' sta.l {work}+6\n asl a\n asl a\n tax\n lda.l $43FD86,x\n cmp #$41');branch('bne','Exit')
    put(f' lda.l {work}+18\n clc\n adc #$4000\n cmp.l $43FD84,x');branch('bne','Exit')
    put(f' lda.l {work}+18\n tax\n lda.l $439014,x\n ora.l $439016,x');branch('bne','Exit')
    put(f' lda.l {work}+4\n sta.l {search}+4\n lda #256\n sta.l {search}+6\n lda #0\n sta.l {search}+8\n jsl SourceFindHereEmpty_Execute');branch('bcs')
    put(f' lda.l {search}+2\n cmp #2');branch('bne')
    # Source time and rush.time are both u32; strict greater-than, no signed test.
    put(f' lda.l {work}+14\n cmp.l {state}+54');branch('bcc','Preinput');branch('bne','RushExpired')
    put(f' lda.l {work}+12\n cmp.l {state}+52');branch('bcc','Preinput');branch('beq','Preinput')
    label('RushExpired');put(f' lda #0\n sta.l {state}+20\n sta.l {state}+22\n lda #3\n sta.l {state}+6\n jsl SourcePlayerState_Write');branch('bcs')
    put(f' lda #5\n sta.l {state}+6\n jsl SourcePlayerState_Write');branch('bcs')
    label('Preinput');put(f' lda.l {work}+4\n sta.l {combo}+4\n lda #1\n sta.l {work}+16\n jsl SourceCombo_Begin');branch('bcs')
    label('ComboResult');put(f' lda.l {combo}+2\n cmp #4');branch('beq','Exit');put(' cmp #3');branch('beq','Pending');put(' cmp #2');branch('bne')
    state_read();put(f' lda.l {state}+32\n ora.l {state}+34');branch('bne','Charge')
    put(f' lda.l {work}+24\n tax\n lda.l $43EB04,x\n ora.l $43EB06,x');branch('bne','Pain')
    put(f' lda.l {work}+20\n tax\n lda.l $40901C,x\n ora.l $40901E,x');branch('beq','Continue')
    put(f' lda.l {work}+26\n tax\n lda.l $40C050,x\n ora.l $40C052,x');branch('bne','Continue')
    label('Pain');put(f' lda.l {work}+4\n sta.l {pain}+4\n lda #3\n sta.l {work}+16\n jsl PainServices_Begin');branch('bcs');put(' jmp PlayerEarly_HelperResult')
    label('Charge');put(f' lda.l {work}+4\n sta.l {charge}+4\n lda #2\n sta.l {work}+16\n jsl ChargeServices_Begin');branch('bcs')
    label('HelperResult');put(' cmp #0');branch('beq','Exit');put(' cmp #1');branch('bne')
    label('Pending');put(f' lda #3\n sta.l {work}+2\n lda #1\n ply\n plx\n plp\n clc\n rtl')
    label('FinishFrame');put(f' php\n rep #$39\n phx\n phy\n lda.l {work}\n cmp #$B688');branch('bne')
    put(f' lda.l {work}+2\n cmp #3');branch('bne')
    put(f' lda.l {work}+16\n cmp #1');branch('beq','ComboFinish');put(' cmp #2');branch('beq','ChargeFinish');put(' cmp #3');branch('bne')
    put(' jsl PainServices_FinishFrame');branch('bcs');put(' jmp PlayerEarly_HelperResult')
    label('ChargeFinish');put(' jsl ChargeServices_FinishFrame');branch('bcs');put(' jmp PlayerEarly_HelperResult')
    label('ComboFinish');put(f' jsl {symbols["SourceAnimationInit4086_Ack"]}');branch('bcs')
    put(' jsl SourceCombo_Finish');branch('bcs');put(' jmp PlayerEarly_ComboResult')
    for name,status in (('Continue',2),('Exit',4)):
        label(name);put(f' lda #{status}\n sta.l {work}+2\n lda #0\n ply\n plx\n plp\n clc\n rtl')
    label('Bad');put(f' lda #5\n sta.l {work}+2\n ply\n plx\n plp\n sec\n rtl')
    return '\n'.join(lines)+'\n'
