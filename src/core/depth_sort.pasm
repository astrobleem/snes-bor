; ============================================================================
; core/depth_sort.pasm -- Actor depth-sort slice (plan_game.md 7, sixth
; slice, following the jump/jumpattack/jumpattack2 slice).
;
; Own bank (.bank 9, jsl-entry/rtl-exit, same pattern as core/jump.pasm/
; core/pausemenu.pasm/core/options.pasm) for the standard reason: bank 0's
; $C100-$FC00 region is chronically at or near zero free bytes.
;
; Problem this fixes (found+documented by core/jump.pasm's own header, which
; explicitly flagged the gap rather than inventing a fix out of scope for
; that slice): every entity in this project always renders at the SAME OBJ
; priority bits (attribute byte always $30|(palette<<1) -- see Character_
; RenderFrame in main.pasm). For sprites of equal priority, real SNES
; hardware always draws the sprite with the LOWER OAM index in FRONT. Before
; this slice, main.pasm emitted OAM entries in fixed dispatch order (player
; always slot 0 -> always the lowest OAM index -> always drawn in front of
; every AI actor, regardless of which one is actually closer to the camera
; on screen). This is the real bug BOR-style ground-depth sorting exists to
; fix: an actor standing "in front" on screen (larger world/ground Y, lower
; on screen) must draw in front of an actor standing "behind" it (smaller
; Y), independent of which entity slot either one happens to occupy.
;
; This file provides ONLY the sort computation -- a pure function of each
; entity's real ground CHAR_POS_Y, no DP switching, no OAM access. The
; render-order-driven OAM emission loop (phd/tcd per entity + Character_
; RenderFrame dispatch) lives in main.pasm's Character_RenderPass, which is
; the sole caller.
;
; Depth key: CHAR_POS_Y (each entity's real ground/collision Y, read via the
; project's existing fixed-literal-per-slot addresses -- PlayerEntity_PosY/
; Entity1_PosY/Entity2_PosY/Entity3_PosY, all already defined in main.pasm
; for AI-seek/hit-apply). This is read BEFORE Character_RenderFrame's jsl
; Jump_ApplyOamYOffset ever runs for anyone this frame -- jump altitude
; (CHAR_THROW_ZPOS, shared by jump and throw -- notjustfreespecial.txt
; item 4) only ever perturbs the separate WRAM-staging
; OamSetSprite_Y cell inside Character_RenderFrame, never CHAR_POS_Y itself
; (core/jump.pasm's own header already documents that split; this file
; relies on it, doesn't re-implement it). So a jumping actor's ground-depth
; rank is untouched by its own altitude, exactly matching real OpenBOR's
; position.z (height) vs. position.y (depth/lane) separation that core/
; jump.pasm's header describes sourcing this project's jump slice from.
;
; Front-to-back order = descending CHAR_POS_Y (largest Y first). Ties
; (equal CHAR_POS_Y) break toward the lower entity index -- deterministic,
; not meaningfully different from real BOR's own equal-Y draw order, which
; isn't specified either.
; ============================================================================

; --- Depth_Sort_ComputeOrder -- called via jsl from main.pasm's Character_
; RenderPass, once per frame, before any OAM emission. No DP dependency (all
; reads/writes are bare $7Exxxx). Fills Depth_RenderOrder[0..3] (main.pasm)
; with entity ids 0-3, front-to-back.
;
;   @return  Depth_RenderOrder (main.pasm, $7E27E6-$7E27E9) filled.
;            A/X/Y width restored via php/plp; contents of A/X/Y not
;            meaningful to the caller (Character_RenderPass immediately
;            narrows/reloads what it needs).
Depth_Sort_ComputeOrder:
    php
    sep #$30
.a8
.i8
    ; Snapshot ground Y (NOT OamSetSprite_Y, NOT CHAR_THROW_ZPOS-adjusted --
    ; the real CHAR_POS_Y ground/collision key) for all 4 fixed entity
    ; slots, and mark all 4 as not-yet-placed.
    lda.l PlayerEntity_PosY
    sta.l Depth_Y+0
    lda.l Entity1_PosY
    sta.l Depth_Y+1
    lda.l Entity2_PosY
    sta.l Depth_Y+2
    lda.l Entity3_PosY
    sta.l Depth_Y+3
    ; `lda #0 / sta.l` instead of `stz.l`/`stz.w` -- STZ has no long
    ; addressing mode on 65816 at all, and no long-form-fitting bare/`.w`
    ; form either for a $7Exxxx-valued symbol (measured: both hard-error
    ; "does not fit the Absolute encoding" against Poppy fork HEAD; see
    ; allocate_wram.pasm's own identical comment/workaround).
    lda #0
    sta.l Depth_Used+0
    sta.l Depth_Used+1
    sta.l Depth_Used+2
    sta.l Depth_Used+3

    ; Selection sort, descending: 4 passes, each picks the largest
    ; not-yet-used Y and appends its entity id to Depth_RenderOrder. N=4
    ; fixed (this project's entity ceiling -- see PlayerEntity_PosX/Y's own
    ; comment in main.pasm), so an O(n^2) selection sort is both simpler and
    ; safer than a general sort here, matching this codebase's established
    ; preference for fixed-literal/unrolled-over-4 handling (same reasoning
    ; as the Entity1-3_Base literals themselves).
    jsr Depth_Sort_ComputeOrder__FindMax
    sta.l Depth_RenderOrder+0
    tax
    lda #1
    sta.l Depth_Used,x

    jsr Depth_Sort_ComputeOrder__FindMax
    sta.l Depth_RenderOrder+1
    tax
    lda #1
    sta.l Depth_Used,x

    jsr Depth_Sort_ComputeOrder__FindMax
    sta.l Depth_RenderOrder+2
    tax
    lda #1
    sta.l Depth_Used,x

    jsr Depth_Sort_ComputeOrder__FindMax
    sta.l Depth_RenderOrder+3
    ; last slot -- no need to mark used, nothing reads Depth_Used again
    ; until next frame's Depth_Sort_ComputeOrder call re-zeroes it.

    plp
    rtl

; Returns in A (8-bit) the entity id (0-3) with the largest Depth_Y among
; entries whose Depth_Used byte is still 0. Ties keep the first (lowest-id)
; candidate seen. Depth_BestVal/Idx/Found are this routine's own scratch,
; reset fresh on entry every call.
;
; Deliberately tracks a running best VALUE (Depth_BestVal) alongside the
; best INDEX, rather than re-indexing Depth_Y by the current best index --
; X is the only register with `.l Symbol,x` (absolute-long-indexed)
; addressing on 65816 (no `,y` long form exists, and LDX/STX/CPX have no
; long-addressing mode at all -- see CLAUDE.md's toolchain section), and
; this loop already needs X as the scan index, so a second live index into
; the same array isn't available without an extra push/pop per comparison.
; Tracking the value directly avoids needing one.
Depth_Sort_ComputeOrder__FindMax:
.a8
.i8
    lda #0
    sta.l Depth_BestFound
    ldx #0
Depth_Sort_ComputeOrder__FindMax__loop:
.a8
    lda.l Depth_Used,x
    bne Depth_Sort_ComputeOrder__FindMax__skip
    lda.l Depth_BestFound
    bne Depth_Sort_ComputeOrder__FindMax__compare
    ; first unused candidate seen this call -- take it unconditionally
    lda.l Depth_Y,x
    sta.l Depth_BestVal
    txa
    sta.l Depth_BestIdx
    lda #1
    sta.l Depth_BestFound
    bra Depth_Sort_ComputeOrder__FindMax__skip
Depth_Sort_ComputeOrder__FindMax__compare:
    lda.l Depth_Y,x
    cmp.l Depth_BestVal
    bcc Depth_Sort_ComputeOrder__FindMax__skip  ; candidate < best -- keep current best
    beq Depth_Sort_ComputeOrder__FindMax__skip  ; candidate == best -- keep FIRST (lower id)
    sta.l Depth_BestVal
    txa
    sta.l Depth_BestIdx
Depth_Sort_ComputeOrder__FindMax__skip:
.i8
    inx
    cpx #4
    bcc Depth_Sort_ComputeOrder__FindMax__loop

    lda.l Depth_BestIdx
    rts

; low16 DP-window base per entity id (0-3), word-indexed -- see PlayerEntity_
; DpBase/Entity1-3_DpBase's own comment (main.pasm) for why these exist as a
; second copy of the $7Exxxx bases. Indexed via `.l` (long, not bare
; absolute) specifically because this project keeps DBR=$7E throughout
; gameplay code -- a bare `lda EntityDpBaseTable,x` would read $7Exxxx WRAM
; instead of this ROM table (see "Indexed long addressing to a ROM data
; label" in CLAUDE.md's toolchain section for why `.l` is required and
; confirmed working here).
EntityDpBaseTable:
    .dw PlayerEntity_DpBase, Entity1_DpBase, Entity2_DpBase, Entity3_DpBase

; ============================================================================
; Character_RenderPass -- Actor depth-sort slice (plan_game.md 7, sixth
; slice). Emits this frame's OAM entries for all 4 fixed entity slots in
; real ground-depth order (front-to-back == descending CHAR_POS_Y), instead
; of the old fixed slot-0..3 dispatch order Character_PlayFrame (main.pasm)
; used to emit inline. Every entity's movement/anim/hit/grab has already
; resolved for this frame by the time this runs (called from game_state.
; pasm via jsl, right after jsr Core_Oop_Play finishes -- same relative
; position in the frame the old inline OAM emission ran at, so Core_Screen_
; Play/Hud_Play/Core_Oam_Play still run in the same order after it and
; nothing about Screen_PosX's read timing changes).
;
; Why sort matters here at all: every entity always renders at the SAME OBJ
; priority (attribute byte bits always $30|(palette<<1) -- priority 3, never
; varied per entity, see Character_RenderFrame's own comment). For sprites
; of equal priority, SNES hardware always draws the LOWER OAM index in
; FRONT. Before this slice, OAM index was assigned in fixed dispatch order
; (always player=slot0=lowest index=always drawn in front, regardless of
; actual on-screen depth) -- this routine is what this file's own header,
; and core/jump.pasm's before it, flagged as a gap ("no depth-sort axis was
; built... no dynamic OAM draw-order/priority sort for ANYTHING today").
;
; Depth key is real ground CHAR_POS_Y (Depth_Sort_ComputeOrder above),
; snapshotted BEFORE Character_RenderFrame's jsl Jump_ApplyOamYOffset runs
; for anyone -- jump altitude only ever perturbs the WRAM-staging
; OamSetSprite_Y cell inside Character_RenderFrame, never CHAR_POS_Y itself,
; so a jumping actor keeps its ground-depth rank exactly where it was on
; takeoff and lands back into it unchanged.
;
; jsl-entry/rtl-exit -- called via jsl from game_state.pasm (bank 0), and
; itself calls into bank 0's Character_RenderFrame via jsl/rtl (not jsr/rts
; -- cross-bank).
; ============================================================================
Character_RenderPass:
    php
    rep #$31
.a16
.i16
    ; Exactly one reset per frame, unconditionally -- this is now the ONLY
    ; place OAM entries are emitted (replaces the old per-entity Oam_
    ; CursorResetDone flag check that used to live in Character_PlayFrame).
    ; `lda #0 / sta.l` instead of `stz.l`/`stz.w` -- see Depth_Sort_
    ; ComputeOrder's own identical workaround above.
    lda #0
    sta.l Oam_CurrentSlot

    ; jsl (not jsr) even though both routines live in this same bank --
    ; Depth_Sort_ComputeOrder is itself a jsl-entry/rtl-exit routine (its
    ; OTHER caller was originally meant to be cross-bank; kept consistent
    ; rather than giving it two different calling conventions).
    jsl Depth_Sort_ComputeOrder

    ldx #0
Character_RenderPass__loop:
    ; --- entity id (0-3) for this render slot. Narrow to .a8 for the load
    ; ONLY -- 65816 8-bit LDA leaves the accumulator's high byte untouched
    ; (stale, not zeroed), a real, previously-shipped bug class in this
    ; project (see VM Gate 5's "8-bit-write/16-bit-read stale-byte
    ; regression" in project memory) -- the `and #$00FF` below, done back at
    ; .a16, is what actually clears it before this value is doubled and used
    ; as a word-table index. ---
    sep #$20
.a8
    lda.l Depth_RenderOrder,x
    phx                            ; save the outer loop counter -- X gets
                                    ; repurposed below for the DP-base table
                                    ; index (a different value, entity_id*2)
    rep #$31
.a16
.i16
    and #$00FF
    asl a                          ; entity_id*2 -- word-table byte offset
    tax
    lda.l EntityDpBaseTable,x
    phd
    tcd
    sep #$20
.a8
    jsl Character_RenderFrame
    rep #$31
.a16
.i16
    pld
    plx                            ; restore outer loop counter
    inx
    cpx #4
    bcc Character_RenderPass__loop

    plp
    rtl
