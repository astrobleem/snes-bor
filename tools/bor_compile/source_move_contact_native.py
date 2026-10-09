"""Generation-bound persistent pathblocked/grabwalking; no fabricated birth."""
from source_move_contact_layout import layout
from source_hit_state_layout import layout as hit_layout


def emit(plan,sy):
    if plan!=layout(plan['entities']):raise ValueError('MOVE_CONTACT_NATIVE_PLAN')
    h=hit_layout(plan['entities'])['controls'];w=plan['controls'];base=plan['base'];lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('MoveContact_'+n+':\n.a16\n.i16')
    def fault(op):
        nonlocal serial
        serial+=1;n='MoveContact_Guard'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+f' {n}\n jmp MoveContact_Bad\n{n}:\n.a16\n.i16')
    for name in ('Initialize','ClearBirth','Read','Write'):
        label(name);put(' php\n rep #$39\n pha\n phx\n phy')
        put(f' jsl {sy["SourceForeignWork_Check"]}');fault('bcs')
        for op,off in (('txa',8),('tya',10)):
            put(f' {op}\n cmp.l {w}+{off}');fault('bne');put(f' cmp.l {h}+{off}');fault('bne')
        for at,value in ((w+16,base&65535),(w+18,0x42),(w+22,plan['entities']),(h,0xb6a0),(h+22,plan['entities'])):
            put(f' lda.l {at}\n cmp #{value}');fault('bne')
        put(f' lda.l {w}+20');fault('beq');put(f' cmp #{plan["chr_capacity"]+1}');fault('bcs')
        put(f' cmp.l {h}+20');fault('bne')
        if name=='Initialize':
            put(f' lda.l {w}');fault('bne');put(' lda #0\n ldx #0')
            label('ClearAll');put(f' sta.l {base},x\n inx\n inx\n cpx #{plan["bytes"]}\n bne MoveContact_ClearAll\n lda #$B6A6\n sta.l {w}\n jmp MoveContact_Good')
        else:
            put(f' lda.l {w}\n cmp #$B6A6');fault('bne')
            put(f' lda.l {w}+4\n cmp #{plan["entities"]}');fault('bcs');put(f' cmp.l {h}+4');fault('bne')
            put(' jsl HitState_Read');fault('bcs')
            put(f' lda.l {w}+4\n asl a\n asl a\n asl a\n tax')
            if name=='Read':
                for off in range(0,8,2):put(f' lda.l {base}+{off},x\n sta.l {w}+{24+off}')
            elif name=='Write':
                for off in range(0,8,2):put(f' lda.l {w}+{24+off}\n sta.l {base}+{off},x')
            else:
                put(f' lda #0\n sta.l {base},x\n sta.l {base}+2,x\n sta.l {base}+4,x\n sta.l {base}+6,x')
            put(' jmp MoveContact_Good')
    label('Good');put(f' lda #2\n sta.l {w}+2');put(' ply\n plx\n pla\n plp\n clc\n rtl')
    label('Bad');put(f' lda #3\n sta.l {w}+2');put(' ply\n plx\n pla\n plp\n sec\n rtl')
    return '\n'.join(lines)+'\n'
