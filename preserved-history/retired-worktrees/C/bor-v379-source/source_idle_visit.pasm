; Existing idle-only critical seam. Preserve the original metadata warm,
; then service the proven reserved idle transaction before the late actor tail.
; Attacks/jumps never enter this hook; original ownership/coherence checks stay.
SourceIdleVisit:
.a16
.i16
    jsl SourceCritical_Bridge_SourceIdleMetadata
    php
    rep #$30
    pha
    lda.l SourceReserve_Valid
    cmp #$1D1F
    bne SourceIdleVisit_Done
    lda.l SourceSecond_Consumed
    bne SourceIdleVisit_Done
    lda.l SOURCE_PACKET_ACTIVE_META+18
    bne SourceIdleVisit_Done
    lda.l SOURCE_PACKET_ACTIVE_META+50
    bne SourceIdleVisit_Done
    lda.l $434E3C
    cmp #9
    bne SourceIdleVisit_Done
    lda.l $434E60
    cmp #9
    bne SourceIdleVisit_Done
    lda.l $434E3A
    and #255
    bne SourceIdleVisit_Done
    lda.l $434E5E
    and #255
    bne SourceIdleVisit_Done
    lda.l $434E50
    and #255
    bne SourceIdleVisit_Done
    lda.l $434E74
    and #255
    bne SourceIdleVisit_Done
SourceIdleVisit_Service:
.a16
.i16
    jsl SourceSecond_Dispatch
SourceIdleVisit_Done:
.a16
.i16
    pla
    plp
    rtl
SourceIdleVisit_End:
