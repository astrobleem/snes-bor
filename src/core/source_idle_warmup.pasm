; Called only in the ordinary ReadRow prologue, after Seek. Leave the MSU
; cursor alone and retain the original REP31/LDX0 ABI. Optional work uses
; the unchanged original neutral-input/ready-idle private prefetch planner.
; At most ten successful private jobs across this bootstrap opportunity.
SourceWarmup_Row:
.a8
.i16
    rep #$31
.a16
.i16
    php
    pha
    lda.l SourcePrefetch_Submitted
    cmp #10
    bcs SourceWarmup_Done
    lda.l SourcePrefetch_Cursor
    cmp #10
    bcs SourceWarmup_Done
    lda.l SourceVisual_FieldPress1
    ora.l SourceVisual_FieldPress2
    bne SourceWarmup_Done
    jsl SourcePrefetch_DuringWait
SourceWarmup_Done:
.a16
.i16
    pla
    plp
    ldx #0
    rtl
SourceWarmup_End:
