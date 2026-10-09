"""Actual pending descriptor, JUMPDELAY query and mandatory frame continuation.

Absent JUMPDELAY posts DO_JUMP_REQUIRED. That external owner must execute the
complete dojump body. This emitter never acknowledges it or renders it idle.
"""
from source_engine_function_ids import function_id


def emit(work,pending,jumpdelay,symbols):
    if not 0<=jumpdelay<=65535 or not 0<=work<=0xffffff-63 or not 0<=pending<=0xffffff-63 or work<pending+64 and pending<work+64:raise ValueError('TRYJUMP_NATIVE_LAYOUT')
    action=function_id('common_prejump');lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('TryJump_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;skip='TryJump_Skip'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+skip+'\n jmp TryJump_'+n+'\n'+skip+':\n.a16\n.i16')
    def entry(n):label(n);put(f' php\n rep #$39\n phx\n phy\n lda.l {work}\n cmp #$B692');branch('bne')
    def offset(dest,stride):
        put(' lda #0')
        for bit in range(stride.bit_length()-1,-1,-1):
            put(' asl a')
            if stride&(1<<bit):put(f' clc\n adc.l {work}+4')
        put(f' sta.l {work}+{dest}')
    entry('Begin');put(f' lda.l {work}+2');branch('beq','Ready');put(' cmp #2');branch('beq','Ready');put(' cmp #4');branch('bne')
    label('Ready');put(f' lda #1\n sta.l {work}+2')
    put(f' lda.l {work}+4\n cmp #128');branch('bcs')
    offset(24,64);offset(22,32);offset(26,80)
    put(f' lda.l {work}+24\n tax\n lda.l $416800,x\n sta.l {pending}+6\n lda.l {work}+4\n sta.l {pending}+4\n jsl PendingJump_Read');branch('bcs')
    # Real copied life identity is required before publishing the action.
    put(f' lda.l {symbols["SourceLifecycle4086_Ready"]}\n cmp #$B4FB');branch('bne')
    put(f' lda.l {work}+26\n tax\n lda.l $43904A,x\n cmp #$B4FB');branch('bne')
    put(f' lda.l $439048,x\n cmp.l {pending}+6');branch('bne')
    for at in range(0,12,2):put(f' lda.l {work}+{8+at}\n sta.l {pending}+{32+at}')
    put(f' lda.l {work}+6\n sta.l {pending}+44\n lda #0\n sta.l {pending}+46\n jsl PendingJump_Write');branch('bcs')
    put(f' lda.l {work}+4\n sta.l {symbols["SourceAnimationInit4086_Slot"]}\n lda #{jumpdelay}\n sta.l {symbols["SourceAnimationInit4086_Number"]}\n jsl {symbols["SourceAnimationInit4086_Resolve"]}');branch('bcs')
    put(f' lda.l {symbols["SourceAnimationInit4086_Handle"]}');branch('beq','DoRequired')
    put(f' lda.l {symbols["SourceAnimationInit4086_Count"]}');branch('beq','DoRequired')
    put(f' lda.l {work}+26\n tax\n lda #{action}\n sta.l $43900C,x\n lda #0\n sta.l $43900E,x\n lda.l {work}+24\n tax\n lda #0\n sta.l $416824,x\n sta.l $416826,x\n sta.l $416828,x\n sta.l $41682A,x\n lda.l {work}+22\n tax\n lda #0\n sta.l $43EB00,x\n sta.l $43EB02,x\n lda #0\n sta.l {symbols["SourceAnimationInit4086_Reset"]}\n jsl {symbols["SourceAnimationInit4086_Begin"]}');branch('bcs')
    put(f' lda.l {symbols["SourceAnimationInit4086_State"]}\n cmp #2');branch('beq','Return');put(' cmp #1');branch('bne')
    put(f' lda #3\n sta.l {work}+2\n lda #$8001\n jmp TryJump_Exit')
    entry('FinishFrame');put(f' lda.l {work}+2\n cmp #3');branch('bne')
    put(f' lda.l {symbols["SourceAnimationInit4086_Slot"]}\n cmp.l {work}+4');branch('bne')
    put(f' lda.l {symbols["SourceAnimationInit4086_Number"]}\n cmp #{jumpdelay}');branch('bne')
    put(f' jsl {symbols["SourceAnimationInit4086_Ack"]}');branch('bcs');put(' jmp TryJump_Return')
    entry('CommonPrejump');put(f' lda.l {work}+2');branch('beq','PrejumpReady');put(' cmp #4');branch('beq','PrejumpReady');put(' cmp #2');branch('bne')
    label('PrejumpReady');put(f' lda.l {work}+4\n cmp #128');branch('bcs');offset(24,20)
    put(f' lda.l {work}+24\n tax\n lda.l $41F510,x');branch('bne','Return')
    offset(24,64)
    put(f' lda.l {work}+24\n tax\n lda.l $416800,x\n sta.l {pending}+6\n lda.l {work}+4\n sta.l {pending}+4\n jsl PendingJump_Read');branch('bcs')
    for at in range(0,12,2):put(f' lda.l {pending}+{32+at}\n sta.l {work}+{8+at}')
    put(f' lda.l {pending}+46');branch('bne')
    put(f' lda.l {pending}+44\n sta.l {work}+6')
    label('DoRequired');put(f' lda #5\n sta.l {work}+2\n lda #$8002\n jmp TryJump_Exit')
    label('Return');put(f' lda #4\n sta.l {work}+2\n lda #0')
    label('Exit');put(' ply\n plx\n plp\n clc\n rtl')
    label('Bad');put(f' lda #6\n sta.l {work}+2\n ply\n plx\n plp\n sec\n rtl')
    return '\n'.join(lines)+'\n'
