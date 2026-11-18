; Skip redundant cleanup only when both words it clears are already zero.
; A stale full-cache certificate still follows the original protection path.
; No new RAM or resource policy. Called with X=physical cache byte offset.
SourceRelease_ProtectOrEmpty:
.a8
.i16
    php
    rep #$30
.a16
.i16
    pha
    lda.l SourceVisual_BlockCache+2,x
    bne SourceRelease_Original
    lda.l SourceVisual_BlockCache+6,x
    bne SourceRelease_Original
    lda.l SourceVisual_BucketMagic
    cmp #$B17B
    beq SourceRelease_Original
SourceRelease_Empty:
    pla
    plp
    sec
    rtl
SourceRelease_Original:
.a16
.i16
    jsl SourcePalette_Bridge_SVActor_Enabled
    bcc SourceRelease_No
    lda.l SVActor_HeldBlocks,x
    ora.l SVActor_OldBlocks,x
    and #$00FF
    beq SourceRelease_No
    pla
    plp
    sec
    rtl
SourceRelease_No:
.a16
.i16
    pla
    plp
    clc
    rtl
SourceRelease_End:
