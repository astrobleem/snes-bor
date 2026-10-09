"""One-time source checkdamagedrop predecessor, exact reachable binary32 domain."""
from source_current_colourmap import layout
from source_hit_state_layout import layout as hits
from source_hit_contact_layout import layout as contacts
from source_hit_block_native import DAMAGE_REQUIRED
from dialect_4086 import GAME_SPEED


def emit(req,sy,code_bank=39,validate_only=False):
    if req['capability']!='SOURCE_ZERO_INITIAL_UNIT_KNOCKDOWN':raise ValueError('DAMAGE_DROP_CAPABILITY')
    w=layout()['controls'];h=hits()['controls'];c=contacts()['controls'];hb=hits()['base'];lines=[];serial=0;size=64
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('CombatDrop_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;l='CombatDrop_Guard'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc',bmi='bpl',bpl='bmi')[op]+f' {l}\n jmp CombatDrop_{n}\n{l}:\n.a16\n.i16')
    def require(at,v):put(f' lda.l {at}\n cmp #{v}');branch('bne')
    def offset(src,stride,dst):
        put(' lda #0\n sta $38')
        for bit in range(stride.bit_length()):
            if stride&(1<<bit):
                put(f' lda ${src:02X}');put('\n'.join(' asl a'for _ in range(bit)));put(' clc\n adc $38\n sta $38')
        put(f' lda $38\n sta ${dst:02X}')
    label('Run');put(f' php\n rep #$39\n phx\n phy\n phd\n tsc\n sec\n sbc #{size}\n tcs\n inc a\n tcd\n stx $3A\n sty $3C\n jsl HitBlock_Run');branch('bcs');put(f' cmp #{DAMAGE_REQUIRED}');branch('bne')
    require(sy['SourceFreeze4086_Ready'],0xb5df);require(sy['SourceDamageEffectsState4086_Ready'],0xb62f);require(w+40,0xb6ad);require(sy['SourceDamageState4086_Ready'],0xb62b);require(sy['SourceFactors4086_Ready'],0xb5f1)
    for off in (0,2):put(f' lda.l {w}+{12+off}\n cmp.l {sy["SourceWorldTick4086_TimeLo"]}+{off}');branch('bne')
    put(f' lda.l {h}+4\n sta $00\n cmp.l {w}+46');branch('bne')
    put(f' lda.l {w}+4\n sta $02\n cmp.l {c}+58');branch('bne');put(f' cmp.l {w}+48');branch('bne')
    offset(0,16,4);put(' tax')
    for off in (0,2):put(f' lda.l {hb}+{off},x\n cmp.l {w}+{56+off}');branch('bne')
    offset(0,64,4);put(' tax')
    for field,off in ((52,6),(54,4)):put(f' lda.l $416800+{off},x\n cmp.l {w}+{field}');branch('bne')
    put(f' lda #3\n sta.l {w}+24\n ldx $3A\n ldy $3C\n jsl CurrentPalette_Run');branch('bcs');put(f' lda.l {w}+36\n sta $06')
    offset(2,24,4);put(' tax\n lda.l $7EF114,x\n cmp #$B62F');branch('bne');put(' lda.l $7EF116,x\n cmp $06');branch('bne')
    offset(2,4,4);put(' tax\n lda.l $43B902,x\n cmp #$B5F1');branch('bne');put(' lda.l $43B900,x\n cmp $06');branch('bne')
    offset(2,80,4);put(' tax\n lda.l $43904A,x\n cmp #$B4FB');branch('bne');put(' lda.l $439048,x\n cmp $06');branch('bne');put(' lda.l $439040,x\n ora.l $439042,x');branch('bne')
    offset(2,32,4);put(' tax\n lda.l $432808,x');branch('bne');put(' lda.l $43280A,x\n cmp #$3F80');branch('bne')
    offset(2,20,8);put(' tax\n lda.l $437E10,x\n cmp #$B5FB');branch('bne');put(' lda.l $437E12,x');branch('bne')
    offset(2,12,10)
    put(f' lda.l {w}+44\n cmp #1');branch('beq','Good');put(' cmp #2');branch('beq','Good');put(' cmp #0');branch('bne')
    require(sy['SourceCollisionFrame4086_Bank'],58);require(sy['SourceCollisionFrame4086_Bytes'],req['effects']['collision_table_bytes'])
    put(f' lda.l {sy["SourceCollisionFrame4086_Status"]}\n cmp #3');branch('beq');put(f' lda #0\n sta.l {sy["SourceCollisionFrame4086_Status"]}\n lda $00\n jsl {sy["SourceCollisionFrame4086_QueryEntity"]}');branch('bcs')
    put(f' lda.l {sy["SourceCollisionFrame4086_Attack"]}\n cmp.l {w}+50');branch('bne');put(' cmp #1');branch('bcc');put(f' cmp #{len(req["effects"]["attacks"])+1}');branch('bcs');put(' dec a\n asl a\n asl a\n tax')
    put(f' lda.l CombatDrop_Attacks+{code_bank<<16},x\n sta $0C\n lda.l CombatDrop_Attacks+{(code_bank<<16)+2},x\n sta $0E')
    put(' lda $08\n tax\n lda.l $437E00,x\n ora.l $437E02,x');branch('bne','CommitType')
    put(' lda $0A\n tax\n lda.l $7FB900,x\n sta $10\n lda.l $7FB902,x\n sta $12')
    # Reset on strictly expired nonzero unsigned timer; equality is not expired.
    put(' lda.l $7FB904,x\n ora.l $7FB906,x');branch('beq','Counter')
    put(f' lda.l $7FB906,x\n cmp.l {w}+14');branch('bcc','Reset');branch('bne','Counter');put(f' lda.l $7FB904,x\n cmp.l {w}+12');branch('bcc','Reset');put(' jmp CombatDrop_Counter')
    label('Reset');put(' lda #0\n sta $10\n sta $12')
    label('Counter');put(' lda $10\n ora $12');branch('beq','Zero')
    put(' lda $12');branch('bpl');put(' and #$7F80\n cmp #$3F80');branch('bcc');put(' cmp #$4B80');branch('bcs','Limit')
    put(' sec\n sbc #$3F80\n lsr a\n lsr a\n lsr a\n lsr a\n tax')
    for off,dst in ((0,20),(2,22),(4,24),(6,26)):put(f' lda.l CombatDrop_Steps+{(code_bank<<16)+off},x\n sta ${dst:02X}')
    put(' lda $10\n and $18\n sta $1C\n lda $12\n and $1A\n ora $1C');branch('bne')
    put(' lda $0C');branch('beq','WriteCounter')
    put(' lda $10\n clc\n adc $14\n sta $10\n lda $12\n adc $16\n sta $12\n jmp CombatDrop_WriteCounter')
    label('Limit');put(' lda $10');branch('bne');put(' lda $12\n cmp #$CB80');branch('bne');put(' jmp CombatDrop_WriteCounter')
    label('Zero');put(' lda $0C');branch('beq','WriteCounter');put(' lda #$BF80\n sta $12')
    label('WriteCounter');
    if validate_only:put(' jmp CombatDrop_Good')
    put(' lda $0A\n tax\n lda $10\n sta.l $7FB900,x\n lda $12\n sta.l $7FB902,x')
    put(f' lda.l {w}+12\n clc\n adc #{GAME_SPEED}\n sta.l $7FB904,x\n lda.l {w}+14\n adc #0\n sta.l $7FB906,x')
    put(' lda $12\n and #$8000\n beq CombatDrop_NoDrop\n lda #1\n bra CombatDrop_Drop\nCombatDrop_NoDrop:\n.a16\n.i16\n lda #0\nCombatDrop_Drop:\n.a16\n.i16\n ldx $08\n sta.l $437E00,x\n lda #0\n sta.l $437E02,x')
    label('CommitType');
    if validate_only:put(' jmp CombatDrop_Good')
    put(f' ldx $0A\n lda $0E\n sta.l $7FB908,x\n lda #0\n sta.l $7FB90A,x\n lda #1\n sta.l {w}+44')
    for name,status,carry in (('Good',2,'clc'),('Bad',3,'sec')):
        label(name);put(f' lda #{status}\n sta.l {w}+42\n tay\n tsc\n clc\n adc #{size}\n tcs\n tya\n pld\n ply\n plx\n plp\n {carry}\n rtl')
    label('Attacks')
    for a in req['effects']['attacks']:put(' .dw '+str(a['attack_drop'])+','+str(a['attack_type']if 0<=a['attack_type']<req['attack_types']else 0))
    label('Steps')
    for exponent in range(127,151):
        step=1<<(150-exponent);mask=step-1
        put(' .dw '+','.join(str(v)for v in (step&65535,step>>16,mask&65535,mask>>16)))
    return ('\n'.join(lines)+'\n').replace('CombatDrop_','CombatDropValidate_')if validate_only else'\n'.join(lines)+'\n'
