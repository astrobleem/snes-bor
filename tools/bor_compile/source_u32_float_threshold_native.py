"""Explicit source evaluation policy for u32-plus-integral-duration comparison.

The compiler must prove GAME_SPEED*chargetime is an exact nonnegative integer
<=65535. WIN32_X87_EXTENDED is the pinned -m32 GCC baseline, verified with the
source C harness and GCC assembly. Integral arithmetic remains exact. BINARY32
is a separate explicit evaluation policy with round to nearest even. Both use
33-bit intermediates; crossing UINT32_MAX never wraps or spuriously faults.
"""

def emit(work,evaluation='WIN32_X87_EXTENDED'):
    if evaluation not in('WIN32_X87_EXTENDED','BINARY32'):raise ValueError('U32_FLOAT_THRESHOLD_EVALUATION')
    if not 0<=work<=0x1000000-64:raise ValueError('U32_FLOAT_THRESHOLD_EXTENT')
    lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('U32FloatThreshold_'+n+':\n.a16\n.i16')
    def branch(op,n):
        nonlocal serial
        serial+=1;skip='U32FloatThreshold_Skip'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+skip+'\n jmp U32FloatThreshold_'+n+'\n'+skip+':\n.a16\n.i16')
    def round_value(name,dst):
        put(f' lda.l {work}+{dst+4}');branch('bne',name+'Q512')
        for shift in range(8,0,-1):
            put(f' lda.l {work}+{dst+2}\n cmp #{1<<(shift+7)}');branch('bcs',name+'Q'+str(1<<shift))
        put(' jmp U32FloatThreshold_'+name+'Rounded')
        for shift in range(9,0,-1):
            q=1<<shift;mask=q-1;label(name+'Q'+str(q))
            put(f' lda.l {work}+{dst}\n and #{mask}\n sta.l {work}+44\n lda.l {work}+{dst}\n and #{(~mask)&65535}\n sta.l {work}+{dst}\n lda.l {work}+44\n cmp #{q//2}')
            branch('bcc',name+'Rounded');branch('bne',name+'Up'+str(q))
            put(f' lda.l {work}+{dst}\n and #{q}');branch('beq',name+'Rounded')
            label(name+'Up'+str(q));put(f' lda.l {work}+{dst}\n clc\n adc #{q}\n sta.l {work}+{dst}\n lda.l {work}+{dst+2}\n adc #0\n sta.l {work}+{dst+2}\n lda.l {work}+{dst+4}\n adc #0\n sta.l {work}+{dst+4}\n jmp U32FloatThreshold_'+name+'Rounded')
        label(name+'Rounded')
    label('Execute');put(f' php\n rep #$39\n pha\n phx\n phy\n lda.l {work}\n cmp #$B68E');branch('bne','Bad')
    put(f' lda.l {work}+14');branch('bne','Bad')
    for src,dst in ((4,20),(8,26)):
        put(f' lda.l {work}+{src}\n sta.l {work}+{dst}\n lda.l {work}+{src+2}\n sta.l {work}+{dst+2}\n lda #0\n sta.l {work}+{dst+4}')
    if evaluation=='BINARY32':round_value('Stall',20);round_value('Time',26)
    put(f' lda.l {work}+20\n clc\n adc.l {work}+12\n sta.l {work}+32\n lda.l {work}+22\n adc #0\n sta.l {work}+34\n lda.l {work}+24\n adc #0\n sta.l {work}+36')
    if evaluation=='BINARY32':round_value('Sum',32)
    put(f' lda #0\n sta.l {work}+16\n lda.l {work}+36\n cmp.l {work}+30');branch('bcc','True');branch('bne','Done')
    put(f' lda.l {work}+34\n cmp.l {work}+28');branch('bcc','True');branch('bne','Done')
    put(f' lda.l {work}+32\n cmp.l {work}+26');branch('bcs','Done')
    label('True');put(f' lda #1\n sta.l {work}+16')
    label('Done');put(f' lda #2\n sta.l {work}+2\n ply\n plx\n pla\n plp\n clc\n rtl')
    label('Bad');put(f' lda #4\n sta.l {work}+2\n ply\n plx\n pla\n plp\n sec\n rtl')
    return '\n'.join(lines)+'\n'
