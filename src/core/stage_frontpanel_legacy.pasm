; Relocated accepted Easy commit, instruction-identical except RTS -> RTL.
; NMI DBR=0 required. Bank0 compatibility entry uses JSL here, then RTS.
StageFp_BG2LegacyCommit:
    ; Called from core/nmi.pasm's Core_Nmi_Play, which forces DBR=0 -- every
    ; $7Exxxx access in THIS routine must be explicit .l, not bare .w, same
    ; reason Core_StreamScroll_CommitColumn's own header comment gives.
    sep #$20
.a8
    lda.l StreamScrollFp_ColPending
    bne StageFp_BG2LegacyCommit__go
    rep #$31
.a16
.i16
    rtl
StageFp_BG2LegacyCommit__go:
    ; VMAIN must be freshly set here too, not assumed from Core_StreamScroll_
    ; CommitColumn's own write just above this call in Core_Nmi_Play -- see
    ; that routine's header comment for the exact word-vs-byte shear bug
    ; this guards against. Harmless if it's already $80 (this call runs
    ; right after that one every frame), but re-asserting costs nothing and
    ; removes any ordering assumption between the two.
    sep #$20
.a8
    lda #$80
    sta $2115
    rep #$31
.a16
.i16
    ldx #0
StageFp_BG2LegacyCommit__row:
.a16
.i16
    txa
    cmp #FP_CONTENT_ROW_COUNT
    bcs StageFp_BG2LegacyCommit__done
    asl a
    asl a
    asl a
    asl a
    asl a                       ; A = row * 32 (words between rows in VRAM)
    clc
    adc.l StreamScrollFp_ColTargetWord
    sta $2116
    ; ColBuf index MUST be X, not Y -- see Core_StreamScroll_CommitColumn's
    ; own header comment for the confirmed Poppy bug (`.l Symbol,y` silently
    ; falls back to a wrong-bank, wrong-length absolute,Y) this avoids.
    phx
    txa
    asl a                       ; A = row * 2 (ColBuf is word-indexed)
    tax
    lda.l StreamScrollFp_ColBuf,x
    sep #$20
.a8
    sta $2118
    rep #$31
.a16
.i16
    lda.l StreamScrollFp_ColBuf,x
    xba
    sep #$20
.a8
    sta $2119
    rep #$31
.a16
.i16
    plx                          ; restore the row counter
    inx
    bra StageFp_BG2LegacyCommit__row
StageFp_BG2LegacyCommit__done:
    sep #$20
.a8
    lda #0
    sta.l StreamScrollFp_ColPending
    rep #$31
.a16
.i16
    rtl
