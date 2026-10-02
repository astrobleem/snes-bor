; ============================================================================
; SA-1 Boot — SA-1 initialization, BW-RAM mapping, ready flag
; Runs on SA-1 after S-CPU releases reset
; ============================================================================

.snes

; SA-1 registers (SA-1 side)
; (already defined in main.pasm)

; BW-RAM addresses (SA-1 side)
BW_CANVAS  = $400000 ; Canvas buffer start (physical BW-RAM bank 0)
BW_READY   = $410000 ; Ready flag for S-CPU

; === SA-1 Entry ===
.bank 1
.org $8000

sa1_reset:
    ; SA-1 boots in native mode already
    sep #$20
.a8
    rep #$10
.i16

    ; Enable SA-1 IRAM writes (self)
    lda #$ff
    sta $222a           ; CIWP

    ; Clear BW-RAM canvas (128x96 = 12,288 bytes at 4bpp)
    ; Fill with test pattern for CC-DMA verification
    rep #$20
.a16
    ldx #$0000
sa1_clear_loop:
    ; Calculate tile index from byte offset (32 bytes per 8x8 tile)
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
    cpx #$1800          ; 12,288 bytes = $3000; $3000/2 = $1800 words
    bcc sa1_clear_loop

    ; Set ready flag for S-CPU
    lda #$5a1a
    sta.l BW_READY

    ; Signal first canvas ready
    lda #$0001
    sta.l $410002

    ; ============================================================================
    ; SA-1 Frame Loop — polls canvas dirty flag, triggers CC-DMA
    ; ============================================================================

sa1_frame_loop:
    ; Check if canvas needs refresh (S-CPU sets $410002 = 1)
    lda.l $410002
    beq sa1_frame_wait
    
    ; Clear the flag
    stz.l $410002
    
    ; Trigger CC-DMA: upload canvas to VRAM $2000
    ; Source: BW-RAM $400000 (physical bank 0)
    sep #$20
.a8
    lda #$00
    sta $2232           ; source low
    sta $2233           ; source high
    sta $2234           ; source bank (BW-RAM physical bank 0)
    
    rep #$20
.a16
    lda #$2000          ; VRAM destination
    sta $2235           ; dest low
    sta $2236           ; dest high
    
    lda #$1800          ; size: 192 tiles * 32 bytes = 6144 = $1800
    sta $2238           ; size low
    sta $2239           ; size high
    
    sep #$20
.a8
    lda #$80
    sta $2231           ; enable CC-DMA mode
    lda #$01
    sta $223a           ; trigger CC-DMA transfer
    ; SA-1 stalls here until CC-DMA completes
    
    stz $2231           ; clear CC-DMA mode
    
sa1_frame_wait:
    wai
    bra sa1_frame_loop

; ============================================================================
; Remaining SA-1-side modules (constants/definitions only, plus not-yet-
; called blitter routines — see src/sa1/sa1_blitter.pasm header).
; ============================================================================
.include "sa1_ccdma.pasm"
.include "sa1_blitter.pasm"