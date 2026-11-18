; Retain only the first coherently observed accepted P2 attack frame.
; This selects a desired key. The existing loader, pins, scene fence and OAM
; submission remain solely responsible for publication.
SourceP2Attack_Field = $7E46F4
SourceP2Attack_Magic = $7E46F6
SourceP2Attack_Init:
.a16
.i16
    lda #0
    sta.l SourceP2Attack_Field
    sta.l SourceP2Attack_Magic
    rtl

SourceP2Attack_Record:
.a16
.i16
    php
    rep #$31
    pha
    lda.l SourceWarm_Slot
    cmp #1
    bne SourceP2Attack_Record__done
    lda.l SourceWarm_Frame
    bne SourceP2Attack_Record__done
    lda.l SourceP2Attack_Magic
    cmp #$A10A
    bne SourceP2Attack_Record__new
    lda.l Nmi_FrameCounter
    sec
    sbc.l SourceP2Attack_Field
    cmp #12
    bcc SourceP2Attack_Record__done
SourceP2Attack_Record__new:
    lda.l Nmi_FrameCounter
    sta.l SourceP2Attack_Field
    lda #$A10A
    sta.l SourceP2Attack_Magic
SourceP2Attack_Record__done:
    pla
    plp
    rtl

SourceP2Attack_Prefer:
.a16
.i16
    php
    rep #$31
    pha
    lda.l SourceVisual_ServiceOnly
    bne SourceP2Attack_Prefer__done
    tdc
    cmp #$0A85
    bne SourceP2Attack_Prefer__done
    lda.l SourceVisual_Key
    cmp #$0216
    bne SourceP2Attack_Prefer__done
    lda.l SourceP2Attack_Magic
    cmp #$A10A
    bne SourceP2Attack_Prefer__done
    lda.l Nmi_FrameCounter
    sec
    sbc.l SourceP2Attack_Field
    cmp #9
    bcs SourceP2Attack_Prefer__done
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    bne SourceP2Attack_Prefer__done
    lda.l Game_StageIndex
    bne SourceP2Attack_Prefer__done
    lda CHAR_SELECTED
    and #$00FF
    cmp #2
    bne SourceP2Attack_Prefer__done
    lda.l SourceVisual_Sa1RuntimeRole+133
    and #$00FF
    cmp #2
    bne SourceP2Attack_Prefer__done
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_Key+2
SourceP2Attack_Prefer__done:
    rep #$31
.a16
.i16
    pla
    plp
    rtl

SourceP2Attack_Ack:
.a16
.i16
    php
    rep #$31
    pha
    tdc
    cmp #$0A85
    bne SourceP2Attack_Ack__done
    lda.l SourceVisual_Key
    cmp #$0216
    bne SourceP2Attack_Ack__done
    lda.l SourceVisual_Key+2
    and #$00FF
    bne SourceP2Attack_Ack__done
    lda #0
    sta.l SourceP2Attack_Magic
SourceP2Attack_Ack__done:
    pla
    plp
    rtl
