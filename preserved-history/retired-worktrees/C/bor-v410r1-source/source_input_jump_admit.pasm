; Admit only pending grounded A edges at the original main input poll.
; This is before simulation/composition, never a mid-scene or NMI service.
; Existing PlayerFields owns edge priority, jump state and field-clock catchup.
; No new RAM, source input writes, media service or publication is introduced.
SourceInputJump_PollFinish:
.a16
.i16
    phx
    phy
    phb
    phd
    lda.l Game_CampaignId
    and #255
    cmp #3
    beq SourceInputJump_Scope0
    brl SourceInputJump_Done
SourceInputJump_Scope0:
.a16
.i16
    lda.l Game_State
    cmp #0
    beq SourceInputJump_Scope1
    brl SourceInputJump_Done
SourceInputJump_Scope1:
.a16
.i16
    lda.l $7E46DE
    cmp #0
    beq SourceInputJump_Scope2
    brl SourceInputJump_Done
SourceInputJump_Scope2:
.a16
.i16
    lda.l $7E175E
    cmp #2
    beq SourceInputJump_Scope3
    brl SourceInputJump_Done
SourceInputJump_Scope3:
.a16
.i16
    lda.l $7E1760
    cmp #1
    beq SourceInputJump_Scope4
    brl SourceInputJump_Done
SourceInputJump_Scope4:
.a16
.i16
    lda.l $7E46DC
    cmp #1
    beq SourceInputJump_Scope5
    brl SourceInputJump_Done
SourceInputJump_Scope5:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #6752
    beq SourceInputJump_Scope6
    brl SourceInputJump_Done
SourceInputJump_Scope6:
.a16
.i16
    sep #$20
.a8
    lda #0
    pha
    plb
    rep #$30
.a16
.i16
    lda #$0A00
    tcd
    jsl SourceInputJump_Player
    lda.l G13_TwoPlayerEnabled
    and #255
    beq SourceInputJump_Done
    lda #$0A85
    tcd
    jsl G13_Player2_ContextEnter
    jsl SourceInputJump_Player
    jsl G13_Player2_ContextExit
SourceInputJump_Done:
.a16
.i16
    rep #$30
    pld
    plb
    ply
    plx
    lda #0
    sta.l SourceVisual_LatchedInput
    sta.l SourceVisual_LatchedInput2
    pla
    plp
    rtl
SourceInputJump_Player:
.a16
.i16
    lda.l Input_trigger
    and #$0080
    beq SourceInputJump_PlayerDone
    tdc
    sec
    sbc #$0A00
    tax
    lda.l SourceVisual_Sa1OwnerPolicy,x
    and #255
    cmp #2
    bne SourceInputJump_PlayerDone
    lda.l $7E5550,x ; exact S6Bridge_Exists row
    and #255
    beq SourceInputJump_PlayerDone
    lda CHAR_HP
    and #255
    beq SourceInputJump_PlayerDone
    lda CHAR_INPUT_DRIVEN
    and #255
    cmp #1
    bne SourceInputJump_PlayerDone
    lda CHAR_SELECTED
    and #255
    cmp #3
    bcs SourceInputJump_PlayerDone
    sep #$20
.a8
    jsl SourceVisual_PlayerFields
    rep #$30
.a16
.i16
SourceInputJump_PlayerDone:
.a16
.i16
    rtl
SourceInputJump_End:
