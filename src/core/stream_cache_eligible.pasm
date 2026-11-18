; Cached eligibility for the ORIGINAL circular first-eligible allocation policy.
; Every physical BG slot has one bit. Init, stamp or reservation changes rebuild
; the table; subsequent allocations remove bits. External touches can only renew
; a stamp, so each candidate is rechecked before use. No new free rows can appear
; without Init, the sole Slot2Tile-freeing owner. Empty table keeps the original
; forced-eviction choice at ScanCursor. This changes search cost, never policy.
;
; $7E5B00..5EFF is source tile staging, $5F00..5F7F validated visual hints.
; The final 128 bytes of that established publisher gap hold this bitset.
StreamCache_EligibleBits = $7E5F80
StreamCache_EligibleStart = $7E4BE2
StreamCache_EligibleRemaining = $7E4BE4
StreamCache_EligibleStep = $7E4BE6
StreamCache_EligibleMask = $7E4BE8

Core_StreamCache_FindEligible:
    rep #$30
.a16
.i16
    lda.l StreamCache_Candidate
    sta.l StreamCache_EligibleStart
    jsr Core_StreamCache_ExhaustedValid
    bcc Core_StreamCache_FindEligible__rebuild
    brl Core_StreamCache_FindEligible__ready
Core_StreamCache_FindEligible__rebuild:
.a16
.i16
    ; A changed stamp does not justify rebuilding 1023 bits when a nearby
    ; legal empty/aged slot satisfies the ORIGINAL circular policy already.
    ; Try 16 legal candidates, skipping only exact reserved ranges. At high
    ; occupancy fall back to the existing generation-cached full bitmap.
    ldy #16
Core_StreamCache_FindEligible__probe:
.a16
.i16
    jsr Core_StreamCache_SkipReserved
    jsr Core_StreamCache_IsEligible
    bcc Core_StreamCache_FindEligible__probe_next
    sec
    rts
Core_StreamCache_FindEligible__probe_next:
.a16
.i16
    lda.l StreamCache_Candidate
    inc a
    cmp #1024
    bcc Core_StreamCache_FindEligible__probe_store
    lda #1
Core_StreamCache_FindEligible__probe_store:
.a16
.i16
    sta.l StreamCache_Candidate
    dey
    bne Core_StreamCache_FindEligible__probe
    ; Build eight eligibility bits at a time, in reverse slot order. The
    ; full original predicate is free OR age>=16, then reservation masking.
    ; Avoid 1023 long calls, repeated reservation decoding and bit shifts.
    lda #1023
    sta.l StreamCache_Candidate
    lda #0
    sta.l StreamCache_EligibleMask
Core_StreamCache_FindEligible__build:
.a16
.i16
    lda.l StreamCache_EligibleMask
    asl a
    sta.l StreamCache_EligibleMask
    lda.l StreamCache_Candidate
    beq Core_StreamCache_FindEligible__build_next
    asl a
    tax
    lda.l StreamCache_Slot2Tile,x
    cmp #$FFFF
    beq Core_StreamCache_FindEligible__build_yes
    lda.l StreamCache_Candidate
    tax
    sep #$20
.a8
    lda.l StreamCache_CurrentStamp
    sec
    sbc.l StreamCache_SlotStamp,x
    cmp #STREAM_CACHE_PROTECT_WINDOW
    rep #$30
.a16
.i16
    bcc Core_StreamCache_FindEligible__build_next
Core_StreamCache_FindEligible__build_yes:
.a16
.i16
    lda.l StreamCache_EligibleMask
    ora #1
    sta.l StreamCache_EligibleMask
Core_StreamCache_FindEligible__build_next:
.a16
.i16
    lda.l StreamCache_Candidate
    and #7
    bne Core_StreamCache_FindEligible__build_decrement
    lda.l StreamCache_Candidate
    lsr a
    lsr a
    lsr a
    tax
    lda.l StreamCache_EligibleMask
    sep #$20
.a8
    sta.l StreamCache_EligibleBits,x
    rep #$30
.a16
.i16
    lda #0
    sta.l StreamCache_EligibleMask
    lda.l StreamCache_Candidate
    beq Core_StreamCache_FindEligible__mask_reserved
Core_StreamCache_FindEligible__build_decrement:
.a16
.i16
    lda.l StreamCache_Candidate
    dec a
    sta.l StreamCache_Candidate
    brl Core_StreamCache_FindEligible__build
Core_StreamCache_FindEligible__mask_reserved:
.a16
.i16
    jsr Core_StreamCache_MaskReserved
    jsr Core_StreamCache_RecordExhausted
Core_StreamCache_FindEligible__ready:
.a16
.i16
    lda.l StreamCache_EligibleStart
    sta.l StreamCache_Candidate
    lda #1023
    sta.l StreamCache_EligibleRemaining
Core_StreamCache_FindEligible__search:
.a16
.i16
    lda.l StreamCache_EligibleRemaining
    bne Core_StreamCache_FindEligible__test_byte
    lda.l StreamCache_EligibleStart
    sta.l StreamCache_Candidate
    clc
    rts
Core_StreamCache_FindEligible__test_byte:
.a16
.i16
    lda.l StreamCache_Candidate
    lsr a
    lsr a
    lsr a
    tax
    lda.l StreamCache_EligibleBits,x
    and #$00FF
    bne Core_StreamCache_FindEligible__test_bit
    ; Skip a whole empty byte, bounded by the remaining circular interval.
    lda.l StreamCache_Candidate
    and #7
    eor #7
    inc a
    cmp.l StreamCache_EligibleRemaining
    bcc Core_StreamCache_FindEligible__advance
    lda.l StreamCache_EligibleRemaining
    bra Core_StreamCache_FindEligible__advance
Core_StreamCache_FindEligible__test_bit:
.a16
.i16
    jsr Core_StreamCache_EligibleBit
    and.l StreamCache_EligibleBits,x
    and #$00FF
    beq Core_StreamCache_FindEligible__one
    jsr Core_StreamCache_IsEligible
    bcc Core_StreamCache_FindEligible__stale
    jsr Core_StreamCache_ClearEligibleBit
    sec
    rts
Core_StreamCache_FindEligible__stale:
.a16
.i16
    jsr Core_StreamCache_ClearEligibleBit
Core_StreamCache_FindEligible__one:
.a16
.i16
    lda #1
Core_StreamCache_FindEligible__advance:
.a16
.i16
    sta.l StreamCache_EligibleStep
    lda.l StreamCache_EligibleRemaining
    sec
    sbc.l StreamCache_EligibleStep
    sta.l StreamCache_EligibleRemaining
    lda.l StreamCache_Candidate
    clc
    adc.l StreamCache_EligibleStep
    cmp #1024
    bcc Core_StreamCache_FindEligible__store
    sec
    sbc #1023
Core_StreamCache_FindEligible__store:
.a16
.i16
    sta.l StreamCache_Candidate
    brl Core_StreamCache_FindEligible__search

; Return A16=bit mask, X16=byte offset. Preserve Candidate.
Core_StreamCache_EligibleBit:
.a16
.i16
    lda.l StreamCache_Candidate
    and #7
    tay
    lda #1
Core_StreamCache_EligibleBit__shift:
.a16
.i16
    cpy #0
    beq Core_StreamCache_EligibleBit__index
    asl a
    dey
    bra Core_StreamCache_EligibleBit__shift
Core_StreamCache_EligibleBit__index:
.a16
.i16
    sta.l StreamCache_EligibleMask
    lda.l StreamCache_Candidate
    lsr a
    lsr a
    lsr a
    tax
    lda.l StreamCache_EligibleMask
    rts

Core_StreamCache_ClearEligibleBit:
.a16
.i16
    jsr Core_StreamCache_EligibleBit
    eor #$FFFF
    sep #$20
.a8
    and.l StreamCache_EligibleBits,x
    sta.l StreamCache_EligibleBits,x
    rep #$30
.a16
.i16
    rts

Core_StreamCache_IsEligible:
.a16
.i16
    jsl Core_StreamCache_IsReserved
    bcs Core_StreamCache_IsEligible__no
    lda.l StreamCache_Candidate
    asl a
    tax
    lda.l StreamCache_Slot2Tile,x
    cmp #$FFFF
    beq Core_StreamCache_IsEligible__yes
    lda.l StreamCache_Candidate
    tax
    sep #$20
.a8
    lda.l StreamCache_CurrentStamp
    sec
    sbc.l StreamCache_SlotStamp,x
    cmp #STREAM_CACHE_PROTECT_WINDOW
    bcc Core_StreamCache_IsEligible__no8
    rep #$30
.a16
.i16
Core_StreamCache_IsEligible__yes:
.a16
.i16
    sec
    rts
Core_StreamCache_IsEligible__no8:
.a8
.i16
    rep #$30
.a16
.i16
Core_StreamCache_IsEligible__no:
.a16
.i16
    clc
    rts

; Reservation ranges are constant during a witnessed layout generation.
Core_StreamCache_MaskReserved:
.a16
.i16
    sep #$20
.a8
    lda.l StreamCache_EligibleBits+64
    and #$C0
    sta.l StreamCache_EligibleBits+64 ; HUD slots 512..517
    lda #0
    ldx #82
Core_StreamCache_MaskReserved__font:
.a8
.i16
    sta.l StreamCache_EligibleBits,x
    inx
    cpx #88
    bcc Core_StreamCache_MaskReserved__font ; slots 656..703
    lda.l StreamCache_NormalLayout
    bne Core_StreamCache_MaskReserved__normal
    lda.l StreamCache_LegacyFpActive
    beq Core_StreamCache_MaskReserved__done
    lda #0
    ldx #66
Core_StreamCache_MaskReserved__legacy:
.a8
.i16
    sta.l StreamCache_EligibleBits,x
    inx
    cpx #82
    bcc Core_StreamCache_MaskReserved__legacy ; slots 528..655
    bra Core_StreamCache_MaskReserved__done
Core_StreamCache_MaskReserved__normal:
.a8
.i16
    lda.l StreamCache_BG2Capacity
    beq Core_StreamCache_MaskReserved__done
    rep #$30
.a16
.i16
    and #$00FF
    sta.l StreamCache_EligibleRemaining
    lda #1023
    sta.l StreamCache_Candidate
    jsr Core_StreamCache_ClearEligibleBit
    lda #768
    sta.l StreamCache_Candidate
Core_StreamCache_MaskReserved__bg2:
.a16
.i16
    jsr Core_StreamCache_ClearEligibleBit
    lda.l StreamCache_Candidate
    inc a
    sta.l StreamCache_Candidate
    lda.l StreamCache_EligibleRemaining
    dec a
    sta.l StreamCache_EligibleRemaining
    bne Core_StreamCache_MaskReserved__bg2
Core_StreamCache_MaskReserved__done:
    rep #$30
.a16
.i16
    rts

; Move forward to the first legal physical slot, preserving Y's probe bound.
; The excluded ranges are exactly Core_StreamCache_IsReserved's ranges.
Core_StreamCache_SkipReserved:
.a16
.i16
    lda.l StreamCache_Candidate
    cmp #512
    bcc Core_StreamCache_SkipReserved__store
    cmp #518
    bcs Core_StreamCache_SkipReserved__font
    lda #518
Core_StreamCache_SkipReserved__font:
.a16
.i16
    cmp #656
    bcc Core_StreamCache_SkipReserved__legacy
    cmp #704
    bcs Core_StreamCache_SkipReserved__legacy
    lda #704
Core_StreamCache_SkipReserved__legacy:
.a16
.i16
    sta.l StreamCache_Candidate
    lda.l StreamCache_NormalLayout
    and #$00FF
    bne Core_StreamCache_SkipReserved__normal
    lda.l StreamCache_LegacyFpActive
    and #$00FF
    beq Core_StreamCache_SkipReserved__return
    lda.l StreamCache_Candidate
    cmp #528
    bcc Core_StreamCache_SkipReserved__return
    cmp #656
    bcs Core_StreamCache_SkipReserved__return
    lda #704 ; legacy foreground ends where the font reservation begins
    bra Core_StreamCache_SkipReserved__store
Core_StreamCache_SkipReserved__normal:
.a16
.i16
    lda.l StreamCache_BG2Capacity
    and #$00FF
    beq Core_StreamCache_SkipReserved__return
    clc
    adc #768
    sta.l StreamCache_OldTile
    lda.l StreamCache_Candidate
    cmp #1023
    beq Core_StreamCache_SkipReserved__wrap
    cmp #768
    bcc Core_StreamCache_SkipReserved__return
    cmp.l StreamCache_OldTile
    bcs Core_StreamCache_SkipReserved__return
    lda.l StreamCache_OldTile
    cmp #1023
    bcc Core_StreamCache_SkipReserved__store
Core_StreamCache_SkipReserved__wrap:
.a16
.i16
    lda #1
Core_StreamCache_SkipReserved__store:
.a16
.i16
    sta.l StreamCache_Candidate
Core_StreamCache_SkipReserved__return:
.a16
.i16
    rts

; Advance a valid bitmap by exactly one modular stamp, never by a guessed
; source-time jump. Check only newly aged rows; retain candidate validation.
Core_StreamCache_AgeEligible:
.a16
.i16
    phx
    phy
    lda.l StreamCache_Candidate
    pha
    ldx #1
    sep #$20
.a8
Core_StreamCache_AgeEligible__scan:
.a8
.i16
    lda.l StreamCache_CurrentStamp
    sec
    sbc.l StreamCache_SlotStamp,x
    cmp #STREAM_CACHE_PROTECT_WINDOW
    bne Core_StreamCache_AgeEligible__next
    rep #$30
.a16
.i16
    phx
    txa
    sta.l StreamCache_Candidate
    jsr Core_StreamCache_IsEligible
    bcc Core_StreamCache_AgeEligible__restore
    jsr Core_StreamCache_EligibleBit
    sep #$20
.a8
    ora.l StreamCache_EligibleBits,x
    sta.l StreamCache_EligibleBits,x
    rep #$30
.a16
.i16
Core_StreamCache_AgeEligible__restore:
.a16
.i16
    plx
    sep #$20
.a8
Core_StreamCache_AgeEligible__next:
.a8
.i16
    inx
    cpx #1024
    bcc Core_StreamCache_AgeEligible__scan
    rep #$30
.a16
.i16
    pla
    sta.l StreamCache_Candidate
    ply
    plx
    rts
