"""Generation-bound pain/juggle storage below unchanged hit-identity rows.

Only storage primitives are emitted. Birth and model metric arguments must be
installed by source-derived providers; no source damage call is synthesized.
"""
from source_hit_contact_layout import layout


def emit(plan,sy):
    if plan!=layout(plan['entities']):raise ValueError('HIT_CONTACT_NATIVE_PLAN')
    from source_hit_state_layout import layout as hits
    hp=hits(plan['entities']);w=plan['controls'];h=hp['controls'];b=plan['base'];lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('HitContact_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;l='HitContact_Guard'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+l+'\n jmp HitContact_'+n+'\n'+l+':\n.a16\n.i16')
    def entry(name):
        label(name);put(' php\n rep #$39\n pha\n phx\n phy')
        put(f' jsl {sy["SourceForeignWork_Check"]}');branch('bcs')
        put(' txa\n ora 1,s');branch('beq')
        for op,off in (('txa',8),('tya',10)):
            put(f' {op}\n cmp.l {w}+{off}');branch('bne')
            put(f' cmp.l {h}+{off}');branch('bne')
        for at,v in ((h,0xb6a0),(h+16,hp['base']&65535),(h+18,0x42),(h+22,plan['entities']),(h+20,plan['chr_capacity']),(w+16,b&65535),(w+18,0x42),(w+20,plan['chr_capacity']),(w+22,plan['entities'])):
            put(f' lda.l {at}\n cmp #{v}');branch('bne')
    entry('Initialize');put(f' lda.l {w}');branch('bne')
    put(' ldx #0\n lda #0')
    label('ClearAll');put(f' sta.l {b},x\n inx\n inx\n cpx #{plan["bytes"]}\n bne HitContact_ClearAll\n lda #$B6A3\n sta.l {w}\n jmp HitContact_Good')
    for name in ('Birth','Read','Write','CopyModel'):
        entry(name);put(f' lda.l {w}\n cmp #$B6A3');branch('bne')
        put(f' lda.l {w}+4\n cmp #{plan["entities"]}');branch('bcs')
        put(f' cmp.l {h}+4');branch('bne')
        if name=='Birth':
            put(f' lda.l {sy["VmSourceWorld_Ready"]}\n cmp #$B4A3');branch('bne')
            put(f' lda.l {sy["VmSourceWorld_Count"]}');branch('beq')
            put(f' cmp #{plan["entities"]+1}');branch('bcs')
            put(f' lda.l {w}+4\n cmp.l {sy["VmSourceWorld_Count"]}');branch('bcs')
        else:put(' jsl HitState_Read');branch('bcs')
        put(f' lda.l {w}+4\n asl a\n asl a\n asl a\n tax')
        if name=='Birth':
            put(f' lda #0\n sta.l {b},x\n sta.l {b}+2,x')
            for off in (0,2):put(f' lda.l {w}+{28+off}\n sta.l {b}+{4+off},x')
        elif name=='Read':
            for off in (0,2,4,6):put(f' lda.l {b}+{off},x\n sta.l {w}+{24+off}')
        elif name=='Write':
            for off in (0,2,4,6):put(f' lda.l {w}+{24+off}\n sta.l {b}+{off},x')
        else:
            for off in (0,2):put(f' lda.l {w}+{28+off}\n sta.l {b}+{4+off},x')
        put(' jmp HitContact_Good')
    label('Good');put(f' lda #2\n sta.l {w}+2\n ply\n plx\n pla\n plp\n clc\n rtl')
    label('Bad');put(f' lda #3\n sta.l {w}+2\n ply\n plx\n pla\n plp\n sec\n rtl')
    return '\n'.join(lines)+'\n'
