; Exact prior whole-packet P2 picture reuse, after the unchanged per-piece
; resource validator and completed entry/lease/piece restoration. No pixel
; duplicate: immutable SOURCE_PACKET_BASE remains the only cached image.
; This 64-byte build/active pair is inside audited unused bytes1072..1135
; of raw-metadata actor row0; MetaSave writes at most bytes0..1071.
SourceP2_Build = $433430
SourceP2_Active = $433450
; Foreground actor emissions are serialized; share the NPC copier scratch.
SourceP2_Scope = SourceNpc_Scope
SourceP2_Init = SourceNpc_Init
SourceP2_Index = SourceNpc_Index
SourceP2_Length = SourceNpc_Length
SourceP2_SourceBegin = SourceNpc_SourceBegin
SourceP2_HiPointer = SourceNpc_HiPointer
SourceP2_HiBits = SourceNpc_HiBits
SourceP2_HiLeft = SourceNpc_HiLeft
SourceP2_Remaining = SourceNpc_Remaining
SourceP2_DestBegin = SourceNpc_DestBegin
SourceP2_BuildingSlot = SourceNpc_BuildingSlot
SourceP2_Select:
.a16
.i16
    lda.l SVActor_Slot
    cmp #1
    bne SourceP2_Select__no
    tdc
    cmp #$0A85
    bne SourceP2_Select__no
    lda #0
    sta.l SourceP2_Index
    tax
    sec
    rts
SourceP2_Select__no:
.a16
.i16
    clc
    rts
SourceP2_FillFingerprint:
.a16
.i16
    lda CHAR_POS_X
    sta.l SourceP2_Build+4,x
    lda CHAR_POS_Y
    sta.l SourceP2_Build+6,x
    lda CHAR_FACING_LEFT
    and #$00FF
    sta.l SourceP2_Build+8,x
    lda.l Screen_PosX
    sta.l SourceP2_Build+10,x
    lda.l SVActor_LeaseScratch
    sta.l SourceP2_Build+12,x
    lda.l Game_StageIndex
    sta.l SourceP2_Build+16,x
    lda CHAR_SELECTED
    and #$00FF
    sta.l SourceP2_Build+18,x
    lda CHAR_THROW_ZPOS
    sta.l SourceP2_Build+20,x
    lda.l SourceVisual_BaseTile
    sta.l SourceP2_Build+22,x
    lda.l SourceVisual_EntryScratch+2
    sta.l SourceP2_Build+28,x
    lda.l SourceVisual_PieceCount
    sta.l SourceP2_Build+30,x
    lda.l SVActor_Slot
    dec a
    asl a
    tax
    lda.l SVActor_Captures,x
    pha
    lda.l SourceP2_Index
    tax
    pla
    sta.l SourceP2_Build+14,x
    rts
SourceP2_TryPicture:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    phd
    lda #$FFFF
    sta.l SourceP2_BuildingSlot
    jsr SourceP2_Scope
bcs SourceP2_TryPicture__scope
    brl SourceP2_TryPicture__miss
SourceP2_TryPicture__scope:
.a16
.i16
    jsr SourceP2_Init
    jsr SourceP2_Select
bcs SourceP2_TryPicture__slot
    brl SourceP2_TryPicture__miss
SourceP2_TryPicture__slot:
.a16
.i16
    lda #0
    sta.l SourceP2_Build+24,x
    lda.l SourceVisual_ServiceOnly
    cmp #0
beq SourceP2_TryPicture__eligible0
    brl SourceP2_TryPicture__miss
SourceP2_TryPicture__eligible0:
.a16
.i16
    lda.l Stage_Mirror
    and #$00FF
beq SourceP2_TryPicture__eligible1
    brl SourceP2_TryPicture__miss
SourceP2_TryPicture__eligible1:
.a16
.i16
    lda CHAR_HP
    and #$00FF
bne SourceP2_TryPicture__eligible2
    brl SourceP2_TryPicture__miss
SourceP2_TryPicture__eligible2:
.a16
.i16
    lda CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
beq SourceP2_TryPicture__eligible3
    brl SourceP2_TryPicture__miss
SourceP2_TryPicture__eligible3:
.a16
.i16
    lda CHAR_SELECTED
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
bne SourceP2_TryPicture__eligible4
    brl SourceP2_TryPicture__miss
SourceP2_TryPicture__eligible4:
.a16
.i16
    lda.l SourceVisual_PieceCount
bne SourceP2_TryPicture__eligible5
    brl SourceP2_TryPicture__miss
SourceP2_TryPicture__eligible5:
.a16
.i16
    cmp #66
bcc SourceP2_TryPicture__eligible6
    brl SourceP2_TryPicture__miss
SourceP2_TryPicture__eligible6:
.a16
.i16
    jsl StageBoundsHost_Normal
bcs SourceP2_TryPicture__eligible7
    brl SourceP2_TryPicture__miss
SourceP2_TryPicture__eligible7:
.a16
.i16
    jsl StageBounds_Row
    lda.l StageBounds_State,x
beq SourceP2_TryPicture__eligible8
    brl SourceP2_TryPicture__miss
SourceP2_TryPicture__eligible8:
.a16
.i16
    lda.l SourceP2_Index
    tax
    lda.l SVActor_Slot
    sta.l SourceP2_BuildingSlot
    lda.l $7E53A0
    sta.l SourceP2_Build,x
    jsr SourceP2_FillFingerprint
    lda.l SourcePacket_ActiveValid
    cmp #1
beq SourceP2_TryPicture__active
    brl SourceP2_TryPicture__miss
SourceP2_TryPicture__active:
.a16
.i16
    lda.l SourcePacket_CopyBusy
beq SourceP2_TryPicture__unlocked
    brl SourceP2_TryPicture__miss
SourceP2_TryPicture__unlocked:
.a16
.i16
    lda.l SourceP2_Active+24,x
    cmp #1
beq SourceP2_TryPicture__picture
    brl SourceP2_TryPicture__miss
SourceP2_TryPicture__picture:
.a16
.i16
    lda.l Nmi_FrameCounter
    sec
    sbc.l SourceP2_Active+26,x
    cmp #64
bcc SourceP2_TryPicture__recent
    brl SourceP2_TryPicture__miss
SourceP2_TryPicture__recent:
.a16
.i16
    lda #10
    sta.l SourceP2_Remaining
    inx
    inx
    inx
    inx
SourceP2_TryPicture__fingerprint:
.a16
.i16
    lda.l SourceP2_Build,x
    cmp.l SourceP2_Active,x
beq SourceP2_TryPicture__sameword
    brl SourceP2_TryPicture__miss
SourceP2_TryPicture__sameword:
.a16
.i16
    inx
    inx
    lda.l SourceP2_Remaining
    dec a
    sta.l SourceP2_Remaining
    bne SourceP2_TryPicture__fingerprint
    lda.l SourceP2_Index
    tax
    lda.l SourceP2_Build+28,x
    cmp.l SourceP2_Active+28,x
beq SourceP2_TryPicture__same28
    brl SourceP2_TryPicture__miss
SourceP2_TryPicture__same28:
.a16
.i16
    lda.l SourceP2_Build+30,x
    cmp.l SourceP2_Active+30,x
beq SourceP2_TryPicture__same30
    brl SourceP2_TryPicture__miss
SourceP2_TryPicture__same30:
.a16
.i16
    lda.l SourceP2_Active,x
    sta.l SourceP2_SourceBegin
    and #3
beq SourceP2_TryPicture__aligned0
    brl SourceP2_TryPicture__miss
SourceP2_TryPicture__aligned0:
.a16
.i16
    lda.l SourceP2_Active+2,x
    and #3
beq SourceP2_TryPicture__aligned1
    brl SourceP2_TryPicture__miss
SourceP2_TryPicture__aligned1:
.a16
.i16
    lda.l SourceP2_Active+2,x
    cmp #513
bcc SourceP2_TryPicture__source_end
    brl SourceP2_TryPicture__miss
SourceP2_TryPicture__source_end:
.a16
.i16
    sec
    sbc.l SourceP2_SourceBegin
bcs SourceP2_TryPicture__ordered
    brl SourceP2_TryPicture__miss
SourceP2_TryPicture__ordered:
.a16
.i16
    cmp #0
bne SourceP2_TryPicture__nonempty
    brl SourceP2_TryPicture__miss
SourceP2_TryPicture__nonempty:
.a16
.i16
    cmp #261
bcc SourceP2_TryPicture__length
    brl SourceP2_TryPicture__miss
SourceP2_TryPicture__length:
.a16
.i16
    sta.l SourceP2_Length
    lda.l $7E53A0
    sta.l SourceP2_DestBegin
    and #3
beq SourceP2_TryPicture__dest_aligned
    brl SourceP2_TryPicture__miss
SourceP2_TryPicture__dest_aligned:
.a16
.i16
    lda.l SourceP2_DestBegin
    cmp #513
    bcc SourceP2_TryPicture__dest_bounded
    brl SourceP2_TryPicture__miss
SourceP2_TryPicture__dest_bounded:
.a16
.i16
    lda.l SourceP2_DestBegin
    clc
    adc.l SourceP2_Length
    cmp #513
bcc SourceP2_TryPicture__capacity
    brl SourceP2_TryPicture__miss
SourceP2_TryPicture__capacity:
.a16
.i16
    ldx #0
SourceP2_TryPicture__queue:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    beq SourceP2_TryPicture__queue_next
    lda.l DmaQueue+4,x
    and #DMA_OPT_REVERSE
beq SourceP2_TryPicture__not_reverse
    brl SourceP2_TryPicture__miss
SourceP2_TryPicture__not_reverse:
.a16
.i16
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$43
bne SourceP2_TryPicture__not_private
    brl SourceP2_TryPicture__miss
SourceP2_TryPicture__not_private:
.a16
.i16
SourceP2_TryPicture__queue_next:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourceP2_TryPicture__queue
    lda.l SourceP2_SourceBegin
    clc
    adc #(SOURCE_PACKET_BASE&$FFFF)
    tax
    lda.l SourceP2_DestBegin
    clc
    adc #(Oam_Buffer&$FFFF)
    tay
    lda.l SourceP2_Length
    dec a
    mvn $7E,$43
    lda.l SourceP2_SourceBegin
    lsr a
    lsr a
    lsr a
    lsr a
    sta.l SourceP2_HiPointer
    tax
    lda.l SOURCE_PACKET_BASE+512,x
    and #$00FF
    sta.l SourceP2_HiBits
    lda.l SourceP2_SourceBegin
    and #15
    lsr a
    lsr a
    tax
    txa
    eor #$FFFF
    inc a
    clc
    adc #4
    sta.l SourceP2_HiLeft
SourceP2_TryPicture__shift:
.a16
.i16
    cpx #0
    beq SourceP2_TryPicture__shift_done
    lda.l SourceP2_HiBits
    lsr a
    lsr a
    sta.l SourceP2_HiBits
    dex
    bra SourceP2_TryPicture__shift
SourceP2_TryPicture__shift_done:
.a16
.i16
    lda.l SourceP2_DestBegin
    lsr a
    lsr a
    tay
    lda.l SourceP2_Length
    lsr a
    lsr a
    sta.l SourceP2_Remaining
    sta.l SourceVisual_VisiblePieces
SourceP2_TryPicture__hi:
.a16
.i16
    lda.l SourceP2_HiBits
    and #3
    sep #$20
.a8
    sta.w $5320,y ; DB7E, actual linked Oam_ExpandedHi low address
    rep #$30
.a16
.i16
    lda.l SourceP2_HiBits
    lsr a
    lsr a
    sta.l SourceP2_HiBits
    iny
    lda.l SourceP2_Remaining
    dec a
    sta.l SourceP2_Remaining
    beq SourceP2_TryPicture__copied
    lda.l SourceP2_HiLeft
    dec a
    sta.l SourceP2_HiLeft
    bne SourceP2_TryPicture__hi
    lda #4
    sta.l SourceP2_HiLeft
    lda.l SourceP2_HiPointer
    inc a
    sta.l SourceP2_HiPointer
    tax
    lda.l SOURCE_PACKET_BASE+512,x
    and #$00FF
    sta.l SourceP2_HiBits
    bra SourceP2_TryPicture__hi
SourceP2_TryPicture__copied:
.a16
.i16
    lda.l SourceP2_DestBegin
    clc
    adc.l SourceP2_Length
    sta.l $7E53A0
    lda CHAR_POS_X
    sec
    sbc.l Screen_PosX
    sta.l SourceVisual_EmitBaseX
    lda CHAR_POS_Y
    sta.l SourceVisual_EmitBaseY
    lda.l SourceVisual_PieceCount
    sta.l SourceVisual_PieceIndex
SourceP2_TryPicture__hit:
.a16
.i16
    rep #$30
    pld
    plb
    ply
    plx
    pla
    plp
    sec
    rtl
SourceP2_TryPicture__miss:
.a16
.i16
    rep #$30
    pld
    plb
    ply
    plx
    pla
    plp
    clc
    rtl
SourceP2_RecordPicture:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    phd
    jsr SourceP2_Scope
bcs SourceP2_RecordPicture__scope
    brl SourceP2_RecordPicture__done
SourceP2_RecordPicture__scope:
.a16
.i16
    lda.l SourceP2_BuildingSlot
    cmp.l SVActor_Slot
beq SourceP2_RecordPicture__building
    brl SourceP2_RecordPicture__done
SourceP2_RecordPicture__building:
.a16
.i16
    jsr SourceP2_Select
bcs SourceP2_RecordPicture__slot
    brl SourceP2_RecordPicture__done
SourceP2_RecordPicture__slot:
.a16
.i16
    lda CHAR_POS_X
    cmp.l SourceP2_Build+4,x
beq SourceP2_RecordPicture__stable0
    brl SourceP2_RecordPicture__done
SourceP2_RecordPicture__stable0:
.a16
.i16
    lda CHAR_POS_Y
    cmp.l SourceP2_Build+6,x
beq SourceP2_RecordPicture__stable1
    brl SourceP2_RecordPicture__done
SourceP2_RecordPicture__stable1:
.a16
.i16
    lda CHAR_FACING_LEFT
    and #$00FF
    cmp.l SourceP2_Build+8,x
beq SourceP2_RecordPicture__stable2
    brl SourceP2_RecordPicture__done
SourceP2_RecordPicture__stable2:
.a16
.i16
    lda.l Screen_PosX
    cmp.l SourceP2_Build+10,x
beq SourceP2_RecordPicture__stable3
    brl SourceP2_RecordPicture__done
SourceP2_RecordPicture__stable3:
.a16
.i16
    lda.l SVActor_LeaseScratch
    cmp.l SourceP2_Build+12,x
beq SourceP2_RecordPicture__stable4
    brl SourceP2_RecordPicture__done
SourceP2_RecordPicture__stable4:
.a16
.i16
    lda.l Game_StageIndex
    cmp.l SourceP2_Build+16,x
beq SourceP2_RecordPicture__stable5
    brl SourceP2_RecordPicture__done
SourceP2_RecordPicture__stable5:
.a16
.i16
    lda CHAR_SELECTED
    and #$00FF
    cmp.l SourceP2_Build+18,x
beq SourceP2_RecordPicture__stable6
    brl SourceP2_RecordPicture__done
SourceP2_RecordPicture__stable6:
.a16
.i16
    lda CHAR_THROW_ZPOS
    cmp.l SourceP2_Build+20,x
beq SourceP2_RecordPicture__stable7
    brl SourceP2_RecordPicture__done
SourceP2_RecordPicture__stable7:
.a16
.i16
    lda.l SourceVisual_BaseTile
    cmp.l SourceP2_Build+22,x
beq SourceP2_RecordPicture__stable8
    brl SourceP2_RecordPicture__done
SourceP2_RecordPicture__stable8:
.a16
.i16
    lda.l SourceVisual_EntryScratch+2
    cmp.l SourceP2_Build+28,x
beq SourceP2_RecordPicture__stable9
    brl SourceP2_RecordPicture__done
SourceP2_RecordPicture__stable9:
.a16
.i16
    lda.l SourceVisual_PieceCount
    cmp.l SourceP2_Build+30,x
beq SourceP2_RecordPicture__stable10
    brl SourceP2_RecordPicture__done
SourceP2_RecordPicture__stable10:
.a16
.i16
    lda.l $7E53A0
    cmp.l SourceP2_Build,x
bcs SourceP2_RecordPicture__end_order
    brl SourceP2_RecordPicture__done
SourceP2_RecordPicture__end_order:
.a16
.i16
    sta.l SourceP2_Build+2,x
    lda.l Nmi_FrameCounter
    sta.l SourceP2_Build+26,x
    lda #1
    sta.l SourceP2_Build+24,x
SourceP2_RecordPicture__done:
.a16
.i16
    rep #$30
    pld
    plb
    ply
    plx
    pla
    plp
    rtl
