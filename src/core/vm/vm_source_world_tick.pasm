; Generic foreground entity traversal. The backend must execute EVERY emitted
; service and acknowledge it exactly once; no automatic no-op handler exists.
; Stable pool slots use the shared complete ent_list permutation at $41F200.
; Birth/death handlers own Maximum and alive state; no other code may reorder
; the list during a tick. Frozen is the result of service 3, not a guess.
; Begin/Poll/Ack/Commit return C=1 on fault. Poll A=service (1..12), 0=complete.
; Ack A=expected service. Commit is permitted only after the complete traversal
; and clears the one outstanding clock tick. All code is outside bank 0.
SourceWorldTick4086_Ready = $7FFAEC
SourceWorldTick4086_State = $7FFAEE ; 0 idle,1 entity,2 arrange,3 clear,4 complete
SourceWorldTick4086_Pending = $7FFAF0
SourceWorldTick4086_Phase = $7FFAF2
SourceWorldTick4086_Index = $7FFAF4
SourceWorldTick4086_Slot = $7FFAF6
SourceWorldTick4086_View = $7FFAF8
SourceWorldTick4086_Side = $7FFAFA
SourceWorldTick4086_Maximum = $7FFAFC
SourceWorldTick4086_Live = $7FFAFE
SourceWorldTick4086_Hole = $7FFB00
SourceWorldTick4086_Frozen = $7FFB02
SourceWorldTick4086_TimeLo = $7FFB04
SourceWorldTick4086_TimeHi = $7FFB06
SourceWorldTick4086_Fault = $7FFB08
SourceWorldTick4086_Compact = $7FFB0A
SourceWorldTick4086_Temporary = $7FFB0C
SourceWorldTick4086_Seen = $7FFB10 ; 16 bytes
SourceWorldTick4086_ScratchEnd = $7FFB20

SourceWorldTick4086_Begin:
.a16
.i16
    php
    rep #$38
    phx
    phy
    jsr SourceWorldTick4086_CheckOwner
    bcc SourceWorldTick4086_Branch_1
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_1:
.a16
.i16
    lda.l SourceWorldTick4086_State
    beq SourceWorldTick4086_Branch_2
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_2:
.a16
.i16
    jsr SourceWorldTick4086_CheckStart
    bcc SourceWorldTick4086_Begin__start_ok
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Begin__start_ok:
.a16
.i16
    lda.l VmSourceWorld_Count
    bne SourceWorldTick4086_Branch_3
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_3:
.a16
.i16
    cmp #129
    bcc SourceWorldTick4086_Branch_4
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_4:
.a16
.i16
    lda.l SourceWorldTick4086_Maximum
    cmp.l VmSourceWorld_Count
    bcs SourceWorldTick4086_Branch_5
    jmp SourceWorldTick4086_Begin__range
SourceWorldTick4086_Branch_5:
.a16
.i16
    beq SourceWorldTick4086_Branch_6
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_6:
.a16
.i16
SourceWorldTick4086_Begin__range:
.a16
.i16
    lda.l VmSourceWorld_Level
    cmp #2
    bcc SourceWorldTick4086_Branch_7
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_7:
.a16
.i16
    lda #0
    sta.l SourceWorldTick4086_Index
    sta.l SourceWorldTick4086_Pending
    sta.l SourceWorldTick4086_Phase
    sta.l SourceWorldTick4086_Fault
    ldx #0
SourceWorldTick4086_Begin__seen_clear:
.a16
.i16
    sta.l SourceWorldTick4086_Seen,x
    inx
    inx
    cpx #16
    bcs SourceWorldTick4086_Branch_8
    jmp SourceWorldTick4086_Begin__seen_clear
SourceWorldTick4086_Branch_8:
.a16
.i16
SourceWorldTick4086_Begin__validate:
.a16
.i16
    jsr SourceWorldTick4086_ReadSlot
    bcc SourceWorldTick4086_Branch_9
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_9:
.a16
.i16
    lda.l SourceWorldTick4086_Slot
    and #15
    asl a
    tax
    lda.l Vm_SourceTargetBitMask,x
    sta.l SourceWorldTick4086_Temporary
    lda.l SourceWorldTick4086_Slot
    lsr a
    lsr a
    lsr a
    lsr a
    asl a
    tax
    lda.l SourceWorldTick4086_Seen,x
    and.l SourceWorldTick4086_Temporary
    beq SourceWorldTick4086_Branch_10
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_10:
.a16
.i16
    lda.l SourceWorldTick4086_Seen,x
    ora.l SourceWorldTick4086_Temporary
    sta.l SourceWorldTick4086_Seen,x
    lda.l SourceWorldTick4086_View
    tax
    lda.l SOURCE_WORLD_POOL+4,x
    cmp #2
    bcc SourceWorldTick4086_Branch_11
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_11:
.a16
.i16
    bne SourceWorldTick4086_Branch_12
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_12:
.a16
.i16
    cmp #1
    beq SourceWorldTick4086_Branch_13
    jmp SourceWorldTick4086_Begin__next
SourceWorldTick4086_Branch_13:
.a16
.i16
    lda.l SourceWorldTick4086_Index
    cmp.l SourceWorldTick4086_Maximum
    bcc SourceWorldTick4086_Branch_14
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_14:
.a16
.i16
SourceWorldTick4086_Begin__next:
.a16
.i16
    lda.l SourceWorldTick4086_Index
    inc a
    sta.l SourceWorldTick4086_Index
    cmp.l VmSourceWorld_Count
    bcs SourceWorldTick4086_Branch_15
    jmp SourceWorldTick4086_Begin__validate
SourceWorldTick4086_Branch_15:
.a16
.i16
    lda.l VmSourceWorld_Time
    sta.l SourceWorldTick4086_TimeLo
    lda.l VmSourceWorld_Time+2
    sta.l SourceWorldTick4086_TimeHi
    lda #0
    sta.l SourceWorldTick4086_Index
    lda #1
    sta.l SourceWorldTick4086_State
    jmp SourceWorldTick4086_Ok

SourceWorldTick4086_Poll:
.a16
.i16
    php
    rep #$38
    phx
    phy
    jsr SourceWorldTick4086_CheckOwner
    bcc SourceWorldTick4086_Branch_16
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_16:
.a16
.i16
    jsr SourceWorldTick4086_CheckTime
    bcc SourceWorldTick4086_Branch_17
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_17:
.a16
.i16
    lda.l SourceWorldTick4086_Pending
    beq SourceWorldTick4086_Branch_18
    jmp SourceWorldTick4086_ReturnPhase
SourceWorldTick4086_Branch_18:
.a16
.i16
SourceWorldTick4086_Poll__state:
.a16
.i16
    lda.l SourceWorldTick4086_State
    cmp #1
    bne SourceWorldTick4086_Branch_19
    jmp SourceWorldTick4086_Poll__entity
SourceWorldTick4086_Branch_19:
.a16
.i16
    cmp #2
    bne SourceWorldTick4086_Branch_20
    jmp SourceWorldTick4086_Poll__arrange
SourceWorldTick4086_Branch_20:
.a16
.i16
    cmp #3
    bne SourceWorldTick4086_Branch_21
    jmp SourceWorldTick4086_Poll__clear
SourceWorldTick4086_Branch_21:
.a16
.i16
    cmp #4
    bne SourceWorldTick4086_Branch_22
    jmp SourceWorldTick4086_Ok
SourceWorldTick4086_Branch_22:
.a16
.i16
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Poll__entity:
.a16
.i16
    lda.l SourceWorldTick4086_Index
    cmp.l SourceWorldTick4086_Maximum
    bcc SourceWorldTick4086_Branch_23
    jmp SourceWorldTick4086_Poll__arrange_start
SourceWorldTick4086_Branch_23:
.a16
.i16
    jsr SourceWorldTick4086_ReadSlot
    bcc SourceWorldTick4086_Branch_24
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_24:
.a16
.i16
    lda.l SourceWorldTick4086_Phase
    beq SourceWorldTick4086_Branch_25
    jmp SourceWorldTick4086_Poll__after_entity_service
SourceWorldTick4086_Branch_25:
.a16
.i16
    jsr SourceWorldTick4086_Alive
    beq SourceWorldTick4086_Branch_26
    jmp SourceWorldTick4086_Poll__entity_next
SourceWorldTick4086_Branch_26:
.a16
.i16
    lda.l SourceWorldTick4086_Side
    tax
    lda.l SOURCE_WORLD_SIDES+12,x
    cmp.l SourceWorldTick4086_TimeLo
    beq SourceWorldTick4086_Branch_27
    jmp SourceWorldTick4086_Poll__reset
SourceWorldTick4086_Branch_27:
.a16
.i16
    lda.l SOURCE_WORLD_SIDES+14,x
    cmp.l SourceWorldTick4086_TimeHi
    bne SourceWorldTick4086_Branch_28
    jmp SourceWorldTick4086_Poll__entity_next
SourceWorldTick4086_Branch_28:
.a16
.i16
SourceWorldTick4086_Poll__reset:
.a16
.i16
    ; Pinned update_ents assigns global self only for an eligible old actor.
    ; arrange_ents uses explicit e and retains this last self pointer.
    lda.l SourceSelf4086_Ready
    beq SourceWorldTick4086_SelfUnbound
    cmp #$B4F6
    beq SourceWorldTick4086_SelfLease
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_SelfLease:
.a16
.i16
    jsl SourceSelf4086_CheckIdle
    bcc SourceWorldTick4086_SelfIdle
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_SelfIdle:
.a16
.i16
    lda.l SourceWorldTick4086_View
    clc
    adc #$4000
    sta.l SourceSelf4086_GlobalLow
    lda #$41
    sta.l SourceSelf4086_GlobalHigh
SourceWorldTick4086_SelfUnbound:
.a16
.i16
    lda #1
    jmp SourceWorldTick4086_Issue
SourceWorldTick4086_Poll__after_entity_service:
.a16
.i16
    cmp #1
    bne SourceWorldTick4086_Branch_29
    jmp SourceWorldTick4086_Poll__after_reset
SourceWorldTick4086_Branch_29:
.a16
.i16
    cmp #2
    bne SourceWorldTick4086_Branch_30
    jmp SourceWorldTick4086_Poll__after_lost
SourceWorldTick4086_Branch_30:
.a16
.i16
    cmp #3
    bne SourceWorldTick4086_Branch_31
    jmp SourceWorldTick4086_Poll__after_frozen
SourceWorldTick4086_Branch_31:
.a16
.i16
    cmp #4
    bne SourceWorldTick4086_Branch_32
    jmp SourceWorldTick4086_Poll__entity_next
SourceWorldTick4086_Branch_32:
.a16
.i16
    cmp #9
    bne SourceWorldTick4086_Branch_33
    jmp SourceWorldTick4086_Poll__velocity
SourceWorldTick4086_Branch_33:
.a16
.i16
    cmp #10
    bne SourceWorldTick4086_Branch_34
    jmp SourceWorldTick4086_Poll__entity_next
SourceWorldTick4086_Branch_34:
.a16
.i16
    cmp #5
    bcs SourceWorldTick4086_Branch_35
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_35:
.a16
.i16
    cmp #9
    bcc SourceWorldTick4086_Branch_36
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_36:
.a16
.i16
    jsr SourceWorldTick4086_Alive
    beq SourceWorldTick4086_Branch_37
    jmp SourceWorldTick4086_Poll__entity_next
SourceWorldTick4086_Branch_37:
.a16
.i16
    lda.l SourceWorldTick4086_Phase
    inc a
    jmp SourceWorldTick4086_Issue
SourceWorldTick4086_Poll__after_reset:
.a16
.i16
    lda.l VmSourceWorld_Level
    bne SourceWorldTick4086_Branch_38
    jmp SourceWorldTick4086_Poll__after_lost
SourceWorldTick4086_Branch_38:
.a16
.i16
    lda #2
    jmp SourceWorldTick4086_Issue
SourceWorldTick4086_Poll__after_lost:
.a16
.i16
    jsr SourceWorldTick4086_Alive
    beq SourceWorldTick4086_Branch_39
    jmp SourceWorldTick4086_Poll__entity_next
SourceWorldTick4086_Branch_39:
.a16
.i16
    lda #$FFFF
    sta.l SourceWorldTick4086_Frozen ; requires a fresh explicit query answer
    lda #3
    jmp SourceWorldTick4086_Issue
SourceWorldTick4086_Poll__after_frozen:
.a16
.i16
    lda.l SourceWorldTick4086_Frozen
    cmp #2
    bcc SourceWorldTick4086_Branch_40
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_40:
.a16
.i16
    bne SourceWorldTick4086_Branch_41
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_41:
.a16
.i16
    cmp #0
    bne SourceWorldTick4086_Branch_42
    jmp SourceWorldTick4086_Poll__not_frozen
SourceWorldTick4086_Branch_42:
.a16
.i16
    lda #4
    jmp SourceWorldTick4086_Issue
SourceWorldTick4086_Poll__not_frozen:
.a16
.i16
    lda #5
    jmp SourceWorldTick4086_Issue
SourceWorldTick4086_Poll__velocity:
.a16
.i16
    lda.l SourceVelocity4086_Ready
    cmp #$B5DE
    bne SourceWorldTick4086_VelocityUnbound
    lda #0
    sta.l SourceVelocity4086_Status
SourceWorldTick4086_VelocityUnbound:
.a16
.i16
    lda #10
    jmp SourceWorldTick4086_Issue
SourceWorldTick4086_Poll__entity_next:
.a16
.i16
    lda #0
    sta.l SourceWorldTick4086_Phase
    jsr SourceWorldTick4086_NextIndex
    jmp SourceWorldTick4086_Poll__entity
SourceWorldTick4086_Poll__arrange_start:
.a16
.i16
    jsr SourceWorldTick4086_CountLive
    lda.l SourceWorldTick4086_Live
    bne SourceWorldTick4086_Branch_43
    jmp SourceWorldTick4086_Complete
SourceWorldTick4086_Branch_43:
.a16
.i16
    cmp.l SourceWorldTick4086_Maximum
    bne SourceWorldTick4086_Branch_44
    jmp SourceWorldTick4086_Poll__uncompacted
SourceWorldTick4086_Branch_44:
.a16
.i16
    lda #1
    bra SourceWorldTick4086_Poll__arrange_init
SourceWorldTick4086_Poll__uncompacted:
.a16
.i16
    lda #0
SourceWorldTick4086_Poll__arrange_init:
.a16
.i16
    sta.l SourceWorldTick4086_Compact
    lda #$FFFF
    sta.l SourceWorldTick4086_Hole
    lda #0
    sta.l SourceWorldTick4086_Index
    lda #2
    sta.l SourceWorldTick4086_State
SourceWorldTick4086_Poll__arrange:
.a16
.i16
    lda.l SourceWorldTick4086_Index
    cmp.l SourceWorldTick4086_Maximum
    bcc SourceWorldTick4086_Branch_45
    jmp SourceWorldTick4086_Poll__clear_start
SourceWorldTick4086_Branch_45:
.a16
.i16
    jsr SourceWorldTick4086_ReadSlot
    bcc SourceWorldTick4086_Branch_46
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_46:
.a16
.i16
    lda.l SourceWorldTick4086_Compact
    bne SourceWorldTick4086_Branch_47
    jmp SourceWorldTick4086_Poll__post_check
SourceWorldTick4086_Branch_47:
.a16
.i16
    jsr SourceWorldTick4086_Alive
    bne SourceWorldTick4086_Branch_48
    jmp SourceWorldTick4086_Poll__swap
SourceWorldTick4086_Branch_48:
.a16
.i16
    lda.l SourceWorldTick4086_Hole
    bmi SourceWorldTick4086_Branch_49
    jmp SourceWorldTick4086_Poll__post_check
SourceWorldTick4086_Branch_49:
.a16
.i16
    lda.l SourceWorldTick4086_Index
    sta.l SourceWorldTick4086_Hole
    bra SourceWorldTick4086_Poll__post_check
SourceWorldTick4086_Poll__swap:
.a16
.i16
    lda.l SourceWorldTick4086_Hole
    bpl SourceWorldTick4086_Branch_50
    jmp SourceWorldTick4086_Poll__post_check
SourceWorldTick4086_Branch_50:
.a16
.i16
    asl a
    tax
    lda.l SOURCE_TARGET_ORDER,x
    sta.l SourceWorldTick4086_Temporary
    lda.l SourceWorldTick4086_Slot
    sta.l SOURCE_TARGET_ORDER,x
    lda.l SourceWorldTick4086_Index
    asl a
    tax
    lda.l SourceWorldTick4086_Temporary
    sta.l SOURCE_TARGET_ORDER,x
    lda.l SourceWorldTick4086_Hole
    inc a
    sta.l SourceWorldTick4086_Hole
    jsr SourceWorldTick4086_ReadSlot
SourceWorldTick4086_Poll__post_check:
.a16
.i16
    jsr SourceWorldTick4086_Alive
    beq SourceWorldTick4086_Branch_51
    jmp SourceWorldTick4086_Poll__post_next
SourceWorldTick4086_Branch_51:
.a16
.i16
    lda #11
    jmp SourceWorldTick4086_Issue
SourceWorldTick4086_Poll__post_next:
.a16
.i16
    jsr SourceWorldTick4086_NextIndex
    jmp SourceWorldTick4086_Poll__arrange
SourceWorldTick4086_Poll__clear_start:
.a16
.i16
    lda.l SourceWorldTick4086_Compact
    bne SourceWorldTick4086_Branch_52
    jmp SourceWorldTick4086_Poll__clear_init
SourceWorldTick4086_Branch_52:
.a16
.i16
    jsr SourceWorldTick4086_CountLive
    lda.l SourceWorldTick4086_Live
    sta.l SourceWorldTick4086_Maximum
SourceWorldTick4086_Poll__clear_init:
.a16
.i16
    lda #0
    sta.l SourceWorldTick4086_Index
    lda #3
    sta.l SourceWorldTick4086_State
SourceWorldTick4086_Poll__clear:
.a16
.i16
    lda.l SourceWorldTick4086_Index
    cmp.l SourceWorldTick4086_Maximum
    bcc SourceWorldTick4086_Branch_53
    jmp SourceWorldTick4086_Complete
SourceWorldTick4086_Branch_53:
.a16
.i16
    jsr SourceWorldTick4086_ReadSlot
    bcc SourceWorldTick4086_Branch_54
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_54:
.a16
.i16
    lda #12
    jmp SourceWorldTick4086_Issue
SourceWorldTick4086_Complete:
.a16
.i16
    lda #4
    sta.l SourceWorldTick4086_State
    jmp SourceWorldTick4086_Ok

SourceWorldTick4086_Ack:
.a16
.i16
    php
    rep #$38
    phx
    phy
    cmp.l SourceWorldTick4086_Phase
    beq SourceWorldTick4086_Branch_55
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_55:
.a16
.i16
    jsr SourceWorldTick4086_CheckOwner
    bcc SourceWorldTick4086_Branch_56
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_56:
.a16
.i16
    jsr SourceWorldTick4086_CheckTime
    bcc SourceWorldTick4086_Branch_57
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_57:
.a16
.i16
    lda.l SourceWorldTick4086_Pending
    cmp #1
    beq SourceWorldTick4086_Branch_58
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_58:
.a16
.i16
    jsl SourceUpdateFrame4086_CheckIdle
    bcc SourceWorldTick4086_Ack__frame_idle
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Ack__frame_idle:
.a16
.i16
    lda.l SourceWorldTick4086_Phase
    cmp #2
    bne SourceWorldTick4086_AckLostDone
    lda.l SourceLost4086_Ready
    beq SourceWorldTick4086_AckLostDone
    cmp #$B5E0
    beq SourceWorldTick4086_AckLostLease
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_AckLostLease:
.a16
.i16
    lda.l SourceLost4086_Status
    cmp #2
    beq SourceWorldTick4086_AckLostDone
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_AckLostDone:
.a16
.i16
    lda.l SourceWorldTick4086_Phase
    cmp #5
    bne SourceWorldTick4086_AckScriptDone
    lda.l SourceUpdateScript4086_Ready
    beq SourceWorldTick4086_AckScriptDone
    cmp #$B5E1
    beq SourceWorldTick4086_AckScriptLease
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_AckScriptLease:
.a16
.i16
    lda.l SourceUpdateScript4086_Status
    cmp #2
    beq SourceWorldTick4086_AckScriptDone
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_AckScriptDone:
.a16
.i16
    lda.l SourceWorldTick4086_Phase
    cmp #6
    bne SourceWorldTick4086_AckAIDone
    lda.l SourceAIRun4086_Ready
    beq SourceWorldTick4086_AckAIDone
    cmp #$B5E6
    beq SourceWorldTick4086_AckAILease
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_AckAILease:
.a16
.i16
    lda.l SourceAIRun4086_State
    cmp #2
    beq SourceWorldTick4086_AckAIRunDone
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_AckAIRunDone:
.a16
.i16
    lda.l SourceAI4086_State
    cmp #5
    beq SourceWorldTick4086_AckAIDone
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_AckAIDone:
.a16
.i16
    lda.l SourceWorldTick4086_Phase
    cmp #1
    beq SourceWorldTick4086_AckFreeze
    cmp #3
    beq SourceWorldTick4086_AckFreeze
    cmp #4
    bne SourceWorldTick4086_AckFreezeDone
SourceWorldTick4086_AckFreeze:
.a16
.i16
    lda.l SourceFreeze4086_Ready
    beq SourceWorldTick4086_AckFreezeDone
    cmp #$B5DF
    beq SourceWorldTick4086_AckFreezeLease
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_AckFreezeLease:
.a16
.i16
    lda.l SourceFreeze4086_Status
    cmp #2
    beq SourceWorldTick4086_AckFreezeDone
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_AckFreezeDone:
.a16
.i16
    lda.l SourceWorldTick4086_Phase
    cmp #10
    beq SourceWorldTick4086_AckMovement
    cmp #12
    bne SourceWorldTick4086_AckVelocityDone
SourceWorldTick4086_AckMovement:
.a16
.i16
    lda.l SourceVelocity4086_Ready
    beq SourceWorldTick4086_AckVelocityDone
    cmp #$B5DE
    beq SourceWorldTick4086_AckVelocityLease
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_AckVelocityLease:
.a16
.i16
    lda.l SourceVelocity4086_Status
    cmp #2
    beq SourceWorldTick4086_AckVelocityDone
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_AckVelocityDone:
.a16
.i16
    lda.l VmState_Status
    and #$00FF
    cmp #VMSTAT_RUNNING
    bne SourceWorldTick4086_Branch_59
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_59:
.a16
.i16
    cmp #VMSTAT_YIELDED
    bne SourceWorldTick4086_Branch_60
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_60:
.a16
.i16
    cmp #VMSTAT_FAULT
    bne SourceWorldTick4086_Branch_61
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_61:
.a16
.i16
    lda #0
    sta.l SourceWorldTick4086_Pending
    lda.l SourceWorldTick4086_Phase
    cmp #11
    bcs SourceWorldTick4086_Branch_62
    jmp SourceWorldTick4086_Ok
SourceWorldTick4086_Branch_62:
.a16
.i16
    jsr SourceWorldTick4086_NextIndex
    jmp SourceWorldTick4086_Ok

SourceWorldTick4086_Commit:
.a16
.i16
    php
    rep #$38
    phx
    phy
    jsr SourceWorldTick4086_CheckOwner
    bcc SourceWorldTick4086_Branch_63
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_63:
.a16
.i16
    jsr SourceWorldTick4086_CheckTime
    bcc SourceWorldTick4086_Branch_64
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_64:
.a16
.i16
    lda.l SourceWorldTick4086_State
    cmp #4
    beq SourceWorldTick4086_Branch_65
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_65:
.a16
.i16
    lda.l SourceWorldTick4086_Pending
    beq SourceWorldTick4086_Branch_66
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_66:
.a16
.i16
    lda.l SourceClock4086_TimeLo
    cmp.l SourceWorldTick4086_TimeLo
    beq SourceWorldTick4086_Branch_67
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_67:
.a16
.i16
    lda.l SourceClock4086_TimeHi
    cmp.l SourceWorldTick4086_TimeHi
    beq SourceWorldTick4086_Branch_68
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_68:
.a16
.i16
    jsl SourceClock4086_Commit
    bcc SourceWorldTick4086_Branch_69
    jmp SourceWorldTick4086_Bad
SourceWorldTick4086_Branch_69:
.a16
.i16
    lda.l SourceClock4086_TimeLo
    sta.l VmSourceWorld_Time
    lda.l SourceClock4086_TimeHi
    sta.l VmSourceWorld_Time+2
    lda #0
    sta.l SourceWorldTick4086_State
    jmp SourceWorldTick4086_Ok

SourceWorldTick4086_Issue:
.a16
.i16
    sta.l SourceWorldTick4086_Phase
    cmp #2
    bne SourceWorldTick4086_IssueLostDone
    lda.l SourceLost4086_Ready
    cmp #$B5E0
    bne SourceWorldTick4086_IssueLostDone
    lda #0
    sta.l SourceLost4086_Status
SourceWorldTick4086_IssueLostDone:
.a16
.i16
    lda.l SourceWorldTick4086_Phase
    cmp #5
    bne SourceWorldTick4086_IssueScriptDone
    lda.l SourceUpdateScript4086_Ready
    cmp #$B5E1
    bne SourceWorldTick4086_IssueScriptDone
    lda #0
    sta.l SourceUpdateScript4086_Status
SourceWorldTick4086_IssueScriptDone:
.a16
.i16
    lda.l SourceWorldTick4086_Phase
    cmp #6
    bne SourceWorldTick4086_IssueAIDone
    lda.l SourceAIRun4086_Ready
    cmp #$B5E6
    bne SourceWorldTick4086_IssueAIDone
    lda #0
    sta.l SourceAIRun4086_State
    sta.l SourceAI4086_State
SourceWorldTick4086_IssueAIDone:
.a16
.i16
    lda.l SourceWorldTick4086_Phase
    cmp #1
    beq SourceWorldTick4086_IssueFreeze
    cmp #3
    beq SourceWorldTick4086_IssueFreeze
    cmp #4
    bne SourceWorldTick4086_IssueMovement
SourceWorldTick4086_IssueFreeze:
.a16
.i16
    lda.l SourceFreeze4086_Ready
    cmp #$B5DF
    bne SourceWorldTick4086_IssueMovement
    lda #0
    sta.l SourceFreeze4086_Status
SourceWorldTick4086_IssueMovement:
.a16
.i16
    lda.l SourceWorldTick4086_Phase
    cmp #12
    bne SourceWorldTick4086_IssuePending
    lda.l SourceVelocity4086_Ready
    cmp #$B5DE
    bne SourceWorldTick4086_IssuePending
    lda #0
    sta.l SourceVelocity4086_Status
SourceWorldTick4086_IssuePending:
.a16
.i16
    lda #1
    sta.l SourceWorldTick4086_Pending
SourceWorldTick4086_ReturnPhase:
.a16
.i16
    lda.l SourceWorldTick4086_Phase
    ply
    plx
    plp
    clc
    rtl
SourceWorldTick4086_Ok:
.a16
.i16
    lda #0
    ply
    plx
    plp
    clc
    rtl
SourceWorldTick4086_Bad:
.a16
.i16
    lda #1
    sta.l SourceWorldTick4086_Fault
    ply
    plx
    plp
    sec
    rtl

SourceWorldTick4086_CheckOwner:
.a16
.i16
    lda.l SourceWorldTick4086_Ready
    cmp #$B4D5
    beq SourceWorldTick4086_Branch_70
    jmp SourceWorldTick4086_HelperBad
SourceWorldTick4086_Branch_70:
.a16
.i16
    lda.l VmSourceWorld_Ready
    cmp #$B4A3
    beq SourceWorldTick4086_Branch_71
    jmp SourceWorldTick4086_HelperBad
SourceWorldTick4086_Branch_71:
.a16
.i16
    lda.l SourceWorldTick4086_Fault
    beq SourceWorldTick4086_Branch_72
    jmp SourceWorldTick4086_HelperBad
SourceWorldTick4086_Branch_72:
.a16
.i16
    lda.l VmSourceWorld_PoolBase
    cmp #$4000
    bne SourceWorldTick4086_CheckOwner__bad
    lda.l VmSourceWorld_SideBase
    cmp #$6800
    bne SourceWorldTick4086_CheckOwner__bad
    clc
    rts
SourceWorldTick4086_CheckOwner__bad:
.a16
.i16
    sec
    rts
SourceWorldTick4086_CheckTime:
.a16
.i16
    lda.l VmSourceWorld_Time
    cmp.l SourceWorldTick4086_TimeLo
    beq SourceWorldTick4086_Branch_73
    jmp SourceWorldTick4086_HelperBad
SourceWorldTick4086_Branch_73:
.a16
.i16
    lda.l VmSourceWorld_Time+2
    cmp.l SourceWorldTick4086_TimeHi
    beq SourceWorldTick4086_Branch_74
    jmp SourceWorldTick4086_HelperBad
SourceWorldTick4086_Branch_74:
.a16
.i16
    clc
    rts
SourceWorldTick4086_HelperBad:
.a16
.i16
    sec
    rts
SourceWorldTick4086_CheckStart:
.a16
.i16
    lda.l SourceClock4086_Ready
    cmp #$B4C5
    bne SourceWorldTick4086_CheckStart__bad
    lda.l SourceClock4086_Due
    beq SourceWorldTick4086_CheckStart__bad
    lda.l SourceClock4086_TimeLo
    cmp.l VmSourceWorld_Time
    bne SourceWorldTick4086_CheckStart__bad
    lda.l SourceClock4086_TimeHi
    cmp.l VmSourceWorld_Time+2
    bne SourceWorldTick4086_CheckStart__bad
    lda.l VmState_Status
    and #$00FF
    cmp #VMSTAT_RUNNING
    beq SourceWorldTick4086_CheckStart__bad
    cmp #VMSTAT_YIELDED
    beq SourceWorldTick4086_CheckStart__bad
    cmp #VMSTAT_FAULT
    beq SourceWorldTick4086_CheckStart__bad
    clc
    rts
SourceWorldTick4086_CheckStart__bad:
.a16
.i16
    sec
    rts
SourceWorldTick4086_ReadSlot:
.a16
.i16
    lda.l SourceWorldTick4086_Index
    cmp.l VmSourceWorld_Count
    bcc SourceWorldTick4086_Branch_75
    jmp SourceWorldTick4086_HelperBad
SourceWorldTick4086_Branch_75:
.a16
.i16
    asl a
    tax
    lda.l SOURCE_TARGET_ORDER,x
    cmp.l VmSourceWorld_Count
    bcc SourceWorldTick4086_Branch_76
    jmp SourceWorldTick4086_HelperBad
SourceWorldTick4086_Branch_76:
.a16
.i16
    sta.l SourceWorldTick4086_Slot
    asl a
    asl a
    asl a
    asl a
    sta.l SourceWorldTick4086_Temporary
    asl a
    asl a
    sta.l SourceWorldTick4086_Side
    clc
    adc.l SourceWorldTick4086_Temporary
    sta.l SourceWorldTick4086_View
    clc
    rts
SourceWorldTick4086_Alive:
.a16
.i16
    lda.l SourceWorldTick4086_View
    tax
    lda.l SOURCE_WORLD_POOL+4,x
    cmp #1
    rts
SourceWorldTick4086_NextIndex:
.a16
.i16
    lda.l SourceWorldTick4086_Index
    inc a
    sta.l SourceWorldTick4086_Index
    rts
SourceWorldTick4086_CountLive:
.a16
.i16
    lda #0
    sta.l SourceWorldTick4086_Live
    ldx #0
    ldy #0
SourceWorldTick4086_CountLive__loop:
.a16
.i16
    lda.l SOURCE_WORLD_POOL+4,x
    cmp #1
    beq SourceWorldTick4086_Branch_77
    jmp SourceWorldTick4086_CountLive__next
SourceWorldTick4086_Branch_77:
.a16
.i16
    lda.l SourceWorldTick4086_Live
    inc a
    sta.l SourceWorldTick4086_Live
SourceWorldTick4086_CountLive__next:
.a16
.i16
    txa
    clc
    adc #80
    tax
    iny
    tya
    cmp.l VmSourceWorld_Count
    bcs SourceWorldTick4086_Branch_78
    jmp SourceWorldTick4086_CountLive__loop
SourceWorldTick4086_Branch_78:
.a16
.i16
    rts
