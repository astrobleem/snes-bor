; Literal common_attack_proc animating short circuit. Finished/air/resource
; branches remain explicit until their actual entity fields and services exist.
; Stable engine callback 17. No semantic-ID completion without this body.
SourceCommonAttackProc4086_Ready = $43BF60
SourceCommonAttackProc4086_Status = $43BF62
SourceCommonAttackProc4086_End = $43BF64
SourceCommonAttackProc4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceCommonAttackProc4086_Ready
 cmp #$B607
 beq SourceCommonAttackProc4086_ReadyChecked
 jmp SourceCommonAttackProc4086_Bad
SourceCommonAttackProc4086_ReadyChecked:
.a16
.i16
 lda.l SourceCommonAttackProc4086_Status
 beq SourceCommonAttackProc4086_Start
 cmp #2
 beq SourceCommonAttackProc4086_Start
 jmp SourceCommonAttackProc4086_Bad
SourceCommonAttackProc4086_Start:
.a16
.i16
 lda #1
 sta.l SourceCommonAttackProc4086_Status
 jsl SourceAI4086_CheckOwner
 bcc SourceCommonAttackProc4086_OwnerChecked
 jmp SourceCommonAttackProc4086_Bad
SourceCommonAttackProc4086_OwnerChecked:
.a16
.i16
 lda.l SourceAI4086_State
 cmp #1
 beq SourceCommonAttackProc4086_ActionChecked
 jmp SourceCommonAttackProc4086_Bad
SourceCommonAttackProc4086_ActionChecked:
.a16
.i16
 lda.l SourceAI4086_Callback
 cmp #17
 beq SourceCommonAttackProc4086_CallbackChecked
 jmp SourceCommonAttackProc4086_Bad
SourceCommonAttackProc4086_CallbackChecked:
.a16
.i16
 lda.l SourceAI4086_Callback+2
 beq SourceCommonAttackProc4086_CallbackHighChecked
 jmp SourceCommonAttackProc4086_Bad
SourceCommonAttackProc4086_CallbackHighChecked:
.a16
.i16
 lda.l SourceAI4086_Life
 tax
 lda.l $43900C,x
 cmp #17
 beq SourceCommonAttackProc4086_LiveActionChecked
 jmp SourceCommonAttackProc4086_Bad
SourceCommonAttackProc4086_LiveActionChecked:
.a16
.i16
 lda.l $43900E,x
 beq SourceCommonAttackProc4086_Animating
 jmp SourceCommonAttackProc4086_Bad
SourceCommonAttackProc4086_Animating:
.a16
.i16
 lda.l SourceAI4086_Slot
 asl a
 asl a
 pha
 asl a
 asl a
 clc
 adc 1,s
 tax
 pla
 lda.l $41F510,x
 bne SourceCommonAttackProc4086_Done
 jmp SourceCommonAttackProc4086_Bad
SourceCommonAttackProc4086_Done:
.a16
.i16
 lda #2
 sta.l SourceCommonAttackProc4086_Status
 lda #0
 ply
 plx
 plp
 clc
 rtl
SourceCommonAttackProc4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceCommonAttackProc4086_Status
 ply
 plx
 plp
 sec
 rtl
