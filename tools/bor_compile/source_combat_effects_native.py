"""One-time source freeze/unfreeze, palette identity and scalar damage effects.

Requires actual target/collision/prelude/block selection with a DAMAGE ticket.
It does not perform preceding damagedrop or subsequent health/action services.
Current palette control tail +40..63 holds the contact snapshot and state.
"""
from source_current_colourmap import layout as colours
from source_hit_contact_layout import layout as contacts
from source_hit_state_layout import layout as hits
from source_hit_block_native import DAMAGE_REQUIRED


def emit(req,sy,code_bank=39,damagedrop=False):
    if req['capability']!='SOURCE_FREEZE_UNFREEZE_NO_STEAL_SEAL_DOT':raise ValueError('COMBAT_EFFECTS_CAPABILITY')
    plan=colours();w=plan['controls'];c=contacts()['controls'];h=hits()['controls'];hb=hits()['base'];lines=[];serial=0;size=64
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('CombatEffects_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;l='CombatEffects_Guard'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+f' {l}\n jmp CombatEffects_{n}\n{l}:\n.a16\n.i16')
    def require(at,v):put(f' lda.l {at}\n cmp #{v}');branch('bne')
    def offset(src,stride,dst):
        put(f' lda ${src:02X}\n asl a\n asl a')
        if stride in (16,64,80):
            if stride==80:put(' asl a\n asl a\n sta $38\n asl a\n asl a\n clc\n adc $38')
            else:put('\n'.join(' asl a'for _ in range(stride.bit_length()-3)))
        elif stride in (20,24,40):
            if stride!=20:put(' asl a')
            put(' sta $38\n asl a')
            if stride in (20,40):put(' asl a')
            put(' clc\n adc $38')
        else:raise ValueError('COMBAT_EFFECTS_OFFSET')
        put(f' sta ${dst:02X}')
    label('Run');put(f' php\n rep #$39\n phx\n phy\n phd\n tsc\n sec\n sbc #{size}\n tcs\n inc a\n tcd\n stx $3A\n sty $3C')
    put(' jsl HitBlock_Run');branch('bcs');put(f' cmp #{DAMAGE_REQUIRED}');branch('bne')
    require(w+40,0xb6ad);require(sy['SourceFreeze4086_Ready'],0xb5df);require(sy['SourceDamageEffectsState4086_Ready'],0xb62f)
    for off in (0,2):put(f' lda.l {w}+{12+off}\n cmp.l {sy["SourceWorldTick4086_TimeLo"]}+{off}');branch('bne')
    put(f' lda.l {h}+4\n sta $00\n cmp.l {w}+46');branch('bne')
    put(f' lda.l {w}+4\n sta $02\n cmp.l {c}+58');branch('bne');put(f' cmp.l {w}+48');branch('bne')
    offset(0,16,4);put(' tax')
    for off in (0,2):put(f' lda.l {hb}+{off},x\n cmp.l {w}+{56+off}');branch('bne')
    offset(0,64,4);put(' tax')
    for field,off in ((52,6),(54,4)):put(f' lda.l $416800+{off},x\n cmp.l {w}+{field}');branch('bne')
    # Validate independent current palette state before any actor mutation.
    put(f' lda #3\n sta.l {w}+24\n ldx $3A\n ldy $3C\n jsl CurrentPalette_Run');branch('bcs')
    put(f' lda.l {w}+36\n sta $06')
    offset(2,24,8);put(' tax\n lda.l $7EF114,x\n cmp #$B62F');branch('bne');put(' lda.l $7EF116,x\n cmp $06');branch('bne')
    offset(2,20,10);put(' tax\n lda.l $437E10,x\n cmp #$B5FB');branch('bne')
    put(f' lda.l {w}+44\n cmp #2');branch('beq','Good');put(' cmp #'+str(1 if damagedrop else 0));branch('bne')
    require(sy['SourceCollisionFrame4086_Bank'],58);require(sy['SourceCollisionFrame4086_Bytes'],req['collision_table_bytes'])
    put(f' lda.l {sy["SourceCollisionFrame4086_Status"]}\n cmp #3');branch('beq');put(f' lda #0\n sta.l {sy["SourceCollisionFrame4086_Status"]}\n lda $00\n jsl {sy["SourceCollisionFrame4086_QueryEntity"]}');branch('bcs')
    put(f' lda.l {sy["SourceCollisionFrame4086_Attack"]}\n cmp.l {w}+50');branch('bne');put(' cmp #1');branch('bcc');put(f' cmp #{len(req["attacks"])+1}');branch('bcs')
    put(' dec a\n asl a\n asl a\n asl a\n asl a\n tax')
    for off,dst in ((0,12),(2,14),(4,16),(6,18),(8,20),(10,22),(12,24),(14,26)):
        put(f' lda.l CombatEffects_Attacks+{(code_bank<<16)+off},x\n sta ${dst:02X}')
    put(' lda $06\n asl a\n asl a\n tax')
    for off,dst in ((0,28),(2,30)):put(f' lda.l CombatEffects_Models+{(code_bank<<16)+off},x\n sta ${dst:02X}')
    offset(2,40,32);put(' tax\n lda.l $42E000,x\n ora.l $42E002,x\n sta $22')
    offset(2,64,4);put(' tax\n lda.l $416830,x\n sta $24\n lda.l $416832,x\n sta $26')
    offset(2,80,4);put(' tax\n lda.l $414008,x\n cmp #2');branch('bne');put(' lda.l $41400A,x');branch('bne')
    for off,n in ((0,'Lo'),(2,'Hi')):put(f' lda.l $41400C+{off},x\n sta.l {sy["SourceModelEntityCopy4086_"+n]}\n lda ${36+off:02X}\n sta.l {sy["SourceDefaultPlayer4086_Inv"+n]}')
    # Source Q16 helper compares y/base; base was saved at DP24/26.
    put(f' lda $24\n sta.l {sy["SourceDefaultPlayer4086_InvLo"]}\n lda $26\n sta.l {sy["SourceDefaultPlayer4086_InvHi"]}\n jsl {sy["SourceInAir4086_Q16Compatibility"]}\n sta $2C')
    put(' lda $0A\n tax\n lda.l $437E00,x\n sta $28\n lda.l $437E02,x\n sta $2A')
    put(' lda $0C\n ora $0E');branch('beq','WasFrozen');put(' lda $22');branch('bne','WasFrozen')
    # New freeze: select actual source map without changing restore map.
    put(' lda $10\n cmp #$FFFF');branch('bne','FreezePaletteDone');put(' lda $12\n cmp #$FFFF');branch('bne','FreezePaletteDone')
    put(' lda $1C\n cmp #$FFFF');branch('bne','FreezePalette');put(' lda $1E\n cmp #$FFFF');branch('beq','FreezePaletteDone')
    label('FreezePalette')
    for off in (0,2):put(f' lda ${28+off:02X}\n sta.l {w}+{28+off}')
    put(f' lda #2\n sta.l {w}+24\n ldx $3A\n ldy $3C\n jsl CurrentPalette_Run');branch('bcs')
    label('FreezePaletteDone');put(' lda $20\n tax\n lda #1\n sta.l $42E000,x\n lda #0\n sta.l $42E002,x\n sta $28\n sta $2A\n lda.l $42E004,x\n ora.l $42E006,x');branch('bne','DropPolicy')
    put(f' lda.l {w}+12\n clc\n adc $14\n sta.l $42E004,x\n lda.l {w}+14\n adc $16\n sta.l $42E006,x\n jmp CombatEffects_DropPolicy')
    label('WasFrozen');put(' lda $22');branch('beq','DropPolicy')
    put(f' lda #4\n sta.l {w}+24\n ldx $3A\n ldy $3C\n jsl CurrentPalette_Run');branch('bcs')
    put(' lda $20\n tax\n lda #0\n sta.l $42E000,x\n sta.l $42E002,x\n sta.l $42E004,x\n sta.l $42E006,x\n lda #1\n sta $28\n lda #0\n sta $2A')
    label('DropPolicy')
    # Models table holds fmap then nodrop; fetch signed nodrop independently.
    put(' lda $06\n asl a\n asl a\n tax');put(f' lda.l CombatEffects_NoDrop+{code_bank<<16},x\n sta $30\n lda.l CombatEffects_NoDrop+{(code_bank<<16)+2},x\n sta $32\n ora $30');branch('beq','Air');put(' lda #0\n sta $28\n sta $2A')
    label('Air');put(' lda $2C');branch('beq','Commit');put(' lda $20\n tax\n lda.l $42E000,x\n ora.l $42E002,x');branch('bne','Commit')
    put(' lda $32');branch('bne','SignedNoDrop');put(' lda $30\n cmp #2');branch('bcs','Commit');put(' jmp CombatEffects_DropAir')
    label('SignedNoDrop');put(' lda $32\n and #$8000');branch('beq','Commit')
    label('DropAir');put(' lda #1\n sta $28\n lda #0\n sta $2A')
    label('Commit');put(' lda $0A\n tax\n lda $28\n sta.l $437E00,x\n lda $2A\n sta.l $437E02,x\n lda $08\n tax\n lda #0\n sta.l $7EF100,x\n sta.l $7EF102,x\n lda $28\n ora $2A');branch('beq','Complete')
    # This capability admits only source zero staydown rise/riseattack.
    put(' lda #0\n sta.l $7EF104,x\n sta.l $7EF106,x\n sta.l $7EF108,x\n sta.l $7EF10A,x')
    label('Complete');put(f' lda #2\n sta.l {w}+44')
    for name,status,carry in (('Good',2,'clc'),('Bad',3,'sec')):
        label(name);put(f' lda #{status}\n sta.l {w}+42\n tay\n tsc\n clc\n adc #{size}\n tcs\n tya\n pld\n ply\n plx\n plp\n {carry}\n rtl')
    label('Attacks')
    for a in req['attacks']:
        if any(a['staydown'][:2]):raise ValueError('COMBAT_EFFECTS_STAYDOWN_BODY_REQUIRED')
        vals=(a['freeze'],a['forcemap'],a['freezetime'],0)
        put(' .dw '+','.join(str(v&65535)+','+str((v>>16)&65535)for v in vals))
    for name,field in (('Models','frozen_map'),('NoDrop','nodrop')):
        label(name);put(' .dw '+','.join(str(m[field]&65535)+','+str((m[field]>>16)&65535)for m in req['models']))
    return '\n'.join(lines)+'\n'
