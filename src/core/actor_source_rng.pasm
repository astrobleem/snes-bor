; Pinned GAMELIB3/RAND32.ASM integer recurrence, independent project/world state.
; Separate caller-owned D context (not an actor DP): 00 seed32,04 result32,
; 08 product48,0E shifted multiplier48,14 source seed32,18 remainder16.
; A16/I16 DBR0 decimal clear; JSL/RTL. Shared world stream, NOT per-actor RNG.
; Scheduling/call-order ownership remains with the source world scheduler.
S6_Random32:
    rep #$30
    .a16
    .i16
    lda $00
    sta $14
    lda $02
    sta $16
    stz $08
    stz $0A
    stz $0C
    lda #$4E6D
    sta $0E
    lda #$41C6
    sta $10
    stz $12
    ldx #32
S6_Random32__bit:
    .a16
    .i16
    lsr $16
    ror $14
    bcc S6_Random32__shift
    lda $08
    clc
    adc $0E
    sta $08
    lda $0A
    adc $10
    sta $0A
    lda $0C
    adc $12
    sta $0C
S6_Random32__shift:
    .a16
    .i16
    asl $0E
    rol $10
    rol $12
    dex
    bne S6_Random32__bit
    lda $08
    clc
    adc #12345
    sta $00
    lda $0A
    adc #0
    sta $02
    sta $04
    lda $0C
    adc #0
    sta $06
    rtl

; Unsigned full returned-word modulo1000, no replacement byte distribution.
S6_RandomModulo1000:
    rep #$30
    .a16
    .i16
    lda $04
    sta $14
    lda $06
    sta $16
    stz $18
    ldx #32
S6_RandomModulo1000__bit:
    .a16
    .i16
    asl $14
    rol $16
    rol $18
    lda $18
    cmp #1000
    bcc S6_RandomModulo1000__next
    sbc #1000
    sta $18
S6_RandomModulo1000__next:
    .a16
    .i16
    dex
    bne S6_RandomModulo1000__bit
    rtl
