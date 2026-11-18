; Translated existing immutable completed-NPC picture, with original gates.
SourceNpcMove_Scope:
.a16
.i16
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
beq SourceNpcMove_Scope__guard0
    brl SourceNpcMove_Scope__no
SourceNpcMove_Scope__guard0:
.a16
.i16
    lda.l Game_State
    cmp #0
beq SourceNpcMove_Scope__guard1
    brl SourceNpcMove_Scope__no
SourceNpcMove_Scope__guard1:
.a16
.i16
    lda.l $7E175E
    cmp #2
beq SourceNpcMove_Scope__guard2
    brl SourceNpcMove_Scope__no
SourceNpcMove_Scope__guard2:
.a16
.i16
    lda.l $7E1760
    cmp #1
beq SourceNpcMove_Scope__guard3
    brl SourceNpcMove_Scope__no
SourceNpcMove_Scope__guard3:
.a16
.i16
    lda.l $7E46DC
    cmp #1
beq SourceNpcMove_Scope__guard4
    brl SourceNpcMove_Scope__no
SourceNpcMove_Scope__guard4:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
beq SourceNpcMove_Scope__guard5
    brl SourceNpcMove_Scope__no
SourceNpcMove_Scope__guard5:
.a16
.i16
    lda.l SourceVisual_CompletedMagic
    cmp #$C04D
beq SourceNpcMove_Scope__guard6
    brl SourceNpcMove_Scope__no
SourceNpcMove_Scope__guard6:
.a16
.i16
    lda.l SVActor_Magic
    cmp #$AC19
beq SourceNpcMove_Scope__guard7
    brl SourceNpcMove_Scope__no
SourceNpcMove_Scope__guard7:
.a16
.i16
    sec
    rts
SourceNpcMove_Scope__no:
.a16
.i16
    clc
    rts

SourceNpcMove_Init:
.a16
.i16
    lda.l SourceNpc_Magic
    cmp #$4E43
    beq SourceNpcMove_Init__done
    lda #0
    ldx #0
SourceNpcMove_Init__clear:
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
    bcc SourceNpcMove_Init__clear
    lda #$4E43
    sta.l SourceNpc_Magic
SourceNpcMove_Init__done:
.a16
.i16
    rts

SourceNpcMove_Select:
.a16
.i16
    lda.l SVActor_Slot
    cmp #2
    bcc SourceNpcMove_Select__no
    cmp #6
    bcs SourceNpcMove_Select__no
    sec
    sbc #2
    asl a
    tax
    tdc
    cmp.l SourceNpc_Dps,x
    bne SourceNpcMove_Select__no
    txa
    asl a
    asl a
    asl a
    asl a
    sta.l SourceNpc_Index
    tax
    sec
    rts
SourceNpcMove_Select__no:
.a16
.i16
    clc
    rts

SourceNpcMove_FillFingerprint:
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

SourceNpcMove_TryPicture:
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
    jsr SourceNpcMove_Scope
bcs SourceNpcMove_TryPicture__scope
    brl SourceNpcMove_TryPicture__miss
SourceNpcMove_TryPicture__scope:
.a16
.i16
    jsr SourceNpcMove_Init
    jsr SourceNpcMove_Select
bcs SourceNpcMove_TryPicture__slot
    brl SourceNpcMove_TryPicture__miss
SourceNpcMove_TryPicture__slot:
.a16
.i16
    lda #0
    sta.l SourceNpc_Build+24,x
    lda.l SourceVisual_ServiceOnly
    cmp #0
beq SourceNpcMove_TryPicture__eligible0
    brl SourceNpcMove_TryPicture__miss
SourceNpcMove_TryPicture__eligible0:
.a16
.i16
    lda.l Stage_Mirror
    and #$00FF
beq SourceNpcMove_TryPicture__eligible1
    brl SourceNpcMove_TryPicture__miss
SourceNpcMove_TryPicture__eligible1:
.a16
.i16
    lda CHAR_HP
    and #$00FF
bne SourceNpcMove_TryPicture__eligible2
    brl SourceNpcMove_TryPicture__miss
SourceNpcMove_TryPicture__eligible2:
.a16
.i16
    lda CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #2
beq SourceNpcMove_TryPicture__eligible3
    brl SourceNpcMove_TryPicture__miss
SourceNpcMove_TryPicture__eligible3:
.a16
.i16
    lda CHAR_SELECTED
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
bne SourceNpcMove_TryPicture__eligible4
    brl SourceNpcMove_TryPicture__miss
SourceNpcMove_TryPicture__eligible4:
.a16
.i16
    lda.l SourceVisual_PieceCount
bne SourceNpcMove_TryPicture__eligible5
    brl SourceNpcMove_TryPicture__miss
SourceNpcMove_TryPicture__eligible5:
.a16
.i16
    cmp #66
bcc SourceNpcMove_TryPicture__eligible6
    brl SourceNpcMove_TryPicture__miss
SourceNpcMove_TryPicture__eligible6:
.a16
.i16
    jsl StageBoundsHost_Normal
bcs SourceNpcMove_TryPicture__eligible7
    brl SourceNpcMove_TryPicture__miss
SourceNpcMove_TryPicture__eligible7:
.a16
.i16
    jsl StageBounds_Row
    lda.l StageBounds_State,x
beq SourceNpcMove_TryPicture__eligible8
    brl SourceNpcMove_TryPicture__miss
SourceNpcMove_TryPicture__eligible8:
.a16
.i16
    lda.l SourceNpc_Index
    tax
    lda.l SVActor_Slot
    sta.l SourceNpc_BuildingSlot
    lda.l $7E53A0
    sta.l SourceNpc_Build,x
    jsr SourceNpcMove_FillFingerprint
    lda.l SourcePacket_ActiveValid
    cmp #1
beq SourceNpcMove_TryPicture__active
    brl SourceNpcMove_TryPicture__miss
SourceNpcMove_TryPicture__active:
.a16
.i16
    lda.l SourcePacket_CopyBusy
beq SourceNpcMove_TryPicture__unlocked
    brl SourceNpcMove_TryPicture__miss
SourceNpcMove_TryPicture__unlocked:
.a16
.i16
    lda.l SourceNpc_Active+24,x
    cmp #1
beq SourceNpcMove_TryPicture__picture
    brl SourceNpcMove_TryPicture__miss
SourceNpcMove_TryPicture__picture:
.a16
.i16
    lda.l Nmi_FrameCounter
    sec
    sbc.l SourceNpc_Active+26,x
    cmp #64
bcc SourceNpcMove_TryPicture__recent
    brl SourceNpcMove_TryPicture__miss
SourceNpcMove_TryPicture__recent:
.a16
.i16
    lda #8
    sta.l SourceNpc_Remaining
    txa
    clc
    adc #8
    tax
SourceNpcMove_TryPicture__fingerprint:
.a16
.i16
    lda.l SourceNpc_Build,x
    cmp.l SourceNpc_Active,x
beq SourceNpcMove_TryPicture__sameword
    brl SourceNpcMove_TryPicture__miss
SourceNpcMove_TryPicture__sameword:
.a16
.i16
    inx
    inx
    lda.l SourceNpc_Remaining
    dec a
    sta.l SourceNpc_Remaining
    bne SourceNpcMove_TryPicture__fingerprint
    lda.l SourceNpc_Index
    tax
    lda.l SourceNpc_Build+28,x
    cmp.l SourceNpc_Active+28,x
beq SourceNpcMove_TryPicture__same28
    brl SourceNpcMove_TryPicture__miss
SourceNpcMove_TryPicture__same28:
.a16
.i16
    lda.l SourceNpc_Build+30,x
    cmp.l SourceNpc_Active+30,x
beq SourceNpcMove_TryPicture__same30
    brl SourceNpcMove_TryPicture__miss
SourceNpcMove_TryPicture__same30:
.a16
.i16
    lda.l SourceNpc_Active,x
    sta.l SourceNpc_SourceBegin
    and #3
beq SourceNpcMove_TryPicture__aligned0
    brl SourceNpcMove_TryPicture__miss
SourceNpcMove_TryPicture__aligned0:
.a16
.i16
    lda.l SourceNpc_Active+2,x
    and #3
beq SourceNpcMove_TryPicture__aligned1
    brl SourceNpcMove_TryPicture__miss
SourceNpcMove_TryPicture__aligned1:
.a16
.i16
    lda.l SourceNpc_Active+2,x
    cmp #513
bcc SourceNpcMove_TryPicture__source_end
    brl SourceNpcMove_TryPicture__miss
SourceNpcMove_TryPicture__source_end:
.a16
.i16
    sec
    sbc.l SourceNpc_SourceBegin
