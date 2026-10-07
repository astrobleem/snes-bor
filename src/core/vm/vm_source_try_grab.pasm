; common_try_grab(NULL): real mandatory C rand and read-only early false gates.
; Non-null animation with chance zero/idling requires find_ent_here/trygrab;
; those services remain explicitly unbound. No fabricated target response.
SourceTryGrab4086_Ready = $43BD76
SourceTryGrab4086_Status = $43BD78 ; 0 idle,2 false complete,3 fault
SourceTryGrab4086_End = $43BD7A
SourceTryGrab4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceTryGrab4086_Ready
 cmp #$B5EC
 beq SourceTryGrab4086_Lease
 jmp SourceTryGrab4086_Bad
SourceTryGrab4086_Lease:
.a16
.i16
 lda.l SourceTryGrab4086_Status
 beq SourceTryGrab4086_Idle
 jmp SourceTryGrab4086_Bad
SourceTryGrab4086_Idle:
.a16
.i16
 jsl SourceNormalAttack4086_CheckOwner
 bcc SourceTryGrab4086_Owner
 jmp SourceTryGrab4086_Bad
SourceTryGrab4086_Owner:
.a16
.i16
 lda.l SourceNormalAttack4086_State
 cmp #1
 beq SourceTryGrab4086_Random
 jmp SourceTryGrab4086_Bad
SourceTryGrab4086_Random:
.a16
.i16
 jsl SourceCRandom4086_Next
 bcc SourceTryGrab4086_Chance
 jmp SourceTryGrab4086_Bad
SourceTryGrab4086_Chance:
.a16
.i16
 lda.l SourceCRandom4086_Result
 and #7
 bne SourceTryGrab4086_False
 ; validanim is pure. Idling false short-circuits after that pure predicate.
 lda.l SourceAI4086_Flags
 tax
 lda.l $43EB00,x
 ora.l $43EB02,x
 beq SourceTryGrab4086_False
 lda.l SourceModelAnimationCopy4086_Maximum
 cmp #21
 bcs SourceTryGrab4086_Cache
 jmp SourceTryGrab4086_Bad
SourceTryGrab4086_Cache:
.a16
.i16
 lda.l SourceAI4086_ModelOffset
 tax
 lda.l SOURCE_MODEL_ANIMATION_CACHE+40,x ; ANI_THROW=20
 ora.l SOURCE_MODEL_ANIMATION_CACHE+34,x ; ANI_GRAB=17
 beq SourceTryGrab4086_False
 jmp SourceTryGrab4086_Bad
SourceTryGrab4086_False:
.a16
.i16
 lda #0
 sta.l SourceNormalAttack4086_Response
 sta.l SourceNormalAttack4086_Response+2
 lda #2
 sta.l SourceTryGrab4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceTryGrab4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceTryGrab4086_Status
 ply
 plx
 plp
 sec
 rtl
