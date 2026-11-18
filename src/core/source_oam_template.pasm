; Exact player OAM memoization; no resource, input, world or DMA ownership.
; Slot0 $436000..66FF, slot1 $436700..6DFF; controls $436E00..6EFF.
; Header64 + piece bytes1040 + OAM512 + expandedHi128 =1744 <1792.
; Existing completed validation and entire scene/pin retirement remain original.
SourceTemplate_Control = $436E00
SourceTemplate_Header = $436E40
SourceTemplate_Init:
.a16
.i16
.a16
.i16
    sta.l SVActor_Magic
    php
    rep #$30
    pha
    lda #0
    sta.l $436000
    sta.l $436700
    sta.l SourceTemplate_Control
    sta.l SourceTemplate_Control+2
    pla
    plp
    rtl
; C=eligible, A=private slot offset. No private reads before all scope gates.
SourceTemplate_Scope:
.a16
.i16
.a16
.i16
    lda.l Game_CampaignId
    and #255
    cmp #3
    beq SourceTemplate_G29
    brl SourceTemplate_ScopeNo
SourceTemplate_G29:
.a16
.i16
    lda.l Game_State
    cmp #0
    beq SourceTemplate_G34
    brl SourceTemplate_ScopeNo
SourceTemplate_G34:
.a16
.i16
    lda.l Game_StageIndex
    cmp #0
    beq SourceTemplate_G39
    brl SourceTemplate_ScopeNo
SourceTemplate_G39:
.a16
.i16
    lda.l $7E175E
    cmp #2
    beq SourceTemplate_G44
    brl SourceTemplate_ScopeNo
SourceTemplate_G44:
.a16
.i16
    lda.l $7E1760
    cmp #1
    beq SourceTemplate_G49
    brl SourceTemplate_ScopeNo
SourceTemplate_G49:
.a16
.i16
    lda.l $7E46DC
    cmp #1
    beq SourceTemplate_G54
    brl SourceTemplate_ScopeNo
SourceTemplate_G54:
.a16
.i16
    lda.l $7E46DE
    cmp #0
    beq SourceTemplate_G59
    brl SourceTemplate_ScopeNo
SourceTemplate_G59:
.a16
.i16
    lda.l SVActor_Magic
    cmp #44057
    beq SourceTemplate_G64
    brl SourceTemplate_ScopeNo
SourceTemplate_G64:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #6752
    beq SourceTemplate_G69
    brl SourceTemplate_ScopeNo
SourceTemplate_G69:
.a16
.i16
    lda.l Stage_Mirror
    and #255
    beq SourceTemplate_NoMirror
    brl SourceTemplate_ScopeNo
SourceTemplate_NoMirror:
.a16
.i16
    tdc
    cmp #$0A00
    bne SourceTemplate_ScopeP2
    lda #$6000
    sec
    rts
SourceTemplate_ScopeP2:
.a16
.i16
    cmp #$0A85
    bne SourceTemplate_ScopeNo
    lda #$6700
    sec
    rts
SourceTemplate_ScopeNo:
.a16
.i16
    clc
    rts
SourceTemplate_Try:
.a16
.i16
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    cld
    jsr SourceTemplate_Scope
    bcs SourceTemplate_G99
    brl SourceTemplate_No
SourceTemplate_G99:
.a16
.i16
    sta.l SourceTemplate_Control
    lda #0
    sta.l SourceTemplate_Control+2
    sta.l SourceTemplate_Control+14
    lda.l Oam_CurrentSlot
    sta.l SourceTemplate_Control+4
    and #3
    beq SourceTemplate_G108
    brl SourceTemplate_No
SourceTemplate_G108:
.a16
.i16
    lda.l Oam_CurrentSlot
    cmp #513
    bcc SourceTemplate_G113
    brl SourceTemplate_No
SourceTemplate_G113:
.a16
.i16
    lda.l SourceVisual_PieceCount
    cmp #66
    bcc SourceTemplate_G118
    brl SourceTemplate_No
SourceTemplate_G118:
.a16
.i16
    lda #$43
    sep #$20
.a8
    pha
    plb
    rep #$30
.a16
.i16
    lda #0
    ldx #0
SourceTemplate_HeaderClear:
.a16
.i16
    sta.w $6E40,x
    inx
    inx
    cpx #64
    bcc SourceTemplate_HeaderClear
    lda.l SourceVisual_PieceCount
    sta.w $6E44
    lda.l Game_StageIndex
    sta.w $6E46
    lda.l SourceVisual_EmitBaseX
    sta.w $6E48
    lda.l SourceVisual_EmitBaseY
    sta.w $6E4A
    lda.l SourceVisual_BaseTile
    sta.w $6E50
    lda.l SourceVisual_EmitBoundsMode
    sta.w $6E52
    lda CHAR_POS_Y
    sta.w $6E4C
    lda CHAR_FACING_LEFT
    and #255
    sta.w $6E4E
    lda.l Stage_Mirror
    and #255
    sta.w $6E56
    sep #$20
.a8
    lda #$FF
    jsl StageFp_BG2OamAttr
    rep #$30
.a16
.i16
    and #255
    sta.w $6E54
    ldx #0
SourceTemplate_HeaderEntry:
.a16
.i16
    lda.l SourceVisual_EntryScratch,x
    sta.w $6E58,x
    inx
    inx
    cpx #24
    bcc SourceTemplate_HeaderEntry
    lda.l SourceVisual_Record
    clc
    adc #16
    tax
    ldy #0
SourceTemplate_HeaderPalette:
.a16
.i16
    lda.l SourceVisual_State,x
    sta.w $6E70,y
    inx
    inx
    iny
    iny
    cpy #8
    bcc SourceTemplate_HeaderPalette
    tdc
    sta.w $6E78
    lda #1
    sta.l SourceTemplate_Control+14
    lda.l SourceTemplate_Control
    tax
    lda.w $0000,x
    cmp #$534D
    beq SourceTemplate_G194
    brl SourceTemplate_No
SourceTemplate_G194:
.a16
.i16
    inx
    inx
    inx
    inx
    ldy #4
SourceTemplate_CompareHeader:
.a16
.i16
    cpy #8
    bne SourceTemplate_HeaderNotPosition
    txa
    clc
    adc #6
    tax
    ldy #14
SourceTemplate_HeaderNotPosition:
.a16
.i16
    lda.w $0000,x
    cmp.w $6E40,y
    beq SourceTemplate_G205
    brl SourceTemplate_No
SourceTemplate_G205:
.a16
.i16
    inx
    inx
    iny
    iny
    cpy #64
    bcc SourceTemplate_CompareHeader
    lda.l SourceVisual_PieceCount
    asl a
    asl a
    asl a
    asl a
    sta.l SourceTemplate_Control+6
    lda.l SourceTemplate_Control
    clc
    adc #64
    tay
    ldx #0
SourceTemplate_ComparePieces:
.a16
.i16
    txa
    cmp.l SourceTemplate_Control+6
    beq SourceTemplate_PiecesEqual
    lda.l SourceVisual_PieceTable,x
    cmp.w $0000,y
    beq SourceTemplate_G231
    brl SourceTemplate_No
SourceTemplate_G231:
.a16
.i16
    inx
    inx
    iny
    iny
    bra SourceTemplate_ComparePieces
SourceTemplate_PiecesEqual:
.a16
.i16
    lda.l SourceTemplate_Control
    tax
    lda.w $0002,x
    bne SourceTemplate_LengthNonzero
    brl SourceTemplate_No
SourceTemplate_LengthNonzero:
.a16
.i16
    cmp #513
    bcc SourceTemplate_G245
    brl SourceTemplate_No
SourceTemplate_G245:
.a16
.i16
    sta.l SourceTemplate_Control+8
    and #3
    beq SourceTemplate_G250
    brl SourceTemplate_No
SourceTemplate_G250:
.a16
.i16
    lda.l SourceVisual_PieceCount
    asl a
    asl a
    cmp.l SourceTemplate_Control+8
    beq SourceTemplate_ExactRowCount
    brl SourceTemplate_No
SourceTemplate_ExactRowCount:
.a16
.i16
    lda.l SourceTemplate_Control+8
    clc
    adc.l Oam_CurrentSlot
    bcc SourceTemplate_CapacityNoCarry
    brl SourceTemplate_No
SourceTemplate_CapacityNoCarry:
.a16
.i16
    cmp #513
    bcc SourceTemplate_G258
    brl SourceTemplate_No
SourceTemplate_G258:
.a16
.i16
    sta.l SourceTemplate_Control+10
    lda.l SourceTemplate_Control
    tax
    lda.l SourceVisual_EmitBaseX
    sec
    sbc.w $0008,x
    sta.l SourceTemplate_Control+16
    lda.l SourceVisual_EmitBaseY
    sec
    sbc.w $000A,x
    sta.l SourceTemplate_Control+18
    lda #0
    sta.l SourceTemplate_Control+20
    lda.l SourceTemplate_Control
    clc
    adc #$450
    tay
SourceTemplate_CheckRelative:
.a16
.i16
    jsr SourceTemplate_Position
    bcs SourceTemplate_RelativeVisible
    brl SourceTemplate_No
SourceTemplate_RelativeVisible:
.a16
.i16
    iny
    iny
    iny
    iny
    lda.l SourceTemplate_Control+20
    inc a
    sta.l SourceTemplate_Control+20
    cmp.l SourceVisual_PieceCount
    bcc SourceTemplate_CheckRelative
    lda #0
    sta.l SourceTemplate_Control+20
    lda.l SourceTemplate_Control
    clc
    adc #$450
    tay
SourceTemplate_CopyOam:
.a16
.i16
    jsr SourceTemplate_Position
    pha
    lda.l SourceTemplate_Control+20
    asl a
    asl a
    clc
    adc.l Oam_CurrentSlot
    tax
    pla
    sta.l Oam_Buffer,x
    lda.w $0002,y
    sta.l Oam_Buffer+2,x
    txa
    lsr a
    lsr a
    tax
    sep #$20
.a8
    lda.l SourceTemplate_Control+30
    sta.l Oam_ExpandedHi,x
    rep #$30
.a16
.i16
    iny
    iny
    iny
    iny
    lda.l SourceTemplate_Control+20
    inc a
    sta.l SourceTemplate_Control+20
    cmp.l SourceVisual_PieceCount
    bcc SourceTemplate_CopyOam
    lda.l SourceTemplate_Control+10
    sta.l Oam_CurrentSlot
    lda.l SourceTemplate_Control+8
    lsr a
    lsr a
    sta.l SourceVisual_VisiblePieces
    lda.l SourceVisual_PieceCount
    sta.l SourceVisual_PieceIndex
    lda #1
    sta.l SourceTemplate_Control+2
    plb
    ply
    plx
    pla
    plp
    sec
    rtl
SourceTemplate_No:
.a16
.i16
.a16
.i16
    plb
    ply
    plx
    pla
    plp
    rep #$30
.a16
.i16
    lda #0
    sta.l SourceVisual_VisiblePieces
    sta.l SourceVisual_PieceIndex
    clc
    rtl
SourceTemplate_Finish:
.a16
.i16
.a16
.i16
    jsl SourcePacket_EmitFinish
    php
    rep #$30
    pha
    phx
    phy
    phb
    cld
    jsr SourceTemplate_Scope
    bcs SourceTemplate_G353
    brl SourceTemplate_FinishDone
SourceTemplate_G353:
.a16
.i16
    cmp.l SourceTemplate_Control
    beq SourceTemplate_G357
    brl SourceTemplate_FinishDone
SourceTemplate_G357:
.a16
.i16
    lda.l SourceTemplate_Control+14
    cmp #1
    beq SourceTemplate_HeaderWasPrepared
    brl SourceTemplate_FinishDone
SourceTemplate_HeaderWasPrepared:
.a16
.i16
    lda.l SourceTemplate_Control+2
    beq SourceTemplate_G361
    brl SourceTemplate_FinishDone
SourceTemplate_G361:
.a16
.i16
    lda.l Oam_CurrentSlot
    cmp #513
    bcc SourceTemplate_G366
    brl SourceTemplate_FinishDone
SourceTemplate_G366:
.a16
.i16
    sec
    sbc.l SourceTemplate_Control+4
    bcs SourceTemplate_G371
    brl SourceTemplate_FinishDone
SourceTemplate_G371:
.a16
.i16
    cmp #0
    bne SourceTemplate_G375
    brl SourceTemplate_FinishDone
SourceTemplate_G375:
.a16
.i16
    sta.l SourceTemplate_Control+8
    lda.l SourceVisual_PieceCount
    asl a
    asl a
    cmp.l SourceTemplate_Control+8
    beq SourceTemplate_AllPiecesCaptured
    brl SourceTemplate_FinishDone
SourceTemplate_AllPiecesCaptured:
.a16
.i16
    lda.l SourceTemplate_Control+8
    and #3
    beq SourceTemplate_G380
    brl SourceTemplate_FinishDone
SourceTemplate_G380:
.a16
.i16
    lda #$43
    sep #$20
.a8
    pha
    plb
    rep #$30
.a16
.i16
    lda.l SourceTemplate_Control
    tax
    lda #0
    sta.w $0000,x
    lda.l SourceTemplate_Control+8
    sta.w $0002,x
    inx
    inx
    inx
    inx
    ldy #4
SourceTemplate_StoreHeader:
.a16
.i16
    lda.w $6E40,y
    sta.w $0000,x
    inx
    inx
    iny
    iny
    cpy #64
    bcc SourceTemplate_StoreHeader
    lda.l SourceVisual_PieceCount
    asl a
    asl a
    asl a
    asl a
    sta.l SourceTemplate_Control+6
    lda.l SourceTemplate_Control
    clc
    adc #64
    tay
    ldx #0
SourceTemplate_StorePieces:
.a16
.i16
    txa
    cmp.l SourceTemplate_Control+6
    beq SourceTemplate_StoredPieces
    lda.l SourceVisual_PieceTable,x
    sta.w $0000,y
    inx
    inx
    iny
    iny
    bra SourceTemplate_StorePieces
SourceTemplate_StoredPieces:
.a16
.i16
    lda.l SourceTemplate_Control
    clc
    adc #$450
    tay
    lda.l SourceTemplate_Control+4
    tax
SourceTemplate_StoreOam:
.a16
.i16
    lda.l Oam_Buffer,x
    sta.w $0000,y
    inx
    inx
    iny
    iny
    txa
    cmp.l Oam_CurrentSlot
    bcc SourceTemplate_StoreOam
    lda.l Oam_CurrentSlot
    lsr a
    lsr a
    sta.l SourceTemplate_Control+12
    lda.l SourceTemplate_Control+4
    lsr a
    lsr a
    tax
    lda.l SourceTemplate_Control
    clc
    adc #$650
    tay
    sep #$20
.a8
SourceTemplate_StoreHi:
.a8
.i16
    lda.l Oam_ExpandedHi,x
    sta.w $0000,y
    inx
    iny
    rep #$20
.a16
    txa
    cmp.l SourceTemplate_Control+12
    sep #$20
.a8
    bcc SourceTemplate_StoreHi
    rep #$30
.a16
.i16
    lda.l SourceTemplate_Control
    tax
    lda #$534D
    sta.w $0000,x
SourceTemplate_FinishDone:
.a16
.i16
.a16
.i16
    plb
    ply
    plx
    pla
    plp
    rtl

; Read-only geometry preflight/replay. Y names a cached OAM row. Cached
; Hi bit0 reconstructs signed9bit X; emitted Y>=224 is negative screen Y.
; One normal row corresponds to each exact matching source-piece record.
SourceTemplate_Position:
.a16
.i16
    lda.l SourceTemplate_Control+20
    asl a
    asl a
    asl a
    asl a
    sta.l SourceTemplate_Control+28
    lda.l SourceTemplate_Control
    clc
    adc #$650
    clc
    adc.l SourceTemplate_Control+20
    tax
    lda.w $0000,x
    and #3
    sta.l SourceTemplate_Control+30
    and #1
    beq SourceTemplate_PositiveOldX
    lda.w $0000,y
    and #255
    ora #$FF00
    bra SourceTemplate_OldXReady
SourceTemplate_PositiveOldX:
.a16
.i16
    lda.w $0000,y
    and #255
SourceTemplate_OldXReady:
.a16
.i16
    clc
    adc.l SourceTemplate_Control+16
    sta.l SourceTemplate_Control+22
    bmi SourceTemplate_NegativeNewX
    cmp #256
    bcc SourceTemplate_NewXVisible
    brl SourceTemplate_PositionNo
SourceTemplate_NegativeNewX:
.a16
.i16
    ldx.w $6E1C
    clc
    adc.l SourceVisual_PieceTable+4,x
    bmi SourceTemplate_PositionNo
    beq SourceTemplate_PositionNo
SourceTemplate_NewXVisible:
.a16
.i16
    lda.w $0000,y
    xba
    and #255
    cmp #224
    bcc SourceTemplate_OldYReady
    ora #$FF00
SourceTemplate_OldYReady:
.a16
.i16
    clc
    adc.l SourceTemplate_Control+18
    sta.l SourceTemplate_Control+24
    bmi SourceTemplate_NegativeNewY
    cmp #224
    bcc SourceTemplate_NewYVisible
    bra SourceTemplate_PositionNo
SourceTemplate_NegativeNewY:
.a16
.i16
    ldx.w $6E1C
    clc
    adc.l SourceVisual_PieceTable+6,x
    bmi SourceTemplate_PositionNo
    beq SourceTemplate_PositionNo
SourceTemplate_NewYVisible:
.a16
.i16
    lda.l SourceTemplate_Control+30
    and #2
    sta.l SourceTemplate_Control+30
    lda.l SourceTemplate_Control+22
    bpl SourceTemplate_NewXHiReady
    lda.l SourceTemplate_Control+30
    ora #1
    sta.l SourceTemplate_Control+30
SourceTemplate_NewXHiReady:
.a16
.i16
    lda.l SourceTemplate_Control+22
    and #255
    sta.l SourceTemplate_Control+26
    lda.l SourceTemplate_Control+24
    and #255
    xba
    ora.l SourceTemplate_Control+26
    sec
    rts
SourceTemplate_PositionNo:
.a16
.i16
    clc
    rts

SourceTemplate_End:
.a16
.i16
