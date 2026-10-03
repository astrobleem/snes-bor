; Opt-in packet transaction. Called from the existing NMI OAM queue consumer.
; X is the live queue slot, DBR/D retain the established NMI convention.
; A 608-byte request owns 544 OAM bytes plus a private 64-byte CGRAM image.
; Both transfers complete in this invocation before the queue clears ACTIVE.
; No main-thread CGRAM write, second admission, or partly committed packet.
S7Palette_Transfer:
    rep #$31
.a16
.i16
    lda.l DmaQueue,x
    cmp #608
    bne S7Palette_Transfer__oam
    lda.l DmaQueue+7,x
    and #255
    cmp #$7F
    bne S7Palette_Transfer__oam
    lda.l DmaQueue+5,x
    cmp #$8D00
    beq S7Palette_Transfer__first
    cmp #$A600
    bne S7Palette_Transfer__oam
    lda #$A880
    bra S7Palette_Transfer__cgram
S7Palette_Transfer__first:
.a16
.i16
    lda #$A840
S7Palette_Transfer__cgram:
.a16
.i16
    sta $4372
    lda #64
    sta $4375
    sep #$20
.a8
    lda #224
    sta $2121
    lda #$7F
    sta $4374
    lda #0
    sta $4370
    lda #$22
    sta $4371
    lda #$80
    sta $420B
    rep #$31
.a16
.i16
; Observe after the first post-$420B instruction boundary: the emulator's exec
; hook before that instruction can run before the pending hardware DMA stalls.
S7Palette_Transfer__completed:
.a16
.i16
    lda #544
    bra S7Palette_Transfer__length
S7Palette_Transfer__oam:
.a16
.i16
    lda.l DmaQueue,x
S7Palette_Transfer__length:
.a16
.i16
    sta $4375
    lda.l DmaQueue+5,x
    sta $4372
    lda.l DmaQueue+2,x
    sta $2102
    sep #$20
.a8
    lda.l DmaQueue+7,x
    sta $4374
    lda #0
    sta $4370
    lda #4
    sta $4371
    lda #$80
    sta $420B
    rep #$31
.a16
.i16
    rtl
