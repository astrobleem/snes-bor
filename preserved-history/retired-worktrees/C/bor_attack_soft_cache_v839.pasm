; Soft preference only: prefer other legal victims over fully warmed attack
; media, but fall back to the original victim when no alternative exists.
; No cache state, pins, queue, input or resource readiness is changed here.
.bank 5
.org $C700
SourceAttackCache_SoftVictim:
.a8
.i16
    rep #$31
.a16
    phx
    phy
    lda.l SourceAttackOwned_InitMagic
    cmp #$B077
    bne SourceAttackCache_Original
    lda.l Game_CampaignId
    and #255
    cmp #3
    bne SourceAttackCache_Original
    lda.l Game_StageIndex
    bne SourceAttackCache_Original
    lda.l SourcePrefetch_Cursor
    cmp #10
    bne SourceAttackCache_Original
    lda.l SourcePrefetch_PhysicalPending
    bne SourceAttackCache_Original
    lda.l SourceVisual_BlockCache,x
    pha
    ldx #0
SourceAttackCache_FirstId:
    lda.l SourceAttackCache_Ids,x
    cmp 1,s
    beq SourceAttackCache_PreferOther
    inx
    inx
    cpx #20
    bcc SourceAttackCache_FirstId
    pla
SourceAttackCache_Original:
    ply
    plx
    rep #$31
    jml SourceVisual_AllocateBlock__claim
SourceAttackCache_PreferOther:
    ldy #504
SourceAttackCache_Alternative:
    tyx
    lda.l SourceVisual_BlockCache+2,x
    cmp #2
    bne SourceAttackCache_Next
    lda.l SourceVisual_BlockCache+4,x
    ora.l SVActor_HeldBlocks,x
    ora.l SVActor_OldBlocks,x
    and #255
    bne SourceAttackCache_Next
    lda.l SourceVisual_BlockCache,x
    pha
    ldx #0
SourceAttackCache_AlternativeId:
    lda.l SourceAttackCache_Ids,x
    cmp 1,s
    beq SourceAttackCache_IsAttack
    inx
    inx
    cpx #20
    bcc SourceAttackCache_AlternativeId
    pla
    pla
    tyx
    ply
    pla
    rep #$31
    jml SourceVisual_AllocateBlock__claim
SourceAttackCache_IsAttack:
    pla
SourceAttackCache_Next:
    tya
    sec
    sbc #8
    tay
    bpl SourceAttackCache_Alternative
    pla
    bra SourceAttackCache_Original
SourceAttackCache_Ids:
    .dw 11120,6005,4493,14972,13713,12783,11465,15711,6374,203
SourceAttackCache_End:
.assert SourceAttackCache_End <= $05C900, "soft cache preference exceeds gap"
