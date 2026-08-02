.snes
.bank 0
.org $8000
    jml far_code
    jmp far_code
.bank 1
.org $8000
far_code:
    rts
