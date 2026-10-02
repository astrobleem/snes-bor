; Multi-bank cross-bank-call test #3: a full jsl/rtl round trip using the
; explicit bank:offset workaround confirmed in bank_test_explicit.pasm, to
; prove the actually-useful pattern (call into bank 1, return, keep running
; in bank 0) works, not just a one-way jml. marker1 proves bank 1 code ran;
; marker2 proves control genuinely returned to bank 0 afterward (not just
; that bank 1 ran and then hung/crashed).
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
    sta.l $7E1000       ; marker1 = "about to call bank 1"
    jsl $01:8000        ; explicit bank:offset -- BankOneRoutine's address
    lda #$22
    sta.l $7E1001       ; marker2 = "control returned to bank 0 after rtl"
Start__hang:
    bra Start__hang

.bank 1
.org $8000
BankOneRoutine:
    lda #$AA
    sta.l $7E1000       ; marker1 = "bank 1 code ran"
    rtl
