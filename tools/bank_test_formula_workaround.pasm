; Multi-bank test #4: is the bank-1 label's LOW 16 BITS correct (only the
; bank byte wrong), or is the whole address wrong? BankOneRoutine sits at
; $8010 here (not $8000, so it can't coincidentally collide with Start's
; own address the way the earlier tests' $8000-vs-$8000 case could) --
; padded with 16 nops first so a resolved offset of $8000 vs $8010 is
; unambiguous.
;
; Result: main.sym reports `00:8010 BankOneRoutine` -- bank byte still
; wrong (00, not 01), but the OFFSET is correct ($8010, matching the real
; padding). So only the bank byte needs a manual fix, not the whole
; address. Tried computing that fix automatically as
; `(BankOneRoutine & $FFFF) | $010000` and assigning it to a named
; constant -- Poppy fails to evaluate that as a jsl operand ("Cannot
; evaluate operand for instruction 'jsl'"), a separate, smaller parser/
; evaluator limitation. A plain numeric literal constant
; (`BANK1_ROUTINE_FIXED = $018010`, computed by hand and verified against
; raw bytes below) works fine and is sufficient -- matching this project's
; existing fixup-constant convention for other Poppy label-resolution bugs
; (poppy_assembler_bugs.md bugs 7-8).
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
    sta.l $7E1000
BANK1_ROUTINE_FIXED = $018010
    jsl BANK1_ROUTINE_FIXED
    lda #$22
    sta.l $7E1001
Start__hang:
    bra Start__hang

.bank 1
.org $8000
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
BankOneRoutine:
    lda #$AA
    sta.l $7E1000
    rtl
