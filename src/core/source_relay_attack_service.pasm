; Borrow the existing foreground relay producer turn for a coherently
; accepted first attack before the native mirror catches up. No extra turn,
; OAM emission or readiness shortcut. Existing ReadAttack and ServiceCurrent
; retain all ownership, first-NPC, key, metadata and physical DMA fences.
SourceWarm_RelayService:
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
    beq SourceWarm_RelayForeground
    brl SourceWarm_RelayNo
SourceWarm_RelayForeground:
.a16
.i16
    lda #0
    jsl SourceWarm_ReadAttack
    bcs SourceWarm_RelayCandidate
    lda #1
    jsl SourceWarm_ReadAttack
    bcs SourceWarm_RelayCandidate
    brl SourceWarm_RelayNo
SourceWarm_RelayCandidate:
.a16
.i16
    ; The reader rejects both native jumps. Also defer to an accepted peer
    ; jump whose native mirror has not yet caught up, then recheck sequence.
    lda.l SourceWarm_Slot
    beq SourceWarm_RelayPeerP2
    lda.l $434E50
    bra SourceWarm_RelayPeerRole
SourceWarm_RelayPeerP2:
.a16
.i16
    lda.l $434E74
SourceWarm_RelayPeerRole:
.a16
.i16
    and #$00FF
    cmp #7
    beq SourceWarm_RelayNo
    lda.l $434E7C
    cmp.l SourceWarm_Seq
    bne SourceWarm_RelayNo
    and #1
    bne SourceWarm_RelayNo
    lda.l SourceWarm_Slot
    beq SourceWarm_RelayP1
    lda #$0A85
    bra SourceWarm_RelayDp
SourceWarm_RelayP1:
.a16
.i16
    lda #$0A00
SourceWarm_RelayDp:
.a16
.i16
    tcd
SourceWarm_RelayJob:
.a16
.i16
    jsl SourceVisual_ServiceCurrent
SourceWarm_RelayConsumed:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    sec
    rtl
SourceWarm_RelayNo:
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
SourceWarm_RelayEnd:
