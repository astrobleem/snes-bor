; Mutable modeldata.offscreenkill, signed DWORD. B610 leases 43D600..D7FF.
; Requires cost/movement/autokill leases; animation-cache capacity 5632 bytes.
; Constructor memset clears; full model copy REPLACES; knife_spawn modifies.
SourceOffscreenState4086_Ready = $40BF4C
SourceOffscreenState4086_Base = $40BF4E
SourceOffscreenState4086_Bank = $40BF50
SourceOffscreenState4086_Bytes = $40BF52
SourceOffscreenState4086_Models = $40BF54
SourceOffscreenState4086_Model = $40BF56
SourceOffscreenState4086_Slot = $40BF58
SourceOffscreenState4086_Value = $40BF5A
SourceOffscreenState4086_End = $40BF5E
SOURCE_ENTITY_OFFSCREEN = $43D600
SOURCE_ENTITY_OFFSCREEN_END = $43D800
SOURCE_OFFSCREEN_ANIMATION_CAPACITY = 5632

SourceOffscreenState4086_CheckCacheSpan:
.a16
.i16
 php
 rep #$38
 pha
 lda.l SourceOffscreenState4086_Ready
 beq SourceOffscreenState4086_SpanGood
 cmp #$B610
 bne SourceOffscreenState4086_SpanBad
 lda.l SourceAttackCostState4086_Ready
 cmp #$B609
 bne SourceOffscreenState4086_SpanBad
 lda.l SourceMovementState4086_Ready
 cmp #$B60B
 bne SourceOffscreenState4086_SpanBad
 lda.l SourceAutokillState4086_Ready
 cmp #$B60E
 bne SourceOffscreenState4086_SpanBad
 lda 1,s
 cmp #SOURCE_OFFSCREEN_ANIMATION_CAPACITY+1
 bcs SourceOffscreenState4086_SpanBad
SourceOffscreenState4086_SpanGood:
.a16
.i16
 pla
 plp
 clc
 rtl
SourceOffscreenState4086_SpanBad:
.a16
.i16
 pla
 plp
 sec
 rtl

SourceOffscreenState4086_PreflightBirth:
.a16
.i16
 php
 rep #$38
 pha
 lda.l SourceOffscreenState4086_Ready
 beq SourceOffscreenState4086_BirthGood
 cmp #$B610
 bne SourceOffscreenState4086_BirthBad
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 bne SourceOffscreenState4086_BirthBad
 lda.l VmSourceWorld_Count
 beq SourceOffscreenState4086_BirthBad
 cmp #129
 bcs SourceOffscreenState4086_BirthBad
 cmp 1,s
 bcc SourceOffscreenState4086_BirthBad
 beq SourceOffscreenState4086_BirthBad
 lda.l SourceModelAnimationCopy4086_Ready
 cmp #$B4E9
 bne SourceOffscreenState4086_BirthBad
 lda.l SourceModelAnimationCopy4086_Bytes
 beq SourceOffscreenState4086_BirthBad
 jsl SourceAttackCostState4086_CheckCacheSpan
 bcs SourceOffscreenState4086_BirthBad
SourceOffscreenState4086_BirthGood:
.a16
.i16
 pla
 plp
 clc
 rtl
SourceOffscreenState4086_BirthBad:
.a16
.i16
 pla
 plp
 sec
 rtl

SourceOffscreenState4086_BirthClear:
.a16
.i16
 php
 rep #$38
 phx
 pha
 jsl SourceOffscreenState4086_PreflightBirth
 bcs SourceOffscreenState4086_ClearBad
 lda.l SourceOffscreenState4086_Ready
 beq SourceOffscreenState4086_ClearGood
 lda 1,s
 asl a
 asl a
 tax
 lda #0
 sta.l SOURCE_ENTITY_OFFSCREEN,x
 sta.l SOURCE_ENTITY_OFFSCREEN+2,x
SourceOffscreenState4086_ClearGood:
.a16
.i16
 pla
 plx
 plp
 clc
 rtl
SourceOffscreenState4086_ClearBad:
.a16
.i16
 pla
 plx
 plp
 sec
 rtl

; A=slot X=model. Immutable B4OS validated offline incl CRC before lease.
; Pure actor preflight captures source value in scratch, preserves CPU context.
SourceOffscreenState4086_PreflightModel:
.a16
.i16
 php
 rep #$38
 phx
 phy
 phd
 pha
 sta.l SourceOffscreenState4086_Slot
 txa
 sta.l SourceOffscreenState4086_Model
 tsc
 sec
 sbc #4
 tcs
 inc a
 tcd
 lda.l SourceOffscreenState4086_Ready
 bne SourceOffscreenState4086_ModelEnabled
 jmp SourceOffscreenState4086_ModelGood
SourceOffscreenState4086_ModelEnabled:
.a16
.i16
 cmp #$B610
 bne SourceOffscreenState4086_ModelBadNear
 lda.l SourceOffscreenState4086_Slot
 jsl SourceOffscreenState4086_PreflightBirth
 bcs SourceOffscreenState4086_ModelBadNear
 lda.l SourceOffscreenState4086_Models
 beq SourceOffscreenState4086_ModelBadNear
 cmp #17
 bcs SourceOffscreenState4086_ModelBadNear
 cmp.l SourceModelEntityCopy4086_Models
 bne SourceOffscreenState4086_ModelBadNear
 cmp.l SourceOffscreenState4086_Model
 bcc SourceOffscreenState4086_ModelBadNear
 beq SourceOffscreenState4086_ModelBadNear
 asl a
 asl a
 asl a
 clc
 adc #24
 cmp.l SourceOffscreenState4086_Bytes
 bne SourceOffscreenState4086_ModelBadNear
 lda.l SourceOffscreenState4086_Bank
 beq SourceOffscreenState4086_ModelBadNear
 cmp #64
 bcs SourceOffscreenState4086_ModelBadNear
 sta $02
 lda.l SourceOffscreenState4086_Base
 cmp #$8000
 bcc SourceOffscreenState4086_ModelBadNear
 sta $00
 clc
 adc.l SourceOffscreenState4086_Bytes
 bcc SourceOffscreenState4086_Header
 beq SourceOffscreenState4086_Header
SourceOffscreenState4086_ModelBadNear:
.a16
.i16
 jmp SourceOffscreenState4086_ModelBad
SourceOffscreenState4086_Header:
.a16
.i16
 ldy #0
 lda [$00],y
 cmp #$3442
 beq SourceOffscreenState4086_HeaderCheck0
 jmp SourceOffscreenState4086_HeaderBad
SourceOffscreenState4086_HeaderCheck0:
.a16
.i16
 ldy #2
 lda [$00],y
 cmp #$534F
 beq SourceOffscreenState4086_HeaderCheck1
 jmp SourceOffscreenState4086_HeaderBad
SourceOffscreenState4086_HeaderCheck1:
.a16
.i16
 ldy #4
 lda [$00],y
 cmp #1
 beq SourceOffscreenState4086_HeaderCheck2
 jmp SourceOffscreenState4086_HeaderBad
SourceOffscreenState4086_HeaderCheck2:
.a16
.i16
 ldy #6
 lda [$00],y
 cmp #8
 beq SourceOffscreenState4086_HeaderCheck3
 jmp SourceOffscreenState4086_HeaderBad
SourceOffscreenState4086_HeaderCheck3:
.a16
.i16
 ldy #10
 lda [$00],y
 cmp #0
 beq SourceOffscreenState4086_HeaderCheck4
 jmp SourceOffscreenState4086_HeaderBad
SourceOffscreenState4086_HeaderCheck4:
.a16
.i16
 ldy #14
 lda [$00],y
 cmp #0
 beq SourceOffscreenState4086_HeaderCheck5
 jmp SourceOffscreenState4086_HeaderBad
SourceOffscreenState4086_HeaderCheck5:
.a16
.i16
 ldy #20
 lda [$00],y
 cmp #0
 beq SourceOffscreenState4086_HeaderCheck6
 jmp SourceOffscreenState4086_HeaderBad
SourceOffscreenState4086_HeaderCheck6:
.a16
.i16
 ldy #22
 lda [$00],y
 cmp #0
 beq SourceOffscreenState4086_HeaderCheck7
 jmp SourceOffscreenState4086_HeaderBad
SourceOffscreenState4086_HeaderCheck7:
.a16
.i16
 ldy #8
 lda [$00],y
 cmp.l SourceOffscreenState4086_Models
 beq SourceOffscreenState4086_HeaderCheck8
 jmp SourceOffscreenState4086_HeaderBad
SourceOffscreenState4086_HeaderCheck8:
.a16
.i16
 asl a
 asl a
 asl a
 ldy #12
 cmp [$00],y
 beq SourceOffscreenState4086_HeaderCheck9
 jmp SourceOffscreenState4086_HeaderBad
SourceOffscreenState4086_HeaderCheck9:
.a16
.i16
 lda.l SourceOffscreenState4086_Model
 asl a
 asl a
 asl a
 clc
 adc #24
 tay
 lda [$00],y
 cmp.l SourceOffscreenState4086_Model
 beq SourceOffscreenState4086_HeaderCheck10
 jmp SourceOffscreenState4086_HeaderBad
SourceOffscreenState4086_HeaderCheck10:
.a16
.i16
 iny
 iny
 lda [$00],y
 beq SourceOffscreenState4086_HeaderCheck11
 jmp SourceOffscreenState4086_HeaderBad
SourceOffscreenState4086_HeaderCheck11:
.a16
.i16
 iny
 iny
 lda [$00],y
 sta.l SourceOffscreenState4086_Value
 iny
 iny
 lda [$00],y
 sta.l SourceOffscreenState4086_Value+2
 bra SourceOffscreenState4086_ModelGood
SourceOffscreenState4086_HeaderBad:
.a16
.i16
 jmp SourceOffscreenState4086_ModelBad
SourceOffscreenState4086_ModelGood:
.a16
.i16
 tsc
 clc
 adc #4
 tcs
 pla
 pld
 ply
 plx
 plp
 clc
 rtl
SourceOffscreenState4086_ModelBad:
.a16
.i16
 tsc
 clc
 adc #4
 tcs
 pla
 pld
 ply
 plx
 plp
 sec
 rtl

SourceOffscreenState4086_ApplyModel:
.a16
.i16
 php
 rep #$38
 phx
 pha
 jsl SourceOffscreenState4086_PreflightModel
 bcs SourceOffscreenState4086_ApplyBad
 lda.l SourceOffscreenState4086_Ready
 beq SourceOffscreenState4086_ApplyGood
 lda.l SourceOffscreenState4086_Slot
 asl a
 asl a
 tax
 lda.l SourceOffscreenState4086_Value
 sta.l SOURCE_ENTITY_OFFSCREEN,x
 lda.l SourceOffscreenState4086_Value+2
 sta.l SOURCE_ENTITY_OFFSCREEN+2,x
SourceOffscreenState4086_ApplyGood:
.a16
.i16
 pla
 plx
 plp
 clc
 rtl
SourceOffscreenState4086_ApplyBad:
.a16
.i16
 pla
 plx
 plp
 sec
 rtl
