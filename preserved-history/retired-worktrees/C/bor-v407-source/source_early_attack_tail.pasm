; Foreground-only paired admission, before composition. P2 receives only
; the original metadata/lease selection prefix before the existing priority
; loader runs. No new transfer, Ready rule, pin protocol or emitted picture.
SourceEarlyAttack_Tail:
.a16
.i16
    lda.l $7E46DE
    beq SourceEarlyAttack_Foreground
SourceEarlyAttack_Pop:
.a16
.i16
    ply
    plx
    pla
    plp
    rtl
SourceEarlyAttack_Foreground:
.a16
.i16
    lda.l SourceReserve_Valid
    cmp #$1D1F
    bne SourceEarlyAttack_Pop
SourceEarlyAttack_Reserved:
.a16
.i16
    lda.l $434E50
    and #$00FF
    cmp #2
    bne SourceEarlyAttack_Pop
    lda.l $434E74
    and #$00FF
    cmp #2
    bne SourceEarlyAttack_Pop
SourceEarlyAttack_Check:
.a16
.i16
    lda #0
    jsl SourceWarm_ReadAttack
    bcc SourceEarlyAttack_Pop
    lda #1
    jsl SourceWarm_ReadAttack
    bcc SourceEarlyAttack_Pop
SourceEarlyAttack_Service:
.a16
.i16
    ; Successful coherent P2 reader preserves its input A=1. Both player
    ; attacks were authenticated immediately above; bootstrap reset owns0.
    sta.l SourceNpcFast_Armed
SourceEarlyAttack_AfterArm:
.a16
.i16
    phb
    phd
    sep #$20
.a8
    lda #0
    pha
    plb
    rep #$30
.a16
.i16
    lda #$0A85
    tcd
    lda #1
    sta.l SourceVisual_ServiceOnly
    lda #0
    sta.l SourceCritical_Completing
    jsl SourceEarlyAttack_Observe
    lda.l SourceVisual_CallCount
    inc a
    sta.l SourceVisual_CallCount
    jsl SourceEarlyAttack_Resume
    lda.l Nmi_FrameCounter
    cmp.l SourceVisual_PresentationField
    beq SourceEarlyAttack_SameField
    sta.l SourceVisual_PresentationField
    lda #0
    sta.l SourceVisual_PresentationMask
SourceEarlyAttack_SameField:
.a16
.i16
    jsl SourceEarlyAttack_Find
    bcc SourceEarlyAttack_Restore
    ; Original accepted reader excludes jumps, dead/rebound actors, first
    ; NPC work and StageBounds_State != 0. Keep original viewport admission.
    jsl SourceEarlyAttack_Viewport
    bcc SourceEarlyAttack_Restore
    jsl SourceEarlyAttack_Select
    bcc SourceEarlyAttack_Restore
    jsl SVActor_ServiceFirstNpcDuringWait
    jsl SourceEarlyAttack_CopyPeerMetadata
SourceEarlyAttack_Restore:
.a16
.i16
    pld
    plb
    jml SourceEarlyAttack_Pop
; Cross-bank adapters to original bank10 RTS routines. PEA supplies their
; short return to the RTL of an existing four-byte long-call bridge. That
; RTL consumes our original JSL frame; no return target is writable data.
SourceEarlyAttack_Observe:
.a16
.i16
    .db $F4 ; PEA absolute immediate
    .dw ((SourcePalette_Bridge_SVActor_Enabled+2)&$FFFF)
    jml SourceVisual_CompletedObserve
SourceEarlyAttack_Resume:
.a16
.i16
    .db $F4 ; PEA absolute immediate
    .dw ((SourcePalette_Bridge_SVActor_Enabled+2)&$FFFF)
    jml SourceVisual_ResumePendingBlock
SourceEarlyAttack_Find:
.a16
.i16
    .db $F4 ; PEA absolute immediate
    .dw ((SourcePalette_Bridge_SVActor_Enabled+2)&$FFFF)
    jml SourceVisual_FindEntry
SourceEarlyAttack_Viewport:
.a16
.i16
    .db $F4 ; PEA absolute immediate
    .dw ((SourcePalette_Bridge_SVActor_Enabled+2)&$FFFF)
    jml SourceVisual_FrameInViewport
SourceEarlyAttack_Select:
.a16
.i16
    .db $F4 ; PEA absolute immediate
    .dw ((SourcePalette_Bridge_SVActor_Enabled+2)&$FFFF)
    jml SourceVisual_SelectResidency

; Copy immutable metadata only. Source/target entries and stage must match.
SourceEarlyAttack_CopyPeerMetadata:
.a16
.i16
    php
    rep #$30
    cld
    pha
    phx
    phy
    phb
    lda.l Game_CampaignId
    and #255
    cmp #3
    beq SourceEarlyAttack_CopyGuard0
    brl SourceEarlyAttack_CopyDone
SourceEarlyAttack_CopyGuard0:
.a16
.i16
    lda.l Game_State
    cmp #0
    beq SourceEarlyAttack_CopyGuard1
    brl SourceEarlyAttack_CopyDone
SourceEarlyAttack_CopyGuard1:
.a16
.i16
    lda.l $7E46DE
    cmp #0
    beq SourceEarlyAttack_CopyGuard2
    brl SourceEarlyAttack_CopyDone
SourceEarlyAttack_CopyGuard2:
.a16
.i16
    lda.l $7E175E
    cmp #2
    beq SourceEarlyAttack_CopyGuard3
    brl SourceEarlyAttack_CopyDone
SourceEarlyAttack_CopyGuard3:
.a16
.i16
    lda.l $7E1760
    cmp #1
    beq SourceEarlyAttack_CopyGuard4
    brl SourceEarlyAttack_CopyDone
SourceEarlyAttack_CopyGuard4:
.a16
.i16
    lda.l $7E46DC
    cmp #1
    beq SourceEarlyAttack_CopyGuard5
    brl SourceEarlyAttack_CopyDone
SourceEarlyAttack_CopyGuard5:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #6752
    beq SourceEarlyAttack_CopyGuard6
    brl SourceEarlyAttack_CopyDone
SourceEarlyAttack_CopyGuard6:
.a16
.i16
    lda.l SourceVisual_CompletedMagic
    cmp #49229
    beq SourceEarlyAttack_CopyGuard7
    brl SourceEarlyAttack_CopyDone
SourceEarlyAttack_CopyGuard7:
.a16
.i16
    lda.l SVActor_Magic
    cmp #44057
    beq SourceEarlyAttack_CopyGuard8
    brl SourceEarlyAttack_CopyDone
SourceEarlyAttack_CopyGuard8:
.a16
.i16
    lda.l SVActor_MetaData+SVActor_MetaValid
    cmp #1
    beq SourceEarlyAttack_CopyGuard9
    brl SourceEarlyAttack_CopyDone
SourceEarlyAttack_CopyGuard9:
.a16
.i16
    lda.l SourceVisual_State+38
    cmp #1
    beq SourceEarlyAttack_CopyGuard10
    brl SourceEarlyAttack_CopyDone
SourceEarlyAttack_CopyGuard10:
.a16
.i16
    lda.l SourceVisual_State+60
    and #255
    cmp #0
    beq SourceEarlyAttack_CopyGuard11
    brl SourceEarlyAttack_CopyDone
SourceEarlyAttack_CopyGuard11:
.a16
.i16
    lda.l SourceVisual_State+61
    cmp #534
    beq SourceEarlyAttack_CopyGuard12
    brl SourceEarlyAttack_CopyDone
SourceEarlyAttack_CopyGuard12:
.a16
.i16
    lda.l SVActor_MetaData+4
    cmp #534
    beq SourceEarlyAttack_CopyGuard13
    brl SourceEarlyAttack_CopyDone
SourceEarlyAttack_CopyGuard13:
.a16
.i16
    lda.l SVActor_MetaData+SVActor_MetaStage
    cmp.l Game_StageIndex
    beq SourceEarlyAttack_CopyStage
    brl SourceEarlyAttack_CopyDone
SourceEarlyAttack_CopyStage:
.a16
.i16
    lda.l SVActor_MetaData
    cmp.l SourceVisual_State+32
    beq SourceEarlyAttack_CopyEntry
    brl SourceEarlyAttack_CopyDone
SourceEarlyAttack_CopyEntry:
.a16
.i16
    cmp #SOURCE_VISUAL_CATALOG_COUNT
    bcc SourceEarlyAttack_CopyIndex
    brl SourceEarlyAttack_CopyDone
SourceEarlyAttack_CopyIndex:
.a16
.i16
    lda.l SVActor_MetaData+6
    cmp #6
    bcc SourceEarlyAttack_CopyKey
    brl SourceEarlyAttack_CopyDone
SourceEarlyAttack_CopyKey:
.a16
.i16
    lda.l SVActor_MetaData+2
    beq SourceEarlyAttack_CopyDone
    cmp #66
    bcs SourceEarlyAttack_CopyDone
    lda.l SVActor_MetaData+16
    and #$00FF
    cmp.l SVActor_MetaData+2
    bne SourceEarlyAttack_CopyDone
    lda.l SVActor_MetaData+1280+SVActor_MetaValid
    cmp #1
    bne SourceEarlyAttack_CopyNow
    lda.l SVActor_MetaData+1280
    cmp.l SVActor_MetaData
    bne SourceEarlyAttack_CopyNow
    lda.l SVActor_MetaData+1280+SVActor_MetaStage
    cmp.l Game_StageIndex
    beq SourceEarlyAttack_CopyDone
SourceEarlyAttack_CopyNow:
.a16
.i16
    lda #0
    sta.l SVActor_MetaData+1280+SVActor_MetaValid
    lda.l SVActor_MetaData+2
    asl a
    asl a
    asl a
    asl a
    clc
    adc #27 ; 28-byte entry header + 16 bytes/piece - 1
    ldx #(SVActor_MetaData&$FFFF)
    ldy #((SVActor_MetaData+1280)&$FFFF)
    mvn $43,$43
    lda.l Game_StageIndex
    sta.l SVActor_MetaData+1280+SVActor_MetaStage
    lda #1
    sta.l SVActor_MetaData+1280+SVActor_MetaValid
SourceEarlyAttack_CopyDone:
.a16
.i16
    plb
    ply
    plx
    pla
    plp
    rtl
SourceEarlyAttack_End:
