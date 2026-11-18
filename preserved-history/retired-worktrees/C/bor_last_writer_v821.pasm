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
    lda.l SourceAttackOwned_Stages
    sta.l SourceOamReceipt_Stages
    lda #1
    sta.l SourceOamReceipt_Valid
SourceOamReceipt_AckDone:
.a16
.i16
    pla
    plp
    rtl

; READ-ONLY veto at the cancellation decision, not a one-shot input clear.
; Caller is S-CPU NMI: native state and worker input mailboxes cannot be
; concurrently changed by foreground. SA1 completion is fenced twice.
SourceOamReceipt_NoPendingJump:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    lda.l $412008
    ora.l $41200C
    beq SourceJumpCheck_0
    brl SourceJumpCheck_No
SourceJumpCheck_0:
.a16
.i16
    lda.l $412440
    cmp.l $412442
    beq SourceJumpCheck_3
    brl SourceJumpCheck_No
SourceJumpCheck_3:
.a16
.i16
    lda.l $412002
    cmp.l $412004
    beq SourceJumpCheck_6
    brl SourceJumpCheck_No
SourceJumpCheck_6:
.a16
.i16
    tay
    lda.l $434E7E
    cmp #$4D50
    beq SourceJumpCheck_9
    brl SourceJumpCheck_No
SourceJumpCheck_9:
.a16
.i16
    lda.l $434E7C
    bit #1
    beq SourceJumpCheck_12
    brl SourceJumpCheck_No
SourceJumpCheck_12:
.a16
.i16
    tax
    lda.l $434E2E
    inc a
    and #511
    cmp.l $412004
    beq SourceJumpCheck_15
    brl SourceJumpCheck_No
SourceJumpCheck_15:
.a16
.i16
    lda.l $412014
    ora.l $412016
    ora.l $412018
    ora.l $41201A
    ora.l Input_trigger
    and #$80
    beq SourceJumpCheck_18
    brl SourceJumpCheck_No
SourceJumpCheck_18:
.a16
.i16
    lda.l $7E0A00+CHAR_SELECTED
    and #255
    cmp #3
    bcc SourceJumpCheck_21
    brl SourceJumpCheck_No
SourceJumpCheck_21:
.a16
.i16
    lda.l $7E0A00+CHAR_THROW_ZPOS
    beq SourceJumpCheck_24
    brl SourceJumpCheck_No
SourceJumpCheck_24:
.a16
.i16
    lda.l $7E0A85+CHAR_SELECTED
    and #255
    cmp #3
    bcc SourceJumpCheck_27
    brl SourceJumpCheck_No
SourceJumpCheck_27:
.a16
.i16
    lda.l $7E0A85+CHAR_THROW_ZPOS
    beq SourceJumpCheck_30
    brl SourceJumpCheck_No
SourceJumpCheck_30:
.a16
.i16
    txa
    cmp.l $434E7C
    beq SourceJumpCheck_33
    brl SourceJumpCheck_No
SourceJumpCheck_33:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    beq SourceJumpCheck_36
    brl SourceJumpCheck_No
SourceJumpCheck_36:
.a16
.i16
    tya
    cmp.l $412002
    beq SourceJumpCheck_39
    brl SourceJumpCheck_No
SourceJumpCheck_39:
.a16
.i16
    cmp.l $412004
    beq SourceJumpCheck_42
    brl SourceJumpCheck_No
SourceJumpCheck_42:
.a16
.i16
    lda.l $412008
    ora.l $41200C
    beq SourceJumpCheck_45
    brl SourceJumpCheck_No
SourceJumpCheck_45:
.a16
.i16
    lda.l $412440
    cmp.l $412442
    beq SourceJumpCheck_48
    brl SourceJumpCheck_No
SourceJumpCheck_48:
.a16
.i16
    ply
    plx
    pla
    plp
    sec
    rtl
SourceJumpCheck_No:
.a16
.i16
    ply
    plx
    pla
    plp
    clc
    rtl

SourceOamReceipt_End:
.assert SourceOamReceipt_End <= $27B000, "receipt helper exceeds verified gap"
