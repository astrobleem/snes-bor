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
;     position.y (pure jump height, this project's Player_JumpZPos). This
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
    ; X(16-bit) = CHAR_GRAB_TARGET, zero-extended -- the real byte offset
    ; of whichever AI slot (1/2/3) this player is currently holding.
    rep #$30
.a16
.i16
    lda CHAR_GRAB_TARGET
    and #$00FF
    tax
    jsl Character_Grab_Throw
    sep #$20
.a8
    lda #0
    sta CHAR_SELECTED           ; thrower returns to idle immediately -- no
    lda #$FF                     ; unique throw-swing art in any roster pak
    sta CHAR_FRAME_INDEX         ; (same "no unique art" simplification as
    lda #1                       ; this file's own jumpattack2 reuse)
    sta CHAR_TICK_COUNTER
    sec
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
; position past 0 in one frame, see Player_JumpZPos's own comment). Also
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
    rep #$31
.a16
.i16
    lda #JUMP_INITIAL_VEL
    sta.l Player_JumpZVel
    lda #0
    sta.l Player_JumpZPos
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
    lda.l Player_JumpZPos
    clc
    adc.l Player_JumpZVel
    sta.l Player_JumpZPos
    lda.l Player_JumpZVel
    clc
    adc #JUMP_GRAVITY
    sta.l Player_JumpZVel

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
    lda.l Player_JumpZPos
    beq Jump_PlayerTick__zpos_le0
    bmi Jump_PlayerTick__zpos_le0
    bra Jump_PlayerTick__still_airborne
Jump_PlayerTick__zpos_le0:
.a16
    lda.l Player_JumpZVel
    beq Jump_PlayerTick__do_land
    bmi Jump_PlayerTick__do_land
    bra Jump_PlayerTick__still_airborne
Jump_PlayerTick__do_land:
.a16
    lda #0
    sta.l Player_JumpZPos
    sta.l Player_JumpZVel
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
; Two disjoint airborne cases, checked in DP-local (self) fields only:
;   - JUMP: player only (Jump_PlayerTick, this file), height in the
;     player-only global Player_JumpZPos cell.
;   - THROWN (G7 throw slice): any entity (always an AI slot in practice --
;     the grabber is always the player, see CHAR_GRAB_TARGET's own
;     comment), height in this entity's own per-instance CHAR_THROW_ZPOS
;     field (Character_Grab_Throw/Character_Throw_Play, vm_native_engine.
;     pasm) -- IDENTICAL toss()-sourced Q8.8 physics to jump's own, just
;     per-entity storage instead of a shared global cell. ---
Jump_ApplyOamYOffset:
.a8
    lda CHAR_INPUT_DRIVEN
    cmp #1
    bne Jump_ApplyOamYOffset__check_thrown
    lda CHAR_SELECTED
    cmp #CHAR_SELECTED_JUMP
    bne Jump_ApplyOamYOffset__check_thrown
    lda.l OamSetSprite_Y
    sec
    sbc.l Player_JumpZPos+1        ; high byte = integer pixel part of Q8.8
    sta.l OamSetSprite_Y
    rtl
Jump_ApplyOamYOffset__check_thrown:
.a8
    lda CHAR_SELECTED
    cmp #CHAR_SELECTED_THROWN
    bne Jump_ApplyOamYOffset__done
    lda.l OamSetSprite_Y
    sec
    sbc CHAR_THROW_ZPOS+1          ; DP-local (self) -- high byte, same
                                     ; Q8.8-integer-part convention as jump
    sta.l OamSetSprite_Y
Jump_ApplyOamYOffset__done:
    rtl
