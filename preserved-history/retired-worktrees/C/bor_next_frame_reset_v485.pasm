
; Existing SVActor startup reset clears the held arrays after this seam.
; Do not inspect power-on private stamps; establish them unconditionally.
SourceNextFrame_Reset:
.a16
.i16
    jsl SourceReserve_Reset
    php
    rep #$30
    pha
    lda.l Game_CampaignId
    and #255
    cmp #3
    bne SourceNextFrame_ResetDone
    lda #0
    sta.l SourceNextWitness_Base
    sta.l SourceNextWitness_Base+512
    sta.l SourceNextFrame_Base
    sta.l SourceNextFrame_Base+1024
SourceNextFrame_ResetDone:
.a16
.i16
    pla
    plp
    rtl
SourceNextFrame_ResetEnd:
