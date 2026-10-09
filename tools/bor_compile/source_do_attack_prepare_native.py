"""Actual check_attack gate plus bounded do_attack owner/identity preparation.

Active preparation returns a mandatory target-loop ticket; it never fabricates
hit callbacks, damage, blocking or a world-phase acknowledgement.
"""
from source_hit_contact_layout import layout
from source_check_attack_native import DO_ATTACK
TARGET_LOOP_REQUIRED=0x8110


def emit(requirements,plan,sy,code_bank=39,collision_bank=58):
    if plan!=layout(plan['entities'])or not 0<=code_bank<64 or not 0<=collision_bank<64:raise ValueError('DO_ATTACK_PREPARE_NATIVE_PLAN')
    from source_hit_state_layout import layout as hits
    hp=hits(plan['entities']);h=hp['controls'];w=plan['controls'];lines=[];serial=0;size=48
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('DoAttackPrepare_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;l='DoAttackPrepare_Guard'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc',bpl='bmi',bmi='bpl')[op]+' '+l+'\n jmp DoAttackPrepare_'+n+'\n'+l+':\n.a16\n.i16')
    def require(at,v):put(f' lda.l {at}\n cmp #{v}');branch('bne')
    label('Run');put(f' php\n rep #$39\n phx\n phy\n phd\n tsc\n sec\n sbc #{size}\n tcs\n inc a\n tcd\n stx $28\n sty $2A')
    require(sy['SourceCollisionFrame4086_Bank'],collision_bank);require(sy['SourceCollisionFrame4086_Bytes'],requirements['collision_table_bytes'])
    put(' jsl CheckAttack_Run');branch('bcs');put(' cmp #0');branch('beq','Done');put(f' cmp #{DO_ATTACK}');branch('bne')
    require(sy['SourceRetirement4086_Ready'],0xb4f8)
    put(f' lda.l {sy["SOURCE_RETIREMENT_ROLES"]}+28\n ora.l {sy["SOURCE_RETIREMENT_ROLES"]}+30');branch('bne','Done')
    require(w,0xb6a3);require(w+20,plan['chr_capacity']);require(h+20,plan['chr_capacity'])
    for op,off in (('txa',8),('tya',10)):
        put(f' {op}\n cmp.l {w}+{off}');branch('bne')
    put(f' lda.l {h}+4\n sta $00\n sta $02\n lda #0\n sta $04')
    # e's original view token is already validated by the actual check_attack.
    put(' lda $00\n asl a\n asl a\n asl a\n asl a\n sta $06\n asl a\n asl a\n clc\n adc $06\n adc #$4000\n sta $08\n lda #$41\n sta $0A')
    label('OwnerLoop');put(f' inc $04\n lda $04\n cmp #{plan["entities"]+1}');branch('bcs')
    put(' lda $02\n asl a\n asl a\n asl a\n asl a\n asl a\n asl a\n tax\n lda.l $40903A,x\n cmp #$B638');branch('bne')
    put(' lda.l $409008,x\n sta $0C\n lda.l $40900A,x\n sta $0E\n ora $0C');branch('beq','OwnerDone')
    for off,n in ((0,'Lo'),(2,'Hi')):put(f' lda ${12+off:02X}\n sta.l {sy["SourceRetirement4086_Arg"+n]}')
    put(f' jsl {sy["SourceRetirement4086_ResolvePointer"]}');branch('bcs');put(' cmp #$FFFF');branch('beq');put(' sta $02\n lda $0C\n sta $08\n lda $0E\n sta $0A\n jmp DoAttackPrepare_OwnerLoop')
    label('OwnerDone');put(' lda $00\n asl a\n asl a\n asl a\n asl a\n sta $06\n lsr a\n clc\n adc $06\n tax\n lda.l $7EF102,x');branch('bmi','DamageMask');branch('bne','ProjectileMask');put(' lda.l $7EF100,x');branch('beq','DamageMask')
    label('ProjectileMask');put(' lda #52\n sta $06\n jmp DoAttackPrepare_Mask')
    label('DamageMask');put(' lda #48\n sta $06')
    label('Mask');put(' lda $00\n asl a\n asl a\n asl a\n asl a\n asl a\n sta $10\n asl a\n clc\n adc $10\n clc\n adc $06\n tax\n lda.l $40C000,x\n sta $12\n lda.l $40C002,x\n sta $14')
    put(' ldx $28\n ldy $2A\n jsl AttackIdentity_Assign');branch('bcs')
    # The allocation helper's actual Read/Write publishes the resulting ID.
    for off in (0,2):put(f' lda.l {h}+{28+off}\n sta ${22+off:02X}')
    put(f' lda.l {sy["SourceCollisionFrame4086_Attack"]}');branch('beq');put(f' cmp #{len(requirements["attacks"])+1}');branch('bcs')
    put(' dec a\n asl a\n asl a\n tax')
    for off in (0,2):put(f' lda.l DoAttackPrepare_Forces+{(code_bank<<16)+off},x\n sta ${26+off:02X}')
    for src,off in ((8,32),(18,36),(26,40),(22,48)):
        for half in (0,2):put(f' lda ${src+half:02X}\n sta.l {w}+{off+half}')
    for n,off in (('Handle',44),('Frame',46)):put(f' lda.l {sy["SourceCollisionFrame4086_"+n]}\n sta.l {w}+{off}')
    put(f' lda #$B6A4\n sta.l {w}+52\n lda $02\n sta.l {w}+54\n lda #{TARGET_LOOP_REQUIRED}\n jmp DoAttackPrepare_Good')
    label('Done');put(' lda #0')
    label('Good');put(f' tay\n tsc\n clc\n adc #{size}\n tcs\n tya\n pld\n ply\n plx\n plp\n clc\n rtl')
    label('Bad');put(f' tsc\n clc\n adc #{size}\n tcs\n pld\n ply\n plx\n plp\n sec\n rtl')
    label('Forces')
    for attack in requirements['attacks']:
        v=attack['attack_force'];put(' .dw '+str(v&65535)+','+str((v>>16)&65535))
    label('End')
    return '\n'.join(lines)+'\n'
