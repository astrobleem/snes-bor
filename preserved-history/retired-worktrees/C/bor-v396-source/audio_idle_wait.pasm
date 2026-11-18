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
    nop
    nop
    nop
    nop ; same single priority service now runs after the field changes
    jsl SourcePrefetch_DuringWait
    lda #0
    pha ; one foreground position attempt at most in this wait
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
    lda 3,s
    cmp.l Nmi_FrameCounter
    bne Tad_StreamWaitFrame__done
    lda 1,s
    bne Tad_StreamWaitFrame__position_done
    jsl SourceReserve_Wait
    bcc Tad_StreamWaitFrame__position_done
    lda #1
    sta 1,s
Tad_StreamWaitFrame__position_done:
.a16
.i16
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
    pla ; discard bounded position-attempt local
    pla
    ply
    plx
    pld
    plb
    plp
    jml SourceFreshWait_ServiceReturn
    nop
    nop
    nop
    nop
