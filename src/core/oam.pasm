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

; --- Core_Oam_SetSprite's caller-filled request cells. Same pattern as
; core/dma.pasm's DmaRequest_* staging area (fill these, then jsr) rather
; than a register-passed convention -- 5 independent byte fields doesn't
; fit cleanly in A/X/Y. Not part of the shadow-clear range (OamShadow_End)
; -- always fully overwritten by the caller before use, same as OamHi*
; above. Fills the remaining gap before main.pasm's Anim_* block ($7E53B0).
OamSetSprite_X    = $7E53AB ; .db — X-low (0-255; 9th/X-high bit lives in Hi below)
OamSetSprite_Y    = $7E53AC ; .db
OamSetSprite_Tile = $7E53AD ; .db — OBJ base tile index
OamSetSprite_Attr = $7E53AE ; .db — priority/palette/flip byte
OamSetSprite_Hi   = $7E53AF ; .db — hi-table byte, pre-shifted (bit0=X-high, bit1=size),
                             ;        same convention as Oam_ExpandedHi's own entries

; Highest Oam_CurrentSlot byte-count ever seen across frames, so the
; per-frame post-upload reset (Core_Oam_ClearActive) only has to walk the
; slots that have ever actually been in use instead of the full 128-sprite
; table -- see Core_Oam_ClearActive's own header for why. NOT part of
; OamShadow_Start..End (must survive Core_Oam_Init's shadow-clear loop
; running before this cell exists, and is set to 0 explicitly below
; instead). $7E53C8: main.pasm's Anim_* block runs $7E53B0-$7E53C7,
; confirmed collision-free via a project-wide grep for $7E53C8 and up.
Oam_HighWaterSlot = $7E53C8 ; .dw

; Nonzero: Core_Oam_Play's NEXT call must transfer the full 544-byte table
; (both main and hi) regardless of Oam_CurrentSlot/Oam_HighWaterSlot,
; instead of just the active range -- see Core_Oam_Init's header for why
; a one-time full push is needed, and Core_Oam_Play's for how this flag is
; consumed. $7E53CA: immediately after Oam_HighWaterSlot ($7E53C8-C9),
; confirmed free via a project-wide grep for $7E53CA and up.
Oam_NeedFullUpload = $7E53CA ; .dw

OAM_DEFAULT_Y = $F0      ; off the visible 224-line frame -> sprite hidden

Core_Oam_Init:
    rep #$31
.a16
    lda #0
    ldx #0
Core_Oam_Init__clear_loop:
    sta.l OamShadow_Start,x
    inx
    inx
    cpx #OamShadow_End - OamShadow_Start
    bcc Core_Oam_Init__clear_loop

    lda #0
    sta.l Oam_HighWaterSlot

    jsr Core_Oam_ClearAll

    ; Real hardware OAM RAM starts in an undefined state (Mesen2 seeds it
    ; with random garbage at power-on/reset, matching real hardware's
    ; unpredictable SRAM contents) -- Core_Oam_ClearAll above only zeroes
    ; the WRAM *shadow* copy, and Core_Oam_Play's per-frame upload only
    ; ever DMAs the active range (see its own header), so without an
    ; explicit full-table push, every hardware OAM slot beyond whatever's
    ; actively used this session keeps its power-on garbage forever --
    ; invisible in WRAM-shadow-only testing (which is all this project did
    ; until a take_screenshot visual check caught it): a garbage slot's
    ; random Y coordinate combined with this project's 32x64 large sprite
    ; size means the "hidden" OAM_DEFAULT_Y=$F0 wrap trick doesn't apply to
    ; slots that were never written at all, so they render as scattered
    ; noise blocks across the whole visible screen.
    ;
    ; A first fix attempt hand-rolled a synchronous immediate DMA straight
    ; to hardware channel 7 here, bypassing the async queue entirely
    ; (reasoning: Core_Nmi_Init, which runs immediately before this, leaves
    ; the screen in forced blank, and forced blank permits OAM writes any
    ; time). That was abandoned after a real bug: DBR is not guaranteed 0
    ; this early in scpu_boot, so the register writes silently landed
    ; nowhere until switched to explicit `.l $00xxxx` addressing -- and even
    ; then, the hi-table target address written was wrong ($0200, a BYTE
    ; address, when $2102/$2103 take a 9-bit WORD address -- see
    ; Core_Oam_Play's own hi-table comment for the ground-truth fix), which
    ; alone fully explains the run-to-run "nondeterministic-looking" results
    ; this attempt produced: the real cause was a broken pass/fail metric
    ; (raw nonzero-byte count, which can't distinguish "cleared" from
    ; "correctly hidden at Y=$F0" -- Core_Oam_ClearAll's own hidden-slot
    ; value) combined with this real address bug, not any actual run-to-run
    ; variation.
    ;
    ; Fix: don't hand-roll a second DMA path at all. Just tell Core_Oam_Play
    ; its very next call must push the FULL table instead of only the
    ; active range -- routing the one-time full clear through the same
    ; already-proven Core_Oam_Play -> core/dma.pasm's queue ->
    ; Core_Nmi_Play -> Core_Dma_ProcessQueue path every other OAM upload
    ; uses, correctly vblank-timed and DBR-safe by construction, no raw
    ; register writes or NMI race here at all.
    lda #1
    sta.l Oam_NeedFullUpload

    ; default sprite tile base: VRAM word $4000
    lda #$4000
    sta Oam_VramStart

    sep #$20
.a8
    lda #$C2                ; base word $4000 (field 2 << 13), size mode 6
                             ; (16x32 small / 32x64 large -- Mesen2-source-
                             ; verified pair table, SnesPpuTools.cpp
                             ; _oamSizes[6] = {{2,4},{4,8}}) -- large (32x64,
                             ; 4 tiles wide x 8 tall) is what a real 32x48 BOR
                             ; character sprite uses now; was size mode 0
                             ; (8x8/16x16) for the old decorative test/dpad
                             ; sprites only.
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
Core_Oam_ClearAll__hi_loop:
    lda #0
    sta.l Oam_ExpandedHi,x
    sta.l Oam_PackedHi,x
    inx
    cpx #OAM_SLOTS
    bcc Core_Oam_ClearAll__hi_loop
    rts

; Post-upload per-frame reset, called by Core_Nmi_Play instead of
; Core_Oam_ClearAll. Same effect (hide every previously-active entry,
; rewind the write cursor) but bounded to Oam_HighWaterSlot -- the highest
; byte count Core_Oam_Play has ever actually used -- instead of walking
; the full 128-sprite / 544-byte table every single vblank regardless of
; how many sprites are live. That full walk (this routine's other half,
; Core_Oam_ClearAll, still used once at Core_Oam_Init boot time) was
; measured via a temporary HVBJOY probe in core/nmi.pasm to be the
; dominant cost pushing Core_Nmi_Play's forced-blank commit bracket past
; real vblank once a per-frame OAM sprite (Character_PlayFrame) made
; "clear+reupload every frame" the steady-state case: with 1 active
; sprite it walked 127 sprites' worth of dead work for every 1 that
; mattered. Core_Oam_Play is responsible for growing Oam_HighWaterSlot as
; Oam_CurrentSlot grows; this routine only ever reads it, never shrinks
; it -- shrinking would leave a since-vacated higher slot's stale sprite
; on screen forever, which is exactly the bug this whole shadow-buffer
; system exists to prevent.
Core_Oam_ClearActive:
    rep #$31
.a16
    lda #0
    sta Oam_CurrentSlot

    ; --- Main table: Oam_HighWaterSlot/4 sprites (exact -- Oam_CurrentSlot
    ; only ever advances by exactly 4 per sprite written, so this divides
    ; evenly, no rounding needed). ---
    lda.l Oam_HighWaterSlot
    lsr a
    lsr a
    beq Core_Oam_ClearActive__main_skip
    tay
    ldx #0
Core_Oam_ClearActive__main_loop:
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
    dey
    bne Core_Oam_ClearActive__main_loop
Core_Oam_ClearActive__main_skip:

    ; --- Hi table: ceil(sprite_count/4) bytes -- identical formula to
    ; Core_Oam_Play's own hi-table DMA length, so this clears exactly the
    ; byte range that could ever have actually been written to hardware. ---
    lda.l Oam_HighWaterSlot
    clc
    adc #15
    lsr a
    lsr a
    lsr a
    lsr a
    beq Core_Oam_ClearActive__hi_skip
    tay
    ldx #0
Core_Oam_ClearActive__hi_loop:
    lda #0
    sta.l Oam_ExpandedHi,x
    sta.l Oam_PackedHi,x
    inx
    dey
    bne Core_Oam_ClearActive__hi_loop
Core_Oam_ClearActive__hi_skip:
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
; brightness gets restored, every single frame, steady-state). That bug
; came from an *unpaced* loop enqueuing many duplicate uploads per real
; frame (Core_Nmi_WaitFrame didn't exist yet) -- it was never about "one
; upload per frame" being inherently unsafe. main.pasm's TestSprite_PlayFrame
; now legitimately calls Core_Oam_SetSprite + this routine every frame to
; drive a live sprite; one 544-byte OAM DMA/frame is a small fraction of
; vblank's budget and does not reintroduce that bug.
Core_Oam_Play:
    rep #$31
.a16
    lda Oam_CurrentSlot
    bne Core_Oam_Play__has_sprites
    lda.l Oam_NeedFullUpload
    bne Core_Oam_Play__has_sprites
    ; bra (same +-127 range limit as bcc/beq) has to clear the entire rest
    ; of this routine from here -- the longest jump in the file even before
    ; this session's additions grew it further. jmp is absolute, no range
    ; limit.
    jmp Core_Oam_Play__done
    nop
; Transfers only the ACTIVE sprite range (0..Oam_CurrentSlot for the main
; table, ceil(sprite_count/4) bytes for the hi table) instead of the fixed
; full 544-byte table every frame. Real hardware OAM slots beyond the
; active range simply keep whatever an earlier frame's (also-truncated)
; DMA last wrote there -- safe as long as nothing in this codebase ever
; writes a sprite into a slot and then later leaves it unwritten while
; some LOWER slot stays active (every current caller re-asserts every
; active sprite's full state every single frame, own boot-time or first-
; frame Core_Oam_ClearAll-driven upload already cleared the rest to hidden
; once) -- if a future entity system adds sprites that come and go non-
; contiguously, this needs revisiting (either go back to a full transfer,
; or explicitly re-hide a freed slot's Y before it drops out of the active
; range). Was a fixed 544-byte transfer (measured, via a temporary HVBJOY
; probe in core/nmi.pasm, to be the dominant cost pushing Core_Nmi_Play's
; commit bracket past real vblank once a real per-frame character sprite
; made "one sprite every frame" the steady-state case instead of an
; occasional test) -- with 1 active sprite this is 4+1=5 bytes instead of
; 544, cutting the OAM DMA to roughly 1% of its previous cost.
Core_Oam_Play__has_sprites:
    ; Grow the high-water mark Core_Oam_ClearActive uses to bound its
    ; per-frame walk -- see Oam_HighWaterSlot's own header comment. Only
    ; ever grows; a shrink would let a since-vacated slot's stale sprite
    ; survive on screen.
    lda Oam_CurrentSlot
    cmp.l Oam_HighWaterSlot
    bcc Core_Oam_Play__hwm_done
    sta.l Oam_HighWaterSlot
Core_Oam_Play__hwm_done:

    jsr Core_Oam_TransformHiOam

    ; --- Main table: Oam_CurrentSlot bytes (already a byte count: 4
    ; bytes/sprite), starting at OAM address 0 -- except on the one-shot
    ; full-upload frame (Oam_NeedFullUpload, set once by Core_Oam_Init),
    ; where the whole 512-byte table goes regardless of Oam_CurrentSlot so
    ; every hardware slot beyond the active range gets its power-on
    ; garbage overwritten with the already-zeroed WRAM shadow. ---
    lda #$5100                        ; low+mid byte of Oam_Buffer's address
    sta DmaRequest_SourceAddrLow
    lda #0
    sta DmaRequest_TargetAddr         ; OAM address 0
    lda.l Oam_NeedFullUpload
    beq Core_Oam_Play__main_len_partial
    lda #OAM_SLOTS * 4
    bra Core_Oam_Play__main_len_done
Core_Oam_Play__main_len_partial:
    lda Oam_CurrentSlot
                             ; every other branch target in this file guards with a nop; this one didn't,
                             ; the sibling bug below (Core_Oam_Play__hi_len_done) proved the risk is real
Core_Oam_Play__main_len_done:
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
    bcs Core_Oam_Play__queued_main
    ; bra (not just bcc/bcs) is also range-limited to +-127 bytes -- the
    ; hi-table dispatch block below (grown this session by the one-shot
    ; full-upload length decision) pushed Core_Oam_Play__done far enough
    ; away that a plain `bra` here no longer reaches it. jmp is absolute,
    ; no range limit.
    jmp Core_Oam_Play__done
Core_Oam_Play__queued_main:
    lda #1
    sta Oam_UploadFlag

    ; --- Hi table: ceil(sprite_count/4) bytes, starting at OAM address 512
    ; (word address $0100, NOT byte address $0200) -- real hardware OAM's
    ; hi table always starts there regardless of transfer size (it's a
    ; fixed region, not relocatable). $2102/$2103 (OAMADDL/H, written here
    ; as one 16-bit store spanning both, same as Core_Dma_TransferOam's own
    ; convention) take a 9-bit WORD address: OAMADDL is the low 8 bits,
    ; OAMADDH bit0 is bit 8, OAMADDH bit7 is EnableOamPriority (unrelated) --
    ; ground-truth verified against Mesen2's SnesPpu.cpp
    ; (`_state.InternalOamAddress = _state.OamRamAddress << 1`, i.e. the
    ; PPU's real internal byte address is the written value doubled). Byte
    ; 512 = word 256 = $0100. A previous version of this write used $0200
    ; (the BYTE address, only valid if this register took bytes) -- since
    ; $0200's low byte is $00 and OAMADDH's bit0 is 0, that silently
    ; targeted word 0 (main-table byte 0) instead, zeroing over live sprite
    ; data with hi-table content every frame this ran. Caught via a direct
    ; snesSpriteRam hardware-OAM read showing sprite 0's Y stuck at 0
    ; instead of the expected value.
    ; sprite_count = Oam_CurrentSlot/4; ceil(sprite_count/4) =
    ; ceil(Oam_CurrentSlot/16) = (Oam_CurrentSlot+15)>>4. Best-effort: if
    ; this second enqueue fails (queue full), the hi table just stays one
    ; frame stale -- for the size/X-high bits, which change far less often
    ; than position, this is not visually significant, unlike skipping the
    ; main table would be. ---
    lda #$5300                        ; low+mid byte of Oam_PackedHi's address
    sta DmaRequest_SourceAddrLow
    lda #$0100                        ; OAM word address 256 (hi table start)
    sta DmaRequest_TargetAddr

    ; Same one-shot-full-upload override as the main table above, decided
    ; and consumed here (this is the last read of Oam_NeedFullUpload this
    ; call) rather than at the main table's enqueue, so a queue-full
    ; failure on the main table (which leaves Oam_NeedFullUpload set for a
    ; retry next frame, see the bcs branch above) doesn't get contradicted
    ; by an early clear here.
    lda.l Oam_NeedFullUpload
    beq Core_Oam_Play__hi_len_partial
    lda #0
    sta.l Oam_NeedFullUpload
    lda #OAM_SLOTS / 4
    bra Core_Oam_Play__hi_len_done
Core_Oam_Play__hi_len_partial:
    lda Oam_CurrentSlot
    clc
    adc #15
    lsr a
    lsr a
    lsr a
    lsr a
    ; HISTORICAL, RESOLVED: this exact spot once root-caused a real Poppy
    ; branch-target label misresolution bug (poppy#4, fixed 2026-08-19 in
    ; the fork -- see CLAUDE.md's toolchain section). Core_Oam_Play__hi_
    ; len_done had no nop guard, so Poppy resolved the label onto the LAST
    ; `lsr a` above instead of the `sta` below it -- the one-shot full-
    ; upload branch (`lda #OAM_SLOTS/4 / bra Core_Oam_Play__hi_len_done`)
    ; landed there and silently re-executed that lsr, halving the intended
    ; 32-byte hi-table length to 16 before it ever reached the sta. Root-
    ; caused via a WRAM ring-log instrumenting Core_Dma_TransferOam's
    ; actual DAS7 value (16, not 32) cross-checked against a direct
    ; disassemble showing the label address landing mid-shift-sequence.
    ; The nop guards this bug required are no longer needed (poppy#4 fixed
    ; assembler-side); kept only as bug history, not a live workaround.
Core_Oam_Play__hi_len_done:
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
    bra Core_Oam_Play__done
Core_Oam_Play__done:
    rts

; Call once per sprite you want visible this frame, after filling
; OamSetSprite_X/Y/Tile/Attr/Hi. Writes one entry at the Oam_CurrentSlot
; cursor and advances it by 4 (one Oam_Buffer slot); does NOT call
; Core_Oam_Play itself -- caller writes every sprite for the frame first,
; then calls Core_Oam_Play once. Never indexes a .l bank-$7E symbol with Y
; (long-indexed-Y store doesn't exist in hardware -- see this file's header
; and Core_Oam_TransformHiOam's own bug-1 note); X only, per that same
; established pattern.
    nop
    nop
    nop
Core_Oam_SetSprite:
    php
    rep #$31
.a16
    lda Oam_CurrentSlot
    tax                          ; X = byte offset into Oam_Buffer (stride 4/sprite)

    sep #$20
.a8
    lda.l OamSetSprite_X
    sta.l Oam_Buffer,x
    lda.l OamSetSprite_Y
    sta.l Oam_Buffer+1,x
    lda.l OamSetSprite_Tile
    sta.l Oam_Buffer+2,x
    lda.l OamSetSprite_Attr
    sta.l Oam_Buffer+3,x

    rep #$31
.a16
    lda Oam_CurrentSlot
    lsr a
    lsr a                         ; sprite index = byte-offset / 4 (Oam_ExpandedHi is stride 1)
    tax

    sep #$20
.a8
    lda.l OamSetSprite_Hi
    sta.l Oam_ExpandedHi,x

    rep #$31
.a16
    lda Oam_CurrentSlot
    clc
    adc #4
    sta Oam_CurrentSlot

    plp
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
Core_Oam_TransformHiOam:
    php
    rep #$31
.a16
    lda #0
    sta.l OamHiSrcIndex
    sta.l OamHiDstIndex

    ; Only pack the groups Core_Oam_Play will actually DMA this frame --
    ; ceil(Oam_CurrentSlot/16) hi-table bytes, same formula as its DMA
    ; length -- instead of always walking the full 32 groups (128
    ; sprites) regardless of how many are active. This loop, unbounded,
    ; was (together with Core_Oam_ClearAll's own full-128 walk) the
    ; dominant per-frame cost pushing Core_Nmi_Play's vblank commit past
    ; real vblank -- see Core_Oam_ClearActive's header for the full story.
    lda Oam_CurrentSlot
    clc
    adc #15
    lsr a
    lsr a
    lsr a
    lsr a
    beq Core_Oam_TransformHiOam__done   ; nothing active -- nothing to pack
    tay
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
    dey
    bne Core_Oam_TransformHiOam__loop
Core_Oam_TransformHiOam__done:
    plp
    rts
