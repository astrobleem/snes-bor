; Scene-image generation only. No resource/OAM/DMA behavior changes.
SourceNextScene_Magic = $437C00
SourceNextScene_Low = $437C02
SourceNextScene_High = $437C04
SourceNextScene_Begin:
.a16
.i16
    lda #1
    sta.l SourcePacket_CopyBusy
    php
    rep #$30
    pha
    lda #0
    sta.l SourceNextScene_Magic
    lda.l SourceNextScene_Low
    inc a
    sta.l SourceNextScene_Low
    bne SourceNextScene_BeginDone
    lda.l SourceNextScene_High
    inc a
    sta.l SourceNextScene_High
SourceNextScene_BeginDone:
.a16
.i16
    pla
    plp
    rtl
SourceNextScene_Queued:
.a16
.i16
    lda #1
    sta.l SourcePacket_ActiveValid
    sta.l SourcePacket_ThisFrame
    php
    rep #$30
    pha
    lda #$5343
    sta.l SourceNextScene_Magic
    pla
    plp
    rtl
SourceNextScene_End:
