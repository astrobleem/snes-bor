"""Ordered source target scan through real preparation/filter/collision.

An admitted target returns a mandatory hit-service ticket before ondoattack.
No API accepts a fabricated callback response or acknowledges phase8.
"""
from source_hit_contact_layout import layout
from source_do_attack_prepare_native import TARGET_LOOP_REQUIRED
HIT_SERVICE_REQUIRED=0x8111


def emit(plan,sy):
    if plan!=layout(plan['entities']):raise ValueError('ATTACK_LOOP_PLAN')
    from source_hit_state_layout import layout as hits
    w=plan['controls'];h=hits(plan['entities'])['controls'];lines=[];serial=0;size=16
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('AttackLoop_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;l='AttackLoop_Guard'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+f' {l}\n jmp AttackLoop_{n}\n{l}:\n.a16\n.i16')
    def entry(n):
        label(n);put(f' php\n rep #$39\n phx\n phy\n phd\n tsc\n sec\n sbc #{size}\n tcs\n inc a\n tcd\n stx $00\n sty $02')
        put(f' jsl {sy["SourceForeignWork_Check"]}');branch('bcs')
    entry('Begin');put(f' lda.l {w}+60');branch('bne')
    put(' jsl DoAttackPrepare_Run');branch('bcs');put(' cmp #0');branch('beq','Inactive');put(f' cmp #{TARGET_LOOP_REQUIRED}');branch('bne')
    put(f' lda #0\n sta.l {w}+56\n lda #$FFFF\n sta.l {w}+58\n lda #1\n sta.l {w}+60\n lda #{TARGET_LOOP_REQUIRED}\n jmp AttackLoop_Good')
    label('Inactive');put(f' lda #3\n sta.l {w}+60\n lda #0\n jmp AttackLoop_Good')
    entry('Poll')
    for at,v in ((w,0xb6a3),(w+52,0xb6a4),(sy['SourceWorldTick4086_Ready'],0xb4d5),(sy['SourceWorldTick4086_State'],1),(sy['SourceWorldTick4086_Phase'],8),(sy['SourceWorldTick4086_Pending'],1),(sy['SourceWorldTick4086_Fault'],0)):
        put(f' lda.l {at}\n cmp #{v}');branch('bne')
    for op,off in (('txa',8),('tya',10)):
        put(f' {op}\n cmp.l {w}+{off}');branch('bne');put(f' cmp.l {h}+{off}');branch('bne')
    for off in (0,2):
        put(f' lda.l {sy["SourceWorldTick4086_TimeLo"]}+{off}\n cmp.l {sy["VmSourceWorld_Time"]}+{off}');branch('bne')
    put(f' lda.l {h}+4\n cmp.l {sy["SourceWorldTick4086_Slot"]}');branch('bne')
    put(f' lda.l {w}+60\n cmp #2');branch('beq','Pending');put(' cmp #3');branch('beq','Done');put(' cmp #1');branch('bne')
    put(f' lda.l {sy["VmSourceWorld_Count"]}');branch('beq');put(f' cmp #{plan["entities"]+1}');branch('bcs')
    put(f' lda.l {sy["SourceWorldTick4086_Slot"]}\n cmp.l {sy["VmSourceWorld_Count"]}');branch('bcs')
    put(' asl a\n asl a\n asl a\n asl a\n asl a\n asl a\n tax')
    # Original animation pointer controls !followed. No hit has yet been serviced.
    put(f' lda.l $416804,x\n cmp.l {w}+44');branch('bne','Done')
    # Attack parameters were captured before the loop. An external frame writer
    # cannot be admitted while the source call is suspended before hit services.
    put(f' lda.l $416806,x\n cmp.l {w}+46');branch('bne')
    label('Next');put(f' lda.l {w}+56\n cmp.l {sy["VmSourceWorld_Count"]}');branch('bcs','Done')
    put(f' sta.l {h}+26\n ldx $00\n ldy $02\n jsl AttackTarget_Run');branch('bcs');put(' cmp #0');branch('bne','Admitted')
    put(f' lda.l {w}+56\n inc a\n sta.l {w}+56\n jmp AttackLoop_Next')
    label('Admitted');put(f' lda.l {w}+56\n sta.l {w}+58\n lda #2\n sta.l {w}+60')
    label('Pending');put(f' lda #{HIT_SERVICE_REQUIRED}\n jmp AttackLoop_Good')
    label('Done');put(f' lda #3\n sta.l {w}+60\n lda #0')
    label('Good');put(f' tay\n tsc\n clc\n adc #{size}\n tcs\n tya\n pld\n ply\n plx\n plp\n clc\n rtl')
    label('Bad');put(f' tsc\n clc\n adc #{size}\n tcs\n pld\n ply\n plx\n plp\n sec\n rtl')
    return '\n'.join(lines)+'\n'
