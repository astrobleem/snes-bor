"""Closed source pre-block side effects and live blocking branch choice.

Requires a real accepted collision/prelude. It changes source bomb flags,
consumes actual rand32 only at its source checkpoint, and suspends before the
selected action body. No fabricated damage response or world acknowledgement.
"""
from source_hit_contact_layout import layout
from source_hit_state_layout import layout as hits
PASSIVE_BLOCK_REQUIRED=0x8113
ACTIVE_BLOCK_REQUIRED=0x8114
DAMAGE_REQUIRED=0x8115


def emit(req,plan,sy,code_bank=39):
    if plan!=layout(plan['entities']) or req['capability']!='SOURCE_DEFAULT_BLOCK_PROPERTIES_NO_COUNTER':raise ValueError('HIT_BLOCK_NATIVE_REQUIREMENTS')
    w=plan['controls'];h=hits(plan['entities'])['controls'];lines=[];serial=0;size=64
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('HitBlock_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;l='HitBlock_Guard'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc',bmi='bpl',bpl='bmi')[op]+f' {l}\n jmp HitBlock_{n}\n{l}:\n.a16\n.i16')
    def require(at,v):put(f' lda.l {at}\n cmp #{v}');branch('bne')
    def offset(src,stride,dst):
        put(f' lda ${src:02X}')
        if stride==80:put(' asl a\n asl a\n asl a\n asl a\n sta $24\n asl a\n asl a\n clc\n adc $24')
        elif stride==96:put(' asl a\n asl a\n asl a\n asl a\n asl a\n sta $24\n asl a\n clc\n adc $24')
        elif stride==40:put(' asl a\n asl a\n asl a\n sta $24\n asl a\n asl a\n clc\n adc $24')
        elif stride==24:put(' asl a\n asl a\n asl a\n sta $24\n asl a\n clc\n adc $24')
        elif stride in (4,16,32,64):put('\n'.join(' asl a'for _ in range(stride.bit_length()-1)))
        else:raise ValueError('HIT_BLOCK_OFFSET')
        put(f' sta ${dst:02X}')
    label('Run');put(f' php\n rep #$39\n phx\n phy\n phd\n tsc\n sec\n sbc #{size}\n tcs\n inc a\n tcd\n stx $38\n sty $3A')
    put(f' jsl {sy["SourceForeignWork_Check"]}');branch('bcs')
    for at,v in ((w,0xb6a3),(w+52,0xb6a4),(h,0xb6a0),(h+40,1),(h+42,0xb6a7),
                 (sy['SourceWorldTick4086_Ready'],0xb4d5),(sy['SourceWorldTick4086_State'],1),(sy['SourceWorldTick4086_Phase'],8),(sy['SourceWorldTick4086_Pending'],1),(sy['SourceWorldTick4086_Fault'],0),
                 (sy['SourceSelf4086_Ready'],0xb4f6),(sy['SourceSelf4086_Fault'],0),(sy['SourceSelf4086_GlobalHigh'],0x41)):
        require(at,v)
    for op,off in (('txa',8),('tya',10)):
        put(f' {op}\n cmp.l {w}+{off}');branch('bne');put(f' cmp.l {h}+{off}');branch('bne')
    for off in (0,2):put(f' lda.l {sy["SourceWorldTick4086_TimeLo"]}+{off}\n cmp.l {sy["VmSourceWorld_Time"]}+{off}');branch('bne')
    put(f' lda.l {h}+4\n cmp.l {sy["SourceWorldTick4086_Slot"]}');branch('bne');put(f' cmp.l {sy["VmSourceWorld_Count"]}');branch('bcs');put(' sta $00')
    require(h+38,0x41);require(sy['SourceRetirement4086_Ready'],0xb4f8)
    for off,n in ((0,'Lo'),(2,'Hi')):put(f' lda.l {h}+{36+off}\n sta.l {sy["SourceRetirement4086_Arg"+n]}')
    put(f' jsl {sy["SourceRetirement4086_ResolvePointer"]}');branch('bcs');put(' cmp #$FFFF');branch('beq')
    put(f' lda.l {h}+36\n tax\n cmp.l $410000,x');branch('bne');put(' lda.l $410002,x\n cmp #$41');branch('bne')
    put(f' lda.l {w}+58\n cmp.l {h}+26');branch('bne');put(f' cmp.l {sy["VmSourceWorld_Count"]}');branch('bcs');put(' sta $02')
    offset(2,80,4);put(f' lda $04\n clc\n adc #$4000\n cmp.l {sy["SourceSelf4086_GlobalLow"]}');branch('bne')
    put(f' lda.l {w}+60\n cmp #5');branch('beq','Retained');put(' cmp #4');branch('bne')
    for at,v in ((sy['SourceFactors4086_Ready'],0xb5f1),(sy['SourceFactors4086_Models'],len(req['models'])),
                 (sy['SourceModelAnimationCopy4086_Ready'],0xb4e9),(sy['SourceModelAnimationCopy4086_Models'],len(req['models'])),
                 (sy['SourceModelAnimationCopy4086_Maximum'],req['maximum_animations']),(sy['SourceModelAnimationCopy4086_RowBytes'],req['maximum_animations']*2)):
        require(at,v)
    put(f' lda.l {sy["SourceModelAnimationCopy4086_Bytes"]}\n cmp #{len(req["models"])*req["maximum_animations"]*2}');branch('bcc');put(' cmp #8193');branch('bcs')
    # Both actual immutable vectors are zero at the source threshold fields.
    # Target model pairing also prevents consuming an unrelated actor vector.
    for src in (0,2):
        offset(src,64,4);put(' tax\n lda.l $416800,x\n sta $06')
        put(f' cmp #{len(req["models"])}');branch('bcs')
        offset(src,4,4);put(' tax\n lda.l $43B902,x\n cmp #$B5F1');branch('bne');put(' lda.l $43B900,x\n cmp $06');branch('bne')
        offset(src,32,4);put(' tax\n lda.l $43280C,x\n ora.l $43280E,x');branch('bne')
        if src==2:put(' lda.l $432804,x\n ora.l $432806,x');branch('bne')
    # Validate unchanged captured attack cursor, then query its actual metadata.
    offset(0,64,4);put(f' tax\n lda.l $416804,x\n cmp.l {w}+44');branch('bne');put(f' lda.l $416806,x\n cmp.l {w}+46');branch('bne')
    require(sy['SourceCollisionFrame4086_Bank'],58);require(sy['SourceCollisionFrame4086_Bytes'],req['collision_table_bytes'])
    put(f' lda.l {sy["SourceCollisionFrame4086_Status"]}\n cmp #3');branch('beq')
    put(f' lda #0\n sta.l {sy["SourceCollisionFrame4086_Status"]}\n lda $00\n jsl {sy["SourceCollisionFrame4086_QueryEntity"]}');branch('bcs')
    put(f' lda.l {sy["SourceCollisionFrame4086_Attack"]}');branch('beq');put(f' cmp #{len(req["attacks"])+1}');branch('bcs')
    put(' dec a\n asl a\n asl a\n tax')
    for off in (0,2):put(f' lda.l HitBlock_NoBlock+{(code_bank<<16)+off},x\n sta ${8+off:02X}')
    # Current cached-model pointer may be inherited from another source model.
    # The shared immutable handle retains its source numframes.
    offset(2,64,4);put(' tax\n lda.l $416800,x\n sta $06\n asl a\n asl a\n asl a\n asl a\n sta $24\n asl a\n asl a\n asl a\n asl a\n clc\n adc $24\n sta $0C\n lda $06\n asl a\n asl a\n asl a\n asl a\n asl a\n asl a\n clc\n adc $0C\n tax')
    put(f' lda.l $43C000+{req["block_role"]*2},x\n sta $0E')
    put(' lda #0\n sta $10')
    put(' lda $0E');branch('beq','BlockValidated');put(f' cmp #{len(req["animations"])+1}');branch('bcs')
    put(f' asl a\n tax\n lda.l HitBlock_FrameCounts+{code_bank<<16},x\n sta $10')
    label('BlockValidated')
    # Read real integer directions, flags, AI policy, relation and signed busy.
    for src,dst in ((0,18),(2,22)):
        offset(src,80,4);put(' tax\n lda.l $414018,x\n cmp #1');branch('bne');put(' lda.l $41401A,x');branch('bne')
        for off in (0,2):put(f' lda.l $41401C+{off},x\n sta ${dst+off:02X}')
    put(' lda $12\n cmp $16');branch('bne','Front');put(' lda $14\n cmp $18');branch('bne','Front');put(' lda #1\n jmp HitBlock_Facing')
    label('Front');put(' lda #0')
    label('Facing');put(' sta $18')
    offset(2,24,4);put(' tax\n lda.l $42F408,x\n ora.l $42F40A,x\n sta $1A')
    for off in (0,2):put(f' lda.l $42F40C+{off},x\n sta ${28+off:02X}')
    offset(2,40,4);put(' tax\n lda.l $42E000,x\n ora.l $42E002,x\n sta $20')
    offset(2,32,4);put(' tax\n lda.l $43EB0C,x\n ora.l $43EB0E,x\n sta $22')
    put(' lda #0\n sta $26')
    put(' lda $1A');branch('bne','Classified');put(' lda $10');branch('beq','Classified')
    offset(2,64,4);put(' tax\n lda.l $40901C,x\n ora.l $40901E,x');branch('bne','Classified')
    offset(2,80,4);put(' tax\n lda.l $414008,x\n cmp #2');branch('bne');put(' lda.l $41400A,x');branch('bne')
    for off,n in ((0,'Lo'),(2,'Hi')):put(f' lda.l $41400C+{off},x\n sta.l {sy["SourceModelEntityCopy4086_"+n]}')
    offset(2,64,4);put(' tax')
    for off,n in ((0,'Lo'),(2,'Hi')):put(f' lda.l $416830+{off},x\n sta.l {sy["SourceDefaultPlayer4086_Inv"+n]}')
    put(f' jsl {sy["SourceInAir4086_Q16Compatibility"]}\n cmp #0');branch('bne','Classified')
    put(' lda $20\n ora $18');branch('bne','Classified')
    offset(2,32,4);put(' tax\n lda.l $43EB00,x\n ora.l $43EB02,x');branch('bne','NotBusy')
    offset(2,96,4);put(' tax\n lda.l $40C05A,x');branch('bpl','Classified')
    label('NotBusy');put(' lda $0A');branch('bmi','Blockable');put(' ora $08');branch('bne','Classified')
    label('Blockable');require(sy['SourceRandom4086_Ready'],0xb4d4);require(sy['SourceRandom4086_Busy'],0);put(' lda #1\n sta $26')
    label('Classified')
    # Complete source pre-block bomb changes before rand32. Juggle subtraction
    # is a pure no-op under this derived zero-cost capability; item rejects.
    for src in (2,0):
        offset(src,4,4);put(' tax\n lda.l $7EFD02,x');branch('bne','BombNext'+str(src));put(' lda.l $7EFD00,x\n cmp #1');branch('bne','BombNext'+str(src))
        put(' lda #2\n sta.l $7EFD00,x');label('BombNext'+str(src))
    put(' lda $26');branch('beq','Active')
    put(f' jsl {sy["SourceRandom4086_Next"]}');branch('bcs')
    put(f' lda.l {sy["VmNativeVariant_Result"]}+4\n and $1C\n cmp #1');branch('bne','Active')
    put(f' lda.l {sy["VmNativeVariant_Result"]}+6\n and $1E');branch('bne','Active')
    put(f' lda #{PASSIVE_BLOCK_REQUIRED}\n jmp HitBlock_Selected')
    label('Active');put(' lda $1A');branch('bne','ActiveFlags')
    offset(2,96,4);put(' tax\n lda.l $40C048,x\n cmp #1');branch('bne','Damage');put(' lda.l $40C04A,x');branch('bne','Damage')
    label('ActiveFlags');put(' lda $22');branch('beq','Damage');put(' lda $18\n ora $20');branch('bne','Damage')
    put(' lda $0A');branch('bmi','ActiveSelected');put(' ora $08');branch('bne','Damage')
    label('ActiveSelected');put(f' lda #{ACTIVE_BLOCK_REQUIRED}\n jmp HitBlock_Selected')
    label('Damage');put(f' lda #{DAMAGE_REQUIRED}')
    label('Selected');put(f' sta.l {w}+62\n lda #5\n sta.l {w}+60')
    label('Retained');put(f' lda.l {w}+62\n cmp #{PASSIVE_BLOCK_REQUIRED}');branch('bcc');put(f' cmp #{DAMAGE_REQUIRED+1}');branch('bcs')
    label('Good');put(f' tay\n tsc\n clc\n adc #{size}\n tcs\n tya\n pld\n ply\n plx\n plp\n clc\n rtl')
    label('Bad');put(f' tsc\n clc\n adc #{size}\n tcs\n pld\n ply\n plx\n plp\n sec\n rtl')
    label('NoBlock')
    for a in req['attacks']:put(' .dw '+str(a['no_block']&65535)+','+str((a['no_block']>>16)&65535))
    label('FrameCounts');put(' .dw 0,'+','.join(str(a['numframes'])for a in sorted(req['animations'],key=lambda a:a['handle'])))
    return '\n'.join(lines)+'\n'
