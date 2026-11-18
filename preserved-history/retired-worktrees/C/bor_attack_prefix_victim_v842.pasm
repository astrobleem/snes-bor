; Prefer the first warm-up piece over a later attack piece when one of those
; optional tiles must be evicted. This is a tie-break among legal victims,
; never a new pin or a refusal to make progress. Reloading the prefix fits
; the existing bounded warm-up visit; a tail miss can miss that whole visit.
.bank 5
.org $C000
SourceAttackPrefix_Victim:
.a8
.i16
    rep #$31
.a16
    phx
    phy
    lda.l SourceAttackOwned_InitMagic
    cmp #$B077
    bne SourceAttackPrefix_Original
    lda.l Game_StageIndex
    bne SourceAttackPrefix_Original
    lda.l Game_CampaignId
    and #255
    cmp #3
    bne SourceAttackPrefix_Original
    lda.l SourcePrefetch_Cursor
    cmp #10
    bne SourceAttackPrefix_Original
    lda.l SourceVisual_BlockCache,x
    pha
    ldx #0
SourceAttackPrefix_CheckId:
.a16
.i16
    lda.l SourceAttackPrefix_Ids,x
    cmp 1,s
    beq SourceAttackPrefix_AttackVictim
    inx
    inx
    cpx #20
    bcc SourceAttackPrefix_CheckId
    pla
SourceAttackPrefix_Original:
.a16
.i16
    ply
    plx
    rep #$31
    jml SourceVisual_AllocateBlock__claim
SourceAttackPrefix_AttackVictim:
.a16
.i16
    pla
    ldx #504
SourceAttackPrefix_FindFirst:
.a16
.i16
    lda.l SourceVisual_BlockCache,x
    cmp #11120
    bne SourceAttackPrefix_Next
    lda.l SourceVisual_BlockCache+2,x
    cmp #2
    bne SourceAttackPrefix_Next
    lda.l SourceVisual_BlockCache+4,x
    ora.l SVActor_HeldBlocks,x
    ora.l SVActor_OldBlocks,x
    and #255
    bne SourceAttackPrefix_Next
    ply
    pla
    rep #$31
    jml SourceVisual_AllocateBlock__claim
SourceAttackPrefix_Next:
.a16
.i16
    txa
    sec
    sbc #8
    tax
    bpl SourceAttackPrefix_FindFirst
    bra SourceAttackPrefix_Original
SourceAttackPrefix_Ids:
    .dw 11120,6005,4493,14972,13713,12783,11465,15711,6374,203
SourceAttackPrefix_End:
.assert SourceAttackPrefix_End <= $05C200, "prefix-victim helper exceeds gap"
