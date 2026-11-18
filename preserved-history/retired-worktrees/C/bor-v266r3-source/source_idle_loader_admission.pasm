; C1 at THIS compositor seam means "visit the normal loader", not Ready.
; First idle already has an exact accepted walk-to-idle eligibility guard.
; Avoid warming and physically scanning its metadata twice: the unchanged
; ordinary loader still reads pieces, checks every DMA fence, allocates/pins,
; admits palettes and validates publication. No cache Ready/queue/world writes.
SourceIdle_AdmissionOrCritical:
.a16
.i16
    php
    pha
    lda.l SourceVisual_Key
    cmp #$0016
    bne SourceIdle_AdmissionFallback
    lda.l SourceVisual_ServiceOnly
    bne SourceIdle_AdmissionFallback
    jsl SourceIdle_CanFinish
    bcc SourceIdle_AdmissionFallback
    phx
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+29,x
    plx
    cmp #$0016
    bne SourceIdle_AdmissionFallback
SourceIdle_AdmissionAllowed:
.a16
.i16
    pla
    plp
    sec
    rtl
SourceIdle_AdmissionFallback:
.a16
.i16
    pla
    plp
    jml SourceCritical_CompleteReady
SourceIdle_AdmissionEnd:
