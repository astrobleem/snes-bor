"""Canonical pinned player_fall_check, preserving full landing marker identity."""
from source_player_run_4086 import KEYS


def emit(work,history,input_owner,input_magic,symbols):
    spans=((work,24),(history,1024),(input_owner,2))
    for i,(a,n)in enumerate(spans):
        if not 0<=a<=0x1000000-n:raise ValueError('PLAYER_FALL_EXTENT')
        if any(a<b+m and b<a+n for b,m in spans[i+1:]):raise ValueError('PLAYER_FALL_OVERLAP')
    if history&255 or not 1<=input_magic<=65535:raise ValueError('PLAYER_FALL_INPUT_OWNER')
    lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('PlayerFall_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;skip='PlayerFall_Skip'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+skip+'\n jmp PlayerFall_'+n+'\n'+skip+':\n.a16\n.i16')
    label('Execute');put(' php\n rep #$39\n pha\n phx\n phy')
    for address,magic in ((work,0xb689),(input_owner,input_magic),(symbols['VmSourceWorld_Ready'],0xb4a3),
                           (symbols['VmSourceWorld_PoolBase'],0x4000),(symbols['SourcePhysicsState4086_Ready'],0xb61c)):
        put(f' lda.l {address}\n cmp #{magic}');branch('bne')
    put(f' lda.l {symbols["VmSourceWorld_Count"]}');branch('beq');put(' cmp #129');branch('bcs')
    put(f' lda.l {work}+4\n cmp.l {symbols["VmSourceWorld_Count"]}');branch('bcs')
    put(' asl a\n asl a\n asl a\n asl a');put(f' sta.l {work}+12\n asl a\n asl a\n clc\n adc.l {work}+12\n tax\n clc\n adc #$4000\n cmp.l $414000,x');branch('bne')
    put(' lda.l $414002,x\n cmp #$41');branch('bne')
    put(' lda.l $414028,x\n cmp #1');branch('bne')
    put(' lda.l $41402A,x\n ora.l $41402E,x');branch('bne')
    put(' lda.l $41402C,x\n cmp #4');branch('bcs')
    put(f' sta.l {work}+6\n lda.l {work}+10');branch('bne','Keys')
    put(f' lda.l {work}+8\n cmp #2');branch('beq','Done')
    label('Keys');put(f' lda.l {work}+6\n xba\n tax\n lda.l {history}+216,x\n and #{KEYS["moveup"]|KEYS["jump"]}\n cmp #{KEYS["moveup"]|KEYS["jump"]}');branch('bne','Done')
    put(f' lda.l {work}+12\n tax\n lda #$FFFE\n sta.l $42D80C,x\n lda #$FFFF\n sta.l $42D80E,x')
    for name,status,carry in (('Done',2,'clc'),('Bad',4,'sec')):
        label(name);put(f' lda #{status}\n sta.l {work}+2\n ply\n plx\n pla\n plp\n {carry}\n rtl')
    return '\n'.join(lines)+'\n'
