"""Source attack sequence assignment under explicit world/canvas/hit leases.

Initialize once after the foreign arena clear. Assignment requires phase8.
The caller still owns ordered targeting, real hit services and world completion.
"""
from source_foreign_state_layout import layout as arena
from source_hit_state_layout import layout


def emit(plan,sy):
    if plan!=layout(plan['entities']):raise ValueError('ATTACK_ID_HIT_PLAN')
    region=next(r for r in arena(sy['SOURCE_FOREIGN_WORK_BASE'],sy['SOURCE_FOREIGN_WORK_BYTES'],plan['entities'])['regions']if r['name']=='attack_identity_sequence')
    seq=region['address'];w=plan['controls'];lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('AttackIdentity_'+n+':\n.a16\n.i16')
    def bad(op):
        nonlocal serial
        serial+=1;l='AttackIdentity_Guard'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+l+'\n jmp AttackIdentity_Bad\n'+l+':\n.a16\n.i16')
    def entry(n):
        label(n);put(' php\n rep #$39\n pha\n phx\n phy')
        put(f' jsl {sy["SourceForeignWork_Check"]}');bad('bcs')
    entry('Initialize');put(f' lda.l {seq}+4');bad('bne')
    put(f' lda #1\n sta.l {seq}\n lda #0\n sta.l {seq}+2\n lda #$B6A2\n sta.l {seq}+4\n jmp AttackIdentity_Good')
    entry('Assign')
    for n,v in (('SourceWorldTick4086_Ready',0xb4d5),('SourceWorldTick4086_State',1),('SourceWorldTick4086_Pending',1),('SourceWorldTick4086_Phase',8),('SourceWorldTick4086_Fault',0)):
        put(f' lda.l {sy[n]}\n cmp #{v}');bad('bne')
    put(f' lda.l {sy["SourceWorldTick4086_Slot"]}\n cmp.l {w}+4');bad('bne')
    for off,n in ((0,'Lo'),(2,'Hi')):
        put(f' lda.l {sy["SourceWorldTick4086_Time"+n]}\n cmp.l {sy["VmSourceWorld_Time"]+off}');bad('bne')
    put(f' lda.l {seq}+4\n cmp #$B6A2');bad('bne')
    put(f' lda.l {seq}\n ora.l {seq}+2');bad('beq')
    put(' jsl HitState_Read');bad('bcs')
    put(f' lda.l {w}+4\n asl a\n asl a\n asl a\n asl a\n sta.l {w}+36\n asl a\n asl a\n clc\n adc.l {w}+36\n adc #$4000\n tax\n cmp.l $410000,x');bad('bne')
    put(f' txa\n sec\n sbc #$4000\n cmp.l {sy["SourceWorldTick4086_View"]}');bad('bne')
    put(f' lda.l {w}+4\n asl a\n asl a\n asl a\n asl a\n asl a\n asl a\n cmp.l {sy["SourceWorldTick4086_Side"]}');bad('bne')
    put(' lda.l $410002,x\n cmp #$41');bad('bne')
    put(' lda.l $410004,x\n ora.l $410006,x');bad('beq')
    put(f' lda.l {w}+28\n ora.l {w}+30\n bne AttackIdentity_Good')
    put(f' lda.l {seq}\n clc\n adc #1\n sta.l {w}+28\n lda.l {seq}+2\n adc #0\n sta.l {w}+30\n ora.l {w}+28\n bne AttackIdentity_Write\n lda #1\n sta.l {w}+28')
    label('Write');put(f' lda.l {w}+8\n tax\n lda.l {w}+10\n tay\n jsl HitState_Write');bad('bcs')
    for off in (0,2):put(f' lda.l {w}+{28+off}\n sta.l {seq}+{off}')
    label('Good');put(' ply\n plx\n pla\n plp\n clc\n rtl')
    label('Bad');put(' ply\n plx\n pla\n plp\n sec\n rtl')
    return '\n'.join(lines)+'\n'
