; Multi-bank cross-bank-call test #1: SYMBOLIC jml reference to a label
; defined under `.bank 1`. Confirmed (see org_test.pasm/jml_test.pasm and
; poppy_assembler_bugs.md bug notes) that Poppy resolves a bank-1 label's
; address with bank byte $00 instead of $01, even though the label's real
; bytes are correctly emitted at the right file offset for bank 1. Expected
; behavior here: `jml BankOneRoutine` assembles to `jml $00:8000` (Start's
; own address), so this hangs re-executing Start forever and the WRAM
; marker at $7E1000 stays $11 (never reaches $AA). Compare against
; bank_test_explicit.pasm, which uses a literal `$01:8000` instead of the
; symbol to confirm whether that's a usable workaround.
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
    jml BankOneRoutine
Start__hang:
    bra Start__hang

.bank 1
.org $8000
BankOneRoutine:
    lda #$AA
    sta.l $7E1000       ; marker = "bank 1 code actually ran"
BankOneRoutine__hang:
    bra BankOneRoutine__hang
