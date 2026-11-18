; Reuse only an already-validated stationary completed NPC picture.
; No private pixel copy: read the immutable previous whole SOURCE_PACKET_BASE.
; Build/active metadata commit with that same full packet, never independently.
; No resource/queue/Ready/ownership/game-state/hardware writes.
; Gap audited between retry scratch ending435474 and SIGNED_X at435600.
SourceNpc_Build = $435480 ; four32-byte rows, ends435500
SourceNpc_Active = $435500 ; four32-byte rows, ends435580
SourceNpc_Index = $4355C0
SourceNpc_Length = $4355C2
SourceNpc_SourceBegin = $4355C4
SourceNpc_HiPointer = $4355C6
SourceNpc_HiBits = $4355C8
SourceNpc_HiLeft = $4355CA
SourceNpc_Remaining = $4355CC
SourceNpc_DestBegin = $4355CE
SourceNpc_Magic = $7EEFD0
SourceNpc_BuildingSlot = $7EEFD2
SourceNpc_Scope:
.a16
.i16
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
beq SourceNpc_Scope__guard0
    brl SourceNpc_Scope__no
SourceNpc_Scope__guard0:
.a16
.i16
    lda.l Game_State
    cmp #0
beq SourceNpc_Scope__guard1
    brl SourceNpc_Scope__no
SourceNpc_Scope__guard1:
.a16
.i16
    lda.l $7E175E
    cmp #2
beq SourceNpc_Scope__guard2
    brl SourceNpc_Scope__no
SourceNpc_Scope__guard2:
.a16
.i16
    lda.l $7E1760
    cmp #1
beq SourceNpc_Scope__guard3
    brl SourceNpc_Scope__no
SourceNpc_Scope__guard3:
.a16
.i16
    lda.l $7E46DC
    cmp #1
beq SourceNpc_Scope__guard4
    brl SourceNpc_Scope__no
SourceNpc_Scope__guard4:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
beq SourceNpc_Scope__guard5
    brl SourceNpc_Scope__no
SourceNpc_Scope__guard5:
.a16
.i16
    lda.l SourceVisual_CompletedMagic
    cmp #$C04D
beq SourceNpc_Scope__guard6
    brl SourceNpc_Scope__no
SourceNpc_Scope__guard6:
.a16
.i16
    lda.l SVActor_Magic
    cmp #$AC19
beq SourceNpc_Scope__guard7
    brl SourceNpc_Scope__no
SourceNpc_Scope__guard7:
.a16
.i16
    sec
    rts
SourceNpc_Scope__no:
.a16
.i16
    clc
    rts
SourceNpc_Init:
.a16
.i16
    lda.l SourceNpc_Magic
    cmp #$4E44
    beq SourceNpc_Init__done
    lda #0
    ldx #0
SourceNpc_Init__clear:
.a16
.i16
    sta.l SourceNpc_Build+24,x
    sta.l SourceNpc_Active+24,x
    txa
    clc
    adc #32
    tax
    lda #0
    cpx #128
    bcc SourceNpc_Init__clear
    sta.l SourceP2_Build+24
    sta.l SourceP2_Active+24
    lda #$4E44
    sta.l SourceNpc_Magic
SourceNpc_Init__done:
.a16
.i16
    rts
SourceNpc_FrameBegin:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    phd
    jsr SourceNpc_Scope
    bcc SourceNpc_FrameBegin__done
    jsr SourceNpc_Init
    ldx #0
    lda #0
SourceNpc_FrameBegin__clear:
.a16
.i16
    sta.l SourceNpc_Build+24,x
    txa
    clc
    adc #32
    tax
    lda #0
    cpx #128
    bcc SourceNpc_FrameBegin__clear
    sta.l SourceP2_Build+24
SourceNpc_FrameBegin__done:
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
SourceNpc_CommitPictureMeta:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    phd
    jsr SourceNpc_Scope
    bcc SourceNpc_CommitPictureMeta__done
    lda.l SourceNpc_Magic
    cmp #$4E44
    bne SourceNpc_CommitPictureMeta__done
    ldx #(SourceNpc_Build&$FFFF)
    ldy #(SourceNpc_Active&$FFFF)
    lda #127
    mvn $43,$43
    ldx #(SourceP2_Build&$FFFF)
    ldy #(SourceP2_Active&$FFFF)
    lda #31
    mvn $43,$43
SourceNpc_CommitPictureMeta__done:
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
SourceNpc_Select:
.a16
.i16
    lda.l SVActor_Slot
    cmp #2
    bcc SourceNpc_Select__no
    cmp #6
    bcs SourceNpc_Select__no
    sec
    sbc #2
    asl a
    tax
    tdc
    cmp.l SourceNpc_Dps,x
    bne SourceNpc_Select__no
    txa
    asl a
    asl a
    asl a
    asl a
    sta.l SourceNpc_Index
    tax
    sec
    rts
SourceNpc_Select__no:
.a16
.i16
    clc
    rts
SourceNpc_Dps:
    .dw $0B0A,$0B8F,$0C14,$0C99
SourceNpc_FillFingerprint:
.a16
.i16
    lda CHAR_POS_X
    sta.l SourceNpc_Build+4,x
    lda CHAR_POS_Y
    sta.l SourceNpc_Build+6,x
    lda CHAR_FACING_LEFT
    and #$00FF
    sta.l SourceNpc_Build+8,x
    lda.l Screen_PosX
    sta.l SourceNpc_Build+10,x
    lda.l SVActor_LeaseScratch
    sta.l SourceNpc_Build+12,x
    lda.l Game_StageIndex
    sta.l SourceNpc_Build+16,x
    lda CHAR_SELECTED
    and #$00FF
    sta.l SourceNpc_Build+18,x
    lda CHAR_THROW_ZPOS
    sta.l SourceNpc_Build+20,x
    lda.l SourceVisual_BaseTile
    sta.l SourceNpc_Build+22,x
    lda.l SourceVisual_EntryScratch+2
    sta.l SourceNpc_Build+28,x
    lda.l SourceVisual_PieceCount
    sta.l SourceNpc_Build+30,x
    lda.l SVActor_Slot
    dec a
    asl a
    tax
    lda.l SVActor_Captures,x
    pha
    lda.l SourceNpc_Index
    tax
    pla
    sta.l SourceNpc_Build+14,x
    rts
SourceNpc_TryPicture:
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
    sta.l SourceNpc_BuildingSlot
    jsr SourceNpc_Scope
bcs SourceNpc_TryPicture__scope
    brl SourceNpc_TryPicture__miss
SourceNpc_TryPicture__scope:
.a16
.i16
    jsr SourceNpc_Init
    jsr SourceNpc_Select
bcs SourceNpc_TryPicture__slot
    brl SourceNpc_TryPicture__miss
SourceNpc_TryPicture__slot:
.a16
.i16
    lda #0
    sta.l SourceNpc_Build+24,x
    lda.l SourceVisual_ServiceOnly
    cmp #0
beq SourceNpc_TryPicture__eligible0
    brl SourceNpc_TryPicture__miss
SourceNpc_TryPicture__eligible0:
.a16
.i16
    lda.l Stage_Mirror
    and #$00FF
beq SourceNpc_TryPicture__eligible1
    brl SourceNpc_TryPicture__miss
SourceNpc_TryPicture__eligible1:
.a16
.i16
    lda CHAR_HP
    and #$00FF
bne SourceNpc_TryPicture__eligible2
    brl SourceNpc_TryPicture__miss
SourceNpc_TryPicture__eligible2:
.a16
.i16
    lda CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #2
beq SourceNpc_TryPicture__eligible3
    brl SourceNpc_TryPicture__miss
SourceNpc_TryPicture__eligible3:
.a16
.i16
    lda CHAR_SELECTED
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
bne SourceNpc_TryPicture__eligible4
    brl SourceNpc_TryPicture__miss
SourceNpc_TryPicture__eligible4:
.a16
.i16
    lda.l SourceVisual_PieceCount
bne SourceNpc_TryPicture__eligible5
    brl SourceNpc_TryPicture__miss
SourceNpc_TryPicture__eligible5:
.a16
.i16
    cmp #66
bcc SourceNpc_TryPicture__eligible6
    brl SourceNpc_TryPicture__miss
SourceNpc_TryPicture__eligible6:
.a16
.i16
    jsl StageBoundsHost_Normal
bcs SourceNpc_TryPicture__eligible7
    brl SourceNpc_TryPicture__miss
SourceNpc_TryPicture__eligible7:
.a16
.i16
    jsl StageBounds_Row
    lda.l StageBounds_State,x
beq SourceNpc_TryPicture__eligible8
    brl SourceNpc_TryPicture__miss
SourceNpc_TryPicture__eligible8:
.a16
.i16
    lda.l SourceNpc_Index
    tax
    lda.l SVActor_Slot
    sta.l SourceNpc_BuildingSlot
    lda.l $7E53A0
    sta.l SourceNpc_Build,x
    jsr SourceNpc_FillFingerprint
    lda.l SourcePacket_ActiveValid
    cmp #1
beq SourceNpc_TryPicture__active
    brl SourceNpc_TryPicture__miss
SourceNpc_TryPicture__active:
.a16
.i16
    lda.l SourcePacket_CopyBusy
beq SourceNpc_TryPicture__unlocked
    brl SourceNpc_TryPicture__miss
SourceNpc_TryPicture__unlocked:
.a16
.i16
    lda.l SourceNpc_Active+24,x
    cmp #1
beq SourceNpc_TryPicture__picture
    brl SourceNpc_TryPicture__miss
SourceNpc_TryPicture__picture:
.a16
.i16
    lda.l Nmi_FrameCounter
    sec
    sbc.l SourceNpc_Active+26,x
    cmp #64
bcc SourceNpc_TryPicture__recent
    brl SourceNpc_TryPicture__miss
SourceNpc_TryPicture__recent:
.a16
.i16
    lda #10
    sta.l SourceNpc_Remaining
    inx
    inx
    inx
    inx
SourceNpc_TryPicture__fingerprint:
.a16
.i16
    lda.l SourceNpc_Build,x
    cmp.l SourceNpc_Active,x
beq SourceNpc_TryPicture__sameword
    brl SourceNpc_TryPicture__miss
SourceNpc_TryPicture__sameword:
.a16
.i16
    inx
    inx
    lda.l SourceNpc_Remaining
    dec a
    sta.l SourceNpc_Remaining
    bne SourceNpc_TryPicture__fingerprint
    lda.l SourceNpc_Index
    tax
    lda.l SourceNpc_Build+28,x
    cmp.l SourceNpc_Active+28,x
beq SourceNpc_TryPicture__same28
    brl SourceNpc_TryPicture__miss
SourceNpc_TryPicture__same28:
.a16
.i16
    lda.l SourceNpc_Build+30,x
    cmp.l SourceNpc_Active+30,x
beq SourceNpc_TryPicture__same30
    brl SourceNpc_TryPicture__miss
SourceNpc_TryPicture__same30:
.a16
.i16
    lda.l SourceNpc_Active,x
    sta.l SourceNpc_SourceBegin
    and #3
beq SourceNpc_TryPicture__aligned0
    brl SourceNpc_TryPicture__miss
SourceNpc_TryPicture__aligned0:
.a16
.i16
    lda.l SourceNpc_Active+2,x
    and #3
beq SourceNpc_TryPicture__aligned1
    brl SourceNpc_TryPicture__miss
SourceNpc_TryPicture__aligned1:
.a16
.i16
    lda.l SourceNpc_Active+2,x
    cmp #513
bcc SourceNpc_TryPicture__source_end
    brl SourceNpc_TryPicture__miss
SourceNpc_TryPicture__source_end:
.a16
.i16
    sec
    sbc.l SourceNpc_SourceBegin
bcs SourceNpc_TryPicture__ordered
    brl SourceNpc_TryPicture__miss
SourceNpc_TryPicture__ordered:
.a16
.i16
    cmp #0
bne SourceNpc_TryPicture__nonempty
    brl SourceNpc_TryPicture__miss
SourceNpc_TryPicture__nonempty:
.a16
.i16
    cmp #261
bcc SourceNpc_TryPicture__length
    brl SourceNpc_TryPicture__miss
SourceNpc_TryPicture__length:
.a16
.i16
    sta.l SourceNpc_Length
    lda.l $7E53A0
    sta.l SourceNpc_DestBegin
    and #3
beq SourceNpc_TryPicture__dest_aligned
    brl SourceNpc_TryPicture__miss
SourceNpc_TryPicture__dest_aligned:
.a16
.i16
    lda.l SourceNpc_DestBegin
    cmp #513
    bcc SourceNpc_TryPicture__dest_bounded
    brl SourceNpc_TryPicture__miss
SourceNpc_TryPicture__dest_bounded:
.a16
.i16
    lda.l SourceNpc_DestBegin
    clc
    adc.l SourceNpc_Length
    cmp #513
bcc SourceNpc_TryPicture__capacity
    brl SourceNpc_TryPicture__miss
SourceNpc_TryPicture__capacity:
.a16
.i16
    ldx #0
SourceNpc_TryPicture__queue:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    beq SourceNpc_TryPicture__queue_next
    lda.l DmaQueue+4,x
    and #DMA_OPT_REVERSE
beq SourceNpc_TryPicture__not_reverse
    brl SourceNpc_TryPicture__miss
SourceNpc_TryPicture__not_reverse:
.a16
.i16
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$43
bne SourceNpc_TryPicture__not_private
    brl SourceNpc_TryPicture__miss
SourceNpc_TryPicture__not_private:
.a16
.i16
SourceNpc_TryPicture__queue_next:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourceNpc_TryPicture__queue
    lda.l SourceNpc_SourceBegin
    clc
    adc #(SOURCE_PACKET_BASE&$FFFF)
    tax
    lda.l SourceNpc_DestBegin
    clc
    adc #(Oam_Buffer&$FFFF)
    tay
    lda.l SourceNpc_Length
    dec a
    mvn $7E,$43
    lda.l SourceNpc_SourceBegin
    lsr a
    lsr a
    lsr a
    lsr a
    sta.l SourceNpc_HiPointer
    tax
    lda.l SOURCE_PACKET_BASE+512,x
    and #$00FF
    sta.l SourceNpc_HiBits
    lda.l SourceNpc_SourceBegin
    and #15
    lsr a
    lsr a
    tax
    txa
    eor #$FFFF
    inc a
    clc
    adc #4
    sta.l SourceNpc_HiLeft
SourceNpc_TryPicture__shift:
.a16
.i16
    cpx #0
    beq SourceNpc_TryPicture__shift_done
    lda.l SourceNpc_HiBits
    lsr a
    lsr a
    sta.l SourceNpc_HiBits
    dex
    bra SourceNpc_TryPicture__shift
SourceNpc_TryPicture__shift_done:
.a16
.i16
    lda.l SourceNpc_DestBegin
    lsr a
    lsr a
    tay
    lda.l SourceNpc_Length
    lsr a
    lsr a
    sta.l SourceNpc_Remaining
    sta.l SourceVisual_VisiblePieces
SourceNpc_TryPicture__hi:
.a16
.i16
    lda.l SourceNpc_HiBits
    and #3
    sep #$20
.a8
    sta.w $5320,y ; DB7E, actual linked Oam_ExpandedHi low address
    rep #$30
.a16
.i16
    lda.l SourceNpc_HiBits
    lsr a
    lsr a
    sta.l SourceNpc_HiBits
    iny
    lda.l SourceNpc_Remaining
    dec a
    sta.l SourceNpc_Remaining
    beq SourceNpc_TryPicture__copied
    lda.l SourceNpc_HiLeft
    dec a
    sta.l SourceNpc_HiLeft
    bne SourceNpc_TryPicture__hi
    lda #4
    sta.l SourceNpc_HiLeft
    lda.l SourceNpc_HiPointer
    inc a
    sta.l SourceNpc_HiPointer
    tax
    lda.l SOURCE_PACKET_BASE+512,x
    and #$00FF
    sta.l SourceNpc_HiBits
    bra SourceNpc_TryPicture__hi
SourceNpc_TryPicture__copied:
.a16
.i16
    lda.l SourceNpc_DestBegin
    clc
    adc.l SourceNpc_Length
    sta.l $7E53A0
    lda CHAR_POS_X
    sec
    sbc.l Screen_PosX
    sta.l SourceVisual_EmitBaseX
    lda CHAR_POS_Y
    sta.l SourceVisual_EmitBaseY
    lda.l SourceVisual_PieceCount
    sta.l SourceVisual_PieceIndex
SourceNpc_TryPicture__hit:
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
SourceNpc_TryPicture__miss:
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
SourceNpc_RecordPicture:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    phd
    jsr SourceNpc_Scope
bcs SourceNpc_RecordPicture__scope
    brl SourceNpc_RecordPicture__done
SourceNpc_RecordPicture__scope:
.a16
.i16
    lda.l SourceNpc_BuildingSlot
    cmp.l SVActor_Slot
beq SourceNpc_RecordPicture__building
    brl SourceNpc_RecordPicture__done
SourceNpc_RecordPicture__building:
.a16
.i16
    jsr SourceNpc_Select
bcs SourceNpc_RecordPicture__slot
    brl SourceNpc_RecordPicture__done
SourceNpc_RecordPicture__slot:
.a16
.i16
    lda CHAR_POS_X
    cmp.l SourceNpc_Build+4,x
beq SourceNpc_RecordPicture__stable0
    brl SourceNpc_RecordPicture__done
SourceNpc_RecordPicture__stable0:
.a16
.i16
    lda CHAR_POS_Y
    cmp.l SourceNpc_Build+6,x
beq SourceNpc_RecordPicture__stable1
    brl SourceNpc_RecordPicture__done
SourceNpc_RecordPicture__stable1:
.a16
.i16
    lda CHAR_FACING_LEFT
    and #$00FF
    cmp.l SourceNpc_Build+8,x
beq SourceNpc_RecordPicture__stable2
    brl SourceNpc_RecordPicture__done
SourceNpc_RecordPicture__stable2:
.a16
.i16
    lda.l Screen_PosX
    cmp.l SourceNpc_Build+10,x
beq SourceNpc_RecordPicture__stable3
    brl SourceNpc_RecordPicture__done
SourceNpc_RecordPicture__stable3:
.a16
.i16
    lda.l SVActor_LeaseScratch
    cmp.l SourceNpc_Build+12,x
beq SourceNpc_RecordPicture__stable4
    brl SourceNpc_RecordPicture__done
SourceNpc_RecordPicture__stable4:
.a16
.i16
    lda.l Game_StageIndex
    cmp.l SourceNpc_Build+16,x
beq SourceNpc_RecordPicture__stable5
    brl SourceNpc_RecordPicture__done
SourceNpc_RecordPicture__stable5:
.a16
.i16
    lda CHAR_SELECTED
    and #$00FF
    cmp.l SourceNpc_Build+18,x
beq SourceNpc_RecordPicture__stable6
    brl SourceNpc_RecordPicture__done
SourceNpc_RecordPicture__stable6:
.a16
.i16
    lda CHAR_THROW_ZPOS
    cmp.l SourceNpc_Build+20,x
beq SourceNpc_RecordPicture__stable7
    brl SourceNpc_RecordPicture__done
SourceNpc_RecordPicture__stable7:
.a16
.i16
    lda.l SourceVisual_BaseTile
    cmp.l SourceNpc_Build+22,x
beq SourceNpc_RecordPicture__stable8
    brl SourceNpc_RecordPicture__done
SourceNpc_RecordPicture__stable8:
.a16
.i16
    lda.l SourceVisual_EntryScratch+2
    cmp.l SourceNpc_Build+28,x
beq SourceNpc_RecordPicture__stable9
    brl SourceNpc_RecordPicture__done
SourceNpc_RecordPicture__stable9:
.a16
.i16
    lda.l SourceVisual_PieceCount
    cmp.l SourceNpc_Build+30,x
beq SourceNpc_RecordPicture__stable10
    brl SourceNpc_RecordPicture__done
SourceNpc_RecordPicture__stable10:
.a16
.i16
    lda.l $7E53A0
    cmp.l SourceNpc_Build,x
bcs SourceNpc_RecordPicture__end_order
    brl SourceNpc_RecordPicture__done
SourceNpc_RecordPicture__end_order:
.a16
.i16
    sta.l SourceNpc_Build+2,x
    lda.l Nmi_FrameCounter
    sta.l SourceNpc_Build+26,x
    lda #1
    sta.l SourceNpc_Build+24,x
SourceNpc_RecordPicture__done:
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
