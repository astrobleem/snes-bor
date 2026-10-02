; ============================================================================
; SA-1 Blitter — pixel-granularity frame blitter into BW-RAM canvas
; Handles unaligned blits across 8x8 tile boundaries
; ============================================================================

.snes

; Canvas constants (from sa1_ccdma.pasm)
CANVAS_PITCH = 64    ; bytes per row (128 pixels / 2)

; BW-RAM addresses (from sa1_boot.pasm)

; === Blit 4bpp sprite to canvas ===
; A = source address (24-bit in A:X — A=bank, X=offset)
; $00 = destination X (pixel)
; $02 = destination Y (pixel)
; $04 = width in pixels
; $06 = height in pixels
; $08 = source pitch (bytes per row)
; Blits 4bpp packed pixels, handles unaligned destination
blit_4bpp:
    php
    rep #$30
.a16
    ; TODO: implement unaligned 4bpp blit
    ; For PoC, this is a stub — we only need aligned CC-DMA transfer
    plp
    rts

; === Clear canvas to transparent (color 0) ===
clear_canvas:
    php
    rep #$30
.a16
    ; STZ has no long-addressing mode on real 65816; this Poppy build
    ; doesn't reject `stz.l Symbol,x`, it silently mis-encodes it. Use
    ; lda #0 / sta.l instead (see src/core/oop.pasm header for the same
    ; pattern documented in detail).
    lda #0
    ldx #$0000
.loop:
    sta.l BW_CANVAS,x
    inx
    inx
    cpx #$1800
    bcc .loop
    plp
    rts

; === Fill canvas with test pattern ===
; Creates a gradient pattern for CC-DMA verification
; Each 8x8 tile gets a unique color index 0-15
fill_test_pattern:
    php
    rep #$30
.a16
    ldx #$0000
.loop:
    ; Calculate tile index from byte offset
    ; Each 8x8 tile = 32 bytes (8 rows * 4 bytes at 4bpp)
    txa
    lsr
    lsr
    lsr
    lsr
    lsr                 ; tile index (0-191)
    tay
    ; Spread color across nibbles for visibility
    tya
    and #$000f
    asl
    asl
    asl
    asl                 ; color in high nibble
    ora #$0001          ; low nibble = 1
    sta.l BW_CANVAS,x
    inx
    inx
    cpx #$1800
    bcc .loop
    plp
    rts