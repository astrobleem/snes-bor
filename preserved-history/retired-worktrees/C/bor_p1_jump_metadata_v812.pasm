.org $FE80
; Enter with the original metadata P1end in A. Mask1/start0 were checked.
SourceP1Jump_MetadataUnified:
.a16
.i16
    cmp #32
    beq SourceP1Jump_Eight
    cmp #36
    beq SourceP1Jump_Nine
    jmp.w SourceNormalize_No
SourceP1Jump_Eight:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+32
    cmp #32
    beq SourceP1Jump_EightPeer
    jmp.w SourceNormalize_No
SourceP1Jump_EightPeer:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+34
    cmp #72
    bne SourceP1Jump_EightJump
    jml SourceNormalize_Guard4
SourceP1Jump_EightJump:
.a16
.i16
    cmp #68
    beq SourceP1Jump_Common
    jmp.w SourceNormalize_No
SourceP1Jump_Nine:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+32
    cmp #36
    beq SourceP1Jump_NinePeer
    jmp.w SourceNormalize_No
SourceP1Jump_NinePeer:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+34
    cmp #72
    beq SourceP1Jump_Common
    jmp.w SourceNormalize_No
SourceP1Jump_Common:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+12
    cmp #$0716
    beq SourceP1Jump_C0
    jmp.w SourceNormalize_No
SourceP1Jump_C0:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+44
    cmp #$0716
    beq SourceP1Jump_C1
    jmp.w SourceNormalize_No
SourceP1Jump_C1:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+16
    cmp #1
    beq SourceP1Jump_C2
    jmp.w SourceNormalize_No
SourceP1Jump_C2:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+48
    cmp #1
    beq SourceP1Jump_C3
    jmp.w SourceNormalize_No
SourceP1Jump_C3:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+8
    cmp #22
    beq SourceP1Jump_C4
    jmp.w SourceNormalize_No
SourceP1Jump_C4:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+40
    cmp #22
    beq SourceP1Jump_C5
    jmp.w SourceNormalize_No
SourceP1Jump_C5:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+6
    cmp #150
    beq SourceP1Jump_C6
    jmp.w SourceNormalize_No
SourceP1Jump_C6:
.a16
.i16
    lda.l SourceAttackOwned_Hold
    ora.l $7E0A00+CHAR_THROW_ZPOS
    ora.l $7E0A85+CHAR_THROW_ZPOS
    beq SourceP1Jump_C7
    jmp.w SourceNormalize_No
SourceP1Jump_C7:
.a16
.i16
    lda.l $7E0A00+CHAR_SELECTED
    and #255
    cmp #3
    bcc SourceP1Jump_C8
    jmp.w SourceNormalize_No
SourceP1Jump_C8:
.a16
.i16
    lda.l $7E0A85+CHAR_SELECTED
    and #255
    cmp #3
    bcc SourceP1Jump_C9
    jmp.w SourceNormalize_No
SourceP1Jump_C9:
.a16
.i16
    lda.l $411AE6
    and #255
    cmp #8
    beq SourceP1Jump_Tail
    jmp.w SourceNormalize_No
SourceP1Jump_Tail:
.a16
.i16
    lda.l $434F00+508
    cmp #$E0C0
    beq SourceP1Jump_T0
    jmp.w SourceNormalize_No
SourceP1Jump_T0:
.a16
.i16
    lda.l $434F00+510
    beq SourceP1Jump_T1
    jmp.w SourceNormalize_No
SourceP1Jump_T1:
.a16
.i16
    lda.l $434F00+543
    and #$00C0
    cmp #$0040
    beq SourceP1Jump_T2
    jmp.w SourceNormalize_No
SourceP1Jump_T2:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+2
    cmp #36
    beq SourceP1Jump_Seal
    lda.l $434F00+504
    cmp #$E0C0
    beq SourceP1Jump_T3
    jmp.w SourceNormalize_No
SourceP1Jump_T3:
.a16
.i16
    lda.l $434F00+506
    beq SourceP1Jump_T4
    jmp.w SourceNormalize_No
SourceP1Jump_T4:
.a16
.i16
    lda.l $434F00+543
    and #$0030
    cmp #$0010
    beq SourceP1Jump_Seal
    jmp.w SourceNormalize_No
SourceP1Jump_Seal:
.a16
.i16
SourceP1Jump_Yes:
.a16
.i16
    sec
    rtl
SourceP1Jump_End:
.assert SourceP1Jump_End <= $3D0000, "P1 metadata exceeds audited bank tail"
