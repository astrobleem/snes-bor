; The sole caller is SourceRewarm_Arm at the foreground post-WaitFrame edge.
; WaitFrame snapshots Nmi_FrameCounter then waits for a change before that
; call, so there is at most one service call per completed wait interval.
; No new persistent timestamp, world/input mutation or display-ACK writer.
SourceHot_Begin:
.a16
.i16
    lda #2
    sta.l $437BAC
    jsl SourceHot_Service
    jml SourceRewarm_Done
SourceHot_TickAndLoad:
.a16
.i16
    php
    jsl SourceHot_Service
    plp
    lda.l SourceAttackTemplate_Base
    rtl
SourceHot_Service:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    phd
    cld
    lda.l SourceInput_Selected1
    ora.l SourceInput_Selected2
    ora.l SourceVisual_LatchedInput
    ora.l SourceVisual_LatchedInput2
    ora.l Input_trigger
    ora.l Input2_trigger_Addr
    and #$80
    beq SourceHot_NoJump
    brl SourceHot_Cancel
SourceHot_NoJump:
.a16
.i16
    lda.l $7E0A00+CHAR_SELECTED
    and #255
    cmp #3
    bcc SourceHot_Player0Grounded
    brl SourceHot_Cancel
SourceHot_Player0Grounded:
.a16
.i16
    lda.l $7E0A00+133+CHAR_SELECTED
    and #255
    cmp #3
    bcc SourceHot_Player1Grounded
    brl SourceHot_Cancel
SourceHot_Player1Grounded:
.a16
.i16
    lda.l $7E0A00+CHAR_THROW_ZPOS
    ora.l $7E0A00+133+CHAR_THROW_ZPOS
    beq SourceHot_Grounded
    brl SourceHot_Cancel
SourceHot_Grounded:
.a16
.i16
    jsl SourceHotJump_NoPendingInput
    bcs SourceHot_JournalClear
    brl SourceHot_Cancel
SourceHot_JournalClear:
.a16
.i16
    lda.l SourceAttackTemplate_Base
    cmp #$A770
    bne SourceHot_NeedsTemplate
    lda.l SourceAttackTemplate_Base+128
    cmp #$A770
    bne SourceHot_NeedsTemplate
    brl SourceHot_Done
SourceHot_NeedsTemplate:
.a16
.i16
    jsl SourceWarm_SettleCompleted
    jsl SourceHot_SourceStandby_Prepare
    lda.l SourceAttackTemplate_Base
    cmp #$A770
    bne SourceHot_CheckDirection
    lda.l SourceAttackTemplate_Base+128
    cmp #$A770
    bne SourceHot_CheckDirection
    brl SourceHot_Done
SourceHot_CheckDirection:
.a16
.i16
    jsl SourceRecover_NoPendingInput
    bcs SourceHot_QuietActions
    brl SourceHot_Done
SourceHot_QuietActions:
.a16
.i16
    lda.l SourceInput_Producer
    cmp.l $437B90
    beq SourceHot_StableInput
    brl SourceHot_Done
SourceHot_StableInput:
.a16
.i16
    dec a
    and #63
    asl a
    asl a
    tax
    lda.l SourceInput_Ring,x
    ora.l SourceInput_Ring+2,x
    and #$0F00
    bne SourceHot_HaveDirection
    brl SourceHot_Done
SourceHot_HaveDirection:
.a16
.i16
    lda.l SourcePrefetch_PhysicalPending
    beq SourceHot_NoPhysicalJob
    brl SourceHot_Done
SourceHot_NoPhysicalJob:
.a16
.i16
    jsl SourceRecover_ChooseCursor
    lda.l $437BFE
    pha
    lda #$B6A5
    sta.l $437BFE
    lda.l SourcePrefetch_Cursor
    jsl SourceHot_SourcePrefetch_TryOne
    bcc SourceHot_NotSubmitted
    lda.l SourcePrefetch_Submitted
    inc a
    sta.l SourcePrefetch_Submitted
SourceHot_NotSubmitted:
.a16
.i16
    pla
    sta.l $437BFE
    lda.l SourcePrefetch_Plan+20
    beq SourceHot_Done
    lda.l SourcePrefetch_Cursor
    inc a
    cmp #10
    bcc SourceHot_SaveCursor
    lda #10
SourceHot_SaveCursor:
.a16
.i16
    sta.l SourcePrefetch_Cursor
    jsl SourceHot_SourceStandby_Prepare
    bra SourceHot_Done
SourceHot_Cancel:
.a16
.i16
    lda #1
    sta.l $437BAC
SourceHot_Done:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    rtl
