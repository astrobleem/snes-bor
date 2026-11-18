; A native-accepted role change may supersede unfinished idle/walk media.
; Same-role animation frames, attacks, jumps, unseen actors and other models
; retain their original rule. This predicate does not release/allocate/queue
; or publish anything. The ORIGINAL replacement-DMA fence still runs next.
SourceRole_CanReplace:
.a16
.i16
    php
    rep #$30
    cld
    pha
    phx
    phy
    tdc
    cmp #$0A00
    beq SourceRole_P1
    cmp #$0A85
    beq SourceRole_P2
    brl SourceRole_No
SourceRole_P1:
.a16
.i16
    ldx #0
    bra SourceRole_Record
SourceRole_P2:
.a16
.i16
    ldx #32
SourceRole_Record:
.a16
.i16
    txa
    cmp.l SourceVisual_Record
    beq SourceRole_RecordValid
    brl SourceRole_No
SourceRole_RecordValid:
.a16
.i16
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    cmp.l SourceVisual_ActorSlot
    beq SourceRole_SlotValid
    brl SourceRole_No
SourceRole_SlotValid:
.a16
.i16
    lda.l SourceVisual_State+6,x
    cmp #1
    beq SourceRole_Mode
    cmp #2
    beq SourceRole_Mode
    brl SourceRole_No
SourceRole_Mode:
.a16
.i16
    lda.l SourceVisual_State+28,x
    and #255
    cmp #0
    beq SourceRole_Guard1
    brl SourceRole_No
SourceRole_Guard1:
.a16
.i16
    lda.l SourceVisual_State+29,x
    and #255
    cmp #22
    beq SourceRole_Guard2
    brl SourceRole_No
SourceRole_Guard2:
.a16
.i16
    lda.l SourceVisual_State,x
    cmp.l SourceVisual_EntryIndexSaved
    bne SourceRole_NewEntry
    brl SourceRole_No
SourceRole_NewEntry:
.a16
.i16
    lda.l SourceVisual_State+30,x
    and #$00FF
    cmp #2
    bcc SourceRole_Guard3
    brl SourceRole_No
SourceRole_Guard3:
.a16
.i16
    tay
    lda.l SourceVisual_Key
    and #255
    cmp #22
    beq SourceRole_Guard4
    brl SourceRole_No
SourceRole_Guard4:
.a16
.i16
    lda.l SourceVisual_Key+3
    and #255
    cmp #0
    beq SourceRole_Guard5
    brl SourceRole_No
SourceRole_Guard5:
.a16
.i16
    lda.l SourceVisual_EntryScratch
    cmp.l SourceVisual_Key
    beq SourceRole_EntryLow
    brl SourceRole_No
SourceRole_EntryLow:
.a16
.i16
    lda.l SourceVisual_EntryScratch+2
    cmp.l SourceVisual_Key+2
    beq SourceRole_EntryHigh
    brl SourceRole_No
SourceRole_EntryHigh:
.a16
.i16
    lda.l SourceVisual_Key+1
    and #$00FF
    cmp #0
    bne SourceRole_NotIdle
    brl SourceRole_GoIdle
SourceRole_NotIdle:
.a16
.i16
    cmp #1
    bne SourceRole_NotWalk
    brl SourceRole_GoWalk
SourceRole_NotWalk:
.a16
.i16
    cmp #2
    bne SourceRole_BadGoal
    brl SourceRole_GoAttack
SourceRole_BadGoal:
.a16
.i16
    brl SourceRole_No
SourceRole_GoIdle:
.a16
.i16
    tya
    cmp #1
    beq SourceRole_IdleOld
    brl SourceRole_No
SourceRole_IdleOld:
.a16
.i16
    lda.l SourceVisual_Key+2
    cmp #1
    bcc SourceRole_Guard6
    brl SourceRole_No
SourceRole_Guard6:
.a16
.i16
    tdc
    sec
    sbc #$0A00
    tax
    lda.l SourceVisual_Sa1RuntimeRole,x
    and #255
    cmp #0
    beq SourceRole_Guard7
    brl SourceRole_No
SourceRole_Guard7:
.a16
.i16
    brl SourceRole_Live
SourceRole_GoWalk:
.a16
.i16
    tya
    cmp #0
    beq SourceRole_WalkOld
    brl SourceRole_No
SourceRole_WalkOld:
.a16
.i16
    lda.l SourceVisual_Key+2
    cmp #10
    bcc SourceRole_Guard8
    brl SourceRole_No
SourceRole_Guard8:
.a16
.i16
    tdc
    sec
    sbc #$0A00
    tax
    lda.l SourceVisual_Sa1RuntimeRole,x
    and #255
    cmp #1
    beq SourceRole_Guard9
    brl SourceRole_No
SourceRole_Guard9:
.a16
.i16
    brl SourceRole_Live
SourceRole_GoAttack:
.a16
.i16
    lda.l SourceVisual_Key+2
    cmp #6
    bcc SourceRole_Guard10
    brl SourceRole_No
