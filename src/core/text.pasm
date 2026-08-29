; ============================================================================
; core/text.pasm -- BG3 text renderer (plan_game.md Phase G1).
;
; The hard prerequisite for every later plan_game.md phase (menus, HUD text,
; score, game-state screens): nothing menu-shaped can exist before strings
; can be drawn. Reuses the exact same BG3-tilemap/DMA plumbing Hud_Play
; already proved out (Phase 6) -- a small WRAM staging buffer built per call,
; then one queued VRAM DMA via Core_Dma_Enqueue, never a direct $2118/9
; write (see core/nmi.pasm's header on why an unpaced per-frame direct write
; corrupts the top of the frame).
;
; Font source: the BOR pak's own DATA\SPRITES\FONT.GIF (see
; tools/bg_converter/make_font_tiles.py's header for the full extraction
; rationale), ROM-resident in `.bank 2` (Font_TilesData/Font_PaletteData in
; main.pasm) and DMA'd into VRAM/CGRAM once by Core_Text_Init -- not
; MSU-streamed, since font data is small, static, and never changes at
; runtime, unlike character/BG art.
;
; Palette: BG3 tilemap palette id FONT_CGRAM_PAL_ID (1), i.e. CGRAM colors
; 4-7 (real hardware: a 2bpp tile's palette field p reads CGRAM p*4..p*4+3).
; Palette id 0 is the HUD's; ids 1-3 are ALSO what convert_frontpanel.py uses
; on a level with a frontpanel layer (all 4 available BG3 palette ids are
; taken when one is loaded -- see convert_bg.py's PALETTE_OFFSET comment).
; The currently-shipped level (stage 1B) has no frontpanel, so palette id 1
; is safe today. DELIBERATELY UNRESOLVED: a level with both a frontpanel and
; on-screen text needs a real answer (draw text on BG1 instead, or suspend
; the FP resolver while text/menus are up) -- not implemented here.
;
; VRAM: font tiles at word FONT_TILES_VRAM_WORD ($5900), inside BG3's
; existing $5000-$5FFF char-base block (BG34NBA, unchanged), past the HUD's
; 12 tiles ($5000-$505F) and the frontpanel streaming cache's reserved
; region ($5100-$58FF) -- see main.pasm's VRAM map comment above Bg_LoadScene
; for the full picture. 95 glyphs * 8 words = 760 words fits the remaining
; $5900-$5FFF (1792 words) with room to spare.
;
; Tilemap: BG3's single 32x32 map at word BG3_TILEMAP_VRAM_WORD, same map the
; HUD (rows 0-3) and frontpanel (rows 21-27, when loaded) already share.
; Core_Text_DrawString/DrawNumber take an explicit row/col -- callers must
; pick rows that don't collide with those two owners.
;
; String source: NOT a runtime pointer. This project deliberately avoids
; Direct-Page indirect addressing outside core/oop.pasm's own per-instance DP
; window (see vm_run.pasm's "never `[ptr],y`, DP is core/oop.pasm's"), and
; 65816 has no indirect addressing mode that doesn't go through DP. Instead,
; every string a caller wants to draw is baked into one ROM table,
; Text_StringPool (bank 2, right after the font data), and callers pass a
; compile-time offset INTO that pool -- the same fixed-base-plus-index
; pattern core/vm/vm_string.pasm already uses for its own string reads.
;
; ROM budget: this file's CODE must fit in the reserved $8C60-$9000 gap (928
; bytes) -- see main.pasm's `.org $8C60` site and plan_vm.md 0.3's matching
; $9000-$AC00 VM reservation right after it. Overflow past $9000 silently
; corrupts the VM region, not a build error. Text_StringPool's DATA lives in
; bank 2 instead, alongside the font blob, so it doesn't compete for this
; budget.
; ============================================================================

FONT_DATA_BANK       = $02   ; Font_TilesData/Font_PaletteData/Text_StringPool's bank (main.pasm .bank 2)
FONT_TILES_VRAM_WORD = $5900
FONT_TILE_INDEX_BASE = (FONT_TILES_VRAM_WORD - BG3_TILES_VRAM_WORD) / 8   ; = 288
FONT_CGRAM_PAL_ID    = 1
FONT_CGRAM_BYTE_ADDR = FONT_CGRAM_PAL_ID * 4 * 2   ; = 8 (CGADD is a color index, DMA target is bytes)
FONT_TILE_BYTES      = 1520   ; 95 tiles * 16 bytes (2bpp)
FONT_PALETTE_BYTES   = 8      ; 4 colors * 2 bytes

FONT_ASCII_FIRST = 32
FONT_ASCII_LAST  = 126

TEXT_ROW_ENTRIES = 32
TEXT_ROW_BYTES   = TEXT_ROW_ENTRIES * 2   ; 64

; $7E2500-$7E256B was NOT free -- it silently overlapped both
; StreamCache_* (core/stream_cache.pasm, $7E2500-$7E2520) and
; StreamScroll_ColBuf (main.pasm, $7E255A-$7E2591), both of which are live
; whenever BG1 streaming is running (i.e. as soon as the camera scrolls).
; Found via a plain grep for every existing WRAM address before picking a
; new base, not by re-checking the original choice -- that grep is what
; should have happened the first time. Relocated to $7E2700, past every
; address main.pasm/core/*.pasm currently declare (highest prior use found:
; StreamScrollFp_RepairCur, ending $7E2666) with margin to spare.
TextStaging           = $7E2700   ; 64B -- one tilemap row, pre-DMA (scratch, reused per call)
Text_Row              = $7E2740   ; .db
Text_StagingOffset    = $7E2741   ; .dw -- byte offset into TextStaging, advances as glyphs are emitted
Text_StringIndex      = $7E2743   ; .dw -- running index into Text_StringPool (DrawString only)
Text_NumberValue      = $7E2745   ; .dw -- remaining value (DrawNumber only)
Text_PlaceValue       = $7E2747   ; .dw
Text_Started          = $7E2749   ; .db -- leading-zero suppression flag
Text_DigitScratch     = $7E274A   ; .db
; Text_G1DemoDrawn: one-shot flag, NOT part of the general text API -- see
; its own use site in main.pasm's scpu_main_loop for why it exists (the
; queue-drain hazard below).
Text_G1DemoDrawn      = $7E274B   ; .db
Text_LabelValue       = $7E274C   ; .dw -- Core_Text_DrawLabeledNumber's 4th
                                    ; parameter (row/col/label already fill
                                    ; A/X/Y; the value doesn't fit a 4th
                                    ; register, so the caller sets this cell
                                    ; immediately before the jsr, same
                                    ; before-the-call-parameter-cell pattern
                                    ; DmaRequest_* already uses for Core_Dma_
                                    ; Enqueue)

; TextStaging is ONE shared buffer reused by every DrawString/DrawNumber
; call, and Text_FlushRow's DMA is QUEUED, not synchronous (core/dma.pasm:
; "Queue-only for now", drained once per frame from Core_Nmi_Play/NMI).
; Calling DrawString/DrawNumber twice in the same frame -- and ESPECIALLY
; twice before the first NMI has ever fired, i.e. from boot code before
; Core_Nmi_Init -- overwrites TextStaging's content before the first call's
; queued DMA actually runs, so both transfers end up copying whatever the
; LAST call left in the buffer. Caught exactly this way: a boot-time
; DrawString("SNES-BOR") immediately followed by a boot-time
; DrawNumber(1024) rendered "1024-BOR" on row 4 (the string's row) instead
; of "SNES-BOR" on row 4 and "1024" on row 5 -- both DMAs fired against the
; post-DrawNumber buffer contents once NMI finally started. Caller's
; responsibility: don't call either of these again until at least one NMI
; has drained the queue since the last call (verified in this project's own
; gate -- see tools/verify/game_g1_text.py and its callers in main.pasm).

; ============================================================================
; Core_Text_Init -- one-time boot load of font tiles + palette from ROM into
; VRAM/CGRAM. Call once. NOT alongside the other Core_*_Init calls before
; Core_Nmi_Init -- two real ordering constraints instead (see main.pasm's own
; call site for the full story): must run AFTER Bg_LoadScene (whose CGRAM
; image load zeros the whole BG3-reserved CGRAM block, clobbering the font's
; colors if this ran first) and AFTER Character_BlankPadding_Guarded (whose
; raw $2116/$2118 VRAM writes are unsafe against ANY DMA-queue traffic
; draining mid-loop, this call's included, while unguarded -- fixed by
; wrapping BlankPadding itself in Core_Nmi_Stop/Start, not by this call's
; position, but keeping this after it too is still correct and simpler than
; re-deriving the ordering later).
; ============================================================================
    nop
Core_Text_Init:
    php
    rep #$31
.a16
.i16
    lda #Font_TilesData
    sta.l DmaRequest_SourceAddrLow
    lda #FONT_TILES_VRAM_WORD * 2
    sta.l DmaRequest_TargetAddr
    lda #FONT_TILE_BYTES
    sta.l DmaRequest_Length
    sep #$20
.a8
    lda #FONT_DATA_BANK
    sta.l DmaRequest_SourceBank
    lda #DMA_TYPE_VRAM
    sta.l DmaRequest_TypeFlags
    rep #$31
.a16
.i16
    jsr Core_Dma_Enqueue

    ; --- Palette: direct synchronous $2121/$2122 writes, NOT the queue.
    ; An earlier version queued this exactly like the tile DMA above and it
    ; appeared to silently never land (CGRAM colors 4-7 read back as zero at
    ; boot). Root cause found and fixed: it was never the queue -- it was
    ; boot ORDER. Core_Text_Init was being called before Bg_LoadScene, and
    ; Bg_LoadScene's own CGRAM image load zeroes the entire BG3-reserved
    ; CGRAM block as part of loading BG1's palette, wiping out whatever this
    ; DMA had just written. Moving the Core_Text_Init call to run AFTER
    ; Bg_LoadScene (see main.pasm) is what actually fixed it; a queued DMA
    ; would work fine there too. Kept as a direct write anyway since it's
    ; only 8 bytes and this project already has a working precedent for the
    ; exact same CGRAM range (Bg_LoadSceneFp_Streaming's own
    ; "CGADD = color 4 (BG3 sub-palette 1)" loop) -- not a reliability fix,
    ; just reuses an existing pattern instead of the queue for something
    ; this small. ---
    sep #$20
.a8
    lda #FONT_CGRAM_PAL_ID * 4   ; CGADD = color 4
    sta $2121
    rep #$31
.a16
.i16
    ldx #0
Core_Text_Init__pal_loop:
    sep #$20
.a8
    lda.l Font_PaletteData,x
    sta $2122
    rep #$31
.a16
.i16
    inx
    cpx #FONT_PALETTE_BYTES
    bne Core_Text_Init__pal_loop

    plp
    rts

; ============================================================================
; Text_EmitGlyph -- write one glyph's tilemap word into TextStaging at
; Text_StagingOffset, then advance it. No-op (offset still advances) once the
; row is full, so callers don't need their own bounds check.
;   A(8-bit) = ASCII code
; Clobbers A/X. Out-of-range codes draw as blank (space) rather than garbage.
; ============================================================================
    nop
Text_EmitGlyph:
    sep #$20
.a8
    cmp #FONT_ASCII_FIRST
    bcc Text_EmitGlyph__blank
    cmp #FONT_ASCII_LAST + 1
    bcc Text_EmitGlyph__have
Text_EmitGlyph__blank:
    sep #$20
.a8
    lda #FONT_ASCII_FIRST
Text_EmitGlyph__have:
    sep #$20
.a8
    sec
    sbc #FONT_ASCII_FIRST        ; A = glyph index 0-94 (8-bit, cannot overflow)
    rep #$31
.a16
.i16
    and #$00FF                   ; zero-extend to 16-bit
    clc
    adc #FONT_TILE_INDEX_BASE     ; full 10-bit tile id -- must be a real 16-bit
                                   ; add: FONT_TILE_INDEX_BASE (288) already
                                   ; exceeds one byte, so splitting this into
                                   ; separate 8-bit low/high stores (an earlier
                                   ; version did) silently drops the tile id's
                                   ; bit 8 unless the low-byte add is proven
                                   ; never to carry -- one 16-bit word write
                                   ; below avoids the whole hazard.
    ora #(HUD_ENTRY_HIGH * $100)  ; priority bit, same convention as Hud_DrawBar
    ora #(FONT_CGRAM_PAL_ID * $0400)  ; BG3 tilemap palette field (bits 10-12)
    pha                           ; save the finished word
    lda.l Text_StagingOffset
    tax
    cpx #TEXT_ROW_BYTES
    bcs Text_EmitGlyph__skip
    pla
    sta.l TextStaging,x           ; 16-bit word store: low byte at x, high at x+1
    inx
    inx
    txa
    sta.l Text_StagingOffset
    rts
Text_EmitGlyph__skip:
    rep #$31
.a16
.i16
    pla
    rts

; ============================================================================
; Text_FlushRow -- DMA TextStaging's full 32-entry row to BG3 tilemap row
; Text_Row (already set by the caller before this is reached; NOT passed via
; A/stack -- an earlier version pushed A in 8-bit mode and pulled it back in
; 16-bit mode after a width change, silently misaligning the stack).
; Clobbers A/X/Y.
; ============================================================================
    nop
Text_FlushRow:
    rep #$31
.a16
.i16
    lda #TextStaging
    sta.l DmaRequest_SourceAddrLow
    lda.l Text_Row
    and #$00FF
    asl a                    ; row * 32 entries * 2 bytes/entry = row << 6
    asl a
    asl a
    asl a
    asl a
    asl a
    clc
    adc #BG3_TILEMAP_VRAM_WORD * 2
    sta.l DmaRequest_TargetAddr
    lda #TEXT_ROW_BYTES
    sta.l DmaRequest_Length
    sep #$20
.a8
    lda #$7E
    sta.l DmaRequest_SourceBank
    lda #DMA_TYPE_VRAM
    sta.l DmaRequest_TypeFlags
    rep #$31
.a16
.i16
    jsr Core_Dma_Enqueue
    rts

; ============================================================================
; Core_Text_DrawString -- draw a null-terminated Text_StringPool entry into
; one BG3 tilemap row, starting at the given column.
;   A(8-bit)  = row (0-31)
;   X(16-bit) = column (0-31)
;   Y(16-bit) = offset into Text_StringPool (see the pool's own labels below)
; Clobbers A/X/Y.
; ============================================================================
    nop
Core_Text_DrawString:
    php
    sep #$20
.a8
    sta.l Text_Row
    rep #$31
.a16
.i16
    txa
    asl a
    sta.l Text_StagingOffset
    tya
    sta.l Text_StringIndex
Core_Text_DrawString__loop:
    rep #$31
.a16
.i16
    lda.l Text_StringIndex
    tax
    sep #$20
.a8
    lda.l Text_StringPool,x
    beq Core_Text_DrawString__done
    pha
    rep #$31
.a16
.i16
    inx
    txa
    sta.l Text_StringIndex
    sep #$20
.a8
    pla
    jsr Text_EmitGlyph
    bra Core_Text_DrawString__loop
Core_Text_DrawString__done:
    jsr Text_FlushRow
    plp
    rts

; ============================================================================
; Text_DrawNumber__digit -- divide Text_NumberValue by Text_PlaceValue,
; emitting the quotient digit unless it's a suppressed leading zero.
; Clobbers A/X.
; ============================================================================
    nop
Text_DrawNumber__digit:
    rep #$31
.a16
.i16
    lda.l Text_PlaceValue
    pha
    lda.l Text_NumberValue
    tax
    pla
    jsr Core_Math_Div        ; A = quotient (the digit, 0-9), X = remainder
    rep #$31
.a16
.i16
    pha                       ; save quotient
    txa
    sta.l Text_NumberValue    ; remainder -> new value
    pla                       ; restore quotient
    sep #$20
.a8
    sta.l Text_DigitScratch
    lda.l Text_Started
    bne Text_DrawNumber__digit__show
    lda.l Text_DigitScratch
    bne Text_DrawNumber__digit__show
    rep #$31
.a16
.i16
    lda.l Text_PlaceValue
    cmp #1
    beq Text_DrawNumber__digit__force
    rts
Text_DrawNumber__digit__force:
    sep #$20
.a8
Text_DrawNumber__digit__show:
    sep #$20
.a8
    lda #1
    sta.l Text_Started
    lda.l Text_DigitScratch
    clc
    adc #$30                  ; '0'
    jsr Text_EmitGlyph
    rts

; ============================================================================
; Core_Text_DrawNumber -- draw a 16-bit unsigned value as decimal, no leading
; zeros (0 itself draws as a single "0"), left-aligned at the given column.
;   A(8-bit)  = row (0-31)
;   X(16-bit) = column (0-31)
;   Y(16-bit) = value (0-65535)
; Clobbers A/X/Y.
; ============================================================================
    nop
Core_Text_DrawNumber:
    php
    sep #$20
.a8
    sta.l Text_Row
    rep #$31
.a16
.i16
    txa
    asl a
    sta.l Text_StagingOffset
    tya
    sta.l Text_NumberValue
    sep #$20
.a8
    lda #0
    sta.l Text_Started

    rep #$31
.a16
.i16
    lda #10000
    sta.l Text_PlaceValue
    jsr Text_DrawNumber__digit
    rep #$31
.a16
.i16
    lda #1000
    sta.l Text_PlaceValue
    jsr Text_DrawNumber__digit
    rep #$31
.a16
.i16
    lda #100
    sta.l Text_PlaceValue
    jsr Text_DrawNumber__digit
    rep #$31
.a16
.i16
    lda #10
    sta.l Text_PlaceValue
    jsr Text_DrawNumber__digit
    rep #$31
.a16
.i16
    lda #1
    sta.l Text_PlaceValue
    jsr Text_DrawNumber__digit

    jsr Text_FlushRow
    plp
    rts

; ============================================================================
; Core_Text_DrawLabeledNumber -- Phase G6 (plan_game.md 6): draw a short
; label followed immediately by a decimal number (no leading zeros), then
; blank every remaining column through 32, all in ONE Text_FlushRow -- built
; specifically so callers never need the 2-calls-across-2-frames drip
; DrawString+DrawNumber would otherwise require (see this file's own
; TextStaging-hazard note above): unlike calling DrawString then DrawNumber
; back to back, this composes both column ranges into a single TextStaging
; pass before its one flush, so it is exactly as safe to call once per frame
; as either primitive alone -- the existing "don't call any Draw* twice in
; the same frame" rule still applies to THIS routine as a whole, but it only
; costs one call (and one queued DMA) to draw a full label+value row.
;
; Always redraws every column through 32, including ones the number itself
; didn't touch -- this is what makes it safe to call again with a SHORTER
; number later (e.g. this project's own scoreboard rows, which only ever
; grow, but a future caller might not): unlike Core_Text_DrawNumber alone,
; a shrinking value here can't leave a stale trailing digit, because nothing
; past the label is ever left unwritten.
;
;   A(8-bit)  = row (0-31)
;   X(16-bit) = column the label starts at (0-31)
;   Y(16-bit) = offset into Text_StringPool of the label (short -- must
;               leave room for the widest value this call site will ever
;               draw, plus at least one column of separation; callers are
;               responsible for this, same as any other fixed-width HUD
;               layout in this codebase)
;   Text_LabelValue (.dw, set by caller before this jsr) = the number
; Clobbers A/X/Y.
; ============================================================================
Core_Text_DrawLabeledNumber:
    php
    sep #$20
.a8
    sta.l Text_Row
    rep #$31
.a16
.i16
    txa
    asl a
    sta.l Text_StagingOffset
    tya
    sta.l Text_StringIndex
Core_Text_DrawLabeledNumber__label_loop:
    rep #$31
.a16
.i16
    lda.l Text_StringIndex
    tax
    sep #$20
.a8
    lda.l Text_StringPool,x
    beq Core_Text_DrawLabeledNumber__label_done
    pha
    rep #$31
.a16
.i16
    inx
    txa
    sta.l Text_StringIndex
    sep #$20
.a8
    pla
    jsr Text_EmitGlyph
    bra Core_Text_DrawLabeledNumber__label_loop
Core_Text_DrawLabeledNumber__label_done:
    ; --- number: same digit-place loop Core_Text_DrawNumber uses, sharing
    ; Text_NumberValue/Text_PlaceValue/Text_Started/Text_DigitScratch and
    ; Text_DrawNumber__digit itself (no leading zeros; continues from
    ; wherever the label left Text_StagingOffset). ---
    rep #$31
.a16
.i16
    lda.l Text_LabelValue
    sta.l Text_NumberValue
    sep #$20
.a8
    lda #0
    sta.l Text_Started
    rep #$31
.a16
.i16
    lda #10000
    sta.l Text_PlaceValue
    jsr Text_DrawNumber__digit
    rep #$31
.a16
.i16
    lda #1000
    sta.l Text_PlaceValue
    jsr Text_DrawNumber__digit
    rep #$31
.a16
.i16
    lda #100
    sta.l Text_PlaceValue
    jsr Text_DrawNumber__digit
    rep #$31
.a16
.i16
    lda #10
    sta.l Text_PlaceValue
    jsr Text_DrawNumber__digit
    rep #$31
.a16
.i16
    lda #1
    sta.l Text_PlaceValue
    jsr Text_DrawNumber__digit

    ; --- blank every remaining column through 32, so a shorter value never
    ; leaves a longer previous draw's trailing digit behind. ---
    rep #$31
.a16
.i16
    lda.l Text_StagingOffset
    lsr a                    ; byte offset -> column
    tax
Core_Text_DrawLabeledNumber__pad_loop:
    rep #$31
.a16
.i16
    cpx #TEXT_ROW_ENTRIES
    bcs Core_Text_DrawLabeledNumber__pad_done
    sep #$20
.a8
    lda #32                  ; ASCII space
    jsr Text_EmitGlyph
    rep #$31
.a16
.i16
    inx
    bra Core_Text_DrawLabeledNumber__pad_loop
Core_Text_DrawLabeledNumber__pad_done:
    jsr Text_FlushRow
    plp
    rts

; ============================================================================
; Core_Text_G1Demo -- one-shot Core_Text_DrawNumber proof, called from
; scpu_main_loop right after its first Core_Nmi_WaitFrame each frame (main
; only invokes it there; the flag makes every call after the first a no-op).
;
; NOT called from boot alongside the DrawString demo. TextStaging is one
; buffer shared by every DrawString/DrawNumber call, and Text_FlushRow's DMA
; is queued, not synchronous -- calling this before Core_Nmi_Init (i.e.
; before any NMI has ever drained the queue) would overwrite TextStaging's
; content before the boot-time DrawString's own queued transfer runs, and
; both would end up copying the DrawNumber call's bytes. That happened for
; real: a boot-time DrawString("SNES-BOR") followed immediately by a
; boot-time DrawNumber(1024) rendered "1024-BOR" on row 4 instead of
; "SNES-BOR" on row 4 / "1024" on row 5. Firing here instead, after
; Core_Nmi_WaitFrame has returned at least once, guarantees a real NMI (and
; therefore a Core_Dma_ProcessQueue drain) already ran since the boot-time
; call, so this call's use of TextStaging is safe.
;
; Row 5, value 1024: nonzero leading digit exercises Text_Started's
; leading-zero suppression, the interior 0 exercises a mid-number zero
; digit (not suppressed), the trailing 4 exercises the final always-shown
; digit. Clobbers A/X/Y (same as Core_Text_DrawNumber, which does the work).
; ============================================================================
    nop
Core_Text_G1Demo:
    sep #$20
.a8
    lda.l Text_G1DemoDrawn
    bne Core_Text_G1Demo__done
    lda #1
    sta.l Text_G1DemoDrawn
    lda #5
    rep #$31
.a16
.i16
    ldx #0
    ldy #1024
    jsr Core_Text_DrawNumber
    rts
Core_Text_G1Demo__done:
    rts
