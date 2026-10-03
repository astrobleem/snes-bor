; NMI consumer-side protection of the compiler's pinned OBJ blocks. A late
; legacy upload cannot defeat an earlier model/slot validation. No source
; pixels are modified on rejection. Exact compiler entry requests remain
; permitted until entry completes; all other writes must avoid leased bytes.
; AD28 armed; AD2A..AD34 NMI-only range/index/rejection scratch.
S7Lease_Admit:
    rep #$30
.a16
.i16
    phx
    lda #0
    sta.l $7FAD32
    lda.l $7FAD28
    bne S7Lease_Admit__armed
    brl S7Lease_Admit__pass
S7Lease_Admit__armed:
.a16
.i16
    txa
    sta.l $7FAD30
    lda.l DmaQueue+2,x
    and #$FFFE
    sta.l $7FAD2A
    lda.l DmaQueue,x
    bne S7Lease_Admit__length
    brl S7Lease_Admit__deny
S7Lease_Admit__length:
.a16
.i16
    clc
    adc.l $7FAD2A
    bcc S7Lease_Admit__end
    brl S7Lease_Admit__deny
S7Lease_Admit__end:
.a16
.i16
    cmp #$8001
    bcs S7Lease_Admit__upper
    brl S7Lease_Admit__pass
S7Lease_Admit__upper:
.a16
.i16
    cmp #$C000
    bcc S7Lease_Admit__clamped
    lda #$C000
S7Lease_Admit__clamped:
.a16
.i16
    dec a
    sec
    sbc #$8000
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    sta.l $7FAD2E
    lda.l $7FAD2A
    cmp #$C000
    bcc S7Lease_Admit__lower
    brl S7Lease_Admit__pass
S7Lease_Admit__lower:
.a16
.i16
    cmp #$8000
    bcs S7Lease_Admit__start
    lda #$8000
S7Lease_Admit__start:
.a16
.i16
    sec
    sbc #$8000
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    tax
S7Lease_Admit__scan:
.a16
.i16
    lda.l S7Lease_Segments,x
    and #255
    bne S7Lease_Admit__entry
    txa
    cmp.l $7FAD2E
    bcs S7Lease_Admit__pass
    inx
    bra S7Lease_Admit__scan
S7Lease_Admit__entry:
.a16
.i16
    lda.l S7Pub_State+6
    bne S7Lease_Admit__deny
    lda.l S7Pub_State
    cmp #S7Pub_TransferCount
    bcs S7Lease_Admit__deny
    asl a
    asl a
    asl a
    tax
    ; Compare the entire immutable descriptor to the actual queued request.
    lda.l S7Pub_Transfers,x
    pha
    lda.l S7Pub_Transfers+2,x
    pha
    lda.l S7Pub_Transfers+4,x
    pha
    lda.l S7Pub_Transfers+6,x
    and #$03FF
    pha
    lda.l $7FAD30
    tax
    pla
    sta.l $7FAD2C
    lda.l DmaQueue+7,x
    and #255
    sta.l $7FAD34
    lda.l DmaQueue+4,x
    and #3
    xba
    ora.l $7FAD34
    eor.l $7FAD2C
    sta.l $7FAD2C
    pla
    eor.l DmaQueue,x
    ora.l $7FAD2C
    sta.l $7FAD2C
    pla
    eor.l DmaQueue+2,x
    ora.l $7FAD2C
    sta.l $7FAD2C
    pla
    eor.l DmaQueue+5,x
    ora.l $7FAD2C
    bne S7Lease_Admit__deny
S7Lease_Admit__pass:
.a16
.i16
    plx
    sec
    rtl
S7Lease_Admit__deny:
.a16
.i16
    lda #1
    sta.l $7FAD32
    lda #$D70D
    sta.l S7Pub_State+$FE
S7Lease_Admit__denied:
.a16
.i16
    plx
    clc
    rtl

S7Lease_AdmitCgram:
    rep #$30
.a16
.i16
    phx
    lda #0
    sta.l $7FAD32
    lda.l $7FAD28
    bne S7Lease_AdmitCgram__armed
    brl S7Lease_Admit__pass
S7Lease_AdmitCgram__armed:
.a16
.i16
    txa
    sta.l $7FAD30
    lda.l DmaQueue+2,x
    and #$01FE
    sta.l $7FAD2A
    lda.l DmaQueue,x
    bne S7Lease_AdmitCgram__length
    brl S7Lease_Admit__deny
S7Lease_AdmitCgram__length:
.a16
.i16
    clc
    adc.l $7FAD2A
    bcc S7Lease_AdmitCgram__range
    brl S7Lease_Admit__deny
S7Lease_AdmitCgram__range:
.a16
.i16
    cmp #449
    bcs S7Lease_AdmitCgram__owned
    brl S7Lease_Admit__pass
S7Lease_AdmitCgram__owned:
.a16
.i16
    brl S7Lease_Admit__entry
