; Foreground-only replacement for the bank-0 NMI wait. Stream producers may
; poll ACK / stage the next descriptor while waiting; existing per-field
; budgeting still controls submissions. No audio work is added to NMI.
; Preserve the original REP #$31 / old-counter A / final CMP contract, and
; all X/Y/D/DBR state. Return through the original bank-0 RTS for JSR callers.
Tad_StreamWaitFrame:
.a16
.i16
    rep #$31
    php
    phb
    phd
    phx
    phy
    lda.l Nmi_FrameCounter
    pha
    cld
    lda #0
    tcd
    sep #$20
.a8
    pha
    plb
    rep #$30
.a16
.i16
Tad_StreamWaitFrame__loop:
.a16
.i16
    lda 1,s
    cmp.l Nmi_FrameCounter
    bne Tad_StreamWaitFrame__done
    sep #$20
.a8
    lda.l AudioStream_Enable
    beq Tad_StreamWaitFrame__no_pump
    lda.l AudioSemantic_FootDieStreamActive
    beq Tad_StreamWaitFrame__no_pump
    jsl Tad_StreamLatePump
Tad_StreamWaitFrame__no_pump:
.a8
.i16
    rep #$30
.a16
.i16
    bra Tad_StreamWaitFrame__loop
Tad_StreamWaitFrame__done:
.a16
.i16
    pla
    ply
    plx
    pld
    plb
    plp
    cmp.l Nmi_FrameCounter
    jml Core_Nmi_WaitFrame__return
