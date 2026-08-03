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

; --- Core_Oam_TransformHiOam's own working scratch, NOT part of the shadow
; buffer above (always fully overwritten before being read within one call,
; so they don't need to be in the init/upload clear cycle). Placed in the
; gap between OamShadow_End and main.pasm's Anim_* WRAM block ($7E53B0+) --
; confirmed via a project-wide grep for 7E53A/7E53B that nothing else claims
; this range.
OamHiSrcIndex   = $7E53A6 ; .dw — index into Oam_ExpandedHi for the current group (stride 4)
OamHiDstIndex   = $7E53A8 ; .dw — index into Oam_PackedHi for the current group (stride 1)
OamHiPackedTemp = $7E53AA ; .db — this group's packed byte, built up before the store

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

    ; default sprite tile base: VRAM word $4000
    lda #$4000
    sta Oam_VramStart

    sep #$20
.a8
    lda #$02                ; base word $4000 (field 2 << 13), size mode 0
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

; Packs Oam_ExpandedHi (1 byte/sprite; bit0 = X-high, bit1 = size, matching
; real hardware's field layout so no bit-order remap is needed, just
; positioning) into Oam_PackedHi (real hardware 2nd-OAM-table format: 4
; sprites/byte, sprite N's 2 bits at bits [(N&3)*2+1 : (N&3)*2] of byte
; N>>2 -- ground truth is Mesen2's SnesPpu.cpp FetchSpritePosition:
; `highTableValue = oamRam[0x200|(N>>2)] >> ((N<<1)&0x06)`, bit0 feeds the
; X-sign table, bit1 ORs into OamMode's bit2).
;
; TWO real, independent bugs were found in this routine in a previous
; session (it had never executed before that session's TestSprite_Init gave
; it real data) and left deliberately unfixed pending root-causing a
; miscompile risk. Both are fixed here now:
;
; 1. `sta.l Oam_PackedHi,y` was not a real 65816 addressing mode (no
;    long-indexed-by-Y store exists in hardware, only long-indexed-by-X,
;    opcode $9F) -- Poppy silently emitted a bank-dropping 2-byte
;    absolute-Y store instead of erroring. FIX: never index a `.l` bank-$7E
;    symbol with Y anywhere in this routine. Two WRAM scratch counters
;    (OamHiSrcIndex, OamHiDstIndex, both stride-appropriate 16-bit values)
;    replace the X/Y register pair; each is loaded into X via `lda.l`+`tax`
;    (both real, unindexed or X-indexed instructions, never Y) immediately
;    before the one indexed access that needs it, then X is free to hold a
;    different value for the next indexed access in the same iteration.
;    This is the same "swap what X means, never touch Y for `.l`" pattern
;    as `Core_Oam_Play`'s own DMA-request setup elsewhere in this project.
;
; 2. The original LDA/ROR/ORA bit-interleave (ported from upstream's
;    TRANSFORM_HIOAM macro) didn't place each sprite's 2 bits at hardware's
;    expected position -- a from-scratch Python simulation found sprite 0's
;    bits landing at bits 7-6 instead of 1-0, with at least one input bit
;    lost. FIX: replaced with explicit AND #$03 (mask to the 2 meaningful
;    bits) / ASL A * (2*group-position) (shift into place) / ORA (merge)
;    per sprite, building the packed byte in OamHiPackedTemp one sprite at a
;    time. No ROR, no carry-chain reasoning required to verify by hand --
;    each sprite's contribution can be checked independently.
;
; A previous attempt at bug 1 alone (temporary DBR=$7E via phb/pha/plb,
; dropping `.l` for short addressing) was bisected to break Ralf's BG2
; idle/walk animation ticking completely, even with this routine never
; actually called at runtime -- strong evidence of a Poppy address-
; estimation-pass side effect from adding certain instructions to this
; routine's body (not a runtime bug, since it happened whether or not the
; routine executed), never root-caused to a mechanism, and NOT added as a
; numbered entry to poppy_assembler_bugs.md for that reason. This rewrite
; avoids phb/pha/plb entirely -- the DBR manipulation, not merely "changing
; this routine's size," is the leading suspect, so the fix below sticks to
; addressing patterns (`lda.l`/`sta.l`/`ora.l` unindexed, `lda.l ...,x` and
; `sta.l ...,x` long-indexed-X, `tax`) already proven safe elsewhere in this
; exact file. Still: raw-byte-verify every guarded label in this file after
; this change, same as any edit that shifts code size in the $C100-$FC00
; window -- see poppy_assembler_bugs.md bug #4.
    nop
    nop
    nop
    nop
Core_Oam_TransformHiOam:
    php
    rep #$31
.a16
    lda #0
    sta.l OamHiSrcIndex
    sta.l OamHiDstIndex
    nop
Core_Oam_TransformHiOam__loop:
    lda.l OamHiSrcIndex
    tax
    sep #$20
.a8
    lda.l Oam_ExpandedHi,x
    and #$03
    sta.l OamHiPackedTemp              ; packed = sprite0's 2 bits (bits 1-0)

    lda.l Oam_ExpandedHi+1,x
    and #$03
    asl a
    asl a                               ; sprite1's bits -> bits 3-2
    ora.l OamHiPackedTemp
    sta.l OamHiPackedTemp

    lda.l Oam_ExpandedHi+2,x
    and #$03
    asl a
    asl a
    asl a
    asl a                               ; sprite2's bits -> bits 5-4
    ora.l OamHiPackedTemp
    sta.l OamHiPackedTemp

    lda.l Oam_ExpandedHi+3,x
    and #$03
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a                               ; sprite3's bits -> bits 7-6
    ora.l OamHiPackedTemp
    sta.l OamHiPackedTemp

    rep #$31
.a16
    lda.l OamHiDstIndex
    tax
    sep #$20
.a8
    lda.l OamHiPackedTemp
    sta.l Oam_PackedHi,x                ; long-indexed-X: a real opcode

    rep #$31
.a16
    lda.l OamHiSrcIndex
    clc
    adc #4
    sta.l OamHiSrcIndex
    lda.l OamHiDstIndex
    inc a
    sta.l OamHiDstIndex
    cmp #32                             ; = OAM_SLOTS/4 groups of 4 sprites
    bcc Core_Oam_TransformHiOam__loop
    plp
    rts