bcs SourceNpcMove_TryPicture__ordered
    brl SourceNpcMove_TryPicture__miss
SourceNpcMove_TryPicture__ordered:
.a16
.i16
    cmp #0
bne SourceNpcMove_TryPicture__nonempty
    brl SourceNpcMove_TryPicture__miss
SourceNpcMove_TryPicture__nonempty:
.a16
.i16
    cmp #261
bcc SourceNpcMove_TryPicture__length
    brl SourceNpcMove_TryPicture__miss
SourceNpcMove_TryPicture__length:
.a16
.i16
    sta.l SourceNpc_Length
    lda.l $7E53A0
    sta.l SourceNpc_DestBegin
    and #3
beq SourceNpcMove_TryPicture__dest_aligned
    brl SourceNpcMove_TryPicture__miss
SourceNpcMove_TryPicture__dest_aligned:
.a16
.i16
    lda.l SourceNpc_DestBegin
    cmp #513
    bcc SourceNpcMove_TryPicture__dest_bounded
    brl SourceNpcMove_TryPicture__miss
SourceNpcMove_TryPicture__dest_bounded:
.a16
.i16
    lda.l SourceNpc_DestBegin
    clc
    adc.l SourceNpc_Length
    cmp #513
bcc SourceNpcMove_TryPicture__capacity
    brl SourceNpcMove_TryPicture__miss
SourceNpcMove_TryPicture__capacity:
.a16
.i16
    ldx #0
SourceNpcMove_TryPicture__queue:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    beq SourceNpcMove_TryPicture__queue_next
    lda.l DmaQueue+4,x
    and #DMA_OPT_REVERSE
beq SourceNpcMove_TryPicture__not_reverse
    brl SourceNpcMove_TryPicture__miss
SourceNpcMove_TryPicture__not_reverse:
.a16
.i16
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$43
bne SourceNpcMove_TryPicture__not_private
    brl SourceNpcMove_TryPicture__miss
SourceNpcMove_TryPicture__not_private:
.a16
.i16
SourceNpcMove_TryPicture__queue_next:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourceNpcMove_TryPicture__queue
    jsr SourceNpcMove_Preflight
    bcs SourceNpcMove_PreflightOK
    brl SourceNpcMove_TryPicture__miss
SourceNpcMove_PreflightOK:
.a16
.i16
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
SourceNpcMove_TryPicture__shift:
.a16
.i16
    cpx #0
    beq SourceNpcMove_TryPicture__shift_done
    lda.l SourceNpc_HiBits
    lsr a
    lsr a
    sta.l SourceNpc_HiBits
    dex
    bra SourceNpcMove_TryPicture__shift
SourceNpcMove_TryPicture__shift_done:
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
SourceNpcMove_TryPicture__hi:
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
    beq SourceNpcMove_TryPicture__copied
    lda.l SourceNpc_HiLeft
    dec a
    sta.l SourceNpc_HiLeft
    bne SourceNpcMove_TryPicture__hi
    lda #4
    sta.l SourceNpc_HiLeft
    lda.l SourceNpc_HiPointer
    inc a
    sta.l SourceNpc_HiPointer
    tax
    lda.l SOURCE_PACKET_BASE+512,x
    and #$00FF
    sta.l SourceNpc_HiBits
    bra SourceNpcMove_TryPicture__hi
SourceNpcMove_TryPicture__copied:
.a16
.i16
    jsr SourceNpcMove_Translate
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
SourceNpcMove_TryPicture__hit:
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
SourceNpcMove_TryPicture__miss:
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

; Scope and all lifetime/camera/pose/generation gates are the original
; SourceNpc_TryPicture gates. Preflight writes only this unused private scratch.
SourceNpcMove_DeltaX = $436000
SourceNpcMove_DeltaY = $436002
SourceNpcMove_Loop = $436004
SourceNpcMove_End = $436006
SourceNpcMove_Hi = $436008
SourceNpcMove_Preflight:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    cld
    lda.l SourceNpc_Index
    tax
    lda.l SourceNpc_Build+4,x
    sec
    sbc.l SourceNpc_Active+4,x
    sta.l SourceNpcMove_DeltaX
    lda.l SourceNpc_Build+6,x
    sec
    sbc.l SourceNpc_Active+6,x
    sta.l SourceNpcMove_DeltaY
    ora.l SourceNpcMove_DeltaX
    bne SourceNpcMove_Guard27
    brl SourceNpcMove_PreflightYes
SourceNpcMove_Guard27:
.a16
.i16
    lda.l SourceVisual_PieceCount
    asl a
    asl a
    cmp.l SourceNpc_Length
    beq SourceNpcMove_Guard36
    brl SourceNpcMove_PreflightNo
SourceNpcMove_Guard36:
.a16
.i16
    lda.l SourceNpc_SourceBegin
    sta.l SourceNpcMove_Loop
    clc
    adc.l SourceNpc_Length
    sta.l SourceNpcMove_End
SourceNpcMove_PreflightRow:
.a16
.i16
    lda.l SourceNpcMove_Loop
    tax
    lda.l SOURCE_PACKET_BASE+1,x
    and #255
    cmp #224
    bcc SourceNpcMove_Guard54
    brl SourceNpcMove_PreflightNo
SourceNpcMove_Guard54:
.a16
.i16
    clc
    adc.l SourceNpcMove_DeltaY
    bpl SourceNpcMove_Guard61
    brl SourceNpcMove_PreflightNo
SourceNpcMove_Guard61:
.a16
.i16
    cmp #224
    bcc SourceNpcMove_Guard67
    brl SourceNpcMove_PreflightNo
SourceNpcMove_Guard67:
.a16
.i16
    lda.l SOURCE_PACKET_BASE,x
    and #255
    clc
    adc.l SourceNpcMove_DeltaX
    bpl SourceNpcMove_Guard76
    brl SourceNpcMove_PreflightNo
SourceNpcMove_Guard76:
.a16
.i16
    cmp #256
    bcc SourceNpcMove_Guard82
    brl SourceNpcMove_PreflightNo
SourceNpcMove_Guard82:
.a16
.i16
    lda.l SourceNpcMove_Loop
    lsr a
    lsr a
    lsr a
    lsr a
    tax
    lda.l SOURCE_PACKET_BASE+512,x
    and #255
    sta.l SourceNpcMove_Hi
    lda.l SourceNpcMove_Loop
    and #15
    lsr a
    lsr a
    tay
    lda.l SourceNpcMove_Hi
SourceNpcMove_PreflightShift:
.a16
.i16
    cpy #0
    beq SourceNpcMove_PreflightShifted
    lsr a
    lsr a
    dey
    bra SourceNpcMove_PreflightShift
SourceNpcMove_PreflightShifted:
.a16
.i16
    and #1
    beq SourceNpcMove_Guard115
    brl SourceNpcMove_PreflightNo
SourceNpcMove_Guard115:
.a16
.i16
    lda.l SourceNpcMove_Loop
    clc
    adc #4
    sta.l SourceNpcMove_Loop
    cmp.l SourceNpcMove_End
    bcs SourceNpcMove_PreflightYes
    brl SourceNpcMove_PreflightRow
SourceNpcMove_PreflightYes:
.a16
.i16
    ply
    plx
    pla
    plp
    sec
    rts
SourceNpcMove_PreflightNo:
.a16
.i16
    ply
    plx
    pla
    plp
    clc
    rts

; Every row passed the read-only preflight before the original full copy.
; No high-X bit changes: both old and new row X are nonnegative <256.
SourceNpcMove_Translate:
.a16
.i16
    php
    rep #$30
    pha
    phx
    cld
    lda.l SourceNpcMove_DeltaX
    ora.l SourceNpcMove_DeltaY
    beq SourceNpcMove_TranslateDone
    lda.l SourceNpc_DestBegin
    clc
    adc.l SourceNpc_Length
    sta.l SourceNpcMove_End
    lda.l SourceNpc_DestBegin
    tax
SourceNpcMove_TranslateRow:
.a16
.i16
    lda.l Oam_Buffer,x
    and #255
    clc
    adc.l SourceNpcMove_DeltaX
    sep #$20
.a8
    sta.l Oam_Buffer,x
    rep #$30
.a16
.i16
    lda.l Oam_Buffer+1,x
    and #255
    clc
    adc.l SourceNpcMove_DeltaY
    sep #$20
.a8
    sta.l Oam_Buffer+1,x
    rep #$30
.a16
.i16
    txa
    clc
    adc #4
    tax
    cmp.l SourceNpcMove_End
    bcc SourceNpcMove_TranslateRow
SourceNpcMove_TranslateDone:
.a16
.i16
    plx
    pla
    plp
    rts
SourceNpcMove_EndCode:
