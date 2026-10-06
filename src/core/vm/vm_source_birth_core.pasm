; B4F9 augments only existing admitted NONE/idle births. Fixture lease only.
; Caller runs Preflight before view/side writes, Apply before alive publication.
; Existing named-variable ownership requires the full cleanup constructor and
; is rejected here. No callbacks or asynchronous state are hidden in this leaf.
SourceBirthCore4086_Ready = $7FFE64
SourceBirthCore4086_Slot = $7FFE66
SourceBirthCore4086_Model = $7FFE68
SourceBirthCore4086_Status = $7FFE6A
SourceBirthCore4086_Base = $7FFE6C
SourceBirthCore4086_Bank = $7FFE6E
SourceBirthCore4086_Bytes = $7FFE70
SourceBirthCore4086_Models = $7FFE72
SourceBirthCore4086_ReadOffset = $7FFE74
SourceBirthCore4086_Row = $7FFE76
SourceBirthCore4086_Core = $7FFE78
SourceBirthCore4086_Flags = $7FFE7A
SourceBirthCore4086_Relation = $7FFE7C
SourceBirthCore4086_Token = $7FFE7E
SourceBirthCore4086_Variable = $7FFE80
SourceBirthCore4086_End = $7FFE82

SourceBirthCore4086_Preflight:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceBirthCore4086_Ready
 bne SourceBirthCore4086_Guard_1
 jmp SourceBirthCore4086_Good
SourceBirthCore4086_Guard_1:
.a16
.i16
 cmp #$B4F9
 beq SourceBirthCore4086_Guard_2
 jmp SourceBirthCore4086_Bad
SourceBirthCore4086_Guard_2:
.a16
.i16
 lda.l SourceBirthCore4086_Status
 cmp #1
 bne SourceBirthCore4086_Guard_3
 jmp SourceBirthCore4086_Bad
SourceBirthCore4086_Guard_3:
.a16
.i16
 cmp #3
 bne SourceBirthCore4086_Guard_4
 jmp SourceBirthCore4086_Bad
SourceBirthCore4086_Guard_4:
.a16
.i16
 lda.l SourceBirthCore4086_Models
 bne SourceBirthCore4086_Guard_5
 jmp SourceBirthCore4086_Bad
SourceBirthCore4086_Guard_5:
.a16
.i16
 cmp #17
 bcc SourceBirthCore4086_Guard_6
 jmp SourceBirthCore4086_Bad
SourceBirthCore4086_Guard_6:
.a16
.i16
 cmp.l SourceModelEntityCopy4086_Models
 beq SourceBirthCore4086_Guard_7
 jmp SourceBirthCore4086_Bad
SourceBirthCore4086_Guard_7:
.a16
.i16
 cmp.l VmSourceWorld_TemplateCount
 beq SourceBirthCore4086_Guard_8
 jmp SourceBirthCore4086_Bad
SourceBirthCore4086_Guard_8:
.a16
.i16
 cmp.l SourceBirthCore4086_Model
 bcs SourceBirthCore4086_Guard_9
 jmp SourceBirthCore4086_Bad
SourceBirthCore4086_Guard_9:
.a16
.i16
 bne SourceBirthCore4086_Guard_10
 jmp SourceBirthCore4086_Bad
SourceBirthCore4086_Guard_10:
.a16
.i16
 lda.l SourceBirthCore4086_Base
 cmp #$8000
 bcs SourceBirthCore4086_Guard_11
 jmp SourceBirthCore4086_Bad
SourceBirthCore4086_Guard_11:
.a16
.i16
 clc
 adc.l SourceBirthCore4086_Bytes
 bcc SourceBirthCore4086_Guard_12
 jmp SourceBirthCore4086_Bad
SourceBirthCore4086_Guard_12:
.a16
.i16
 sta.l SourceBirthCore4086_End
 lda.l SourceBirthCore4086_Bank
 cmp #$40
 bcc SourceBirthCore4086_Guard_13
 jmp SourceBirthCore4086_Bad
SourceBirthCore4086_Guard_13:
.a16
.i16
 lda.l SourceBirthCore4086_Base
 tax
 jsr SourceBirthCore4086_Read
 cmp #$3442
 beq SourceBirthCore4086_Guard_14
 jmp SourceBirthCore4086_Bad
SourceBirthCore4086_Guard_14:
.a16
.i16
 inx
 inx
 jsr SourceBirthCore4086_Read
 cmp #$4942
 beq SourceBirthCore4086_Guard_15
 jmp SourceBirthCore4086_Bad
SourceBirthCore4086_Guard_15:
.a16
.i16
 inx
 inx
 jsr SourceBirthCore4086_Read
 cmp #1
 beq SourceBirthCore4086_Guard_16
 jmp SourceBirthCore4086_Bad
SourceBirthCore4086_Guard_16:
.a16
.i16
 inx
 inx
 jsr SourceBirthCore4086_Read
 cmp #208
 beq SourceBirthCore4086_Guard_17
 jmp SourceBirthCore4086_Bad
SourceBirthCore4086_Guard_17:
.a16
.i16
 inx
 inx
 jsr SourceBirthCore4086_Read
 cmp.l SourceBirthCore4086_Models
 beq SourceBirthCore4086_Guard_18
 jmp SourceBirthCore4086_Bad
SourceBirthCore4086_Guard_18:
.a16
.i16
 lda.l SourceBirthCore4086_Model
 asl a
 asl a
 asl a
 asl a
 pha
 asl a
 asl a
 pha
 asl a
 clc
 adc 1,s
 clc
 adc 3,s
 ply
 ply
 clc
 adc #24
 clc
 adc.l SourceBirthCore4086_Base
 sta.l SourceBirthCore4086_Row
 clc
 adc #208
 cmp.l SourceBirthCore4086_End
 bcc SourceBirthCore4086_RowBounds
 beq SourceBirthCore4086_RowBounds
 jmp SourceBirthCore4086_Bad
SourceBirthCore4086_RowBounds:
.a16
.i16
 lda.l SourceBirthCore4086_Row
 tax
 jsr SourceBirthCore4086_Read
 cmp.l SourceBirthCore4086_Model
 beq SourceBirthCore4086_Guard_19
 jmp SourceBirthCore4086_Bad
SourceBirthCore4086_Guard_19:
.a16
.i16
 inx
 inx
 jsr SourceBirthCore4086_Read
 cmp #1
 beq SourceBirthCore4086_Guard_20
 jmp SourceBirthCore4086_Bad
SourceBirthCore4086_Guard_20:
.a16
.i16
 lda.l SourceBirthCore4086_Slot
 cmp.l VmSourceWorld_Count
 bcc SourceBirthCore4086_Guard_21
 jmp SourceBirthCore4086_Bad
SourceBirthCore4086_Guard_21:
.a16
.i16
 sta.l SourceRetirement4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l SourceBirthCore4086_Flags
 asl a
 sta.l SourceBirthCore4086_Relation
 clc
 adc.l SourceBirthCore4086_Flags
 sta.l SourceBirthCore4086_Core
 lda.l SourceBirthCore4086_Slot
 asl a
 asl a
 asl a
 asl a
 pha
 asl a
 asl a
 clc
 adc 1,s
 ply
 clc
 adc #$4000
 sta.l SourceBirthCore4086_Token
 tax
 lda.l $410004,x
 beq SourceBirthCore4086_Guard_22
 jmp SourceBirthCore4086_Bad
SourceBirthCore4086_Guard_22:
.a16
.i16
 lda.l $410000,x
 cmp.l SourceBirthCore4086_Token
 beq SourceBirthCore4086_Guard_23
 jmp SourceBirthCore4086_Bad
SourceBirthCore4086_Guard_23:
.a16
.i16
 lda.l $410002,x
 cmp #$0041
 beq SourceBirthCore4086_Guard_24
 jmp SourceBirthCore4086_Bad
SourceBirthCore4086_Guard_24:
.a16
.i16
 jsl SourceRetirement4086_ApplyNoEvents
 bcc SourceBirthCore4086_Guard_25
 jmp SourceBirthCore4086_Bad
SourceBirthCore4086_Guard_25:
.a16
.i16
 ; Retirement preflight validates physical core/flags/vars/roles/self leases.
 lda.l VmSourceVars_Base
 sta.l SourceBirthCore4086_Variable
 lda.l VmSourceVars_Count
 tay
SourceBirthCore4086_VarLoop:
.a16
.i16
 lda.l SourceBirthCore4086_Variable
 tax
 lda.l $410000,x
 cmp.l SourceBirthCore4086_Token
 bne SourceBirthCore4086_VarNext
 lda.l $410002,x
 cmp #$0041
 bne SourceBirthCore4086_Guard_26
 jmp SourceBirthCore4086_Bad
SourceBirthCore4086_Guard_26:
.a16
.i16
SourceBirthCore4086_VarNext:
.a16
.i16
 lda.l SourceBirthCore4086_Variable
 clc
 adc #64
 sta.l SourceBirthCore4086_Variable
 dey
 bne SourceBirthCore4086_VarLoop
SourceBirthCore4086_Good:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
SourceBirthCore4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceBirthCore4086_Status
 ply
 plx
 plp
 sec
 rtl

SourceBirthCore4086_Apply:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jsl SourceBirthCore4086_Preflight
 bcc SourceBirthCore4086_Guard_27
 jmp SourceBirthCore4086_Bad
SourceBirthCore4086_Guard_27:
.a16
.i16
 lda.l SourceBirthCore4086_Ready
 bne SourceBirthCore4086_Guard_28
 jmp SourceBirthCore4086_Good
SourceBirthCore4086_Guard_28:
.a16
.i16
 lda #1
 sta.l SourceBirthCore4086_Status
 lda.l SourceBirthCore4086_Row
 clc
 adc #16
 sta.l SourceBirthCore4086_ReadOffset
 lda.l SourceBirthCore4086_Core
 tax
 ldy #48
SourceBirthCore4086_CoreLoop:
.a16
.i16
 phx
 lda.l SourceBirthCore4086_ReadOffset
 tax
 jsr SourceBirthCore4086_Read
 plx
 sta.l $40C000,x
 inx
 inx
 jsr SourceBirthCore4086_NextRead
 dey
 bne SourceBirthCore4086_CoreLoop
 lda.l SourceBirthCore4086_Flags
 tax
 ldy #16
SourceBirthCore4086_FlagLoop:
.a16
.i16
 phx
 lda.l SourceBirthCore4086_ReadOffset
 tax
 jsr SourceBirthCore4086_Read
 plx
 sta.l $43EB00,x
 inx
 inx
 jsr SourceBirthCore4086_NextRead
 dey
 bne SourceBirthCore4086_FlagLoop
 lda.l SourceBirthCore4086_Relation
 tax
 ldy #32
SourceBirthCore4086_RelationLoop:
.a16
.i16
 phx
 lda.l SourceBirthCore4086_ReadOffset
 tax
 jsr SourceBirthCore4086_Read
 plx
 sta.l $409000,x
 inx
 inx
 jsr SourceBirthCore4086_NextRead
 dey
 bne SourceBirthCore4086_RelationLoop
 lda.l SOURCE_RETIREMENT_ROLES
 inc a
 sta.l SOURCE_RETIREMENT_ROLES
 lda #2
 sta.l SourceBirthCore4086_Status
 jmp SourceBirthCore4086_Good
SourceBirthCore4086_NextRead:
.a16
.i16
 lda.l SourceBirthCore4086_ReadOffset
 inc a
 inc a
 sta.l SourceBirthCore4086_ReadOffset
 rts
SourceBirthCore4086_Read:
.a16
.i16
 phb
 sep #$20
.a8
 lda.l SourceBirthCore4086_Bank
 pha
 plb
 rep #$20
.a16
 lda.w $0000,x
 plb
 ora #0
 rts

SourceBirthCore4086_CheckIdle:
.a16
.i16
 php
 rep #$38
 pha
 lda.l SourceBirthCore4086_Ready
 beq SourceBirthCore4086_IdleGood
 cmp #$B4F9
 bne SourceBirthCore4086_IdleBad
 lda.l SourceBirthCore4086_Status
 beq SourceBirthCore4086_IdleGood
 cmp #2
 bne SourceBirthCore4086_IdleBad
SourceBirthCore4086_IdleGood:
.a16
.i16
 pla
 plp
 clc
 rtl
SourceBirthCore4086_IdleBad:
.a16
.i16
 pla
 plp
 sec
 rtl
