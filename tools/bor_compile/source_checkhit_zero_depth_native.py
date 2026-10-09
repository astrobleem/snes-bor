"""Bounded native zero-depth collision over current source frame metadata.

X/Y carry independent generation. Hit-state controls provide attacker slot+4,
target slot+26 and counter0/1 at+24. Success publishes Q16 contact at+44..63;
miss preserves that record. Actor identities and world phase remain unchanged.
This uses the existing explicit Q16 coordinate adaptation.
"""
import re
from source_hit_state_layout import layout


def emit(requirements,plan,symbols,bank,code_bank=39):
    if plan!=layout(plan['entities'])or not 0<=bank<64:raise ValueError('CHECKHIT_ZERO_DEPTH_NATIVE_PLAN')
    if requirements['capability']!='ZERO_DEPTH_IMMUTABLE_UNIFORM_GRABDISTANCE' or not 0<=requirements['depth_limit_q16']<0x80000000:raise ValueError('CHECKHIT_ZERO_DEPTH_CAPABILITY')
    if not 0<=code_bank<64:raise ValueError('CHECKHIT_NATIVE_CODE_BANK')
    w=plan['controls'];lines=[];serial=0;size=112
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('CheckHit_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;l='CheckHit_Guard'+str(serial)
        inv=dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc',bpl='bmi',bmi='bpl',bvc='bvs',bvs='bvc')
        put(' '+inv[op]+' '+l+'\n jmp CheckHit_'+n+'\n'+l+':\n.a16\n.i16')
    def load(n):put(f' lda.l {symbols[n]}')
    def require(n,v):load(n);put(f' cmp #{v}');branch('bne')
    def copy_long(src,dst):put(f' lda.l {src}\n sta ${dst:02X}\n lda.l {src+2}\n sta ${dst+2:02X}')
    label('Run');put(f' php\n rep #$39\n phx\n phy\n phd\n tsc\n sec\n sbc #{size}\n tcs\n inc a\n tcd')
    put(f' jsl {symbols["SourceForeignWork_Check"]}');branch('bcs')
    for n,v in (('SourceWorldTick4086_Ready',0xb4d5),('SourceWorldTick4086_State',1),('SourceWorldTick4086_Pending',1),('SourceWorldTick4086_Phase',8),('SourceWorldTick4086_Fault',0),('SourceCollisionFrame4086_Ready',0xb5ee),('SourceCollisionFrame4086_Bank',bank),('SourceCollisionFrame4086_Bytes',requirements['collision_table_bytes'])):require(n,v)
    load('SourceCollisionFrame4086_Status');put(' cmp #2');branch('beq','QueryReady');put(' cmp #0');branch('bne');label('QueryReady')
    load('SourceWorldTick4086_Slot');put(f' cmp.l {w}+4');branch('bne')
    for field,off in (('Lo',0),('Hi',2)):
        load('SourceWorldTick4086_Time'+field);put(f' cmp.l {symbols["VmSourceWorld_Time"]+off}');branch('bne')
    put(' jsl HitState_Read');branch('bcs')
    put(f' lda.l {w}+24\n cmp #2');branch('bcs');put(' sta $06')
    put(f' lda.l {w}+4\n sta $08\n cmp.l {w}+26');branch('beq','Miss')
    put(f' lda.l {w}+26\n sta $0A')
    for who,slot,idx,pose,direction in (('A',8,0,24,16),('B',10,2,36,20)):
        put(f' lda #0\n sta.l {symbols["SourceCollisionFrame4086_Status"]}\n lda ${slot:02X}\n jsl {symbols["SourceCollisionFrame4086_QueryEntity"]}');branch('bcs')
        if who=='A':
            load('SourceCollisionFrame4086_Attack');branch('beq');put(f' cmp #{requirements["attack_count"]+1}');branch('bcs');put(' sta $00')
        else:
            load('SourceCollisionFrame4086_Vulnerable');branch('beq','Miss')
            load('SourceCollisionFrame4086_Box');branch('beq','Miss');put(f' cmp #{requirements["box_count"]+1}');branch('bcs');put(' sta $02')
            load('SourceCollisionFrame4086_Attack');put(' sta $04')
        load('SourceCollisionFrame4086_EntityView');put(' tax')
        for off in (8,48,56):
            put(f' lda.l ${0x410000+off:06X},x\n cmp #{symbols["BOR_VT_DECIMAL"]}');branch('bne')
            put(f' lda.l ${0x410002+off:06X},x');branch('bne')
        put(f' lda.l $410018,x\n cmp #{symbols["BOR_VT_INTEGER"]}');branch('bne');put(' lda.l $41001A,x');branch('bne')
        for off,dst in ((52,pose),(12,pose+4),(60,pose+8),(28,direction)):
            put(f' lda.l ${0x410000+off:06X},x\n sta ${dst:02X}\n lda.l ${0x410002+off:06X},x\n sta ${dst+2:02X}')
    # Attack LUT stride20: six signed coordinates, counter16, reserved16, type32.
    put(' lda $00\n dec a\n asl a\n asl a\n sta $30\n asl a\n asl a\n clc\n adc $30\n sta $30\n tax\n lda.l CheckHit_Attacks+12,x\n sta $5C\n lda.l CheckHit_Attacks+16,x\n sta $44\n lda.l CheckHit_Attacks+18,x\n sta $46')
    put(' lda $06');branch('beq','NormalTarget')
    put(' lda $04');branch('beq','Miss');put(f' cmp #{requirements["attack_count"]+1}');branch('bcs')
    put(' dec a\n asl a\n asl a\n sta $32\n asl a\n asl a\n clc\n adc $32\n sta $32\n tax\n lda.l CheckHit_Attacks+12,x\n eor #$8000\n sta $5E\n lda $5C\n eor #$8000\n cmp $5E');branch('bcc','Miss')
    put(' jmp CheckHit_Depth')
    label('NormalTarget');put(' lda $02\n dec a\n asl a\n asl a\n sta $32\n asl a\n clc\n adc $32\n sta $32')
    label('Depth');put(' lda $20\n sec\n sbc $2C\n sta $58\n lda $22\n sbc $2E\n sta $5A');branch('bvs')
    put(' lda $5A');branch('bpl','PositiveDepth')
    put(' lda #0\n sec\n sbc $58\n sta $58\n lda #0\n sbc $5A\n sta $5A');branch('bvs')
    label('PositiveDepth');limit=requirements['depth_limit_q16'];put(f' lda $5A\n cmp #{limit>>16}');branch('bcc','Anchors');branch('bne','Miss')
    put(f' lda $58\n cmp #{(limit&65535)+1}') if limit&65535!=65535 else put(' jmp CheckHit_Anchors')
    if limit&65535!=65535:branch('bcs','Miss')
    label('Anchors')
    for x,alt,z,anchor in ((24,28,32,96),(36,40,44,100)):
        put(f' ldx #{x}\n jsr CheckHit_Trunc\n sta ${anchor:02X}')
        put(f' lda ${z:02X}\n sec\n sbc ${alt:02X}\n sta $58\n lda ${z+2:02X}\n sbc ${alt+2:02X}\n sta $5A');branch('bvs')
        put(f' ldx #88\n jsr CheckHit_Trunc\n sta ${anchor+2:02X}')
    # Endpoint addition is bounded and fails explicitly on signed16 overflow.
    for who,anchor,direction,rect in (('A',96,16,52),('B',100,20,60)):
        def draw(table):
            put(f' lda ${direction:02X}\n ora ${direction+2:02X}');branch('beq',who+'Left'+table)
            for co,dst in ((0,rect),(4,rect+4)):
                put(f' lda ${anchor:02X}\n clc\n adc.l CheckHit_{table}+{co},x');branch('bvs');put(f' sta ${dst:02X}')
            put(' jmp CheckHit_'+who+'Vertical'+table)
            label(who+'Left'+table)
            for co,dst in ((4,rect),(0,rect+4)):
                put(f' lda ${anchor:02X}\n sec\n sbc.l CheckHit_{table}+{co},x');branch('bvs');put(f' sta ${dst:02X}')
            label(who+'Vertical'+table)
            for co,dst in ((2,rect+2),(6,rect+6)):
                put(f' lda ${anchor+2:02X}\n clc\n adc.l CheckHit_{table}+{co},x');branch('bvs');put(f' sta ${dst:02X}')
        put(' lda $30\n tax')if who=='A'else put(' lda $32\n tax')
        if who=='A':draw('Attacks')
        else:
            put(' lda $06');branch('beq','TargetBox');draw('Attacks');put(' jmp CheckHit_Rects')
            label('TargetBox');draw('Boxes')
    label('Rects')
    for left,right in ((52,64),(60,56),(54,66),(62,58)):
        put(f' lda ${right:02X}\n eor #$8000\n sta $68\n lda ${left:02X}\n eor #$8000\n cmp $68');branch('bcc','Overlap'+str(left));branch('bne','Miss');label('Overlap'+str(left))
    # Select greater left/top and smaller right/bottom, then sum in signed32.
    for a,b,c,d,dst in ((52,60,56,64,72),(54,62,58,66,76)):
        put(f' lda ${b:02X}\n eor #$8000\n sta $68\n lda ${a:02X}\n eor #$8000\n cmp $68');branch('bcs','Max'+str(dst));put(f' lda ${b:02X}\n sta $6C\n jmp CheckHit_MaxDone{dst}');label('Max'+str(dst));put(f' lda ${a:02X}\n sta $6C');label('MaxDone'+str(dst))
        put(f' lda ${d:02X}\n eor #$8000\n sta $68\n lda ${c:02X}\n eor #$8000\n cmp $68');branch('bcc','Min'+str(dst));put(f' lda ${d:02X}\n sta $6E\n jmp CheckHit_MinDone{dst}');label('Min'+str(dst));put(f' lda ${c:02X}\n sta $6E');label('MinDone'+str(dst))
        put(' lda $6C\n bpl CheckHit_SignA'+str(dst)+'\n lda #$FFFF\n bra CheckHit_SignADone'+str(dst));label('SignA'+str(dst));put(' lda #0');label('SignADone'+str(dst));put(' sta $68')
        put(' lda $6E\n bpl CheckHit_SignB'+str(dst)+'\n lda #$FFFF\n bra CheckHit_SignBDone'+str(dst));label('SignB'+str(dst));put(' lda #0');label('SignBDone'+str(dst));put(' sta $6A')
        put(' lda $6C\n clc\n adc $6E\n sta $6C\n lda $68\n adc $6A\n sta $6E\n lda $6E\n cmp #$8000\n ror a\n sta $6E\n lda $6C\n ror a')
        put(f' sta ${dst+2:02X}\n lda $6C\n and #1\n beq CheckHit_CenterLowZero{dst}\n lda #$8000\n bra CheckHit_CenterLowDone{dst}');label('CenterLowZero'+str(dst));put(' lda #0');label('CenterLowDone'+str(dst));put(f' sta ${dst:02X}')
    # Source chooses front z by original z comparison, then publishes z+1.
    put(' lda $2E\n eor #$8000\n sta $68\n lda $22\n eor #$8000\n cmp $68');branch('bcc','TargetZ');branch('bne','AttackerZ')
    put(' lda $20\n cmp $2C');branch('bcc','TargetZ');branch('beq','TargetZ')
    label('AttackerZ');put(' lda $20\n sta $50\n lda $22\n sta $52\n jmp CheckHit_ZReady')
    label('TargetZ');put(' lda $2C\n sta $50\n lda $2E\n sta $52')
    label('ZReady');put(' lda $52\n clc\n adc #1\n sta $52');branch('bvs')
    put(' lda $50\n sec\n sbc $4C\n sta $54\n lda $52\n sbc $4E\n sta $56');branch('bvs')
    for src,off in ((72,44),(84,48),(80,52),(68,56)):
        put(f' lda ${src:02X}\n sta.l {w}+{off}\n lda ${src+2:02X}\n sta.l {w}+{off+2}')
    put(f' lda #1\n sta.l {w}+60\n lda #0\n sta.l {w}+62\n lda #1\n jmp CheckHit_Good')
    label('Miss');put(' lda #0');label('Good');put(' tay\n tsc\n clc\n adc #'+str(size)+'\n tcs\n tya\n pld\n ply\n plx\n plp\n clc\n rtl')
    label('Bad');put(' tsc\n clc\n adc #'+str(size)+'\n tcs\n pld\n ply\n plx\n plp\n sec\n rtl')
    label('Trunc');put(' lda $02,x\n bpl CheckHit_TruncDone\n pha\n lda $00,x\n beq CheckHit_TruncExact\n pla\n inc a\n rts');label('TruncExact');put(' pla');label('TruncDone');put(' rts')
    label('Boxes')
    for box in requirements['boxes']:put(' .dw '+','.join(str(v&65535)for v in box))
    label('Attacks')
    for a in requirements['attacks']:put(' .dw '+','.join(str(v&65535)for v in a['attack_coords']+[a['counterattack'],0,a['attack_type']&65535,(a['attack_type']>>16)&65535]))
    label('CodeEnd')
    code='\n'.join(lines)+'\n'
    # Small sign-extension branches are also relaxed, keeping labels annotated.
    # Poppy label arithmetic retains the 16-bit offset. Qualify LUT reads
    # explicitly with the caller-selected SNES code bank.
    code=re.sub(r'(\.l CheckHit_(?:Attacks|Boxes)\+)(\d+)',lambda m:m[1]+str((code_bank<<16)+int(m[2])),code)
    return code
