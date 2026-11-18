; Only a post-physical private ACK may arm this staged-image receipt.
; DMA module owns the previously unused word between BudgetTotal and Remaining.
; Zero is invalid, including stage wrap: fail open to ordinary publication.
SourceAttackReceipt = $7E047C
.bank 5
.org $C000
SourceAttackReceipt_Init:
.a16
.i16
    lda #0
    sta DmaQueue_CurrentSlot
    stz.w $047C
    rtl
SourceAttackReceipt_Direct:
.a8
.i16
    php
    rep #$20
.a16
    stz.w $047C
    plp
.a8
    sta.l $00420B
    rtl
SourceAttackReceipt_Arm:
.a16
.i16
    sta.l SourceAttackOwned_AckField
    php
    pha
    lda.l SourceAttackOwned_Stages
    sta.l SourceAttackReceipt
    pla
    plp
    rtl
; Tail of the real short-called generic OAM handler. No ACK or pin mutation
; occurs on suppression. It preserves an already displayed, still held image;
; it never credits a generic descriptor as a specialized completion.
SourceAttackReceipt_Queued:
.a8
.i16
    rep #$31
.a16
    lda.l SourceAttackReceipt
    beq SourceAttackReceipt_Normal
    jsl SourceAttackReceipt_Allow
    bcc SourceAttackReceipt_Normal
    sep #$20
.a8
    lda #$80
    rep #$31
.a16
    jml SourceAttackReceipt_QueuedReturn
SourceAttackReceipt_Normal:
.a16
.i16
    stz.w $047C
    lda.l DmaQueue+5,x
    jml SourceAttackReceipt_QueuedBody
SourceAttackReceipt_Allow:
.a16
.i16
    php
    pha
    phx
    phy
    cmp.l SourceAttackOwned_Stages
    beq SourceAttackReceipt_Check0
    brl SourceAttackReceipt_No
SourceAttackReceipt_Check0:
    lda.l SourceAttackOwned_State
    cmp #2
    beq SourceAttackReceipt_Check1
    brl SourceAttackReceipt_No
SourceAttackReceipt_Check1:
    lda.l SourceAttackOwned_Hold
    cmp #1
    beq SourceAttackReceipt_Check2
    brl SourceAttackReceipt_No
SourceAttackReceipt_Check2:
    lda.l SourceAttackOwned_Busy
    ora.l SourcePacket_CopyBusy
    ora.l SourceAttackOwned_Suppressed
    ora.l Game_StageIndex
    beq SourceAttackReceipt_Check3
    brl SourceAttackReceipt_No
SourceAttackReceipt_Check3:
    lda.l SourceAttackOwned_Camera
    cmp.l Screen_PosX
    beq SourceAttackReceipt_Check4
    brl SourceAttackReceipt_No
SourceAttackReceipt_Check4:
    lda.l DmaQueue+4,x
    and #255
    cmp #$41
    beq SourceAttackReceipt_Check5
    brl SourceAttackReceipt_No
SourceAttackReceipt_Check5:
    lda.l DmaQueue,x
    cmp #544
    beq SourceAttackReceipt_Check6
    brl SourceAttackReceipt_No
SourceAttackReceipt_Check6:
    lda.l DmaQueue+2,x
    beq SourceAttackReceipt_Check7
    brl SourceAttackReceipt_No
SourceAttackReceipt_Check7:
    lda.l DmaQueue+5,x
    cmp #$4F00
    beq SourceAttackReceipt_Check8
    brl SourceAttackReceipt_No
SourceAttackReceipt_Check8:
    lda.l DmaQueue+7,x
    and #255
    cmp #$43
    beq SourceAttackReceipt_Check9
    brl SourceAttackReceipt_No
SourceAttackReceipt_Check9:
    txa
    lsr a
    lsr a
    lsr a
    tax
    lda.l DmaQueue_Owner,x
    and #255
    beq SourceAttackReceipt_Check10
    brl SourceAttackReceipt_No
SourceAttackReceipt_Check10:
    jsl SourceOamReceipt_NoPendingJump
    bcs SourceAttackReceipt_Check11
    brl SourceAttackReceipt_No
SourceAttackReceipt_Check11:
    ; Neither player's new movement may be hidden behind an old full image.
    lda.l $412014
    ora.l $412016
    ora.l $412018
    ora.l $41201A
    ora.l Input_trigger
    and #$0F00
    beq SourceAttackReceipt_Check12
    brl SourceAttackReceipt_No
SourceAttackReceipt_Check12:
    jsl SourceStandby_FaceLive
    bcs SourceAttackReceipt_Check13
    brl SourceAttackReceipt_No
SourceAttackReceipt_Check13:
    jsl SourceAttackMask_PhysicalLive
    bcs SourceAttackReceipt_Yes
SourceAttackReceipt_No:
    ply
    plx
    pla
    plp
    clc
    rtl
SourceAttackReceipt_Yes:
    ply
    plx
    pla
    plp
    sec
    rtl
