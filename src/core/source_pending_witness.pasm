; Conservative no-pending witness in P1 completed-control spare bytes.
; LegacyCgramDrops endsCB; saved immutable entry beginsE0. No actor/world data.
SourcePending_KnownClear = $7EEFCC
SourcePending_SawPending = $7EEFCE
SourcePending_Invalidate:
    php
    rep #$30
.a16
.i16
    pha
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    bne SourcePending_Invalidate__done
    lda #0
    sta.l SourcePending_KnownClear
SourcePending_Invalidate__done:
.a16
.i16
    pla
    plp
    rtl

; Called only after the original ascending full scan reached all64 rows.
SourcePending_CertifyEmpty:
    php
    rep #$30
.a16
.i16
    pha
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    bne SourcePending_CertifyEmpty__done
    lda.l SourceVisual_CompletedMagic
    cmp #$C04D
    bne SourcePending_CertifyEmpty__done
    lda.l SourcePending_SawPending
    bne SourcePending_CertifyEmpty__done
    lda #1
    sta.l SourcePending_KnownClear
SourcePending_CertifyEmpty__done:
.a16
.i16
    pla
    plp
    rtl
SourcePending_CodeEnd:
