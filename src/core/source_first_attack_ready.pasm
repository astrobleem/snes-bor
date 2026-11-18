; Prefer an already completed exact authored first attack picture only on
; P2 first entering an accepted unarmed attack. Existing lookup, allocation,
; physical readiness, pins and publication checks remain authoritative.
SourceFirstAttack_Prefer:
.a16
.i16
    php
    rep #$30
    pha
    lda.l SourceVisual_Key
    cmp #534
    beq SourceFirstAttack_G1
    brl SourceFirstAttack_Done
SourceFirstAttack_G1:
.a16
.i16
    tdc
    cmp #$0A85
    beq SourceFirstAttack_P2
    brl SourceFirstAttack_Done
SourceFirstAttack_P2:
.a16
.i16
    lda.l SourceVisual_Key+2
    cmp #1
    beq SourceFirstAttack_G2
    brl SourceFirstAttack_Done
SourceFirstAttack_G2:
.a16
.i16
    lda.l Game_CampaignId
    and #255
    cmp #3
    beq SourceFirstAttack_G3
    brl SourceFirstAttack_Done
SourceFirstAttack_G3:
.a16
.i16
    lda.l Game_State
    cmp #0
    beq SourceFirstAttack_G4
    brl SourceFirstAttack_Done
SourceFirstAttack_G4:
.a16
.i16
    lda.l Game_StageIndex
    cmp #0
    beq SourceFirstAttack_G5
    brl SourceFirstAttack_Done
SourceFirstAttack_G5:
.a16
.i16
    lda.l SourceVisual_State+32+30
    and #255
    cmp #2
    bcc SourceFirstAttack_G6
    brl SourceFirstAttack_Done
SourceFirstAttack_G6:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourceFirstAttack_G7
    brl SourceFirstAttack_Done
SourceFirstAttack_G7:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage
    cmp #0
    beq SourceFirstAttack_G8
    brl SourceFirstAttack_Done
SourceFirstAttack_G8:
.a16
.i16
    lda.l SVActor_Data+SVActor_Roster
    cmp #22
    beq SourceFirstAttack_G9
    brl SourceFirstAttack_Done
SourceFirstAttack_G9:
.a16
.i16
    lda.l SVActor_Data+1
    and #255
    cmp #2
    bcc SourceFirstAttack_G10
    brl SourceFirstAttack_Done
SourceFirstAttack_G10:
.a16
.i16
    lda.l SVActor_Data+3
    and #255
    cmp #0
    beq SourceFirstAttack_G11
    brl SourceFirstAttack_Done
SourceFirstAttack_G11:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    cmp #1
    beq SourceFirstAttack_G12
    brl SourceFirstAttack_Done
SourceFirstAttack_G12:
.a16
.i16
    lda.l SourceVisual_CompletedStage
    cmp #0
    beq SourceFirstAttack_G13
    brl SourceFirstAttack_Done
SourceFirstAttack_G13:
.a16
.i16
    lda.l SourceVisual_CompletedRoster
    cmp #22
    beq SourceFirstAttack_G14
    brl SourceFirstAttack_Done
SourceFirstAttack_G14:
.a16
.i16
    lda.l SourceVisual_CompletedEntry
    cmp #534
    beq SourceFirstAttack_G15
    brl SourceFirstAttack_Done
SourceFirstAttack_G15:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+2
    cmp #0
    beq SourceFirstAttack_G16
    brl SourceFirstAttack_Done
SourceFirstAttack_G16:
.a16
.i16
    lda.l SourceVisual_State+6
    cmp #2
    beq SourceFirstAttack_G17
    brl SourceFirstAttack_Done
SourceFirstAttack_G17:
.a16
.i16
    lda.l SourceVisual_State+28
    and #255
    cmp #1
    beq SourceFirstAttack_G18
    brl SourceFirstAttack_Done
SourceFirstAttack_G18:
.a16
.i16
    lda.l SourceVisual_State+29
    cmp #534
    beq SourceFirstAttack_G19
    brl SourceFirstAttack_Done
SourceFirstAttack_G19:
.a16
.i16
    lda.l SourceVisual_State
    cmp.l SourceVisual_CompletedLease
    beq SourceFirstAttack_SameLease
    brl SourceFirstAttack_Done
SourceFirstAttack_SameLease:
.a16
.i16
    lda #1
    jsl SourceWarm_ReadAttack
    bcs SourceFirstAttack_Accepted
    brl SourceFirstAttack_Done
SourceFirstAttack_Accepted:
.a16
.i16
    lda.l SourceWarm_Frame
    cmp #1
    beq SourceFirstAttack_G20
    brl SourceFirstAttack_Done
SourceFirstAttack_G20:
.a16
.i16
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_Key+2
    rep #$30
.a16
.i16
SourceFirstAttack_Changed:
SourceFirstAttack_Done:
.a16
.i16
    pla
    plp
    jml SourceVisual_PreferSharedFirstIdle
SourceFirstAttack_End:
