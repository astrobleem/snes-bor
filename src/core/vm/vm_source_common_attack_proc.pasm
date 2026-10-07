; Literal common_attack_proc animating / airborne short circuits. Finished/resource
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
 phd
 tsc
 sec
 sbc #10
 tcs
 inc a
 tcd
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
 beq SourceCommonAttackProc4086_Airborne
 jmp SourceCommonAttackProc4086_Done
SourceCommonAttackProc4086_Airborne:
.a16
.i16
 lda.l SourceAI4086_View
 tax
 lda.l $410008,x
 cmp #BOR_VT_DECIMAL
 beq SourceCommonAttackProc4086_YTag
 jmp SourceCommonAttackProc4086_Bad
SourceCommonAttackProc4086_YTag:
.a16
.i16
 lda.l $41000A,x
 beq SourceCommonAttackProc4086_YRead
 jmp SourceCommonAttackProc4086_Bad
SourceCommonAttackProc4086_YRead:
.a16
.i16
 lda.l $41000C,x
 sta $00
 lda.l $41000E,x
 sta $02
 eor #$8000
 sta $08
 lda.l SourceAI4086_Side
 tax
 lda.l $416830,x
 sta $04
 lda.l $416832,x
 sta $06
 eor #$8000
 cmp $08
 bcc SourceCommonAttackProc4086_YGreater
 bne SourceCommonAttackProc4086_BaseGreater
 lda $04
 cmp $00
 bcc SourceCommonAttackProc4086_YGreater
SourceCommonAttackProc4086_BaseGreater:
.a16
.i16
 lda $04
 sec
 sbc $00
 lda $06
 sbc $02
 bra SourceCommonAttackProc4086_CompareAir
SourceCommonAttackProc4086_YGreater:
.a16
.i16
 lda $00
 sec
 sbc $04
 lda $02
 sbc $06
SourceCommonAttackProc4086_CompareAir:
.a16
.i16
 ; Exact absolute Q16.16 difference, including signed32 extreme pairs.
 ; Source float storage remains the declared ACCEPTED_COMPAT_Q16_16 policy.
 cmp #4
 bcs SourceCommonAttackProc4086_Done
 jmp SourceCommonAttackProc4086_Bad
SourceCommonAttackProc4086_Done:
.a16
.i16
 lda #2
 sta.l SourceCommonAttackProc4086_Status
 tsc
 clc
 adc #10
 tcs
 pld
 ply
 plx
 lda #0
 plp
 clc
 rtl
SourceCommonAttackProc4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceCommonAttackProc4086_Status
 tsc
 clc
 adc #10
 tcs
 pld
 ply
 plx
 lda #0
 plp
 sec
 rtl
