; UNHOOKED current/next presentation building block. Foreground only.
; Next-P1/P2 use held-array bits64/128, distinct from legacy cache-owner
; bits64/128. Existing allocator protects all low8 held bits. Actor-held
; bits1..5 and the reserved-idle bit0 are preserved. No Ready or DMA writes.
; Acquire validates the entire selected pending lease BEFORE adding pins.
; No next lease may already use this player's bit. Publication/adoption and
; its physical acknowledgement protocol are deliberately not implemented here.
SourceNextPins_Acquire:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    lda #0
    pha
    pha
    pha
    pha
    pha
    pha
    pha
    pha
    pha
    pha
    pha
    lda.l $7E46DE
    beq SourceNextPins_G27
    brl SourceNextPins_No
SourceNextPins_G27:
.a16
.i16
    lda.l Game_CampaignId
    and #255
    cmp #3
    beq SourceNextPins_G33
    brl SourceNextPins_No
SourceNextPins_G33:
.a16
.i16
    lda.l Game_State
    beq SourceNextPins_G41
    brl SourceNextPins_No
SourceNextPins_G41:
.a16
.i16
    lda.l Game_StageIndex
    beq SourceNextPins_G47
    brl SourceNextPins_No
SourceNextPins_G47:
.a16
.i16
    lda.l $7E175E
    cmp #2
    beq SourceNextPins_G53
    brl SourceNextPins_No
SourceNextPins_G53:
.a16
.i16
    lda.l $7E1760
    cmp #1
    beq SourceNextPins_G60
    brl SourceNextPins_No
SourceNextPins_G60:
.a16
.i16
    lda.l $7E46DC
    cmp #1
    beq SourceNextPins_G67
    brl SourceNextPins_No
SourceNextPins_G67:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SourceNextPins_G74
    brl SourceNextPins_No
SourceNextPins_G74:
.a16
.i16
    lda.l SourceVisual_CompletedMagic
    cmp #$C04D
    beq SourceNextPins_G81
    brl SourceNextPins_No
SourceNextPins_G81:
.a16
.i16
    lda.l SVActor_Magic
    cmp #$AC19
    beq SourceNextPins_G88
    brl SourceNextPins_No
SourceNextPins_G88:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #2
    bcc SourceNextPins_G95
    brl SourceNextPins_No
SourceNextPins_G95:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    beq SourceNextPins_P1
    tdc
    cmp #$0A85
    beq SourceNextPins_P2DP
    brl SourceNextPins_No
SourceNextPins_P2DP:
.a16
.i16
    lda #128
    sta 7,s
    lda #2
    sta 9,s
    brl SourceNextPins_PlayerReady
SourceNextPins_P1:
.a16
.i16
    tdc
    cmp #$0A00
    beq SourceNextPins_P1DP
    brl SourceNextPins_No
SourceNextPins_P1DP:
.a16
.i16
    lda #64
    sta 7,s
    lda #1
    sta 9,s
SourceNextPins_PlayerReady:
.a16
.i16
    lda CHAR_HP
    and #255
    bne SourceNextPins_G133
    brl SourceNextPins_No
SourceNextPins_G133:
.a16
.i16
    lda CHAR_INPUT_DRIVEN
    and #255
    cmp #1
    beq SourceNextPins_G140
    brl SourceNextPins_No
SourceNextPins_G140:
.a16
.i16
    lda CHAR_SELECTED
    and #255
    cmp #3
    bcc SourceNextPins_G148
    brl SourceNextPins_No
SourceNextPins_G148:
.a16
.i16
    lda CHAR_ROSTER_INDEX
    and #255
    cmp #22
    beq SourceNextPins_G156
    brl SourceNextPins_No
SourceNextPins_G156:
.a16
.i16
    lda CHAR_MAP_INDEX
    and #255
    beq SourceNextPins_G164
    brl SourceNextPins_No
SourceNextPins_G164:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    asl a
    sta 11,s
    cmp.l SourceVisual_Record
    beq SourceNextPins_G178
    brl SourceNextPins_No
SourceNextPins_G178:
.a16
.i16
    tax
    lda.l SourceVisual_State,x
    cmp.l SourceVisual_EntryIndexSaved
    beq SourceNextPins_G185
    brl SourceNextPins_No
SourceNextPins_G185:
.a16
.i16
    lda.l SourceVisual_State+6,x
    cmp #1
    beq SourceNextPins_Mode
    cmp #2
    beq SourceNextPins_G196
    brl SourceNextPins_No
SourceNextPins_G196:
.a16
.i16
SourceNextPins_Mode:
.a16
.i16
    lda.l SourceVisual_State+28,x
    and #255
    beq SourceNextPins_G204
    brl SourceNextPins_No
SourceNextPins_G204:
.a16
.i16
    lda.l SourceVisual_State+29,x
    cmp.l SourceVisual_EntryScratch
    beq SourceNextPins_G211
    brl SourceNextPins_No
SourceNextPins_G211:
.a16
.i16
    lda.l SourceVisual_Key
    cmp.l SourceVisual_EntryScratch
    beq SourceNextPins_G218
    brl SourceNextPins_No
SourceNextPins_G218:
.a16
.i16
    lda.l SourceVisual_Key+2
    cmp.l SourceVisual_EntryScratch+2
    beq SourceNextPins_G225
    brl SourceNextPins_No
SourceNextPins_G225:
.a16
.i16
    lda.l SourceVisual_EntryScratch+1
    and #255
    dec a
    cmp #2
    bcc SourceNextPins_G232
    brl SourceNextPins_No
SourceNextPins_G232:
.a16
.i16
    lda.l SourceVisual_PieceCount
    bne SourceNextPins_G241
    brl SourceNextPins_No
SourceNextPins_G241:
.a16
.i16
    cmp #66
    bcc SourceNextPins_G247
    brl SourceNextPins_No
SourceNextPins_G247:
.a16
.i16
    sta 3,s
    lda.l SourceVisual_EntryScratch+12
    and #255
    cmp 3,s
    beq SourceNextPins_G254
    brl SourceNextPins_No
SourceNextPins_G254:
.a16
.i16
    lda.l SourceVisual_EntryScratch+14
    and #255
    bne SourceNextPins_G262
    brl SourceNextPins_No
SourceNextPins_G262:
.a16
.i16
    cmp #9
    bcc SourceNextPins_G269
    brl SourceNextPins_No
SourceNextPins_G269:
.a16
.i16
    sta 21,s
    lda 11,s
    tax
    lda.l SourceVisual_State+14,x
    cmp 21,s
    beq SourceNextPins_G278
    brl SourceNextPins_No
SourceNextPins_G278:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    clc
    adc.l SourceVisual_ActorSlot
    sta 5,s
    ldx #0
SourceNextPins_EmptyBlocks:
.a16
.i16
    lda.l SVActor_HeldBlocks,x
    and 7,s
    beq SourceNextPins_G299
    brl SourceNextPins_No
SourceNextPins_G299:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #512
    bcc SourceNextPins_EmptyBlocks
    ldx #0
SourceNextPins_EmptyPalettes:
.a16
.i16
    lda.l SVActor_HeldPalettes,x
    and 7,s
    beq SourceNextPins_G316
    brl SourceNextPins_No
SourceNextPins_G316:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourceNextPins_EmptyPalettes
SourceNextPins_Validate:
.a16
.i16
    lda 1,s
    cmp 3,s
    bcc SourceNextPins_HavePiece
    brl SourceNextPins_Reserve
SourceNextPins_HavePiece:
.a16
.i16
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_PieceTable+12,x
    sta 17,s
    lda.l SourceVisual_PieceTable+10,x
    sta 19,s
    lda.l SourceVisual_PieceTable+8,x
    and #255
    cmp 21,s
    bcc SourceNextPins_G348
    brl SourceNextPins_No
SourceNextPins_G348:
.a16
.i16
    clc
    adc 11,s
    tax
    lda.l SourceVisual_State+16,x
    and #255
    bne SourceNextPins_G359
    brl SourceNextPins_No
SourceNextPins_G359:
.a16
.i16
    cmp #9
    bcc SourceNextPins_G366
    brl SourceNextPins_No
SourceNextPins_G366:
.a16
.i16
    dec a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_PaletteCache,x
    cmp 19,s
    beq SourceNextPins_G377
    brl SourceNextPins_No
SourceNextPins_G377:
.a16
.i16
    lda.l SourceVisual_PaletteCache+3,x
    and #255
    cmp #1
    beq SourceNextPins_PaletteState
    cmp #2
    beq SourceNextPins_G389
    brl SourceNextPins_No
SourceNextPins_G389:
.a16
.i16
SourceNextPins_PaletteState:
.a16
.i16
    lda.l SourceVisual_PaletteCache+4,x
    and 9,s
    bne SourceNextPins_G397
    brl SourceNextPins_No
SourceNextPins_G397:
.a16
.i16
    lda 1,s
    clc
    adc 5,s
    tax
    lda.l SourceVisual_ActorPieceMap,x
    and #255
    cmp #64
    bcc SourceNextPins_G408
    brl SourceNextPins_No
SourceNextPins_G408:
.a16
.i16
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_BlockCache,x
    cmp 17,s
    beq SourceNextPins_G420
    brl SourceNextPins_No
SourceNextPins_G420:
.a16
.i16
    lda.l SourceVisual_BlockCache+2,x
    cmp #1
    beq SourceNextPins_BlockState
    cmp #2
    beq SourceNextPins_G431
    brl SourceNextPins_No
SourceNextPins_G431:
.a16
.i16
SourceNextPins_BlockState:
.a16
.i16
    lda.l SourceVisual_BlockCache+4,x
    and 9,s
    bne SourceNextPins_G439
    brl SourceNextPins_No
SourceNextPins_G439:
.a16
.i16
    lda 1,s
    inc a
    sta 1,s
    brl SourceNextPins_Validate
SourceNextPins_Reserve:
.a16
.i16
    lda #0
    sta 1,s
SourceNextPins_ReservePiece:
.a16
.i16
    lda 1,s
    cmp 3,s
    bcc SourceNextPins_PinPiece
    brl SourceNextPins_Yes
SourceNextPins_PinPiece:
.a16
.i16
    clc
    adc 5,s
    tax
    lda.l SourceVisual_ActorPieceMap,x
    and #255
    asl a
    asl a
    asl a
    tax
    lda.l SVActor_HeldBlocks,x
    ora 7,s
    sta.l SVActor_HeldBlocks,x
    lda 1,s
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_PieceTable+8,x
    and #255
    clc
    adc 11,s
    tax
    lda.l SourceVisual_State+16,x
    and #255
    dec a
    asl a
    asl a
    asl a
    tax
    lda.l SVActor_HeldPalettes,x
    ora 7,s
    sta.l SVActor_HeldPalettes,x
    lda 1,s
    inc a
    sta 1,s
    brl SourceNextPins_ReservePiece
SourceNextPins_Yes:
.a16
.i16
    tsc
    clc
    adc #22
    tcs
    ply
    plx
    pla
    plp
    sec
    rtl
SourceNextPins_No:
.a16
.i16
    tsc
    clc
    adc #22
    tcs
    ply
    plx
    pla
    plp
    clc
    rtl
; A=player0/1. Only unpublished cancellation or acknowledged adoption.
; Caller must not drop the sole pin of a physically displayed next packet.
SourceNextPins_ReleaseUnpublished:
.a16
.i16
    php
    rep #$30
    pha
    phx
    cmp #2
    bcc SourceNextPins_ReleaseSlot
    brl SourceNextPins_ReleaseNo
SourceNextPins_ReleaseSlot:
.a16
.i16
    cmp #0
    beq SourceNextPins_ReleaseP1
    lda #$FF7F
    bra SourceNextPins_ReleaseMask
SourceNextPins_ReleaseP1:
.a16
.i16
    lda #$FFBF
SourceNextPins_ReleaseMask:
.a16
.i16
    pha
    lda.l $7E46DE
    beq SourceNextPins_ReleaseForeground
    brl SourceNextPins_ReleasePopNo
SourceNextPins_ReleaseForeground:
.a16
.i16
    lda.l Game_CampaignId
    and #255
    cmp #3
    beq SourceNextPins_ReleaseCampaign
    brl SourceNextPins_ReleasePopNo
SourceNextPins_ReleaseCampaign:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SourceNextPins_ReleaseMagic
    brl SourceNextPins_ReleasePopNo
SourceNextPins_ReleaseMagic:
.a16
.i16
    lda.l SVActor_Magic
    cmp #$AC19
    beq SourceNextPins_ReleaseOwned
    brl SourceNextPins_ReleasePopNo
SourceNextPins_ReleaseOwned:
.a16
.i16
    ldx #0
SourceNextPins_ReleaseBlocks:
.a16
.i16
    lda.l SVActor_HeldBlocks,x
    and 1,s
    sta.l SVActor_HeldBlocks,x
    txa
    clc
    adc #8
    tax
    cpx #512
    bcc SourceNextPins_ReleaseBlocks
    ldx #0
SourceNextPins_ReleasePalettes:
.a16
.i16
    lda.l SVActor_HeldPalettes,x
    and 1,s
    sta.l SVActor_HeldPalettes,x
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourceNextPins_ReleasePalettes
    pla
    plx
    pla
    plp
    sec
    rtl
SourceNextPins_ReleasePopNo:
.a16
.i16
    pla
SourceNextPins_ReleaseNo:
.a16
.i16
    plx
    pla
    plp
    clc
    rtl
SourceNextPins_End:
