"""Native spawnplayer input reset using the already allocated source history rows.

A=index after source &3; X/Y=exclusive foreign generation. No constructor or
production consumer is installed. Exactly the two rings and combostep change.
"""
from source_player_input_4086 import ROW_BYTES,MAX_SPECIAL_INPUTS
from source_player_global_layout import layout as global_layout


def emit_weapon(sy):
    """Post-recovery set_weapon child; A=index, X/Y=foreign generation.

    Requires installed source weapon metadata and an idle model owner. Returns
    carry clear for an actual begun transition; State=1 still requires services,
    State=2 is the source same-model early return. Never synthesizes an Ack.
    """
    lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('SpawnWeapon_'+n+':\n.a16\n.i16')
    def guard(op):
        nonlocal serial
        serial+=1;k='SpawnWeapon_Guard'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+k+'\n jmp SpawnWeapon_Bad\n'+k+':\n.a16\n.i16')
    def require(name,value):put(f' lda.l {sy[name]}\n cmp #{value}');guard('bne')
    label('Begin');put(' php\n rep #$39\n pha\n phx\n phy\n phd\n tsc\n sec\n sbc #8\n tcs\n inc a\n tcd\n lda 15,s\n cmp #4');guard('bcs');put(' sta $00')
    put(f' jsl {sy["SourceForeignWork_Check"]}');guard('bcs');put(' jsl PlayerGlobal_Check');guard('bcs')
    for name,value in (('SourceSelf4086_Ready',0xb4f6),('SourceSelf4086_Active',0),('SourceSelf4086_Fault',0),('SourceSelf4086_GlobalHigh',0x41),('VmSourceWorld_Ready',0xb4a3),('VmSourceWorld_PoolBase',0x4000),('SourceModelTransition4086_Ready',0xb4f0)):
        require(name,value)
    put(f' jsl {sy["SourceModelTransition4086_CheckIdle"]}');guard('bcs')
    put(' lda $00\n asl a\n asl a\n tax');put(f' lda.l $43FD84,x\n cmp.l {sy["SourceSelf4086_GlobalLow"]}');guard('bne');put(' lda.l $43FD86,x\n cmp #$41');guard('bne')
    put(f' lda.l {sy["SourceSelf4086_GlobalLow"]}\n sec\n sbc #$4000');guard('bcc');put(' sta $02\n ldx #0')
    label('Slot');put(' cmp #80\n bcc SpawnWeapon_Found\n sec\n sbc #80\n inx\n bra SpawnWeapon_Slot')
    label('Found');put(' cmp #0');guard('bne');put(' txa');put(f' cmp.l {sy["VmSourceWorld_Count"]}');guard('bcs');put(f' sta.l {sy["SourceWeapon4086_Slot"]}\n sta.l {sy["SourceModelTransition4086_Slot"]}')
    put(' ldx $02\n lda.l $414004,x');guard('beq');put(' lda.l $414028,x\n cmp #1');guard('bne');put(' lda.l $41402A,x\n ora.l $41402E,x');guard('bne');put(' lda.l $41402C,x\n cmp $00');guard('bne')
    put(' lda $00\n asl a\n asl a\n tax\n lda.l $43EA00,x\n sta $04\n lda.l $43EA02,x\n sta $06\n ora $04\n bne SpawnWeapon_Saved')
    put(f' lda.l {sy["SourceWeapon4086_LevelWeaponLo"]}\n sta $04\n lda.l {sy["SourceWeapon4086_LevelWeaponHi"]}\n sta $06')
    label('Saved');put(f' lda $04\n sta.l {sy["SourceWeapon4086_NumberLo"]}\n lda $06\n sta.l {sy["SourceWeapon4086_NumberHi"]}\n lda #0\n sta.l {sy["SourceWeapon4086_AnimFlagLo"]}\n sta.l {sy["SourceWeapon4086_AnimFlagHi"]}\n jsl {sy["SourceWeapon4086_Resolve"]}');guard('bcs')
    put(f' lda.l {sy["SourceWeapon4086_Selected"]}\n sta.l {sy["SourceModelTransition4086_New"]}\n lda.l {sy["SourceWeapon4086_Sync"]}\n sta.l {sy["SourceModelAnimation4086_Sync"]}\n jsl {sy["SourceModelTransition4086_Begin"]}');guard('bcs')
    for name,carry in (('Good','clc'),('Bad','sec')):
        label(name);put(' tsc\n clc\n adc #8\n tcs\n pld\n ply\n plx\n pla\n plp\n '+carry+'\n rtl')
    return '\n'.join(lines)+'\n'


def emit_history_reset(rows,sy):
    if rows&255 or not 0<=rows<=0x1000000-4*ROW_BYTES or (rows&65535)>65536-4*ROW_BYTES:
        raise ValueError('SPAWN_HISTORY_LAYOUT')
    return f"""SpawnHistory_Reset:
.a16
.i16
 php
 rep #$39
 pha
 phx
 phy
 jsl {sy['SourceForeignWork_Check']}
 bcs SpawnHistory_Bad
 lda 5,s
 cmp #4
 bcs SpawnHistory_Bad
 xba
 tax
 ldy #{MAX_SPECIAL_INPUTS*4}
 lda #0
SpawnHistory_Clear:
.a16
.i16
 sta.l {rows},x
 inx
 inx
 dey
 bne SpawnHistory_Clear
 txa
 sec
 sbc #{MAX_SPECIAL_INPUTS*8}
 tax
 lda #0
 sta.l {rows+232},x
 sta.l {rows+234},x
 ply
 plx
 pla
 plp
 clc
 rtl
SpawnHistory_Bad:
.a16
.i16
 ply
 plx
 pla
 plp
 sec
 rtl
"""


def emit_recovery(tail,sy):
    """Post-constructor index, rings and exact signed health/MP recovery.

    A is the canonical player index; X/Y the foreign generation. The caller
    supplies an actual created entity as global self and the matching player
    role. Rush policy zero is admitted. Constructor and weapon children remain
    required; this routine does not acknowledge either child.
    """
    plan=global_layout(tail);players=plan['player_base'];lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('SpawnRecovery_'+n+':\n.a16\n.i16')
    def guard(op,n='Bad'):
        nonlocal serial
        serial+=1;k='SpawnRecovery_Guard'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc',bvs='bvc')[op]+' '+k+'\n jmp SpawnRecovery_'+n+'\n'+k+':\n.a16\n.i16')
    def require(at,value):put(f' lda.l {at}\n cmp #{value}');guard('bne')
    label('Apply');put(' php\n rep #$39\n pha\n phx\n phy\n phd\n tsc\n sec\n sbc #32\n tcs\n inc a\n tcd\n txa\n sta $1C\n tya\n sta $1E\n lda 39,s\n cmp #4');guard('bcs');put(' sta $00')
    put(f' jsl {sy["SourceForeignWork_Check"]}');guard('bcs');put(' jsl PlayerGlobal_Check');guard('bcs')
    for at,v in ((sy['VmSourceWorld_Ready'],0xb4a3),(sy['VmSourceWorld_PoolBase'],0x4000),
                 (sy['SourceSelf4086_Ready'],0xb4f6),(sy['SourceSelf4086_Active'],0),(sy['SourceSelf4086_Fault'],0),
                 (sy['SourceSelf4086_GlobalHigh'],0x41),(sy['SourceModelEntityCopy4086_Ready'],0xb4eb),
                 (plan['global_base']+8,0),(plan['global_base']+10,0)):require(at,v)
    put(f' lda.l {sy["VmSourceWorld_Count"]}');guard('beq');put(' cmp #129');guard('bcs');put(f' cmp.l {sy["SourceModelEntityCopy4086_Entities"]}');guard('bne')
    put(' lda $00\n asl a\n asl a\n tax');put(f' lda.l $43FD84,x\n cmp.l {sy["SourceSelf4086_GlobalLow"]}');guard('bne');require('$43FD86,x',0x41)
    put(' txa\n sta $06\n asl a\n asl a\n clc\n adc $06\n sta $06')
    put(f' lda.l {sy["SourceSelf4086_GlobalLow"]}\n sec\n sbc #$4000');guard('bcc');put(' sta $02\n ldx #0')
    label('FindSlot');put(' cmp #80');guard('bcc','Found');put(' sec\n sbc #80\n sta $04\n inx\n txa');put(f' cmp.l {sy["VmSourceWorld_Count"]}');guard('bcs');put(' lda $04\n jmp SpawnRecovery_FindSlot')
    label('Found');put(' cmp #0');guard('bne');put(' txa\n asl a\n asl a\n asl a\n asl a\n asl a\n sta $04\n asl a\n clc\n adc $04\n sta $04\n ldx $02')
    put(f' lda.l $414000,x\n cmp.l {sy["SourceSelf4086_GlobalLow"]}');guard('bne');require('$414002,x',0x41);put(' lda.l $414004,x');guard('beq');require('$414020,x',1);require('$414022,x',0)
    put(' ldx $04\n lda.l $40C048,x\n and #1');guard('beq');require('$40C04A,x',0)
    for name,saved,add,current,max_at,core in (('Health',8,5,36,60,False),('MP',12,2,76,64,True)):
        put(' ldx '+('$04'if core else'$02'))
        put(f' lda.l ${"40C000"if core else"414000"}+{current},x\n sta $08\n lda.l ${"40C000"if core else"414000"}+{current+2},x\n sta $0A\n ldx $06\n lda.l {players+saved},x\n sta $0C\n lda.l {players+saved+2},x\n sta $0E\n ora $0C');guard('beq',name+'Clamp')
        put(f' clc\n lda $0C\n adc #{add}\n sta $08\n lda $0E\n adc #0\n sta $0A');guard('bvs')
        label(name+'Clamp');put(f' ldx $04\n lda.l $40C000+{max_at+2},x\n eor #$8000\n sta $10\n lda $0A\n eor #$8000\n cmp $10');guard('bcc',name+'Done');guard('bne',name+'Maximum')
        put(f' lda $08\n cmp.l $40C000+{max_at},x');guard('bcc',name+'Done');guard('beq',name+'Done')
        label(name+'Maximum');put(f' lda.l $40C000+{max_at},x\n sta $08\n lda.l $40C000+{max_at+2},x\n sta $0A')
        label(name+'Done');put(' lda $08\n sta '+('$14'if core else'$18')+'\n lda $0A\n sta '+('$16'if core else'$1A'))
    put(' lda $00\n ldx $1C\n ldy $1E\n jsl SpawnHistory_Reset');guard('bcs')
    put(' ldx $02\n lda #1\n sta.l $414028,x\n lda #0\n sta.l $41402A,x\n sta.l $41402E,x\n lda $00\n sta.l $41402C,x\n lda $18\n sta.l $414024,x\n lda $1A\n sta.l $414026,x\n ldx $04\n lda $14\n sta.l $40C04C,x\n lda $16\n sta.l $40C04E,x')
    for name,carry in (('Good','clc'),('Bad','sec')):
        label(name);put(' tsc\n clc\n adc #32\n tcs\n pld\n ply\n plx\n pla\n plp\n '+carry+'\n rtl')
    return '\n'.join(lines)+'\n'
