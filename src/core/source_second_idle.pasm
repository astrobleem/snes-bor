; Preserve all established helper addresses; private latch occupies unused reservation header.
SourceSecond_Consumed = $436004
SourceSecond_Dispatch:
.a16
.i16
    jsl SourcePacket_ForegroundPrepare
    php
    rep #$30
    pha
    lda.l SourceReserve_Valid
    cmp #$1D1F
    beq SourceSecond_DispatchConsumed
    lda #0
    sta.l SourceSecond_Consumed
SourceSecond_DispatchConsumed:
    pla
    plp
    jsl SourceSecond_Wait
    rtl
SourceSecond_Wait:
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
    lda.l SourceSecond_Consumed
    beq SourceSecond_CheckValid
    brl SourceSecond_Done
SourceSecond_CheckValid:
.a16
.i16
    lda.l SourceReserve_Valid
    cmp #$1D1F
    beq SourceSecond_NotConsumed
    brl SourceSecond_Done
SourceSecond_NotConsumed:
.a16
.i16
lda.l Game_CampaignId
and #255
cmp #3
    beq SourceSecond_G20
    brl SourceSecond_Done
SourceSecond_G20:
.a16
.i16
lda.l Game_State
cmp #0
    beq SourceSecond_G28
    brl SourceSecond_Done
SourceSecond_G28:
.a16
.i16
lda.l Game_StageIndex
cmp #0
    beq SourceSecond_G35
    brl SourceSecond_Done
SourceSecond_G35:
.a16
.i16
lda.l $7E175E
cmp #2
    beq SourceSecond_G42
    brl SourceSecond_Done
SourceSecond_G42:
.a16
.i16
lda.l $7E1760
cmp #1
    beq SourceSecond_G49
    brl SourceSecond_Done
SourceSecond_G49:
.a16
.i16
lda.l $7E46DC
cmp #1
    beq SourceSecond_G56
    brl SourceSecond_Done
SourceSecond_G56:
.a16
.i16
lda.l $7E46DE
cmp #0
    beq SourceSecond_G63
    brl SourceSecond_Done
SourceSecond_G63:
.a16
.i16
lda.l SourceInput_Magic
cmp #6752
    beq SourceSecond_G70
    brl SourceSecond_Done
SourceSecond_G70:
.a16
.i16
lda.l SourceVisual_CompletedMagic
cmp #49229
    beq SourceSecond_G77
    brl SourceSecond_Done
SourceSecond_G77:
.a16
.i16
lda.l SVActor_Magic
cmp #44057
    beq SourceSecond_G84
    brl SourceSecond_Done
SourceSecond_G84:
.a16
.i16
SourceSecond_UnusedChecked:
.a16
.i16
lda.l Stage_Mirror
and #255
cmp #0
    beq SourceSecond_G91
    brl SourceSecond_Done
SourceSecond_G91:
.a16
.i16
lda.l Screen_PosX
cmp #0
    beq SourceSecond_G99
    brl SourceSecond_Done
SourceSecond_G99:
.a16
.i16
    lda.l SourcePacket_ActiveCamera
    cmp #0
    beq SourceSecond_Depth0
    brl SourceSecond_Done
SourceSecond_Depth0:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+6
    cmp #150
    beq SourceSecond_Depth1
    brl SourceSecond_Done
SourceSecond_Depth1:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+38
    cmp #150
    beq SourceSecond_Depth2
    brl SourceSecond_Done
SourceSecond_Depth2:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+18
    cmp #0
    beq SourceSecond_Depth3
    brl SourceSecond_Done
SourceSecond_Depth3:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+50
    cmp #0
    beq SourceSecond_Depth4
    brl SourceSecond_Done
SourceSecond_Depth4:
.a16
.i16
    lda.l $434E36
    cmp #188
    beq SourceSecond_Depth5
    brl SourceSecond_Done
SourceSecond_Depth5:
.a16
.i16
    lda.l $434E5A
    cmp #188
    beq SourceSecond_Depth6
    brl SourceSecond_Done
SourceSecond_Depth6:
.a16
.i16
lda.l SourcePacket_ActiveValid
cmp #1
    beq SourceSecond_G106
    brl SourceSecond_Done
SourceSecond_G106:
.a16
.i16
lda.l SourcePacket_CopyBusy
cmp #0
    beq SourceSecond_G113
    brl SourceSecond_Done
SourceSecond_G113:
.a16
.i16
lda.l SourcePacket_RefreshAccepted
cmp #1
    beq SourceSecond_G120
    brl SourceSecond_Done
SourceSecond_G120:
.a16
.i16
lda.l $434E7E
cmp #19792
    beq SourceSecond_G127
    brl SourceSecond_Done
SourceSecond_G127:
.a16
.i16
lda.l $434E7C
and #1
cmp #0
    beq SourceSecond_G134
    brl SourceSecond_Done
SourceSecond_G134:
.a16
.i16
lda.l $434E2C
cmp #0
    beq SourceSecond_G142
    brl SourceSecond_Done
SourceSecond_G142:
.a16
.i16
lda.l $434E7C
    sta.l SourceReserve_Seq
lda.l SOURCE_PACKET_ACTIVE_META
cmp #0
    beq SourceSecond_G151
    brl SourceSecond_Done
SourceSecond_G151:
.a16
.i16
    lda #0
    sta.l $436006
    lda.l SOURCE_PACKET_ACTIVE_META+2
    cmp #40
    beq SourceSecond_TwentyPieces
    cmp #48
    beq SourceSecond_TwentyFourPieces
    brl SourceSecond_Done
SourceSecond_TwentyPieces:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+32
    cmp #40
    bne SourceSecond_BadRanges
    lda.l SOURCE_PACKET_ACTIVE_META+34
    cmp #80
    beq SourceSecond_G172
SourceSecond_BadRanges:
.a16
.i16
    brl SourceSecond_Done
SourceSecond_TwentyFourPieces:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+32
    cmp #48
    bne SourceSecond_BadRanges
    lda.l SOURCE_PACKET_ACTIVE_META+34
    cmp #96
    bne SourceSecond_BadRanges
    lda #1
    sta.l $436006
SourceSecond_G172:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+16
cmp #1
    beq SourceSecond_G179
    brl SourceSecond_Done
SourceSecond_G179:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+48
cmp #1
    beq SourceSecond_G186
    brl SourceSecond_Done
SourceSecond_G186:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+10
cmp #0
    beq SourceSecond_G193
    brl SourceSecond_Done
SourceSecond_G193:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+42
cmp #0
    beq SourceSecond_G200
    brl SourceSecond_Done
SourceSecond_G200:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+8
cmp #22
    beq SourceSecond_G207
    brl SourceSecond_Done
SourceSecond_G207:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+40
cmp #22
    beq SourceSecond_G214
    brl SourceSecond_Done
SourceSecond_G214:
.a16
.i16
lda.l $434E9C
cmp #0
    beq SourceSecond_G221
    brl SourceSecond_Done
SourceSecond_G221:
.a16
.i16
lda.l $434E9E
cmp #133
    beq SourceSecond_G228
    brl SourceSecond_Done
SourceSecond_G228:
.a16
.i16
lda.l $434E38
cmp #0
    beq SourceSecond_G235
    brl SourceSecond_Done
SourceSecond_G235:
.a16
.i16
lda.l $434E3A
cmp #0
    beq SourceSecond_G242
    brl SourceSecond_Done
SourceSecond_G242:
.a16
.i16
lda.l $434E3C
cmp #9
    beq SourceSecond_G249
    brl SourceSecond_Done
SourceSecond_G249:
.a16
.i16
lda.l $434E40
cmp #1
    beq SourceSecond_G256
    brl SourceSecond_Done
SourceSecond_G256:
.a16
.i16
lda.l $434E42
cmp #0
    beq SourceSecond_G263
    brl SourceSecond_Done
SourceSecond_G263:
.a16
.i16
lda.l $434E4A
and #255
cmp #2
    beq SourceSecond_G270
    brl SourceSecond_Done
SourceSecond_G270:
.a16
.i16
lda.l $434E50
and #255
cmp #0
    beq SourceSecond_G278
    brl SourceSecond_Done
SourceSecond_G278:
.a16
.i16
lda.l $7E0A00+CHAR_HP
and #255
cmp #0
    bne SourceSecond_G286
    brl SourceSecond_Done
SourceSecond_G286:
.a16
.i16
lda.l $7E0A00+CHAR_INPUT_DRIVEN
and #255
cmp #1
    beq SourceSecond_G294
    brl SourceSecond_Done
SourceSecond_G294:
.a16
.i16
lda.l $7E0A00+CHAR_ROSTER_INDEX
and #255
cmp #22
    beq SourceSecond_G302
    brl SourceSecond_Done
SourceSecond_G302:
.a16
.i16
lda.l $7E0A00+CHAR_MAP_INDEX
and #255
cmp #0
    beq SourceSecond_G310
    brl SourceSecond_Done
SourceSecond_G310:
.a16
.i16
lda.l $7E0A00+CHAR_SELECTED
and #255
cmp #3
    bcc SourceSecond_G318
    brl SourceSecond_Done
SourceSecond_G318:
.a16
.i16
lda.l $434E5C
cmp #0
    beq SourceSecond_G326
    brl SourceSecond_Done
SourceSecond_G326:
.a16
.i16
lda.l $434E5E
cmp #0
    beq SourceSecond_G333
    brl SourceSecond_Done
SourceSecond_G333:
.a16
.i16
lda.l $434E60
cmp #9
    beq SourceSecond_G340
    brl SourceSecond_Done
SourceSecond_G340:
.a16
.i16
lda.l $434E64
cmp #1
    beq SourceSecond_G347
    brl SourceSecond_Done
SourceSecond_G347:
.a16
.i16
lda.l $434E66
cmp #0
    beq SourceSecond_G354
    brl SourceSecond_Done
SourceSecond_G354:
.a16
.i16
lda.l $434E6E
and #255
cmp #2
    beq SourceSecond_G361
    brl SourceSecond_Done
SourceSecond_G361:
.a16
.i16
lda.l $434E74
and #255
cmp #0
    beq SourceSecond_G369
    brl SourceSecond_Done
SourceSecond_G369:
.a16
.i16
lda.l $7E0A85+CHAR_HP
and #255
cmp #0
    bne SourceSecond_G377
    brl SourceSecond_Done
SourceSecond_G377:
.a16
.i16
lda.l $7E0A85+CHAR_INPUT_DRIVEN
and #255
cmp #1
    beq SourceSecond_G385
    brl SourceSecond_Done
SourceSecond_G385:
.a16
.i16
lda.l $7E0A85+CHAR_ROSTER_INDEX
and #255
cmp #22
    beq SourceSecond_G393
    brl SourceSecond_Done
SourceSecond_G393:
.a16
.i16
lda.l $7E0A85+CHAR_MAP_INDEX
and #255
cmp #0
    beq SourceSecond_G401
    brl SourceSecond_Done
SourceSecond_G401:
.a16
.i16
lda.l $7E0A85+CHAR_SELECTED
and #255
cmp #3
    bcc SourceSecond_G409
    brl SourceSecond_Done
SourceSecond_G409:
.a16
.i16
lda.l SourceVisual_BlockCache+0
cmp #8842
    beq SourceSecond_G417
    brl SourceSecond_Done
SourceSecond_G417:
.a16
.i16
lda.l SourceVisual_BlockCache+2
cmp #2
    beq SourceSecond_G424
    brl SourceSecond_Done
SourceSecond_G424:
.a16
.i16
lda.l SourceVisual_BlockCache+8
cmp #2633
    beq SourceSecond_G431
    brl SourceSecond_Done
SourceSecond_G431:
.a16
.i16
lda.l SourceVisual_BlockCache+10
cmp #2
    beq SourceSecond_G438
    brl SourceSecond_Done
SourceSecond_G438:
.a16
.i16
lda.l SourceVisual_BlockCache+16
cmp #5886
    beq SourceSecond_G445
    brl SourceSecond_Done
SourceSecond_G445:
.a16
.i16
lda.l SourceVisual_BlockCache+18
cmp #2
    beq SourceSecond_G452
    brl SourceSecond_Done
SourceSecond_G452:
.a16
.i16
lda.l SourceVisual_BlockCache+24
cmp #13304
    beq SourceSecond_G459
    brl SourceSecond_Done
SourceSecond_G459:
.a16
.i16
lda.l SourceVisual_BlockCache+26
cmp #2
    beq SourceSecond_G466
    brl SourceSecond_Done
SourceSecond_G466:
.a16
.i16
lda.l SourceVisual_BlockCache+32
cmp #1592
    beq SourceSecond_G473
    brl SourceSecond_Done
SourceSecond_G473:
.a16
.i16
lda.l SourceVisual_BlockCache+34
cmp #2
    beq SourceSecond_G480
    brl SourceSecond_Done
SourceSecond_G480:
.a16
.i16
lda.l SourceVisual_BlockCache+40
cmp #12228
    beq SourceSecond_G487
    brl SourceSecond_Done
SourceSecond_G487:
.a16
.i16
lda.l SourceVisual_BlockCache+42
cmp #2
    beq SourceSecond_G494
    brl SourceSecond_Done
SourceSecond_G494:
.a16
.i16
lda.l SourceVisual_BlockCache+48
cmp #7241
    beq SourceSecond_G501
    brl SourceSecond_Done
SourceSecond_G501:
.a16
.i16
lda.l SourceVisual_BlockCache+50
cmp #2
    beq SourceSecond_G508
    brl SourceSecond_Done
SourceSecond_G508:
.a16
.i16
lda.l SourceVisual_BlockCache+56
cmp #559
    beq SourceSecond_G515
    brl SourceSecond_Done
SourceSecond_G515:
.a16
.i16
lda.l SourceVisual_BlockCache+58
cmp #2
    beq SourceSecond_G522
    brl SourceSecond_Done
SourceSecond_G522:
.a16
.i16
lda.l SourceVisual_BlockCache+64
cmp #3618
    beq SourceSecond_G529
    brl SourceSecond_Done
SourceSecond_G529:
.a16
.i16
lda.l SourceVisual_BlockCache+66
cmp #2
    beq SourceSecond_G536
    brl SourceSecond_Done
SourceSecond_G536:
.a16
.i16
lda.l SourceVisual_BlockCache+72
cmp #11343
    beq SourceSecond_G543
    brl SourceSecond_Done
SourceSecond_G543:
.a16
.i16
lda.l SourceVisual_BlockCache+74
cmp #2
    beq SourceSecond_G550
    brl SourceSecond_Done
SourceSecond_G550:
.a16
.i16
lda.l SourceVisual_PaletteCache
cmp #361
    beq SourceSecond_G557
    brl SourceSecond_Done
SourceSecond_G557:
.a16
.i16
lda.l SourceVisual_PaletteCache+3
and #255
cmp #1
    beq SourceSecond_G564
    brl SourceSecond_Done
SourceSecond_G564:
.a16
.i16
lda.l DmaQueue+4
    and #$40
    beq SourceSecond_Q0
lda.l DmaQueue+7
and #255
cmp #67
    bne SourceSecond_G575
    brl SourceSecond_Done
SourceSecond_G575:
.a16
.i16
lda.l DmaQueue+4
and #31
cmp #1
    bne SourceSecond_G583
    brl SourceSecond_Done
SourceSecond_G583:
.a16
.i16
SourceSecond_Q0:
.a16
.i16
lda.l DmaQueue+12
    and #$40
    beq SourceSecond_Q1
lda.l DmaQueue+15
and #255
cmp #67
    bne SourceSecond_G597
    brl SourceSecond_Done
SourceSecond_G597:
.a16
.i16
lda.l DmaQueue+12
and #31
cmp #1
    bne SourceSecond_G605
    brl SourceSecond_Done
SourceSecond_G605:
.a16
.i16
SourceSecond_Q1:
.a16
.i16
lda.l DmaQueue+20
    and #$40
    beq SourceSecond_Q2
lda.l DmaQueue+23
and #255
cmp #67
    bne SourceSecond_G619
    brl SourceSecond_Done
SourceSecond_G619:
.a16
.i16
lda.l DmaQueue+20
and #31
cmp #1
    bne SourceSecond_G627
    brl SourceSecond_Done
SourceSecond_G627:
.a16
.i16
SourceSecond_Q2:
.a16
.i16
lda.l DmaQueue+28
    and #$40
    beq SourceSecond_Q3
lda.l DmaQueue+31
and #255
cmp #67
    bne SourceSecond_G641
    brl SourceSecond_Done
SourceSecond_G641:
.a16
.i16
lda.l DmaQueue+28
and #31
cmp #1
    bne SourceSecond_G649
    brl SourceSecond_Done
SourceSecond_G649:
.a16
.i16
SourceSecond_Q3:
.a16
.i16
lda.l DmaQueue+36
    and #$40
    beq SourceSecond_Q4
lda.l DmaQueue+39
and #255
cmp #67
    bne SourceSecond_G663
    brl SourceSecond_Done
SourceSecond_G663:
.a16
.i16
lda.l DmaQueue+36
and #31
cmp #1
    bne SourceSecond_G671
    brl SourceSecond_Done
SourceSecond_G671:
.a16
.i16
SourceSecond_Q4:
.a16
.i16
lda.l DmaQueue+44
    and #$40
    beq SourceSecond_Q5
lda.l DmaQueue+47
and #255
cmp #67
    bne SourceSecond_G685
    brl SourceSecond_Done
SourceSecond_G685:
.a16
.i16
lda.l DmaQueue+44
and #31
cmp #1
    bne SourceSecond_G693
    brl SourceSecond_Done
SourceSecond_G693:
.a16
.i16
SourceSecond_Q5:
.a16
.i16
lda.l DmaQueue+52
    and #$40
    beq SourceSecond_Q6
lda.l DmaQueue+55
and #255
cmp #67
    bne SourceSecond_G707
    brl SourceSecond_Done
SourceSecond_G707:
.a16
.i16
lda.l DmaQueue+52
and #31
cmp #1
    bne SourceSecond_G715
    brl SourceSecond_Done
SourceSecond_G715:
.a16
.i16
SourceSecond_Q6:
.a16
.i16
lda.l DmaQueue+60
    and #$40
    beq SourceSecond_Q7
lda.l DmaQueue+63
and #255
cmp #67
    bne SourceSecond_G729
    brl SourceSecond_Done
SourceSecond_G729:
.a16
.i16
lda.l DmaQueue+60
and #31
cmp #1
    bne SourceSecond_G737
    brl SourceSecond_Done
SourceSecond_G737:
.a16
.i16
SourceSecond_Q7:
.a16
.i16
    brl SourceSecond_TryPromote
SourceSecond_TryPromote:
.a16
.i16
lda.l SourceReserve_Valid
cmp #7455
    beq SourceSecond_G762
    brl SourceSecond_Done
SourceSecond_G762:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+12
cmp #278
    beq SourceSecond_G769
    brl SourceSecond_Done
SourceSecond_G769:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+44
cmp #278
    beq SourceSecond_G776
    brl SourceSecond_Done
SourceSecond_G776:
.a16
.i16
    lda.l SVActor_OldBlocks+0
    and #1
    beq SourceSecond_OldClear0
    brl SourceSecond_Done
SourceSecond_OldClear0:
.a16
.i16
    lda.l SVActor_OldBlocks+8
    and #1
    beq SourceSecond_OldClear132
    brl SourceSecond_Done
SourceSecond_OldClear132:
.a16
.i16
    lda.l SVActor_OldBlocks+16
    and #1
    beq SourceSecond_OldClear268
    brl SourceSecond_Done
SourceSecond_OldClear268:
.a16
.i16
    lda.l SVActor_OldBlocks+24
    and #1
    beq SourceSecond_OldClear405
    brl SourceSecond_Done
SourceSecond_OldClear405:
.a16
.i16
    lda.l SVActor_OldBlocks+32
    and #1
    beq SourceSecond_OldClear542
    brl SourceSecond_Done
SourceSecond_OldClear542:
.a16
.i16
    lda.l SVActor_OldBlocks+40
    and #1
    beq SourceSecond_OldClear679
    brl SourceSecond_Done
SourceSecond_OldClear679:
.a16
.i16
    lda.l SVActor_OldBlocks+48
    and #1
    beq SourceSecond_OldClear816
    brl SourceSecond_Done
SourceSecond_OldClear816:
.a16
.i16
    lda.l SVActor_OldBlocks+56
    and #1
    beq SourceSecond_OldClear953
    brl SourceSecond_Done
SourceSecond_OldClear953:
.a16
.i16
    lda.l SVActor_OldBlocks+64
    and #1
    beq SourceSecond_OldClear1090
    brl SourceSecond_Done
SourceSecond_OldClear1090:
.a16
.i16
    lda.l SVActor_OldBlocks+72
    and #1
    beq SourceSecond_OldClear1229
    brl SourceSecond_Done
SourceSecond_OldClear1229:
.a16
.i16
    lda.l SVActor_OldPalettes
    and #1
    beq SourceSecond_OldClear1368
    brl SourceSecond_Done
SourceSecond_OldClear1368:
.a16
.i16
SourceSecond_Promote:
.a16
.i16
    jsl SourceIdleFinalize_Begin
    nop
    nop
    nop
    lda #0
    sta.l SourcePacket_NmiPending
    sta.l SourcePacket_RefreshAccepted
    lda.l SVActor_HeldBlocks+0
    ora #1
    sta.l SVActor_HeldBlocks+0
    lda.l SVActor_HeldBlocks+8
    ora #1
    sta.l SVActor_HeldBlocks+8
    lda.l SVActor_HeldBlocks+16
    ora #1
    sta.l SVActor_HeldBlocks+16
    lda.l SVActor_HeldBlocks+24
    ora #1
    sta.l SVActor_HeldBlocks+24
    lda.l SVActor_HeldBlocks+32
    ora #1
    sta.l SVActor_HeldBlocks+32
    lda.l SVActor_HeldBlocks+40
    ora #1
    sta.l SVActor_HeldBlocks+40
    lda.l SVActor_HeldBlocks+48
    ora #1
    sta.l SVActor_HeldBlocks+48
    lda.l SVActor_HeldBlocks+56
    ora #1
    sta.l SVActor_HeldBlocks+56
    lda.l SVActor_HeldBlocks+64
    ora #1
    sta.l SVActor_HeldBlocks+64
    lda.l SVActor_HeldBlocks+72
    ora #1
    sta.l SVActor_HeldBlocks+72
    lda.l SVActor_HeldPalettes
    ora #1
    sta.l SVActor_HeldPalettes
    lda #65529
    sta.l SourceReserve_Signed+0
    sep #$20
.a8
    sta.l SourceReserve_Oam+0
    lda.l SourceReserve_Oam+3
    eor #$40
    sta.l SourceReserve_Oam+3
    rep #$30
.a16
    lda #65529
    sta.l SourceReserve_Signed+4
    sep #$20
.a8
    sta.l SourceReserve_Oam+4
    lda.l SourceReserve_Oam+7
    eor #$40
    sta.l SourceReserve_Oam+7
    rep #$30
.a16
    lda #1
    sta.l SourceReserve_Signed+8
    sep #$20
.a8
    sta.l SourceReserve_Oam+8
    lda.l SourceReserve_Oam+11
    eor #$40
    sta.l SourceReserve_Oam+11
    rep #$30
.a16
    lda #1
    sta.l SourceReserve_Signed+12
    sep #$20
.a8
    sta.l SourceReserve_Oam+12
    lda.l SourceReserve_Oam+15
    eor #$40
    sta.l SourceReserve_Oam+15
    rep #$30
.a16
    lda #9
    sta.l SourceReserve_Signed+16
    sep #$20
.a8
    sta.l SourceReserve_Oam+16
    lda.l SourceReserve_Oam+19
    eor #$40
    sta.l SourceReserve_Oam+19
    rep #$30
.a16
    lda #9
    sta.l SourceReserve_Signed+20
    sep #$20
.a8
    sta.l SourceReserve_Oam+20
    lda.l SourceReserve_Oam+23
    eor #$40
    sta.l SourceReserve_Oam+23
    rep #$30
.a16
    lda #17
    sta.l SourceReserve_Signed+24
    sep #$20
.a8
    sta.l SourceReserve_Oam+24
    lda.l SourceReserve_Oam+27
    eor #$40
    sta.l SourceReserve_Oam+27
    rep #$30
.a16
    lda #17
    sta.l SourceReserve_Signed+28
    sep #$20
.a8
    sta.l SourceReserve_Oam+28
    lda.l SourceReserve_Oam+31
    eor #$40
    sta.l SourceReserve_Oam+31
    rep #$30
.a16
    lda #25
    sta.l SourceReserve_Signed+32
    sep #$20
.a8
    sta.l SourceReserve_Oam+32
    lda.l SourceReserve_Oam+35
    eor #$40
    sta.l SourceReserve_Oam+35
    rep #$30
.a16
    lda #25
    sta.l SourceReserve_Signed+36
    sep #$20
.a8
    sta.l SourceReserve_Oam+36
    lda.l SourceReserve_Oam+39
    eor #$40
    sta.l SourceReserve_Oam+39
    rep #$30
.a16
    lda #57
    sta.l SourceReserve_Signed+40
    sep #$20
.a8
    sta.l SourceReserve_Oam+40
    lda.l SourceReserve_Oam+43
    eor #$40
    sta.l SourceReserve_Oam+43
    rep #$30
.a16
    lda #57
    sta.l SourceReserve_Signed+44
    sep #$20
.a8
    sta.l SourceReserve_Oam+44
    lda.l SourceReserve_Oam+47
    eor #$40
    sta.l SourceReserve_Oam+47
    rep #$30
.a16
    lda #65
    sta.l SourceReserve_Signed+48
    sep #$20
.a8
    sta.l SourceReserve_Oam+48
    lda.l SourceReserve_Oam+51
    eor #$40
    sta.l SourceReserve_Oam+51
    rep #$30
.a16
    lda #65
    sta.l SourceReserve_Signed+52
    sep #$20
.a8
    sta.l SourceReserve_Oam+52
    lda.l SourceReserve_Oam+55
    eor #$40
    sta.l SourceReserve_Oam+55
    rep #$30
.a16
    lda #73
    sta.l SourceReserve_Signed+56
    sep #$20
.a8
    sta.l SourceReserve_Oam+56
    lda.l SourceReserve_Oam+59
    eor #$40
    sta.l SourceReserve_Oam+59
    rep #$30
.a16
    lda #73
    sta.l SourceReserve_Signed+60
    sep #$20
.a8
    sta.l SourceReserve_Oam+60
    lda.l SourceReserve_Oam+63
    eor #$40
    sta.l SourceReserve_Oam+63
    rep #$30
.a16
    lda #81
    sta.l SourceReserve_Signed+64
    sep #$20
.a8
    sta.l SourceReserve_Oam+64
    lda.l SourceReserve_Oam+67
    eor #$40
    sta.l SourceReserve_Oam+67
    rep #$30
.a16
    lda #81
    sta.l SourceReserve_Signed+68
    sep #$20
.a8
    sta.l SourceReserve_Oam+68
    lda.l SourceReserve_Oam+71
    eor #$40
    sta.l SourceReserve_Oam+71
    rep #$30
.a16
    lda #89
    sta.l SourceReserve_Signed+72
    sep #$20
.a8
    sta.l SourceReserve_Oam+72
    lda.l SourceReserve_Oam+75
    eor #$40
    sta.l SourceReserve_Oam+75
    rep #$30
.a16
    lda #89
    sta.l SourceReserve_Signed+76
    sep #$20
.a8
    sta.l SourceReserve_Oam+76
    lda.l SourceReserve_Oam+79
    eor #$40
    sta.l SourceReserve_Oam+79
    rep #$30
.a16
    lda #5
    sta.l SourceReserve_High
    lda #0
    sta.l SourceReserve_High+2
    sep #$20
.a8
    sta.l SourceReserve_High+4
    rep #$30
.a16
    sta.l SourceReserve_Meta+18
    sta.l SourceReserve_Meta+50
    lda.l SVActor_HeldBlocks+0
    and #1
    ora.l SVActor_OldBlocks+0
    sta.l SVActor_OldBlocks+0
    lda.l SVActor_HeldBlocks+0
    and #$FFFE
    sta.l SVActor_HeldBlocks+0
    lda.l SVActor_HeldBlocks+8
    and #1
    ora.l SVActor_OldBlocks+8
    sta.l SVActor_OldBlocks+8
    lda.l SVActor_HeldBlocks+8
    and #$FFFE
    sta.l SVActor_HeldBlocks+8
    lda.l SVActor_HeldBlocks+16
    and #1
    ora.l SVActor_OldBlocks+16
    sta.l SVActor_OldBlocks+16
    lda.l SVActor_HeldBlocks+16
    and #$FFFE
    sta.l SVActor_HeldBlocks+16
    lda.l SVActor_HeldBlocks+24
    and #1
    ora.l SVActor_OldBlocks+24
    sta.l SVActor_OldBlocks+24
    lda.l SVActor_HeldBlocks+24
    and #$FFFE
    sta.l SVActor_HeldBlocks+24
    lda.l SVActor_HeldBlocks+32
    and #1
    ora.l SVActor_OldBlocks+32
    sta.l SVActor_OldBlocks+32
    lda.l SVActor_HeldBlocks+32
    and #$FFFE
    sta.l SVActor_HeldBlocks+32
    lda.l SVActor_HeldBlocks+40
    and #1
    ora.l SVActor_OldBlocks+40
    sta.l SVActor_OldBlocks+40
    lda.l SVActor_HeldBlocks+40
    and #$FFFE
    sta.l SVActor_HeldBlocks+40
    lda.l SVActor_HeldBlocks+48
    and #1
    ora.l SVActor_OldBlocks+48
    sta.l SVActor_OldBlocks+48
    lda.l SVActor_HeldBlocks+48
    and #$FFFE
    sta.l SVActor_HeldBlocks+48
    lda.l SVActor_HeldBlocks+56
    and #1
    ora.l SVActor_OldBlocks+56
    sta.l SVActor_OldBlocks+56
    lda.l SVActor_HeldBlocks+56
    and #$FFFE
    sta.l SVActor_HeldBlocks+56
    lda.l SVActor_HeldBlocks+64
    and #1
    ora.l SVActor_OldBlocks+64
    sta.l SVActor_OldBlocks+64
    lda.l SVActor_HeldBlocks+64
    and #$FFFE
    sta.l SVActor_HeldBlocks+64
    lda.l SVActor_HeldBlocks+72
    and #1
    ora.l SVActor_OldBlocks+72
    sta.l SVActor_OldBlocks+72
    lda.l SVActor_HeldBlocks+72
    and #$FFFE
    sta.l SVActor_HeldBlocks+72
    lda.l SVActor_HeldPalettes+0
    and #1
    ora.l SVActor_OldPalettes+0
    sta.l SVActor_OldPalettes+0
    lda.l SVActor_HeldPalettes+0
    and #$FFFE
    sta.l SVActor_HeldPalettes+0
    lda.l SVActor_Await
    ora #1
    sta.l SVActor_Await
    lda #1
    sta.l SourceSecond_Consumed
ldx #((SourceReserve_Oam) & $FFFF)
    ldy #((SOURCE_PACKET_BASE) & $FFFF)
    lda #79
    mvn $43,$43
ldx #((SourceReserve_High) & $FFFF)
    ldy #((SOURCE_PACKET_BASE+512) & $FFFF)
    lda #4
    mvn $43,$43
ldx #((SourceReserve_Oam) & $FFFF)
    ldy #((SOURCE_PACKET_BUFFER) & $FFFF)
    lda #79
    mvn $43,$43
ldx #((SourceReserve_High) & $FFFF)
    ldy #((SOURCE_PACKET_BUFFER+512) & $FFFF)
    lda #4
    mvn $43,$43
ldx #((SourceReserve_Meta) & $FFFF)
    ldy #((SOURCE_PACKET_ACTIVE_META) & $FFFF)
    lda #63
    mvn $43,$43
ldx #((SourceReserve_Signed) & $FFFF)
    ldy #((SOURCE_PACKET_SIGNED_X) & $FFFF)
    lda #79
    mvn $43,$43
    lda.l $436006
    bne SourceSecond_HasSurplus
    brl SourceSecond_NoSurplus
SourceSecond_HasSurplus:
.a16
.i16
    lda #$F000
    sta.l SOURCE_PACKET_BASE+80
    lda #0
    sta.l SOURCE_PACKET_BASE+82
    lda #$F000
    sta.l SOURCE_PACKET_BASE+84
    lda #0
    sta.l SOURCE_PACKET_BASE+86
    lda #$F000
    sta.l SOURCE_PACKET_BASE+88
    lda #0
    sta.l SOURCE_PACKET_BASE+90
    lda #$F000
    sta.l SOURCE_PACKET_BASE+92
    lda #0
    sta.l SOURCE_PACKET_BASE+94
    sep #$20
.a8
    lda #0
    sta.l SOURCE_PACKET_BASE+517
    rep #$30
.a16
.i16
    lda #$F000
    sta.l SOURCE_PACKET_BUFFER+80
    lda #0
    sta.l SOURCE_PACKET_BUFFER+82
    lda #$F000
    sta.l SOURCE_PACKET_BUFFER+84
    lda #0
    sta.l SOURCE_PACKET_BUFFER+86
    lda #$F000
    sta.l SOURCE_PACKET_BUFFER+88
    lda #0
    sta.l SOURCE_PACKET_BUFFER+90
    lda #$F000
    sta.l SOURCE_PACKET_BUFFER+92
    lda #0
    sta.l SOURCE_PACKET_BUFFER+94
    sep #$20
.a8
    lda #0
    sta.l SOURCE_PACKET_BUFFER+517
    rep #$30
.a16
.i16
SourceSecond_NoSurplus:
.a16
.i16
lda #$FFFF
    sta.l SourcePacket_ReadSeq
    lda #0
    sta.l SourcePacket_CopyBusy
    jsl SourceSecond_FinalRefresh
lda.l SourcePacket_RefreshAccepted
cmp #1
    beq SourceSecond_G908
    brl SourceSecond_CancelFresh
SourceSecond_G908:
.a16
.i16
    ; A newer producer sequence may carry the exact same captured pose.
    ; Reuse only all fourteen words read by SourcePacket_Refresh, bracketed
    ; by an even, live header. The original exact idle semantics still run.
    lda.l $434E7E
    cmp #$4D50
    beq SourceSecond_ReuseMagic
    brl SourceSecond_CancelFresh
SourceSecond_ReuseMagic:
.a16
.i16
    lda.l $434E7C
    sta.l SourceReserve_Seq
    and #1
    beq SourceSecond_ReuseEven
    brl SourceSecond_CancelFresh
SourceSecond_ReuseEven:
.a16
.i16
    lda.l SourceReserve_Seq
    cmp.l SourcePacket_ReadSeq
    bne SourceSecond_CompareSnapshot
    brl SourceSecond_SnapshotIdentical
SourceSecond_CompareSnapshot:
.a16
.i16
    lda.l $434E34
    cmp.l $4353C0
    beq SourceSecond_SameWord0_0
    brl SourceSecond_CancelFresh
SourceSecond_SameWord0_0:
.a16
.i16
    lda.l $434E3C
    cmp.l $4353C2
    beq SourceSecond_SameWord0_1
    brl SourceSecond_CancelFresh
SourceSecond_SameWord0_1:
.a16
.i16
    lda.l $434E40
    cmp.l $4353C4
    beq SourceSecond_SameWord0_2
    brl SourceSecond_CancelFresh
SourceSecond_SameWord0_2:
.a16
.i16
    lda.l $434E42
    cmp.l $4353C6
    beq SourceSecond_SameWord0_3
    brl SourceSecond_CancelFresh
SourceSecond_SameWord0_3:
.a16
.i16
    lda.l $434E44
    cmp.l $4353C8
    beq SourceSecond_SameWord0_4
    brl SourceSecond_CancelFresh
SourceSecond_SameWord0_4:
.a16
.i16
    lda.l $434E4A
    cmp.l $4353CA
    beq SourceSecond_SameWord0_5
    brl SourceSecond_CancelFresh
SourceSecond_SameWord0_5:
.a16
.i16
    lda.l $434E9C
    cmp.l $4353CC
    beq SourceSecond_SameWord0_6
    brl SourceSecond_CancelFresh
SourceSecond_SameWord0_6:
.a16
.i16
    lda.l $434E58
    cmp.l $4353D0
    beq SourceSecond_SameWord1_0
    brl SourceSecond_CancelFresh
SourceSecond_SameWord1_0:
.a16
.i16
    lda.l $434E60
    cmp.l $4353D2
    beq SourceSecond_SameWord1_1
    brl SourceSecond_CancelFresh
SourceSecond_SameWord1_1:
.a16
.i16
    lda.l $434E64
    cmp.l $4353D4
    beq SourceSecond_SameWord1_2
    brl SourceSecond_CancelFresh
SourceSecond_SameWord1_2:
.a16
.i16
    lda.l $434E66
    cmp.l $4353D6
    beq SourceSecond_SameWord1_3
    brl SourceSecond_CancelFresh
SourceSecond_SameWord1_3:
.a16
.i16
    lda.l $434E68
    cmp.l $4353D8
    beq SourceSecond_SameWord1_4
    brl SourceSecond_CancelFresh
SourceSecond_SameWord1_4:
.a16
.i16
    lda.l $434E6E
    cmp.l $4353DA
    beq SourceSecond_SameWord1_5
    brl SourceSecond_CancelFresh
SourceSecond_SameWord1_5:
.a16
.i16
    lda.l $434E9E
    cmp.l $4353DC
    beq SourceSecond_SameWord1_6
    brl SourceSecond_CancelFresh
SourceSecond_SameWord1_6:
.a16
.i16
SourceSecond_SnapshotIdentical:
.a16
.i16
    lda.l $434E2C
    cmp #0
    beq SourceSecond_Fresh0
    brl SourceSecond_CancelFresh
SourceSecond_Fresh0:
.a16
.i16
    lda.l $434E9C
    cmp #0
    beq SourceSecond_Fresh1
    brl SourceSecond_CancelFresh
SourceSecond_Fresh1:
.a16
.i16
    lda.l $434E9E
    cmp #133
    beq SourceSecond_Fresh2
    brl SourceSecond_CancelFresh
SourceSecond_Fresh2:
.a16
.i16
    lda.l $434E36
    cmp #188
    beq SourceSecond_Fresh3
    brl SourceSecond_CancelFresh
SourceSecond_Fresh3:
.a16
.i16
    lda.l $434E38
    cmp #0
    beq SourceSecond_Fresh4
    brl SourceSecond_CancelFresh
SourceSecond_Fresh4:
.a16
.i16
    lda.l $434E3A
    cmp #0
    beq SourceSecond_Fresh5
    brl SourceSecond_CancelFresh
SourceSecond_Fresh5:
.a16
.i16
    lda.l $434E3C
    cmp #9
    beq SourceSecond_Fresh6
    brl SourceSecond_CancelFresh
SourceSecond_Fresh6:
.a16
.i16
    lda.l $434E40
    cmp #1
    beq SourceSecond_Fresh7
    brl SourceSecond_CancelFresh
SourceSecond_Fresh7:
.a16
.i16
    lda.l $434E42
    cmp #0
    beq SourceSecond_Fresh8
    brl SourceSecond_CancelFresh
SourceSecond_Fresh8:
.a16
.i16
    lda.l $434E4A
    and #255
    cmp #2
    beq SourceSecond_Fresh9
    brl SourceSecond_CancelFresh
SourceSecond_Fresh9:
.a16
.i16
    lda.l $434E50
    and #255
    cmp #0
    beq SourceSecond_Fresh10
    brl SourceSecond_CancelFresh
SourceSecond_Fresh10:
.a16
.i16
    lda.l $434E5A
    cmp #188
    beq SourceSecond_Fresh11
    brl SourceSecond_CancelFresh
SourceSecond_Fresh11:
.a16
.i16
    lda.l $434E5C
    cmp #0
    beq SourceSecond_Fresh12
    brl SourceSecond_CancelFresh
SourceSecond_Fresh12:
.a16
.i16
    lda.l $434E5E
    cmp #0
    beq SourceSecond_Fresh13
    brl SourceSecond_CancelFresh
SourceSecond_Fresh13:
.a16
.i16
    lda.l $434E60
    cmp #9
    beq SourceSecond_Fresh14
    brl SourceSecond_CancelFresh
SourceSecond_Fresh14:
.a16
.i16
    lda.l $434E64
    cmp #1
    beq SourceSecond_Fresh15
    brl SourceSecond_CancelFresh
SourceSecond_Fresh15:
.a16
.i16
    lda.l $434E66
    cmp #0
    beq SourceSecond_Fresh16
    brl SourceSecond_CancelFresh
SourceSecond_Fresh16:
.a16
.i16
    lda.l $434E6E
    and #255
    cmp #2
    beq SourceSecond_Fresh17
    brl SourceSecond_CancelFresh
SourceSecond_Fresh17:
.a16
.i16
    lda.l $434E74
    and #255
    cmp #0
    beq SourceSecond_Fresh18
    brl SourceSecond_CancelFresh
SourceSecond_Fresh18:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    beq SourceSecond_FreshMagic
    brl SourceSecond_CancelFresh
SourceSecond_FreshMagic:
.a16
.i16
    lda.l SourceReserve_Seq
    cmp.l $434E7C
    beq SourceSecond_Publish
SourceSecond_CancelFresh:
.a16
.i16
    jml SourceIdleFinalize_Retry
    nop
    nop
    nop
    brl SourceSecond_Done
SourceSecond_Publish:
.a16
.i16
    lda.l SourceReserve_Seq
    sta.l SourcePacket_ReadSeq
    jsl SourceNextScene_IdleReady
    nop
    nop
    nop
    nop
    nop
    nop
    nop
SourceSecond_Promoted:
.a16
.i16
    brl SourceSecond_Done
SourceSecond_Done:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    rtl

; A complete actor's BUILD_META and live OAM are left untouched by the
; independent private-packet transaction. Preserve caller status exactly.
; Entered only by the original EmitFinish epilogue, with its saved
; registers still on the stack. Reuse that save frame instead of nesting
; another full wrapper call. The final PLA/PLP/RTL remain exactly original.
SourceSecond_EmitDone:
.a16
.i16
    pld
    plb
    ply
    plx
    lda.l SourceReserve_Valid
    cmp #$1D1F
    bne SourceSecond_RenderReset
    lda.l SourceSecond_Consumed
    bne SourceSecond_RenderDone
    lda.l $434E3C
    cmp #9
    beq SourceSecond_FastIdle0
    brl SourceSecond_RenderDone
SourceSecond_FastIdle0:
.a16
.i16
    lda.l $434E60
    cmp #9
    beq SourceSecond_FastIdle1
    brl SourceSecond_RenderDone
SourceSecond_FastIdle1:
.a16
.i16
    lda.l $434E3A
    and #255
    beq SourceSecond_FastZero0
    brl SourceSecond_RenderDone
SourceSecond_FastZero0:
.a16
.i16
    lda.l $434E5E
    and #255
    beq SourceSecond_FastZero1
    brl SourceSecond_RenderDone
SourceSecond_FastZero1:
.a16
.i16
    lda.l $434E50
    and #255
    beq SourceSecond_FastZero2
    brl SourceSecond_RenderDone
SourceSecond_FastZero2:
.a16
.i16
    lda.l $434E74
    and #255
    beq SourceSecond_FastZero3
    brl SourceSecond_RenderDone
SourceSecond_FastZero3:
.a16
.i16

    jsl SourceSecond_Dispatch
    bra SourceSecond_RenderDone
SourceSecond_RenderReset:
.a16
.i16
    ; Reset at ordinary actor boundaries before the first reservation is consumed.
    ; The original foreground Wait path remains entirely unchanged.
    lda #0
    sta.l SourceSecond_Consumed
SourceSecond_RenderDone:
    pla
    plp
    rtl
SourceSecond_RenderBoundary:
.a16
.i16
    jml SourcePacket_EmitFinish
SourceSecond_RenderEnd:
