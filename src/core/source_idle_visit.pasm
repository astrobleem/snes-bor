; Existing idle-only critical seam. Preserve the original metadata warm,
; then service the proven reserved idle transaction before the late actor tail.
; Attacks/jumps never enter this hook; original ownership/coherence checks stay.
SourceIdleVisit:
.a16
.i16
    jsl SourceCritical_Bridge_SourceIdleMetadata
; Same transaction may run before metadata loading at an exact idle0 key.
SourceIdleVisit_Check:
.a16
.i16
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

; Same bounded policy as SourcePacket_PrepareGeometry: retry only a torn
; producer snapshot, at most twice with64 polls each. No NMI entry, field wait,
; template recopy, pin rotation or relaxation of the original reader fences.
SourceSecond_FinalRefresh:
.a16
.i16
    jsl SourcePacket_ForegroundPrepare
    php
    rep #$30
    pha
    phx
    lda.l SourcePacket_RefreshAccepted
    cmp #1
    beq SourceSecond_FinalRefresh_Done
    lda.l SourcePacket_MainRetryNeeded
    cmp #1
    bne SourceSecond_FinalRefresh_Done
    ldx #64
SourceSecond_FinalRefresh_Wait1:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    bne SourceSecond_FinalRefresh_Next1
    lda.l $434E7C
    and #1
    beq SourceSecond_FinalRefresh_Read1
SourceSecond_FinalRefresh_Next1:
.a16
.i16
    dex
    bne SourceSecond_FinalRefresh_Wait1
    bra SourceSecond_FinalRefresh_Done
SourceSecond_FinalRefresh_Read1:
.a16
.i16
    jsl SourcePacket_ForegroundPrepare
    lda.l SourcePacket_RefreshAccepted
    cmp #1
    beq SourceSecond_FinalRefresh_Done
    lda.l SourcePacket_MainRetryNeeded
    cmp #1
    bne SourceSecond_FinalRefresh_Done
    ldx #64
SourceSecond_FinalRefresh_Wait2:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    bne SourceSecond_FinalRefresh_Next2
    lda.l $434E7C
    and #1
    beq SourceSecond_FinalRefresh_Read2
SourceSecond_FinalRefresh_Next2:
.a16
.i16
    dex
    bne SourceSecond_FinalRefresh_Wait2
    bra SourceSecond_FinalRefresh_Done
SourceSecond_FinalRefresh_Read2:
.a16
.i16
    jsl SourcePacket_ForegroundPrepare
SourceSecond_FinalRefresh_Done:
.a16
.i16
    plx
    pla
    plp
    rtl
SourceIdleVisit_ModuleEnd:
