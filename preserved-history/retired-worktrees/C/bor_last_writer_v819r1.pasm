; Receipt instrumentation only. No queue cancellation/admission/pin changes.
; Source build metadata ends434E9F; this24-byte private stage0 record is in
; the previously exercised transaction arena before immutable image434F00.
SourceOamReceipt_Base = $434EA0
SourceOamReceipt_Magic = $434EA0
SourceOamReceipt_Valid = $434EA2
SourceOamReceipt_Ack = $434EA4
SourceOamReceipt_Low = $434EA6
SourceOamReceipt_High = $434EA8
SourceOamReceipt_Mask = $434EAA
SourceOamReceipt_Stage = $434EAC
SourceOamReceipt_Camera = $434EAE
SourceOamReceipt_Stages = $434EB0
SourceOamReceipt_Field = $434EB2
SourceOamReceipt_CommonAck = $434EB4
.org $AE00
SourceOamReceipt_Init:
.a16
.i16
    sta.l SourceAttackOwned_SourceHi
    php
    rep #$30
    pha
    phx
    lda #0
    ldx #22
SourceOamReceipt_Clear:
.a16
.i16
    sta.l SourceOamReceipt_Base,x
    dex
    dex
    bpl SourceOamReceipt_Clear
    lda #$5257
    sta.l SourceOamReceipt_Magic
    plx
    pla
    plp
    rtl
; Called only AFTER real OAM transport returned, preserving caller ABI.
SourceOamReceipt_Invalidate:
.a16
.i16
    php
    rep #$30
    pha
    lda.l SourceOamReceipt_Magic
    cmp #$5257
    bne SourceOamReceipt_InvalidDone
    lda #0
    sta.l SourceOamReceipt_Valid
SourceOamReceipt_InvalidDone:
.a16
.i16
    pla
    plp
    rtl
SourceOamReceipt_QueuedTransfer:
.a8
.i16
    sta $420B
    rep #$31
.a16
.i16
    jsl SourceOamReceipt_Invalidate
    rtl
SourceOamReceipt_DirectTransfer:
.a8
.i16
    php
    rep #$30
.a16
.i16
    pha
    jsl SourceOamReceipt_Invalidate
    lda.l SourceOamReceipt_Magic
    cmp #$5257
    bne SourceOamReceipt_DirectGo
    lda.l SourceAttackOwned_InitMagic
    cmp #$B077
    bne SourceOamReceipt_DirectGo
    lda.l SourceAttackOwned_Use
    cmp #1
    bne SourceOamReceipt_DirectGo
    lda.l SourceAttackOwned_State
    cmp #1
    bne SourceOamReceipt_DirectGo
    lda.l $004372
    cmp #$7600
    bne SourceOamReceipt_DirectGo
    lda.l $004374
    and #255
    cmp #$43
    bne SourceOamReceipt_DirectGo
    lda.l $004375
    cmp #544
    bne SourceOamReceipt_DirectGo
    lda.l $004370
    cmp #$0400
    bne SourceOamReceipt_DirectGo
    lda #2
    sta.l SourceOamReceipt_Valid
SourceOamReceipt_DirectGo:
.a16
.i16
    pla
    plp
.a8
.i16
    sta.l $00420B
    rtl
; Replaces the original final AckField store. Only this post-success private
; ACK path authorizes a receipt. No Ready, pending, claim or scene is changed.
SourceOamReceipt_PrivateAck:
.a16
.i16
    sta.l SourceAttackOwned_AckField
    php
    rep #$30
    pha
    lda.l SourceOamReceipt_Magic
    cmp #$5257
    bne SourceOamReceipt_AckDone
    lda.l SourceOamReceipt_Valid
    cmp #2
    bne SourceOamReceipt_AckDone
    lda #0
    sta.l SourceOamReceipt_Valid
    lda.l SourceAttackOwned_PhysicalAcks
    sta.l SourceOamReceipt_Ack
    lda.l SourceAttackOwned_PhysicalLow
    sta.l SourceOamReceipt_Low
    lda.l SourceAttackOwned_PhysicalHigh
    sta.l SourceOamReceipt_High
    lda.l $437A9A
    sta.l SourceOamReceipt_Mask
    lda.l Game_StageIndex
    sta.l SourceOamReceipt_Stage
    lda.l SourceAttackOwned_Camera
    sta.l SourceOamReceipt_Camera
    lda.l SourceAttackOwned_Stages
    sta.l SourceOamReceipt_Stages
    lda.l SourceAttackOwned_AckField
    sta.l SourceOamReceipt_Field
    lda.l SourceVisual_CompletedAcks
    sta.l SourceOamReceipt_CommonAck
    lda #1
    sta.l SourceOamReceipt_Valid
SourceOamReceipt_AckDone:
.a16
.i16
    pla
    plp
    rtl
SourceOamReceipt_End:
.assert SourceOamReceipt_End <= $27B000, "receipt helper exceeds verified gap"
