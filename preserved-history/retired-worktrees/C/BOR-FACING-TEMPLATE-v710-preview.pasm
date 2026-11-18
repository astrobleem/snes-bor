
SourceFacing_Meta0:
.a16
.i16
    lda.l $437A9C
    and #1
    bne SourceFacing_Match0
    lda.l $7E0A00+CHAR_FACING_LEFT
    and #255
    cmp #2
    bcs SourceFacing_No0
    cmp.l SOURCE_PACKET_ACTIVE_META+18
    beq SourceFacing_Yes0
    bra SourceFacing_No0
SourceFacing_Match0:
.a16
.i16
    lda.l $7E0A00+CHAR_FACING_LEFT
    and #255
    cmp #2
    bcs SourceFacing_No0
    cmp.l SourceAttackTemplate_Base+20
    beq SourceFacing_Yes0
SourceFacing_No0:
.a16
.i16
    lda #1
    sec
    rtl
SourceFacing_Yes0:
.a16
.i16
    lda #0
    sec
    rtl

SourceFacing_Meta1:
.a16
.i16
    lda.l $437A9C
    and #2
    bne SourceFacing_Match1
    lda.l $7E0A85+CHAR_FACING_LEFT
    and #255
    cmp #2
    bcs SourceFacing_No1
    cmp.l SOURCE_PACKET_ACTIVE_META+50
    beq SourceFacing_Yes1
    bra SourceFacing_No1
SourceFacing_Match1:
.a16
.i16
    lda.l $7E0A85+CHAR_FACING_LEFT
    and #255
    cmp #2
    bcs SourceFacing_No1
    cmp.l SourceAttackTemplate_Base+148
    beq SourceFacing_Yes1
SourceFacing_No1:
.a16
.i16
    lda #1
    sec
    rtl
SourceFacing_Yes1:
.a16
.i16
    lda #0
    sec
    rtl

; Only static immutable root templates are turned. Current hardware, normal
; packets, tile/palette identities, pins, gameplay and input are untouched.
; Full capture/seal/generation checks run again after this foreground adapter.
SourceFacing_AdaptStatic:
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
    lda.l SourceAttackOwned_State
    ora.l SourceAttackOwned_Hold
    ora.l SourceAttackOwned_Busy
    ora.l SourcePacket_CopyBusy
    ora.l Game_StageIndex
    ora.l Screen_PosX
    beq SourceFacing_Free
    brl SourceFacing_Done
SourceFacing_Free:
.a16
.i16
    lda.l SourceStandby_FaceMask
    and #1
    bne SourceFacing_Adapt0Guard0
    brl SourceFacing_SlotDone0
SourceFacing_Adapt0Guard0:
.a16
.i16
    lda.l SourceAttackTemplate_Base+0
    cmp #$A770
    beq SourceFacing_Adapt0Guard1
    brl SourceFacing_SlotDone0
SourceFacing_Adapt0Guard1:
.a16
.i16
    lda.l $4119E6
    and #255
    cmp #9
    beq SourceFacing_Adapt0Guard2
    brl SourceFacing_SlotDone0
SourceFacing_Adapt0Guard2:
.a16
.i16
    lda.l $7E0A00+CHAR_THROW_ZPOS
    beq SourceFacing_Adapt0Guard3
    brl SourceFacing_SlotDone0
SourceFacing_Adapt0Guard3:
.a16
.i16
    lda.l $7E0A00+CHAR_SELECTED
    and #255
    cmp #3
    bcc SourceFacing_Adapt0Guard4
    brl SourceFacing_SlotDone0
SourceFacing_Adapt0Guard4:
.a16
.i16
    lda.l SourceAttackTemplate_Base+14
    cmp #128
    beq SourceFacing_Adapt0Guard5
    brl SourceFacing_SlotDone0
SourceFacing_Adapt0Guard5:
.a16
.i16
    lda.l SourceAttackTemplate_Base+16
    cmp #150
    beq SourceFacing_Adapt0Guard6
    brl SourceFacing_SlotDone0
SourceFacing_Adapt0Guard6:
.a16
.i16
    lda.l SourceAttackTemplate_Base+18
    cmp #0
    beq SourceFacing_Adapt0Guard7
    brl SourceFacing_SlotDone0
SourceFacing_Adapt0Guard7:
.a16
.i16
    lda.l $7E0A00+CHAR_FACING_LEFT
    and #255
    cmp #2
    bcc SourceFacing_Adapt0Guard8
    brl SourceFacing_SlotDone0
SourceFacing_Adapt0Guard8:
.a16
.i16
    sta.l $437BB0
    cmp.l SourceAttackTemplate_Base+20
    bne SourceFacing_Adapt0Guard9
    brl SourceFacing_SlotDone0
SourceFacing_Adapt0Guard9:
.a16
.i16
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l $437BB4
    lda #1
    sta.l SourceAttackOwned_Busy
    sta.l SourcePacket_CopyBusy
    lda #0
    sta.l SourceAttackTemplate_Base+0
    ldx #0
SourceFacing_Piece0:
.a16
.i16
    lda.l $437BB0
    beq SourceFacing_Unflipped0
    lda.l SourceStandby_PiecesLong+4,x
    bra SourceFacing_Offset0
SourceFacing_Unflipped0:
.a16
.i16
    lda.l SourceStandby_PiecesLong,x
SourceFacing_Offset0:
.a16
.i16
    clc
    adc #128
    and #511
    sta.l $437BB2
    txa
    lsr a
    lsr a
    tax
    sep #$20
.a8
    lda.l $437BB2
    sta.l SourceAttackTemplate_Base+32,x
    lda.l SourceAttackTemplate_Base+35,x
    and #$BF
    ora.l $437BB4
    sta.l SourceAttackTemplate_Base+35,x
    rep #$30
.a16
.i16
    txa
    lsr a
    lsr a
    tax
    lda.l SourceAttackTemplate_Base+72,x
    and #2
    sta.l $437BB6
    lda.l $437BB2
    and #256
    xba
    ora.l $437BB6
    sep #$20
.a8
    sta.l SourceAttackTemplate_Base+72,x
    rep #$30
.a16
.i16
    txa
    asl a
    asl a
    asl a
    asl a
    clc
    adc #16
    tax
    cpx #160
    bcs SourceFacing_PiecesDone0
    brl SourceFacing_Piece0
SourceFacing_PiecesDone0:
.a16
.i16
    lda.l $437BB0
    sta.l SourceAttackTemplate_Base+20
    lda #$A770
    sta.l SourceAttackTemplate_Base+0
    lda #0
    sta.l SourceAttackOwned_Busy
    sta.l SourcePacket_CopyBusy
SourceFacing_SlotDone0:
.a16
.i16
    lda.l SourceStandby_FaceMask
    and #2
    bne SourceFacing_Adapt1Guard0
    brl SourceFacing_SlotDone1
SourceFacing_Adapt1Guard0:
.a16
.i16
    lda.l SourceAttackTemplate_Base+128
    cmp #$A770
    beq SourceFacing_Adapt1Guard1
    brl SourceFacing_SlotDone1
SourceFacing_Adapt1Guard1:
.a16
.i16
    lda.l $411AE6
    and #255
    cmp #9
    beq SourceFacing_Adapt1Guard2
    brl SourceFacing_SlotDone1
SourceFacing_Adapt1Guard2:
.a16
.i16
    lda.l $7E0A85+CHAR_THROW_ZPOS
    beq SourceFacing_Adapt1Guard3
    brl SourceFacing_SlotDone1
SourceFacing_Adapt1Guard3:
.a16
.i16
    lda.l $7E0A85+CHAR_SELECTED
    and #255
    cmp #3
    bcc SourceFacing_Adapt1Guard4
    brl SourceFacing_SlotDone1
SourceFacing_Adapt1Guard4:
.a16
.i16
    lda.l SourceAttackTemplate_Base+142
    cmp #128
    beq SourceFacing_Adapt1Guard5
    brl SourceFacing_SlotDone1
SourceFacing_Adapt1Guard5:
.a16
.i16
    lda.l SourceAttackTemplate_Base+144
    cmp #150
    beq SourceFacing_Adapt1Guard6
    brl SourceFacing_SlotDone1
SourceFacing_Adapt1Guard6:
.a16
.i16
    lda.l SourceAttackTemplate_Base+146
    cmp #0
    beq SourceFacing_Adapt1Guard7
    brl SourceFacing_SlotDone1
SourceFacing_Adapt1Guard7:
.a16
.i16
    lda.l $7E0A85+CHAR_FACING_LEFT
    and #255
    cmp #2
    bcc SourceFacing_Adapt1Guard8
    brl SourceFacing_SlotDone1
SourceFacing_Adapt1Guard8:
.a16
.i16
    sta.l $437BB0
    cmp.l SourceAttackTemplate_Base+148
    bne SourceFacing_Adapt1Guard9
    brl SourceFacing_SlotDone1
SourceFacing_Adapt1Guard9:
.a16
.i16
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l $437BB4
    lda #1
    sta.l SourceAttackOwned_Busy
    sta.l SourcePacket_CopyBusy
    lda #0
    sta.l SourceAttackTemplate_Base+128
    ldx #0
SourceFacing_Piece1:
.a16
.i16
    lda.l $437BB0
    beq SourceFacing_Unflipped1
    lda.l SourceStandby_PiecesLong+4,x
    bra SourceFacing_Offset1
SourceFacing_Unflipped1:
.a16
.i16
    lda.l SourceStandby_PiecesLong,x
SourceFacing_Offset1:
.a16
.i16
    clc
    adc #128
    and #511
    sta.l $437BB2
    txa
    lsr a
    lsr a
    tax
    sep #$20
.a8
    lda.l $437BB2
    sta.l SourceAttackTemplate_Base+160,x
    lda.l SourceAttackTemplate_Base+163,x
    and #$BF
    ora.l $437BB4
    sta.l SourceAttackTemplate_Base+163,x
    rep #$30
.a16
.i16
    txa
    lsr a
    lsr a
    tax
    lda.l SourceAttackTemplate_Base+200,x
    and #2
    sta.l $437BB6
    lda.l $437BB2
    and #256
    xba
    ora.l $437BB6
    sep #$20
.a8
    sta.l SourceAttackTemplate_Base+200,x
    rep #$30
.a16
.i16
    txa
    asl a
    asl a
    asl a
    asl a
    clc
    adc #16
    tax
    cpx #160
    bcs SourceFacing_PiecesDone1
    brl SourceFacing_Piece1
SourceFacing_PiecesDone1:
.a16
.i16
    lda.l $437BB0
    sta.l SourceAttackTemplate_Base+148
    lda #$A770
    sta.l SourceAttackTemplate_Base+128
    lda #0
    sta.l SourceAttackOwned_Busy
    sta.l SourcePacket_CopyBusy
SourceFacing_SlotDone1:
.a16
.i16
SourceFacing_Done:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    rtl
SourceFacing_CaptureLive:
.a16
.i16
    jsl SourceAttackLease_Capture
    php
    rep #$30
    pha
    phx
    lda.l SourceVisual_ActorSlot
    cmp #2
    bcs SourceFacing_CaptureDone
    tax
    lda #$FFFE
    cpx #0
    beq SourceFacing_ClearMarker
    lda #$FFFD
SourceFacing_ClearMarker:
.a16
.i16
    and.l SourceStandby_FaceMask
    sta.l SourceStandby_FaceMask
SourceFacing_CaptureDone:
.a16
.i16
    plx
    pla
    plp
    rtl
