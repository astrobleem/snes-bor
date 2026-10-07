; B4AT scalar cache: 16x12 bytes at $40BD00..$40BDBF, outside core cache.
; Actual entity copy: 128x14 bytes at $438800..$438EFF. Held palettes end
; $437E00, combat ends $438800, sentinel begins $438FC0, life begins $439000.
; Aggression int32, attackthrottle binary32, attackthrottletime binary32,
; per-entity publication marker B603 at +12. No float/color quantization.
SourceAttackTiming4086_Ready = $43BF0E
SourceAttackTiming4086_Bank = $43BF10
SourceAttackTiming4086_Base = $43BF12
SourceAttackTiming4086_Bytes = $43BF14
SourceAttackTiming4086_Status = $43BF16
SourceAttackTiming4086_Models = $43BF18
SourceAttackTiming4086_End = $43BF1A
SOURCE_ATTACK_TIMING_CACHE = $40BD00
SourceAttackTiming4086_Globals = $40BDC0 ; min chance, offscreen factor, duration
SOURCE_ENTITY_ATTACK_TIMING = $438800
SOURCE_ENTITY_ATTACK_TIMING_STRIDE = 14
SOURCE_ENTITY_ATTACK_TIMING_END = $438F00
SourceAttackTiming4086_Load:
.a16
.i16
 php
 rep #$38
 phx
 phy
 phd
 tsc
 sec
 sbc #10
 tcs
 inc a
 tcd
 lda.l SourceAttackTiming4086_Ready
 cmp #$B603
 beq SourceAttackTiming4086_L1
 jmp SourceAttackTiming4086_LoadBad
SourceAttackTiming4086_L1:
.a16
.i16
 lda.l SourceAttackTiming4086_Status
 beq SourceAttackTiming4086_LoadStart
 cmp #2
 beq SourceAttackTiming4086_LoadStart
 jmp SourceAttackTiming4086_LoadBad
SourceAttackTiming4086_LoadStart:
.a16
.i16
 lda #1
 sta.l SourceAttackTiming4086_Status
 lda.l SourceAttackTiming4086_Bank
 beq SourceAttackTiming4086_BankBad
 cmp #64
 bcc SourceAttackTiming4086_L2
SourceAttackTiming4086_BankBad:
.a16
.i16
 jmp SourceAttackTiming4086_LoadBad
SourceAttackTiming4086_L2:
.a16
.i16
 sta $02
 lda.l SourceAttackTiming4086_Base
 cmp #$8000
 bcs SourceAttackTiming4086_L3
 jmp SourceAttackTiming4086_LoadBad
SourceAttackTiming4086_L3:
.a16
.i16
 sta $00
 lda.l SourceAttackTiming4086_Bytes
 cmp #40
 bcs SourceAttackTiming4086_Minimum
 jmp SourceAttackTiming4086_LoadBad
SourceAttackTiming4086_Minimum:
.a16
.i16
 cmp #221
 bcc SourceAttackTiming4086_Maximum
 jmp SourceAttackTiming4086_LoadBad
SourceAttackTiming4086_Maximum:
.a16
.i16
 lda $00
 clc
 adc.l SourceAttackTiming4086_Bytes
 bcc SourceAttackTiming4086_Header
 beq SourceAttackTiming4086_Header
 jmp SourceAttackTiming4086_LoadBad
SourceAttackTiming4086_Header:
.a16
.i16
 ldy #0
 lda [$00],y
 cmp #$3442
 beq SourceAttackTiming4086_L4
 jmp SourceAttackTiming4086_LoadBad
SourceAttackTiming4086_L4:
.a16
.i16
 ldy #2
 lda [$00],y
 cmp #$5441
 beq SourceAttackTiming4086_L5
 jmp SourceAttackTiming4086_LoadBad
SourceAttackTiming4086_L5:
.a16
.i16
 ldy #4
 lda [$00],y
 cmp #1
 beq SourceAttackTiming4086_L6
 jmp SourceAttackTiming4086_LoadBad
SourceAttackTiming4086_L6:
.a16
.i16
 ldy #6
 lda [$00],y
 beq SourceAttackTiming4086_CountBad
 cmp #17
 bcc SourceAttackTiming4086_L7
SourceAttackTiming4086_CountBad:
.a16
.i16
 jmp SourceAttackTiming4086_LoadBad
SourceAttackTiming4086_L7:
.a16
.i16
 sta $04
 asl a
 asl a
 sta $06
 asl a
 clc
 adc $06
 sta $08
 clc
 adc #28
 cmp.l SourceAttackTiming4086_Bytes
 beq SourceAttackTiming4086_L8
 jmp SourceAttackTiming4086_LoadBad
SourceAttackTiming4086_L8:
.a16
.i16
 ldy #8
 lda [$00],y
 cmp #12
 beq SourceAttackTiming4086_L9
 jmp SourceAttackTiming4086_LoadBad
SourceAttackTiming4086_L9:
.a16
.i16
 ldy #10
 lda [$00],y
 iny
 iny
 ora [$00],y
 iny
 iny
 ora [$00],y
 beq SourceAttackTiming4086_ValidateGlobals
 jmp SourceAttackTiming4086_LoadBad
SourceAttackTiming4086_ValidateGlobals:
.a16
.i16
 ldy #18
 ldx #3
SourceAttackTiming4086_Global:
.a16
.i16
 lda [$00],y
 and #$7F80
 cmp #$7F80
 bne SourceAttackTiming4086_GlobalGood
 jmp SourceAttackTiming4086_LoadBad
SourceAttackTiming4086_GlobalGood:
.a16
.i16
 iny
 iny
 iny
 iny
 dex
 bne SourceAttackTiming4086_Global
 ldy #34
 ldx $04
SourceAttackTiming4086_Row:
.a16
.i16
 lda [$00],y
 and #$7F80
 cmp #$7F80
 bne SourceAttackTiming4086_ThrottleGood
 jmp SourceAttackTiming4086_LoadBad
SourceAttackTiming4086_ThrottleGood:
.a16
.i16
 iny
 iny
 iny
 iny
 lda [$00],y
 and #$7F80
 cmp #$7F80
 bne SourceAttackTiming4086_TimeGood
 jmp SourceAttackTiming4086_LoadBad
SourceAttackTiming4086_TimeGood:
.a16
.i16
 tya
 clc
 adc #8
 tay
 dex
 bne SourceAttackTiming4086_Row
 ; All header/row validation precedes cache publication.
 ldy #16
 ldx #0
SourceAttackTiming4086_CopyGlobals:
.a16
.i16
 lda [$00],y
 sta.l SourceAttackTiming4086_Globals,x
 iny
 iny
 inx
 inx
 cpx #12
 bcc SourceAttackTiming4086_CopyGlobals
 ldy #28
 ldx #0
SourceAttackTiming4086_CopyCache:
.a16
.i16
 lda [$00],y
 sta.l SOURCE_ATTACK_TIMING_CACHE,x
 iny
 iny
 inx
 inx
 cpx $08
 bcc SourceAttackTiming4086_CopyCache
 lda $04
 sta.l SourceAttackTiming4086_Models
 lda #2
 sta.l SourceAttackTiming4086_Status
 tsc
 clc
 adc #10
 tcs
 pld
 ply
 plx
 plp
 clc
 rtl
SourceAttackTiming4086_LoadBad:
.a16
.i16
 lda #3
 sta.l SourceAttackTiming4086_Status
 tsc
 clc
 adc #10
 tcs
 pld
 ply
 plx
 plp
 sec
 rtl

; A=physical slot, X=new current model. Preflight does not change entity rows.
SourceAttackTiming4086_PreflightEntity:
.a16
.i16
 php
 rep #$38
 pha
 lda.l SourceAttackTiming4086_Ready
 cmp #$B603
 bne SourceAttackTiming4086_PreflightBad
 lda.l SourceAttackTiming4086_Status
 cmp #2
 bne SourceAttackTiming4086_PreflightBad
 lda.l SourceAttackTiming4086_Models
 beq SourceAttackTiming4086_PreflightBad
 cmp #17
 bcs SourceAttackTiming4086_PreflightBad
 cmp.l SourceModelEntityCopy4086_Models
 bne SourceAttackTiming4086_PreflightBad
 txa
 cmp.l SourceAttackTiming4086_Models
 bcs SourceAttackTiming4086_PreflightBad
 lda 1,s
 cmp #128
 bcs SourceAttackTiming4086_PreflightBad
 pla
 plp
 clc
 rtl
SourceAttackTiming4086_PreflightBad:
.a16
.i16
 pla
 plp
 sec
 rtl
SourceAttackTiming4086_CopyEntity:
.a16
.i16
 php
 rep #$38
 phx
 phy
 pha
 jsl SourceAttackTiming4086_PreflightEntity
 bcc SourceAttackTiming4086_EntityValid
 jmp SourceAttackTiming4086_EntityBad
SourceAttackTiming4086_EntityValid:
.a16
.i16
 phd
 tsc
 sec
 sbc #12
 tcs
 inc a
 tcd
 txa
 asl a
 asl a
 pha
 asl a
 clc
 adc 1,s
 tax
 pla
 lda.l SOURCE_ATTACK_TIMING_CACHE,x
 sta $00
 lda.l SOURCE_ATTACK_TIMING_CACHE+2,x
 sta $02
 lda.l SOURCE_ATTACK_TIMING_CACHE+4,x
 sta $04
 lda.l SOURCE_ATTACK_TIMING_CACHE+6,x
 sta $06
 lda.l SOURCE_ATTACK_TIMING_CACHE+8,x
 sta $08
 lda.l SOURCE_ATTACK_TIMING_CACHE+10,x
 sta $0A
 lda 15,s
 asl a
 pha
 asl a
 clc
 adc 1,s
 asl a
 clc
 adc 1,s
 tax
 pla
 lda #0
 sta.l SOURCE_ENTITY_ATTACK_TIMING+12,x
 lda $00
 sta.l SOURCE_ENTITY_ATTACK_TIMING,x
 lda $02
 sta.l SOURCE_ENTITY_ATTACK_TIMING+2,x
 lda $04
 sta.l SOURCE_ENTITY_ATTACK_TIMING+4,x
 lda $06
 sta.l SOURCE_ENTITY_ATTACK_TIMING+6,x
 lda $08
 sta.l SOURCE_ENTITY_ATTACK_TIMING+8,x
 lda $0A
 sta.l SOURCE_ENTITY_ATTACK_TIMING+10,x
 lda #$B603
 sta.l SOURCE_ENTITY_ATTACK_TIMING+12,x
 tsc
 clc
 adc #12
 tcs
 pld
 pla
 ply
 plx
 plp
 clc
 rtl
SourceAttackTiming4086_EntityBad:
.a16
.i16
 pla
 ply
 plx
 plp
 sec
 rtl
