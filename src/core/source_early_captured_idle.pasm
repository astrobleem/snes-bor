; Promote only ALREADY captured two-player idle to private position transport.
; No capture, owner/Ready/ack, live OAM shadow, input or world writes.
SourceEarlyIdle_AfterCapture:
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
tdc
    cmp #$0A85
beq SourceEarlyIdle_Gate13
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate13:
.a16
.i16
lda.l Game_CampaignId
    and #255
    cmp #3
beq SourceEarlyIdle_Gate20
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate20:
.a16
.i16
lda.l Game_State
    cmp #0
beq SourceEarlyIdle_Gate28
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate28:
.a16
.i16
lda.l $7E175E
    cmp #2
beq SourceEarlyIdle_Gate35
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate35:
.a16
.i16
lda.l $7E1760
    cmp #1
beq SourceEarlyIdle_Gate42
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate42:
.a16
.i16
lda.l $7E46DC
    cmp #1
beq SourceEarlyIdle_Gate49
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate49:
.a16
.i16
lda.l $7E46DE
    cmp #0
beq SourceEarlyIdle_Gate56
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate56:
.a16
.i16
lda.l SourceVisual_CompletedMagic
    cmp #49229
beq SourceEarlyIdle_Gate63
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate63:
.a16
.i16
lda.l SVActor_Magic
    cmp #44057
beq SourceEarlyIdle_Gate70
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate70:
.a16
.i16
lda.l SourceInput_Magic
    cmp #6752
beq SourceEarlyIdle_Gate77
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate77:
.a16
.i16
lda.l Game_StageIndex
    cmp #0
beq SourceEarlyIdle_Gate84
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate84:
.a16
.i16
lda.l Stage_Mirror
    and #255
    cmp #0
beq SourceEarlyIdle_Gate91
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate91:
.a16
.i16
lda.l Screen_PosX
    cmp #0
beq SourceEarlyIdle_Gate99
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate99:
.a16
.i16
lda.l SourcePacket_CopyBusy
    cmp #0
beq SourceEarlyIdle_Gate106
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate106:
.a16
.i16
lda.l SourcePacket_ActiveValid
    cmp #1
beq SourceEarlyIdle_Gate113
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate113:
.a16
.i16
lda.l SourceVisual_CompletedPending
    cmp #0
beq SourceEarlyIdle_Gate120
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate120:
.a16
.i16
lda.l Oam_UploadFlag
    cmp #0
beq SourceEarlyIdle_Gate127
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate127:
.a16
.i16
lda.l SourceVisual_CompletedEarly
    cmp #0
beq SourceEarlyIdle_Gate134
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate134:
.a16
.i16
lda.l SourceVisual_CompletedValid
    cmp #1
beq SourceEarlyIdle_Gate141
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate141:
.a16
.i16
lda.l SourceVisual_CompletedEntry
    cmp #22
beq SourceEarlyIdle_Gate148
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate148:
.a16
.i16
lda.l SourceVisual_CompletedEntry+2
    cmp #0
beq SourceEarlyIdle_Gate155
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate155:
.a16
.i16
lda.l SourceVisual_CompletedEntry+12
    and #255
    cmp #10
beq SourceEarlyIdle_Gate162
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate162:
.a16
.i16
lda.l SVActor_Data+SVActor_Valid
    cmp #1
beq SourceEarlyIdle_Gate170
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate170:
.a16
.i16
lda.l SVActor_Data
    cmp #22
beq SourceEarlyIdle_Gate177
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate177:
.a16
.i16
lda.l SVActor_Data+2
    cmp #0
beq SourceEarlyIdle_Gate184
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate184:
.a16
.i16
lda.l SVActor_Data+12
    and #255
    cmp #10
beq SourceEarlyIdle_Gate191
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate191:
.a16
.i16
lda.l SVActor_Data+SVActor_Stage
    cmp #0
beq SourceEarlyIdle_Gate199
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate199:
.a16
.i16
lda.l Oam_CurrentSlot
    cmp #80
beq SourceEarlyIdle_Gate206
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate206:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+0
    cmp #0
beq SourceEarlyIdle_Gate213
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate213:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+2
    cmp #40
beq SourceEarlyIdle_Gate220
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate220:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+12
    cmp #278
beq SourceEarlyIdle_Gate227
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate227:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+15
    and #255
    cmp #0
beq SourceEarlyIdle_Gate234
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate234:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+16
    cmp #1
beq SourceEarlyIdle_Gate242
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate242:
.a16
.i16
lda.l SOURCE_PACKET_BUILD_META+0
    cmp #0
beq SourceEarlyIdle_Gate249
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate249:
.a16
.i16
lda.l SOURCE_PACKET_BUILD_META+2
    cmp #40
beq SourceEarlyIdle_Gate256
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate256:
.a16
.i16
lda.l SOURCE_PACKET_BUILD_META+12
    cmp #22
beq SourceEarlyIdle_Gate263
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate263:
.a16
.i16
lda.l SOURCE_PACKET_BUILD_META+14
    cmp #0
beq SourceEarlyIdle_Gate270
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate270:
.a16
.i16
lda.l SOURCE_PACKET_BUILD_META+16
    cmp #1
beq SourceEarlyIdle_Gate277
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate277:
.a16
.i16
lda.l $7E0A00+0+CHAR_HP
    and #255
    cmp #0
bne SourceEarlyIdle_Gate284
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate284:
.a16
.i16
lda.l $7E0A00+0+CHAR_INPUT_DRIVEN
    and #255
    cmp #1
beq SourceEarlyIdle_Gate292
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate292:
.a16
.i16
lda.l $7E0A00+0+CHAR_ROSTER_INDEX
    and #255
    cmp #22
beq SourceEarlyIdle_Gate300
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate300:
.a16
.i16
lda.l $7E0A00+0+CHAR_SELECTED
    and #255
    cmp #3
bcc SourceEarlyIdle_Gate308
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate308:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+32
    cmp #40
beq SourceEarlyIdle_Gate316
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate316:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+34
    cmp #80
beq SourceEarlyIdle_Gate323
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate323:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+44
    cmp #278
beq SourceEarlyIdle_Gate330
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate330:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+47
    and #255
    cmp #0
beq SourceEarlyIdle_Gate337
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate337:
.a16
.i16
lda.l SOURCE_PACKET_ACTIVE_META+48
    cmp #1
beq SourceEarlyIdle_Gate345
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate345:
.a16
.i16
lda.l SOURCE_PACKET_BUILD_META+32
    cmp #40
beq SourceEarlyIdle_Gate352
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate352:
.a16
.i16
lda.l SOURCE_PACKET_BUILD_META+34
    cmp #80
beq SourceEarlyIdle_Gate359
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate359:
.a16
.i16
lda.l SOURCE_PACKET_BUILD_META+44
    cmp #22
beq SourceEarlyIdle_Gate366
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate366:
.a16
.i16
lda.l SOURCE_PACKET_BUILD_META+46
    cmp #0
beq SourceEarlyIdle_Gate373
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate373:
.a16
.i16
lda.l SOURCE_PACKET_BUILD_META+48
    cmp #1
beq SourceEarlyIdle_Gate380
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate380:
.a16
.i16
lda.l $7E0A00+133+CHAR_HP
    and #255
    cmp #0
bne SourceEarlyIdle_Gate387
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate387:
.a16
.i16
lda.l $7E0A00+133+CHAR_INPUT_DRIVEN
    and #255
    cmp #1
beq SourceEarlyIdle_Gate395
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate395:
.a16
.i16
lda.l $7E0A00+133+CHAR_ROSTER_INDEX
    and #255
    cmp #22
beq SourceEarlyIdle_Gate403
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate403:
.a16
.i16
lda.l $7E0A00+133+CHAR_SELECTED
    and #255
    cmp #3
bcc SourceEarlyIdle_Gate411
    brl SourceEarlyIdle_Done
SourceEarlyIdle_Gate411:
.a16
.i16
ldx #0
SourceEarlyIdle_HiCheck:
.a16
.i16
    lda.l Oam_ExpandedHi,x
    and #255
    beq SourceEarlyIdle_HiGood
    brl SourceEarlyIdle_Done
SourceEarlyIdle_HiGood:
.a16
.i16
    inx
    cpx #20
    bcc SourceEarlyIdle_HiCheck
    ldx #0
SourceEarlyIdle_QueueCheck:
.a16
.i16
    lda.l DmaQueue+4,x
    and #64
    beq SourceEarlyIdle_NextQueue
    lda.l DmaQueue+7,x
    and #255
    cmp #$43
    bne SourceEarlyIdle_QueueType
    brl SourceEarlyIdle_Done
SourceEarlyIdle_QueueType:
.a16
.i16
    lda.l DmaQueue+4,x
    and #31
    cmp #1
    bne SourceEarlyIdle_NextQueue
    brl SourceEarlyIdle_Done
SourceEarlyIdle_NextQueue:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourceEarlyIdle_QueueCheck
SourceEarlyIdle_Promote:
.a16
.i16
    lda #1
    sta.l SourcePacket_CopyBusy
    lda #0
    sta.l SourcePacket_NmiPending
    sta.l SourcePacket_ActiveValid
    ldx #(Oam_Buffer & $FFFF)
    ldy #(SOURCE_PACKET_BASE & $FFFF)
    lda #79
    mvn $43,$7E
    ldx #(Oam_Buffer & $FFFF)
    ldy #(SOURCE_PACKET_BUFFER & $FFFF)
    lda #79
    mvn $43,$7E
    ldx #(SOURCE_PACKET_BUILD_META & $FFFF)
    ldy #(SOURCE_PACKET_ACTIVE_META & $FFFF)
    lda #63
    mvn $43,$43
    lda #0
    sta.l SOURCE_PACKET_ACTIVE_META+30
    sta.l SOURCE_PACKET_ACTIVE_META+62
    sta.l SOURCE_PACKET_BASE+512
    sta.l SOURCE_PACKET_BASE+514
    sta.l SOURCE_PACKET_BUFFER+512
    sta.l SOURCE_PACKET_BUFFER+514
    sep #$20
.a8
    sta.l SOURCE_PACKET_BASE+516
    sta.l SOURCE_PACKET_BUFFER+516
    rep #$30
.a16
.i16
    ldx #0
SourceEarlyIdle_SignedX:
.a16
.i16
    lda.l Oam_Buffer,x
    and #255
    sta.l $435600,x
    txa
    clc
    adc #4
    tax
    cpx #80
    bcc SourceEarlyIdle_SignedX
    lda #0
    sta.l SourcePacket_ActiveCamera
    lda #$FFFF
    sta.l SourcePacket_ReadSeq
    lda #1
    sta.l SourcePacket_ActiveValid
    lda #0
    sta.l SourcePacket_CopyBusy
    tcd
    jsl SourcePacket_ForegroundPrepare
    bcc SourceEarlyIdle_Done
    lda.l SourcePacket_RefreshAccepted
    cmp #1
    bne SourceEarlyIdle_Done
    ; A new pose is a real image change, even when its actor foot did not move.
    lda.l Screen_PosX
    sta.l SourcePacket_PendingCamera
    lda #1
    sta.l SourcePacket_Changed
    sta.l SourcePacket_NmiPending
SourceEarlyIdle_Scheduled:
.a16
.i16
SourceEarlyIdle_Done:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    jml SourceEarlyIdle_CaptureReturn
SourceEarlyIdle_End:
