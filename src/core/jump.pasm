; ============================================================================
; core/jump.pasm -- Real jump slice (plan_game.md 7, first of three
; sequential slices: jump, then special, then grab/throw mutual-lock).
;
; Own bank (.bank 8, jsl-entry/rtl-exit, same pattern as core/pausemenu.pasm/
; core/options.pasm) for the standard reason: $C100-$FC00 is chronically at
; or near zero free bytes, and this module's base-offset chaining math is
; large (three chained 24-bit shift-add-by-768 hops) but only ever needed
; for the player.
;
; Real OpenBOR-sourced physics (DCurrent/openbor, engine/openbor.c, fetched
; and read this slice -- NOT invented):
;   - tryjump()/dojump()/toss(): jumpheight IS the initial upward velocity
;     directly (toss(self, jumpheight) sets velocity.y = jumpheight), not a
;     peak-height value requiring a physics solve.
;   - check_gravity(): position.y += velocity.y each tick; velocity.y +=
;     gravity each tick (gravity = -0.1 by default, level->gravity); land
;     when position.y <= base (0 here) AND velocity.y <= 0.
;   - LEO's real char file (data\CHARS\LEO\LEO.TXT, TMNT pak): `jumpheight 5`
;     (his own jumpheight; the commented-out `#jumpspeed 20` is real BOR's
;     own default fallback too -- default_model_jumpspeed=-1 sentinel means
;     "use max(speed.x, 1)", and LEO's speed field IS 20).
;   - Ground-jump trigger (real BOR.C, the player think loop): `FLAG_JUMP &&
;     notinair` -- edge-triggered-then-consumed, not held-repeat.
;
; Q8.8 fixed point (16-bit signed, 8 fractional bits) for height/velocity --
; SNES has no float unit. JUMP_INITIAL_VEL/JUMP_GRAVITY (main.pasm) are the
; literal real BOR.C constants (5.0, -0.1) scaled by 256, NOT a feel-tuned
; conversion -- OpenBOR's internal Y-units don't map 1:1 onto SNES pixels/
; 60fps, so this project keeps the same literal magnitudes rather than
; inventing a screen-scale-matched constant (see JUMP_INITIAL_VEL's own
; comment in main.pasm for the full reasoning).
;
; Scope, this slice only (per the user's explicit "do only jump" -- special
; and grab/throw mutual-lock are separate, later slices):
;   - Player (slot 0) only. AI entities never jump today; nothing here reads
;     these cells for them.
;   - Real Z-axis: up/down (height above ground), gravity, landing.
;   - jump/jumpattack/jumpattack2 anims wired to real LEO frame data (the
;     only roster character with any of the three today).
;   - Visual-only OAM Y offset while airborne -- CHAR_POS_Y itself (the real
;     ground/collision Y) is never touched, matching real OpenBOR's own
;     separation of position.z (ground/depth, this project's CHAR_POS_Y) and
;     position.y (pure jump height, this project's CHAR_THROW_ZPOS). This
;     project has no dynamic OAM draw-order/priority sort for ANYTHING
;     today (core/oam.pasm confirmed, grep-checked this slice) -- CHAR_POS_Y
;     movement already doesn't get one, so jump doesn't need to invent one
;     to match that existing baseline; it only needs the visual height
;     offset, which this file provides.
;   - Horizontal movement while airborne deliberately reuses the EXISTING
;     continuous per-frame dpad-read walk code unchanged, rather than
;     porting real BOR.C's one-shot ballistic X-velocity-at-launch model --
;     this project already re-reads dpad input every frame for ground
;     movement, so a second, parallel X-velocity system would be redundant,
;     not a gameplay difference the player would ever notice.
; ============================================================================

; --- Jump_ComputeBases -- called via jsl from bank 0's Anim_LoadCharacter,
; once per character load (boot + live reselect), for EVERY entity.
;
; First computes map_base (24-bit) = attack2_base + (attack2 + jump +
; jumpattack + jumpattack2 frame_count)*768 (plan_game.md 8a row 3, `map`)
; UNCONDITIONALLY, for every entity -- moved here from bank 0 for ROM
; budget ($C100-$FC00 was at its ceiling), not because it's player-only;
; every entity needs its own map_base regardless of who's driving it (a
; boss render-reassigned onto an AI slot still needs its own real
; map_base). Same shift-add-by-768 idiom as every other *_base field, fed a
; SUMMED count instead of attack2_fcount alone: n*768+m*768+k*768+j*768 ==
; (n+m+k+j)*768, so one hop lands exactly where 4 chained hops would
; (jump/jumpattack/jumpattack2 sit consecutively between attack2 and remap
; in the blob -- pack_msu_roster.py's layout). Collapses back to the
; pre-jump-slice value when jump/jumpattack/jumpattack2_fcount are all 0
; (every character except LEO).
;
; THEN no-ops (rtl) for anything but the player (CHAR_INPUT_DRIVEN==1)
; before computing the 3 individual chained player-only bases (jump_base =
; attack2_base + attack2_fcount*768; jumpattack_base = jump_base +
; jump_fcount*768; jumpattack2_base = jumpattack_base +
; jumpattack_fcount*768) and copying them, plus the already-read
; JumpRecFCount/Delay-family transient cells (main.pasm, populated earlier
; in the SAME Anim_LoadCharacter call this jsl came from), into the real
; Player_Jump* cells gameplay reads -- these are standalone player-only
; WRAM cells, not a per-instance struct field, same reasoning as
; Player_InvulnFrames (project memory: a shared struct field for state only
; the player ever uses once broke spawn-slot assignment despite
; audit_all.py passing clean).
;
; Caller convention: .a16/.i16 in, .a16/.i16 out (matches Anim_LoadCharacter's
; own convention at this call site).
Jump_ComputeBases:
.a16
.i16
    sep #$20
.a8
    lda CHAR_ATTACK2_FCOUNT
    clc
    adc.l JumpRecFCount
    clc
    adc.l JumpAttackRecFCount
    clc
    adc.l JumpAttack2RecFCount
    rep #$31
.a16
.i16
    and #$00FF
    sta.l AnimHeaderStaging+12
    asl a
    clc
    adc.l AnimHeaderStaging+12
    sta.l AnimHeaderStaging+14
    sep #$20
.a8
    lda #0
    sta.l AnimHeaderStaging+12
    lda.l AnimHeaderStaging+14
    sta.l AnimHeaderStaging+13
    rep #$31
.a16
.i16
    lda CHAR_ATTACK2_BASE_LO
    clc
    adc.l AnimHeaderStaging+12
    sta CHAR_SPECIAL_BASE_LO
    sep #$20
.a8
    lda CHAR_ATTACK2_BASE_HI
    adc.l AnimHeaderStaging+15
    sta CHAR_SPECIAL_BASE_HI

    ; --- G7 content-audit slice: 6 more chained hops (attack3, attack4,
    ; grabmove, slide, riseattack, grabattack -- NEW_MOVE_SLOT_NAMES' own
    ; order, matching pack_msu_roster.py's blob layout), THEN CHAR_MAP_BASE
    ; itself as a 7th final hop -- all computed for EVERY entity
    ; unconditionally (any entity, including an AI-driven roster slot,
    ; needs its own correct CHAR_MAP_BASE, which must skip past all 6 new
    ; slots regardless of who's driving; this replaces the old special-
    ; slice map_base=special_base+special_fcount*768 single hop). Uses the
    ; shared Jump_HopBase subroutine (below) instead of 7 more hand-unrolled
    ; shift-add blocks -- this slice's own "generic table, not more
    ; copy-paste" directive. Collapses back to the pre-this-slice value
    ; when all 6 new slots' fcount are 0 (every roster member but LEO/
    ; BEBOP/ROCK/LEATHER/FOOT01/FOOT02). ---
    lda CHAR_SPECIAL_FCOUNT
    sta.l JumpHopFCount
    lda CHAR_SPECIAL_BASE_LO
    sta.l JumpHopBaseLo
    lda CHAR_SPECIAL_BASE_LO+1
    sta.l JumpHopBaseLo+1
    lda CHAR_SPECIAL_BASE_HI
    sta.l JumpHopBaseHi
    jsr Jump_HopBase
    lda.l JumpHopBaseLo
    sta CHAR_ATTACK3_BASE_LO
    lda.l JumpHopBaseLo+1
    sta CHAR_ATTACK3_BASE_LO+1
    lda.l JumpHopBaseHi
    sta CHAR_ATTACK3_BASE_HI

    lda CHAR_ATTACK3_FCOUNT
    sta.l JumpHopFCount
    lda CHAR_ATTACK3_BASE_LO
    sta.l JumpHopBaseLo
    lda CHAR_ATTACK3_BASE_LO+1
    sta.l JumpHopBaseLo+1
    lda CHAR_ATTACK3_BASE_HI
    sta.l JumpHopBaseHi
    jsr Jump_HopBase
    lda.l JumpHopBaseLo
    sta CHAR_ATTACK4_BASE_LO
    lda.l JumpHopBaseLo+1
    sta CHAR_ATTACK4_BASE_LO+1
    lda.l JumpHopBaseHi
    sta CHAR_ATTACK4_BASE_HI

    lda CHAR_ATTACK4_FCOUNT
    sta.l JumpHopFCount
    lda CHAR_ATTACK4_BASE_LO
    sta.l JumpHopBaseLo
    lda CHAR_ATTACK4_BASE_LO+1
    sta.l JumpHopBaseLo+1
    lda CHAR_ATTACK4_BASE_HI
    sta.l JumpHopBaseHi
    jsr Jump_HopBase
    lda.l JumpHopBaseLo
    sta CHAR_GRABMOVE_BASE_LO
    lda.l JumpHopBaseLo+1
    sta CHAR_GRABMOVE_BASE_LO+1
    lda.l JumpHopBaseHi
    sta CHAR_GRABMOVE_BASE_HI

    lda CHAR_GRABMOVE_FCOUNT
    sta.l JumpHopFCount
    lda CHAR_GRABMOVE_BASE_LO
    sta.l JumpHopBaseLo
    lda CHAR_GRABMOVE_BASE_LO+1
    sta.l JumpHopBaseLo+1
    lda CHAR_GRABMOVE_BASE_HI
    sta.l JumpHopBaseHi
    jsr Jump_HopBase
    lda.l JumpHopBaseLo
    sta CHAR_SLIDE_BASE_LO
    lda.l JumpHopBaseLo+1
    sta CHAR_SLIDE_BASE_LO+1
    lda.l JumpHopBaseHi
    sta CHAR_SLIDE_BASE_HI

    lda CHAR_SLIDE_FCOUNT
    sta.l JumpHopFCount
    lda CHAR_SLIDE_BASE_LO
    sta.l JumpHopBaseLo
    lda CHAR_SLIDE_BASE_LO+1
    sta.l JumpHopBaseLo+1
    lda CHAR_SLIDE_BASE_HI
    sta.l JumpHopBaseHi
    jsr Jump_HopBase
    lda.l JumpHopBaseLo
    sta CHAR_RISEATTACK_BASE_LO
    lda.l JumpHopBaseLo+1
    sta CHAR_RISEATTACK_BASE_LO+1
    lda.l JumpHopBaseHi
    sta CHAR_RISEATTACK_BASE_HI

    lda CHAR_RISEATTACK_FCOUNT
    sta.l JumpHopFCount
    lda CHAR_RISEATTACK_BASE_LO
    sta.l JumpHopBaseLo
    lda CHAR_RISEATTACK_BASE_LO+1
    sta.l JumpHopBaseLo+1
    lda CHAR_RISEATTACK_BASE_HI
    sta.l JumpHopBaseHi
    jsr Jump_HopBase
    lda.l JumpHopBaseLo
    sta CHAR_GRABATTACK_BASE_LO
    lda.l JumpHopBaseLo+1
    sta CHAR_GRABATTACK_BASE_LO+1
    lda.l JumpHopBaseHi
    sta CHAR_GRABATTACK_BASE_HI

    lda CHAR_GRABATTACK_FCOUNT
    sta.l JumpHopFCount
    lda CHAR_GRABATTACK_BASE_LO
    sta.l JumpHopBaseLo
    lda CHAR_GRABATTACK_BASE_LO+1
    sta.l JumpHopBaseLo+1
    lda CHAR_GRABATTACK_BASE_HI
    sta.l JumpHopBaseHi
    jsr Jump_HopBase
    lda.l JumpHopBaseLo
    sta CHAR_FREESPECIAL_BASE_LO
    lda.l JumpHopBaseLo+1
    sta CHAR_FREESPECIAL_BASE_LO+1
    lda.l JumpHopBaseHi
    sta CHAR_FREESPECIAL_BASE_HI

    lda CHAR_FREESPECIAL_FCOUNT
    sta.l JumpHopFCount
    lda CHAR_FREESPECIAL_BASE_LO
    sta.l JumpHopBaseLo
    lda CHAR_FREESPECIAL_BASE_LO+1
    sta.l JumpHopBaseLo+1
    lda CHAR_FREESPECIAL_BASE_HI
    sta.l JumpHopBaseHi
    jsr Jump_HopBase
    lda.l JumpHopBaseLo
    sta CHAR_GET_BASE_LO
    lda.l JumpHopBaseLo+1
    sta CHAR_GET_BASE_LO+1
    lda.l JumpHopBaseHi
    sta CHAR_GET_BASE_HI

    ; claude_close_g7_g8_before_g10.md Part 2: get_base -> waiting_base, one
    ; more hop (pack_msu_roster.py's blob appends get_bytes right after
    ; freespecial's own frames, BEFORE waiting -- new_slot_bytes now
    ; includes 'get' LAST in NEW_MOVE_SLOT_NAMES) -- collapses back to the
    ; pre-this-slice waiting_base value when CHAR_GET_FCOUNT==0 (every
    ; roster member except LEO).
    lda CHAR_GET_FCOUNT
    sta.l JumpHopFCount
    lda CHAR_GET_BASE_LO
    sta.l JumpHopBaseLo
    lda CHAR_GET_BASE_LO+1
    sta.l JumpHopBaseLo+1
    lda CHAR_GET_BASE_HI
    sta.l JumpHopBaseHi
    jsr Jump_HopBase
    lda.l JumpHopBaseLo
    sta CHAR_WAITING_BASE_LO
    lda.l JumpHopBaseLo+1
    sta CHAR_WAITING_BASE_LO+1
    lda.l JumpHopBaseHi
    sta CHAR_WAITING_BASE_HI

    ; notjustfreespecial.txt G5 slice: waiting_base -> map_base, one more
    ; hop (pack_msu_roster.py appends waiting_bytes right after the
    ; freespecial/new-slot frames, BEFORE the remap section) -- collapses
    ; back to the pre-this-slice map_base value when CHAR_WAITING_FCOUNT==0
    ; (every roster member except LEO).
    lda CHAR_WAITING_FCOUNT
    sta.l JumpHopFCount
    lda CHAR_WAITING_BASE_LO
    sta.l JumpHopBaseLo
    lda CHAR_WAITING_BASE_LO+1
    sta.l JumpHopBaseLo+1
    lda CHAR_WAITING_BASE_HI
    sta.l JumpHopBaseHi
    jsr Jump_HopBase
    lda.l JumpHopBaseLo
    sta CHAR_MAP_BASE_LO
    lda.l JumpHopBaseLo+1
    sta CHAR_MAP_BASE_LO+1
    lda.l JumpHopBaseHi
    sta CHAR_MAP_BASE_HI

    lda CHAR_INPUT_DRIVEN
    cmp #1
    beq Jump_ComputeBases__is_player
    rep #$31
.a16
.i16
    rtl
Jump_ComputeBases__is_player:
.a8
    lda.l JumpRecFCount
    sta.l Player_JumpFCount
    lda.l JumpRecDelay
    sta.l Player_JumpDelay
    lda.l JumpAttackRecFCount
    sta.l Player_JumpAttackFCount
    lda.l JumpAttackRecDelay
    sta.l Player_JumpAttackDelay
    lda.l JumpAttack2RecFCount
    sta.l Player_JumpAttack2FCount
    lda.l JumpAttack2RecDelay
    sta.l Player_JumpAttack2Delay

    ; --- hop 1: jump_base = attack2_base + attack2_fcount*768 ---
    lda CHAR_ATTACK2_FCOUNT
    rep #$31
.a16
.i16
    and #$00FF
    sta.l AnimHeaderStaging+12
    asl a
    clc
    adc.l AnimHeaderStaging+12
    sta.l AnimHeaderStaging+14
    sep #$20
.a8
    lda #0
    sta.l AnimHeaderStaging+12
    lda.l AnimHeaderStaging+14
    sta.l AnimHeaderStaging+13
    rep #$31
.a16
.i16
    lda CHAR_ATTACK2_BASE_LO
    clc
    adc.l AnimHeaderStaging+12
    sta.l Player_JumpBaseLo
    sep #$20
.a8
    lda CHAR_ATTACK2_BASE_HI
    adc.l AnimHeaderStaging+15
    sta.l Player_JumpBaseHi

    ; --- hop 2: jumpattack_base = jump_base + jump_fcount*768 ---
    lda.l Player_JumpFCount
    rep #$31
.a16
.i16
    and #$00FF
    sta.l AnimHeaderStaging+12
    asl a
    clc
    adc.l AnimHeaderStaging+12
    sta.l AnimHeaderStaging+14
    sep #$20
.a8
    lda #0
    sta.l AnimHeaderStaging+12
    lda.l AnimHeaderStaging+14
    sta.l AnimHeaderStaging+13
    rep #$31
.a16
.i16
    lda.l Player_JumpBaseLo
    clc
    adc.l AnimHeaderStaging+12
    sta.l Player_JumpAttackBaseLo
    sep #$20
.a8
    lda.l Player_JumpBaseHi
    adc.l AnimHeaderStaging+15
    sta.l Player_JumpAttackBaseHi

    ; --- hop 3: jumpattack2_base = jumpattack_base + jumpattack_fcount*768 ---
    lda.l Player_JumpAttackFCount
    rep #$31
.a16
.i16
    and #$00FF
    sta.l AnimHeaderStaging+12
    asl a
    clc
    adc.l AnimHeaderStaging+12
    sta.l AnimHeaderStaging+14
    sep #$20
.a8
    lda #0
    sta.l AnimHeaderStaging+12
    lda.l AnimHeaderStaging+14
    sta.l AnimHeaderStaging+13
    rep #$31
.a16
.i16
    lda.l Player_JumpAttackBaseLo
    clc
    adc.l AnimHeaderStaging+12
    sta.l Player_JumpAttack2BaseLo
    sep #$20
.a8
    lda.l Player_JumpAttackBaseHi
    adc.l AnimHeaderStaging+15
    sta.l Player_JumpAttack2BaseHi

    rep #$31
.a16
.i16
    rtl

; --- Jump_HopBase -- G7 content-audit slice. Shared subroutine: new_base =
; prev_base + prev_fcount*768 (the same shift-add-by-768 idiom every other
; *_base field in this project chains with), factored out so the 7 new
; chain hops above are ~14-line call sites instead of ~25-line hand-unrolled
; blocks each. Same-bank jsr (called only from within Jump_ComputeBases).
;
;   in:  .a8 -- JumpHopFCount (frame count of the PREVIOUS slot),
;        JumpHopBaseLo/JumpHopBaseHi (PREVIOUS slot's 24-bit base).
;   out: JumpHopBaseLo/JumpHopBaseHi overwritten with prev_base +
;        prev_fcount*768. Clobbers A. Width in/out: .a8/.i16 (matches every
;        call site above, which is always mid-Jump_ComputeBases at .a8).
Jump_HopBase:
.a8
    lda.l JumpHopFCount
    rep #$31
.a16
.i16
    and #$00FF
    sta.l AnimHeaderStaging+12
    asl a
    clc
    adc.l AnimHeaderStaging+12
    sta.l AnimHeaderStaging+14
    sep #$20
.a8
    lda #0
    sta.l AnimHeaderStaging+12
    lda.l AnimHeaderStaging+14
    sta.l AnimHeaderStaging+13
    rep #$31
.a16
.i16
    lda.l JumpHopBaseLo
    clc
    adc.l AnimHeaderStaging+12
    sta.l JumpHopBaseLo
    sep #$20
.a8
    lda.l JumpHopBaseHi
    adc.l AnimHeaderStaging+15
    sta.l JumpHopBaseHi
    rts

; --- Jump_PlaySpecialAdvance -- G7 special slice. Called via jsl from bank
; 0's Anim_Play_Special__jsl (moved here for ROM budget, same reasoning as
; every other bank-8 relocation in this file). Mirrors Anim_Play_Attack2's
; own advance/revert-to-idle shape exactly, just reading CHAR_SPECIAL_*
; fields -- Msu1_LoadFrame itself can't move (same-bank-only constraint,
; AnimBase_ComputeFallBase's own comment), so this routine only sets up
; CHAR_FRAME_INDEX/AnimHeaderStaging and signals via carry whether the
; bank-0 caller still needs to make that call. Only ever reached with
; CHAR_ATTACK_VARIANT==2, which only Jump_PlayerInputGate's own special
; trigger ever sets (gated there on CHAR_SPECIAL_FCOUNT!=0), so no zero-
; frame-count guard is needed here -- matches attack2's own precondition-
; trusted shape.
;
;   in:  none (DP-local self).
;   out: carry SET = caller must jsr Msu1_LoadFrame (CHAR_FRAME_INDEX/
;        AnimHeaderStaging+0/+2 ready); carry CLEAR = animation finished,
;        already reverted to idle. Clobbers A.
Jump_PlaySpecialAdvance:
.a8
    lda CHAR_FRAME_INDEX
    inc a
    cmp CHAR_SPECIAL_FCOUNT
    bcc Jump_PlaySpecialAdvance__frame_ok
    lda #0
    sta CHAR_SELECTED
    lda #$FF
    sta CHAR_FRAME_INDEX
    lda #1
    sta CHAR_TICK_COUNTER
    clc
    rtl
Jump_PlaySpecialAdvance__frame_ok:
.a8
    sta CHAR_FRAME_INDEX
    lda CHAR_SPECIAL_DELAY
    sta CHAR_TICK_COUNTER
    rep #$31
.a16
.i16
    lda CHAR_SPECIAL_BASE_LO
    sta.l AnimHeaderStaging+0
    sep #$20
.a8
    lda CHAR_SPECIAL_BASE_HI
    sta.l AnimHeaderStaging+2
    sec
    rtl

; --- Jump_PlayGetAdvance -- claude_close_g7_g8_before_g10.md Part 2. Same
; shape as Jump_PlaySpecialAdvance above (its own dedicated fcount/delay/
; base fields, not the indexed move-slot table -- see CHAR_GET_FCOUNT's own
; struct comment). Only ever reached with CHAR_ATTACK_VARIANT==GET_MOVE_
; VARIANT, set by Character_Pickup_CheckOverlap's own trigger (gated there
; on CHAR_GET_FCOUNT!=0), so no zero-frame-count guard needed, matching
; special's own precondition-trusted shape.
;
;   in:  none (DP-local self -- always the player, same as special's own
;        contract, since only the player ever collects an item).
;   out: carry SET = caller must jsr Msu1_LoadFrame; carry CLEAR =
;        animation finished, already reverted to idle. Clobbers A.
Jump_PlayGetAdvance:
.a8
    lda CHAR_FRAME_INDEX
    inc a
    cmp CHAR_GET_FCOUNT
    bcc Jump_PlayGetAdvance__frame_ok
    lda #0
    sta CHAR_SELECTED
    lda #$FF
    sta CHAR_FRAME_INDEX
    lda #1
    sta CHAR_TICK_COUNTER
    clc
    rtl
Jump_PlayGetAdvance__frame_ok:
.a8
    sta CHAR_FRAME_INDEX
    lda CHAR_GET_DELAY
    sta CHAR_TICK_COUNTER
    rep #$31
.a16
.i16
    lda CHAR_GET_BASE_LO
    sta.l AnimHeaderStaging+0
    sep #$20
.a8
    lda CHAR_GET_BASE_HI
    sta.l AnimHeaderStaging+2
    sec
    rtl

; --- Jump_PlayMoveSlotAdvance -- G7 content-audit slice (extended by the
; reopened-again slice's `freespecial` addition). The real generic
; animation descriptor table this slice's own directive calls for: ONE
; shared routine for all 7 new move slots (attack3/attack4/grab/slide/
; riseattack/grabattack/freespecial), instead of a 6th, 7th, 8th...
; hand-copied Anim_Play_Attack2__advance-style block. Works because the 7
; slots' DP fields are laid out with a fixed 5-byte stride (CHAR_ATTACK3_
; FCOUNT=76, CHAR_ATTACK4_FCOUNT=81, ... CHAR_GRABATTACK_FCOUNT=101,
; CHAR_FREESPECIAL_FCOUNT=106 -- see main.pasm's CHAR_* struct comment;
; freespecial was deliberately placed immediately after grabattack, NOT
; after the unrelated atchain/combo block, specifically to preserve this
; stride) -- direct-page-indexed-by-X addressing (`lda CHAR_ATTACK3_
; FCOUNT,x`) reaches any of the 7 slots' fields from ONE set of
; instructions, X = (CHAR_ATTACK_VARIANT-3)*5.
;
;   in:  none (DP-local self) -- computes X = (CHAR_ATTACK_VARIANT-3)*5
;        itself (ROM budget: bank 0 was at its $C100-$FC00 ceiling, so this
;        multiply moved here instead of staying a bank-0 stub computation).
;   out: carry SET = caller must jsr Msu1_LoadFrame (CHAR_FRAME_INDEX/
;        AnimHeaderStaging+0/+2 ready); carry CLEAR = animation finished,
;        already reverted to idle. Clobbers A/X. Entry .a8, exit
;        .a8-equivalent (matches Jump_PlaySpecialAdvance's own convention).
Jump_PlayMoveSlotAdvance:
.a8
    ; claude_close_g7_g8_before_g10.md Part 2: GET (variant 10) redirected
    ; here since the bank-0 caller (Anim_Play_Attack) still just checks
    ; variant>=3 -- own dedicated fields, NOT this indexed table (its own
    ; X=(variant-3)*5 addressing would land on CHAR_ATCHAIN0 for variant
    ; 10, not a real move-slot field -- see CHAR_GET_FCOUNT's own struct
    ; comment). Checked here, bank 8, instead of adding a second bank-0
    ; dispatch branch (that bank was already at its ROM ceiling).
    lda CHAR_ATTACK_VARIANT
    cmp #GET_MOVE_VARIANT
    bne Jump_PlayMoveSlotAdvance__not_get
    jmp Jump_PlayGetAdvance
Jump_PlayMoveSlotAdvance__not_get:
.a8
    lda CHAR_ATTACK_VARIANT
    sec
    sbc #3
    rep #$31
.a16
.i16
    and #$00FF
    sta.l JumpHopBaseLo             ; scratch reuse (Jump_ComputeBases only
    asl a                            ; uses this mid-load-character, never
    asl a                            ; concurrently with attack dispatch)
    clc
    adc.l JumpHopBaseLo
    tax
    sep #$20
.a8
    lda CHAR_FRAME_INDEX
    inc a
    cmp CHAR_ATTACK3_FCOUNT,x
    bcc Jump_PlayMoveSlotAdvance__frame_ok
    lda #0
    sta CHAR_SELECTED
    lda #$FF
    sta CHAR_FRAME_INDEX
    lda #1
    sta CHAR_TICK_COUNTER
    clc
    rtl
Jump_PlayMoveSlotAdvance__frame_ok:
.a8
    sta CHAR_FRAME_INDEX
    lda CHAR_ATTACK3_DELAY,x
    sta CHAR_TICK_COUNTER
    lda CHAR_ATTACK3_BASE_LO,x
    sta.l AnimHeaderStaging+0
    lda CHAR_ATTACK3_BASE_LO+1,x
    sta.l AnimHeaderStaging+1
    lda CHAR_ATTACK3_BASE_HI,x
    sta.l AnimHeaderStaging+2
    sec
    rtl

; --- Jump_AtchainTrigger -- G7 content-audit slice. Real perform_atchain()
; (DCurrent/openbor engine/openbor.c, called from player_think()): a SINGLE
; attack button cycles the character's declared attack1-4 sequence --
; repeated presses within a combo-timer window advance CHAR_COMBOSTEP;
; letting the window lapse resets to step 0. Only ever called (from bank
; 0's Anim_Play__no_jump_this_frame) when CHAR_CHAINLENGTH!=0 -- LEO
; (`atchain 1 2 3 1 2 4`), FOOT01/FOOT02 (`atchain 1 2 3`) today.
;
; ATCHAIN_COMBO_WINDOW is a feel-tuned frame count (real BOR.C's own combo
; window is derived from each move's `attack.time`/animation delay, not a
; single fixed constant) -- not a re-derived real magnitude, same class of
; deliberate simplification this project already applies to jump's X-
; velocity model (see core/jump.pasm's file header). CHAR_ATCHAIN0-5 are
; PRE-TRANSLATED at pack time (pack_msu_roster.py's ATCHAIN_RAW_TO_VARIANT)
; from real BOR attack-numbers into this engine's own CHAR_ATTACK_VARIANT
; values (0/1/3/4 only -- atchain never references special or the other 4
; new move slots), so this routine only ever writes a variant Anim_Play_
; Attack already understands.
;
;   in:  none (DP-local self, always the player -- CHAR_CHAINLENGTH!=0 is
;        only ever set on the CURRENTLY LOADED character's own struct, and
;        this is only reached via the player-input path).
;   out: carry SET = a new attack step was triggered this frame (CHAR_
;        SELECTED/CHAR_ATTACK_VARIANT/CHAR_FRAME_INDEX/CHAR_TICK_COUNTER
;        all set, same shape as attack1/attack2's own trigger code) --
;        caller dispatches immediately. Carry CLEAR = no press this frame
;        (COMBOTIMER decayed if running) -- caller falls through to
;        idle/walk dispatch. Clobbers A/X.
ATCHAIN_COMBO_WINDOW = 40
Jump_AtchainTrigger:
.a8
    lda CHAR_COMBOTIMER
    beq Jump_AtchainTrigger__no_decay
    dec a
    sta CHAR_COMBOTIMER
Jump_AtchainTrigger__no_decay:
.a8
    lda.l Input_trigger+1
    and #ANIM_ATTACK_BUTTON_MASK    ; Y -- the sole real chain button
    bne Jump_AtchainTrigger__pressed
    clc
    rtl
Jump_AtchainTrigger__pressed:
.a8
    lda CHAR_COMBOTIMER
    beq Jump_AtchainTrigger__reset
    lda CHAR_COMBOSTEP
    inc a
    cmp CHAR_CHAINLENGTH
    bcc Jump_AtchainTrigger__step_set
    lda #0
    bra Jump_AtchainTrigger__step_set
Jump_AtchainTrigger__reset:
.a8
    lda #0
Jump_AtchainTrigger__step_set:
    sta CHAR_COMBOSTEP
    rep #$31
.a16
.i16
    and #$00FF
    tax
    sep #$20
.a8
    lda CHAR_ATCHAIN0,x
    sta CHAR_ATTACK_VARIANT
    lda #ATCHAIN_COMBO_WINDOW
    sta CHAR_COMBOTIMER
    lda #2
    sta CHAR_SELECTED
    lda #$FF
    sta CHAR_FRAME_INDEX
    lda #1
    sta CHAR_TICK_COUNTER
    sec
    rtl

; --- Jump_RiseattackTrigger -- G7 content-audit slice. Real
; player_lie_check() (DCurrent/openbor engine/openbor.c): UP(held)+attack
; (Y, edge) while lying (HP>0, not still playing the fall animation, not
; the terminal dead-blink state) plays riseattack instead of the ordinary
; rise. Player-only (every other G7 trigger in this project is
; deliberately player-only -- jump/special/throw all share this scope
; boundary), gated on CHAR_RISEATTACK_FCOUNT!=0 (BEBOP/ROCK/LEATHER only,
; real converted `riseattack` data). Reuses the existing CHAR_SELECTED==2
; attack pathway (variant 7 = riseattack's move slot) so Character_
; HitApply's hit check needs no dedicated per-move code, matching this
; project's established attack2/special precedent. Only ever called (from
; bank 0's Anim_Play__player_input) when CHAR_SELECTED==CHAR_SELECTED_FALL.
;
;   in:  none (DP-local self).
;   out: carry SET = riseattack triggered this frame (CHAR_SELECTED/
;        CHAR_ATTACK_VARIANT/CHAR_FRAME_INDEX/CHAR_TICK_COUNTER/CHAR_
;        FALL_STATE_TIMER all set) -- caller dispatches immediately. Carry
;        CLEAR = no trigger (caller's existing FALL/RISE reaction-lock
;        continues unchanged). Clobbers A.
Jump_RiseattackTrigger:
.a8
    lda CHAR_INPUT_DRIVEN
    cmp #1
    bne Jump_RiseattackTrigger__no
    lda CHAR_RISEATTACK_FCOUNT
    beq Jump_RiseattackTrigger__no
    lda CHAR_FALL_STATE_TIMER
    beq Jump_RiseattackTrigger__no
    cmp #$FF
    beq Jump_RiseattackTrigger__no
    lda.l Input_press+1
    and #$08                        ; Up held
    beq Jump_RiseattackTrigger__no
    lda.l Input_trigger+1
    and #ANIM_ATTACK_BUTTON_MASK    ; Y edge
    beq Jump_RiseattackTrigger__no
    lda #0
    sta CHAR_FALL_STATE_TIMER
    lda #2
    sta CHAR_SELECTED
    lda #7                           ; riseattack's move-slot variant
    sta CHAR_ATTACK_VARIANT
    lda #$FF
    sta CHAR_FRAME_INDEX
    lda #1
    sta CHAR_TICK_COUNTER
    sec
    rtl
Jump_RiseattackTrigger__no:
.a8
    clc
    rtl

; --- Jump_LoadFreespecialRecord -- G7 reopened-again slice. Moved off the
; bank-0 Anim_LoadCharacter hot path for ROM budget (main.pasm was at its
; $C100-$FC00 ceiling) -- reads the 2 sequential MSU port bytes (freespecial
; fcount/delay, RECORD_SIZE 44->46) straight to DP and zeroes the FSM
; tracking fields, same discipline as every other new-slot fcount/delay
; pair, just relocated. DP is already switched to this entity at the call
; site (mid Anim_LoadCharacter).
;
;   in:  none. out: none. Clobbers A.
Jump_LoadFreespecialRecord:
.a8
    lda $2001
    sta CHAR_FREESPECIAL_FCOUNT
    lda $2001
    sta CHAR_FREESPECIAL_DELAY
    lda #0
    sta CHAR_FREESPECIAL_STEP
    sta CHAR_FREESPECIAL_TIMER
    rtl

; --- Jump_FreespecialTrigger -- G7 reopened-again slice. Real
; model_init_defaultreadme() (DCurrent/openbor engine/openbor.c, ~line
; 21039) auto-installs a default 3-step command (forward,forward,attack)
; into model->special[] for any character declaring ANI_FREESPECIAL without
; an explicit `special` command override, consumed via player_preinput()->
; check_combo() (player_think(), BEFORE player_check_special()) -- a real,
; player-reachable trigger, not the "AI-exclusive" classification the prior
; content-audit slice wrongly gave it (see CHAR_FREESPECIAL_FCOUNT's own
; comment in main.pasm). FREESPECIAL_TAP_WINDOW is a feel-tuned frame count
; (real BOR.C uses command_input_hold_trigger_collect()/command_input_
; history_grace_time_get(), COMMAND_TIME_DEFAULT=GAME_SPEED_DEFAULT/4=50,
; against a full input-history ring buffer, not a single FSM timer) -- not
; a re-derived real magnitude, same class of deliberate simplification this
; project already applies to atchain's own combo window (ATCHAIN_COMBO_
; WINDOW just above). LEO is the only roster member with real freespecial
; data (CHAR_FREESPECIAL_FCOUNT!=0) -- every other character's forward-tap
; presses harmlessly advance/decay CHAR_FREESPECIAL_STEP/TIMER (both stay
; unread since Jump_PlayMoveSlotAdvance never dispatches variant 9 for
; them, CHAR_FREESPECIAL_FCOUNT==0 makes Jump_PlayerInputGate skip the
; trigger check itself -- see below).
;
;   in:  none (DP-local self, always the player -- only ever called from
;        Jump_PlayerInputGate, which only runs for CHAR_INPUT_DRIVEN==1).
;   out: carry SET = freespecial just triggered (CHAR_SELECTED/CHAR_ATTACK_
;        VARIANT/CHAR_FRAME_INDEX/CHAR_TICK_COUNTER all set, same shape as
;        every other move-slot trigger in this file) -- caller dispatches
;        immediately. Carry CLEAR = no trigger this frame (STEP/TIMER
;        updated/decayed as needed) -- caller falls through. Clobbers A.
FREESPECIAL_TAP_WINDOW = 20
Jump_FreespecialTrigger:
.a8
    lda CHAR_FREESPECIAL_TIMER
    beq Jump_FreespecialTrigger__no_decay
    dec a
    sta CHAR_FREESPECIAL_TIMER
    bne Jump_FreespecialTrigger__no_decay
    lda #0
    sta CHAR_FREESPECIAL_STEP
Jump_FreespecialTrigger__no_decay:
.a8
    lda CHAR_FACING_LEFT
    beq Jump_FreespecialTrigger__facing_right
    lda #$02                        ; Left is forward when facing left
    bra Jump_FreespecialTrigger__have_mask
Jump_FreespecialTrigger__facing_right:
.a8
    lda #$01                        ; Right is forward when facing right
Jump_FreespecialTrigger__have_mask:
.a8
    sta.l JumpHopBaseLo              ; scratch reuse (Jump_ComputeBases only
                                       ; uses this mid-load-character, never
                                       ; concurrently with player input)
    lda.l Input_trigger+1            ; direction bits live in the HIGH byte
                                       ; (Up/Down/Left/Right -- see this
                                       ; file's own Jump_PlayerTick header
                                       ; comment for the full bit map), NOT
                                       ; the low byte -- a real bug found by
                                       ; game_g7_content_audit.py's own new
                                       ; freespecial checks (STEP never
                                       ; advanced on a real Right press).
    and.l JumpHopBaseLo
    beq Jump_FreespecialTrigger__no_forward
    lda CHAR_FREESPECIAL_STEP
    cmp #2
    beq Jump_FreespecialTrigger__no_step_advance
    inc a
    sta CHAR_FREESPECIAL_STEP
    lda #FREESPECIAL_TAP_WINDOW
    sta CHAR_FREESPECIAL_TIMER
Jump_FreespecialTrigger__no_step_advance:
.a8
    clc
    rtl
Jump_FreespecialTrigger__no_forward:
.a8
    lda CHAR_FREESPECIAL_STEP
    cmp #2
    bne Jump_FreespecialTrigger__no_trigger
    lda.l Input_trigger+1
    and #ANIM_ATTACK_BUTTON_MASK    ; Y -- same button real check_combo()'s
    beq Jump_FreespecialTrigger__no_trigger  ; default command ends on
    lda #0
    sta CHAR_FREESPECIAL_STEP
    sta CHAR_FREESPECIAL_TIMER
    lda #9                           ; freespecial's move-slot variant
    sta CHAR_ATTACK_VARIANT
    lda #2
    sta CHAR_SELECTED
    lda #$FF
    sta CHAR_FRAME_INDEX
    lda #1
    sta CHAR_TICK_COUNTER
    sec
    rtl
Jump_FreespecialTrigger__no_trigger:
.a8
    clc
    rtl

; --- Jump_PlayerInputGate -- G7 throw slice. Called via jsl from bank 0's
; hot per-frame player-input path (Anim_Play__player_input) -- the ONLY
; entry point that leaf uses now; both this gate's own grab/throw check
; AND Jump_PlayerTick (below) are reached from here so bank 0 pays for
; exactly one jsl/bcs round trip, same "keep the bank-0 call site minimal"
; shape as Game_State_Pause_CheckEntry.
;
; Real BOR.C: a grabbing player can't jump (ground-jump and grab are
; mutually exclusive player states), and common_throw is reached from the
; SAME attack buttons that would otherwise start a ground attack1/attack2
; -- so this checks CHAR_GRAB_TARGET first and only falls through to
; Jump_PlayerTick when NOT currently grabbing (there's also no roster
; member with both real jump AND real grab data to make the ordering
; matter in practice today, but the real-source rule holds regardless).
;
;   in:  none (DP-local self -- always the player, grabber-only precondit-
;        ion matches Character_HitApply__TryGrab's own restriction).
;   out: carry SET whenever this frame's action should skip straight to
;        dispatch (jump just started/still airborne, OR a throw was just
;        executed this frame); CLEAR covers grounded-no-jump, just-landed,
;        and grab-hold-no-throw-button (all fall through to normal ground
;        dispatch). Clobbers A/X.
; ============================================================================
Jump_PlayerInputGate:
.a8
    ; G7 reopened-again slice: freespecial checked FIRST, before special/
    ; grab/slide -- real player_preinput()->check_combo() runs BEFORE
    ; player_check_special() in player_think() (see Jump_FreespecialTrigger's
    ; own header). No-ops entirely (falls through, STEP/TIMER left alone)
    ; if this roster character has no real freespecial anim (CHAR_
    ; FREESPECIAL_FCOUNT==0 -- every roster member but LEO).
    lda CHAR_FREESPECIAL_FCOUNT
    beq Jump_PlayerInputGate__no_freespecial
    jsl Jump_FreespecialTrigger
    bcs Jump_PlayerInputGate__freespecial_triggered
    bra Jump_PlayerInputGate__no_freespecial
Jump_PlayerInputGate__freespecial_triggered:
.a8
    sec
    rtl
Jump_PlayerInputGate__no_freespecial:
.a8
    ; G7 special slice: real check_special()/player_check_special()
    ; (DCurrent/openbor engine/openbor.c) -- checked first, before the
    ; grab/jump gate below, since a special move releases any active grab
    ; link the same frame it triggers (dograb-release happens before
    ; toss()/anim-set in real source). L button (Input_trigger, mask $20 --
    ; the other genuinely free button per this file's own map, Jump_
    ; PlayerTick's header comment). No-ops if this roster character has no
    ; real special anim (CHAR_SPECIAL_FCOUNT==0 -- every character but
    ; LEO). LEO's own special has no `energycost` line (PAK-verified) --
    ; real check_special()/check_energy() is a no-op cost deduction when
    ; energycost.cost==0, so this project applies none here, matching
    ; source (not an oversight).
    lda CHAR_SPECIAL_FCOUNT
    beq Jump_PlayerInputGate__no_special
    lda.l Input_trigger
    and #$20                ; L button
    beq Jump_PlayerInputGate__no_special
    lda CHAR_GRAB_TARGET
    cmp #$FF
    beq Jump_PlayerInputGate__special_trigger
    jsl Character_Special_ReleaseGrab
Jump_PlayerInputGate__special_trigger:
.a8
    lda #2
    sta CHAR_SELECTED
    lda #2
    sta CHAR_ATTACK_VARIANT
    lda #$FF
    sta CHAR_FRAME_INDEX
    lda #1
    sta CHAR_TICK_COUNTER
    sec
    rtl
Jump_PlayerInputGate__no_special:
.a8
    ; G7 content-audit slice: LEO's real, separate `grab` anim (distinct
    ; from JOE's attack2-is-grab mutual lock just below -- see CHAR_
    ; GRABMOVE_FCOUNT's own comment in main.pasm). R button (Input_trigger,
    ; mask $10 -- the last genuinely free button per this file's own map).
    ; Shipped the SAME way this project's own precedent already treats
    ; "grab" for a character without the mutual-lock struct fields set up
    ; (see game_g7_attack2.py's docstring: JOE's own `grab` role was
    ; deliberately shipped as a generic one-shot attack move, not real
    ; dograb()/adjust_grabposition() mutual-lock semantics, for the exact
    ; same "no collision/link machinery built" reason) -- plays the grab
    ; anim through the ordinary CHAR_SELECTED==2 attack pathway, dealing
    ; damage via the existing hit check, no CHAR_GRAB_TARGET link. R+Y
    ; (grabattack, held R + Y edge) takes priority over plain R (grab
    ; alone) when this character also has real grabattack data (LEO) --
    ; real BOR.C's grabattack requires an active grab hold; this project's
    ; simplified non-link grab has no "holding" state to gate on, so R+Y
    ; is this slice's own stand-in trigger shape for "attack while
    ; grabbing" instead. No-ops entirely (falls through unchanged) if this
    ; roster character has neither real move (CHAR_GRABMOVE_FCOUNT==0 --
    ; every roster member but LEO).
    ;
    ; notjustfreespecial.txt item 2: now that LEO's grab lands through the
    ; same CHAR_GRAB_TARGET mutual-lock TryGrab gives JOE (see vm_native_
    ; engine.pasm's TryGrab condition widening), R and R+Y need real
    ; hold-state gating too, matching real BOR's dograb()/grabattack()
    ; precondition (grabattack requires an active hold) -- previously
    ; neither had any hold check at all, since the grab swing was just a
    ; plain one-shot attack with nothing to hold. R (plain grab-attempt)
    ; only starts a new attempt when NOT already holding; R+Y (grabattack)
    ; only fires when ALREADY holding.
    lda CHAR_GRABMOVE_FCOUNT
    beq Jump_PlayerInputGate__no_grabmove
    lda.l Input_trigger
    and #$10                        ; R
    beq Jump_PlayerInputGate__no_grabmove
    lda CHAR_GRAB_TARGET
    cmp #$FF
    bne Jump_PlayerInputGate__grabmove_already_holding
    ; not holding -- plain R starts a new grab attempt; R+Y (grabattack)
    ; is meaningless without an existing hold, falls through unchanged.
    bra Jump_PlayerInputGate__grab_trigger
Jump_PlayerInputGate__grabmove_already_holding:
.a8
    lda CHAR_GRABATTACK_FCOUNT
    beq Jump_PlayerInputGate__no_grabmove
    lda.l Input_trigger+1
    and #ANIM_ATTACK_BUTTON_MASK     ; Y
    beq Jump_PlayerInputGate__no_grabmove
    lda #8                           ; grabattack's move-slot variant
    bra Jump_PlayerInputGate__grabmove_apply
Jump_PlayerInputGate__grab_trigger:
.a8
    lda #5                           ; grab's move-slot variant
Jump_PlayerInputGate__grabmove_apply:
.a8
    sta CHAR_ATTACK_VARIANT
    lda #2
    sta CHAR_SELECTED
    lda #$FF
    sta CHAR_FRAME_INDEX
    lda #1
    sta CHAR_TICK_COUNTER
    sec
    rtl
Jump_PlayerInputGate__no_grabmove:
.a8
    ; G7 content-audit slice: real slide trigger (player_think(), DCurrent/
    ; openbor engine/openbor.c) -- A(jump button)+DOWN while grounded (real
    ; BOR also requires "not already running"; this project's B-button run
    ; state doesn't gate movement-anim selection today, so this slice
    ; doesn't add that precondition either -- LEO is the only roster member
    ; with real slide data, and nothing exercises the interaction). Checked
    ; here (same gate as jump/grab/special) so it takes priority over a
    ; plain ground-jump when Down is also held. No-ops if this roster
    ; character has no real `slide` anim (CHAR_SLIDE_FCOUNT==0 -- everyone
    ; but LEO).
    lda CHAR_SLIDE_FCOUNT
    beq Jump_PlayerInputGate__no_slide
    lda.l Input_press+1
    and #$04                         ; Down held
    beq Jump_PlayerInputGate__no_slide
    lda.l Input_trigger
    and #$80                         ; A edge
    beq Jump_PlayerInputGate__no_slide
    lda #6                           ; slide's move-slot variant
    sta CHAR_ATTACK_VARIANT
    lda #2
    sta CHAR_SELECTED
    lda #$FF
    sta CHAR_FRAME_INDEX
    lda #1
    sta CHAR_TICK_COUNTER
    sec
    rtl
Jump_PlayerInputGate__no_slide:
.a8
    lda CHAR_GRAB_TARGET
    cmp #$FF
    beq Jump_PlayerInputGate__not_grabbing
    lda.l Input_trigger+1
    and #ANIM_ATTACK_BUTTON_MASK    ; Y
    bne Jump_PlayerInputGate__do_throw
    lda.l Input_trigger
    and #ANIM_ATTACK2_BUTTON_MASK   ; X
    bne Jump_PlayerInputGate__do_throw
    clc                              ; grab-hold, no throw button pressed --
    rtl                               ; caller falls through to normal
                                       ; ground dispatch (walk-only, matches
                                       ; Character_Grab_Play's own rigid
                                       ; follow-drag)
Jump_PlayerInputGate__do_throw:
.a8
    ; X(16-bit) = resolved CharacterEntity offset for the held actor slot ID.
    rep #$30
.a16
.i16
    lda CHAR_GRAB_TARGET
    jsl Character_Grab_SlotToOffset_Long
    bcc Jump_PlayerInputGate__throw_invalid
    tax
    jsl Character_Grab_Throw
    sep #$20
.a8
    lda CHAR_ROSTER_INDEX
    cmp #12                        ; LEO is the only shipped THROW.WAV user
    bne Jump_PlayerInputGate__throw_audio_done
    ; The documented SNES throw adaptation reuses idle instead of source
    ; throw art, so no authored frame reaches Audio_FrameSoundDispatch.
    ; Emit the source throw-impact sound at the accepted production toss edge.
    jsl AudioSemantic_EmitThrow
Jump_PlayerInputGate__throw_audio_done:
.a8
    lda #0
    sta CHAR_SELECTED           ; thrower returns to idle immediately -- no
    lda #$FF                     ; unique throw-swing art in any roster pak
    sta CHAR_FRAME_INDEX         ; (same "no unique art" simplification as
    lda #1                       ; this file's own jumpattack2 reuse)
    sta CHAR_TICK_COUNTER
    sec
    rtl
Jump_PlayerInputGate__throw_invalid:
.a16
.i16
    sep #$20
.a8
    clc
    rtl
Jump_PlayerInputGate__not_grabbing:
.a8
    jsl Jump_PlayerTick   ; same-bank; its own carry convention (see its
                            ; header below) passes straight through this
                            ; rtl unchanged
    rtl

; --- Jump_PlayerTick -- called via jsl from Jump_PlayerInputGate above
; (moved off the bank-0 hot path along with the grab/throw gate itself),
; only ever reached when the player is NOT currently grabbing.
;
; Two disjoint paths, selected by whether CHAR_SELECTED is already
; CHAR_SELECTED_JUMP:
;
; GROUNDED (CHAR_SELECTED != JUMP): real BOR.C ground-jump trigger,
; `FLAG_JUMP && notinair`, edge-triggered-then-consumed. A button
; (Input_trigger, mask $80 -- the one genuinely free button per this
; project's existing map: high byte B=$80 run, Y=$40 attack1, Sel=$20,
; Start=$10, Up/Down/Left/Right=$08/$04/$02/$01; low byte X=$40 attack2,
; A=$80 free, L=$20 free, R=$10 free). No-ops if this roster character has
; no real jump anim (Player_JumpFCount==0 -- every roster member except
; LEO). On trigger: real BOR.C toss(self, jumpheight) -- velocity.y =
; jumpheight directly (JUMP_INITIAL_VEL) -- position.y gets a deliberate
; half-unit lift in real BOR.C ("Get some altitude (needed for checks)"),
; not replicated here since this project's landing check runs once per
; frame, not sub-frame, so the very next frame's ZPos += ZVel already
; clears 0 before any landing check can fire.
;
; AIRBORNE (CHAR_SELECTED == JUMP): real BOR.C check_gravity() -- position
; += velocity, velocity += gravity, every tick, land when position<=0 AND
; velocity<=0 (NOT position==0 alone -- a large downward velocity can step
; position past 0 in one frame, see CHAR_THROW_ZPOS's own comment). Also
; checks for a jump-attack trigger (real BOR.C: attack button while
; notinair plays a jump-attack instead of a ground attack) -- Y for
; jumpattack (Player_JumpAnimMode=1), X for jumpattack2 (mode=2), same
; buttons as the equivalent GROUND attack1/attack2 trigger elsewhere in
; this file, only takes effect from mode 0 (plain jump) so a swing in
; progress can't be re-triggered by itself.
;
; Returns carry SET whenever CHAR_SELECTED is JUMP after this call (jump
; just started, or still airborne after this tick) -- bank-0 caller skips
; its own ground attack2/attack1/idle/walk dispatch this frame. Carry
; CLEAR covers "grounded, no jump button" (unchanged) and "landed this
; frame" (CHAR_SELECTED already reset to idle/walk by this routine,
; deliberately falling through to normal ground dispatch the SAME frame
; for responsiveness -- a control-feel choice, not a real-source claim).
;
; Entry/exit convention: .a8 in (matches Anim_Play__player_input's own
; state at its call site), .a8-equivalent out (carry meaningful, width not
; guaranteed -- caller re-asserts as needed, matching every other jsl
; boundary in this file).
Jump_PlayerTick:
.a8
    lda CHAR_SELECTED
    cmp #CHAR_SELECTED_JUMP
    beq Jump_PlayerTick__airborne

    ; --- grounded: try starting a new jump ---
    lda.l Player_JumpFCount
    beq Jump_PlayerTick__no
    lda.l Input_trigger
    and #$80                ; A button
    beq Jump_PlayerTick__no
    ; OpenBOR dojump() emits global_sample_list.jump at this accepted
    ; ground-jump edge, before jump velocity/state initialization. This is a
    ; documented SNES adaptation, not an airborne-frame or jumpattack sound.
    lda #AUDIO_SEMANTIC_JUMP
    sta.l AudioSemantic_CurrentId
    lda.l AudioSemantic_JumpRequestCount
    inc
    sta.l AudioSemantic_JumpRequestCount
    lda.l AudioSemantic_RequestCount
    inc
    sta.l AudioSemantic_RequestCount
    phd
    pea $0000
    pld
    lda #SFX_JUMP_ID
    cmp Tad_sfxQueue_sfx
    bcs Jump_PlayerTick__jump_queue_done
    sta Tad_sfxQueue_sfx
    lda #TAD_CENTER_PAN
    sta Tad_sfxQueue_pan
Jump_PlayerTick__jump_queue_done:
    pld
    rep #$31
.a16
.i16
    lda #JUMP_INITIAL_VEL
    sta CHAR_THROW_ZVEL    ; notjustfreespecial.txt item 4: DP-local (self)
                             ; -- jump now shares the SAME per-entity Z
                             ; storage throw already uses (Character_Grab_
                             ; Throw/Character_Throw_Play, vm_native_engine.
                             ; pasm), not a separate player-only global.
                             ; Both are the identical real toss()-sourced
                             ; Q8.8 height/velocity; the old duplication was
                             ; storage only, not physics.
    lda #0
    sta CHAR_THROW_ZPOS
    sep #$20
.a8
    lda #0
    sta.l Player_JumpAnimMode
    lda #CHAR_SELECTED_JUMP
    sta CHAR_SELECTED
    lda #$FF
    sta CHAR_FRAME_INDEX
    lda #1
    sta CHAR_TICK_COUNTER
    sec
    rtl
Jump_PlayerTick__no:
.a8
    clc
    rtl

Jump_PlayerTick__airborne:
.a8
    rep #$31
.a16
.i16
    lda CHAR_THROW_ZPOS
    clc
    adc CHAR_THROW_ZVEL
    sta CHAR_THROW_ZPOS
    lda CHAR_THROW_ZVEL
    clc
    adc #JUMP_GRAVITY
    sta CHAR_THROW_ZVEL

    sep #$20
.a8
    ; --- jump-attack trigger (mode 0 only -- see header) ---
    lda.l Player_JumpAnimMode
    bne Jump_PlayerTick__land_check
    lda.l Player_JumpAttackFCount
    beq Jump_PlayerTick__try_jumpattack2
    lda.l Input_trigger+1
    and #ANIM_ATTACK_BUTTON_MASK    ; Y
    beq Jump_PlayerTick__try_jumpattack2
    lda #1
    sta.l Player_JumpAnimMode
    lda #$FF
    sta CHAR_FRAME_INDEX
    lda #1
    sta CHAR_TICK_COUNTER
    bra Jump_PlayerTick__land_check
Jump_PlayerTick__try_jumpattack2:
.a8
    lda.l Player_JumpAttack2FCount
    beq Jump_PlayerTick__land_check
    lda.l Input_trigger
    and #ANIM_ATTACK2_BUTTON_MASK   ; X
    beq Jump_PlayerTick__land_check
    lda #2
    sta.l Player_JumpAnimMode
    lda #$FF
    sta CHAR_FRAME_INDEX
    lda #1
    sta CHAR_TICK_COUNTER

Jump_PlayerTick__land_check:
.a8
    rep #$31
.a16
.i16
    lda CHAR_THROW_ZPOS
    beq Jump_PlayerTick__zpos_le0
    bmi Jump_PlayerTick__zpos_le0
    bra Jump_PlayerTick__still_airborne
Jump_PlayerTick__zpos_le0:
.a16
    lda CHAR_THROW_ZVEL
    beq Jump_PlayerTick__do_land
    bmi Jump_PlayerTick__do_land
    bra Jump_PlayerTick__still_airborne
Jump_PlayerTick__do_land:
.a16
    lda #0
    sta CHAR_THROW_ZPOS
    sta CHAR_THROW_ZVEL
    sep #$20
.a8
    lda.l Input_press+1
    and #$03                        ; Left|Right held
    beq Jump_PlayerTick__land_idle
    lda #1
    bra Jump_PlayerTick__land_got
Jump_PlayerTick__land_idle:
.a8
    lda #0
Jump_PlayerTick__land_got:
.a8
    sta CHAR_SELECTED
    lda #$FF
    sta CHAR_FRAME_INDEX
    lda #1
    sta CHAR_TICK_COUNTER
    clc
    rtl
Jump_PlayerTick__still_airborne:
.a16
    sep #$20
.a8
    sec
    rtl

; --- Anim_Play_Jump -- called via jsl from bank 0's Anim_Play__dispatch
; (Anim_Play__jump stub), once per frame while CHAR_SELECTED ==
; CHAR_SELECTED_JUMP, for the player only (nothing else ever sets that
; CHAR_SELECTED value). Same Msu1_StreamBusy-gated tick-then-advance shape
; as Anim_Play_Attack/Attack2 (main.pasm) -- duplicated per Player_
; JumpAnimMode arm rather than data-driven, matching this file's own
; established style for this shape (see Anim_Play_Attack2's header).
;
; Modes 1/2 (jumpattack/jumpattack2) are non-looping strikes: on finishing
; their real frame count, revert to mode 0 (plain jump/fall pose) rather
; than reverting CHAR_SELECTED away from JUMP -- the character is still
; airborne; only Jump_PlayerTick's own landing check ends JUMP. Mode 0
; itself holds its last frame once finished (a large CHAR_TICK_COUNTER,
; not a wrap/revert) for the same reason: still airborne, no further real
; frame data to show.
;
; Entry/exit convention: .a8 in (matches Anim_Play__dispatch's own state,
; via the Anim_Play__jump stub), width not guaranteed out (Msu1_LoadFrame's
; own exit convention is .a16/.i16 -- see main.pasm's header on it; this
; matches Anim_Play_Attack/Attack2's own `jsr Msu1_LoadFrame / rts` which
; likewise never re-asserts width afterward).
Anim_Play_Jump:
.a8
    lda.l Msu1_StreamBusy
    beq Anim_Play_Jump__not_busy
    rtl
Anim_Play_Jump__not_busy:
.a8
    lda CHAR_TICK_COUNTER
    dec a
    sta CHAR_TICK_COUNTER
    beq Anim_Play_Jump__advance
    rtl
Anim_Play_Jump__advance:
.a8
    lda.l Player_JumpAnimMode
    cmp #1
    beq Anim_Play_Jump__mode1
    cmp #2
    beq Anim_Play_Jump__mode2

    ; --- mode 0: plain jump/fall pose ---
    lda CHAR_FRAME_INDEX
    inc a
    cmp.l Player_JumpFCount
    bcc Anim_Play_Jump__mode0_ok
    lda.l Player_JumpFCount
    dec a
    sta CHAR_FRAME_INDEX
    lda #$FF
    sta CHAR_TICK_COUNTER
    rtl
Anim_Play_Jump__mode0_ok:
.a8
    sta CHAR_FRAME_INDEX
    lda.l Player_JumpDelay
    sta CHAR_TICK_COUNTER
    rep #$31
.a16
.i16
    lda.l Player_JumpBaseLo
    sta.l AnimHeaderStaging+0
    sep #$20
.a8
    lda.l Player_JumpBaseHi
    sta.l AnimHeaderStaging+2
    lda CHAR_FRAME_INDEX
    jsl Msu1_LoadFrame_Long
    rtl

    ; --- mode 1: jumpattack (Y) ---
Anim_Play_Jump__mode1:
.a8
    lda CHAR_FRAME_INDEX
    inc a
    cmp.l Player_JumpAttackFCount
    bcc Anim_Play_Jump__mode1_ok
    lda #0
    sta.l Player_JumpAnimMode
    lda #$FF
    sta CHAR_FRAME_INDEX
    lda #1
    sta CHAR_TICK_COUNTER
    rtl
Anim_Play_Jump__mode1_ok:
.a8
    sta CHAR_FRAME_INDEX
    lda.l Player_JumpAttackDelay
    sta CHAR_TICK_COUNTER
    rep #$31
.a16
.i16
    lda.l Player_JumpAttackBaseLo
    sta.l AnimHeaderStaging+0
    sep #$20
.a8
    lda.l Player_JumpAttackBaseHi
    sta.l AnimHeaderStaging+2
    lda CHAR_FRAME_INDEX
    jsl Msu1_LoadFrame_Long
    rtl

    ; --- mode 2: jumpattack2 (X) ---
Anim_Play_Jump__mode2:
.a8
    lda CHAR_FRAME_INDEX
    inc a
    cmp.l Player_JumpAttack2FCount
    bcc Anim_Play_Jump__mode2_ok
    lda #0
    sta.l Player_JumpAnimMode
    lda #$FF
    sta CHAR_FRAME_INDEX
    lda #1
    sta CHAR_TICK_COUNTER
    rtl
Anim_Play_Jump__mode2_ok:
.a8
    sta CHAR_FRAME_INDEX
    lda.l Player_JumpAttack2Delay
    sta CHAR_TICK_COUNTER
    rep #$31
.a16
.i16
    lda.l Player_JumpAttack2BaseLo
    sta.l AnimHeaderStaging+0
    sep #$20
.a8
    lda.l Player_JumpAttack2BaseHi
    sta.l AnimHeaderStaging+2
    lda CHAR_FRAME_INDEX
    jsl Msu1_LoadFrame_Long
    rtl

; --- Jump_ApplyOamYOffset: visual-only OAM Y offset while airborne. Real
; OpenBOR keeps position.z (height) separate from position.y (depth/lane),
; drawing at screen Y = position.y - position.z (engine/openbor.c). This
; project has no depth axis, so the airborne entity's own Z height is
; applied directly against the already-computed OamSetSprite_Y as that same
; visual offset -- a sourced translation, not an invented mechanic. Called
; from Character_RenderFrame (main.pasm) right after OamSetSprite_Y is set
; from CHAR_POS_Y, once per entity per Character_RenderPass (plan_game.md 7
; actor depth-sort slice) -- moved to its own bank for main.pasm ROM budget
; (see file header).
;
; notjustfreespecial.txt item 4: JUMP (player only, Jump_PlayerTick) and
; THROWN (any entity, Character_Grab_Throw/Character_Throw_Play) now share
; the SAME per-entity CHAR_THROW_ZPOS field (DP-local self) -- there is no
; longer a separate player-only global to branch on; both real states are
; just "this entity is airborne, its height lives in CHAR_THROW_ZPOS" now.
; Two different CHAR_SELECTED values still gate whether the offset applies
; (JUMP vs THROWN are genuinely distinct animation/game states -- only the
; underlying Z storage and gravity tick were ever duplicated). ---
Jump_ApplyOamYOffset:
.a8
    lda CHAR_SELECTED
    cmp #CHAR_SELECTED_JUMP
    beq Jump_ApplyOamYOffset__apply
    cmp #CHAR_SELECTED_THROWN
    bne Jump_ApplyOamYOffset__done
Jump_ApplyOamYOffset__apply:
.a8
    lda.l OamSetSprite_Y
    sec
    sbc CHAR_THROW_ZPOS+1          ; DP-local (self) -- high byte = integer
                                     ; pixel part of Q8.8, same field/
                                     ; convention for both JUMP and THROWN
    sta.l OamSetSprite_Y
Jump_ApplyOamYOffset__done:
    rtl

; ----------------------------------------------------------------------------
; notjustfreespecial.txt G5 slice: the char-select screen (core/charselect.
; pasm) never ran Core_Oop_Play/Character_RenderPass/Core_Oam_Play at all
; (confirmed by inspection: Game_State_Play only dispatches those from the
; GAME_STATE_PLAYING branch, never from Game_State_Play__charselect) -- a
; portrait sprite needs its own small, self-contained render path, called
; via jsl from charselect's own bank. Lives here (bank 8, already jump.pasm's
; own bank) rather than bank 0 -- that region is at its ROM-budget ceiling
; (confirmed empirically). Every same-bank-only (`rts`) bank-0 dependency
; (Msu1_LoadFrame, Core_Oam_SetSprite, Core_Oam_Play) is reached via its own
; small `_Long` trampoline (main.pasm), same pattern this file already uses
; for Msu1_LoadFrame_Long elsewhere. Both routines phd/tcd to the PLAYER's
; own OopDp window first (Game_State_CharSelect_ReloadPlayer precedent --
; charselect code runs outside any per-entity OOP dispatch, so CHAR_* DP-
; relative fields are only valid once explicitly switched) and pld back
; before returning; CLAUDE.md's "player is always slot 0" makes this a
; plain `lda.l OopDp` with no ,x offset, same as ReloadPlayer.
;
; CharSelect_PortraitUpdate -- called once per charselect frame from the top
; of Game_State_Play__charselect. Two jobs, deliberately NOT split across
; two call sites the way an earlier version of this slice had them (draw_
; header/ReloadPlayer calling a stream routine directly, on the SAME frame
; as Anim_LoadCharacter's own palette DMA): that stacked Msu1_LoadFrame's 6
; DMA-queue slots on top of Anim_LoadCharacter's palette DMA (1 slot) and
; whatever else was already queued that frame, in Core_Dma's fixed 8-slot
; queue -- a real, reproduced regression (game_g5_menus.py's LEO-wrap
; sequence started failing every check after it, right after Left-wrap
; selected LEO). Fixed by DEFERRING the stream: draw_header/ReloadPlayer
; below only set CharSelect_PortraitPending=1 (two cheap instructions, no
; DMA); THIS routine, called every frame, only actually streams (clearing
; the flag first) when the flag is set -- always at least one full frame
; after the reselect that set it, so it never shares a frame with Anim_
; LoadCharacter's own DMA.
;
; Streaming: the player's real CHAR_WAITING_BASE frame 0 into their
; existing OBJ tile column (Msu1_LoadFrame, same mechanism every other
; animation uses). No-op if CHAR_WAITING_FCOUNT==0 (12 of 13 roster
; characters -- only LEO has real `waiting` data).
;
; OAM: writes (or hides) the portrait's OAM entry and drains it via Core_
; Oam_Play every frame regardless (cheap -- no DMA stream, just the same
; OamSetSprite_*/Core_Oam_SetSprite/Core_Oam_Play sequence Character_
; PlayFrame's own tile/attr block uses, see that routine's comments for the
; *4/palette/hi-table derivation this mirrors). Fixed screen position (top-
; left corner, clear of the header/name/instr text rows below) since char-
; select has no camera/scroll. Hidden (OamSetSprite_Y=$F0, this project's
; established "clean slot" sentinel -- see memory: ccdma_validated_nmi_
; timing_bug) whenever the CURRENTLY selected character has no real
; waiting data -- this is what makes reselecting away from LEO correctly
; remove his portrait rather than leaving a stale frame on screen.
; Overwritten cleanly before real gameplay begins with no explicit tear-
; down needed: Oam_CursorResetDone is cleared once per frame regardless of
; Game_State (see scpu_main_loop), so the very first GAME_STATE_PLAYING
; frame's own Character_RenderPass writes entity 0's real sprite into this
; exact same OAM slot 0 before that frame's Core_Nmi_Play ever commits it --
; the portrait never survives a single visible vblank past CHARSELECT.
;
; Both jobs phd/tcd to the PLAYER's own OopDp window first (Game_State_
; CharSelect_ReloadPlayer precedent -- charselect code runs outside any
; per-entity OOP dispatch, so CHAR_* DP-relative fields are only valid once
; explicitly switched) and pld back before returning; CLAUDE.md's "player
; is always slot 0" makes this a plain `lda.l OopDp` with no ,x offset,
; same as ReloadPlayer. Lives here (bank 8, already jump.pasm's own bank)
; rather than bank 0 -- that region is at its ROM-budget ceiling (confirmed
; empirically). Every same-bank-only (`rts`) bank-0 dependency (Msu1_
; LoadFrame, Core_Oam_SetSprite, Core_Oam_Play) is reached via its own
; small `_Long` trampoline (main.pasm), same pattern this file already
; uses for Msu1_LoadFrame_Long elsewhere.
CharSelect_PortraitUpdate:
    php
    rep #$31
.a16
.i16
    lda.l OopDp
    phd
    tcd
    sep #$20
.a8
    lda.l CharSelect_PortraitPending
    beq CharSelect_PortraitUpdate__no_stream
    lda #0
    sta.l CharSelect_PortraitPending
    lda CHAR_WAITING_FCOUNT
    beq CharSelect_PortraitUpdate__no_stream
    rep #$31
.a16
.i16
    lda CHAR_WAITING_BASE_LO
    sta.l AnimHeaderStaging+0
    sep #$20
.a8
    lda CHAR_WAITING_BASE_HI
    sta.l AnimHeaderStaging+2
    lda #0
    jsl Msu1_LoadFrame_Long
CharSelect_PortraitUpdate__no_stream:
    sep #$20
.a8
    lda CHAR_WAITING_FCOUNT
    bne CharSelect_PortraitUpdate__visible
    lda #$F0
    sta.l OamSetSprite_Y
    bra CharSelect_PortraitUpdate__set
CharSelect_PortraitUpdate__visible:
    sep #$20
.a8
    lda #16
    sta.l OamSetSprite_X
    lda #24
    sta.l OamSetSprite_Y
    lda CHAR_TILE_COLUMN
    asl a
    asl a
    sta.l OamSetSprite_Tile
    lda CHAR_PALETTE_SLOT
    asl a
    ora #$30
    sta.l OamSetSprite_Attr
    lda #$02
    sta.l OamSetSprite_Hi
CharSelect_PortraitUpdate__set:
    jsl Core_Oam_SetSprite_Long
    jsl Core_Oam_Play_Long
    sep #$20
.a8
    pld
    plp
    rtl

; ============================================================================
; Character_HitApply__ApplyPickup -- G8 item/pickup slice
; (notjustfreespecial.txt). Called from main.pasm's Character_HitApply_
; VsEntity1/2/3 (bank 0, jsl) the moment a CHAR_INPUT_DRIVEN_PROP slot's HP
; reaches 0 with a nonzero CHAR_PICKUP_TYPE -- i.e. a real breakable's
; contained item (Table->Apple, Chair->Money, per BOR's own DATA\EASY\
; 1BEASY.TXT) or a standalone item spawn (DATA\EASY\1AEASY.TXT's own
; `spawn 1up`) has just been revealed/collected. Own bank, same ROM-budget
; reason as this file's other routines.
;
; Entered in .a8 (caller's own ambient width): A = the entity's
; CHAR_PICKUP_TYPE value (PICKUP_TYPE_* in main.pasm), already read by the
; caller. DP is still the PLAYER's own window (this leaf runs inside the
; player's own Character_HitApply call chain -- see Character_HitApply__
; do_vs_all_ai's header), so CHAR_HP below is the PLAYER's own HP, not the
; dying prop's -- exactly the entity a pickup effect should apply to.
; Doesn't touch X/Y. Exits in .a8 via rtl, matching every other _Long-style
; leaf in this file.
; ============================================================================
Character_HitApply__ApplyPickup:
    php
    sep #$20
.a8
    sta.l G13_PickupAmount
    cmp #PICKUP_TYPE_APPLE
    beq Character_HitApply__ApplyPickup__heal_apple
    cmp #PICKUP_TYPE_MEAT
    beq Character_HitApply__ApplyPickup__heal_meat
    cmp #PICKUP_TYPE_MONEY
    beq Character_HitApply__ApplyPickup__money
    cmp #PICKUP_TYPE_ONEUP
    beq Character_HitApply__ApplyPickup__oneup
    cmp #PICKUP_TYPE_GOLD
    bne Character_HitApply__ApplyPickup__not_gold
    jmp Character_HitApply__ApplyPickup__gold
Character_HitApply__ApplyPickup__not_gold:
    jmp Character_HitApply__ApplyPickup__done  ; unrecognized -- no-op
Character_HitApply__ApplyPickup__heal_apple:
    sep #$20
.a8
    lda #PICKUP_HEAL_APPLE
    bra Character_HitApply__ApplyPickup__heal
Character_HitApply__ApplyPickup__heal_meat:
    sep #$20
.a8
    lda #PICKUP_HEAL_MEAT
Character_HitApply__ApplyPickup__heal:
    sep #$20
.a8
    ; The dispatch entry uses G13_PickupAmount for the pickup kind.  At this
    ; leaf A is the authored heal amount; retain that amount before loading
    ; the collector's current HP.
    sta.l G13_PickupAmount
    ; PlayerEntity_Hp += A, clamped at CHAR_HP_MAX (never past the HUD
    ; bar's own max -- same clamp-not-wrap idiom Game_Score_Award uses for
    ; Game_Score). Real bug found live-tracing this: the bare DP-relative
    ; `CHAR_HP` offset assumed the current D register was still the
    ; PLAYER's own OopDp window (this leaf's own header comment claims
    ; that), but at runtime it silently read/wrote the wrong window --
    ; heals/clamps never took effect even though the byte-for-byte
    ; assembled code (sep/clc/adc $23/cmp/bcc/sta $23) was itself
    ; correct. Use the fixed absolute PlayerEntity_Hp symbol instead,
    ; matching the proven-reliable style this same routine already uses
    ; for Game_Score/Game_Lives -- doesn't depend on D at all.
    clc
    lda.l G13_PickupForP2
    bne Character_HitApply__ApplyPickup__heal_p2
    lda.l PlayerEntity_Hp
    jmp Character_HitApply__ApplyPickup__heal_add
Character_HitApply__ApplyPickup__heal_p2:
    lda.l Entity1_Hp
    jmp Character_HitApply__ApplyPickup__heal_add
Character_HitApply__ApplyPickup__heal_add:
    sep #$20
.a8
    clc
    adc.l G13_PickupAmount
    cmp #CHAR_HP_MAX + 1
    bcc Character_HitApply__ApplyPickup__heal_store
    lda #CHAR_HP_MAX
Character_HitApply__ApplyPickup__heal_store:
    sta.l G13_PickupValue
    lda.l G13_PickupForP2
    beq Character_HitApply__ApplyPickup__heal_store_p1
    lda.l G13_PickupValue
    sta.l Entity1_Hp
    jmp Character_HitApply__ApplyPickup__done
Character_HitApply__ApplyPickup__heal_store_p1:
    lda.l G13_PickupValue
    sta.l PlayerEntity_Hp
    jmp Character_HitApply__ApplyPickup__done
Character_HitApply__ApplyPickup__oneup:
.a8
    lda.l G13_PickupForP2
    beq Character_HitApply__ApplyPickup__oneup_p1
    lda.l G13_P2Lives
    inc a
    sta.l G13_P2Lives
    jmp Character_HitApply__ApplyPickup__done
Character_HitApply__ApplyPickup__oneup_p1:
    lda.l Game_Lives
    inc a
    sta.l Game_Lives
    bra Character_HitApply__ApplyPickup__done
Character_HitApply__ApplyPickup__money:
.a8
    rep #$20
.a16
    lda #PICKUP_SCORE_MONEY
    jsl G13_PlayerScore_Add
    sep #$20
.a8
    bra Character_HitApply__ApplyPickup__done
Character_HitApply__ApplyPickup__gold:
.a8
    rep #$20
.a16
    lda #PICKUP_SCORE_GOLD
    jsl G13_PlayerScore_Add
    sep #$20
.a8
Character_HitApply__ApplyPickup__done:
    plp
    rtl

; ============================================================================
; Character_HitApply__RevealOrPickup -- claude_close_g7_g8_before_g10.md
; Part 2. Moved here from main.pasm (bank 0 ran out of its own $C100-$FC00
; budget -- 3 near-identical inline copies of this dispatch, one per
; VsEntity1/2/3, no longer fit) -- same ROM-budget reasoning as every other
; own-bank module in this file.
;
; Called via jsl (from main.pasm's Character_HitApply_VsEntity1/2/3, each
; already having confirmed EntityN_Hp==0 this frame) with X (16-bit) =
; CHAR_ZP_LEN*N selecting which of the 3 AI slots just died. If that slot's
; CHAR_PICKUP_TYPE is 0, no-op (ordinary enemy kill). If nonzero: a real
; converted item sprite exists for it (EntityN_ItemRosterIdx != 0) defers to
; the broken-pending-reveal sentinel (CHAR_HP=1) instead of rewarding
; instantly -- core/spawn.pasm's Spawn_RevealPendingItems does the actual
; art reassignment once Msu1_StreamBusy allows it, and the new overlap-
; based Character_Pickup_CheckOverlap applies the real reward once the
; player touches the revealed item. No converted sprite (ItemRosterIdx==0,
; a bare breakable with no item, or an item name without real art yet)
; keeps the original instant-reward-on-kill behavior, unchanged.
;
; Entered in .a8 (caller's ambient width, matches TryGrab's own contract).
; Doesn't touch Y. Exits .a8 via rtl.
; ============================================================================
Character_HitApply__RevealOrPickup:
    php
    ; The attacker DP is still live on entry.  Establish the one-shot reward
    ; owner before the slot dispatch; ApplyPickup consumes this selector.
    rep #$31
.a16
.i16
    tdc
    cmp #$0A85
    bne Character_HitApply__RevealOrPickup__owner_p1
    sep #$20
.a8
    lda.l G13_TwoPlayerEnabled
    beq Character_HitApply__RevealOrPickup__owner_p1
    lda #1
    sta.l G13_PickupForP2
    bra Character_HitApply__RevealOrPickup__dispatch
Character_HitApply__RevealOrPickup__owner_p1:
    sep #$20
.a8
    lda #0
    sta.l G13_PickupForP2
Character_HitApply__RevealOrPickup__dispatch:
    rep #$30
.a16
.i16
    cpx #CHAR_ZP_LEN
    bne Character_HitApply__RevealOrPickup__check2
    jmp Character_HitApply__RevealOrPickup__e1
Character_HitApply__RevealOrPickup__check2:
    rep #$30
.a16
.i16
    cpx #CHAR_ZP_LEN*2
    bne Character_HitApply__RevealOrPickup__check3
    jmp Character_HitApply__RevealOrPickup__e2
Character_HitApply__RevealOrPickup__check3:
    rep #$30
.a16
.i16
    cpx #CHAR_ZP_LEN*3
    bne Character_HitApply__RevealOrPickup__check4
    jmp Character_HitApply__RevealOrPickup__e3
Character_HitApply__RevealOrPickup__check4:
    rep #$30
.a16
.i16
    cpx #CHAR_ZP_LEN*4
    bne Character_HitApply__RevealOrPickup__check5
    jmp Character_HitApply__RevealOrPickup__e4
Character_HitApply__RevealOrPickup__check5:
    rep #$30
.a16
.i16
    cpx #CHAR_ZP_LEN*5
    bne Character_HitApply__RevealOrPickup__invalid
    jmp Character_HitApply__RevealOrPickup__e5
Character_HitApply__RevealOrPickup__invalid:
    brl Character_HitApply__RevealOrPickup__done
Character_HitApply__RevealOrPickup__e1:
    sep #$20
.a8
    lda.l Entity1_PickupType
    bne Character_HitApply__RevealOrPickup__e1_has_pickup
    brl Character_HitApply__RevealOrPickup__done
Character_HitApply__RevealOrPickup__e1_has_pickup:
    sep #$20
.a8
    lda.l Entity1_ItemRosterIdx
    beq Character_HitApply__RevealOrPickup__e1_instant
    lda #1
    sta.l Entity1_Hp
    brl Character_HitApply__RevealOrPickup__done
Character_HitApply__RevealOrPickup__e1_instant:
.a8
    lda.l Entity1_PickupType   ; reload -- clobbered by the ItemRosterIdx
                                  ; check above; ApplyPickup needs A ==
                                  ; CHAR_PICKUP_TYPE, not ItemRosterIdx
    jsl Audio_EmitPickup
    jsl Character_HitApply__ApplyPickup
    lda #0
    sta.l Entity1_PickupType
    brl Character_HitApply__RevealOrPickup__done
Character_HitApply__RevealOrPickup__e2:
    sep #$20
.a8
    lda.l Entity2_PickupType
    bne Character_HitApply__RevealOrPickup__e2_has_pickup
    brl Character_HitApply__RevealOrPickup__done
Character_HitApply__RevealOrPickup__e2_has_pickup:
    sep #$20
.a8
    lda.l Entity2_ItemRosterIdx
    beq Character_HitApply__RevealOrPickup__e2_instant
    lda #1
    sta.l Entity2_Hp
    brl Character_HitApply__RevealOrPickup__done
Character_HitApply__RevealOrPickup__e2_instant:
.a8
    lda.l Entity2_PickupType   ; reload -- clobbered by the ItemRosterIdx
                                  ; check above; ApplyPickup needs A ==
                                  ; CHAR_PICKUP_TYPE, not ItemRosterIdx
    jsl Audio_EmitPickup
    jsl Character_HitApply__ApplyPickup
    lda #0
    sta.l Entity2_PickupType
    brl Character_HitApply__RevealOrPickup__done
Character_HitApply__RevealOrPickup__e3:
    sep #$20
.a8
    lda.l Entity3_PickupType
    bne Character_HitApply__RevealOrPickup__e3_has_pickup
    brl Character_HitApply__RevealOrPickup__done
Character_HitApply__RevealOrPickup__e3_has_pickup:
    sep #$20
.a8
    lda.l Entity3_ItemRosterIdx
    beq Character_HitApply__RevealOrPickup__e3_instant
    lda #1
    sta.l Entity3_Hp
    brl Character_HitApply__RevealOrPickup__done
Character_HitApply__RevealOrPickup__e3_instant:
.a8
    lda.l Entity3_PickupType   ; reload -- clobbered by the ItemRosterIdx
                                  ; check above; ApplyPickup needs A ==
                                  ; CHAR_PICKUP_TYPE, not ItemRosterIdx
    jsl Audio_EmitPickup
    jsl Character_HitApply__ApplyPickup
    lda #0
    sta.l Entity3_PickupType
    brl Character_HitApply__RevealOrPickup__done
Character_HitApply__RevealOrPickup__e4:
    sep #$20
.a8
    lda.l Entity4_PickupType
    bne Character_HitApply__RevealOrPickup__e4_has_pickup
    brl Character_HitApply__RevealOrPickup__done
Character_HitApply__RevealOrPickup__e4_has_pickup:
    sep #$20
.a8
    lda.l Entity4_ItemRosterIdx
    beq Character_HitApply__RevealOrPickup__e4_instant
    lda #1
    sta.l Entity4_Hp
    brl Character_HitApply__RevealOrPickup__done
Character_HitApply__RevealOrPickup__e4_instant:
.a8
    lda.l Entity4_PickupType
    jsl Audio_EmitPickup
    jsl Character_HitApply__ApplyPickup
    lda #0
    sta.l Entity4_PickupType
    brl Character_HitApply__RevealOrPickup__done
Character_HitApply__RevealOrPickup__e5:
    sep #$20
.a8
    lda.l Entity5_PickupType
    bne Character_HitApply__RevealOrPickup__e5_has_pickup
    brl Character_HitApply__RevealOrPickup__done
Character_HitApply__RevealOrPickup__e5_has_pickup:
    sep #$20
.a8
    lda.l Entity5_ItemRosterIdx
    beq Character_HitApply__RevealOrPickup__e5_instant
    lda #1
    sta.l Entity5_Hp
    brl Character_HitApply__RevealOrPickup__done
Character_HitApply__RevealOrPickup__e5_instant:
.a8
    lda.l Entity5_PickupType
    jsl Audio_EmitPickup
    jsl Character_HitApply__ApplyPickup
    lda #0
    sta.l Entity5_PickupType
Character_HitApply__RevealOrPickup__done:
    sep #$20
.a8
    lda #0
    sta.l G13_PickupForP2
    plp
    rtl

; ============================================================================
; Character_Pickup_CheckOverlap -- claude_close_g7_g8_before_g10.md Part 2.
; Called once per frame (core/game_state.pasm's Game_State_Play, right
; after Spawn_RevealPendingItems) via jsl/rtl. Separates DESTRUCTION from
; COLLECTION: a revealed item (CHAR_INPUT_DRIVEN_PROP, CHAR_PICKUP_TYPE!=0,
; EntityN_ItemRosterIdx==0 -- the object phase is over, or this was always a
; standalone item with no object phase at all) sits in the world showing
; its own real converted item sprite until the PLAYER's own AABB overlaps
; it (same per-axis abs-difference test Character_HitApply_VsEntity1/2/3
; already use for combat, just unconditional -- not gated on CHAR_SELECTED
; ==2/attacking, and checked here instead of there since this is a passive
; touch, not a landed hit). On overlap: applies the real reward exactly
; once (Character_HitApply__ApplyPickup, same leaf combat pickups already
; use), clears CHAR_PICKUP_TYPE, and sets CHAR_HP=0 (the ordinary soft-kill
; sentinel -- Anim_Play's own dead-check hides the sprite next frame, same
; as any other prop's removal).
;
; A CHAR_HP==1 "broken, pending reveal" sentinel (ItemRosterIdx still
; nonzero) is deliberately NOT touched here -- it isn't collectible yet,
; only visibly broken; Spawn_RevealPendingItems owns that transition.
;
; No caller-convention assumed on entry (jsl/rtl). Clobbers A/X. Exits
; .a16/.i16 (matches its caller's own jsl/rtl convention, called right after
; Spawn_RevealPendingItems which has the same contract).
; ============================================================================
; Three independent leaf routines, not one parameterized by a runtime-
; computed target address -- same reasoning as Character_HitApply_
; VsEntity1/2/3's own header (indexed-by-something-other-than-X long
; addressing has its own confirmed Poppy miscompile risk; a shared branch
; target risks exceeding +-127 bytes across 3 inlined copies). Each is a
; near-literal copy of Character_HitApply_VsEntity1/2/3's own dx/dy AABB
; test against its own EntityN_PosX/Y, gated first on the real pickup-
; collectible-state check (InputDriven/PickupType/ItemRosterIdx/Hp).
Character_Pickup_CheckOverlap:
    php
    jsr Character_Pickup_CheckOverlap__vs1
    jsr Character_Pickup_CheckOverlap__vs2
    jsr Character_Pickup_CheckOverlap__vs3
    jsr Character_Pickup_CheckOverlap__vs4
    jsr Character_Pickup_CheckOverlap__vs5
    plp
    rep #$31
.a16
.i16
    rtl

Character_Pickup_CheckOverlap__vs1:
    sep #$20
.a8
    lda.l Entity1_InputDriven
    cmp #CHAR_INPUT_DRIVEN_PROP
    bne Character_Pickup_CheckOverlap__vs1_no
    lda.l Entity1_PickupType
    beq Character_Pickup_CheckOverlap__vs1_no
    lda.l Entity1_ItemRosterIdx
    bne Character_Pickup_CheckOverlap__vs1_no
    lda.l Entity1_Hp
    beq Character_Pickup_CheckOverlap__vs1_no
    rep #$20
.a16
    lda.l Entity1_PosX
    cmp.l G13_PickupTargetX
    bcs Character_Pickup_CheckOverlap__vs1_dx_otherge
    sec
    lda.l G13_PickupTargetX
    sbc.l Entity1_PosX
    bra Character_Pickup_CheckOverlap__vs1_dx_have
Character_Pickup_CheckOverlap__vs1_dx_otherge:
    rep #$20
.a16
    sec
    sbc.l G13_PickupTargetX
Character_Pickup_CheckOverlap__vs1_dx_have:
.a16
    cmp #CHAR_HITBOX_W
    bcc Character_Pickup_CheckOverlap__vs1_dx_ok
    sep #$20
.a8
    rts                         ; no overlap on X
Character_Pickup_CheckOverlap__vs1_dx_ok:
    sep #$20
.a8
    lda.l Entity1_PosY
    cmp.l G13_PickupTargetY
    bcs Character_Pickup_CheckOverlap__vs1_dy_otherge
    lda.l G13_PickupTargetY
    sec
    sbc.l Entity1_PosY
    bra Character_Pickup_CheckOverlap__vs1_dy_have
Character_Pickup_CheckOverlap__vs1_dy_otherge:
    sec
    sbc.l G13_PickupTargetY
Character_Pickup_CheckOverlap__vs1_dy_have:
.a8
    cmp #CHAR_HITBOX_H
    bcc Character_Pickup_CheckOverlap__vs1_dy_ok
    rts                         ; no overlap on Y
Character_Pickup_CheckOverlap__vs1_dy_ok:
.a8
    jsr Character_Pickup_CheckOverlap__TriggerGet
    lda.l Entity1_PickupType
    pha
    jsl Audio_EmitPickup
    pla
    jsl Character_HitApply__ApplyPickup
    lda #0
    sta.l Entity1_PickupType
    sta.l Entity1_Hp
    rts
Character_Pickup_CheckOverlap__vs1_no:
    rts

Character_Pickup_CheckOverlap__vs2:
    sep #$20
.a8
    lda.l Entity2_InputDriven
    cmp #CHAR_INPUT_DRIVEN_PROP
    bne Character_Pickup_CheckOverlap__vs2_no
    lda.l Entity2_PickupType
    beq Character_Pickup_CheckOverlap__vs2_no
    lda.l Entity2_ItemRosterIdx
    bne Character_Pickup_CheckOverlap__vs2_no
    lda.l Entity2_Hp
    beq Character_Pickup_CheckOverlap__vs2_no
    rep #$20
.a16
    lda.l Entity2_PosX
    cmp.l G13_PickupTargetX
    bcs Character_Pickup_CheckOverlap__vs2_dx_otherge
    sec
    lda.l G13_PickupTargetX
    sbc.l Entity2_PosX
    bra Character_Pickup_CheckOverlap__vs2_dx_have
Character_Pickup_CheckOverlap__vs2_dx_otherge:
    rep #$20
.a16
    sec
    sbc.l G13_PickupTargetX
Character_Pickup_CheckOverlap__vs2_dx_have:
.a16
    cmp #CHAR_HITBOX_W
    bcc Character_Pickup_CheckOverlap__vs2_dx_ok
    sep #$20
.a8
    rts
Character_Pickup_CheckOverlap__vs2_dx_ok:
    sep #$20
.a8
    lda.l Entity2_PosY
    cmp.l G13_PickupTargetY
    bcs Character_Pickup_CheckOverlap__vs2_dy_otherge
    lda.l G13_PickupTargetY
    sec
    sbc.l Entity2_PosY
    bra Character_Pickup_CheckOverlap__vs2_dy_have
Character_Pickup_CheckOverlap__vs2_dy_otherge:
    sec
    sbc.l G13_PickupTargetY
Character_Pickup_CheckOverlap__vs2_dy_have:
.a8
    cmp #CHAR_HITBOX_H
    bcc Character_Pickup_CheckOverlap__vs2_dy_ok
    rts
Character_Pickup_CheckOverlap__vs2_dy_ok:
.a8
    jsr Character_Pickup_CheckOverlap__TriggerGet
    lda.l Entity2_PickupType
    pha
    jsl Audio_EmitPickup
    pla
    jsl Character_HitApply__ApplyPickup
    lda #0
    sta.l Entity2_PickupType
    sta.l Entity2_Hp
    rts
Character_Pickup_CheckOverlap__vs2_no:
    rts

Character_Pickup_CheckOverlap__vs3:
    sep #$20
.a8
    lda.l Entity3_InputDriven
    cmp #CHAR_INPUT_DRIVEN_PROP
    bne Character_Pickup_CheckOverlap__vs3_no
    lda.l Entity3_PickupType
    beq Character_Pickup_CheckOverlap__vs3_no
    lda.l Entity3_ItemRosterIdx
    bne Character_Pickup_CheckOverlap__vs3_no
    lda.l Entity3_Hp
    beq Character_Pickup_CheckOverlap__vs3_no
    rep #$20
.a16
    lda.l Entity3_PosX
    cmp.l G13_PickupTargetX
    bcs Character_Pickup_CheckOverlap__vs3_dx_otherge
    sec
    lda.l G13_PickupTargetX
    sbc.l Entity3_PosX
    bra Character_Pickup_CheckOverlap__vs3_dx_have
Character_Pickup_CheckOverlap__vs3_dx_otherge:
    rep #$20
.a16
    sec
    sbc.l G13_PickupTargetX
Character_Pickup_CheckOverlap__vs3_dx_have:
.a16
    cmp #CHAR_HITBOX_W
    bcc Character_Pickup_CheckOverlap__vs3_dx_ok
    sep #$20
.a8
    rts
Character_Pickup_CheckOverlap__vs3_dx_ok:
    sep #$20
.a8
    lda.l Entity3_PosY
    cmp.l G13_PickupTargetY
    bcs Character_Pickup_CheckOverlap__vs3_dy_otherge
    lda.l G13_PickupTargetY
    sec
    sbc.l Entity3_PosY
    bra Character_Pickup_CheckOverlap__vs3_dy_have
Character_Pickup_CheckOverlap__vs3_dy_otherge:
    sec
    sbc.l G13_PickupTargetY
Character_Pickup_CheckOverlap__vs3_dy_have:
.a8
    cmp #CHAR_HITBOX_H
    bcc Character_Pickup_CheckOverlap__vs3_dy_ok
    rts
Character_Pickup_CheckOverlap__vs3_dy_ok:
.a8
    jsr Character_Pickup_CheckOverlap__TriggerGet
    lda.l Entity3_PickupType
    pha
    jsl Audio_EmitPickup
    pla
    jsl Character_HitApply__ApplyPickup
    lda #0
    sta.l Entity3_PickupType
    sta.l Entity3_Hp
    rts
Character_Pickup_CheckOverlap__vs3_no:
    rts
Character_Pickup_CheckOverlap__vs4:
    sep #$20
.a8
    lda.l Entity4_InputDriven
    cmp #CHAR_INPUT_DRIVEN_PROP
    bne Character_Pickup_CheckOverlap__vs4_no
    lda.l Entity4_PickupType
    beq Character_Pickup_CheckOverlap__vs4_no
    lda.l Entity4_ItemRosterIdx
    bne Character_Pickup_CheckOverlap__vs4_no
    lda.l Entity4_Hp
    beq Character_Pickup_CheckOverlap__vs4_no
    rep #$20
.a16
    lda.l Entity4_PosX
    cmp.l G13_PickupTargetX
    bcs Character_Pickup_CheckOverlap__vs4_dx_otherge
    sec
    lda.l G13_PickupTargetX
    sbc.l Entity4_PosX
    bra Character_Pickup_CheckOverlap__vs4_dx_have
Character_Pickup_CheckOverlap__vs4_dx_otherge:
    rep #$20
.a16
    sec
    sbc.l G13_PickupTargetX
Character_Pickup_CheckOverlap__vs4_dx_have:
.a16
    cmp #CHAR_HITBOX_W
    bcc Character_Pickup_CheckOverlap__vs4_dx_ok
    sep #$20
.a8
    rts
Character_Pickup_CheckOverlap__vs4_dx_ok:
    sep #$20
.a8
    lda.l Entity4_PosY
    cmp.l G13_PickupTargetY
    bcs Character_Pickup_CheckOverlap__vs4_dy_otherge
    lda.l G13_PickupTargetY
    sec
    sbc.l Entity4_PosY
    bra Character_Pickup_CheckOverlap__vs4_dy_have
Character_Pickup_CheckOverlap__vs4_dy_otherge:
    sec
    sbc.l G13_PickupTargetY
Character_Pickup_CheckOverlap__vs4_dy_have:
.a8
    cmp #CHAR_HITBOX_H
    bcc Character_Pickup_CheckOverlap__vs4_dy_ok
    rts
Character_Pickup_CheckOverlap__vs4_dy_ok:
.a8
    jsr Character_Pickup_CheckOverlap__TriggerGet
    lda.l Entity4_PickupType
    pha
    jsl Audio_EmitPickup
    pla
    jsl Character_HitApply__ApplyPickup
    lda #0
    sta.l Entity4_PickupType
    sta.l Entity4_Hp
    rts
Character_Pickup_CheckOverlap__vs4_no:
    rts
Character_Pickup_CheckOverlap__vs5:
    sep #$20
.a8
    lda.l Entity5_InputDriven
    cmp #CHAR_INPUT_DRIVEN_PROP
    bne Character_Pickup_CheckOverlap__vs5_no
    lda.l Entity5_PickupType
    beq Character_Pickup_CheckOverlap__vs5_no
    lda.l Entity5_ItemRosterIdx
    bne Character_Pickup_CheckOverlap__vs5_no
    lda.l Entity5_Hp
    beq Character_Pickup_CheckOverlap__vs5_no
    rep #$20
.a16
    lda.l Entity5_PosX
    cmp.l G13_PickupTargetX
    bcs Character_Pickup_CheckOverlap__vs5_dx_otherge
    sec
    lda.l G13_PickupTargetX
    sbc.l Entity5_PosX
    bra Character_Pickup_CheckOverlap__vs5_dx_have
Character_Pickup_CheckOverlap__vs5_dx_otherge:
    rep #$20
.a16
    sec
    sbc.l G13_PickupTargetX
Character_Pickup_CheckOverlap__vs5_dx_have:
.a16
    cmp #CHAR_HITBOX_W
    bcc Character_Pickup_CheckOverlap__vs5_dx_ok
    sep #$20
.a8
    rts
Character_Pickup_CheckOverlap__vs5_dx_ok:
    sep #$20
.a8
    lda.l Entity5_PosY
    cmp.l G13_PickupTargetY
    bcs Character_Pickup_CheckOverlap__vs5_dy_otherge
    lda.l G13_PickupTargetY
    sec
    sbc.l Entity5_PosY
    bra Character_Pickup_CheckOverlap__vs5_dy_have
Character_Pickup_CheckOverlap__vs5_dy_otherge:
    sec
    sbc.l G13_PickupTargetY
Character_Pickup_CheckOverlap__vs5_dy_have:
.a8
    cmp #CHAR_HITBOX_H
    bcc Character_Pickup_CheckOverlap__vs5_dy_ok
    rts
Character_Pickup_CheckOverlap__vs5_dy_ok:
.a8
    jsr Character_Pickup_CheckOverlap__TriggerGet
    lda.l Entity5_PickupType
    pha
    jsl Audio_EmitPickup
    pla
    jsl Character_HitApply__ApplyPickup
    lda #0
    sta.l Entity5_PickupType
    sta.l Entity5_Hp
    rts
Character_Pickup_CheckOverlap__vs5_no:
    rts

; --- Character_Pickup_CheckOverlap__TriggerGet -- claude_close_g7_g8_
; before_g10.md Part 2. Real ANI_GET (DCurrent/openbor engine/openbor.c's
; common_pickupitem/player-think ANI_GET block): where the player's own
; loaded character has real converted `get` content (CHAR_GET_FCOUNT!=0 --
; only LEO today), enter the real pickup/get pose instead of the silent
; instant-collect every other roster member still uses (real "source-
; defined fallback" for a character with no get anim -- CLAUDE_close_g7_g8
; _before_g10.md Part 2's own wording: "do not fabricate a required
; animation"). The reward itself is applied by the caller immediately
; after this returns, unconditionally, matching real didfind_item()'s own
; timing (the animation is cosmetic -- it never gates the reward).
;
; Deliberately only triggers while the player is idle (CHAR_SELECTED==0)
; -- real player_think()'s own ANI_GET check sits behind a long chain of
; higher-priority action checks (turning, ducking, attacking, etc.) this
; project doesn't fully reproduce; not overwriting an in-progress action
; (attack/jump/fall/etc.) is a safe, real-behavior-preserving
; simplification within that scope, not a fabricated mechanic -- it never
; changes WHETHER or HOW MUCH reward is applied, only whether the cosmetic
; pose is visible this particular frame.
;
;   in:  none. Clobbers A.
; ============================================================================
Character_Pickup_CheckOverlap__TriggerGet:
.a8
    lda.l G13_PickupForP2
    beq Character_Pickup_CheckOverlap__TriggerGet__p1
    lda.l Entity1_GetFcount
    beq Character_Pickup_CheckOverlap__TriggerGet__no
    lda.l Entity1_Selected
    bne Character_Pickup_CheckOverlap__TriggerGet__no
    lda #GET_MOVE_VARIANT
    sta.l Entity1_AttackVariant
    lda #2
    sta.l Entity1_Selected
    lda #$FF
    sta.l Entity1_FrameIndex
    lda #1
    sta.l Entity1_TickCounter
    rts
Character_Pickup_CheckOverlap__TriggerGet__p1:
    sep #$20
.a8
    lda.l PlayerEntity_GetFcount
    beq Character_Pickup_CheckOverlap__TriggerGet__no
    lda.l PlayerEntity_Selected
    bne Character_Pickup_CheckOverlap__TriggerGet__no
    lda #GET_MOVE_VARIANT
    sta.l PlayerEntity_AttackVariant
    lda #2
    sta.l PlayerEntity_Selected
    lda #$FF
    sta.l PlayerEntity_FrameIndex
    lda #1
    sta.l PlayerEntity_TickCounter
Character_Pickup_CheckOverlap__TriggerGet__no:
    rts

; G12 service observer wrappers replace same-size bank-0 accesses. The busy
; read wrapper returns the exact A/flags seen by the existing BEQ; the store
; wrapper performs the original store after recording an accepted upload.
G12_AnimTrace_BusyRead:
    ; This wrapper replaces an actual LDA.l.  Perform that load here so the
    ; caller receives the same A and flags; do not record the incoming A.
    lda.l Msu1_StreamBusy
    php
    ; Preserve the complete accumulator, including the hidden high byte when
    ; the displaced instruction was an A8 load.  Record changes M/I and uses
    ; TDC, so an 8-bit PHA/PLA pair is not sufficient here.
    rep #$20
.a16
    pha
    phx
    phy
    sep #$20
.a8
    sta.l G12_AnimTrace_SavedA
    lda #2                         ; event 2 = actual busy decision
    jsr G12_AnimTrace_Record
    ply
    plx
    rep #$20
.a16
    pla
    plp
    rtl

G12_AnimTrace_BusyStore:
    php
    rep #$20
.a16
    pha
    phx
    phy
    sep #$20
.a8
    sta.l G12_AnimTrace_SavedA
    lda #3
    jsr G12_AnimTrace_Record
    ply
    plx
    rep #$20
.a16
    pla
    plp
    sta.l Msu1_StreamBusy
    rtl

G12_AnimTrace_LoadedRead:
    ; Same-size replacement for Anim_Play's LDA.l CharSelect_Loaded.  The
    ; returned A/flags are the original load result; event 4 records whether
    ; this entity reached the global character-loaded dispatch gate.
    lda.l CharSelect_Loaded
    php
    rep #$20
.a16
    pha
    phx
    phy
    sep #$20
.a8
    sta.l G12_AnimTrace_SavedA
    lda #4
    jsr G12_AnimTrace_Record
    ply
    plx
    rep #$20
.a16
    pla
    plp
    rtl

G12_AnimTrace_InputRead:
    ; Same-size replacement for the attack2 gate's LDA.l Input_trigger.
    ; Return the exact A/flags produced by the displaced load after recording
    ; the event-time value consumed by the following AND #$40.
    lda.l Input_trigger
    php
    rep #$20
.a16
    pha
    phx
    phy
    sep #$20
.a8
    sta.l G12_AnimTrace_SavedA
    sta.l G12_AnimTrace_LastInput
    lda #5                         ; event 5 = attack2 input read
    jsr G12_AnimTrace_Record
    ply
    plx
    rep #$20
.a16
    pla
    plp
    rtl

G12_AnimTrace_Record:
    ; A8 = event kind, SavedA = value at the replaced access.
    sep #$20
.a8
    sta.l G12_AnimTrace_Event
    sta.l G12_AnimTrace_LastEvent
    lda.l G12_AnimTrace_Index
    rep #$20
.a16
    and #$07
    asl a
    asl a
    asl a
    tax
    rep #$31
.a16
.i16
    tdc
    sta.l G12_AnimTrace_Ring,x
    sta.l G12_AnimTrace_LastDp
    sep #$20
.a8
    lda.l G12_AnimTrace_Event
    sta.l G12_AnimTrace_Ring+2,x
    lda.l G12_AnimTrace_SavedA
    sta.l G12_AnimTrace_Ring+3,x
    sta.l G12_AnimTrace_LastValue
    lda CHAR_SELECTED
    sta.l G12_AnimTrace_Ring+4,x
    lda CHAR_FRAME_INDEX
    sta.l G12_AnimTrace_Ring+5,x
    lda CHAR_TICK_COUNTER
    sta.l G12_AnimTrace_Ring+6,x
    lda CHAR_GRAB_TARGET
    sta.l G12_AnimTrace_Ring+7,x
    lda.l G12_AnimTrace_Index
    inc a
    sta.l G12_AnimTrace_Index
    lda.l G12_AnimTrace_Index
    cmp #8
    bcc G12_AnimTrace_Record__done
    lda #0
    sta.l G12_AnimTrace_Index
    lda.l G12_AnimTrace_Overflow
    inc a
    sta.l G12_AnimTrace_Overflow
G12_AnimTrace_Record__done:
    rts
