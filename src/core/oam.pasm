; ============================================================================
; core/oam.pasm — sprite (OAM) shadow buffer, uploaded to hardware via DMA
; during NMI.
;
; Ported (adapted, not literal) from SNES-SuperBossGaiden (src/core/oam.65816
; + oam.h), used with the original author's permission — see
; [[license-authorization-superbossgaiden]] / module headers elsewhere in
; this project for what "adapted" means here.
;
; Game code writes sprite entries into Oam_Buffer (4 bytes/sprite: X-low, Y,
; tile index, attribute) and Oam_ExpandedHi (1 byte/sprite: size bit + X-high
; bit, pre-shifted into position, NOT yet packed) via Oam_CurrentSlot as a
; cursor, then calls Core_Oam_Play once per frame. Core_Oam_Play packs the
; expanded hi-table into the real hardware format (4 sprites/byte) and
; enqueues a single DMA transfer (via core/dma.pasm's Core_Dma_Enqueue) that
; core/nmi.pasm's Core_Nmi_Play drains during the next vblank. Unlike
; upstream, the real hardware transfer goes through this project's existing
; DMA queue instead of a hand-rolled immediate DMA — dma.pasm already has
; DMA_TYPE_OAM wired to hardware channel 7, so there's no reason to bypass it.
; PPU register writes (OBSEL) go through core/nmi.pasm's shadow registers,
; not straight to hardware, matching this project's shadow-register PPU-sync
; architecture.
;
; Same Poppy-assembler workarounds as every other core/*.pasm file this
; project has ported (see core/dma_channel.pasm's header for the .w/.l one,
; and poppy_assembler_bugs.md project memory for the full confirmed list):
;   - Indexed WRAM access always `.l`, never `.w`.
;   - No `stz.l` (no long-addressing STZ exists on real 65816; this Poppy
;     build silently mis-encodes it) — `lda #0` / `sta.l` instead.
;   - Every label that's a branch target gets a `nop` immediately before it
;     as a precaution against this Poppy build's branch-target address
;     misresolution bug, then gets verified via raw-byte alignment check
;     after building (see build.md's Testing section).
; ============================================================================

OAM_SLOTS = 128          ; hardware sprite limit

; --- Shadow OAM tables, DMA'd to real OAM as one contiguous transfer ---
Oam_Buffer     = $7E5100 ; 128 sprites x 4B (X-low, Y, tile, attr) = 512B
Oam_PackedHi   = $7E5300 ; real hardware 2nd-OAM-table format, 32B (4 sprites/byte)
; --- Working buffer, packed into Oam_PackedHi each upload ---
Oam_ExpandedHi = $7E5320 ; 128 sprites x 1B (size/x-high bits, pre-shifted), 128B

Oam_CurrentSlot = $7E53A0 ; .dw — byte offset into Oam_Buffer, next free sprite slot
Oam_UploadFlag  = $7E53A2 ; .dw — nonzero: Core_Oam_Play has a transfer to enqueue
Oam_VramStart   = $7E53A4 ; .dw — VRAM word address sprite tiles are based at

OamShadow_Start = Oam_Buffer
OamShadow_End   = $7E53A6

OAM_DEFAULT_Y = $F0      ; off the visible 224-line frame -> sprite hidden

Core_Oam_Init:
    rep #$31
.a16
    lda #0
    ldx #0
    nop
Core_Oam_Init__clear_loop:
    sta.l OamShadow_Start,x
    inx
    inx
    cpx #OamShadow_End - OamShadow_Start
    bcc Core_Oam_Init__clear_loop

    jsr Core_Oam_ClearAll

    ; default sprite tile base: VRAM word $C000 (top of VRAM, well clear of
    ; the BG tiles/tilemaps main.pasm's boot code already placed below it)
    lda #$C000
    sta Oam_VramStart

    sep #$20
.a8
    lda.l Nmi_ObjSel
    ora #$80                ; name table at word $C000 (bit7, matches base above:
                             ; OBSEL name-select field * $1000 = $8000, plus the
                             ; fixed $8000 base = $C000 when bit7 set and field=0)
    sta.l Nmi_ObjSel
    rep #$31
.a16
    rts

; Reset the shadow buffer to "every sprite hidden" and rewind the write
; cursor. Called at init, and by Core_Nmi_Play after each successful upload
; so next frame's unused slots don't show stale sprites from a frame that
; had more objects on screen.
Core_Oam_ClearAll:
    rep #$31
.a16
    lda #0
    sta Oam_CurrentSlot

    ldx #0
    nop
Core_Oam_ClearAll__loop:
    lda #0
    sta.l Oam_Buffer,x
    lda #OAM_DEFAULT_Y
    sta.l Oam_Buffer+1,x
    lda #0
    sta.l Oam_Buffer+3,x
    inx
    inx
    inx
    inx
    cpx #OAM_SLOTS * 4
    bcc Core_Oam_ClearAll__loop

    ldx #0
    nop
Core_Oam_ClearAll__hi_loop:
    lda #0
    sta.l Oam_ExpandedHi,x
    sta.l Oam_PackedHi,x
    inx
    cpx #OAM_SLOTS
    bcc Core_Oam_ClearAll__hi_loop
    rts

; Call once per frame after all sprites for this frame have been written
; into Oam_Buffer/Oam_ExpandedHi. Packs the hi-table and queues the upload;
; Core_Nmi_Play does the actual DMA and the post-upload buffer reset.
;
; Skips the enqueue entirely when Oam_CurrentSlot is still 0, i.e. game code
; wrote no sprites this frame. Unconditionally enqueuing a fresh 544-byte
; OAM DMA request every single frame regardless of whether OAM content
; changed is exactly the bug core/nmi.pasm's header already warns about:
; it keeps the DMA queue permanently busy with redundant uploads, and the
; real hardware-DMA time that costs pushes Core_Nmi_Play's forced-blank
; commit bracket past the end of vblank into active display (a black band
; across the top of the screen -- confirmed via a debug probe reading
; HVBJOY's vblank flag right after the commit bracket's un-blank write:
; still inside vblank at commit entry, already past it by the time
; brightness gets restored, every single frame, steady-state). Nothing in
; this project yet calls a Core_Oam_SetSprite-style entry point to advance
; Oam_CurrentSlot, so OAM is 100% static -- there is no reason to spend
; vblank DMA bandwidth re-uploading it every frame.
Core_Oam_Play:
    rep #$31
.a16
    lda Oam_CurrentSlot
    bne Core_Oam_Play__has_sprites
    bra Core_Oam_Play__done
    nop
Core_Oam_Play__has_sprites:
    jsr Core_Oam_TransformHiOam

    lda #$5100                        ; low+mid byte of Oam_Buffer's address
    sta DmaRequest_SourceAddrLow
    lda #0
    sta DmaRequest_TargetAddr         ; OAM address 0
    lda #(OAM_SLOTS*4) + (OAM_SLOTS/4)  ; 512 + 32 = 544 bytes, one contiguous transfer
    sta DmaRequest_Length

    sep #$20
.a8
    lda #$7E
    sta DmaRequest_SourceBank
    lda #DMA_TYPE_OAM
    sta DmaRequest_TypeFlags
    rep #$31
.a16
    jsr Core_Dma_Enqueue
    bcs Core_Oam_Play__queued
    bra Core_Oam_Play__done
    nop
Core_Oam_Play__queued:
    lda #1
    sta Oam_UploadFlag
    nop
Core_Oam_Play__done:
    rts

; Packs Oam_ExpandedHi (1 byte/sprite, size+x-high bits pre-shifted into their
; final position) into Oam_PackedHi (real hardware format, 4 sprites/byte).
; Bit-for-bit the same LDA/ROR/ORA sequence as upstream's TRANSFORM_HIOAM
; macro (9 total RORs per group of 4) — this is a specific bit-interleave,
; not something to "simplify" without re-deriving the packing math.
Core_Oam_TransformHiOam:
    php
    rep #$31
.a16
.i16
    ldx #0
    ldy #0
    nop
Core_Oam_TransformHiOam__loop:
    sep #$20
.a8
    clc
    lda.l Oam_ExpandedHi,x
    ror a
    ror a
    ora.l Oam_ExpandedHi+1,x
    ror a
    ror a
    ora.l Oam_ExpandedHi+2,x
    ror a
    ror a
    ora.l Oam_ExpandedHi+3,x
    ror a
    ror a
    ror a
    sta.l Oam_PackedHi,y
    rep #$31
.a16
    inx
    inx
    inx
    inx
    iny
    cpx #OAM_SLOTS
    bcc Core_Oam_TransformHiOam__loop
    plp
    rts
