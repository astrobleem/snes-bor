; Recovery-only eligibility. All readiness/identity/pin checks following the
; original threshold remain authoritative. Startup and ordinary cursor rules
; are unchanged. No resource, queue, input or ACK writes in these helpers.
.bank 5
.org $C000
SourceRecover_Threshold:
.a16
.i16
    lda.l SourcePrefetch_Cursor
    cmp #10
    bcs SourceRecover_ThresholdDone
    cmp #0
    beq SourceRecover_ThresholdOriginal
    pha
    lda.l $437BAC
    cmp #2
    bne SourceRecover_ThresholdRestore
    pla
    lda #10
    cmp #10
SourceRecover_ThresholdDone:
.a16
.i16
    rtl
SourceRecover_ThresholdRestore:
.a16
.i16
    pla
SourceRecover_ThresholdOriginal:
.a16
.i16
    cmp #10
    rtl

; The batched root plan already permits directions in unconsumed ring rows.
; Match its latest-row policy only during pressure recovery. Retry/burst
; eligibility still uses the original neutral-only NoPendingInput routine.
SourceRecover_PlanLatest:
.a16
.i16
    php
    lda.l $437BAC
    cmp #2
    bne SourceRecover_LatestOriginal
    plp
    lda.l SourceInput_Ring,x
    ora.l SourceInput_Ring+2,x
    and #$F0FF
    rtl
SourceRecover_LatestOriginal:
.a16
.i16
    plp
    lda.l SourceInput_Ring,x
    ora.l SourceInput_Ring+2,x
    rtl

SourceRecover_WarmRoles:
.a16
.i16
    php
    lda.l $437BAC
    cmp #2
    bne SourceRecover_WarmRolesOriginal
    plp
    lda.l $434E50
    ora.l $434E74
    and #$FFFE
    rtl
SourceRecover_WarmRolesOriginal:
.a16
.i16
    plp
    lda.l $434E50
    ora.l $434E74
    rtl

; Template maps are hints only. A stale map selects a candidate index but
; never makes a block ready: the original plan scans/authenticates the ID,
; state, pins, queue and physical cookie. Worst case ten constant-size probes.
SourceRecover_ChooseCursor:
.a16
.i16
    phx
    ldx #9
SourceRecover_CursorLoop:
.a16
.i16
    phx
    txa
    asl a
    tax
    lda.l SourcePrefetch_HotIds,x
    pha
    txa
    lsr a
    tax
    lda.l $436CF8,x
    and #255
    cmp #64
    bcs SourceRecover_CursorMissing
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_BlockCache,x
    cmp 1,s
    bne SourceRecover_CursorMissing
    lda.l SourceVisual_BlockCache+2,x
    cmp #2
    bne SourceRecover_CursorMissing
    pla
    plx
    dex
    bpl SourceRecover_CursorLoop
    lda #0
    bra SourceRecover_CursorStore
SourceRecover_CursorMissing:
.a16
.i16
    pla
    pla
SourceRecover_CursorStore:
.a16
.i16
    sta.l SourcePrefetch_Cursor
    plx
    rtl


SourceRecover_WarmRole0:
.a16
.i16
    php
    lda.l $437BAC
    cmp #2
    bne SourceRecover_WarmRole0Original
    plp
    lda.l $434E50
    and #$FFFE
    rtl
SourceRecover_WarmRole0Original:
.a16
.i16
    plp
    lda.l $434E50
    rtl
SourceRecover_StandbyRole0:
.a16
.i16
    php
    lda.l $437BAC
    cmp #2
    bne SourceRecover_Role0Original
    lda.l $434E50
    and #255
    cmp #1
    beq SourceRecover_Role0Walk
    cmp #2
    bne SourceRecover_Role0Original
    lda.l $434E54
    and #255
    cmp #9
    beq SourceRecover_Role0Normalize
    bra SourceRecover_Role0Original
SourceRecover_Role0Walk:
.a16
.i16
    lda.l $434E54
    and #255
    cmp #8
    bne SourceRecover_Role0Original
SourceRecover_Role0Normalize:
.a16
.i16
    plp
    lda.l $434E50
    and #$FF00
    rtl
SourceRecover_Role0Original:
.a16
.i16
    plp
    lda.l $434E50
    rtl
SourceRecover_StandbyProfile0:
.a16
.i16
    php
    lda.l $437BAC
    cmp #2
    bne SourceRecover_Profile0Original
    lda.l $434E50
    and #255
    cmp #2
    bne SourceRecover_Profile0Original
    plp
    lda.l $434E54
    and #$FFFE
    rtl
SourceRecover_Profile0Original:
.a16
.i16
    plp
    lda.l $434E54
    rtl

SourceRecover_WarmRole1:
.a16
.i16
    php
    lda.l $437BAC
    cmp #2
    bne SourceRecover_WarmRole1Original
    plp
    lda.l $434E74
    and #$FFFE
    rtl
SourceRecover_WarmRole1Original:
.a16
.i16
    plp
    lda.l $434E74
    rtl
SourceRecover_StandbyRole1:
.a16
.i16
    php
    lda.l $437BAC
    cmp #2
    bne SourceRecover_Role1Original
    lda.l $434E74
    and #255
    cmp #1
    beq SourceRecover_Role1Walk
    cmp #2
    bne SourceRecover_Role1Original
    lda.l $434E78
    and #255
    cmp #9
    beq SourceRecover_Role1Normalize
    bra SourceRecover_Role1Original
SourceRecover_Role1Walk:
.a16
.i16
    lda.l $434E78
    and #255
    cmp #8
    bne SourceRecover_Role1Original
SourceRecover_Role1Normalize:
.a16
.i16
    plp
    lda.l $434E74
    and #$FF00
    rtl
SourceRecover_Role1Original:
.a16
.i16
    plp
    lda.l $434E74
    rtl
SourceRecover_StandbyProfile1:
.a16
.i16
    php
    lda.l $437BAC
    cmp #2
    bne SourceRecover_Profile1Original
    lda.l $434E74
    and #255
    cmp #2
    bne SourceRecover_Profile1Original
    plp
    lda.l $434E78
    and #$FFFE
    rtl
SourceRecover_Profile1Original:
.a16
.i16
    plp
    lda.l $434E78
    rtl
SourceRecover_NoPendingInput:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    lda #1
    pha
SourceRecover_InputRetry:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SourceRecover_InputGuard0
    brl SourceRecover_NoInputNo
SourceRecover_InputGuard0:
.a16
.i16
    lda.l SourceInput_Overflows
    beq SourceRecover_InputGuard1
    brl SourceRecover_NoInputNo
SourceRecover_InputGuard1:
.a16
.i16
    lda.l SourceVisual_LatchedInput
    ora.l SourceVisual_LatchedInput2
    and #$F0FF
    beq SourceRecover_InputGuard2
    brl SourceRecover_NoInputNo
SourceRecover_InputGuard2:
.a16
.i16
    lda.l $434E50
    ora.l $434E74
    and #254
    beq SourceRecover_InputGuard3
    brl SourceRecover_NoInputNo
SourceRecover_InputGuard3:
.a16
.i16
    lda.l SourceInput_Producer
    cmp #64
    bcc SourceRecover_InputGuard4
    brl SourceRecover_NoInputNo
SourceRecover_InputGuard4:
.a16
.i16
    sta.l $437B90
    lda.l SourceInput_Consumer
    cmp #64
    bcc SourceRecover_InputGuard5
    brl SourceRecover_NoInputNo
SourceRecover_InputGuard5:
.a16
.i16
    tay
    lda.l $437B90
    dec a
    and #63
    asl a
    asl a
    tax
    lda.l SourceInput_Ring,x
    ora.l SourceInput_Ring+2,x
    and #$F0FF
    beq SourceRecover_InputGuard6
    brl SourceRecover_NoInputNo
SourceRecover_InputGuard6:
.a16
.i16
SourceRecover_NoInputLoop:
.a16
.i16
    tya
    cmp.l $437B90
    beq SourceRecover_NoInputEnd
    asl a
    asl a
    tax
    lda.l SourceInput_Ring,x
    ora.l SourceInput_Ring+2,x
    and #$F0FF
    beq SourceRecover_InputGuard7
    brl SourceRecover_NoInputNo
SourceRecover_InputGuard7:
.a16
.i16
    tya
    inc a
    and #63
    tay
    brl SourceRecover_NoInputLoop
SourceRecover_NoInputEnd:
.a16
.i16
    lda.l SourceInput_Producer
    cmp.l $437B90
    beq SourceRecover_NoInputYes
    lda 1,s
    beq SourceRecover_NoInputNo
    dec a
    sta 1,s
    brl SourceRecover_InputRetry
SourceRecover_NoInputYes:
.a16
.i16
    pla
    ply
    plx
    pla
    plp
    sec
    rtl
SourceRecover_NoInputNo:
.a16
.i16
    pla
    ply
    plx
    pla
    plp
    clc
    rtl

SourceRecover_End:
.assert SourceRecover_End <= $05C400, "bounded pressure recovery exceeds gap"

SourceHotJump_NoPendingInput:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    lda #1
    pha
SourceHotJump_InputRetry:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SourceHotJump_InputGuard0
    brl SourceHotJump_NoInputNo
SourceHotJump_InputGuard0:
.a16
.i16
    lda.l SourceInput_Overflows
    beq SourceHotJump_InputGuard1
    brl SourceHotJump_NoInputNo
SourceHotJump_InputGuard1:
.a16
.i16
    lda.l SourceVisual_LatchedInput
    ora.l SourceVisual_LatchedInput2
    and #$0080
    beq SourceHotJump_InputGuard2
    brl SourceHotJump_NoInputNo
SourceHotJump_InputGuard2:
.a16
.i16
SourceHotJump_InputGuard3:
.a16
.i16
    lda.l SourceInput_Producer
    cmp #64
    bcc SourceHotJump_InputGuard4
    brl SourceHotJump_NoInputNo
SourceHotJump_InputGuard4:
.a16
.i16
    sta.l $437B90
    lda.l SourceInput_Consumer
    cmp #64
    bcc SourceHotJump_InputGuard5
    brl SourceHotJump_NoInputNo
SourceHotJump_InputGuard5:
.a16
.i16
    tay
    lda.l $437B90
    dec a
    and #63
    asl a
    asl a
    tax
    lda.l SourceInput_Ring,x
    ora.l SourceInput_Ring+2,x
    and #$0080
    beq SourceHotJump_InputGuard6
    brl SourceHotJump_NoInputNo
SourceHotJump_InputGuard6:
.a16
.i16
SourceHotJump_NoInputLoop:
.a16
.i16
    tya
    cmp.l $437B90
    beq SourceHotJump_NoInputEnd
    asl a
    asl a
    tax
    lda.l SourceInput_Ring,x
    ora.l SourceInput_Ring+2,x
    and #$0080
    beq SourceHotJump_InputGuard7
    brl SourceHotJump_NoInputNo
SourceHotJump_InputGuard7:
.a16
.i16
    tya
    inc a
    and #63
    tay
    brl SourceHotJump_NoInputLoop
SourceHotJump_NoInputEnd:
.a16
.i16
    lda.l SourceInput_Producer
    cmp.l $437B90
    beq SourceHotJump_NoInputYes
    lda 1,s
    beq SourceHotJump_NoInputNo
    dec a
    sta 1,s
    brl SourceHotJump_InputRetry
SourceHotJump_NoInputYes:
.a16
.i16
    pla
    ply
    plx
    pla
    plp
    sec
    rtl
SourceHotJump_NoInputNo:
.a16
.i16
    pla
    ply
    plx
    pla
    plp
    clc
    rtl

SourceHotJump_End:
.assert SourceHotJump_End <= $05C400, "pending-jump helper exceeds gap"
.bank 5
.org $C400
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

SourceHot_SourceStandby_Prepare:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    cld
    lda #0
    sta.l SourceStandby_Result
    sta.l SourceStandby_Target
    lda.l SourceAttackOwned_InitMagic
    cmp #$B077
    beq SourceHot_SourceStandby_G1
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G1:
.a16
.i16
    lda.l SourceVisual_CompletedMagic
    cmp #$C04D
    beq SourceHot_SourceStandby_G2
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G2:
.a16
.i16
    lda.l SVActor_Magic
    cmp #$AC19
    beq SourceHot_SourceStandby_G3
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G3:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SourceHot_SourceStandby_G4
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G4:
.a16
.i16
    lda.l Game_State
    cmp #$0000
    beq SourceHot_SourceStandby_G5
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G5:
.a16
.i16
    lda.l Game_StageIndex
    cmp #$0000
    beq SourceHot_SourceStandby_G6
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G6:
.a16
.i16
    lda.l Screen_PosX
    cmp #$0000
    beq SourceHot_SourceStandby_G7
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G7:
.a16
.i16
    lda.l SourceAttackOwned_State
    cmp #$0000
    beq SourceHot_SourceStandby_G8
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G8:
.a16
.i16
    lda.l SourceAttackOwned_Hold
    cmp #$0000
    beq SourceHot_SourceStandby_G9
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G9:
.a16
.i16
    lda.l SourceAttackOwned_Busy
    cmp #$0000
    beq SourceHot_SourceStandby_G10
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G10:
.a16
.i16
    lda.l SourcePacket_CopyBusy
    cmp #$0000
    beq SourceHot_SourceStandby_G11
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G11:
.a16
.i16
    jsl SourceRewarm_Closed
    cmp #$0000
    beq SourceHot_SourceStandby_G12
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G12:
.a16
.i16
    lda.l $437A96
    cmp #$0000
    beq SourceHot_SourceStandby_G13
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G13:
.a16
.i16
    lda.l $437A98
    cmp #$0000
    beq SourceHot_SourceStandby_G14
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G14:
.a16
.i16
    jsl SourceRewarm_PhysicalMask
    cmp #$0000
    beq SourceHot_SourceStandby_G15
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G15:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    cmp #$0001
    beq SourceHot_SourceStandby_G16
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G16:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #$0001
    beq SourceHot_SourceStandby_G17
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G17:
.a16
.i16
    lda.l Game_CampaignId
    and #255
    cmp #3
    beq SourceHot_SourceStandby_G18
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G18:
.a16
.i16
    lda.l $7E175E
    cmp #$0002
    beq SourceHot_SourceStandby_G19
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G19:
.a16
.i16
    lda.l $7E1760
    cmp #$0001
    beq SourceHot_SourceStandby_G20
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G20:
.a16
.i16
    lda.l $7E46DC
    cmp #$0001
    beq SourceHot_SourceStandby_G21
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G21:
.a16
.i16
    lda.l $7E46DE
    cmp #$0000
    beq SourceHot_SourceStandby_G22
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G22:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    beq SourceHot_SourceStandby_G23
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G23:
.a16
.i16
    lda.l $434E2C
    cmp #$0000
    beq SourceHot_SourceStandby_G24
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G24:
.a16
.i16
    lda.l $434E7C
    sta.l SourceStandby_Seq
    and #1
    beq SourceHot_SourceStandby_G25
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G25:
.a16
.i16
    jsl SourceRecover_Threshold
    nop
    nop
    nop
    bcs SourceHot_SourceStandby_G26
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G26:
.a16
.i16
    lda.l SourcePrefetch_PhysicalPending
    cmp #0
    beq SourceHot_SourceStandby_G27
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G27:
.a16
.i16
    lda.l $7E0A00+CHAR_INPUT_DRIVEN
    and #255
    cmp #1
    beq SourceHot_SourceStandby_G28
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G28:
.a16
.i16
    lda.l $7E0A00+CHAR_ROSTER_INDEX
    and #255
    cmp #22
    beq SourceHot_SourceStandby_G29
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G29:
.a16
.i16
    lda.l $7E0A00+CHAR_MAP_INDEX
    and #255
    cmp #0
    beq SourceHot_SourceStandby_G30
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G30:
.a16
.i16
    lda.l $7E0A00+CHAR_HP
    and #255
    bne SourceHot_SourceStandby_G31
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G31:
.a16
.i16
    lda.l StageBounds_State+0
    cmp #0
    beq SourceHot_SourceStandby_G32
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G32:
.a16
.i16
    lda.l $434E40
    cmp #1
    beq SourceHot_SourceStandby_G33
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G33:
.a16
.i16
    lda.l $434E42
    cmp #0
    beq SourceHot_SourceStandby_G34
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G34:
.a16
.i16
    lda.l $434E4A
    and #255
    cmp #2
    beq SourceHot_SourceStandby_G35
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G35:
.a16
.i16
    jsl SourceRecover_StandbyRole0
    and #255
    cmp #0
    beq SourceHot_SourceStandby_G36
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G36:
.a16
.i16
    jsl SourceRecover_StandbyProfile0
    and #255
    cmp #8
    beq SourceHot_SourceStandby_G37
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G37:
.a16
.i16
    lda.l $434E36
    cmp #188
    beq SourceHot_SourceStandby_G38
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G38:
.a16
.i16
    lda.l $434E44
    bne SourceHot_SourceStandby_G39
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G39:
.a16
.i16
    lda.l $434E44
    cmp #256
    bcc SourceHot_SourceStandby_G40
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G40:
.a16
.i16
    lda.l $434E9C
    cmp #0
    beq SourceHot_SourceStandby_G41
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G41:
.a16
.i16
SourceHot_SourceStandby_TemplateCheck0:
.a16
.i16
    lda.l SourceAttackTemplate_Base+0
    cmp #$A770
    beq SourceHot_SourceStandby_Have0
    lda.l SourceStandby_Target
    ora #1
    sta.l SourceStandby_Target
SourceHot_SourceStandby_Have0:
.a16
.i16
    lda.l $7E0A85+CHAR_INPUT_DRIVEN
    and #255
    cmp #1
    beq SourceHot_SourceStandby_G42
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G42:
.a16
.i16
    lda.l $7E0A85+CHAR_ROSTER_INDEX
    and #255
    cmp #22
    beq SourceHot_SourceStandby_G43
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G43:
.a16
.i16
    lda.l $7E0A85+CHAR_MAP_INDEX
    and #255
    cmp #0
    beq SourceHot_SourceStandby_G44
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G44:
.a16
.i16
    lda.l $7E0A85+CHAR_HP
    and #255
    bne SourceHot_SourceStandby_G45
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G45:
.a16
.i16
    lda.l StageBounds_State+133
    cmp #0
    beq SourceHot_SourceStandby_G46
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G46:
.a16
.i16
    lda.l $434E64
    cmp #1
    beq SourceHot_SourceStandby_G47
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G47:
.a16
.i16
    lda.l $434E66
    cmp #0
    beq SourceHot_SourceStandby_G48
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G48:
.a16
.i16
    lda.l $434E6E
    and #255
    cmp #2
    beq SourceHot_SourceStandby_G49
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G49:
.a16
.i16
    jsl SourceRecover_StandbyRole1
    and #255
    cmp #0
    beq SourceHot_SourceStandby_G50
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G50:
.a16
.i16
    jsl SourceRecover_StandbyProfile1
    and #255
    cmp #8
    beq SourceHot_SourceStandby_G51
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G51:
.a16
.i16
    lda.l $434E5A
    cmp #188
    beq SourceHot_SourceStandby_G52
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G52:
.a16
.i16
    lda.l $434E68
    bne SourceHot_SourceStandby_G53
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G53:
.a16
.i16
    lda.l $434E68
    cmp #256
    bcc SourceHot_SourceStandby_G54
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G54:
.a16
.i16
    lda.l $434E9E
    cmp #133
    beq SourceHot_SourceStandby_G55
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G55:
.a16
.i16
SourceHot_SourceStandby_TemplateCheck1:
.a16
.i16
    lda.l SourceAttackTemplate_Base+128
    cmp #$A770
    beq SourceHot_SourceStandby_Have1
    lda.l SourceStandby_Target
    ora #2
    sta.l SourceStandby_Target
SourceHot_SourceStandby_Have1:
.a16
.i16
    lda.l SourceStandby_Target
    bne SourceHot_SourceStandby_G56
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G56:
.a16
.i16
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l SourceStandby_Pin
    ; Never compete with a still-unpublished first NPC picture.
    lda.l SVActor_LoadOwner
    cmp #3
    bcc SourceHot_SourceStandby_NoFirstNpc
    cmp #7
    bcs SourceHot_SourceStandby_NoFirstNpc
    dec a
    dec a
    asl a
    tax
    lda.l SVActor_Bases,x
    tax
    lda.l SVActor_Data+SVActor_Valid,x
    cmp #1
    beq SourceHot_SourceStandby_G57
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G57:
.a16
.i16
SourceHot_SourceStandby_NoFirstNpc:
.a16
.i16
    ldx #0
SourceHot_SourceStandby_EmptyBlocks:
.a16
.i16
    lda.l SVActor_HeldBlocks,x
    and.l SourceStandby_Pin
    beq SourceHot_SourceStandby_G58
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G58:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #512
    bcc SourceHot_SourceStandby_EmptyBlocks
    ldx #0
SourceHot_SourceStandby_EmptyPalettes:
.a16
.i16
    lda.l SVActor_HeldPalettes,x
    and.l SourceStandby_Pin
    beq SourceHot_SourceStandby_G59
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G59:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourceHot_SourceStandby_EmptyPalettes
    ldx #0
SourceHot_SourceStandby_Queue:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$40
    beq SourceHot_SourceStandby_QueueNext
    lda.l DmaQueue+4,x
    and #255
    cmp #$41
    beq SourceHot_SourceStandby_G60
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G60:
.a16
.i16
    lda.l DmaQueue+7,x
    and #255
    cmp #$43
    beq SourceHot_SourceStandby_PrivateOam
    cmp #$7E
    beq SourceHot_SourceStandby_LegacyOam
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_PrivateOam:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$4F00
    beq SourceHot_SourceStandby_G61
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G61:
.a16
.i16
    lda.l DmaQueue,x
    cmp #544
    beq SourceHot_SourceStandby_G62
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G62:
.a16
.i16
    lda.l DmaQueue+2,x
    cmp #0
    beq SourceHot_SourceStandby_G63
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G63:
.a16
.i16
    brl SourceHot_SourceStandby_QueueNext
SourceHot_SourceStandby_LegacyOam:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$5100
    beq SourceHot_SourceStandby_QueueNext
    cmp #$5300
    beq SourceHot_SourceStandby_QueueNext
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_QueueNext:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourceHot_SourceStandby_Queue
    ldx #0
SourceHot_SourceStandby_FindPalette:
.a16
.i16
    lda.l SourceVisual_PaletteCache,x
    cmp #361
    bne SourceHot_SourceStandby_NextPalette
    lda.l SourceVisual_PaletteCache+3,x
    and #255
    cmp #1
    beq SourceHot_SourceStandby_PaletteFound
SourceHot_SourceStandby_NextPalette:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourceHot_SourceStandby_FindPalette
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_PaletteFound:
.a16
.i16
    txa
    sta.l SourceStandby_PalRecord
    lsr a
    lsr a
    lsr a
    sta.l SourceStandby_Palette
    lda #0
    sta.l SourceStandby_Piece
SourceHot_SourceStandby_FindPiece:
.a16
.i16
    lda.l SourceStandby_Piece
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceStandby_PiecesLong+12,x
    sta.l SourceStandby_Missing
    ldx #0
SourceHot_SourceStandby_FindBlock:
.a16
.i16
    lda.l SourceVisual_BlockCache,x
    cmp.l SourceStandby_Missing
    bne SourceHot_SourceStandby_NextBlock
    lda.l SourceVisual_BlockCache+2,x
    cmp #2
    beq SourceHot_SourceStandby_BlockFound
SourceHot_SourceStandby_NextBlock:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #512
    bcc SourceHot_SourceStandby_FindBlock
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_BlockFound:
.a16
.i16
    txa
    lsr a
    lsr a
    lsr a
    pha
    lda.l SourceStandby_Piece
    tax
    pla
    sep #$20
.a8
    sta.l SourceStandby_Map,x
    rep #$30
.a16
.i16
    lda.l SourceStandby_Piece
    inc a
    sta.l SourceStandby_Piece
    cmp #10
    bcc SourceHot_SourceStandby_FindPiece
    jsl SourceHot_SourceStandby_FreshScope
    bcs SourceHot_SourceStandby_G64
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G64:
.a16
.i16
    lda.l Game_StageIndex
    cmp #0
    beq SourceHot_SourceStandby_G65
    brl SourceHot_SourceStandby_Done
SourceHot_SourceStandby_G65:
.a16
.i16
    ; All physical identities are ready. NMI cannot reallocate any cache row.
    ; Commit pins first, publish lease/template magic last, while writer-busy.
    lda #1
    sta.l SourceAttackOwned_Busy
    lda #0
    sta.l SourceStandby_Piece
SourceHot_SourceStandby_PinBlocks:
.a16
.i16
    lda.l SourceStandby_Piece
    tax
    lda.l SourceStandby_Map,x
    and #255
    asl a
    asl a
    asl a
    tax
    lda.l SVActor_HeldBlocks,x
    ora.l SourceStandby_Pin
    sta.l SVActor_HeldBlocks,x
    lda.l SourceStandby_Piece
    inc a
    sta.l SourceStandby_Piece
    cmp #10
    bcc SourceHot_SourceStandby_PinBlocks
    lda.l SourceStandby_PalRecord
    tax
    lda.l SVActor_HeldPalettes,x
    ora.l SourceStandby_Pin
    sta.l SVActor_HeldPalettes,x
    sep #$20
.a8
    lda #$30
    jsl StageFp_BG2OamAttr
    rep #$30
.a16
.i16
    and #255
    sta.l SourceStandby_Attr
    lda.l SourceStandby_Target
    and #1
    beq SourceHot_SourceStandby_Built0
    lda #0
    sta.l SourceStandby_Lease
    lda #0
    sta.l SourceStandby_Template
    jsr SourceHot_SourceStandby_BuildOne
SourceHot_SourceStandby_Built0:
.a16
.i16
    lda.l SourceStandby_Target
    and #2
    beq SourceHot_SourceStandby_Built1
    lda #1024
    sta.l SourceStandby_Lease
    lda #128
    sta.l SourceStandby_Template
    jsr SourceHot_SourceStandby_BuildOne
SourceHot_SourceStandby_Built1:
.a16
.i16
    lda.l SourceStandby_Target
    ora.l SourceStandby_FaceMask
    sta.l SourceStandby_FaceMask
    lda.l SourceStandby_Target
    sta.l SourceStandby_Result
    lda #0
    sta.l SourceAttackOwned_Busy
SourceHot_SourceStandby_Done:
.a16
.i16
    plb
    ply
    plx
    pla
    plp
    rtl
SourceHot_SourceStandby_BuildOne:
.a16
.i16
    lda.l SourceStandby_Lease
    tax
    lda #0
    sta.l $436C00,x
    sta.l $436C02,x
    lda #22
    sta.l $436C04,x
    lda #$0216
    sta.l $436C06,x
    lda #10
    sta.l $436C08,x
    lda #781
    sta.l $436C0A,x
    txa
    clc
    adc #$6C20
    tay
    ldx #SourceStandby_Header & $FFFF
    lda #23
    mvn $43,$3D
    lda.l SourceStandby_Lease
    clc
    adc #$6C38
    tay
    ldx #SourceStandby_State & $FFFF
    lda #31
    mvn $43,$3D
    lda.l SourceStandby_Lease
    tax
    lda.l SourceStandby_Palette
    inc a
    sta.l $436C48,x
    lda.l SourceStandby_Lease
    clc
    adc #$6C58
    tay
    ldx #SourceStandby_Pieces & $FFFF
    lda #159
    mvn $43,$3D
    lda.l SourceStandby_Template
    clc
    adc #$7400
    tay
    ldx #SourceStandby_TemplateHeader & $FFFF
    lda #23
    mvn $43,$3D
    lda #0
    sta.l SourceStandby_Piece
SourceHot_SourceStandby_FormatPiece:
.a16
.i16
    lda.l SourceStandby_Piece
    tax
    lda.l SourceStandby_Map,x
    and #255
    sta.l SourceStandby_Block
    and #7
    asl a
    sta.l SourceStandby_Tile
    lda.l SourceStandby_Block
    lsr a
    lsr a
    lsr a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    clc
    adc.l SourceStandby_Tile
    sta.l SourceStandby_Tile
    lda.l SourceStandby_Piece
    clc
    adc.l SourceStandby_Lease
    tax
    lda.l SourceStandby_Block
    sep #$20
.a8
    sta.l $436CF8,x
    rep #$30
.a16
.i16
    lda.l SourceStandby_Piece
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceStandby_PiecesLong,x
    clc
    adc #128
    sta.l SourceStandby_PosX
    lda.l SourceStandby_PiecesLong+2,x
    clc
    adc #150
    sta.l SourceStandby_PosY
    txa
    clc
    adc.l SourceStandby_Lease
    tax
    lda.l SourceStandby_Tile
    sta.l $436C66,x
    lda.l SourceStandby_Piece
    asl a
    asl a
    clc
    adc.l SourceStandby_Template
    tax
    sep #$20
.a8
    lda.l SourceStandby_PosX
    sta.l $437420,x
    lda.l SourceStandby_PosY
    sta.l $437421,x
    lda.l SourceStandby_Tile
    sta.l $437422,x
    rep #$30
.a16
.i16
    lda.l SourceStandby_Palette
    asl a
    ora.l SourceStandby_Attr
    sta.l SourceStandby_Block
    lda.l SourceStandby_Tile
    xba
    and #1
    ora.l SourceStandby_Block
    sep #$20
.a8
    sta.l $437423,x
    rep #$30
.a16
.i16
    lda.l SourceStandby_Piece
    clc
    adc.l SourceStandby_Template
    tax
    lda #0
    sep #$20
.a8
    sta.l $437448,x
    rep #$30
.a16
.i16
    lda.l SourceStandby_Piece
    inc a
    sta.l SourceStandby_Piece
    cmp #10
    bcs SourceHot_SourceStandby_FormatDone
    brl SourceHot_SourceStandby_FormatPiece
SourceHot_SourceStandby_FormatDone:
.a16
.i16
    lda.l SourceStandby_Lease
    tax
    lda #$A66C
    sta.l $436C00,x
    lda.l SourceStandby_Template
    tax
    lda #$A770
    sta.l $437400,x
    rts

; Initialize both new foreground authorities before the original owner magic.
SourceHot_SourceStandby_Init:
.a16
.i16
    php
    pha
    lda #0
    sta.l SourceStandby_FaceMask
    sta.l $437BFE
    sta.l $437BA6
    sta.l $437BA8
    sta.l $437BAC
    jsl SourceLayout_Defaults
    sta.l $437BC8
    sta.l $437BCE
    pla
    plp
    sta.l SourceAttackOwned_InitMagic
    rtl
; Only standby-created face0 templates need this additional native-face fence.
; The original accepted-source-role predicate remains authoritative.
SourceHot_SourceStandby_FaceLive:
.a16
.i16
    jsl SourceAttackMask_PatchLive
    bcs SourceHot_SourceStandby_FaceCheck
    rtl
SourceHot_SourceStandby_FaceCheck:
.a16
.i16
    php
    pha
    lda #$FFFF
    nop
    and.l $437A9C
    and #1
    beq SourceHot_SourceStandby_FaceNext
    jsl SourceGroundRoot_Face0
    and #255
    cmp.l SourceAttackTemplate_Base+20
    bne SourceHot_SourceStandby_FaceNo
SourceHot_SourceStandby_FaceNext:
.a16
.i16
    lda #$FFFF
    nop
    and.l $437A9C
    and #2
    beq SourceHot_SourceStandby_FaceYes
    jsl SourceGroundRoot_Face1
    and #255
    cmp.l SourceAttackTemplate_Base+148
    bne SourceHot_SourceStandby_FaceNo
SourceHot_SourceStandby_FaceYes:
.a16
.i16
    pla
    plp
    sec
    rtl
SourceHot_SourceStandby_FaceNo:
.a16
.i16
    pla
    plp
    clc
    rtl

; Bounded optional first-pose media after ordinary foreground work.

SourceHot_SourceStandby_FreshScope:
.a16
.i16
    php
    rep #$30
    pha
    lda.l $434E7C
    sta.l SourceStandby_Seq
    and #1

    beq SourceHot_SourceStandby_Fresh0
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh0:
.a16
.i16
    lda.l SourceAttackOwned_InitMagic
    cmp #$B077
    beq SourceHot_SourceStandby_Fresh1
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh1:
.a16
.i16
    lda.l SourceVisual_CompletedMagic
    cmp #$C04D
    beq SourceHot_SourceStandby_Fresh2
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh2:
.a16
.i16
    lda.l SVActor_Magic
    cmp #$AC19
    beq SourceHot_SourceStandby_Fresh3
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh3:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SourceHot_SourceStandby_Fresh4
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh4:
.a16
.i16
    lda.l Game_State
    cmp #$0000
    beq SourceHot_SourceStandby_Fresh5
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh5:
.a16
.i16
    lda.l Game_StageIndex
    cmp #$0000
    beq SourceHot_SourceStandby_Fresh6
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh6:
.a16
.i16
    lda.l Screen_PosX
    cmp #$0000
    beq SourceHot_SourceStandby_Fresh7
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh7:
.a16
.i16
    lda.l SourceAttackOwned_State
    cmp #$0000
    beq SourceHot_SourceStandby_Fresh8
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh8:
.a16
.i16
    lda.l SourceAttackOwned_Hold
    cmp #$0000
    beq SourceHot_SourceStandby_Fresh9
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh9:
.a16
.i16
    lda.l SourceAttackOwned_Busy
    cmp #$0000
    beq SourceHot_SourceStandby_Fresh10
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh10:
.a16
.i16
    lda.l SourcePacket_CopyBusy
    cmp #$0000
    beq SourceHot_SourceStandby_Fresh11
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh11:
.a16
.i16
    jsl SourceRewarm_Closed
    cmp #$0000
    beq SourceHot_SourceStandby_Fresh12
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh12:
.a16
.i16
    lda.l $437A96
    cmp #$0000
    beq SourceHot_SourceStandby_Fresh13
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh13:
.a16
.i16
    lda.l $437A98
    cmp #$0000
    beq SourceHot_SourceStandby_Fresh14
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh14:
.a16
.i16
    jsl SourceRewarm_PhysicalMask
    cmp #$0000
    beq SourceHot_SourceStandby_Fresh15
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh15:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    cmp #$0001
    beq SourceHot_SourceStandby_Fresh16
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh16:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #$0001
    beq SourceHot_SourceStandby_Fresh17
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh17:
.a16
.i16
    lda.l SourcePrefetch_PhysicalPending
    cmp #$0000
    beq SourceHot_SourceStandby_Fresh18
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh18:
.a16
.i16
    lda.l Game_CampaignId
    and #255
    cmp #3
    beq SourceHot_SourceStandby_Fresh19
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh19:
.a16
.i16
    lda.l $7E175E
    cmp #$0002
    beq SourceHot_SourceStandby_Fresh20
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh20:
.a16
.i16
    lda.l $7E1760
    cmp #$0001
    beq SourceHot_SourceStandby_Fresh21
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh21:
.a16
.i16
    lda.l $7E46DC
    cmp #$0001
    beq SourceHot_SourceStandby_Fresh22
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh22:
.a16
.i16
    lda.l $7E46DE
    cmp #$0000
    beq SourceHot_SourceStandby_Fresh23
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh23:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    beq SourceHot_SourceStandby_Fresh24
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh24:
.a16
.i16
    lda.l $434E2C
    cmp #$0000
    beq SourceHot_SourceStandby_Fresh25
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh25:
.a16
.i16
    jsl SourceRecover_Threshold
    nop
    nop
    nop
    bcs SourceHot_SourceStandby_Fresh26
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh26:
.a16
.i16
    lda.l $7E0A00+CHAR_INPUT_DRIVEN
    and #255
    cmp #1
    beq SourceHot_SourceStandby_Fresh27
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh27:
.a16
.i16
    lda.l $7E0A00+CHAR_ROSTER_INDEX
    and #255
    cmp #22
    beq SourceHot_SourceStandby_Fresh28
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh28:
.a16
.i16
    lda.l $7E0A00+CHAR_MAP_INDEX
    and #255
    cmp #0
    beq SourceHot_SourceStandby_Fresh29
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh29:
.a16
.i16
    lda.l $7E0A00+CHAR_HP
    and #255
    bne SourceHot_SourceStandby_Fresh30
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh30:
.a16
.i16
    lda.l StageBounds_State+0
    cmp #0
    beq SourceHot_SourceStandby_Fresh31
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh31:
.a16
.i16
    lda.l $434E40
    cmp #1
    beq SourceHot_SourceStandby_Fresh32
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh32:
.a16
.i16
    lda.l $434E42
    cmp #0
    beq SourceHot_SourceStandby_Fresh33
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh33:
.a16
.i16
    lda.l $434E4A
    and #255
    cmp #2
    beq SourceHot_SourceStandby_Fresh34
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh34:
.a16
.i16
    jsl SourceRecover_StandbyRole0
    and #255
    cmp #0
    beq SourceHot_SourceStandby_Fresh35
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh35:
.a16
.i16
    jsl SourceRecover_StandbyProfile0
    and #255
    cmp #8
    beq SourceHot_SourceStandby_Fresh36
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh36:
.a16
.i16
    lda.l $434E36
    cmp #188
    beq SourceHot_SourceStandby_Fresh37
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh37:
.a16
.i16
    lda.l $434E44
    bne SourceHot_SourceStandby_Fresh38
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh38:
.a16
.i16
    lda.l $434E44
    cmp #256
    bcc SourceHot_SourceStandby_Fresh39
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh39:
.a16
.i16
    lda.l $434E9C
    cmp #0
    beq SourceHot_SourceStandby_Fresh40
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh40:
.a16
.i16
    lda.l $7E0A85+CHAR_INPUT_DRIVEN
    and #255
    cmp #1
    beq SourceHot_SourceStandby_Fresh41
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh41:
.a16
.i16
    lda.l $7E0A85+CHAR_ROSTER_INDEX
    and #255
    cmp #22
    beq SourceHot_SourceStandby_Fresh42
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh42:
.a16
.i16
    lda.l $7E0A85+CHAR_MAP_INDEX
    and #255
    cmp #0
    beq SourceHot_SourceStandby_Fresh43
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh43:
.a16
.i16
    lda.l $7E0A85+CHAR_HP
    and #255
    bne SourceHot_SourceStandby_Fresh44
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh44:
.a16
.i16
    lda.l StageBounds_State+133
    cmp #0
    beq SourceHot_SourceStandby_Fresh45
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh45:
.a16
.i16
    lda.l $434E64
    cmp #1
    beq SourceHot_SourceStandby_Fresh46
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh46:
.a16
.i16
    lda.l $434E66
    cmp #0
    beq SourceHot_SourceStandby_Fresh47
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh47:
.a16
.i16
    lda.l $434E6E
    and #255
    cmp #2
    beq SourceHot_SourceStandby_Fresh48
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh48:
.a16
.i16
    jsl SourceRecover_StandbyRole1
    and #255
    cmp #0
    beq SourceHot_SourceStandby_Fresh49
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh49:
.a16
.i16
    jsl SourceRecover_StandbyProfile1
    and #255
    cmp #8
    beq SourceHot_SourceStandby_Fresh50
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh50:
.a16
.i16
    lda.l $434E5A
    cmp #188
    beq SourceHot_SourceStandby_Fresh51
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh51:
.a16
.i16
    lda.l $434E68
    bne SourceHot_SourceStandby_Fresh52
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh52:
.a16
.i16
    lda.l $434E68
    cmp #256
    bcc SourceHot_SourceStandby_Fresh53
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh53:
.a16
.i16
    lda.l $434E9E
    cmp #133
    beq SourceHot_SourceStandby_Fresh54
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh54:
.a16
.i16
    jsl SourceHotJump_NoPendingInput
    bcs SourceHot_SourceStandby_FreshJumpClear
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_FreshJumpClear:
.a16
.i16
    lda.l $434E7C
    cmp.l SourceStandby_Seq
    beq SourceHot_SourceStandby_Fresh55
    brl SourceHot_SourceStandby_FreshNo
SourceHot_SourceStandby_Fresh55:
.a16
.i16
    pla
    plp
    sec
    rtl
SourceHot_SourceStandby_FreshNo:
.a16
.i16
    pla
    plp
    clc
    rtl

SourceHot_SourceWarm_TransientNo:
.a16
.i16
    lda #1
    sta.l $437B94
    jml SourceHot_SourceWarm_Plan__no

SourceHot_SourceWarm_Plan:
.a16
.i16
    php
    rep #$30
    cld
    pha
    phx
    phy
    phb
    phd
    lda #0
    sta.l $437B94
    sta.l $437B98
    lda 8,s
    cmp #10
    bcc SourceHot_SourceWarm_Index
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Index:
.a16
.i16
    lda.l $437BFE
    cmp #$B6A5
    beq SourceHot_SourceWarm_Authorized
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Authorized:
.a16
.i16
    jsl SourceRewarm_Closed
    ora.l Screen_PosX
    beq SourceHot_SourceWarm_Cold
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Cold:
.a16
.i16
    jsl SourceRecover_WarmRoles
    nop
    nop
    nop
    nop
    and #255
    beq SourceHot_SourceWarm_Idle
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Idle:
.a16
.i16
    lda #0
    sta.l SourcePrefetch_Plan+20
    lda 8,s
    asl a
    tax
    lda.l SourcePrefetch_HotIds,x
    sta.l SourcePrefetch_Plan
    lda.l SourcePrefetch_HotBanks,x
    sta.l SourcePrefetch_Plan+2
    lda.l SourcePrefetch_HotAddresses,x
    sta.l SourcePrefetch_Plan+4
SourceHot_SourceWarm_Plan__guard49:
.a16
.i16
    ldx #0
SourceHot_SourceWarm_Plan__cache:
.a16
.i16
    lda.l SourceVisual_BlockCache+2,x
    beq SourceHot_SourceWarm_Plan__cache_next
    cmp #1
    beq SourceHot_SourceWarm_Plan__pending
    cmp #2
    beq SourceHot_SourceWarm_Plan__guard50
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard50:
.a16
.i16
    bra SourceHot_SourceWarm_Plan__present
SourceHot_SourceWarm_Plan__pending:
.a16
.i16
    lda.l SourceVisual_BlockCache+5,x
    and #$00FF
    cmp #4
    beq SourceHot_SourceWarm_Plan__guard51
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard51:
.a16
.i16
    jsl SourceHot_SourceWarm_LoadingDispatch
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
SourceHot_SourceWarm_Plan__guard52:
.a16
.i16
SourceHot_SourceWarm_Plan__present:
.a16
.i16
    lda.l SourceVisual_BlockCache,x
    cmp.l SourcePrefetch_Plan
    bne SourceHot_SourceWarm_Plan__guard53
    lda #1
    sta.l SourcePrefetch_Plan+20
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard53:
.a16
.i16
SourceHot_SourceWarm_Plan__cache_next:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #512
    bcs SourceHot_SourceWarm_Plan__cache_done
    brl SourceHot_SourceWarm_Plan__cache
SourceHot_SourceWarm_Plan__cache_done:
.a16
.i16
    lda #64
    sta.l SourcePrefetch_Plan+24
    lda #266
    sta.l SourcePrefetch_Plan+26
    lda #1280
    sta.l SourcePrefetch_Plan+28
SourceHot_SourceWarm_Plan__npc:
.a16
.i16
    lda.l SourcePrefetch_Plan+24
    tax
    lda.l SourceVisual_State+6,x
    beq SourceHot_SourceWarm_Plan__npc_next
    lda.l SourcePrefetch_Plan+26
    tax
    lda.l $7E0A00+CHAR_HP,x
    and #$00FF
    beq SourceHot_SourceWarm_Plan__npc_next
    lda.l SourceVisual_Sa1OwnerPolicy,x
    and #$00FF
    cmp #2
    bne SourceHot_SourceWarm_Plan__npc_next
    lda.l SourcePrefetch_Plan+28
    tax
    lda.l SVActor_Data+SVActor_Valid,x
    cmp #1
    beq SourceHot_SourceWarm_Plan__guard54
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard54:
.a16
.i16
SourceHot_SourceWarm_Plan__npc_next:
.a16
.i16
    lda.l SourcePrefetch_Plan+26
    clc
    adc #133
    sta.l SourcePrefetch_Plan+26
    lda.l SourcePrefetch_Plan+28
    clc
    adc #1280
    sta.l SourcePrefetch_Plan+28
    lda.l SourcePrefetch_Plan+24
    clc
    adc #32
    sta.l SourcePrefetch_Plan+24
    cmp #192
    bcs SourceHot_SourceWarm_Plan__find_empty
    brl SourceHot_SourceWarm_Plan__npc
SourceHot_SourceWarm_Plan__find_empty:
.a16
.i16
    ldx #504
SourceHot_SourceWarm_Plan__empty:
.a16
.i16
    lda.l SourceVisual_BlockCache+2,x
    bne SourceHot_SourceWarm_Plan__empty_next
    lda.l SourceVisual_BlockCache+4,x
    and #$00FF
    bne SourceHot_SourceWarm_Plan__empty_next
    lda.l SVActor_HeldBlocks,x
    ora.l SVActor_OldBlocks,x
    and #$00FF
    beq SourceHot_SourceWarm_Plan__found
SourceHot_SourceWarm_Plan__empty_next:
.a16
.i16
    txa
    sec
    sbc #8
    bcc SourceHot_SourceWarm_Plan__no_near
    tax
    bra SourceHot_SourceWarm_Plan__empty
SourceHot_SourceWarm_Plan__no_near:
.a16
.i16
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__found:
.a16
.i16
    txa
    sta.l SourcePrefetch_Plan+6
    lsr a
    lsr a
    lsr a
    sta.l SourcePrefetch_Plan+8
    lda 8,s
    cmp #22
    bcc SourceHot_SourceWarm_Plan__guard0
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard0:
.a16
.i16
    lda.l $7E46DE
    beq SourceHot_SourceWarm_Plan__guard1
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard1:
.a16
.i16
    jsr SourceHot_SourceWarm_Scope
    bcs SourceHot_SourceWarm_Plan__guard2
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard2:
.a16
.i16
    lda.l Game_StageIndex
    beq SourceHot_SourceWarm_Plan__guard3
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard3:
.a16
.i16
    lda.l Nmi_FrameBusy
    and #$00FF
    cmp #2
    bcc SourceHot_SourceWarm_Plan__guard4
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard4:
.a16
.i16
    jsl SourcePrefetch_BatchPending
    bcs SourceHot_SourceWarm_Plan__guard5
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard5:
.a16
.i16
    lda.l $7E0A00+0+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    beq SourceHot_SourceWarm_Plan__guard6
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard6:
.a16
.i16
    lda.l $7E0A00+0+CHAR_ROSTER_INDEX
    and #$00FF
    cmp #22
    beq SourceHot_SourceWarm_Plan__guard7
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard7:
.a16
.i16
    lda.l $7E0A00+0+CHAR_MAP_INDEX
    and #$00FF
    cmp #0
    beq SourceHot_SourceWarm_Plan__guard8
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard8:
.a16
.i16
    lda.l $7E0A00+0+CHAR_HP
    and #$00FF
    bne SourceHot_SourceWarm_Plan__guard9
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard9:
.a16
.i16
    lda.l $7E0A00+0+CHAR_SELECTED
    and #$00FF
    cmp #3
    bcc SourceHot_SourceWarm_Plan__guard10
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard10:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy+0
    and #$00FF
    cmp #2
    beq SourceHot_SourceWarm_Plan__guard11
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard11:
.a16
.i16
SourceHot_SourceWarm_Plan__guard15:
.a16
.i16
    lda.l $7E0A00+133+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    beq SourceHot_SourceWarm_Plan__guard16
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard16:
.a16
.i16
    lda.l $7E0A00+133+CHAR_ROSTER_INDEX
    and #$00FF
    cmp #22
    beq SourceHot_SourceWarm_Plan__guard17
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard17:
.a16
.i16
    lda.l $7E0A00+133+CHAR_MAP_INDEX
    and #$00FF
    cmp #0
    beq SourceHot_SourceWarm_Plan__guard18
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard18:
.a16
.i16
    lda.l $7E0A00+133+CHAR_HP
    and #$00FF
    bne SourceHot_SourceWarm_Plan__guard19
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard19:
.a16
.i16
    lda.l $7E0A00+133+CHAR_SELECTED
    and #$00FF
    cmp #3
    bcc SourceHot_SourceWarm_Plan__guard20
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard20:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy+133
    and #$00FF
    cmp #2
    beq SourceHot_SourceWarm_Plan__guard21
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard21:
.a16
.i16
SourceHot_SourceWarm_Plan__guard25:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    cmp #1
    beq SourceHot_SourceWarm_Plan__guard26
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard26:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourceHot_SourceWarm_Plan__guard27
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard27:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    beq SourceHot_SourceWarm_Plan__snapshot_magic
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__snapshot_magic:
.a16
.i16
    lda.l $434E2C
    cmp #0
    beq SourceHot_SourceWarm_Plan__snapshot0
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__snapshot0:
.a16
.i16
    lda.l $434E9C
    cmp #0
    beq SourceHot_SourceWarm_Plan__snapshot1
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__snapshot1:
.a16
.i16
    lda.l $434E9E
    cmp #133
    beq SourceHot_SourceWarm_Plan__snapshot2
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__snapshot2:
.a16
.i16
    lda.l $434E3C
    cmp #18
    beq SourceHot_SourceWarm_Plan__snapshot3
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__snapshot3:
.a16
.i16
    lda.l $434E40
    cmp #1
    beq SourceHot_SourceWarm_Plan__snapshot4
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__snapshot4:
.a16
.i16
    lda.l $434E42
    cmp #0
    beq SourceHot_SourceWarm_Plan__snapshot5
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__snapshot5:
.a16
.i16
    lda.l $434E4A
    and #$00FF ; snapshot policy/role is a packed byte mirror
    cmp #2
    beq SourceHot_SourceWarm_Plan__snapshot6
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__snapshot6:
.a16
.i16
    jsl SourceRecover_WarmRole0
    and #$00FF ; snapshot policy/role is a packed byte mirror
    cmp #0
    beq SourceHot_SourceWarm_Plan__snapshot7
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__snapshot7:
.a16
.i16
    lda.l $434E54
    cmp #8
    beq SourceHot_SourceWarm_Plan__snapshot8
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__snapshot8:
.a16
.i16
    lda.l $434E60
    cmp #18
    beq SourceHot_SourceWarm_Plan__snapshot9
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__snapshot9:
.a16
.i16
    lda.l $434E64
    cmp #1
    beq SourceHot_SourceWarm_Plan__snapshot10
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__snapshot10:
.a16
.i16
    lda.l $434E66
    cmp #0
    beq SourceHot_SourceWarm_Plan__snapshot11
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__snapshot11:
.a16
.i16
    lda.l $434E6E
    and #$00FF ; snapshot policy/role is a packed byte mirror
    cmp #2
    beq SourceHot_SourceWarm_Plan__snapshot12
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__snapshot12:
.a16
.i16
    jsl SourceRecover_WarmRole1
    and #$00FF ; snapshot policy/role is a packed byte mirror
    cmp #0
    beq SourceHot_SourceWarm_Plan__snapshot13
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__snapshot13:
.a16
.i16
    lda.l $434E78
    cmp #8
    beq SourceHot_SourceWarm_Plan__snapshot14
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__snapshot14:
.a16
.i16
    lda.l $434E44
    bne SourceHot_SourceWarm_Plan__source_hp0
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__source_hp0:
.a16
.i16
    lda.l $434E68
    bne SourceHot_SourceWarm_Plan__source_hp1
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__source_hp1:
.a16
.i16
    lda.l $434E7C
    bit #1
    beq SourceHot_SourceWarm_Plan__snapshot_even
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__snapshot_even:
.a16
.i16
    sta.l SourcePrefetch_Plan+30
    lda #0
    sta.l SourcePrefetch_Plan+20
    lda 8,s
    asl a
    tax
    lda.l SourcePrefetch_HotIds,x
    sta.l SourcePrefetch_Plan
    lda.l SourcePrefetch_HotBanks,x
    sta.l SourcePrefetch_Plan+2
    lda.l SourcePrefetch_HotAddresses,x
    sta.l SourcePrefetch_Plan+4
    lda.l SourceInput_Producer
    cmp #64
    bcc SourceHot_SourceWarm_Plan__guard28
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard28:
.a16
.i16
    sta.l SourcePrefetch_Plan+12
    lda.l SourceInput_Consumer
    cmp #64
    bcc SourceHot_SourceWarm_Plan__guard29
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard29:
.a16
.i16
    sta.l SourcePrefetch_Plan+14
SourceHot_SourceWarm_Plan__input:
.a16
.i16
    lda.l SourcePrefetch_Plan+14
    cmp.l SourcePrefetch_Plan+12
    beq SourceHot_SourceWarm_Plan__latest
    asl a
    asl a
    tax
    lda.l SourceInput_Ring,x
    ora.l SourceInput_Ring+2,x
    and #$F0FF
    beq SourceHot_SourceWarm_Plan__guard30
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard30:
.a16
.i16
    lda.l SourcePrefetch_Plan+14
    inc a
    and #63
    sta.l SourcePrefetch_Plan+14
    brl SourceHot_SourceWarm_Plan__input
SourceHot_SourceWarm_Plan__latest:
.a16
.i16
    lda.l SourcePrefetch_Plan+12
    dec a
    and #63
    asl a
    asl a
    tax
    jsl SourceRecover_PlanLatest
    nop
    nop
    nop
    nop
    beq SourceHot_SourceWarm_Plan__guard31
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard31:
.a16
.i16
    lda #0
    sta.l SourcePrefetch_Plan+16
    sta.l SourcePrefetch_Plan+18
    ldx #0
SourceHot_SourceWarm_Plan__queue:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourceHot_SourceWarm_Plan__queue_active
    brl SourceHot_SourceWarm_Plan__queue_next
SourceHot_SourceWarm_Plan__queue_active:
.a16
.i16
    phx
    txa
    lsr a
    lsr a
    lsr a
    tax
    lda.l DmaQueue_Owner,x
    and #$00FF
    plx
    cmp #0 ; PLX changes Z: compare the saved owner after restoring X
    beq SourceHot_SourceWarm_Plan__guard32
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard32:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    cmp #$40
    beq SourceHot_SourceWarm_Plan__vram
    cmp #$41
    beq SourceHot_SourceWarm_Plan__oam
    jsl SourceHot_SourceWarm_QueueDispatch
    nop
    nop
    nop
    nop
SourceHot_SourceWarm_Plan__guard33:
.a16
.i16
    lda.l DmaQueue,x
    cmp #1
    bcs SourceHot_SourceWarm_Plan__guard34
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard34:
.a16
.i16
    cmp #33
    bcc SourceHot_SourceWarm_Plan__guard35
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard35:
.a16
.i16
    clc
    adc.l DmaQueue+2,x
    bcc SourceHot_SourceWarm_Plan__guard36
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard36:
.a16
.i16
    cmp #513
    bcc SourceHot_SourceWarm_Plan__guard37
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard37:
.a16
.i16
    brl SourceHot_SourceWarm_Plan__queue_add
SourceHot_SourceWarm_Plan__oam:
.a16
.i16
    lda.l DmaQueue,x
    cmp #1
    bcs SourceHot_SourceWarm_Plan__guard38
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard38:
.a16
.i16
    cmp #545
    bcc SourceHot_SourceWarm_Plan__guard39
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard39:
.a16
.i16
    lda.l DmaQueue+2,x
    beq SourceHot_SourceWarm_Plan__guard40
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard40:
.a16
.i16
    brl SourceHot_SourceWarm_Plan__queue_add
SourceHot_SourceWarm_Plan__vram:
.a16
.i16
    lda.l DmaQueue,x
    cmp #1
    bcs SourceHot_SourceWarm_Plan__guard41
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard41:
.a16
.i16
    cmp #257
    bcc SourceHot_SourceWarm_Plan__guard42
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard42:
.a16
.i16
    dec a
    clc
    adc.l DmaQueue+2,x
    bcc SourceHot_SourceWarm_Plan__guard43
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard43:
.a16
.i16
    cmp #$8000
    bcc SourceHot_SourceWarm_Plan__queue_add
    lda.l DmaQueue+2,x
    cmp #$C000
    bcs SourceHot_SourceWarm_Plan__guard44
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard44:
.a16
.i16
SourceHot_SourceWarm_Plan__queue_add:
.a16
.i16
    lda.l DmaQueue,x
    bit #1
    beq SourceHot_SourceWarm_Plan__even_length
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__even_length:
.a16
.i16
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$43
    bne SourceHot_SourceWarm_Plan__not_private_oam
    lda.l DmaQueue+4,x
    and #$00FF
    cmp #$41
    bne SourceHot_SourceWarm_Plan__bad_source
    lda.l DmaQueue,x
    cmp #544
    bne SourceHot_SourceWarm_Plan__bad_source
    lda.l DmaQueue+5,x
    cmp #$4F00
    beq SourceHot_SourceWarm_Plan__source_checked
    bra SourceHot_SourceWarm_Plan__bad_source
SourceHot_SourceWarm_Plan__not_private_oam:
.a16
.i16
    cmp #$7E
    beq SourceHot_SourceWarm_Plan__source_span
    cmp #$7F
    beq SourceHot_SourceWarm_Plan__source_span
    cmp #$40
    bcs SourceHot_SourceWarm_Plan__bad_source
    lda.l DmaQueue+5,x
    cmp #$8000
    bcs SourceHot_SourceWarm_Plan__source_span
SourceHot_SourceWarm_Plan__bad_source:
.a16
.i16
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__source_span:
.a16
.i16
    lda.l DmaQueue,x
    dec a
    clc
    adc.l DmaQueue+5,x
    bcc SourceHot_SourceWarm_Plan__source_checked
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__source_checked:
.a16
.i16
    lda.l DmaQueue,x
    clc
    adc.l SourcePrefetch_Plan+16
    bcc SourceHot_SourceWarm_Plan__guard45
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard45:
.a16
.i16
    sta.l SourcePrefetch_Plan+16
    lda.l SourcePrefetch_Plan+18
    inc a
    sta.l SourcePrefetch_Plan+18
SourceHot_SourceWarm_Plan__queue_next:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcs SourceHot_SourceWarm_Plan__queue_done
    brl SourceHot_SourceWarm_Plan__queue
SourceHot_SourceWarm_Plan__queue_done:
.a16
.i16
    lda.l SourcePrefetch_Plan+16
    cmp.l DmaQueue_BudgetTotal
    beq SourceHot_SourceWarm_Plan__guard46
    brl SourceHot_SourceWarm_TransientNo
SourceHot_SourceWarm_Plan__guard46:
.a16
.i16
    jsl SourceHot_SourceWarm_BudgetDispatch
    nop
    nop
    nop
    nop
SourceHot_SourceWarm_Plan__guard47:
.a16
.i16
    lda.l SourcePrefetch_Plan+18
    cmp #7
    bcc SourceHot_SourceWarm_Plan__guard48
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__guard48:
.a16
.i16
    lda.l DmaQueue_CurrentSlot
    and #7
    beq SourceHot_SourceWarm_Plan__Commit
    brl SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Plan__Commit:
.a16
.i16
    lda.l SourceInput_Producer
    cmp.l SourcePrefetch_Plan+12
    beq SourceHot_SourceWarm_Plan__guard55
    brl SourceHot_SourceWarm_TransientNo
SourceHot_SourceWarm_Plan__guard55:
.a16
.i16
    lda.l $434E7C
    cmp.l SourcePrefetch_Plan+30
    beq SourceHot_SourceWarm_Plan__snapshot_still_current
    brl SourceHot_SourceWarm_TransientNo
SourceHot_SourceWarm_Plan__snapshot_still_current:
.a16
.i16
    lda #1
    sta.l $437B98
    pld
    plb
    ply
    plx
    pla
    plp
    sec
    rtl
SourceHot_SourceWarm_Plan__no:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    clc
    rtl
SourceHot_SourceWarm_QueueDispatch:
.a16
.i16
    cmp #$42
    beq SourceHot_SourceWarm_QueueCgram
    cmp #$43
    bne SourceHot_SourceWarm_QueueNo
    lda.l $437BFE
    cmp #$B6A5
    bne SourceHot_SourceWarm_QueueNo
    jsl SourcePrefetch_ValidateJob
    bcc SourceHot_SourceWarm_QueueNo
    rep #$20
    pla
    sep #$20
.a8
    pla
    rep #$20
.a16
    jml SourceHot_SourceWarm_Plan__queue_add
SourceHot_SourceWarm_QueueCgram:
.a16
.i16
    rep #$20
    pla
    sep #$20
.a8
    pla
    rep #$20
.a16
    jml SourceHot_SourceWarm_Plan__guard33
SourceHot_SourceWarm_QueueNo:
.a16
.i16
    rep #$20
    pla
    sep #$20
.a8
    pla
    rep #$20
.a16
    jml SourceHot_SourceWarm_Plan__no

SourceHot_SourceWarm_LoadingDispatch:
.a16
.i16
    lda.l SourceVisual_BlockCache+6,x
    cmp #1
    beq SourceHot_SourceWarm_LoadingPresent
    cmp #2
    beq SourceHot_SourceWarm_LoadingPresent
    cmp #$A702
    beq SourceHot_SourceWarm_LoadingPresent
    cmp #$A602
    bne SourceHot_SourceWarm_LoadingNo
    lda.l $437BFE
    cmp #$B6A5
    bne SourceHot_SourceWarm_LoadingNo
    phx
    phy
    ldx #0
SourceHot_SourceWarm_LoadingScan:
.a16
.i16
    jsl SourcePrefetch_ValidateJob
    bcc SourceHot_SourceWarm_LoadingNext
    cmp 3,s
    beq SourceHot_SourceWarm_LoadingFound
SourceHot_SourceWarm_LoadingNext:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourceHot_SourceWarm_LoadingScan
    ply
    plx
    bra SourceHot_SourceWarm_LoadingNo
SourceHot_SourceWarm_LoadingFound:
.a16
.i16
    ply
    plx
SourceHot_SourceWarm_LoadingPresent:
.a16
.i16
    rep #$20
    pla
    sep #$20
.a8
    pla
    rep #$20
.a16
    jml SourceHot_SourceWarm_Plan__present
SourceHot_SourceWarm_LoadingNo:
.a16
.i16
    rep #$20
    pla
    sep #$20
.a8
    pla
    rep #$20
.a16
    jml SourceHot_SourceWarm_Plan__no

SourceHot_SourceWarm_BudgetDispatch:
.a16
.i16
    jsl SourceStandby_BudgetCompare
    bcs SourceHot_SourceWarm_BudgetNo
    rep #$20
    pla
    sep #$20
.a8
    pla
    rep #$20
.a16
    jml SourceHot_SourceWarm_Plan__guard47
SourceHot_SourceWarm_BudgetNo:
.a16
.i16
    rep #$20
    pla
    sep #$20
.a8
    pla
    rep #$20
.a16
    jml SourceHot_SourceWarm_Plan__no
SourceHot_SourceWarm_Scope:
.a16
.i16
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
beq SourceHot_SourceWarm_Scope__guard0
    brl SourceHot_SourceWarm_Scope__no
SourceHot_SourceWarm_Scope__guard0:
.a16
.i16
    lda.l Game_State
    cmp #0
beq SourceHot_SourceWarm_Scope__guard1
    brl SourceHot_SourceWarm_Scope__no
SourceHot_SourceWarm_Scope__guard1:
.a16
.i16
    lda.l $7E175E
    cmp #2
beq SourceHot_SourceWarm_Scope__guard2
    brl SourceHot_SourceWarm_Scope__no
SourceHot_SourceWarm_Scope__guard2:
.a16
.i16
    lda.l $7E1760
    cmp #1
beq SourceHot_SourceWarm_Scope__guard3
    brl SourceHot_SourceWarm_Scope__no
SourceHot_SourceWarm_Scope__guard3:
.a16
.i16
    lda.l $7E46DC
    cmp #1
beq SourceHot_SourceWarm_Scope__guard4
    brl SourceHot_SourceWarm_Scope__no
SourceHot_SourceWarm_Scope__guard4:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
beq SourceHot_SourceWarm_Scope__guard5
    brl SourceHot_SourceWarm_Scope__no
SourceHot_SourceWarm_Scope__guard5:
.a16
.i16
    lda.l SourceVisual_CompletedMagic
    cmp #$C04D
beq SourceHot_SourceWarm_Scope__guard6
    brl SourceHot_SourceWarm_Scope__no
SourceHot_SourceWarm_Scope__guard6:
.a16
.i16
    lda.l SVActor_Magic
    cmp #$AC19
beq SourceHot_SourceWarm_Scope__guard7
    brl SourceHot_SourceWarm_Scope__no
SourceHot_SourceWarm_Scope__guard7:
.a16
.i16
    sec
    rts
SourceHot_SourceWarm_Scope__no:
.a16
.i16
    clc
    rts


SourceHot_SourcePrefetch_TryOne:
.a16
.i16
    php
    rep #$30
    cld
    pha
    phx
    phy
    phb
    phd
    lda.l $7E46DE
    bne SourceHot_SourcePrefetch_TryOne__no_near
    jsr SourceHot_SourceNpc_Scope
    bcc SourceHot_SourcePrefetch_TryOne__no_near
    lda #0
    sta.l SourcePrefetch_Plan+20
    lda 8,s
    jsl SourceHot_SourceWarm_Plan
    bcs SourceHot_SourcePrefetch_TryOne__plan
SourceHot_SourcePrefetch_TryOne__no_near:
.a16
.i16
    brl SourceHot_SourcePrefetch_TryOne__no
SourceHot_SourcePrefetch_TryOne__plan:
.a16
.i16
    lda.l Nmi_FrameBusy
    and #$00FF
    cmp #2
    bcs SourceHot_SourcePrefetch_TryOne__no_near
    sta.l SourcePrefetch_Plan+32
    sep #$20
.a8
    lda #1
    sta.l Nmi_FrameBusy
    lda #0
    pha
    plb
    rep #$30
.a16
.i16
    lda.l SourceInput_Producer
    cmp.l SourcePrefetch_Plan+12
    bne SourceHot_SourcePrefetch_TryOne__abort_near
    lda.l SourceInput_Overflows
    bne SourceHot_SourcePrefetch_TryOne__abort_near
    lda.l $434E7C
    cmp.l SourcePrefetch_Plan+30
    bne SourceHot_SourcePrefetch_TryOne__abort_near
    jsl SourcePrefetch_BatchPending
    bcc SourceHot_SourcePrefetch_TryOne__abort_near
    jsl SourceStandby_BudgetCompare
    nop
    nop
    nop
    bcs SourceHot_SourcePrefetch_TryOne__abort_near
    lda.l SourcePrefetch_Plan+6
    tax
    lda.l SourceVisual_BlockCache+2,x
    bne SourceHot_SourcePrefetch_TryOne__abort_near
    lda.l SourceVisual_BlockCache+4,x
    and #$00FF
    bne SourceHot_SourcePrefetch_TryOne__abort_near
    lda.l SVActor_HeldBlocks,x
    ora.l SVActor_OldBlocks,x
    and #$00FF
    beq SourceHot_SourcePrefetch_TryOne__save
SourceHot_SourcePrefetch_TryOne__abort_near:
.a16
.i16
    brl SourceHot_SourcePrefetch_TryOne__restore_busy_no
SourceHot_SourcePrefetch_TryOne__save:
.a16
.i16
    lda.l SourceVisual_BlockCache,x
    sta.l SourcePrefetch_Plan+40
    lda.l SourceVisual_BlockCache+2,x
    sta.l SourcePrefetch_Plan+42
    lda.l SourceVisual_BlockCache+4,x
    sta.l SourcePrefetch_Plan+44
    lda.l SourceVisual_BlockCache+6,x
    sta.l SourcePrefetch_Plan+46
    ldx #0
SourceHot_SourcePrefetch_TryOne__save_request:
.a16
.i16
    lda.l DmaRequest_SourceAddrLow,x
    sta.l SourcePrefetch_Plan+48,x
    inx
    inx
    cpx #8
    bcc SourceHot_SourcePrefetch_TryOne__save_request
    lda.l SourcePrefetch_Plan+6
    tax
    lda #0
    sta.l SourceVisual_BucketMagic
    sta.l SourcePending_KnownClear
    lda.l SourcePrefetch_Plan
    sta.l SourceVisual_BlockCache,x
    lda #1
    sta.l SourceVisual_BlockCache+2,x
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_BlockCache+4,x
    lda #4
    sta.l SourceVisual_BlockCache+5,x
    lda #2
    sta.l SourceVisual_BlockCache+6,x
    lda #$A6
    sta.l SourceVisual_BlockCache+7,x
    lda.l SourcePrefetch_Plan+2
    sta.l DmaRequest_SourceBank
    lda #DMA_TYPE_SOURCE_BLOCK
    sta.l DmaRequest_TypeFlags
    rep #$30
.a16
.i16
    lda.l SourcePrefetch_Plan+4
    sta.l DmaRequest_SourceAddrLow
    lda #256
    sta.l DmaRequest_Length
    ; Slot->16x32 OBJ origin, matching the original allocator exactly.
    lda.l SourcePrefetch_Plan+8
    and #7
    asl a
    sta.l SourcePrefetch_Plan+34
    lda.l SourcePrefetch_Plan+8
    and #24
    asl a
    asl a
    asl a
    ora.l SourcePrefetch_Plan+34
    sta.l SourcePrefetch_Plan+34
    lda.l SourcePrefetch_Plan+8
    and #32
    asl a
    asl a
    asl a
    ora.l SourcePrefetch_Plan+34
    asl a
    asl a
    asl a
    asl a
    asl a
    clc
    adc #$8000
    sta.l DmaRequest_TargetAddr
    jsl Core_Dma_Enqueue_Long
    bcc SourceHot_SourcePrefetch_TryOne__rollback
    ; Enqueue returns its real chosen queue-byte X. Owner0 is a private
    ; producer, never the P1 completed/retiring owner bits64/128.
    txa
    lsr a
    lsr a
    lsr a
    tax
    sep #$20
.a8
    lda #0
    sta.l DmaQueue_Owner,x
    rep #$30
.a16
.i16
    lda.l SourcePrefetch_PhysicalPending
    inc a
    sta.l SourcePrefetch_PhysicalPending
    lda #2
    sta.l SourcePrefetch_Plan+20
    bra SourceHot_SourcePrefetch_TryOne__restore_request
SourceHot_SourcePrefetch_TryOne__rollback:
.a16
.i16
    lda.l SourcePrefetch_Plan+6
    tax
    lda.l SourcePrefetch_Plan+40
    sta.l SourceVisual_BlockCache,x
    lda.l SourcePrefetch_Plan+42
    sta.l SourceVisual_BlockCache+2,x
    lda.l SourcePrefetch_Plan+44
    sta.l SourceVisual_BlockCache+4,x
    lda.l SourcePrefetch_Plan+46
    sta.l SourceVisual_BlockCache+6,x
SourceHot_SourcePrefetch_TryOne__restore_request:
.a16
.i16
    ldx #0
SourceHot_SourcePrefetch_TryOne__request_word:
.a16
.i16
    lda.l SourcePrefetch_Plan+48,x
    sta.l DmaRequest_SourceAddrLow,x
    inx
    inx
    cpx #8
    bcc SourceHot_SourcePrefetch_TryOne__request_word
    sep #$20
.a8
    lda.l SourcePrefetch_Plan+32
    sta.l Nmi_FrameBusy
    rep #$30
.a16
.i16
    lda.l SourcePrefetch_Plan+20
    cmp #2
    bne SourceHot_SourcePrefetch_TryOne__no
    pld
    plb
    ply
    plx
    pla
    plp
    sec
    rtl
SourceHot_SourcePrefetch_TryOne__restore_busy_no:
.a16
.i16
    sep #$20
.a8
    lda.l SourcePrefetch_Plan+32
    sta.l Nmi_FrameBusy
    rep #$30
.a16
.i16
SourceHot_SourcePrefetch_TryOne__no:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    clc
    rtl
SourceHot_SourcePrefetch_SubmitEnd:
.a16
.i16

; Optional immutable attack tiles: one admission attempt per host field,
; after the existing first-NPC service. No palette or actor publication.
SourcePrefetch_Cursor = $7E46E8
SourcePrefetch_LastField = $7E46EA
SourcePrefetch_Submitted = $7E46EC
SourceHot_SourcePrefetch_Init:
.a16
.i16
    pha
    lda #0
    sta.l SourcePrefetch_PhysicalPending
    sta.l SourcePrefetch_Submitted
    sta.l SourceAttack_Borrowed
    lda #0 ; warm first visible attack frame
    sta.l SourcePrefetch_Cursor
    lda #$FFFF
    sta.l SourcePrefetch_LastField
    pla
    rtl

SourceHot_SourceNpc_Scope:
.a16
.i16
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
beq SourceHot_SourceNpc_Scope__guard0
    brl SourceHot_SourceNpc_Scope__no
SourceHot_SourceNpc_Scope__guard0:
.a16
.i16
    lda.l Game_State
    cmp #0
beq SourceHot_SourceNpc_Scope__guard1
    brl SourceHot_SourceNpc_Scope__no
SourceHot_SourceNpc_Scope__guard1:
.a16
.i16
    lda.l $7E175E
    cmp #2
beq SourceHot_SourceNpc_Scope__guard2
    brl SourceHot_SourceNpc_Scope__no
SourceHot_SourceNpc_Scope__guard2:
.a16
.i16
    lda.l $7E1760
    cmp #1
beq SourceHot_SourceNpc_Scope__guard3
    brl SourceHot_SourceNpc_Scope__no
SourceHot_SourceNpc_Scope__guard3:
.a16
.i16
    lda.l $7E46DC
    cmp #1
beq SourceHot_SourceNpc_Scope__guard4
    brl SourceHot_SourceNpc_Scope__no
SourceHot_SourceNpc_Scope__guard4:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
beq SourceHot_SourceNpc_Scope__guard5
    brl SourceHot_SourceNpc_Scope__no
SourceHot_SourceNpc_Scope__guard5:
.a16
.i16
    lda.l SourceVisual_CompletedMagic
    cmp #$C04D
beq SourceHot_SourceNpc_Scope__guard6
    brl SourceHot_SourceNpc_Scope__no
SourceHot_SourceNpc_Scope__guard6:
.a16
.i16
    lda.l SVActor_Magic
    cmp #$AC19
beq SourceHot_SourceNpc_Scope__guard7
    brl SourceHot_SourceNpc_Scope__no
SourceHot_SourceNpc_Scope__guard7:
.a16
.i16
    sec
    rts
SourceHot_SourceNpc_Scope__no:
.a16
.i16
    clc
    rts

SourceHot_End:
.assert SourceHot_End <= $05F000, "hot-only recovery exceeds verified unused ROM"
