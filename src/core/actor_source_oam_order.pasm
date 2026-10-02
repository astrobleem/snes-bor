; Opt-in two-packet ordering at the existing hardware consumer.
; Enqueue may be interrupted after sampling the drain cursor. Two publication
; requests can consequently occupy reverse ring order. Exchange only their
; immutable source pointers, never tiles, lengths, ACTIVE bits or other DMA.
; Main is suspended during this NMI operation. Poll resolves actual queue
; ownership rather than trusting a stale saved ring index.
; C8: producer ticket; CA/CC/CE: NMI-only current slot/ticket/source scratch.
S7Oam_Order:
    php
    rep #$30
.a16
.i16
    phx
    phy
    lda #0
    sta.l $7FAD24
    lda.l DmaQueue,x
    cmp #544
    beq S7Oam_Order__length_ok
    cmp #608
    beq S7Oam_Order__length_ok
    jmp S7Oam_Order__done
S7Oam_Order__length_ok:
.a16
.i16
    lda.l DmaQueue+7,x
    and #255
    cmp #$7F
    beq S7Oam_Order__bank_ok
    jmp S7Oam_Order__done
S7Oam_Order__bank_ok:
.a16
.i16
    txa
    sta.l $7FA8CA
    lda.l DmaQueue+5,x
    sta.l $7FA8CE
    cmp #$8D00
    beq S7Oam_Order__first
    cmp #$A600
    beq S7Oam_Order__second
    jmp S7Oam_Order__done
S7Oam_Order__first:
.a16
.i16
    lda.l $7F8F38
    sta.l $7FA8CC
    ldy #$A600
    bra S7Oam_Order__scan_start
S7Oam_Order__second:
.a16
.i16
    lda.l $7FA838
    sta.l $7FA8CC
    ldy #$8D00
S7Oam_Order__scan_start:
.a16
.i16
    ldx #0
S7Oam_Order__scan:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$43
    cmp #$41
    bne S7Oam_Order__next
    lda.l DmaQueue+7,x
    and #255
    cmp #$7F
    bne S7Oam_Order__next
    tya
    cmp.l DmaQueue+5,x
    bne S7Oam_Order__next
    phx
    lda.l $7FA8CA
    tax
    lda.l DmaQueue,x
    plx
    cmp.l DmaQueue,x
    bne S7Oam_Order__mismatched
    tya
    cmp #$8D00
    beq S7Oam_Order__other_first
    lda.l $7FA8CC
    sec
    sbc.l $7FA838
    bra S7Oam_Order__compare
S7Oam_Order__other_first:
.a16
.i16
    lda.l $7FA8CC
    sec
    sbc.l $7F8F38
S7Oam_Order__compare:
.a16
.i16
    beq S7Oam_Order__done
    bmi S7Oam_Order__done
    ; At most two tickets are live; modular distance is always below $8000.
    lda.l DmaQueue+5,x
    pha
    lda.l $7FA8CE
    sta.l DmaQueue+5,x
    lda.l $7FA8CA
    tax
    pla
    sta.l DmaQueue+5,x
S7Oam_Order__swapped:
.a16
.i16
    bra S7Oam_Order__done
S7Oam_Order__mismatched:
.a16
.i16
    lda #$D70B
    sta.l S7Pub_State+$FE
    lda #1
    sta.l $7FAD24
    bra S7Oam_Order__done
S7Oam_Order__next:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcs S7Oam_Order__done
    brl S7Oam_Order__scan
S7Oam_Order__done:
.a16
.i16
    ply
    plx
    plp
    rtl
