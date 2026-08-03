; Multi-bank cross-bank-call test #2: same as bank_test_symbolic.pasm, but
; the jump uses an explicit numeric bank:offset literal ($01:8000) instead
; of a symbolic label reference, to test whether that sidesteps Poppy's
; bank-resolution bug (matching this project's established pattern of
; numeric-fixup workarounds for other Poppy label-resolution bugs -- see
; poppy_assembler_bugs.md bugs 7-8). BankOneRoutine is still labeled for
; documentation, just not referenced symbolically by the jump itself.
.snes
.bank 0
.org $8000
Start:
    sei
    clc
    xce
    rep #$30
.a16
.i16
    ldx #$1fff
    txs
    sep #$20
.a8
    lda #$11
    sta.l $7E1000       ; marker = "about to attempt the cross-bank jump"
    jml $01:8000
Start__hang:
    bra Start__hang

.bank 1
.org $8000
BankOneRoutine:
    lda #$AA
    sta.l $7E1000       ; marker = "bank 1 code actually ran"
BankOneRoutine__hang:
    bra BankOneRoutine__hang
