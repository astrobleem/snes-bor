; Multi-bank .org verification test for Poppy
.snes
.bank 0
.org $8000
reset:
    nop                 ; $8000: EA
    nop                 ; $8001: EA
    jmp far_bank_code   ; 3-byte JML to bank 1 label

.org $8100
marker0:
    nop                 ; padding marker at bank 0

.bank 1
.org $8000
far_bank_code:
    lda #$42            ; bank 1 code: A9 42
    rts
