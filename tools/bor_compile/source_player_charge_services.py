"""Canonical player_charge_check and mandatory real set_idle continuation.

Caller owns serialized input/state/animation controls and admits DEFAULT_IDLE_ONLY.
This helper does not select charging or replace the full player controller.
"""
from source_player_run_4086 import KEYS


def emit(work,state,history,input_owner,input_magic,symbols):
    spans=((work,24),(state,64),(history,1024),(input_owner,2))
    for i,(a,n)in enumerate(spans):
        if not 0<=a<=0x1000000-n:raise ValueError('CHARGE_SERVICES_EXTENT')
        if any(a<b+m and b<a+n for b,m in spans[i+1:]):raise ValueError('CHARGE_SERVICES_OVERLAP')
    if history&255 or not 1<=input_magic<=65535:raise ValueError('CHARGE_SERVICES_INPUT_OWNER')
    lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('ChargeServices_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;skip='ChargeServices_Skip'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcs='bcc',bcc='bcs')[op]+' '+skip+'\n jmp ChargeServices_'+n+'\n'+skip+':\n.a16\n.i16')
    label('Begin');put(f' php\n rep #$39\n phx\n phy\n lda.l {work}\n cmp #$B686');branch('bne')
    put(f' lda.l {work}+2');branch('beq','Ready');put(' cmp #2');branch('bne')
    label('Ready');put(f' lda.l {input_owner}\n cmp #{input_magic}');branch('bne')
    put(f' lda.l {work}+4\n sta.l {state}+4\n jsl SourcePlayerState_Read');branch('bcs')
    put(f' lda.l {work}+4\n sta.l {work}+20\n lda #0')
    for bit in range(6,-1,-1):
        put(' asl a')
        if 80&(1<<bit):put(f' clc\n adc.l {work}+20')
    put(f' sta.l {work}+8\n tax\n clc\n adc #$4000\n cmp.l $414000,x');branch('bne')
    put(' lda.l $414002,x\n cmp #$41');branch('bne')
    put(' lda.l $414028,x\n cmp #1');branch('bne')
    put(' lda.l $41402A,x\n ora.l $41402E,x');branch('bne')
    put(' lda.l $41402C,x\n cmp #4');branch('bcs')
    put(f' sta.l {work}+6\n xba\n tax\n lda.l {history}+216,x\n and #{KEYS["jump"]}');branch('beq','Cancel')
    put(f' lda.l {history}+216,x\n and #{KEYS["special"]}');branch('bne','Done')
    label('Cancel');put(f' lda.l {work}+4\n sta.l {symbols["SourceIdle4086_Slot"]}\n lda #0\n sta.l {state}+6\n sta.l {state}+20\n sta.l {state}+22\n jsl SourcePlayerState_Write');branch('bcs')
    put(f' lda.l {work}+8\n tax\n lda #0\n sta.l $43900C,x\n sta.l $43900E,x\n jsl {symbols["SourceSetIdle4086_Begin"]}');branch('bcs')
    put(' cmp #0');branch('beq','Done');put(' cmp #1');branch('bne')
    put(f' lda #3\n sta.l {work}+2\n lda #1\n ply\n plx\n plp\n clc\n rtl')
    label('FinishFrame');put(f' php\n rep #$39\n phx\n phy\n lda.l {work}\n cmp #$B686');branch('bne')
    put(f' lda.l {work}+2\n cmp #3');branch('bne')
    put(f' lda.l {symbols["SourceAnimationInit4086_Slot"]}\n cmp.l {work}+4');branch('bne')
    put(f' jsl {symbols["SourceAnimationInit4086_Ack"]}');branch('bcs')
    label('Done');put(f' lda #2\n sta.l {work}+2\n lda #0\n ply\n plx\n plp\n clc\n rtl')
    label('Bad');put(f' lda #4\n sta.l {work}+2\n ply\n plx\n plp\n sec\n rtl')
    return '\n'.join(lines)+'\n'
