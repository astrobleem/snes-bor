; Actual common_think range query. A=target physical slot (FFFF=NULL), X=role.
; Reads current mutable animation cache; no birth-model identity substitution.
; Neither source macro nor this adapter inserts target exists/dead filtering.
; Numeric predicate is explicit ACCEPTED_COMPAT_Q16_16.
SourceEntityRange4086_Ready = $43BE50
SourceEntityRange4086_Status = $43BE52
SourceEntityRange4086_TargetSlot = $43BE54
SourceEntityRange4086_Role = $43BE56
SourceEntityRange4086_Result = $43BE58
SourceEntityRange4086_TargetView = $43BE5C
SourceEntityRange4086_TargetSide = $43BE5E
SourceEntityRange4086_Handle = $43BE60
SourceEntityRange4086_End = $43BE62
SourceEntityRange4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 sta.l SourceEntityRange4086_TargetSlot
 txa
 sta.l SourceEntityRange4086_Role
 lda.l SourceEntityRange4086_Ready
 cmp #$B5F9
 beq SourceEntityRange4086_Guard1
 jmp SourceEntityRange4086_Bad
SourceEntityRange4086_Guard1:
.a16
.i16
 lda.l SourceEntityRange4086_Status
 beq SourceEntityRange4086_Start
 cmp #2
 beq SourceEntityRange4086_Guard2
 jmp SourceEntityRange4086_Bad
SourceEntityRange4086_Guard2:
.a16
.i16
SourceEntityRange4086_Start:
.a16
.i16
 lda #1
 sta.l SourceEntityRange4086_Status
 jsl SourceCommonThink4086_CheckOwner
 bcc SourceEntityRange4086_Guard3
 jmp SourceEntityRange4086_Bad
SourceEntityRange4086_Guard3:
.a16
.i16
 lda.l VmSourceEntity_Ready
 cmp #$B5EF
 beq SourceEntityRange4086_Guard4
 jmp SourceEntityRange4086_Bad
SourceEntityRange4086_Guard4:
.a16
.i16
 lda.l VmSourceEntity_Base
 cmp #$4000
 beq SourceEntityRange4086_Guard5
 jmp SourceEntityRange4086_Bad
SourceEntityRange4086_Guard5:
.a16
.i16
 lda.l VmSourceEntity_Bank
 cmp #$41
 beq SourceEntityRange4086_Guard6
 jmp SourceEntityRange4086_Bad
SourceEntityRange4086_Guard6:
.a16
.i16
 lda.l VmSourceEntity_Count
 cmp.l VmSourceWorld_Count
 beq SourceEntityRange4086_Guard7
 jmp SourceEntityRange4086_Bad
SourceEntityRange4086_Guard7:
.a16
.i16
 lda.l SourceEntityRange4086_TargetSlot
 cmp #$FFFF
 bne SourceEntityRange4086_NotNull
 jmp SourceEntityRange4086_False
SourceEntityRange4086_NotNull:
.a16
.i16
 cmp.l VmSourceWorld_Count
 bcc SourceEntityRange4086_Guard8
 jmp SourceEntityRange4086_Bad
SourceEntityRange4086_Guard8:
.a16
.i16
 asl a
 asl a
 asl a
 asl a
 sta.l SourceEntityRange4086_TargetView
 asl a
 asl a
 sta.l SourceEntityRange4086_TargetSide
 clc
 adc.l SourceEntityRange4086_TargetView
 clc
 adc #$4000
 sta.l SourceEntityRange4086_TargetView
 tax
 cmp.l $410000,x
 beq SourceEntityRange4086_Guard9
 jmp SourceEntityRange4086_Bad
SourceEntityRange4086_Guard9:
.a16
.i16
 lda.l $410002,x
 cmp #$41
 beq SourceEntityRange4086_Guard10
 jmp SourceEntityRange4086_Bad
SourceEntityRange4086_Guard10:
.a16
.i16
 lda.l SourceCheckRange4086_Ready
 cmp #$B5F7
 beq SourceEntityRange4086_Guard11
 jmp SourceEntityRange4086_Bad
SourceEntityRange4086_Guard11:
.a16
.i16
 lda.l SourceCheckRange4086_Status
 beq SourceEntityRange4086_NumericIdle
 cmp #2
 beq SourceEntityRange4086_Guard12
 jmp SourceEntityRange4086_Bad
SourceEntityRange4086_Guard12:
.a16
.i16
SourceEntityRange4086_NumericIdle:
.a16
.i16
 lda.l SourceEntityRange4086_Role
 cmp.l SourceModelAnimationCopy4086_Maximum
 bcc SourceEntityRange4086_Guard13
 jmp SourceEntityRange4086_Bad
SourceEntityRange4086_Guard13:
.a16
.i16
 asl a
 clc
 adc.l SourceAI4086_ModelOffset
 tax
 lda.l SOURCE_MODEL_ANIMATION_CACHE,x
 sta.l SourceEntityRange4086_Handle
 jsl SourceAnimationRange4086_Query
 bcc SourceEntityRange4086_Guard14
 jmp SourceEntityRange4086_Bad
SourceEntityRange4086_Guard14:
.a16
.i16
 lda.l SourceAI4086_View
 tax
 lda.l $410008,x
 cmp #BOR_VT_DECIMAL
 beq SourceEntityRange4086_Guard15
 jmp SourceEntityRange4086_Bad
SourceEntityRange4086_Guard15:
.a16
.i16
 lda.l $41000A,x
 beq SourceEntityRange4086_Guard16
 jmp SourceEntityRange4086_Bad
SourceEntityRange4086_Guard16:
.a16
.i16
 lda.l $410030,x
 cmp #BOR_VT_DECIMAL
 beq SourceEntityRange4086_Guard17
 jmp SourceEntityRange4086_Bad
SourceEntityRange4086_Guard17:
.a16
.i16
 lda.l $410032,x
 beq SourceEntityRange4086_Guard18
 jmp SourceEntityRange4086_Bad
SourceEntityRange4086_Guard18:
.a16
.i16
 lda.l $410038,x
 cmp #BOR_VT_DECIMAL
 beq SourceEntityRange4086_Guard19
 jmp SourceEntityRange4086_Bad
SourceEntityRange4086_Guard19:
.a16
.i16
 lda.l $41003A,x
 beq SourceEntityRange4086_Guard20
 jmp SourceEntityRange4086_Bad
SourceEntityRange4086_Guard20:
.a16
.i16
 lda.l SourceEntityRange4086_TargetView
 tax
 lda.l $410008,x
 cmp #BOR_VT_DECIMAL
 beq SourceEntityRange4086_Guard21
 jmp SourceEntityRange4086_Bad
SourceEntityRange4086_Guard21:
.a16
.i16
 lda.l $41000A,x
 beq SourceEntityRange4086_Guard22
 jmp SourceEntityRange4086_Bad
SourceEntityRange4086_Guard22:
.a16
.i16
 lda.l $410030,x
 cmp #BOR_VT_DECIMAL
 beq SourceEntityRange4086_Guard23
 jmp SourceEntityRange4086_Bad
SourceEntityRange4086_Guard23:
.a16
.i16
 lda.l $410032,x
 beq SourceEntityRange4086_Guard24
 jmp SourceEntityRange4086_Bad
SourceEntityRange4086_Guard24:
.a16
.i16
 lda.l $410038,x
 cmp #BOR_VT_DECIMAL
 beq SourceEntityRange4086_Guard25
 jmp SourceEntityRange4086_Bad
SourceEntityRange4086_Guard25:
.a16
.i16
 lda.l $41003A,x
 beq SourceEntityRange4086_Guard26
 jmp SourceEntityRange4086_Bad
SourceEntityRange4086_Guard26:
.a16
.i16
 lda.l SourceAI4086_View
 tax
 lda.l $410018,x
 cmp #BOR_VT_INTEGER
 beq SourceEntityRange4086_Guard27
 jmp SourceEntityRange4086_Bad
SourceEntityRange4086_Guard27:
.a16
.i16
 lda.l $41001A,x
 beq SourceEntityRange4086_Guard28
 jmp SourceEntityRange4086_Bad
SourceEntityRange4086_Guard28:
.a16
.i16
 lda.l $41001C,x
 sta.l SourceCheckRange4086_Direction
 lda.l $41001E,x
 sta.l SourceCheckRange4086_Direction+2
 lda.l SourceAI4086_View
 tax
 lda.l $410034,x
 sta.l SourceCheckRange4086_Source+0
 lda.l $410036,x
 sta.l SourceCheckRange4086_Source+2
 lda.l $41003C,x
 sta.l SourceCheckRange4086_Source+4
 lda.l $41003E,x
 sta.l SourceCheckRange4086_Source+6
 lda.l $41000C,x
 sta.l SourceCheckRange4086_Source+8
 lda.l $41000E,x
 sta.l SourceCheckRange4086_Source+10
 lda.l SourceAI4086_Side
 tax
 lda.l $416830,x
 sta.l SourceCheckRange4086_Source+12
 lda.l $416832,x
 sta.l SourceCheckRange4086_Source+14
 lda.l SourceEntityRange4086_TargetView
 tax
 lda.l $410034,x
 sta.l SourceCheckRange4086_Target+0
 lda.l $410036,x
 sta.l SourceCheckRange4086_Target+2
 lda.l $41003C,x
 sta.l SourceCheckRange4086_Target+4
 lda.l $41003E,x
 sta.l SourceCheckRange4086_Target+6
 lda.l $41000C,x
 sta.l SourceCheckRange4086_Target+8
 lda.l $41000E,x
 sta.l SourceCheckRange4086_Target+10
 lda.l SourceEntityRange4086_TargetSide
 tax
 lda.l $416830,x
 sta.l SourceCheckRange4086_Target+12
 lda.l $416832,x
 sta.l SourceCheckRange4086_Target+14
 lda #1
 sta.l SourceCheckRange4086_Present
 jsl SourceCheckRange4086_Execute
 bcc SourceEntityRange4086_Guard29
 jmp SourceEntityRange4086_Bad
SourceEntityRange4086_Guard29:
.a16
.i16
 lda.l SourceCheckRange4086_Result
 sta.l SourceEntityRange4086_Result
 lda.l SourceCheckRange4086_Result+2
 sta.l SourceEntityRange4086_Result+2
 bra SourceEntityRange4086_Done
SourceEntityRange4086_False:
.a16
.i16
 lda #0
 sta.l SourceEntityRange4086_Result
 sta.l SourceEntityRange4086_Result+2
SourceEntityRange4086_Done:
.a16
.i16
 lda #2
 sta.l SourceEntityRange4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceEntityRange4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceEntityRange4086_Status
 ply
 plx
 plp
 sec
 rtl
