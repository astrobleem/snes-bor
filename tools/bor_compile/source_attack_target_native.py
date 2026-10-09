"""Read live source target state, then execute real normal/counter collision.

Only target admission/contact is provided; callers must execute source callbacks,
actual damage and followup services before acknowledging world phase8.
"""
from source_hit_contact_layout import layout
from source_engine_function_ids import function_id


def emit(requirements,plan,sy,code_bank=39,collision_bank=58):
    if plan!=layout(plan['entities'])or requirements['capability']!='SOURCE_NONPOSITIVE_ATTACKONE_TARGET_FILTER':raise ValueError('ATTACK_TARGET_NATIVE_REQUIREMENTS')
    if not 0<=code_bank<64 or not 0<=collision_bank<64:raise ValueError('ATTACK_TARGET_NATIVE_CODE_BANK')
    from source_hit_state_layout import layout as hits
    hp=hits(plan['entities']);h=hp['controls'];w=plan['controls'];lines=[];serial=0;size=64
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('AttackTarget_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;l='AttackTarget_Guard'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc',bpl='bmi',bmi='bpl')[op]+' '+l+'\n jmp AttackTarget_'+n+'\n'+l+':\n.a16\n.i16')
    def require(n,v):put(f' lda.l {sy[n]}\n cmp #{v}');branch('bne')
    def offset(slot,mult,dst):
        put(f' lda ${slot:02X}\n sta ${dst:02X}\n lda #0\n sta ${dst+2:02X}')
        # Small generic constant products avoid a mutable multiplication unit.
        for bit in range(mult.bit_length()):
            if mult&(1<<bit):
                put(f' lda ${slot:02X}')
                for _ in range(bit):put(' asl a')
                put(f' clc\n adc ${dst+2:02X}\n sta ${dst+2:02X}')
        put(f' lda ${dst+2:02X}\n sta ${dst:02X}')
    label('Run');put(f' php\n rep #$39\n phx\n phy\n phd\n tsc\n sec\n sbc #{size}\n tcs\n inc a\n tcd\n stx $38\n sty $3A')
    put(f' jsl {sy["SourceForeignWork_Check"]}');branch('bcs')
    for n,v in (('SourceWorldTick4086_Ready',0xb4d5),('SourceWorldTick4086_State',1),('SourceWorldTick4086_Pending',1),('SourceWorldTick4086_Phase',8),('SourceWorldTick4086_Fault',0),('SourceModelEntityCopy4086_Ready',0xb4eb),('SourceLifecycle4086_Ready',0xb4fb),('SourcePhysicsState4086_Ready',0xb61c),('SourceDamageEffectsState4086_Ready',0xb62f),('SourceCollisionFrame4086_Ready',0xb5ee)):
        require(n,v)
    require('SourceCollisionFrame4086_Bank',collision_bank)
    require('SourceCollisionFrame4086_Bytes',requirements['collision_table_bytes'])
    for n in ('SourceModelEntityCopy4086_Models','SourceLifecycle4086_Models'):require(n,requirements['model_count'])
    require('SourceModelEntityCopy4086_Entities',plan['entities'])
    put(f' lda.l {h}+4\n sta $00\n cmp.l {sy["SourceWorldTick4086_Slot"]}');branch('bne')
    for off,n in ((0,'Lo'),(2,'Hi')):
        put(f' lda.l {sy["SourceWorldTick4086_Time"+n]}\n cmp.l {sy["VmSourceWorld_Time"]+off}');branch('bne')
    offset(0,80,16);put(f' lda $10\n cmp.l {sy["SourceWorldTick4086_View"]}');branch('bne')
    offset(0,64,16);put(f' lda $10\n cmp.l {sy["SourceWorldTick4086_Side"]}');branch('bne')
    put(' ldx $38\n ldy $3A\n jsl HitState_Read');branch('bcs')
    for off in (0,2):put(f' lda.l {h}+{28+off}\n sta ${8+off:02X}')
    put(' lda $08\n ora $0A');branch('beq')
    put(f' lda.l {h}+26\n cmp #{plan["entities"]}');branch('bcs');put(' sta $02\n cmp $00');branch('beq','Miss')
    offset(2,80,16);put(' lda $10\n clc\n adc #$4000\n tax\n sta $14\n lda.l $410004,x\n ora.l $410006,x');branch('beq','Miss')
    put(' txa\n cmp.l $410000,x');branch('bne');put(' lda.l $410002,x\n cmp #$41');branch('bne')
    offset(2,80,16);put(' lda $10\n tax\n lda.l $43904A,x\n cmp #$B4FB');branch('bne')
    put(f' lda.l $439048,x\n cmp #{requirements["model_count"]}');branch('bcs');put(' sta $3C')
    offset(2,64,16);put(' lda $10\n tax\n lda.l $416800,x\n cmp $3C');branch('bne')
    offset(2,80,16);put(' lda $10\n tax')
    put(' lda.l $439014,x\n ora.l $439016,x');branch('bne','Miss')
    put(' lda.l $439018,x\n cmp #1');branch('bne','NotInvincible');put(' lda.l $43901A,x');branch('bne','NotInvincible');put(' lda #1\n sta $0C\n jmp AttackTarget_AttackFrame')
    label('NotInvincible');put(' lda #0\n sta $0C')
    label('AttackFrame');put(f' lda.l {sy["SourceCollisionFrame4086_Status"]}\n cmp #3');branch('beq')
    put(f' lda #0\n sta.l {sy["SourceCollisionFrame4086_Status"]}\n lda $00\n jsl {sy["SourceCollisionFrame4086_QueryEntity"]}');branch('bcs')
    put(f' lda.l {sy["SourceCollisionFrame4086_Attack"]}');branch('beq');put(f' cmp #{len(requirements["attacks"])+1}');branch('bcs')
    put(' dec a\n asl a\n asl a\n asl a\n asl a\n tax\n stx $04')
    for off,dst in ((0,24),(4,28),(8,32),(12,36)):
        for half in (0,2):put(f' lda.l AttackTarget_Attacks+{(code_bank<<16)+off+half},x\n sta ${dst+half:02X}')
    put(' lda $0C');branch('beq','Mask');put(' lda $18\n cmp #15');branch('bne','Miss');put(' lda $1A');branch('bne','Miss')
    label('Mask');offset(0,24,16);put(' lda $10\n tax\n lda.l $7EF114,x\n cmp #$B62F');branch('bne')
    put(' lda.l $7EF102,x');branch('bmi','DamageMask');branch('bne','ProjectileMask')
    put(' lda.l $7EF100,x');branch('beq','DamageMask')
    label('ProjectileMask');offset(0,96,16);put(' lda $10\n tax\n lda.l $40C034,x\n sta $2C\n lda.l $40C036,x\n sta $2E\n jmp AttackTarget_TargetType')
    label('DamageMask');offset(0,96,16);put(' lda $10\n tax\n lda.l $40C030,x\n sta $2C\n lda.l $40C032,x\n sta $2E')
    label('TargetType');offset(2,96,16);put(' lda $10\n tax\n lda.l $40C048,x\n and $2C\n sta $30\n lda.l $40C04A,x\n and $2E\n ora $30');branch('beq','Miss')
    # Paired target storage queries; restore attacker slot before any return.
    put(f' lda $02\n sta.l {h}+4\n sta.l {w}+4\n ldx $38\n ldy $3A\n jsl HitContact_Read\n php\n lda $00\n sta.l {h}+4\n plp');branch('bcs')
    for off in (0,2):put(f' lda.l {w}+{24+off}\n sta ${40+off:02X}')
    put(f' lda $2A\n cmp.l {sy["VmSourceWorld_Time"]+2}');branch('bcc','PainOK');branch('bne','Miss');put(f' lda $28\n cmp.l {sy["VmSourceWorld_Time"]}');branch('bcs','Miss')
    label('PainOK');offset(2,80,16);put(' lda $10\n tax\n lda.l $439004,x\n ora.l $439006,x');branch('beq','Miss')
    put(f' lda.l {h}+32\n cmp $08');branch('bne','HitIDOK');put(f' lda.l {h}+34\n cmp $0A');branch('beq','Miss')
    label('HitIDOK');put(f' lda.l $43900C,x\n cmp #{function_id("common_lie")}');branch('bne','Standing');put(' lda.l $43900E,x');branch('bne','Standing')
    # Lying requires OTG>=BOTH; standing requires OTG<GROUND_ONLY, signed32.
    put(' lda $1E');branch('bmi','Miss');branch('bne','Juggle');put(' lda $1C\n cmp #1');branch('bcc','Miss');put(' jmp AttackTarget_Juggle')
    label('Standing');put(' lda $1E');branch('bmi','Juggle');branch('bne','Miss');put(' lda $1C\n cmp #2');branch('bcs','Miss')
    label('Juggle');offset(2,16,16);put(' lda $10\n tax\n lda.l $42D802,x');branch('bne','Miss');put(' lda.l $42D800,x');branch('beq','Grounded');put(' cmp #1');branch('bne','Miss')
    put(f' lda.l {w}+30\n eor #$8000\n sta $30\n lda $22\n eor #$8000\n cmp $30');branch('bcc','Collision');branch('bne','Miss')
    put(f' lda $20\n cmp.l {w}+28');branch('bcc','Collision');branch('beq','Collision');put(' jmp AttackTarget_Miss')
    label('Grounded');put(' lda $22');branch('bmi','Miss')
    label('Collision');put(f' lda #0\n sta.l {h}+24\n ldx $38\n ldy $3A\n jsl CheckHit_Run');branch('bcs');put(' cmp #0');branch('bne','Hit')
    put(' lda $24\n ora $26');branch('beq','Miss');put(f' lda #1\n sta.l {h}+24\n ldx $38\n ldy $3A\n jsl CheckHit_Run');branch('bcs');put(' cmp #0');branch('bne','Hit')
    label('Miss');put(' lda #0\n jmp AttackTarget_Good');label('Hit');put(' lda #1')
    label('Good');put(f' tay\n tsc\n clc\n adc #{size}\n tcs\n tya\n pld\n ply\n plx\n plp\n clc\n rtl')
    label('Bad');put(f' tsc\n clc\n adc #{size}\n tcs\n pld\n ply\n plx\n plp\n sec\n rtl')
    label('Attacks')
    for attack in requirements['attacks']:
        values=[attack[k]for k in ('attack_type','otg','jugglecost','counterattack')]
        put(' .dw '+','.join(str((v>>half)&65535)for v in values for half in (0,16)))
    label('End')
    return '\n'.join(lines)+'\n'
