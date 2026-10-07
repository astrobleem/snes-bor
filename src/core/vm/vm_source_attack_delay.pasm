; Literal-C compiled randf delay lookup; actual source actor timing identity.
; Does not publish nextattack/stalltime: caller must preserve source call order.
SourceAttackDelay4086_Ready = $43BF1A
SourceAttackDelay4086_Status = $43BF1C
SourceAttackDelay4086_Bank = $43BF1E
SourceAttackDelay4086_Base = $43BF20
SourceAttackDelay4086_Bytes = $43BF22
SourceAttackDelay4086_Kind = $43BF24 ; 0 nextattack,1 stalltime
SourceAttackDelay4086_Result = $43BF26 ; absolute unsigned source time
SourceAttackDelay4086_Delay = $43BF2A
SourceAttackDelay4086_End = $43BF2C
SourceAttackDelay4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 phd
 tsc
 sec
 sbc #32
 tcs
 inc a
 tcd
 lda.l VmNativeVariant_Result
 sta $10
 lda.l VmNativeVariant_Result+2
 sta $12
 lda.l VmNativeVariant_Result+4
 sta $14
 lda.l VmNativeVariant_Result+6
 sta $16
 lda.l SourceModelEntityCopy4086_Lo
 sta $18
 lda.l SourceModelEntityCopy4086_Hi
 sta $1A
 lda.l SourceAttackDelay4086_Ready
 cmp #$B604
 beq SourceAttackDelay4086_Guard1
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard1:
.a16
.i16
 lda.l SourceAttackDelay4086_Status
 beq SourceAttackDelay4086_Start
 cmp #2
 beq SourceAttackDelay4086_Guard2
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard2:
.a16
.i16
SourceAttackDelay4086_Start:
.a16
.i16
 lda #1
 sta.l SourceAttackDelay4086_Status
 jsl SourceCommonThink4086_CheckOwner
 bcc SourceAttackDelay4086_Guard3
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard3:
.a16
.i16
 lda.l SourceAttackTiming4086_Ready
 cmp #$B603
 beq SourceAttackDelay4086_Guard4
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard4:
.a16
.i16
 lda.l SourceAttackTiming4086_Status
 cmp #2
 beq SourceAttackDelay4086_Guard5
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard5:
.a16
.i16
 lda.l SourceAttackTiming4086_Models
 cmp.l SourceModelEntityCopy4086_Models
 beq SourceAttackDelay4086_Guard6
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard6:
.a16
.i16
 lda.l SourceAttackDelay4086_Kind
 cmp #2
 bcc SourceAttackDelay4086_Guard7
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard7:
.a16
.i16
 lda.l SourceAI4086_Slot
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
 lda.l SOURCE_ENTITY_ATTACK_TIMING+12,x
 cmp #$B603
 beq SourceAttackDelay4086_Guard8
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard8:
.a16
.i16
 lda.l SOURCE_ENTITY_ATTACK_TIMING+0,x
 sta $08
 lda.l SOURCE_ENTITY_ATTACK_TIMING+2,x
 sta $0A
 lda.l SOURCE_ENTITY_ATTACK_TIMING+8,x
 sta $0C
 lda.l SOURCE_ENTITY_ATTACK_TIMING+10,x
 sta $0E
 lda.l SourceAttackDelay4086_Bank
 bne SourceAttackDelay4086_Guard9
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard9:
.a16
.i16
 cmp #64
 bcc SourceAttackDelay4086_Guard10
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard10:
.a16
.i16
 sta $02
 lda.l SourceAttackDelay4086_Base
 cmp #$8000
 bcs SourceAttackDelay4086_Guard11
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard11:
.a16
.i16
 sta $00
 clc
 adc.l SourceAttackDelay4086_Bytes
 bcc SourceAttackDelay4086_Extent
 cmp #0
 beq SourceAttackDelay4086_Guard12
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard12:
.a16
.i16
SourceAttackDelay4086_Extent:
.a16
.i16
 ldy #0
 lda [$00],y
 cmp #$3442
 beq SourceAttackDelay4086_Guard13
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard13:
.a16
.i16
 iny
 iny
 lda [$00],y
 cmp #$4454
 beq SourceAttackDelay4086_Guard14
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard14:
.a16
.i16
 iny
 iny
 lda [$00],y
 cmp #1
 beq SourceAttackDelay4086_Guard15
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard15:
.a16
.i16
 iny
 iny
 lda [$00],y
 bne SourceAttackDelay4086_Guard16
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard16:
.a16
.i16
 cmp #17
 bcc SourceAttackDelay4086_Guard17
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard17:
.a16
.i16
 cmp.l SourceAttackTiming4086_Models
 beq SourceAttackDelay4086_Guard18
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard18:
.a16
.i16
 asl a
 asl a
 asl a
 asl a
 clc
 adc #16
 sta $04
 clc
 adc #20000
 cmp.l SourceAttackDelay4086_Bytes
 beq SourceAttackDelay4086_Guard19
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard19:
.a16
.i16
 iny
 iny
 lda [$00],y
 cmp #16
 beq SourceAttackDelay4086_Guard20
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard20:
.a16
.i16
 iny
 iny
 lda [$00],y
 cmp #1
 beq SourceAttackDelay4086_Guard21
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard21:
.a16
.i16
 iny
 iny
 lda [$00],y
 cmp $04
 beq SourceAttackDelay4086_Guard22
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard22:
.a16
.i16
 iny
 iny
 lda [$00],y
 beq SourceAttackDelay4086_Guard23
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard23:
.a16
.i16
 lda.l SourceAI4086_Model
 asl a
 asl a
 asl a
 asl a
 clc
 adc #16
 tay
 lda [$00],y
 cmp $08
 beq SourceAttackDelay4086_Guard24
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard24:
.a16
.i16
 iny
 iny
 lda [$00],y
 cmp $0A
 beq SourceAttackDelay4086_Guard25
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard25:
.a16
.i16
 iny
 iny
 lda [$00],y
 cmp $0C
 beq SourceAttackDelay4086_Guard26
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard26:
.a16
.i16
 iny
 iny
 lda [$00],y
 cmp $0E
 beq SourceAttackDelay4086_Guard27
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard27:
.a16
.i16
 iny
 iny
 lda [$00],y
 cmp $04
 beq SourceAttackDelay4086_Guard28
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard28:
.a16
.i16
 iny
 iny
 lda [$00],y
 cmp $04
 beq SourceAttackDelay4086_Guard29
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard29:
.a16
.i16
 iny
 iny
 lda [$00],y
 sta $06
 cmp #2
 bcc SourceAttackDelay4086_Guard30
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard30:
.a16
.i16
 iny
 iny
 lda [$00],y
 beq SourceAttackDelay4086_Guard31
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard31:
.a16
.i16
 lda $0E
 and #$7FFF
 ora $0C
 beq SourceAttackDelay4086_ZeroMaximum
 lda $06
 cmp #1
 beq SourceAttackDelay4086_Guard32
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard32:
.a16
.i16
 jmp SourceAttackDelay4086_Draw
SourceAttackDelay4086_ZeroMaximum:
.a16
.i16
 lda $06
 beq SourceAttackDelay4086_Guard33
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard33:
.a16
.i16
 lda.l SourceAttackDelay4086_Kind
 bne SourceAttackDelay4086_Draw
 lda #0
 jmp SourceAttackDelay4086_DelayReady
SourceAttackDelay4086_Draw:
.a16
.i16
 jsl SourceRandom4086_Next
 bcc SourceAttackDelay4086_Guard34
 jmp SourceAttackDelay4086_Bad
SourceAttackDelay4086_Guard34:
.a16
.i16
 lda.l VmNativeVariant_Result+4
 sta.l SourceModelEntityCopy4086_Lo
 lda.l VmNativeVariant_Result+6
 sta.l SourceModelEntityCopy4086_Hi
 jsl SourceRandomFloat4086_Modulo10000
 asl a
 clc
 adc $04
 tay
 lda [$00],y
SourceAttackDelay4086_DelayReady:
.a16
.i16
 sta.l SourceAttackDelay4086_Delay
 clc
 adc.l VmSourceWorld_Time
 sta.l SourceAttackDelay4086_Result
 lda.l VmSourceWorld_Time+2
 adc #0
 sta.l SourceAttackDelay4086_Result+2
 lda #2
 sta.l SourceAttackDelay4086_Status
 jmp SourceAttackDelay4086_Return
SourceAttackDelay4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceAttackDelay4086_Status
SourceAttackDelay4086_Return:
.a16
.i16
 lda $10
 sta.l VmNativeVariant_Result
 lda $12
 sta.l VmNativeVariant_Result+2
 lda $14
 sta.l VmNativeVariant_Result+4
 lda $16
 sta.l VmNativeVariant_Result+6
 lda $18
 sta.l SourceModelEntityCopy4086_Lo
 lda $1A
 sta.l SourceModelEntityCopy4086_Hi
 tsc
 clc
 adc #32
 tcs
 pld
 ply
 plx
 lda.l SourceAttackDelay4086_Status
 cmp #2
 beq SourceAttackDelay4086_Good
 plp
 sec
 rtl
SourceAttackDelay4086_Good:
.a16
.i16
 plp
 clc
 rtl
