; Cooperative foreground yield only. A fresh source-replayed A can arrive
; while the old idle/walk frame is still preparing. Return the established
; resource-pending result only when the existing completed image validates.
; The original fallback emitter and input poll remain the only authorities.
.bank 5
.org $C200
SourceJumpYield_Scan:
.a16
.i16
    lda.l SourceInput_Selected1
    ora.l SourceInput_Selected2
    and #$80
    beq SourceJumpYield_ScanNormal
    jsl SourceJumpYield_Check
    bcs SourceJumpYield_Pending
SourceJumpYield_ScanNormal:
.a16
.i16
    lda.l SourceVisual_PieceIndex
    cmp.l SourceVisual_PieceCount
    jml SourceJumpYield_ScanContinue
SourceJumpYield_Apply:
.a16
.i16
    lda.l SourceInput_Selected1
    ora.l SourceInput_Selected2
    and #$80
    beq SourceJumpYield_ApplyNormal
    jsl SourceJumpYield_Check
    bcs SourceJumpYield_Pending
SourceJumpYield_ApplyNormal:
.a16
.i16
    lda.l SourceVisual_PieceIndex
    cmp.l SourceVisual_PieceCount
    jml SourceJumpYield_ApplyContinue
SourceJumpYield_Pending:
.a16
.i16
    jml SourceVisual_PrepareBlocks__pending
SourceJumpYield_Check:
.a16
.i16
    php
    pha
    phx
    phy
    cld
    lda.l Game_CampaignId
    and #255
    cmp #3
    beq SourceJumpYield_G0
    brl SourceJumpYield_No
SourceJumpYield_G0:
    lda.l Game_State
    ora.l Game_StageIndex
    ora.l $7E46DE
    beq SourceJumpYield_G1
    brl SourceJumpYield_No
SourceJumpYield_G1:
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SourceJumpYield_G2
    brl SourceJumpYield_No
SourceJumpYield_G2:
    lda.l SourceVisual_CompletedMagic
    cmp #$C04D
    beq SourceJumpYield_G3
    brl SourceJumpYield_No
SourceJumpYield_G3:
    lda.l SVActor_Magic
    cmp #$AC19
    beq SourceJumpYield_G4
    brl SourceJumpYield_No
SourceJumpYield_G4:
    ldy #0
    lda.l SourceInput_Selected1
    and #$80
    beq SourceJumpYield_Player2
    lda.l SourceVisual_FieldPress1
    and #$80
    bne SourceJumpYield_Player2
    lda.l $7E0A00+CHAR_SELECTED
    and #255
    cmp #3
    bcs SourceJumpYield_Player2
    lda.l $7E0A00+CHAR_THROW_ZPOS
    bne SourceJumpYield_Player2
    lda.l $7E0A00+CHAR_HP
    and #255
    beq SourceJumpYield_Player2
    lda.l $7E0A00+CHAR_INPUT_DRIVEN
    and #255
    cmp #1
    bne SourceJumpYield_Player2
    ldy #1
SourceJumpYield_Player2:
.a16
.i16
    lda.l G13_TwoPlayerEnabled
    and #255
    beq SourceJumpYield_Choose
    lda.l SourceInput_Selected2
    and #$80
    beq SourceJumpYield_Choose
    lda.l SourceVisual_FieldPress2
    and #$80
    bne SourceJumpYield_Choose
    lda.l $7E0A85+CHAR_SELECTED
    and #255
    cmp #3
    bcs SourceJumpYield_Choose
    lda.l $7E0A85+CHAR_THROW_ZPOS
    bne SourceJumpYield_Choose
    lda.l $7E0A85+CHAR_HP
    and #255
    beq SourceJumpYield_Choose
    lda.l $7E0A85+CHAR_INPUT_DRIVEN
    and #255
    cmp #1
    bne SourceJumpYield_Choose
    tya
    ora #2
    tay
SourceJumpYield_Choose:
.a16
.i16
    tya
    bne SourceJumpYield_HasInput
    brl SourceJumpYield_No
SourceJumpYield_HasInput:
    lda.l SourceVisual_ActorSlot
    cmp #6
    bcc SourceJumpYield_SlotValid
    brl SourceJumpYield_No
SourceJumpYield_SlotValid:
    cmp #0
    bne SourceJumpYield_OtherDP
    tdc
    cmp #$0A00
    beq SourceJumpYield_DPValid
    brl SourceJumpYield_No
SourceJumpYield_OtherDP:
    dec a
    asl a
    tax
    lda.l SVActor_Dps,x
    pha
    tdc
    cmp 1,s
    beq SourceJumpYield_OtherDPValid
    pla
    brl SourceJumpYield_No
SourceJumpYield_OtherDPValid:
    pla
SourceJumpYield_DPValid:
    lda.l SourceVisual_ActorSlot
    cmp #2
    bcs SourceJumpYield_CachedOther
    cmp #1
    beq SourceJumpYield_Wants2
    tya
    and #1
    beq SourceJumpYield_NoNear
    lda.l SourceVisual_CompletedValid
    cmp #1
    bne SourceJumpYield_NoNear
    lda.l SourceVisual_CompletedStage
    cmp.l Game_StageIndex
    bne SourceJumpYield_NoNear
    lda CHAR_ROSTER_INDEX
    and #255
    cmp.l SourceVisual_CompletedRoster
    bne SourceJumpYield_NoNear
    lda.l SourceVisual_CompletedEntry+12
    and #255
    beq SourceJumpYield_NoNear
    jsl SourceJumpYield_ValidateP1
    bcs SourceJumpYield_Yes
    bra SourceJumpYield_NoNear
SourceJumpYield_Wants2:
    tya
    and #2
    beq SourceJumpYield_NoNear
SourceJumpYield_CachedOther:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    dec a
    asl a
    tax
    lda.l SVActor_Base
    pha
    lda.l SVActor_Bit
    pha
    lda.l SVActor_Bits,x
    sta.l SVActor_Bit
    lda.l SVActor_Bases,x
    sta.l SVActor_Base
    tax
    lda.l SVActor_Data+12,x
    and #255
    beq SourceJumpYield_OtherInvalid
    jsl SourceJumpYield_ValidateOther
    bcs SourceJumpYield_OtherValid
SourceJumpYield_OtherInvalid:
    pla
    sta.l SVActor_Bit
    pla
    sta.l SVActor_Base
    bra SourceJumpYield_NoNear
SourceJumpYield_OtherValid:
    pla
    sta.l SVActor_Bit
    pla
    sta.l SVActor_Base
    bra SourceJumpYield_Yes
SourceJumpYield_NoNear:
.a16
.i16
SourceJumpYield_No:
.a16
.i16
    ply
    plx
    pla
    plp
    clc
    rtl
SourceJumpYield_Yes:
.a16
.i16
    ply
    plx
    pla
    plp
    sec
    rtl
