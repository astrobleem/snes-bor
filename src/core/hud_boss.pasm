; ============================================================================
; core/hud_boss.pasm -- Phase G9 (plan_game.md 9): boss health bar body.
; S8: campaign 3 dispatches to hud_opponent.pasm; the historical description
; below applies to the preserved legacy path for every other campaign.
; Own bank (like core/spawn.pasm/core/charselect.pasm before it) purely for
; $C100-$FC00 ROM budget -- this didn't fit alongside the rest of main.pasm's
; Hud_Play in that window. Entered via `jsl Hud_Play__boss_bar` from
; main.pasm's Hud_Play (a plain jsl/rtl call, not the trampoline-and-return-
; to-caller shape core/charselect.pasm needed -- this routine has no
; internal multi-step dispatch to worry about, just one straight-line body).
;
; Real OpenBOR (engine/openbor.c drawstatus()) shows an "opponent" bar
; (`elife`) for whatever entity the player is currently fighting, gated on
; that entity NOT having the `nolife` flag -- there is no boss-exclusive
; bar in the stock engine, and (per the same source, drawenemystatus()/
; combat.c) no boss-exclusive AI either: `boss` only (a) triggers
; `bossmusic` on spawn and (b) makes that entity's death check against
; `level->bossescount` for the win condition. This project has no general
; "current opponent" tracking (BOR's ent->opponent pointer, updated on
; every hit exchange) and no `nolife` concept for fodder enemies, so
; building the real generic mechanic is out of scope here -- EntityN_IsBoss
; (real, sourced, already-shipped data from the wait/group/boss slice) is
; used directly as the gate instead: the lowest-numbered living boss-
; flagged entity gets the bar, and the row goes blank when none is. The G4
; win condition already requires all AI dead before the camera unlocks
; (Spawn_LastTriggerX hold-clamp), so a boss stage is already camera-gated
; with no separate code needed.
;
; Own staging buffer (HudBossStaging, not HudStaging) and own DMA --
; main.pasm's Hud_Play__bar own queued transfer only ever covers
; HUD_STAGING_BYTES (row 0), so this needs an independent buffer/DMA the
; same way core/text.pasm's TextStaging is independent of HudStaging.
; Hud_DrawBar and Core_Dma_Enqueue both live in bank 0 and end in `rts`
; (same-bank-only) -- Hud_DrawBar_Long/Core_Dma_Enqueue_Long (main.pasm,
; next to Anim_LoadCharacter_Long/Core_Text_DrawString_Long) are the same
; small trampoline pattern core/charselect.pasm's own header documents.
;
; "Current boss": the lowest-numbered entity with IsBoss set AND HP>0 (real
; BOR levels realistically have exactly one active boss at a time). $FF
; (HudBossCachedHp's sentinel) means "no boss" -- draws as a fully blank
; row, same clear-then-conditionally-draw shape as Hud_Play__bar.
; ============================================================================
Hud_Play__boss_bar:
    sep #$20
.a8
    lda.l Game_CampaignId
    cmp #3
    bne Hud_Play__boss_bar_legacy
    jml HudOpponent_Play
Hud_Play__boss_bar_legacy:
    lda.l Entity1_IsBoss
    beq Hud_Play__boss_bar_check2
    lda.l Entity1_Hp
    bne Hud_Play__boss_bar_have
Hud_Play__boss_bar_check2:
    sep #$20
.a8
    lda.l Entity2_IsBoss
    beq Hud_Play__boss_bar_check3
    lda.l Entity2_Hp
    bne Hud_Play__boss_bar_have
Hud_Play__boss_bar_check3:
    sep #$20
.a8
    lda.l Entity3_IsBoss
    beq Hud_Play__boss_bar_none
    lda.l Entity3_Hp
    bne Hud_Play__boss_bar_have
Hud_Play__boss_bar_none:
.a8
    lda #$FF
Hud_Play__boss_bar_have:
    cmp.l HudBossCachedHp
    beq Hud_Play__boss_bar_clean
    sta.l HudBossCachedHp

    ; --- blank the staging row, then draw the bar over it (unless $FF --
    ; "no boss", leave it blank) ---
    rep #$31
.a16
.i16
    ldx #$0000
Hud_Play__boss_bar_clear:
    rep #$31
.a16
.i16
    lda #$0000
    sta.l HudBossStaging,x
    inx
    inx
    cpx #HUD_STAGING_BYTES
    bcc Hud_Play__boss_bar_clear

    sep #$20
.a8
    lda.l HudBossCachedHp
    cmp #$FF
    beq Hud_Play__boss_bar_dma
    rep #$10
.i16
    ldx #$0000              ; row-relative; DmaRequest_TargetAddr below picks the real row
    jsr Hud_Play__boss_bar_drawbar

Hud_Play__boss_bar_dma:
    rep #$31
.a16
.i16
    lda #HudBossStaging
    sta.l DmaRequest_SourceAddrLow
    lda #(BG3_TILEMAP_VRAM_WORD + HUD_ROW_BOSS * TEXT_ROW_ENTRIES) * 2
    sta.l DmaRequest_TargetAddr
    lda #HUD_STAGING_BYTES
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
    jsl Core_Dma_Enqueue_Long
    rtl
Hud_Play__boss_bar_clean:
    rtl

; ============================================================================
; Hud_Play__boss_bar_drawbar -- render one entity's health bar into
; HudBossStaging. A DUPLICATE of main.pasm's own Hud_DrawBar, not a shared
; call, because Hud_DrawBar hardcodes its target as `HudStaging` (the
; player's row-0 buffer, `sta.l HudStaging,x`) with no parameter for which
; buffer to use -- found the hard way: an earlier version of this file
; called Hud_DrawBar directly (via a bank-0 trampoline), which silently
; drew the boss bar into HudStaging instead of HudBossStaging, leaving
; HudBossStaging's own DMA copy out an all-blank row every time. Reusing
; HudStaging as scratch and copying the result over is NOT safe either --
; Hud_Play__bar's own DMA off HudStaging is QUEUED, not synchronous
; (core/text.pasm's documented "1024-BOR" bug is exactly this hazard
; class), so clobbering HudStaging here could corrupt row 0's own transfer
; if its queued DMA hasn't drained yet. A real duplicated block instead --
; same "small duplicated block over a parameterized shared one when the
; two call sites' surrounding state differs" precedent main.pasm's own
; Msu1_LoadFrame documents.
;   A = that entity's CHAR_HP (8-bit), X = byte offset of the bar's tilemap row
; Leaves X past the bar. Clobbers A/X/Y.
; ============================================================================
Hud_Play__boss_bar_drawbar:
    sep #$20
.a8
    sta.l HudBarHp
    inx
    inx                         ; skip column 0

    lda #HUD_TILE_CAP_LEFT
    sta.l HudBossStaging,x
    inx
    lda #HUD_ENTRY_HIGH
    sta.l HudBossStaging,x
    inx

    ldy #HUD_BAR_TILES
Hud_Play__boss_bar_drawbar_body:
    sep #$20
.a8
    lda.l HudBarHp
    cmp #8
    bcc Hud_Play__boss_bar_drawbar_partial
    lda #8
    sta.l HudBarFilled
    lda.l HudBarHp
    sec
    sbc #8
    sta.l HudBarHp
    bra Hud_Play__boss_bar_drawbar_have
Hud_Play__boss_bar_drawbar_partial:
    sep #$20
.a8
    sta.l HudBarFilled          ; A is still the remaining HP (< 8)
    lda #0
    sta.l HudBarHp
Hud_Play__boss_bar_drawbar_have:
    sep #$20
.a8
    lda.l HudBarFilled
    clc
    adc #HUD_TILE_FILL_BASE
    sta.l HudBossStaging,x
    inx
    lda #HUD_ENTRY_HIGH
    sta.l HudBossStaging,x
    inx
    dey
    bne Hud_Play__boss_bar_drawbar_body

    lda #HUD_TILE_CAP_RIGHT
    sta.l HudBossStaging,x
    inx
    lda #HUD_ENTRY_HIGH
    sta.l HudBossStaging,x
    inx
    rts

; Normal implementation shares this ROM bank, but owns its DMA buffers.
.include "hud_opponent.pasm"
.include "hud_text_banked.pasm"
