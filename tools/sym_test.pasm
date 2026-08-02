.snes
.bank 0
.org $8000
    dw far_code
    dl far_code
.bank 1
.org $8000
far_code:
    rts
