"""Canonical player_pain_check through real special and frame services."""


def emit(work,binding,services):
    spans=((work,24),(binding,64),(services,32))
    for i,(a,n)in enumerate(spans):
        if not 0<=a<=0x1000000-n:raise ValueError('PAIN_SERVICES_EXTENT')
        if any(a<b+m and b<a+n for b,m in spans[i+1:]):raise ValueError('PAIN_SERVICES_OVERLAP')
    lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('PainServices_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;skip='PainServices_Skip'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+skip+'\n jmp PainServices_'+n+'\n'+skip+':\n.a16\n.i16')
    for entry in ('Begin','FinishFrame'):
        label(entry);put(f' php\n rep #$39\n phx\n phy\n lda.l {work}\n cmp #$B687');branch('bne')
        if entry=='Begin':
            put(f' lda.l {work}+2');branch('beq','Ready');put(' cmp #2');branch('bne')
            label('Ready');put(f' lda.l {work}+4\n sta.l {binding}+4\n lda #0\n sta.l {work}+6\n jsl SpecialServices_Begin');branch('bcs')
        else:
            put(f' lda.l {work}+2\n cmp #3');branch('bne')
            put(f' lda.l {work}+4\n cmp.l {binding}+4');branch('bne')
            put(' jsl SpecialServices_FinishFrame');branch('bcs')
        put(' jmp PainServices_Drive')
    label('Drive');put(' cmp #1');branch('beq','Pending');put(' cmp #0');branch('bne')
    put(f' lda.l {services}+2\n cmp #2');branch('beq','Complete');put(' cmp #4');branch('bne')
    # The special service has freshly validated this actor before publication.
    put(f' lda.l {binding}+14\n tax\n lda #0\n sta.l $43EB04,x\n sta.l $43EB06,x\n lda #1\n sta.l {work}+6')
    label('Complete');put(f' lda #2\n sta.l {work}+2\n lda #0\n ply\n plx\n plp\n clc\n rtl')
    label('Pending');put(f' lda #3\n sta.l {work}+2\n lda #1\n ply\n plx\n plp\n clc\n rtl')
    label('Bad');put(f' lda #4\n sta.l {work}+2\n ply\n plx\n plp\n sec\n rtl')
    return '\n'.join(lines)+'\n'
