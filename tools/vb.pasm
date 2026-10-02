.snes
.bank 0
.org $8000
    nop
.org $9000
    lda #$22
.bank 1
.org $8000
    lda #$33
    rts
