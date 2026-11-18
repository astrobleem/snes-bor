; The pending held transaction will scan each canonical private row below.
; Defer duplicate high-row cancellation to that same scan only in this case.
; Other paths execute the original complete scan, with its exact scopes.
; No new RAM, DMA readiness, owner, camera, publication or retirement policy.
SourceOam_CancelOrFuse:
.a16
.i16
    php
    rep #$30
    pha
    lda.l SourceVisual_CompletedHeld
    and #$00FF
    cmp #1
    bne SourceOam_CancelOriginal
    lda.l SourceVisual_CompletedAwait
    ora.l SourceVisual_CompletedRetire
    beq SourceOam_CancelOriginal
    lda.l Oam_UploadFlag
    cmp #1
    bne SourceOam_CancelOriginal
    bra SourceOam_CancelReturn
SourceOam_CancelOriginal:
.a16
.i16
    jsl SourcePacket_CancelFrameHi
SourceOam_CancelReturn:
.a16
.i16
    pla
    plp
    rtl
SourceOam_CancelEnd:
