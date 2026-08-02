.snes
.bank 0
.org $8000

reset:
    sei
    clc
    xce
    rep #$30
.a16
.i16
    lda #$1fff
    tcs
    sep #$20
.a8
    lda #$8f
    sta $2100
    lda #$01
    sta $2105
    ldx #$00
loop:
    lda #$ff
    sta $2118
    lda #$00
    sta $2119
    inx
    cpx #$100
    bne loop
    bra loop

.org $FFE4
    .word $0000
    .word $0000
    .word $0000
    .word $0000
    .word $0000
    .word $0000

.org $FFF4
    .word $0000
    .word $0000
    .word $0000
    .word $0000
    .word $0000
    .word $0000
    .word reset
    .word $0000
