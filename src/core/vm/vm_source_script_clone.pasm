; Synchronous constructor Script_Clear/Copy method-1 services. B5SC admits
; only shared animation programs without init/clear entries. The compiler
; validates B5SC/B4CO identity together before granting B5C1. No callback is
; skipped: a model with another script kind or entry fails compilation.
; Private 32-byte control lease in the former $43B800..$43BFFF free gap;
; existing current lifecycle ends $43B7FF, animation cache starts $43C000.
; Caller supplies Slot/Model. Clear preserves names/owners/scopes and empties
; values across this entity's lists; Bind installs shared-program initialized
; identity only after caller resets the destination script instance.
SourceScriptClone4086_Ready = $43B800
SourceScriptClone4086_Slot = $43B802
SourceScriptClone4086_Model = $43B804
SourceScriptClone4086_Status = $43B806
SourceScriptClone4086_Base = $43B808
SourceScriptClone4086_Bank = $43B80A
SourceScriptClone4086_Bytes = $43B80C
SourceScriptClone4086_Models = $43B80E
SourceScriptClone4086_Token = $43B810
SourceScriptClone4086_Relation = $43B812
SourceScriptClone4086_Mask = $43B814
SourceScriptClone4086_Program = $43B816
SourceScriptClone4086_Row = $43B818
SourceScriptClone4086_End = $43B820

SourceScriptClone4086_Clear:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jsr SourceScriptClone4086_Preflight
 bcc SourceScriptClone4086_Far_1
 jmp SourceScriptClone4086_Bad
SourceScriptClone4086_Far_1:
.a16
.i16
 lda.l SourceScriptClone4086_Relation
 tax
 lda.l $40902E,x
 ora.l $409030,x
 ora.l $409032,x
 ora.l $409034,x
 ora.l $409036,x
 beq SourceScriptClone4086_Far_2
 jmp SourceScriptClone4086_Bad
SourceScriptClone4086_Far_2:
.a16
.i16
 lda.l $40902C,x
 cmp #2
 bcc SourceScriptClone4086_Far_3
 jmp SourceScriptClone4086_Bad
SourceScriptClone4086_Far_3:
.a16
.i16
 ldx #0
 ldy #0
SourceScriptClone4086_ClearLoop:
.a16
.i16
 lda.l $418800,x
 cmp.l SourceScriptClone4086_Token
 beq SourceScriptClone4086_Far_4
 jmp SourceScriptClone4086_Next
SourceScriptClone4086_Far_4:
.a16
.i16
 lda.l $418802,x
 cmp #$0041
 beq SourceScriptClone4086_Far_5
 jmp SourceScriptClone4086_Next
SourceScriptClone4086_Far_5:
.a16
.i16
 lda #0
 sta.l $418808,x
 sta.l $41880A,x
 sta.l $41880C,x
 sta.l $41880E,x
SourceScriptClone4086_Next:
.a16
.i16
 txa
 clc
 adc #64
 tax
 iny
 tya
 cmp.l VmSourceVars_Count
 bcs SourceScriptClone4086_Far_6
 jmp SourceScriptClone4086_ClearLoop
SourceScriptClone4086_Far_6:
.a16
.i16
 lda.l SourceScriptClone4086_Relation
 tax
 lda #0
 sta.l $40902C,x
 sta.l $40902E,x
 jmp SourceScriptClone4086_Good

SourceScriptClone4086_Bind:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jsr SourceScriptClone4086_Preflight
 bcc SourceScriptClone4086_Far_7
 jmp SourceScriptClone4086_Bad
SourceScriptClone4086_Far_7:
.a16
.i16
 lda.l SourceScriptClone4086_Relation
 tax
 lda.l $40902C,x
 ora.l $40902E,x
 ora.l $409030,x
 ora.l $409032,x
 ora.l $409034,x
 ora.l $409036,x
 beq SourceScriptClone4086_Far_8
 jmp SourceScriptClone4086_Bad
SourceScriptClone4086_Far_8:
.a16
.i16
 lda.l VmSourceWorld_SideBase
 clc
 adc.l SourceScriptClone4086_Relation
 tax
 lda.l $410000,x
 cmp.l SourceScriptClone4086_Model
 beq SourceScriptClone4086_Far_9
 jmp SourceScriptClone4086_Bad
SourceScriptClone4086_Far_9:
.a16
.i16
 lda.l SourceScriptClone4086_Model
 asl a
 asl a
 asl a
 clc
 adc #24
 sta.l SourceScriptClone4086_Row
 tax
 jsr SourceScriptClone4086_Read
 cmp.l SourceScriptClone4086_Model
 beq SourceScriptClone4086_Far_10
 jmp SourceScriptClone4086_Bad
SourceScriptClone4086_Far_10:
.a16
.i16
 inx
 inx
 jsr SourceScriptClone4086_Read
 cmp #2
 bcc SourceScriptClone4086_Far_11
 jmp SourceScriptClone4086_Bad
SourceScriptClone4086_Far_11:
.a16
.i16
 sta.l SourceScriptClone4086_Mask
 inx
 inx
 jsr SourceScriptClone4086_Read
 sta.l SourceScriptClone4086_Program
 inx
 inx
 jsr SourceScriptClone4086_Read
 beq SourceScriptClone4086_Far_12
 jmp SourceScriptClone4086_Bad
SourceScriptClone4086_Far_12:
.a16
.i16
 lda.l SourceScriptClone4086_Mask
 bne SourceScriptClone4086_Far_13
 jmp SourceScriptClone4086_Absent
SourceScriptClone4086_Far_13:
.a16
.i16
 lda.l SourceScriptClone4086_Program
 cmp.l SourceAnimationCallback4086_Programs
 bcc SourceScriptClone4086_Far_14
 jmp SourceScriptClone4086_Bad
SourceScriptClone4086_Far_14:
.a16
.i16
 bra SourceScriptClone4086_CheckProgram
SourceScriptClone4086_Absent:
.a16
.i16
 lda.l SourceScriptClone4086_Program
 cmp #$FFFF
 beq SourceScriptClone4086_Far_15
 jmp SourceScriptClone4086_Bad
SourceScriptClone4086_Far_15:
.a16
.i16
SourceScriptClone4086_CheckProgram:
.a16
.i16
 ; Match the actual immutable B4CO model row's program before publishing.
 lda.l SourceScriptClone4086_Model
 asl a
 asl a
 asl a
 asl a
 clc
 adc #32
 clc
 adc.l SourceAnimationCallback4086_Base
 bcc SourceScriptClone4086_Far_16
 jmp SourceScriptClone4086_Bad
SourceScriptClone4086_Far_16:
.a16
.i16
 tax
 phb
 sep #$20
.a8
 lda.l SourceAnimationCallback4086_Bank
 pha
 plb
 rep #$20
.a16
 lda.w $0000,x
 sta.l SourceScriptClone4086_Row
 lda.w $0002,x
 plb
 cmp.l SourceScriptClone4086_Program
 beq SourceScriptClone4086_Far_17
 jmp SourceScriptClone4086_Bad
SourceScriptClone4086_Far_17:
.a16
.i16
 lda.l SourceScriptClone4086_Row
 cmp.l SourceScriptClone4086_Model
 beq SourceScriptClone4086_Far_17_ModelID
 jmp SourceScriptClone4086_Bad
SourceScriptClone4086_Far_17_ModelID:
.a16
.i16
 lda.l SourceScriptClone4086_Relation
 tax
 lda.l SourceScriptClone4086_Mask
 sta.l $40902C,x
 lda #0
 sta.l $40902E,x
SourceScriptClone4086_Good:
.a16
.i16
 lda #2
 sta.l SourceScriptClone4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceScriptClone4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceScriptClone4086_Status
 ply
 plx
 plp
 sec
 rtl

SourceScriptClone4086_Preflight:
.a16
.i16
 lda.l SourceScriptClone4086_Ready
 cmp #$B5C1
 beq SourceScriptClone4086_Far_18
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_18:
.a16
.i16
 lda.l SourceScriptClone4086_Status
 cmp #3
 bne SourceScriptClone4086_Far_19
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_19:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceScriptClone4086_Far_20
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_20:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourceScriptClone4086_Far_21
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_21:
.a16
.i16
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 beq SourceScriptClone4086_Far_22
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_22:
.a16
.i16
 lda.l VmSourceWorld_Count
 bne SourceScriptClone4086_Far_23
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_23:
.a16
.i16
 cmp #129
 bcc SourceScriptClone4086_Far_24
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_24:
.a16
.i16
 lda.l SourceScriptClone4086_Slot
 cmp.l VmSourceWorld_Count
 bcc SourceScriptClone4086_Far_25
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_25:
.a16
.i16
 asl a
 asl a
 asl a
 asl a
 sta.l SourceScriptClone4086_Token
 asl a
 asl a
 sta.l SourceScriptClone4086_Relation
 clc
 adc.l SourceScriptClone4086_Token
 clc
 adc #$4000
 sta.l SourceScriptClone4086_Token
 tax
 cmp.l $410000,x
 beq SourceScriptClone4086_Far_26
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_26:
.a16
.i16
 lda.l $410002,x
 cmp #$0041
 beq SourceScriptClone4086_Far_27
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_27:
.a16
.i16
 lda.l VmSourceVars_Ready
 cmp #$B4A4
 beq SourceScriptClone4086_Far_28
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_28:
.a16
.i16
 lda.l VmSourceVars_Base
 cmp #$8800
 beq SourceScriptClone4086_Far_29
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_29:
.a16
.i16
 lda.l VmSourceVars_Bank
 and #$00FF
 cmp #$41
 beq SourceScriptClone4086_Far_30
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_30:
.a16
.i16
 lda.l VmSourceVars_Count
 bne SourceScriptClone4086_Far_31
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_31:
.a16
.i16
 cmp #385
 bcc SourceScriptClone4086_Far_32
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_32:
.a16
.i16
 lda.l SourceAnimationCallback4086_Ready
 cmp #$B4E6
 beq SourceScriptClone4086_Far_33
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_33:
.a16
.i16
 lda.l SourceAnimationCallback4086_Base
 cmp #$8000
 bcs SourceScriptClone4086_Far_34
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_34:
.a16
.i16
 lda.l SourceAnimationCallback4086_Bank
 bne SourceScriptClone4086_Far_35
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_35:
.a16
.i16
 cmp #64
 bcc SourceScriptClone4086_Far_36
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_36:
.a16
.i16
 lda.l SourceScriptClone4086_Models
 bne SourceScriptClone4086_Far_37
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_37:
.a16
.i16
 cmp #17
 bcc SourceScriptClone4086_Far_38
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_38:
.a16
.i16
 cmp.l VmSourceWorld_TemplateCount
 beq SourceScriptClone4086_Far_39
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_39:
.a16
.i16
 cmp.l SourceAnimationCallback4086_Models
 beq SourceScriptClone4086_Far_40
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_40:
.a16
.i16
 asl a
 asl a
 asl a
 clc
 adc #24
 cmp.l SourceScriptClone4086_Bytes
 beq SourceScriptClone4086_Far_41
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_41:
.a16
.i16
 dec a
 clc
 adc.l SourceScriptClone4086_Base
 bcc SourceScriptClone4086_Far_42
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_42:
.a16
.i16
 lda.l SourceScriptClone4086_Model
 cmp.l SourceScriptClone4086_Models
 bcc SourceScriptClone4086_Far_43
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_43:
.a16
.i16
 lda.l SourceScriptClone4086_Base
 cmp #$8000
 bcs SourceScriptClone4086_Far_44
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_44:
.a16
.i16
 lda.l SourceScriptClone4086_Bank
 bne SourceScriptClone4086_Far_45
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_45:
.a16
.i16
 cmp #64
 bcc SourceScriptClone4086_Far_46
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_46:
.a16
.i16
 ldx #0
 jsr SourceScriptClone4086_Read
 cmp #$3542
 beq SourceScriptClone4086_Far_47
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_47:
.a16
.i16
 ldx #2
 jsr SourceScriptClone4086_Read
 cmp #$4353
 beq SourceScriptClone4086_Far_48
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_48:
.a16
.i16
 ldx #4
 jsr SourceScriptClone4086_Read
 cmp #1
 beq SourceScriptClone4086_Far_49
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_49:
.a16
.i16
 ldx #6
 jsr SourceScriptClone4086_Read
 cmp #8
 beq SourceScriptClone4086_Far_50
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_50:
.a16
.i16
 ldx #8
 jsr SourceScriptClone4086_Read
 cmp.l SourceScriptClone4086_Models
 beq SourceScriptClone4086_Far_51
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_51:
.a16
.i16
 ldx #10
 jsr SourceScriptClone4086_Read
 beq SourceScriptClone4086_Far_52
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_52:
.a16
.i16
 ldx #12
 jsr SourceScriptClone4086_Read
 clc
 adc #24
 cmp.l SourceScriptClone4086_Bytes
 beq SourceScriptClone4086_Far_53
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_53:
.a16
.i16
 ldx #14
 jsr SourceScriptClone4086_Read
 beq SourceScriptClone4086_Far_54
 jmp SourceScriptClone4086_PreflightBad
SourceScriptClone4086_Far_54:
.a16
.i16
 clc
 rts
SourceScriptClone4086_PreflightBad:
.a16
.i16
 sec
 rts
SourceScriptClone4086_Read:
.a16
.i16
 phb
 phx
 txa
 clc
 adc.l SourceScriptClone4086_Base
 tax
 sep #$20
.a8
 lda.l SourceScriptClone4086_Bank
 pha
 plb
 rep #$20
.a16
 lda.w $0000,x
 plx
 plb
 ora #0
 rts

; Nonpublishing paired ROM model/program validation for constructor preflight.
SourceScriptClone4086_CheckModelProgram:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jsr SourceScriptClone4086_Preflight
 bcc SourceScriptClone4086_ProgramCheckStart
 jmp SourceScriptClone4086_Bad
SourceScriptClone4086_ProgramCheckStart:
.a16
.i16
 lda.l SourceScriptClone4086_Model
 asl a
 asl a
 asl a
 clc
 adc #24
 sta.l SourceScriptClone4086_Row
 tax
 jsr SourceScriptClone4086_Read
 cmp.l SourceScriptClone4086_Model
 beq SourceScriptClone4086_ProgramCheck_Far_10
 jmp SourceScriptClone4086_Bad
SourceScriptClone4086_ProgramCheck_Far_10:
.a16
.i16
 inx
 inx
 jsr SourceScriptClone4086_Read
 cmp #2
 bcc SourceScriptClone4086_ProgramCheck_Far_11
 jmp SourceScriptClone4086_Bad
SourceScriptClone4086_ProgramCheck_Far_11:
.a16
.i16
 sta.l SourceScriptClone4086_Mask
 inx
 inx
 jsr SourceScriptClone4086_Read
 sta.l SourceScriptClone4086_Program
 inx
 inx
 jsr SourceScriptClone4086_Read
 beq SourceScriptClone4086_ProgramCheck_Far_12
 jmp SourceScriptClone4086_Bad
SourceScriptClone4086_ProgramCheck_Far_12:
.a16
.i16
 lda.l SourceScriptClone4086_Mask
 bne SourceScriptClone4086_ProgramCheck_Far_13
 jmp SourceScriptClone4086_ProgramCheck_Absent
SourceScriptClone4086_ProgramCheck_Far_13:
.a16
.i16
 lda.l SourceScriptClone4086_Program
 cmp.l SourceAnimationCallback4086_Programs
 bcc SourceScriptClone4086_ProgramCheck_Far_14
 jmp SourceScriptClone4086_Bad
SourceScriptClone4086_ProgramCheck_Far_14:
.a16
.i16
 bra SourceScriptClone4086_ProgramCheck_CheckProgram
SourceScriptClone4086_ProgramCheck_Absent:
.a16
.i16
 lda.l SourceScriptClone4086_Program
 cmp #$FFFF
 beq SourceScriptClone4086_ProgramCheck_Far_15
 jmp SourceScriptClone4086_Bad
SourceScriptClone4086_ProgramCheck_Far_15:
.a16
.i16
SourceScriptClone4086_ProgramCheck_CheckProgram:
.a16
.i16
 ; Match the actual immutable B4CO model row's program before publishing.
 lda.l SourceScriptClone4086_Model
 asl a
 asl a
 asl a
 asl a
 clc
 adc #32
 clc
 adc.l SourceAnimationCallback4086_Base
 bcc SourceScriptClone4086_ProgramCheck_Far_16
 jmp SourceScriptClone4086_Bad
SourceScriptClone4086_ProgramCheck_Far_16:
.a16
.i16
 tax
 phb
 sep #$20
.a8
 lda.l SourceAnimationCallback4086_Bank
 pha
 plb
 rep #$20
.a16
 lda.w $0000,x
 sta.l SourceScriptClone4086_Row
 lda.w $0002,x
 plb
 cmp.l SourceScriptClone4086_Program
 beq SourceScriptClone4086_ProgramCheck_Far_17
 jmp SourceScriptClone4086_Bad
SourceScriptClone4086_ProgramCheck_Far_17:
.a16
.i16
 lda.l SourceScriptClone4086_Row
 cmp.l SourceScriptClone4086_Model
 beq SourceScriptClone4086_ProgramCheck_Far_17_ModelID
 jmp SourceScriptClone4086_Bad
SourceScriptClone4086_ProgramCheck_Far_17_ModelID:
.a16
.i16
 jmp SourceScriptClone4086_Good
