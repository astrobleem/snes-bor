.snes
.bank 0
.org $8000
    dw $1234
    dl $123456
    dw local_label
local_label:
    nop
.bank 1
.org $8000
far_code:
    dw far_code
    rts
