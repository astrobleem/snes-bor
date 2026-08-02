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

    ; === EXACT copy of working VRAM test init ===
    lda #$8f
    sta $2100           ; forced blank
    
    lda #$80
    sta $2115           ; VMAIN = word increment on high byte write
    
    stz $2116           ; VRAM addr = 0
    stz $2117
    
    ; === Upload tile 0 (all $FFFF = color 15) to VRAM $0000 ===
    ldx #$10            ; 16 words = 32 bytes
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

    ; === NOW do PPU init ===
    lda #$01
    sta $2105           ; mode 1
    lda #$04
    sta $2107           ; BG1SC = $04 -> $0400
    lda #$00
    sta $210b           ; BG12NBA = 0 -> tiles at $0000
    lda #$01
    sta $212c           ; TM = BG1

    ; Palette: color 15 = green
    lda #$0f
    sta $2121
    lda #$e0
    sta $2122
    lda #$03
    sta $2122
    
    ; VRAM increment
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