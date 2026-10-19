"""Actual phase-8 attack gate over live source state and B4FC frame metadata.

Inactive gates reset the real source attack identity. Active attacks return an
explicit DO_ATTACK ticket and retain the world request. Hit resolution remains
mandatory and is not acknowledged here.
"""
from source_hit_state_layout import layout

DO_ATTACK=0x8108


def emit(plan,symbols):
    if plan.get('storage_profile')=='RETIRED_SCENE_VIDEO_STAGING':
        from source_hit_state_layout import rehost
        expected=rehost(plan['entities'],plan['base'])
    else:expected=layout(plan['entities'])
    if plan!=expected:raise ValueError('CHECK_ATTACK_NATIVE_PLAN')
    w=plan['controls'];lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('CheckAttack_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;l='CheckAttack_Guard'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+l+'\n jmp CheckAttack_'+n+'\n'+l+':\n.a16\n.i16')
    def load(name):put(f' lda.l {symbols[name]}')
    def require(name,value):load(name);put(f' cmp #{value}');branch('bne')
    label('Run');put(' php\n rep #$39\n phx\n phy')
    put(f' jsl {symbols["SourceForeignWork_Check"]}');branch('bcs')
    for n,v in (('SourceWorldTick4086_Ready',0xb4d5),('SourceWorldTick4086_State',1),('SourceWorldTick4086_Pending',1),('SourceWorldTick4086_Phase',8),('SourceWorldTick4086_Fault',0),('VmSourceWorld_Ready',0xb4a3),('VmSourceWorld_PoolBase',0x4000),('VmSourceWorld_SideBase',0x6800),('SourcePhysicsState4086_Ready',0xb61c),('SourceDamageEffectsState4086_Ready',0xb62f),('SourceFreeze4086_Ready',0xb5df),('SourceSelf4086_Ready',0xb4f6),('SourceSelf4086_Active',0),('SourceSelf4086_Fault',0),('SourceSelf4086_GlobalHigh',0x41)):
        require(n,v)
    put(f' jsl {symbols["SourceUpdateFrame4086_CheckIdle"]}');branch('bcs')
    put(f' jsl {symbols["SourceFrameStack4086_CheckIdle"]}');branch('bcs')
    for n,m in (('SourceWorldTick4086_TimeLo','VmSourceWorld_Time'),('SourceWorldTick4086_TimeHi','VmSourceWorld_Time')):
        load(n);put(f' cmp.l {symbols[m]+(2 if n.endswith("Hi")else 0)}');branch('bne')
    load('SourceWorldTick4086_Slot');put(f' sta.l {w}+4\n jsl HitState_Read');branch('bcs')
    load('SourceWorldTick4086_Slot');put(f' asl a\n asl a\n asl a\n asl a\n sta.l {w}+36')
    put(f' asl a\n asl a\n cmp.l {symbols["SourceWorldTick4086_Side"]}');branch('bne')
    put(f' clc\n adc.l {w}+36\n cmp.l {symbols["SourceWorldTick4086_View"]}');branch('bne')
    put(f' clc\n adc #$4000\n cmp.l {symbols["SourceSelf4086_GlobalLow"]}');branch('bne')
    put(f' tax\n cmp.l $410000,x');branch('bne');put(' lda.l $410002,x\n cmp #$41');branch('bne')
    put(' lda.l $410004,x\n ora.l $410006,x');branch('beq')
    # Canonical offsets: physics16, projectile24, combat20, freeze40, core96.
    put(f' lda.l {w}+36\n tax\n lda.l $42D800,x\n ora.l $42D802,x\n sta.l {w}+38')
    put(f' lda.l {w}+36\n lsr a\n clc\n adc.l {w}+36\n tax\n lda.l $7EF114,x\n cmp #$B62F');branch('bne')
    put(f' lda.l $7EF100,x\n ora.l $7EF102,x\n sta.l {w}+40')
    put(f' lda.l {w}+38');branch('beq','Drop');put(f' lda.l {w}+40');branch('beq','Reset')
    label('Drop');put(f' lda.l {w}+36\n lsr a\n lsr a\n clc\n adc.l {w}+36\n sta.l {w}+42\n tax\n lda.l $437E10,x\n cmp #$B5FB');branch('bne')
    put(f' lda.l $437E00,x\n ora.l $437E02,x');branch('beq','Freeze');put(f' lda.l {w}+38');branch('beq','Reset')
    label('Freeze');put(f' lda.l {w}+36\n asl a\n clc\n adc.l {w}+36\n asl a\n tax\n lda.l $40C04A,x');branch('bne','GlobalFreeze')
    put(' lda.l $40C048,x\n cmp #128');branch('beq','PersonalFreeze')
    label('GlobalFreeze');put(' lda.l $43FD98\n ora.l $43FD9A');branch('bne','Reset')
    put(' lda.l $43FD94\n ora.l $43FD96');branch('beq','PersonalFreeze')
    load('SourceSelf4086_GlobalLow');put(' cmp.l $43FD94');branch('bne','Reset')
    load('SourceSelf4086_GlobalHigh');put(' cmp.l $43FD96');branch('bne','Reset')
    label('PersonalFreeze');put(f' lda.l {w}+42\n asl a\n tax\n lda.l $42E000,x\n ora.l $42E002,x');branch('beq','Collision')
    put(f' lda.l $42E006,x\n cmp.l {symbols["VmSourceWorld_Time"]+2}');branch('bcc','Collision');branch('bne','Reset')
    put(f' lda.l $42E004,x\n cmp.l {symbols["VmSourceWorld_Time"]}');branch('bcc','Collision');branch('beq','Collision')
    put(' jmp CheckAttack_Reset')
    label('Collision');load('SourceWorldTick4086_Slot');put(f' jsl {symbols["SourceCollisionFrame4086_QueryEntity"]}');branch('bcs')
    load('SourceCollisionFrame4086_Attack');branch('beq','Reset')
    put(f' lda #{DO_ATTACK}\n sta.l {w}+24\n jmp CheckAttack_Good')
    label('Reset');put(' lda 3,s\n tax\n lda 1,s\n tay\n jsl HitState_ResetAttack');branch('bcs')
    put(f' lda #0\n sta.l {w}+24')
    label('Good');put(' ply\n plx\n plp\n clc\n rtl')
    label('Bad');put(' ply\n plx\n plp\n sec\n rtl')
    return '\n'.join(lines)+'\n'
