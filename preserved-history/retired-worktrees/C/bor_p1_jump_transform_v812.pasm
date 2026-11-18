; Foreground-only private image; original owner/copy busy flags are held.
; Existing scratch BAE..BB4 and expanded flags7820..7833 are transaction-owned.
.org $AE00
SourceP1Jump_CopyDispatch:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+34
    cmp #68
    beq SourceP1Jump_MoveNew
    cmp #72
    bne SourceP1Jump_CopyOther
    lda.l $437A9C
    cmp #1
    bne SourceP1Jump_MoveOriginal
    lda.l SOURCE_PACKET_ACTIVE_META+2
    cmp #36
    beq SourceP1Jump_MoveNew
    bra SourceP1Jump_MoveOriginal
SourceP1Jump_CopyOther:
.a16
.i16
    jml SourceFacing_CopyUnchanged
SourceP1Jump_MoveOriginal:
.a16
.i16
    ldx #502
    ldy #510
    jml SourceShape_MoveLow
SourceP1Jump_MoveNew:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+2
    clc
    adc #$77D7
    tax
    ldy #$77FF
    lda #471
    mvp $43,$43
    ldx #31
SourceP1Jump_ShiftFlags:
.a16
.i16
    lda.l SOURCE_PACKET_ACTIVE_META+2
    cmp #36
    bne SourceP1Jump_FourBits
    lda.l SourceAttackOwned_Image+511,x
    lsr a
    lsr a
    bra SourceP1Jump_RemainingBits
SourceP1Jump_FourBits:
.a16
.i16
    lda.l SourceAttackOwned_Image+511,x
SourceP1Jump_RemainingBits:
.a16
.i16
    lsr a
    lsr a
    lsr a
    lsr a
    sep #$20
.a8
    sta.l SourceAttackOwned_Image+512,x
    rep #$30
.a16
.i16
    dex
    cpx #2
    bcs SourceP1Jump_ShiftFlags
    lda.l $7E0A85+CHAR_FACING_LEFT
    and #255
    cmp.l $437872
    bne SourceP1Jump_FlipPeer
    jml SourceShape_CopyDone
SourceP1Jump_FlipPeer:
.a16
.i16
    sta.l $437872
    lda.l $437864
    clc
    adc.l $43787E
    asl a
    sta.l $437BB2
    jsl SourceAttackMask_SeedHigh
    ldx #40
    ldy #10
SourceP1Jump_FlipSprite:
.a16
.i16
    lda.w $7820,y
    and #1
    xba
    sta.l $437BB0
    lda.l SourceAttackOwned_Image,x
    and #255
    ora.l $437BB0
    sta.l $437BB0
    lda.w $7820,y
    and #2
    beq SourceP1Jump_Size8
    lda #16
    bra SourceP1Jump_HaveSize
SourceP1Jump_Size8:
.a16
.i16
    lda #8
SourceP1Jump_HaveSize:
.a16
.i16
    sta.l $437BAE
    lda.l $437BB2
    sec
    sbc.l $437BB0
    sec
    sbc.l $437BAE
    and #511
    sep #$20
.a8
    sta.l SourceAttackOwned_Image,x
    rep #$20
.a16
    xba
    and #1
    sta.l $437BB0
    lda.w $7820,y
    and #2
    ora.l $437BB0
    sep #$20
.a8
    sta.w $7820,y
    lda.l SourceAttackOwned_Image+3,x
    eor #$40
    sta.l SourceAttackOwned_Image+3,x
    rep #$30
.a16
.i16
    txa
    clc
    adc #4
    tax
    iny
    cpy #19
    bcc SourceP1Jump_FlipSprite
    ldx #0
    ldy #0
SourceP1Jump_Pack:
.a16
.i16
    lda.w $7820,x
    and #3
    sta.l $437BAE
    lda.w $7821,x
    and #3
    asl a
    asl a
    ora.l $437BAE
    sta.l $437BAE
    lda.w $7822,x
    and #3
    asl a
    asl a
    asl a
    asl a
    ora.l $437BAE
    sta.l $437BAE
    lda.w $7823,x
    and #3
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    ora.l $437BAE
    sep #$20
.a8
    sta.w $7800,y
    rep #$30
.a16
.i16
    inx
    inx
    inx
    inx
    iny
    cpy #5
    bcc SourceP1Jump_Pack
    jml SourceShape_CopyDone
; Failure-only entry: original No1 return remains default. This exception
; prepares the peer's existing pixels in the new facing; it does not discard
; a face check or borrow resources from a future frame.
SourceP1Jump_PeerFallback:
.a16
.i16
    lda.l $437A9C
    cmp #1
    bne SourceP1Jump_PeerReject
    lda.l SOURCE_PACKET_ACTIVE_META+12
    cmp #$0716
    bne SourceP1Jump_PeerReject
    jsl SourceNormalize_Partial1
    bcc SourceP1Jump_PeerReject
    lda.l $7E0A85+CHAR_FACING_LEFT
    and #255
    cmp #2
    bcs SourceP1Jump_PeerReject
    lda #0
    sec
    rtl
SourceP1Jump_PeerReject:
.a16
.i16
    lda #1
    sec
    rtl
SourceP1Jump_TransformEnd:
.assert SourceP1Jump_TransformEnd <= $27B000, "P1 transform exceeds audited gap"

; Tail entry preserves the enclosing SourceReady_Capture save frame.
; BA6 owns throttle state:0 first,1 attempted,3 retried,bit15 pending seal.
; Pending stores producer sequence low14bits. Aliasing at wrap delays retry
; conservatively until the next field. No new memory or producer writes.
SourceReady_BoundedBegin:
.a16
.i16
    lda.l StageTimer_FieldCounter
    cmp.l $437B9C
    bne SourceReady_BoundedNew
    lda.l $437BA6
    beq SourceReady_BoundedFirst
    bit #$8000
    bne SourceReady_BoundedPending
    jml SourceReady_Done
SourceReady_BoundedPending:
.a16
.i16
    lda.l $434E7C
    bit #1
    bne SourceReady_BoundedDone
    and #$3FFE
    ora #$8000
    cmp.l $437BA6
    beq SourceReady_BoundedDone
    lda #3
    bra SourceReady_BoundedMark
SourceReady_BoundedNew:
.a16
.i16
    sta.l $437B9C
SourceReady_BoundedFirst:
.a16
.i16
    lda #1
SourceReady_BoundedMark:
.a16
.i16
    sta.l $437BA6
    lda.l $437BA8
    inc a
    sta.l $437BA8
    jml SourceReady_ProjectionStart
SourceReady_BoundedDone:
.a16
.i16
    jml SourceReady_Done
SourceReady_BoundedGateEnd:
.assert SourceReady_BoundedGateEnd <= $27B000, "bounded ready gate exceeds helper gap"
.org $A600
SourceReady_BoundedSeal:
.a16
.i16
    lda.l $437B3C
    cmp #$A55E
    beq SourceReady_BoundedReturn
    lda.l $437BA6
    cmp #1
    bne SourceReady_BoundedReload
    lda.l $434E7C
    and #$3FFE
    ora #$8000
    sta.l $437BA6
SourceReady_BoundedReload:
.a16
.i16
    lda.l $437B3C
SourceReady_BoundedReturn:
.a16
.i16
    rtl
SourceReady_BoundedEnd:
.assert SourceReady_BoundedEnd <= $27A700, "bounded ready finalizer exceeds helper gap"
