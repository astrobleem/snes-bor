; One independent prepared idle image. SVActor pin bit0 is not an actor.
; Stage0, default Kula, exact ten fixed ready slots; no new DMA admission.
SourceReserve_Valid = $436000
SourceReserve_Seq = $436002
SourceReserve_Oam = $436010
SourceReserve_High = $436060
SourceReserve_Meta = $436070
SourceReserve_Signed = $4360B0
SourceReserve_Wait:
.a16
.i16
    jsl SourcePacket_ForegroundPrepare
    php
    rep #$30
    pha
    phx
    phy
    phb
    phd
    cld
    lda.l SourceReserve_Valid
    cmp #$1D1F
    bne SourceReserve_NotConsumed
    brl SourceReserve_Done
SourceReserve_NotConsumed:
.a16
.i16
lda.l Game_CampaignId
and #255
cmp #3
    beq SourceReserve_G20
    brl SourceReserve_Done
SourceReserve_G20:
.a16
.i16
lda.l Game_State
cmp #0
    beq SourceReserve_G28
    brl SourceReserve_Done
SourceReserve_G28:
.a16
.i16
lda.l Game_StageIndex
cmp #0
    beq SourceReserve_G35
    brl SourceReserve_Done
SourceReserve_G35:
.a16
.i16
lda.l $7E175E
cmp #2
    beq SourceReserve_G42
    brl SourceReserve_Done
SourceReserve_G42:
.a16
.i16
lda.l $7E1760
cmp #1
    beq SourceReserve_G49
    brl SourceReserve_Done
SourceReserve_G49:
.a16
.i16
lda.l $7E46DC
cmp #1
    beq SourceReserve_G56
    brl SourceReserve_Done
SourceReserve_G56:
.a16
.i16
lda.l $7E46DE
cmp #0
    beq SourceReserve_G63
    brl SourceReserve_Done
SourceReserve_G63:
.a16
.i16
lda.l SourceInput_Magic
cmp #6752
    beq SourceReserve_G70
    brl SourceReserve_Done
SourceReserve_G70:
.a16
.i16
lda.l SourceVisual_CompletedMagic
cmp #49229
    beq SourceReserve_G77
    brl SourceReserve_Done
SourceReserve_G77:
.a16
.i16
lda.l SVActor_Magic
cmp #44057
    beq SourceReserve_G84
    brl SourceReserve_Done
SourceReserve_G84:
.a16
.i16
; A Ready stamp has never copied/published the private image. Drop only
; that unused reservation when its fixed geometry is no longer applicable.
    lda.l SourceReserve_Valid
    cmp #$1D1E
    beq SourceReserve_CheckUnused
    brl SourceReserve_UnusedChecked
SourceReserve_CheckUnused:
.a16
.i16
    lda.l SourcePacket_CopyBusy
    beq SourceReserve_UnusedNotBusy
    brl SourceReserve_Done
SourceReserve_UnusedNotBusy:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    beq SourceReserve_UnusedMagic
    brl SourceReserve_Done
SourceReserve_UnusedMagic:
.a16
.i16
    lda.l $434E7C
    sta.l SourceReserve_Seq
    and #1
    beq SourceReserve_UnusedEven
    brl SourceReserve_Done
SourceReserve_UnusedEven:
.a16
.i16
lda.l Stage_Mirror
and #255
cmp #0
    beq SourceReserve_Keep30
    brl SourceReserve_DropUnused
SourceReserve_Keep30:
.a16
.i16
lda.l Screen_PosX
cmp #0
    beq SourceReserve_Keep38
    brl SourceReserve_DropUnused
SourceReserve_Keep38:
.a16
.i16
lda.l SourcePacket_ActiveCamera
cmp #0
    beq SourceReserve_Keep45
    brl SourceReserve_DropUnused
SourceReserve_Keep45:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+6
cmp #150
    beq SourceReserve_Keep52
    brl SourceReserve_DropUnused
SourceReserve_Keep52:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+38
cmp #150
    beq SourceReserve_Keep59
    brl SourceReserve_DropUnused
SourceReserve_Keep59:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+18
cmp #1
    beq SourceReserve_Keep66
    brl SourceReserve_DropUnused
SourceReserve_Keep66:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+50
cmp #1
    beq SourceReserve_Keep73
    brl SourceReserve_DropUnused
SourceReserve_Keep73:
.a16
.i16
lda.l $434E2C
cmp #0
    beq SourceReserve_Keep80
    brl SourceReserve_DropUnused
SourceReserve_Keep80:
.a16
.i16
lda.l $434E9C
cmp #0
    beq SourceReserve_Keep87
    brl SourceReserve_DropUnused
SourceReserve_Keep87:
.a16
.i16
lda.l $434E9E
cmp #133
    beq SourceReserve_Keep94
    brl SourceReserve_DropUnused
SourceReserve_Keep94:
.a16
.i16
lda.l $434E36
cmp #188
    beq SourceReserve_Keep101
    brl SourceReserve_DropUnused
SourceReserve_Keep101:
.a16
.i16
lda.l $434E38
cmp #0
    beq SourceReserve_Keep108
    brl SourceReserve_DropUnused
SourceReserve_Keep108:
.a16
.i16
lda.l $434E3A
cmp #1
    beq SourceReserve_Keep115
    brl SourceReserve_DropUnused
SourceReserve_Keep115:
.a16
.i16
lda.l $434E40
cmp #1
    beq SourceReserve_Keep122
    brl SourceReserve_DropUnused
SourceReserve_Keep122:
.a16
.i16
lda.l $434E42
cmp #0
    beq SourceReserve_Keep129
    brl SourceReserve_DropUnused
SourceReserve_Keep129:
.a16
.i16
lda.l $434E50
and #255
cmp #2
    bcc SourceReserve_Keep136
    brl SourceReserve_DropUnused
SourceReserve_Keep136:
.a16
.i16
lda.l $7E0A00+CHAR_HP
and #255
cmp #0
    bne SourceReserve_Keep144
    brl SourceReserve_DropUnused
SourceReserve_Keep144:
.a16
.i16
lda.l $7E0A00+CHAR_INPUT_DRIVEN
and #255
cmp #1
    beq SourceReserve_Keep152
    brl SourceReserve_DropUnused
SourceReserve_Keep152:
.a16
.i16
lda.l $7E0A00+CHAR_ROSTER_INDEX
and #255
cmp #22
    beq SourceReserve_Keep160
    brl SourceReserve_DropUnused
SourceReserve_Keep160:
.a16
.i16
lda.l $7E0A00+CHAR_MAP_INDEX
and #255
cmp #0
    beq SourceReserve_Keep168
    brl SourceReserve_DropUnused
SourceReserve_Keep168:
.a16
.i16
lda.l $434E5A
cmp #188
    beq SourceReserve_Keep176
    brl SourceReserve_DropUnused
SourceReserve_Keep176:
.a16
.i16
lda.l $434E5C
cmp #0
    beq SourceReserve_Keep183
    brl SourceReserve_DropUnused
SourceReserve_Keep183:
.a16
.i16
lda.l $434E5E
cmp #1
    beq SourceReserve_Keep190
    brl SourceReserve_DropUnused
SourceReserve_Keep190:
.a16
.i16
lda.l $434E64
cmp #1
    beq SourceReserve_Keep197
    brl SourceReserve_DropUnused
SourceReserve_Keep197:
.a16
.i16
lda.l $434E66
cmp #0
    beq SourceReserve_Keep204
    brl SourceReserve_DropUnused
SourceReserve_Keep204:
.a16
.i16
lda.l $434E74
and #255
cmp #2
    bcc SourceReserve_Keep211
    brl SourceReserve_DropUnused
SourceReserve_Keep211:
.a16
.i16
lda.l $7E0A85+CHAR_HP
and #255
cmp #0
    bne SourceReserve_Keep219
    brl SourceReserve_DropUnused
SourceReserve_Keep219:
.a16
.i16
lda.l $7E0A85+CHAR_INPUT_DRIVEN
and #255
cmp #1
    beq SourceReserve_Keep227
    brl SourceReserve_DropUnused
SourceReserve_Keep227:
.a16
.i16
lda.l $7E0A85+CHAR_ROSTER_INDEX
and #255
cmp #22
    beq SourceReserve_Keep235
    brl SourceReserve_DropUnused
SourceReserve_Keep235:
.a16
.i16
lda.l $7E0A85+CHAR_MAP_INDEX
and #255
cmp #0
    beq SourceReserve_Keep243
    brl SourceReserve_DropUnused
SourceReserve_Keep243:
.a16
.i16
brl SourceReserve_UnusedChecked
SourceReserve_DropUnused:
.a16
.i16
    lda.l SourceReserve_Seq
    cmp.l $434E7C
    beq SourceReserve_UnusedSameSeq
    brl SourceReserve_Done
SourceReserve_UnusedSameSeq:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    beq SourceReserve_DropUnusedNow
    brl SourceReserve_Done
SourceReserve_DropUnusedNow:
.a16
.i16
lda.l SVActor_HeldBlocks+0
    and #$FFFE
    sta.l SVActor_HeldBlocks+0
lda.l SVActor_HeldBlocks+8
    and #$FFFE
    sta.l SVActor_HeldBlocks+8
lda.l SVActor_HeldBlocks+16
    and #$FFFE
    sta.l SVActor_HeldBlocks+16
lda.l SVActor_HeldBlocks+24
    and #$FFFE
    sta.l SVActor_HeldBlocks+24
lda.l SVActor_HeldBlocks+32
    and #$FFFE
    sta.l SVActor_HeldBlocks+32
lda.l SVActor_HeldBlocks+40
    and #$FFFE
    sta.l SVActor_HeldBlocks+40
lda.l SVActor_HeldBlocks+48
    and #$FFFE
    sta.l SVActor_HeldBlocks+48
lda.l SVActor_HeldBlocks+56
    and #$FFFE
    sta.l SVActor_HeldBlocks+56
lda.l SVActor_HeldBlocks+64
    and #$FFFE
    sta.l SVActor_HeldBlocks+64
lda.l SVActor_HeldBlocks+72
    and #$FFFE
    sta.l SVActor_HeldBlocks+72
lda.l SVActor_HeldPalettes+0
    and #$FFFE
    sta.l SVActor_HeldPalettes+0
lda #0
    sta.l SourceReserve_Valid
SourceReserve_UnusedDropped:
.a16
.i16
    brl SourceReserve_Done
SourceReserve_UnusedChecked:
.a16
.i16
lda.l Stage_Mirror
and #255
cmp #0
    beq SourceReserve_G91
    brl SourceReserve_Done
SourceReserve_G91:
.a16
.i16
lda.l Screen_PosX
cmp #0
    beq SourceReserve_G99
    brl SourceReserve_Done
SourceReserve_G99:
.a16
.i16
    lda.l SourcePacket_ActiveCamera
    cmp #0
    beq SourceReserve_Depth0
    brl SourceReserve_Done
SourceReserve_Depth0:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+6
    cmp #150
    beq SourceReserve_Depth1
    brl SourceReserve_Done
SourceReserve_Depth1:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+38
    cmp #150
    beq SourceReserve_Depth2
    brl SourceReserve_Done
SourceReserve_Depth2:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+18
    cmp #1
    beq SourceReserve_Depth3
    brl SourceReserve_Done
SourceReserve_Depth3:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+50
    cmp #1
    beq SourceReserve_Depth4
    brl SourceReserve_Done
SourceReserve_Depth4:
.a16
.i16
    lda.l $434E36
    cmp #188
    beq SourceReserve_Depth5
    brl SourceReserve_Done
SourceReserve_Depth5:
.a16
.i16
    lda.l $434E5A
    cmp #188
    beq SourceReserve_Depth6
    brl SourceReserve_Done
SourceReserve_Depth6:
.a16
.i16
lda.l SourcePacket_ActiveValid
cmp #1
    beq SourceReserve_G106
    brl SourceReserve_Done
SourceReserve_G106:
.a16
.i16
lda.l SourcePacket_CopyBusy
cmp #0
    beq SourceReserve_G113
    brl SourceReserve_Done
SourceReserve_G113:
.a16
.i16
lda.l SourcePacket_RefreshAccepted
cmp #1
    beq SourceReserve_G120
    brl SourceReserve_Done
SourceReserve_G120:
.a16
.i16
lda.l $434E7E
cmp #19792
    beq SourceReserve_G127
    brl SourceReserve_Done
SourceReserve_G127:
.a16
.i16
lda.l $434E7C
and #1
cmp #0
    beq SourceReserve_G134
    brl SourceReserve_Done
SourceReserve_G134:
.a16
.i16
lda.l $434E2C
cmp #0
    beq SourceReserve_G142
    brl SourceReserve_Done
SourceReserve_G142:
.a16
.i16
lda.l $434E7C
    sta.l SourceReserve_Seq
lda.l SOURCE_PACKET_ACTIVE_META
cmp #0
    beq SourceReserve_G151
    brl SourceReserve_Done
SourceReserve_G151:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+2
cmp #40
    beq SourceReserve_G158
    brl SourceReserve_Done
SourceReserve_G158:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+32
cmp #40
    beq SourceReserve_G165
    brl SourceReserve_Done
SourceReserve_G165:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+34
cmp #80
    beq SourceReserve_G172
    brl SourceReserve_Done
SourceReserve_G172:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+16
cmp #1
    beq SourceReserve_G179
    brl SourceReserve_Done
SourceReserve_G179:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+48
cmp #1
    beq SourceReserve_G186
    brl SourceReserve_Done
SourceReserve_G186:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+10
cmp #0
    beq SourceReserve_G193
    brl SourceReserve_Done
SourceReserve_G193:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+42
cmp #0
    beq SourceReserve_G200
    brl SourceReserve_Done
SourceReserve_G200:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+8
cmp #22
    beq SourceReserve_G207
    brl SourceReserve_Done
SourceReserve_G207:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+40
cmp #22
    beq SourceReserve_G214
    brl SourceReserve_Done
SourceReserve_G214:
.a16
.i16
lda.l $434E9C
cmp #0
    beq SourceReserve_G221
    brl SourceReserve_Done
SourceReserve_G221:
.a16
.i16
lda.l $434E9E
cmp #133
    beq SourceReserve_G228
    brl SourceReserve_Done
SourceReserve_G228:
.a16
.i16
lda.l $434E38
cmp #0
    beq SourceReserve_G235
    brl SourceReserve_Done
SourceReserve_G235:
.a16
.i16
lda.l $434E3A
cmp #1
    beq SourceReserve_G242
    brl SourceReserve_Done
SourceReserve_G242:
.a16
.i16
lda.l $434E3C
cmp #9
    beq SourceReserve_G249
    brl SourceReserve_Done
SourceReserve_G249:
.a16
.i16
lda.l $434E40
cmp #1
    beq SourceReserve_G256
    brl SourceReserve_Done
SourceReserve_G256:
.a16
.i16
lda.l $434E42
cmp #0
    beq SourceReserve_G263
    brl SourceReserve_Done
SourceReserve_G263:
.a16
.i16
lda.l $434E4A
and #255
cmp #2
    beq SourceReserve_G270
    brl SourceReserve_Done
SourceReserve_G270:
.a16
.i16
lda.l $434E50
and #255
cmp #0
    beq SourceReserve_G278
    brl SourceReserve_Done
SourceReserve_G278:
.a16
.i16
lda.l $7E0A00+CHAR_HP
and #255
cmp #0
    bne SourceReserve_G286
    brl SourceReserve_Done
SourceReserve_G286:
.a16
.i16
lda.l $7E0A00+CHAR_INPUT_DRIVEN
and #255
cmp #1
    beq SourceReserve_G294
    brl SourceReserve_Done
SourceReserve_G294:
.a16
.i16
lda.l $7E0A00+CHAR_ROSTER_INDEX
and #255
cmp #22
    beq SourceReserve_G302
    brl SourceReserve_Done
SourceReserve_G302:
.a16
.i16
lda.l $7E0A00+CHAR_MAP_INDEX
and #255
cmp #0
    beq SourceReserve_G310
    brl SourceReserve_Done
SourceReserve_G310:
.a16
.i16
lda.l $7E0A00+CHAR_SELECTED
and #255
cmp #3
    bcc SourceReserve_G318
    brl SourceReserve_Done
SourceReserve_G318:
.a16
.i16
lda.l $434E5C
cmp #0
    beq SourceReserve_G326
    brl SourceReserve_Done
SourceReserve_G326:
.a16
.i16
lda.l $434E5E
cmp #1
    beq SourceReserve_G333
    brl SourceReserve_Done
SourceReserve_G333:
.a16
.i16
lda.l $434E60
cmp #9
    beq SourceReserve_G340
    brl SourceReserve_Done
SourceReserve_G340:
.a16
.i16
lda.l $434E64
cmp #1
    beq SourceReserve_G347
    brl SourceReserve_Done
SourceReserve_G347:
.a16
.i16
lda.l $434E66
cmp #0
    beq SourceReserve_G354
    brl SourceReserve_Done
SourceReserve_G354:
.a16
.i16
lda.l $434E6E
and #255
cmp #2
    beq SourceReserve_G361
    brl SourceReserve_Done
SourceReserve_G361:
.a16
.i16
lda.l $434E74
and #255
cmp #0
    beq SourceReserve_G369
    brl SourceReserve_Done
SourceReserve_G369:
.a16
.i16
lda.l $7E0A85+CHAR_HP
and #255
cmp #0
    bne SourceReserve_G377
    brl SourceReserve_Done
SourceReserve_G377:
.a16
.i16
lda.l $7E0A85+CHAR_INPUT_DRIVEN
and #255
cmp #1
    beq SourceReserve_G385
    brl SourceReserve_Done
SourceReserve_G385:
.a16
.i16
lda.l $7E0A85+CHAR_ROSTER_INDEX
and #255
cmp #22
    beq SourceReserve_G393
    brl SourceReserve_Done
SourceReserve_G393:
.a16
.i16
lda.l $7E0A85+CHAR_MAP_INDEX
and #255
cmp #0
    beq SourceReserve_G401
    brl SourceReserve_Done
SourceReserve_G401:
.a16
.i16
lda.l $7E0A85+CHAR_SELECTED
and #255
cmp #3
    bcc SourceReserve_G409
    brl SourceReserve_Done
SourceReserve_G409:
.a16
.i16
lda.l SourceVisual_BlockCache+0
cmp #8842
    beq SourceReserve_G417
    brl SourceReserve_Done
SourceReserve_G417:
.a16
.i16
lda.l SourceVisual_BlockCache+2
cmp #2
    beq SourceReserve_G424
    brl SourceReserve_Done
SourceReserve_G424:
.a16
.i16
lda.l SourceVisual_BlockCache+8
cmp #2633
    beq SourceReserve_G431
    brl SourceReserve_Done
SourceReserve_G431:
.a16
.i16
lda.l SourceVisual_BlockCache+10
cmp #2
    beq SourceReserve_G438
    brl SourceReserve_Done
SourceReserve_G438:
.a16
.i16
lda.l SourceVisual_BlockCache+16
cmp #5886
    beq SourceReserve_G445
    brl SourceReserve_Done
SourceReserve_G445:
.a16
.i16
lda.l SourceVisual_BlockCache+18
cmp #2
    beq SourceReserve_G452
    brl SourceReserve_Done
SourceReserve_G452:
.a16
.i16
lda.l SourceVisual_BlockCache+24
cmp #13304
    beq SourceReserve_G459
    brl SourceReserve_Done
SourceReserve_G459:
.a16
.i16
lda.l SourceVisual_BlockCache+26
cmp #2
    beq SourceReserve_G466
    brl SourceReserve_Done
SourceReserve_G466:
.a16
.i16
lda.l SourceVisual_BlockCache+32
cmp #1592
    beq SourceReserve_G473
    brl SourceReserve_Done
SourceReserve_G473:
.a16
.i16
lda.l SourceVisual_BlockCache+34
cmp #2
    beq SourceReserve_G480
    brl SourceReserve_Done
SourceReserve_G480:
.a16
.i16
lda.l SourceVisual_BlockCache+40
cmp #12228
    beq SourceReserve_G487
    brl SourceReserve_Done
SourceReserve_G487:
.a16
.i16
lda.l SourceVisual_BlockCache+42
cmp #2
    beq SourceReserve_G494
    brl SourceReserve_Done
SourceReserve_G494:
.a16
.i16
lda.l SourceVisual_BlockCache+48
cmp #7241
    beq SourceReserve_G501
    brl SourceReserve_Done
SourceReserve_G501:
.a16
.i16
lda.l SourceVisual_BlockCache+50
cmp #2
    beq SourceReserve_G508
    brl SourceReserve_Done
SourceReserve_G508:
.a16
.i16
lda.l SourceVisual_BlockCache+56
cmp #559
    beq SourceReserve_G515
    brl SourceReserve_Done
SourceReserve_G515:
.a16
.i16
lda.l SourceVisual_BlockCache+58
cmp #2
    beq SourceReserve_G522
    brl SourceReserve_Done
SourceReserve_G522:
.a16
.i16
lda.l SourceVisual_BlockCache+64
cmp #3618
    beq SourceReserve_G529
    brl SourceReserve_Done
SourceReserve_G529:
.a16
.i16
lda.l SourceVisual_BlockCache+66
cmp #2
    beq SourceReserve_G536
    brl SourceReserve_Done
SourceReserve_G536:
.a16
.i16
lda.l SourceVisual_BlockCache+72
cmp #11343
    beq SourceReserve_G543
    brl SourceReserve_Done
SourceReserve_G543:
.a16
.i16
lda.l SourceVisual_BlockCache+74
cmp #2
    beq SourceReserve_G550
    brl SourceReserve_Done
SourceReserve_G550:
.a16
.i16
lda.l SourceVisual_PaletteCache
cmp #361
    beq SourceReserve_G557
    brl SourceReserve_Done
SourceReserve_G557:
.a16
.i16
lda.l SourceVisual_PaletteCache+3
and #255
cmp #1
    beq SourceReserve_G564
    brl SourceReserve_Done
SourceReserve_G564:
.a16
.i16
lda.l DmaQueue+4
    and #$40
    beq SourceReserve_Q0
lda.l DmaQueue+7
and #255
cmp #67
    bne SourceReserve_G575
    brl SourceReserve_Done
SourceReserve_G575:
.a16
.i16
lda.l DmaQueue+4
and #31
cmp #1
    bne SourceReserve_G583
    brl SourceReserve_Done
SourceReserve_G583:
.a16
.i16
SourceReserve_Q0:
.a16
.i16
lda.l DmaQueue+12
    and #$40
    beq SourceReserve_Q1
lda.l DmaQueue+15
and #255
cmp #67
    bne SourceReserve_G597
    brl SourceReserve_Done
SourceReserve_G597:
.a16
.i16
lda.l DmaQueue+12
and #31
cmp #1
    bne SourceReserve_G605
    brl SourceReserve_Done
SourceReserve_G605:
.a16
.i16
SourceReserve_Q1:
.a16
.i16
lda.l DmaQueue+20
    and #$40
    beq SourceReserve_Q2
lda.l DmaQueue+23
and #255
cmp #67
    bne SourceReserve_G619
    brl SourceReserve_Done
SourceReserve_G619:
.a16
.i16
lda.l DmaQueue+20
and #31
cmp #1
    bne SourceReserve_G627
    brl SourceReserve_Done
SourceReserve_G627:
.a16
.i16
SourceReserve_Q2:
.a16
.i16
lda.l DmaQueue+28
    and #$40
    beq SourceReserve_Q3
lda.l DmaQueue+31
and #255
cmp #67
    bne SourceReserve_G641
    brl SourceReserve_Done
SourceReserve_G641:
.a16
.i16
lda.l DmaQueue+28
and #31
cmp #1
    bne SourceReserve_G649
    brl SourceReserve_Done
SourceReserve_G649:
.a16
.i16
SourceReserve_Q3:
.a16
.i16
lda.l DmaQueue+36
    and #$40
    beq SourceReserve_Q4
lda.l DmaQueue+39
and #255
cmp #67
    bne SourceReserve_G663
    brl SourceReserve_Done
SourceReserve_G663:
.a16
.i16
lda.l DmaQueue+36
and #31
cmp #1
    bne SourceReserve_G671
    brl SourceReserve_Done
SourceReserve_G671:
.a16
.i16
SourceReserve_Q4:
.a16
.i16
lda.l DmaQueue+44
    and #$40
    beq SourceReserve_Q5
lda.l DmaQueue+47
and #255
cmp #67
    bne SourceReserve_G685
    brl SourceReserve_Done
SourceReserve_G685:
.a16
.i16
lda.l DmaQueue+44
and #31
cmp #1
    bne SourceReserve_G693
    brl SourceReserve_Done
SourceReserve_G693:
.a16
.i16
SourceReserve_Q5:
.a16
.i16
lda.l DmaQueue+52
    and #$40
    beq SourceReserve_Q6
lda.l DmaQueue+55
and #255
cmp #67
    bne SourceReserve_G707
    brl SourceReserve_Done
SourceReserve_G707:
.a16
.i16
lda.l DmaQueue+52
and #31
cmp #1
    bne SourceReserve_G715
    brl SourceReserve_Done
SourceReserve_G715:
.a16
.i16
SourceReserve_Q6:
.a16
.i16
lda.l DmaQueue+60
    and #$40
    beq SourceReserve_Q7
lda.l DmaQueue+63
and #255
cmp #67
    bne SourceReserve_G729
    brl SourceReserve_Done
SourceReserve_G729:
.a16
.i16
lda.l DmaQueue+60
and #31
cmp #1
    bne SourceReserve_G737
    brl SourceReserve_Done
SourceReserve_G737:
.a16
.i16
SourceReserve_Q7:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+12
    cmp #22
    bne SourceReserve_TryPromote
    lda.l SOURCE_PACKET_ACTIVE_META+14
    bne SourceReserve_TryPromote
    lda.l SOURCE_PACKET_ACTIVE_META+44
    cmp #22
    bne SourceReserve_TryPromote
    lda.l SOURCE_PACKET_ACTIVE_META+46
    bne SourceReserve_TryPromote
    brl SourceReserve_Seed
SourceReserve_TryPromote:
.a16
.i16
lda.l SourceReserve_Valid
cmp #7454
    beq SourceReserve_G762
    brl SourceReserve_Done
SourceReserve_G762:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+12
cmp #278
    beq SourceReserve_G769
    brl SourceReserve_Done
SourceReserve_G769:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+44
cmp #278
    beq SourceReserve_G776
    brl SourceReserve_Done
SourceReserve_G776:
.a16
.i16
lda.l SVActor_HeldBlocks+0
and #1
cmp #1
    beq SourceReserve_G783
    brl SourceReserve_Done
SourceReserve_G783:
.a16
.i16
lda.l SVActor_HeldBlocks+8
and #1
cmp #1
    beq SourceReserve_G791
    brl SourceReserve_Done
SourceReserve_G791:
.a16
.i16
lda.l SVActor_HeldBlocks+16
and #1
cmp #1
    beq SourceReserve_G799
    brl SourceReserve_Done
SourceReserve_G799:
.a16
.i16
lda.l SVActor_HeldBlocks+24
and #1
cmp #1
    beq SourceReserve_G807
    brl SourceReserve_Done
SourceReserve_G807:
.a16
.i16
lda.l SVActor_HeldBlocks+32
and #1
cmp #1
    beq SourceReserve_G815
    brl SourceReserve_Done
SourceReserve_G815:
.a16
.i16
lda.l SVActor_HeldBlocks+40
and #1
cmp #1
    beq SourceReserve_G823
    brl SourceReserve_Done
SourceReserve_G823:
.a16
.i16
lda.l SVActor_HeldBlocks+48
and #1
cmp #1
    beq SourceReserve_G831
    brl SourceReserve_Done
SourceReserve_G831:
.a16
.i16
lda.l SVActor_HeldBlocks+56
and #1
cmp #1
    beq SourceReserve_G839
    brl SourceReserve_Done
SourceReserve_G839:
.a16
.i16
lda.l SVActor_HeldBlocks+64
and #1
cmp #1
    beq SourceReserve_G847
    brl SourceReserve_Done
SourceReserve_G847:
.a16
.i16
lda.l SVActor_HeldBlocks+72
and #1
cmp #1
    beq SourceReserve_G855
    brl SourceReserve_Done
SourceReserve_G855:
.a16
.i16
lda.l SVActor_HeldPalettes
and #1
cmp #1
    beq SourceReserve_G863
    brl SourceReserve_Done
SourceReserve_G863:
.a16
.i16
SourceReserve_Promote:
.a16
.i16
    jsl SourceAttackLease_BeforeScene
    nop
    nop
    nop
    lda #0
    sta.l SourcePacket_NmiPending
    sta.l SourcePacket_RefreshAccepted
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
    lda #$1D1F
    sta.l SourceReserve_Valid
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
lda #$FFFF
    sta.l SourcePacket_ReadSeq
    lda #0
    sta.l SourcePacket_CopyBusy
    jsl SourcePacket_ForegroundPrepare
lda.l SourcePacket_RefreshAccepted
cmp #1
    beq SourceReserve_G908
    brl SourceReserve_Done
SourceReserve_G908:
.a16
.i16
lda.l SourceReserve_Seq
    cmp.l $434E7C
    beq SourceReserve_Publish
    lda #0
    sta.l SourcePacket_NmiPending
    brl SourceReserve_Done
SourceReserve_Publish:
.a16
.i16
    jsl SourceNextScene_IdleReady
    nop
    nop
    nop
    nop
    nop
    nop
    nop
SourceReserve_Promoted:
.a16
.i16
    brl SourceReserve_Done
SourceReserve_Seed:
.a16
.i16
lda.l SourceReserve_Valid
    cmp #$1D1E
    bne SourceReserve_SeedNow
    lda.l SVActor_HeldBlocks
    and #1
    beq SourceReserve_SeedNow
    brl SourceReserve_Done
SourceReserve_SeedNow:
.a16
.i16
    lda #0
    sta.l SourceReserve_Valid
ldx #((SOURCE_PACKET_BASE) & $FFFF)
    ldy #((SourceReserve_Oam) & $FFFF)
    lda #79
    mvn $43,$43
ldx #((SOURCE_PACKET_BASE+512) & $FFFF)
    ldy #((SourceReserve_High) & $FFFF)
    lda #4
    mvn $43,$43
ldx #((SOURCE_PACKET_ACTIVE_META) & $FFFF)
    ldy #((SourceReserve_Meta) & $FFFF)
    lda #63
    mvn $43,$43
ldx #((SOURCE_PACKET_SIGNED_X) & $FFFF)
    ldy #((SourceReserve_Signed) & $FFFF)
    lda #79
    mvn $43,$43
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
    lda #$1D1E
    sta.l SourceReserve_Valid
SourceReserve_Seeded:
.a16
.i16
SourceReserve_Done:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    rtl
SourceReserve_Reset:
.a16
.i16
    sta.l SourcePacket_ThisFrame
    sta.l SourceReserve_Valid
    rtl
SourceReserve_End:
