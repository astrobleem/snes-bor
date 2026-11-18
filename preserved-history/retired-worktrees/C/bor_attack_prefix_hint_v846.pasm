; Choose a warm-up prefix only among legal unowned victims. The saved lease
; map is merely a hint: cache identity, physical readiness and every owner
; mask are checked anew. Never scan for an alternative or refuse allocation.
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
    bcc SourceAttackPrefix_Original
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
    lda.l $436CF8
    and #255
    jsr SourceAttackPrefix_Hint
    bcs SourceAttackPrefix_UseHint
    lda.l $4370F8
    and #255
    jsr SourceAttackPrefix_Hint
    bcc SourceAttackPrefix_Original
SourceAttackPrefix_UseHint:
.a16
.i16
    ply
    pla
    rep #$31
    jml SourceVisual_AllocateBlock__claim
SourceAttackPrefix_Hint:
.a16
.i16
    cmp #64
    bcs SourceAttackPrefix_NoHint
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_BlockCache,x
    cmp #11120
    bne SourceAttackPrefix_NoHint
    lda.l SourceVisual_BlockCache+2,x
    cmp #2
    bne SourceAttackPrefix_NoHint
    lda.l SourceVisual_BlockCache+4,x
    ora.l SVActor_HeldBlocks,x
    ora.l SVActor_OldBlocks,x
    and #255
    bne SourceAttackPrefix_NoHint
    sec
    rts
SourceAttackPrefix_NoHint:
.a16
.i16
    clc
    rts
SourceAttackPrefix_Ids:
    .dw 11120,6005,4493,14972,13713,12783,11465,15711,6374,203
SourceAttackPrefix_End:
.assert SourceAttackPrefix_End <= $05C200, "bounded prefix hint exceeds gap"
