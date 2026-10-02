; Explicit source-publication lifecycle, not a simulation pause or frame delay.
; Request word $7FA8C0: 1 close, 2 reopen the same compiler-admitted set.
; A close does not release until the hidden replacement OAM packet completes.
; Reopen is rejected while any old packet owns memory or hardware references.
; $7FA8C2 is the hardware-release cookie, $7FA8C4 the completed reopen generation.
S7Epoch_Service:
    rep #$30
.a16
.i16
    lda.l $7FA8C0
    beq S7Epoch_Service__done
    cmp #1
    beq S7Epoch_Service__close
    cmp #2
    bne S7Epoch_Service__reject
    lda.l S7Pub_State+$F2
    cmp #3
    bne S7Epoch_Service__reject
    lda.l $7FA8C2
    cmp #1
    bne S7Epoch_Service__reject
    jsl S7Packet_Poll
    jsl S7Packet2_Poll
    lda.l $7F8F20
    ora.l $7FA820
    bne S7Epoch_Service__done
    lda.l S7Pub_State+6
    bne S7Epoch_Service__reject
    lda #0
    sta.l S7Pub_State
    sta.l S7Pub_State+2
    sta.l S7Pub_State+4
    sta.l $7FA8C0
    sta.l $7FA8C2
    lda #4
    sta.l S7Pub_State+$F2
    rtl
S7Epoch_Service__close:
.a16
.i16
    lda.l S7Pub_State+$F2
    bne S7Epoch_Service__reject
    lda #1
    sta.l S7Pub_State+$F2
    lda #0
    sta.l $7FA8C0
    rtl
S7Epoch_Service__reject:
.a16
.i16
    lda #$D707
    sta.l S7Pub_State+$FE
    lda #0
    sta.l $7FA8C0
S7Epoch_Service__done:
.a16
.i16
    rtl

S7Epoch_Reopen:
    jsl S7Publisher_Entry
    bcc S7Epoch_Reopen__done
    rep #$30
.a16
.i16
    lda #0
    sta.l S7Pub_State+$F2
    lda.l $7FA8C4
    inc a
    sta.l $7FA8C4
S7Epoch_Reopen__done:
.a16
.i16
    rtl
