; Actual warp early predicates, busy, and grab/no-link handler paths.
; Full FOLLOW+parent distance/action path explicitly requires another backend.
; No source actor-name dispatch; full DWORD idling and physical link truth.
SourceAIReadonly4086_Ready = $43BD48
SourceAIReadonly4086_Status = $43BD4A
SourceAIReadonly4086_Relation = $43BD4C
SourceAIReadonly4086_Result = $43BD4E
SourceAIReadonly4086_Air = $43BD50
SourceAIReadonly4086_End = $43BD52
SourceAIReadonly4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceAIReadonly4086_Ready
 cmp #$B5E8
 beq SourceAIReadonly4086_Far1
 jmp SourceAIReadonly4086_Bad
SourceAIReadonly4086_Far1:
.a16
.i16
 lda.l SourceAIReadonly4086_Status
 beq SourceAIReadonly4086_Far2
 jmp SourceAIReadonly4086_Bad
SourceAIReadonly4086_Far2:
.a16
.i16
 lda.l SourceRetirement4086_Ready
 cmp #$B4F8
 beq SourceAIReadonly4086_Far3
 jmp SourceAIReadonly4086_Bad
SourceAIReadonly4086_Far3:
.a16
.i16
 jsl SourceCommonThink4086_CheckOwner
 bcc SourceAIReadonly4086_Far4
 jmp SourceAIReadonly4086_Bad
SourceAIReadonly4086_Far4:
.a16
.i16
 lda.l SourceCommonThink4086_State
 cmp #1
 bne SourceAIReadonly4086_Far5
 jmp SourceAIReadonly4086_Warp
SourceAIReadonly4086_Far5:
.a16
.i16
 cmp #2
 bne SourceAIReadonly4086_NotLie
 jmp SourceAIReadonly4086_LieAbsent
SourceAIReadonly4086_NotLie:
.a16
.i16
 cmp #3
 bne SourceAIReadonly4086_NotGrabbed
 jmp SourceAIReadonly4086_GrabbedAbsent
SourceAIReadonly4086_NotGrabbed:
.a16
.i16
 cmp #5
 bne SourceAIReadonly4086_NotEscape
 jmp SourceAIReadonly4086_EscapeAbsent
SourceAIReadonly4086_NotEscape:
.a16
.i16
 cmp #4
 bne SourceAIReadonly4086_GrabDispatchNext
 jmp SourceAIReadonly4086_Grab
SourceAIReadonly4086_GrabDispatchNext:
.a16
.i16
 cmp #7
 bne SourceAIReadonly4086_NotAttack
 jmp SourceAIReadonly4086_Attack
SourceAIReadonly4086_NotAttack:
.a16
.i16
 cmp #8
 bne SourceAIReadonly4086_NotMove
 jmp SourceAIReadonly4086_Move
SourceAIReadonly4086_NotMove:
.a16
.i16
 cmp #6
 bne SourceAIReadonly4086_Far6
 jmp SourceAIReadonly4086_Busy
SourceAIReadonly4086_Far6:
.a16
.i16
 jmp SourceAIReadonly4086_Bad
SourceAIReadonly4086_Warp:
.a16
.i16
 jsr SourceAIReadonly4086_Link
 ora #0
 beq SourceAIReadonly4086_Far7
 jmp SourceAIReadonly4086_False
SourceAIReadonly4086_Far7:
.a16
.i16
 lda.l SourceAI4086_Life
 tax
 lda.l $439032,x
 beq SourceAIReadonly4086_Far8
 jmp SourceAIReadonly4086_False
SourceAIReadonly4086_Far8:
.a16
.i16
 lda.l $439030,x
 cmp #10
 beq SourceAIReadonly4086_Far9
 jmp SourceAIReadonly4086_False
SourceAIReadonly4086_Far9:
.a16
.i16
 lda.l SourceAIReadonly4086_Relation
 tax
 lda.l $409000,x
 ora.l $409002,x
 bne SourceAIReadonly4086_Far10
 jmp SourceAIReadonly4086_False
SourceAIReadonly4086_Far10:
.a16
.i16
 ; A true FOLLOW+parent needs range/pointer/distance and npc_warp semantics.
 jmp SourceAIReadonly4086_Bad
SourceAIReadonly4086_LieAbsent:
.a16
.i16
 ; Pinned ANI_RISEATTACK. rand32 occurs AFTER validanim in ai_check_lie.
 lda #49
 jmp SourceAIReadonly4086_AnimationAbsent
SourceAIReadonly4086_GrabbedAbsent:
.a16
.i16
 ; Pinned ANI_SPECIAL. Earlier predicates are read-only.
 lda #21
 jmp SourceAIReadonly4086_AnimationAbsent
SourceAIReadonly4086_EscapeAbsent:
.a16
.i16
 ; Pinned ANI_SPECIAL2. Earlier inair predicate is read-only.
 lda #36
SourceAIReadonly4086_AnimationAbsent:
.a16
.i16
 ; Check the current physical model's mutable cache, not its birth identity.
 cmp.l SourceModelAnimationCopy4086_Maximum
 bcc SourceAIReadonly4086_AnimationBounded
 jmp SourceAIReadonly4086_Bad
SourceAIReadonly4086_AnimationBounded:
.a16
.i16
 asl a
 clc
 adc.l SourceAI4086_ModelOffset
 tax
 lda.l SOURCE_MODEL_ANIMATION_CACHE,x
 beq SourceAIReadonly4086_AnimationMissing
 ; Non-null requires real numframes and the conditional executable handler.
 ; Do not treat presence as a no-op, including inherited/switched handles.
 jmp SourceAIReadonly4086_Bad
SourceAIReadonly4086_AnimationMissing:
.a16
.i16
 jmp SourceAIReadonly4086_False
SourceAIReadonly4086_Grab:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Ready
 cmp #$B4EB
 beq SourceAIReadonly4086_GrabLease
 jmp SourceAIReadonly4086_Bad
SourceAIReadonly4086_GrabLease:
.a16
.i16
 jsr SourceAIReadonly4086_Core
 lda.l $40C050,x
 ora.l $40C052,x
 bne SourceAIReadonly4086_GrabActive
 jmp SourceAIReadonly4086_False
SourceAIReadonly4086_GrabActive:
.a16
.i16
 lda.l $40C058,x
 ora.l $40C05A,x
 beq SourceAIReadonly4086_GrabNotAttacking
 jmp SourceAIReadonly4086_False
SourceAIReadonly4086_GrabNotAttacking:
.a16
.i16
 jsr SourceAIReadonly4086_Link
 ora #0
 beq SourceAIReadonly4086_GrabNoVictim
 ; Real linked common_grab_check must execute release/throw/attack services.
 jmp SourceAIReadonly4086_Bad
SourceAIReadonly4086_GrabNoVictim:
.a16
.i16
 ; common_grab_check returns before any mutation when other == NULL.
 ; ai_check_grab still returns 1, short-circuiting common_think.
 jmp SourceAIReadonly4086_True
SourceAIReadonly4086_Attack:
.a16
.i16
 ; Pinned THINK_SPEED=2; (unsigned time / 2) % 4 uses bits 1..2.
 lda.l VmSourceWorld_Time
 lsr a
 and #3
 bne SourceAIReadonly4086_AttackTick
 jmp SourceAIReadonly4086_False
SourceAIReadonly4086_AttackTick:
.a16
.i16
 jsr SourceAIReadonly4086_CoreLease
 bcc SourceAIReadonly4086_AttackCore
 jmp SourceAIReadonly4086_Bad
SourceAIReadonly4086_AttackCore:
.a16
.i16
 jsr SourceAIReadonly4086_Core
 lda.l $40C038,x
 cmp #$FFFF
 bne SourceAIReadonly4086_AttackMask
 lda.l $40C03A,x
 cmp #$FFFF
 bne SourceAIReadonly4086_AttackMask
 jmp SourceAIReadonly4086_False
SourceAIReadonly4086_AttackMask:
.a16
.i16
 ; MASK_AIATTACK1=0000FFFF: equality, not separate bit tests.
 lda.l $40C038,x
 cmp #1
 beq SourceAIReadonly4086_AttackDisabled
 cmp #2
 beq SourceAIReadonly4086_AttackDisabled
 cmp #4
 bne SourceAIReadonly4086_AttackAir
SourceAIReadonly4086_AttackDisabled:
.a16
.i16
 jmp SourceAIReadonly4086_False
SourceAIReadonly4086_AttackAir:
.a16
.i16
 jsr SourceAIReadonly4086_InAir
 bcc SourceAIReadonly4086_AttackAirChecked
 jmp SourceAIReadonly4086_Bad
SourceAIReadonly4086_AttackAirChecked:
.a16
.i16
 ora #0
 beq SourceAIReadonly4086_AttackUnbound
 jmp SourceAIReadonly4086_False
SourceAIReadonly4086_AttackUnbound:
.a16
.i16
 ; Optional source capability executes real selectors in source order.
 jsl SourceNormalAttackRun4086_Execute
 bcc SourceAIReadonly4086_AttackRan
 jmp SourceAIReadonly4086_Bad
SourceAIReadonly4086_AttackRan:
.a16
.i16
 lda.l SourceNormalAttackRun4086_Status
 cmp #1
 bne SourceAIReadonly4086_AttackComplete
 lda #1
 sta.l SourceAIReadonly4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceAIReadonly4086_Continue:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceAIReadonly4086_Ready
 cmp #$B5E8
 beq SourceAIReadonly4086_ContinueReady
 jmp SourceAIReadonly4086_Bad
SourceAIReadonly4086_ContinueReady:
.a16
.i16
 lda.l SourceAIReadonly4086_Status
 cmp #1
 beq SourceAIReadonly4086_ContinuePending
 jmp SourceAIReadonly4086_Bad
SourceAIReadonly4086_ContinuePending:
.a16
.i16
 jsl SourceCommonThink4086_CheckOwner
 bcc SourceAIReadonly4086_ContinueOwner
 jmp SourceAIReadonly4086_Bad
SourceAIReadonly4086_ContinueOwner:
.a16
.i16
 lda.l SourceCommonThink4086_State
 cmp #7
 beq SourceAIReadonly4086_ContinuePhase
 jmp SourceAIReadonly4086_Bad
SourceAIReadonly4086_ContinuePhase:
.a16
.i16
 jsl SourceNormalAttackRun4086_Continue
 bcc SourceAIReadonly4086_AttackRan
 jmp SourceAIReadonly4086_Bad
SourceAIReadonly4086_AttackComplete:
.a16
.i16
 lda.l SourceNormalAttack4086_Result
 beq SourceAIReadonly4086_AttackFalse
 jmp SourceAIReadonly4086_True
SourceAIReadonly4086_AttackFalse:
.a16
.i16
 jmp SourceAIReadonly4086_False
SourceAIReadonly4086_Move:
.a16
.i16
 jsr SourceAIReadonly4086_CoreLease
 bcc SourceAIReadonly4086_MoveCore
 jmp SourceAIReadonly4086_Bad
SourceAIReadonly4086_MoveCore:
.a16
.i16
 ; Source common_move computes inair before interpreting aimove.
 jsr SourceAIReadonly4086_InAir
 bcc SourceAIReadonly4086_MoveAirChecked
 jmp SourceAIReadonly4086_Bad
SourceAIReadonly4086_MoveAirChecked:
.a16
.i16
 sta.l SourceAIReadonly4086_Air
 jsr SourceAIReadonly4086_Core
 lda.l $40C034,x
 cmp #$FFFF
 bne SourceAIReadonly4086_MoveMask
 lda.l $40C036,x
 cmp #$FFFF
 bne SourceAIReadonly4086_MoveMask
 jmp SourceAIReadonly4086_False
SourceAIReadonly4086_MoveMask:
.a16
.i16
 lda.l $40C034,x
 and #$0780
 beq SourceAIReadonly4086_MoveOrdinary
 ; Biker/arrow/star/bomb have priority even with NOMOVE or an airborne actor.
 jmp SourceAIReadonly4086_Bad
SourceAIReadonly4086_MoveOrdinary:
.a16
.i16
 lda.l $40C034,x
 and #$0800
 beq SourceAIReadonly4086_MoveAir
 jmp SourceAIReadonly4086_False
SourceAIReadonly4086_MoveAir:
.a16
.i16
 lda.l SourceAIReadonly4086_Air
 beq SourceAIReadonly4086_MoveUnbound
 jmp SourceAIReadonly4086_False
SourceAIReadonly4086_MoveUnbound:
.a16
.i16
 ; Real grounded movement target/item/turn/path services remain explicit.
 jmp SourceAIReadonly4086_Bad
SourceAIReadonly4086_Busy:
.a16
.i16
 jsr SourceAIReadonly4086_Link
 ora #0
 beq SourceAIReadonly4086_Far11
 jmp SourceAIReadonly4086_True
SourceAIReadonly4086_Far11:
.a16
.i16
 lda.l SourceAI4086_Flags
 tax
 lda.l $43EB00,x
 ora.l $43EB02,x
 beq SourceAIReadonly4086_Far12
 jmp SourceAIReadonly4086_False
SourceAIReadonly4086_Far12:
.a16
.i16
SourceAIReadonly4086_True:
.a16
.i16
 lda #1
 jmp SourceAIReadonly4086_Publish
SourceAIReadonly4086_False:
.a16
.i16
 lda #0
SourceAIReadonly4086_Publish:
.a16
.i16
 sta.l SourceAIReadonly4086_Result
 sta.l SourceCommonThink4086_Response
 lda #0
 sta.l SourceCommonThink4086_Response+2
 lda #2
 sta.l SourceAIReadonly4086_Status
 lda #0
 ply
 plx
 plp
 clc
 rtl
SourceAIReadonly4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceAIReadonly4086_Status
 lda #0
 ply
 plx
 plp
 sec
 rtl
SourceAIReadonly4086_Link:
.a16
.i16
 lda.l SourceAI4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l SourceAIReadonly4086_Relation
 tax
 lda.l $40901C,x
 ora.l $40901E,x
 rts

SourceAIReadonly4086_Core:
.a16
.i16
 lda.l SourceAI4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 pha
 asl a
 clc
 adc 1,s
 tax
 pla
 rts
SourceAIReadonly4086_CoreLease:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Ready
 cmp #$B4EB
 bne SourceAIReadonly4086_CoreLeaseBad
 clc
 rts
SourceAIReadonly4086_CoreLeaseBad:
.a16
.i16
 sec
 rts
SourceAIReadonly4086_InAir:
.a16
.i16
 lda.l SourceAI4086_View
 tax
 lda.l $410008,x
 cmp #2
 bne SourceAIReadonly4086_InAirBad
 lda.l $41000A,x
 bne SourceAIReadonly4086_InAirBad
 lda.l $41000C,x
 sta.l SourceModelEntityCopy4086_Lo
 lda.l $41000E,x
 sta.l SourceModelEntityCopy4086_Hi
 lda.l SourceAI4086_Side
 tax
 lda.l $416830,x
 sta.l SourceDefaultPlayer4086_InvLo
 lda.l $416832,x
 sta.l SourceDefaultPlayer4086_InvHi
 jsl SourceInAir4086_Q16Compatibility
 ora #0
 clc
 rts
SourceAIReadonly4086_InAirBad:
.a16
.i16
 sec
 rts
