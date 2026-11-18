; Recovery-only eligibility. All readiness/identity/pin checks following the
; original threshold remain authoritative. Startup and ordinary cursor rules
; are unchanged. No resource, queue, input or ACK writes in these helpers.
.bank 5
.org $C000
SourceRecover_Threshold:
.a16
.i16
    lda.l SourcePrefetch_Cursor
    cmp #10
    bcs SourceRecover_ThresholdDone
    cmp #0
    beq SourceRecover_ThresholdOriginal
    pha
    lda.l $437BAC
    cmp #2
    bne SourceRecover_ThresholdRestore
    pla
    lda #10
    cmp #10
SourceRecover_ThresholdDone:
.a16
.i16
    rtl
SourceRecover_ThresholdRestore:
.a16
.i16
    pla
SourceRecover_ThresholdOriginal:
.a16
.i16
    cmp #10
    rtl

; The batched root plan already permits directions in unconsumed ring rows.
; Match its latest-row policy only during pressure recovery. Retry/burst
; eligibility still uses the original neutral-only NoPendingInput routine.
SourceRecover_PlanLatest:
.a16
.i16
    php
    lda.l $437BAC
    cmp #2
    bne SourceRecover_LatestOriginal
    plp
    lda.l SourceInput_Ring,x
    ora.l SourceInput_Ring+2,x
    and #$F0FF
    rtl
SourceRecover_LatestOriginal:
.a16
.i16
    plp
    lda.l SourceInput_Ring,x
    ora.l SourceInput_Ring+2,x
    rtl

SourceRecover_WarmRoles:
.a16
.i16
    php
    lda.l $437BAC
    cmp #2
    bne SourceRecover_WarmRolesOriginal
    plp
    lda.l $434E50
    ora.l $434E74
    and #$FFFE
    rtl
SourceRecover_WarmRolesOriginal:
.a16
.i16
    plp
    lda.l $434E50
    ora.l $434E74
    rtl

; Template maps are hints only. A stale map selects a candidate index but
; never makes a block ready: the original plan scans/authenticates the ID,
; state, pins, queue and physical cookie. Worst case ten constant-size probes.
SourceRecover_ChooseCursor:
.a16
.i16
    phx
    ldx #9
SourceRecover_CursorLoop:
.a16
.i16
    phx
    txa
    asl a
    tax
    lda.l SourcePrefetch_HotIds,x
    pha
    txa
    lsr a
    tax
    lda.l $436CF8,x
    and #255
    cmp #64
    bcs SourceRecover_CursorMissing
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_BlockCache,x
    cmp 1,s
    bne SourceRecover_CursorMissing
    lda.l SourceVisual_BlockCache+2,x
    cmp #2
    bne SourceRecover_CursorMissing
    pla
    plx
    dex
    bpl SourceRecover_CursorLoop
    lda #0
    bra SourceRecover_CursorStore
SourceRecover_CursorMissing:
.a16
.i16
    pla
    pla
SourceRecover_CursorStore:
.a16
.i16
    sta.l SourcePrefetch_Cursor
    plx
    rtl
