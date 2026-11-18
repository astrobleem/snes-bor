; Foreground-only paired admission, before composition. P2 receives only
; the original metadata/lease selection prefix before the existing priority
; loader runs. No new transfer, Ready rule, pin protocol or emitted picture.
SourceEarlyAttack_Tail:
.a16
.i16
    lda.l $7E46DE
    beq SourceEarlyAttack_Foreground
    jml SourceEarlyAttack_Pop
SourceEarlyAttack_Foreground:
.a16
.i16
    lda.l SourceReserve_Valid
    cmp #$1D1F
    beq SourceEarlyAttack_Reserved
    jml SourceEarlyAttack_Pop
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
SourceEarlyAttack_Restore:
.a16
.i16
    pld
    plb
SourceEarlyAttack_Pop:
.a16
.i16
    ply
    plx
    pla
    plp
    rtl
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
SourceEarlyAttack_End:
