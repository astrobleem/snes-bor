"""Unsigned source attack identities with birth and independent generation guards.

Caller owns reduced CHR staging and its lifetime lease. This is storage only;
no hit resolution, model-copy reset or world acknowledgement is synthesized.
"""
from source_hit_state_layout import layout


def emit(plan,symbols):
    expected=layout(plan['entities'])
    if plan!=expected:raise ValueError('HIT_STATE_NATIVE_PLAN')
    work=plan['controls'];base=plan['base'];count=plan['entities']
    lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('HitState_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;skip='HitState_Guard'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+skip+'\n jmp HitState_'+n+'\n'+skip+':\n.a16\n.i16')
    def entry(name):
        label(name);put(' php\n rep #$39\n pha\n phx\n phy')
        put(' txa\n ora 1,s');branch('beq')
        put(f' txa\n cmp.l {work}+8');branch('bne')
        put(f' tya\n cmp.l {work}+10');branch('bne')
        put(' jsr HitState_Bind');branch('bcs')
    entry('ClearBirth');put(f' lda.l {work}+6\n tax\n lda #0')
    for off in range(0,8,2):put(f' sta.l {base}+{off},x')
    for off in (8,10):put(f' lda.l {work}+{off}\n sta.l {base}+{off},x')
    put(f' lda #$B6A1\n sta.l {base}+12,x\n lda.l {work}+4\n sta.l {base}+14,x\n jmp HitState_Good')
    for name in ('Read','Write','ResetAttack'):
        entry(name);put(' jsr HitState_Live');branch('bcs')
        if name=='Read':
            for off in range(0,8,2):put(f' lda.l {base}+{off},x\n sta.l {work}+{28+off}')
        elif name=='Write':
            for off in range(0,8,2):put(f' lda.l {work}+{28+off}\n sta.l {base}+{off},x')
        else:put(f' lda #0\n sta.l {base},x\n sta.l {base}+2,x')
        put(' jmp HitState_Good')
    label('Bind');put(f' lda.l {work}\n cmp #$B6A0');branch('bne','LeaseBad')
    for off,value in ((16,base&65535),(18,0x42),(22,count)):
        put(f' lda.l {work}+{off}\n cmp #{value}');branch('bne','LeaseBad')
    # A caller may carve more persistent state below these fixed rows.
    # Positive staging capacity must remain within the identity boundary.
    put(f' lda.l {work}+20');branch('beq','LeaseBad')
    put(f' cmp #{plan["chr_capacity"]+1}');branch('bcs','LeaseBad')
    put(f' lda.l {symbols["VmSourceWorld_Ready"]}\n cmp #$B4A3');branch('bne','LeaseBad')
    put(f' lda.l {symbols["VmSourceWorld_Count"]}');branch('beq','LeaseBad');put(f' cmp #{count+1}');branch('bcs','LeaseBad')
    put(f' lda.l {work}+4\n cmp.l {symbols["VmSourceWorld_Count"]}');branch('bcs','LeaseBad')
    put(f' asl a\n asl a\n asl a\n asl a\n sta.l {work}+6\n clc\n rts')
    label('Live');put(f' lda.l {work}+6\n tax\n lda.l {base}+12,x\n cmp #$B6A1');branch('bne','LeaseBad')
    put(f' lda.l {base}+14,x\n cmp.l {work}+4');branch('bne','LeaseBad')
    for off in (8,10):put(f' lda.l {base}+{off},x\n cmp.l {work}+{off}');branch('bne','LeaseBad')
    put(' clc\n rts');label('LeaseBad');put(' sec\n rts')
    label('Good');put(f' lda #2\n sta.l {work}+2\n ply\n plx\n pla\n plp\n clc\n rtl')
    label('Bad');put(f' lda #3\n sta.l {work}+2\n ply\n plx\n pla\n plp\n sec\n rtl')
    return '\n'.join(lines)+'\n'
