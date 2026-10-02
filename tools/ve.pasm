.snes
.bank 0
.org $8000
reset:
    nop
.bank 1
.org $8000
sa1_code:
    lda #$66
    rts
.bank 0
.org $FFE0
vectors:
    nop
    nop
