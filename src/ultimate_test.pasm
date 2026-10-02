.snes
.bank 0
.org $8000

reset:
    sei
    clc
    xce
    rep #$30
.a16
.i16
    lda #$1fff
    tcs
    sep #$20
.a8

    ; === Disable NMI ===
    stz $4200

    ; === Forced blank ===
    lda #$8f
    sta $2100
    
    ; === VRAM word increment ===
    lda #$80
    sta $2115
    
    ; === Upload tile 0 (all color 15 = green) to VRAM $0000 ===
    stz $2116
    stz $2117
    ldx #$10
tile_loop:
    lda #$ff
    sta $2118
    lda #$ff
    sta $2119
    dex
    bne tile_loop

    ; === Fill tilemap at $0400 (word $0200) with tile 0 ===
    lda #$00
    sta $2116
    lda #$02
    sta $2117
    ldx #$0400
tmap_loop:
    stz $2118
    stz $2119
    dex
    bne tmap_loop

    ; NOW do the rest of PPU init (mode, tilemaps, palette)
    lda #$01
    sta $2105           ; mode 1
    lda #$04
    sta $2107           ; BG1SC = $04 -> $0400
    lda #$00
    sta $210b           ; BG12NBA = 0 -> BG1 at $0000
    lda #$01
    sta $212c           ; TM = BG1

    ; Palette
    lda #$00
    sta $2121
    lda #$ff
    sta $2122
    lda #$7f
    sta $2122          ; color 0 = white
    lda #$0f
    sta $2121
    lda #$e0
    sta $2122
    lda #$03
    sta $2122          ; color 15 = green

    ; VRAM increment mode
    lda #$80
    sta $2115

    ; Release forced blank
    lda #$0f
    sta $2100

main_loop:
    bra main_loop

.org $FFE0
.word $0000
.word $0000
.word $0000
.word $0000
.word $0000
.word $0000
.word $0000
.word $0000

.org $FFF0
.word $0000
.word $0000
.word $0000
.word $0000
.word $0000
.word $0000
.word reset
.word $0000