SourceRole_Guard10:
.a16
.i16
    tdc
    sec
    sbc #$0A00
    tax
    lda.l SourceVisual_Sa1RuntimeRole,x
    and #255
    cmp #2
    beq SourceRole_Guard11
    brl SourceRole_No
SourceRole_Guard11:
.a16
.i16
    brl SourceRole_Live
SourceRole_Live:
.a16
.i16
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    and #255
    cmp #1
    beq SourceRole_Guard12
    brl SourceRole_No
SourceRole_Guard12:
.a16
.i16
    lda.l $7E0A00+CHAR_ROSTER_INDEX,x
    and #255
    cmp #22
    beq SourceRole_Guard13
    brl SourceRole_No
SourceRole_Guard13:
.a16
.i16
    lda.l $7E0A00+CHAR_MAP_INDEX,x
    and #255
    cmp #0
    beq SourceRole_Guard14
    brl SourceRole_No
SourceRole_Guard14:
.a16
.i16
    lda.l $7E0A00+CHAR_HP,x
    and #$00FF
    bne SourceRole_Hp
    brl SourceRole_No
SourceRole_Hp:
.a16
.i16
    lda.l $7E0A00+CHAR_SELECTED,x
    and #$00FF
    cmp #3
    bcc SourceRole_Guard15
    brl SourceRole_No
SourceRole_Guard15:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy,x
    and #255
    cmp #2
    beq SourceRole_Guard16
    brl SourceRole_No
SourceRole_Guard16:
.a16
.i16
    lda.l $7E46DE
    cmp #0
    beq SourceRole_Guard17
    brl SourceRole_No
SourceRole_Guard17:
.a16
.i16
    lda.l Game_StageIndex
    cmp #0
    beq SourceRole_Guard18
    brl SourceRole_No
SourceRole_Guard18:
.a16
.i16
    jsr SourceNpc_Scope
    bcs SourceRole_Guard19
    brl SourceRole_No
SourceRole_Guard19:
.a16
.i16
    tdc
    cmp #$0A00
    beq SourceRole_P1Picture
    brl SourceRole_P2Picture
SourceRole_P1Picture:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    cmp #1
    beq SourceRole_Guard20
    brl SourceRole_No
SourceRole_Guard20:
.a16
.i16
    lda.l SourceVisual_CompletedStage
    cmp #0
    beq SourceRole_Guard21
    brl SourceRole_No
SourceRole_Guard21:
.a16
.i16
    lda.l SourceVisual_CompletedRoster
    cmp #22
    beq SourceRole_Guard22
    brl SourceRole_No
SourceRole_Guard22:
.a16
.i16
    lda.l SourceVisual_CompletedEntry
    and #255
    cmp #22
    beq SourceRole_Guard23
    brl SourceRole_No
SourceRole_Guard23:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+3
    and #255
    cmp #0
    beq SourceRole_Guard24
    brl SourceRole_No
SourceRole_Guard24:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+1
    and #$00FF
    cmp #2
    bcc SourceRole_Guard25
    brl SourceRole_No
SourceRole_Guard25:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+12
    cmp #1
    bcs SourceRole_Guard26
    brl SourceRole_No
SourceRole_Guard26:
.a16
.i16
    cmp #66
    bcc SourceRole_Guard27
    brl SourceRole_No
SourceRole_Guard27:
.a16
.i16
    brl SourceRole_Yes
SourceRole_P2Picture:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourceRole_Guard28
    brl SourceRole_No
SourceRole_Guard28:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage
    cmp #0
    beq SourceRole_Guard29
    brl SourceRole_No
SourceRole_Guard29:
.a16
.i16
    lda.l SVActor_Data+SVActor_Roster
    cmp #22
    beq SourceRole_Guard30
    brl SourceRole_No
SourceRole_Guard30:
.a16
.i16
    lda.l SVActor_Data
    and #255
    cmp #22
    beq SourceRole_Guard31
    brl SourceRole_No
SourceRole_Guard31:
.a16
.i16
    lda.l SVActor_Data+3
    and #255
    cmp #0
    beq SourceRole_Guard32
    brl SourceRole_No
SourceRole_Guard32:
.a16
.i16
    lda.l SVActor_Data+1
    and #$00FF
    cmp #2
    bcc SourceRole_Guard33
    brl SourceRole_No
SourceRole_Guard33:
.a16
.i16
    lda.l SVActor_Data+12
    cmp #1
    bcs SourceRole_Guard34
    brl SourceRole_No
SourceRole_Guard34:
.a16
.i16
    cmp #66
    bcc SourceRole_Guard35
    brl SourceRole_No
SourceRole_Guard35:
.a16
.i16
    brl SourceRole_Yes
SourceRole_Yes:
.a16
.i16
    ply
    plx
    pla
    plp
    sec
    rtl
SourceRole_No:
.a16
.i16
    ply
    plx
    pla
    plp
    clc
    rtl
SourceRole_End:
.a16
.i16
