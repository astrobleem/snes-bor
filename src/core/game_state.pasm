; ============================================================================
; core/game_state.pasm -- Phase G2 (plan_game.md 2): the game state machine.
;
; Today scpu_main_loop falls straight into gameplay forever; there is no
; concept of "not in gameplay." Game_State_Play is the single entry point
; scpu_main_loop now calls (replacing the ~11-line straight-line jsr list
; that used to live there directly -- see the call site's own comment for
; why that move is budget-positive, not just cosmetic).
;
; Boot state is deliberately GAME_STATE_PLAYING (=0): every existing gate
; (phase5/6/8/9/11_damage/12_roster, game_g1_text, the non-routine phase9_*/
; phase10_frontpanel scripts) drives the ROM from boot and asserts gameplay
; is already running. Making PLAYING the zero/boot-default value means the
; existing zero-init-before-Core_Nmi_Init step (main.pasm's scpu_boot, right
; next to Oam_UploadFlag/HighWaterSlot -- memory boot_nmi_race_before_oam_
; init) doubles as the state choice, with no separate write needed. TITLE
; exists and is reachable (a debugger/gate can force-write Game_State), but
; does not become the real boot state until G5 gives it actual content.
;
; Scope for this phase (plan_game.md 2): define all 7 states, implement
; TITLE/PLAYING/PAUSED for real, and make every other state an explicit
; no-op Play routine (never a state that spins without Core_Nmi_WaitFrame --
; that still happens unconditionally in scpu_main_loop, once per iteration,
; regardless of Game_State). CHARSELECT is deliberately NOT wired to the
; existing CharSelect_Index roster logic here -- CLAUDE.md says that
; hard-coded roster is to be phased out as VM gates land, so this phase
; does not invest in it.
; ============================================================================

GAME_STATE_PLAYING    = 0   ; current behavior -- also the boot default, see above
GAME_STATE_TITLE      = 1   ; title screen, waiting for Start
GAME_STATE_CHARSELECT = 2   ; character select (stub only, see header)
GAME_STATE_PAUSED     = 3   ; frozen, pause menu drawn (stub content, real freeze)
GAME_STATE_GAMEOVER   = 4   ; game over, continue countdown (Phase G3 -- real, see below)
GAME_STATE_STAGECLEAR = 5   ; stage cleared, transition (Phase G4 -- real, see below)
GAME_STATE_ENDING     = 6   ; credits (stub)

Game_State     = $7E2750   ; .dw -- current state, see GAME_STATE_* above
Game_StatePrev = $7E2752   ; .dw -- last frame's state, used only to detect
                           ; the transition edge into a non-playing state
                           ; (one-shot OAM clear+upload, then Core_Oam_Play
                           ; stops being called for the rest of that state)

; ============================================================================
; Phase G5 (plan_game.md 5): title screen.
;
; Per the advisor consult for this phase: GAME_STATE_PLAYING stays the boot
; default (=0) -- every existing gate (phase5/6/8/9/11_damage/12_roster,
; game_g1-g4, plus the two non-routine wall-clock scripts) drives the ROM
; from boot expecting gameplay already running, and flipping the boot state
; to TITLE would mean touching every one of them. TITLE was already
; organically reachable (Game_State_Play__gameover_timeout, Phase G3) with
; no drawn content; this phase gives it content without changing when it's
; entered.
;
; Core_Text_DrawString shares ONE WRAM staging buffer (TextStaging,
; core/text.pasm) and its DMA is QUEUED, not synchronous -- two DrawString
; calls in the same frame silently corrupt each other (the confirmed
; "1024-BOR" bug, see text.pasm's own header). A title screen needs two rows
; drawn (and later, two cleared), so this cannot be a single "draw everything
; on the transition edge" routine -- it has to be a one-DrawString-per-frame
; drip driven by Title_Step, exactly like Core_Text_G1Demo's own one-shot
; pattern but with more than one step.
;
; Every string drawn here fills the FULL 32-column row (padded with trailing
; spaces), not just the visible text -- see Text_Str_TitleMain/TitlePress/
; TitleBlank in main.pasm's Text_StringPool. This sidesteps a real hazard:
; TextStaging is reused across calls with no clearing of untouched columns,
; so a short string leaves whatever a PREVIOUS DrawString call (to a
; different row/column) left in the columns it didn't touch. A full-row
; string always overwrites all 64 bytes of the shared buffer, so there is
; never a stale-column gap regardless of call history.
;
; Rows 10/12: clear of the HUD (rows 0-3) and the frontpanel streaming cache
; (rows 21-27, when a stage with one is loaded) -- see text.pasm's own
; tilemap-ownership comment. Column 0 always (full-row strings need no
; centering logic).
; ============================================================================

TITLE_ROW_MAIN  = 10
TITLE_ROW_PRESS = 12

TITLE_STEP_DRAW_MAIN  = 0   ; draw the title row this frame, then advance
TITLE_STEP_DRAW_PRESS = 1   ; draw "PRESS START" this frame, then advance
TITLE_STEP_WAIT       = 2   ; idle, polling Start, until pressed
TITLE_STEP_CLEAR_MAIN = 3   ; blank the title row this frame, then advance
TITLE_STEP_CLEAR_PRESS = 4  ; blank "PRESS START" this frame, then advance
                             ; -- anything >= 5 falls through to entering
                             ; PLAYING (see Game_State_Play__title below)

Title_Step = $7E2760   ; .db -- see TITLE_STEP_* above; zeroed at boot
                        ; (main.pasm, alongside Game_Lives) and reset back
                        ; to TITLE_STEP_DRAW_MAIN right before this phase's
                        ; code sets Game_State back to PLAYING, so TITLE is
                        ; always ready to redraw from scratch the next time
                        ; it's entered (e.g. a later GAME OVER timeout)

; ============================================================================
; Phase G3 (plan_game.md 3): player death, lives, continues, game over.
;
; The player (entity 0, CHAR_INPUT_DRIVEN==1) was previously exempt from the
; damage system entirely -- Character_HitApply_VsPlayer clamps CHAR_HP at 0
; and nothing reacts. This phase adds a reaction, but deliberately NOT by
; reusing the AI soft-kill machinery (the CHAR_INPUT_DRIVEN==2-gated dead
; checks scattered through Anim_Play/Character_PlayFrame/Character_HitApply):
; that path freezes an entity forever, which is correct for a corpse but
; wrong for the player, who must respawn or reach GAME OVER instead. Player
; death is handled ENTIRELY here, once per frame, at the top of the PLAYING
; dispatch -- see Game_State_Play__playing below -- so none of those four
; existing dead-check call sites needed to change at all.
;
; No death/fall animation exists in the MSU roster format (converter only
; emits idle/walk/attack) -- plan_game.md 3 explicitly permits accepting a
; plain reaction instead: the killing blow already stamps CHAR_HIT_STUN via
; Character_HitApply_VsPlayer like any other hit, so the existing generic
; hit-reaction (hold idle) already reads as "you got hit" for the one frame
; before Game_State_HandlePlayerDeath below reacts to CHAR_HP==0.
; ============================================================================

GAME_LIVES_START             = 20    ; arbitrary arcade-style default; BOR
                                       ; itself has no lives concept, this
                                       ; project's own choice for a loss loop.
                                       ; Set deliberately high (not a balance
                                       ; choice): with 3, unattended AI combat
                                       ; drove Game_Lives to 0 and reached
                                       ; GAME_STATE_GAMEOVER by ~frame 1200 in
                                       ; measured testing, and GAMEOVER skips
                                       ; Game_State_Play__playing's entire body
                                       ; (no Oop/Oam/Screen/streaming) -- long
                                       ; verify gates (phase6.py alone runs
                                       ; ~1720 cumulative frames with no player
                                       ; input) were one unlucky combat RNG
                                       ; roll from silently freezing mid-gate.
                                       ; 20 gives ~6000 frames of organic-death
                                       ; margin at the measured ~1 life/300f
                                       ; rate -- real difficulty tuning is a
                                       ; later phase's job, not this one's.
PLAYER_RESPAWN_INVULN_FRAMES = 90     ; ~1.5s @ 60Hz
PLAYER_RESPAWN_X_MARGIN      = 16     ; px inset from the camera's left edge,
                                       ; so the respawned player isn't flush
                                       ; against the screen boundary
PLAYER_RESPAWN_Y             = 150    ; matches CharacterEntity_Init__player's
                                       ; own boot default
GAME_OVER_CONTINUE_FRAMES    = 300    ; ~5s @ 60Hz to press Start before
                                       ; falling back to GAME_STATE_TITLE

Game_Lives             = $7E2754   ; .db -- remaining lives; a death at 0
                                    ; lives triggers GAME_STATE_GAMEOVER
                                    ; instead of a respawn
Player_InvulnFrames    = $7E2755   ; .db -- brief post-respawn invulnerability
                                    ; countdown; Character_HitApply_VsPlayer
                                    ; skips stun/damage entirely while nonzero
GameOver_ContinueTimer = $7E2756   ; .dw -- frames left to press Start before
                                    ; GAME_STATE_GAMEOVER falls back to TITLE;
                                    ; set once on the transition INTO
                                    ; GAMEOVER (see
                                    ; Game_State_HandlePlayerDeath), not
                                    ; lazily -- ticking a stale/garbage value
                                    ; down would be wrong on first entry

; ============================================================================
; Phase G4 (plan_game.md 4): win condition and stage transition.
;
; BOR's own win condition is "all spawned enemies defeated and the level's
; spawn queue exhausted, then reach the right edge." The queue-exhausted/
; all-dead half is cheap: core/spawn.pasm's Spawn_Index vs Spawn_Count IS
; "queue exhausted", and CHAR_HP==0 on Entity1/2/3 IS "no AI alive" -- the
; exact same soft-kill sentinel Phase 11 and the spawn queue's own "slot
; free" check already use, so this needed no new per-entity state at all.
;
; The "reach the right edge" half needed one real design decision (see this
; session's advisor consult): BOR normally holds the camera back from a
; level's true end until its current combat wave clears, so simply letting
; the player walk to Screen_MaxX from frame 1 would make "win" trivial and
; instant. Rather than hand-author a per-level "combat zone" table this
; project doesn't have, the hold boundary is DERIVED from data the level
; already has: core/spawn.pasm's Spawn_LastTriggerX -- the trigger_x of the
; stage's own LAST spawn record (spawn tables are packed in ascending
; trigger order, so this is always the highest trigger in the table), which
; is already expressed in the same Screen_PosX camera-space units Screen_MaxX
; itself uses. Stage_Load clamps Screen_MaxX down to this value at load
; time; Game_State_Play__playing's win check raises it back to the stage's
; TRUE full width (Stage_TrueMaxX, captured once by Stage_Load right after
; Core_Screen_SetPlayfieldBorder computes it) the instant the queue-
; exhausted+all-dead condition goes true. Reaching Stage_TrueMaxX after that
; point (Core_Screen_Play's own existing clamp naturally caps Screen_PosX
; there as the player keeps walking) is the real stage-clear trigger.
;
; Two writers to Screen_MaxX (the hold-clamp and the unlock) is exactly the
; hazard class the old 79px streaming-level bug (see main.pasm's Boot_Set
; PlayfieldBorder header) came from -- avoided here by making the unlock an
; unconditional overwrite from a cached Stage_TrueMaxX, never an in-place
; adjustment of whatever Screen_MaxX currently holds.
;
; Stage_Load is a full, blocking, boot-style reload (Core_StreamCache_Init/
; Core_StreamCacheFp_Init re-init, Bg_LoadScene, BG3 tilemap clear, the
; conditional frontpanel load, Spawn_Init, HudDirty force, playfield border
; recompute) -- deliberately NOT the live per-frame incremental streaming
; path (Core_StreamScroll_Play's ring-buffer eviction/repair machinery),
; which has never been exercised for a full level swap and is designed for
; small per-frame deltas, not replacing an entire tileset+tilemap+palette+
; spawn-queue at once. Held under sei with the screen already effectively
; blanked (Core_Nmi_Play's own per-vblank forced-blank bracket, widened here
; by simply not returning from Stage_Load until the whole reload is done --
; same "stall everything, nothing runs until this returns" shape scpu_boot's
; own Bg_LoadScene call already uses, just triggered by a state transition
; instead of the reset vector). AI entities need NO explicit reset here:
; the win condition already requires Entity1/2/3_Hp == 0 (all soft-killed),
; and Spawn_Play already resets position/facing/HP whenever it reuses a
; freed slot for the NEXT wave -- the exact same mechanism a stage
; transition's fresh Spawn_Init leans on, no new code path. Only the player
; needs an explicit reset, via the existing Game_State_RespawnPlayer.
;
; STAGE_COUNT must match len(BG_SCREENS) in build_rom.py -- same hand-synced,
; checked-at-build-time-not-automatically-enforced pattern as this file's
; own GAME_LIVES_START-adjacent constants and main.pasm's RESET/NMI/IRQ
; vectors (see CLAUDE.md). build_rom.py's check_stage_count() cross-checks
; it against the packed bor.msu's real bg_count.
; ============================================================================

STAGE_COUNT = 2   ; BG_SCREENS/FP_SCREENS/SPAWN_TABLES length in build_rom.py

Game_StageIndex   = $7E2758   ; .dw -- 0-based index of the currently loaded
                               ; stage; Bg_LoadScene_StageIndex (main.pasm)
                               ; is set from this (low byte) before every
                               ; jsr Bg_LoadScene, boot and Stage_Load alike
Stage_Cleared     = $7E275A   ; .db -- 0 until this stage's win condition
                               ; has fired once, then 1 until the next
                               ; Stage_Load resets it back to 0
Stage_TrueMaxX    = $7E275B   ; .dw -- Screen_MaxX's real, fully-unlocked
                               ; value for the current stage, cached by
                               ; Stage_Load right after Core_Screen_
                               ; SetPlayfieldBorder computes it
Stage_LoadPending = $7E275D   ; .db -- set the same frame Game_State enters
                               ; STAGECLEAR; tells Game_State_Play__
                               ; stageclear to actually run Stage_Load on
                               ; its own first active frame (the generic
                               ; transition-edge OAM-hide at the top of
                               ; Game_State_Play runs first, same discipline
                               ; as every other PLAYING exit)

; ----------------------------------------------------------------------
; Called once per scpu_main_loop iteration, right after Core_Nmi_WaitFrame/
; Tad_Process/Tad_FinishLoadingData/Core_Input_Poll (all of which must keep
; running in every state -- music must not stop when paused, and input must
; keep being read to ever leave a state). Entry/exit convention: .a16/.i16,
; matching scpu_main_loop's own (see Core_Screen_Play for the same pattern
; of re-asserting width at entry rather than trusting the caller).
; ----------------------------------------------------------------------
Game_State_Play:
    php
    rep #$31
.a16
    lda Game_State
    cmp Game_StatePrev
    beq Game_State_Play__no_transition
    ; Entering a new state this frame. If the state we're LEAVING was
    ; PLAYING and the one we're ENTERING is not, hide every sprite once --
    ; otherwise hardware OAM keeps showing the last-uploaded gameplay
    ; frame forever, since Core_Oam_Play won't be called again below.
    ; (Entering PLAYING from a non-playing state needs no symmetric
    ; action: CharacterEntity_Play/Core_Oam_Play resume driving OAM from
    ; real state on the very next PLAYING frame.)
    lda Game_StatePrev
    cmp #GAME_STATE_PLAYING
    bne Game_State_Play__transition_done
    lda Game_State
    cmp #GAME_STATE_PLAYING
    beq Game_State_Play__transition_done
    jsr Core_Oam_ClearAll
    lda #1
    sta.l Oam_NeedFullUpload
    jsr Core_Oam_Play
    ; Core_Oam_Play leaves Oam_NeedFullUpload SET on a queue-full DMA-enqueue
    ; failure (core/oam.pasm's own comment on the main-table `bcs` branch --
    ; it's only cleared once the hi-table enqueue also lands) -- reuse that
    ; as a success signal instead of assuming a single jsr always lands.
    ; Committing this transition (advancing Game_StatePrev) before confirming
    ; the enqueue actually succeeded is exactly the bug class memory
    ; dma_commit_before_confirm_bug generalizes; CLAUDE.md's "at most one
    ; entity may stream an animation frame per frame" note means the queue
    ; genuinely can be full (6 of 8 slots) right when a transition lands.
    ; Don't advance Game_StatePrev until it reads back 0 -- next frame's
    ; transition check (Game_StatePrev still PLAYING) retries the whole
    ; hide attempt for free, with no extra state needed.
    lda.l Oam_NeedFullUpload
    bne Game_State_Play__no_transition
Game_State_Play__transition_done:
    lda Game_State
    sta Game_StatePrev
Game_State_Play__no_transition:
    rep #$31
.a16
    lda Game_State
    ; Phase G5: bne-past-a-jmp instead of beq for every case here now --
    ; the title screen's own block (below) pushed several of these targets
    ; out of a plain branch's +-127-byte range; jmp has no such limit, and
    ; the bne only ever needs to skip one instruction.
    cmp #GAME_STATE_PLAYING
    bne Game_State_Play__check_title
    jmp Game_State_Play__playing
Game_State_Play__check_title:
    rep #$30
.a16
    cmp #GAME_STATE_TITLE
    bne Game_State_Play__check_paused
    jmp Game_State_Play__title
Game_State_Play__check_paused:
    rep #$30
.a16
    cmp #GAME_STATE_PAUSED
    bne Game_State_Play__check_gameover
    jmp Game_State_Play__paused
Game_State_Play__check_gameover:
    rep #$30
.a16
    cmp #GAME_STATE_GAMEOVER
    bne Game_State_Play__check_stageclear
    jmp Game_State_Play__gameover
Game_State_Play__check_stageclear:
    rep #$30
.a16
    cmp #GAME_STATE_STAGECLEAR
    bne Game_State_Play__not_stageclear
    brl Game_State_Play__stageclear     ; brl, not beq -- Game_State_Play__
                                          ; stageclear is now defined well
                                          ; past the win-check block below,
                                          ; out of a plain branch's range
                                          ; (same fix spawn.pasm's own
                                          ; Spawn_Play__not_yet needed)
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Game_State_Play__not_stageclear:
    ; CHARSELECT/ENDING: explicit no-op stubs for this phase -- Core_Nmi_
    ; WaitFrame (scpu_main_loop) already keeps pacing correct, nothing else
    ; needs to run yet.
    jmp Game_State_Play__done

; ----------------------------------------------------------------------
; Phase G5: title screen step dispatch. See this file's own Phase G5 header
; above for why this is a multi-frame drip instead of a single draw. Entry/
; exit convention: .a16/.i16 (Game_State_Play's).
; ----------------------------------------------------------------------
Game_State_Play__title:
    sep #$20
.a8
    lda.l Title_Step
    ; Each check below uses a short bne-past-a-jmp instead of a direct beq:
    ; the target routines are spread out enough across this file (several
    ; full DrawString call sites apart) that a plain beq risks the real
    ; 65816 +-127-byte conditional-branch limit -- jmp has no such limit,
    ; and the bne itself only ever has to skip one instruction.
    cmp #TITLE_STEP_WAIT
    bne Game_State_Play__title_check_draw_main
    jmp Game_State_Play__title_wait
Game_State_Play__title_check_draw_main:
    sep #$20
.a8
    cmp #TITLE_STEP_DRAW_MAIN
    bne Game_State_Play__title_check_draw_press
    jmp Game_State_Play__title_draw_main
Game_State_Play__title_check_draw_press:
    sep #$20
.a8
    cmp #TITLE_STEP_DRAW_PRESS
    bne Game_State_Play__title_check_clear_main
    jmp Game_State_Play__title_draw_press
Game_State_Play__title_check_clear_main:
    sep #$20
.a8
    cmp #TITLE_STEP_CLEAR_MAIN
    bne Game_State_Play__title_check_clear_press
    jmp Game_State_Play__title_clear_main
Game_State_Play__title_check_clear_press:
    sep #$20
.a8
    cmp #TITLE_STEP_CLEAR_PRESS
    bne Game_State_Play__title_check_done
    jmp Game_State_Play__title_clear_press
Game_State_Play__title_check_done:
    ; Title_Step >= 5 (TITLE_STEP_CLEAR_PRESS done) -- both rows are clean,
    ; finish the transition into PLAYING.
    jmp Game_State_Play__title_enter_playing

Game_State_Play__title_draw_main:
    sep #$20
.a8
    lda #TITLE_ROW_MAIN
    rep #$31
.a16
.i16
    ldx #0
    ldy #(Text_Str_TitleMain - Text_StringPool)
    jsr Core_Text_DrawString
    sep #$20
.a8
    lda #TITLE_STEP_DRAW_PRESS
    sta.l Title_Step
    rep #$31
.a16
.i16
    jmp Game_State_Play__done

Game_State_Play__title_draw_press:
    sep #$20
.a8
    lda #TITLE_ROW_PRESS
    rep #$31
.a16
.i16
    ldx #0
    ldy #(Text_Str_TitlePress - Text_StringPool)
    jsr Core_Text_DrawString
    sep #$20
.a8
    lda #TITLE_STEP_WAIT
    sta.l Title_Step
    rep #$31
.a16
.i16
    jmp Game_State_Play__done

Game_State_Play__title_wait:
    rep #$31
.a16
.i16
    lda.l Input_trigger+1
    and #$0010                     ; Start -- same high-byte layout as
                                    ; Game_State_Play__gameover's own check
    bne Game_State_Play__title_wait_pressed
    jmp Game_State_Play__done
Game_State_Play__title_wait_pressed:
    sep #$20
.a8
    lda #TITLE_STEP_CLEAR_MAIN
    sta.l Title_Step
    rep #$31
.a16
.i16
    jmp Game_State_Play__done

Game_State_Play__title_clear_main:
    sep #$20
.a8
    lda #TITLE_ROW_MAIN
    rep #$31
.a16
.i16
    ldx #0
    ldy #(Text_Str_TitleBlank - Text_StringPool)
    jsr Core_Text_DrawString
    sep #$20
.a8
    lda #TITLE_STEP_CLEAR_PRESS
    sta.l Title_Step
    rep #$31
.a16
.i16
    jmp Game_State_Play__done

Game_State_Play__title_clear_press:
    sep #$20
.a8
    lda #TITLE_ROW_PRESS
    rep #$31
.a16
.i16
    ldx #0
    ldy #(Text_Str_TitleBlank - Text_StringPool)
    jsr Core_Text_DrawString
    sep #$20
.a8
    lda #5                          ; any value >= TITLE_STEP_CLEAR_PRESS+1
                                    ; works; this falls through to
                                    ; Game_State_Play__title_enter_playing
                                    ; the very next frame this state runs
    sta.l Title_Step
    rep #$31
.a16
.i16
    jmp Game_State_Play__done

Game_State_Play__title_enter_playing:
    sep #$20
.a8
    lda #TITLE_STEP_DRAW_MAIN
    sta.l Title_Step            ; reset for the next time TITLE is entered
    rep #$31
.a16
.i16
    lda #GAME_STATE_PLAYING
    sta.l Game_State
    jmp Game_State_Play__done

Game_State_Play__paused:
    ; Frozen: gameplay subsystems below simply don't run. Music keeps
    ; playing (scpu_main_loop's Tad_Process/Tad_FinishLoadingData calls
    ; are outside this dispatch, unconditional every state) and input
    ; keeps being polled (also outside this dispatch), so a future pause
    ; menu can read Start/Select to resume without any change here.
    jmp Game_State_Play__done

Game_State_Play__gameover:
    rep #$31
.a16
    ; Phase G3: continue countdown. Start before GameOver_ContinueTimer
    ; hits 0 continues (fresh lives, full respawn, back to PLAYING);
    ; letting it expire falls back to GAME_STATE_TITLE -- the existing
    ; "nothing is running" holding state (G2). There's no better fallback
    ; yet; a real "insert coin"/attract-mode content is G5's job.
    lda.l Input_trigger+1
    and #$0010                     ; Start -- core/input.pasm's documented
                                    ; "B Y Sel Start U D L R" high-byte layout
    beq Game_State_Play__gameover_no_continue
    lda #GAME_LIVES_START
    sta.l Game_Lives
    jsr Game_State_RespawnPlayer
    lda #GAME_STATE_PLAYING
    sta.l Game_State
    jmp Game_State_Play__done
Game_State_Play__gameover_no_continue:
    lda.l GameOver_ContinueTimer
    beq Game_State_Play__gameover_timeout
    dec a
    sta.l GameOver_ContinueTimer
    jmp Game_State_Play__done
Game_State_Play__gameover_timeout:
    rep #$31
.a16
    lda #GAME_STATE_TITLE
    sta.l Game_State
    jmp Game_State_Play__done

Game_State_Play__playing:
    rep #$31
.a16
    ; Phase G3 (plan_game.md 3): player death check, before this frame's
    ; Core_Oop_Play pass -- see this file's Phase G3 header for why this
    ; is handled entirely here rather than in the AI-shaped dead-check
    ; sites elsewhere. Reads CHAR_HP==0 one frame after the killing blow
    ; landed (Character_HitApply_VsPlayer already stamped hit-stun/HP the
    ; frame before, via the normal collision pass) -- that one frame of
    ; latency is harmless: the player is exempt from every AI-only dead
    ; check, so it just plays one more ordinary (already-stunned) frame.
    lda.l PlayerEntity_Hp
    and #$00FF
    bne Game_State_Play__no_death
    jsr Game_State_HandlePlayerDeath
    lda.l Game_State
    cmp #GAME_STATE_PLAYING
    beq Game_State_Play__no_death
    ; Left PLAYING (GAMEOVER) this frame -- skip the rest of the gameplay
    ; body; the transition-edge check at the top of this routine will hide
    ; OAM next call, same as any other PLAYING exit.
    jmp Game_State_Play__done
Game_State_Play__no_death:
    rep #$31
.a16
    ; Phase G3: tick the post-respawn invulnerability window down once per
    ; frame regardless of whether a hit actually lands this frame --
    ; Character_HitApply_VsPlayer only READS this, never decrements it.
    lda.l Player_InvulnFrames
    and #$00FF
    beq Game_State_Play__invuln_done
    dec a
    sta.l Player_InvulnFrames
Game_State_Play__invuln_done:
    ; Phase G4: win condition, checked once per PLAYING frame before the
    ; gameplay body below -- see this file's own Phase G4 header for the
    ; full two-step design (queue-exhausted+all-AI-dead unlocks the camera
    ; clamp; reaching the newly-unlocked true edge is the real trigger).
    sep #$20
.a8
    lda.l Stage_Cleared
    bne Game_State_Play__stage_check_edge
    lda.l Spawn_Index
    cmp.l Spawn_Count
    bcc Game_State_Play__stage_no_win_a8
    lda.l Entity1_Hp
    ora.l Entity2_Hp
    ora.l Entity3_Hp
    bne Game_State_Play__stage_no_win_a8
    lda #1
    sta.l Stage_Cleared
    rep #$31
.a16
.i16
    lda.l Stage_TrueMaxX
    sta Screen_MaxX
    bra Game_State_Play__stage_check_edge
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Game_State_Play__stage_no_win_a8:
    rep #$31
.a16
.i16
    bra Game_State_Play__stage_no_win
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Game_State_Play__stage_check_edge:
    rep #$31
.a16
.i16
    lda Screen_PosX
    cmp.l Stage_TrueMaxX
    bcc Game_State_Play__stage_no_win
    sep #$20
.a8
    lda #1
    sta.l Stage_LoadPending
    rep #$31
.a16
.i16
    lda #GAME_STATE_STAGECLEAR
    sta.l Game_State
    jmp Game_State_Play__done
Game_State_Play__stage_no_win:
    rep #$31
.a16
.i16

    ; The body every gate today already exercises from boot -- moved
    ; here verbatim from scpu_main_loop, same call order, same comments
    ; preserved at each call site below.
    jsr Core_Oop_Play
    jsr Core_Screen_Play
    ; --- Gate 0 (plan_vm.md 2, 0.2 deviation 1): the script VM gets one
    ; call per frame, same as the two lines above. Vm_Run itself is a
    ; no-op once the loaded script has reached VMSTAT_DONE/VMSTAT_FAULT,
    ; so this is safe to call unconditionally on every iteration
    ; regardless of whether a script is loaded, running, or finished. ---
    jsr Vm_Run
    ; Phase 9 step 4 follow-up: clamp the just-eased camera position to what
    ; SyncScroll has actually resolved, BEFORE it's committed below -- see
    ; Core_StreamScroll_ClampCamera's own header comment for why.
    jsr Core_StreamScroll_ClampCamera
    ; Phase 8: commit the eased camera position to BG1's horizontal scroll
    ; shadow -- Core_Nmi_Play writes Nmi_Bg1ScrollX to $210D (write-twice,
    ; low then high byte) every vblank regardless, so this just has to keep
    ; the shadow current. Nmi_Bg1ScrollY is deliberately left untouched: no
    ; vertical scroll exists (see the playfield-height comment at msu1_done).
    lda Screen_PosX
    sta.l Nmi_Bg1ScrollX
    ; Phase 9 step 4: keep the streaming BG1 ring buffer in sync with the
    ; camera position just committed above. No-ops for a BG_MODE_STATIC
    ; level (the shipped boss build) and whenever an animation-frame stream
    ; still has DMAs in flight -- see Core_StreamScroll_Play's own header.
    jsr Core_StreamScroll_Play
    ; Phase 10 Step 2c (plan.md 2.10): same idea, for the BG3 frontpanel's
    ; own cache -- see Core_StreamScrollFp_Play's own header for the DMA-
    ; queue-sharing note (BG1 and FP may both enqueue in the same frame).
    jsr Core_StreamScrollFp_Play
    ; Spawn-table phase: runs before Hud_Play so a spawn landing this frame
    ; (CHAR_HP 0 -> CHAR_HP_MAX) is reflected in the same frame's HUD bar
    ; redraw instead of lagging one frame behind.
    jsr Spawn_Play
    ; Hud_Play runs AFTER Core_Oop_Play (so it sees this frame's CHAR_HP, which
    ; Character_HitApply may have just changed) and BEFORE Core_Oam_Play. It is
    ; dirty-gated and enqueues nothing on a frame where no HP changed -- see its
    ; header for why that matters to the vblank budget.
    jsr Hud_Play
    jsr Core_Oam_Play

Game_State_Play__done:
    plp
    rts

; ----------------------------------------------------------------------
; Phase G4 (plan_game.md 4): GAME_STATE_STAGECLEAR dispatch. Entered via the
; normal transition-edge path at the top of Game_State_Play (same OAM-hide
; discipline as any other PLAYING exit -- see that block's own comment).
; Stage_LoadPending is set the SAME frame Game_State became STAGECLEAR (see
; the win-check above), so this runs the actual (heavy, blocking) reload on
; its own very first active frame, then immediately returns to PLAYING.
; Entry/exit convention: .a16/.i16 (Game_State_Play's).
; ----------------------------------------------------------------------
Game_State_Play__stageclear:
    sep #$20
.a8
    lda.l Stage_LoadPending
    beq Game_State_Play__stageclear_done   ; already loaded -- no-op
    lda #0
    sta.l Stage_LoadPending

    rep #$31
.a16
.i16
    lda.l Game_StageIndex
    inc a
    cmp #STAGE_COUNT
    bcc Game_State_Play__stageclear_next
    ; --- no more stages: this project's content ends here for now -- go to
    ; the existing ENDING stub rather than looping or crashing. A real
    ; ending (G10) is out of this phase's scope. ---
    lda #GAME_STATE_ENDING
    sta.l Game_State
    jmp Game_State_Play__stageclear_done
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Game_State_Play__stageclear_next:
    sta.l Game_StageIndex
    sep #$20
.a8
    sta.l Bg_LoadScene_StageIndex   ; A's low byte == the new Game_StageIndex
                                     ; (STAGE_COUNT is tiny; always fits a byte)
    rep #$31
.a16
.i16
    jsr Stage_Load
    lda #GAME_STATE_PLAYING
    sta.l Game_State
Game_State_Play__stageclear_done:
    jmp Game_State_Play__done

; ----------------------------------------------------------------------
; Phase G3 (plan_game.md 3): called once, the instant PlayerEntity_Hp
; reads 0 during PLAYING (see Game_State_Play__playing above). Decrements
; Game_Lives; if lives remain, respawns the player in place (see
; Game_State_RespawnPlayer below); otherwise arms the continue countdown
; and transitions to GAME_STATE_GAMEOVER. Entry/exit convention: .a16/.i16
; (Game_State_Play's).
; ----------------------------------------------------------------------
Game_State_HandlePlayerDeath:
    rep #$31
.a16
    lda.l Game_Lives
    and #$00FF
    beq Game_State_HandlePlayerDeath__gameover
    sep #$20
.a8
    dec a
    sta.l Game_Lives
    rep #$31
.a16
    jsr Game_State_RespawnPlayer
    rts

Game_State_HandlePlayerDeath__gameover:
    rep #$31
.a16
    lda #GAME_OVER_CONTINUE_FRAMES
    sta.l GameOver_ContinueTimer
    lda #GAME_STATE_GAMEOVER
    sta.l Game_State
    rts

; ----------------------------------------------------------------------
; Phase G3: full player reset -- HP, hit-stun, facing, animation-selection
; (plan_game.md 3's own "watch out" list: "not just HP"), a brief
; invulnerability window, and reposition to the camera's current left
; edge. Called both from a normal death-with-lives-remaining (above) and
; from a GAME OVER continue (Game_State_Play__gameover). Entry/exit
; convention: .a16/.i16.
; ----------------------------------------------------------------------
Game_State_RespawnPlayer:
    sep #$20
.a8
    lda #CHAR_HP_MAX
    sta.l PlayerEntity_Hp
    lda #0
    sta.l PlayerEntity_HitStun
    sta.l PlayerEntity_FacingLeft
    sta.l PlayerEntity_Selected
    lda #$FF
    sta.l PlayerEntity_FrameIndex
    lda #1
    sta.l PlayerEntity_TickCounter
    lda #PLAYER_RESPAWN_INVULN_FRAMES
    sta.l Player_InvulnFrames
    lda #PLAYER_RESPAWN_Y
    sta.l PlayerEntity_PosY
    rep #$31
.a16
    lda Screen_PosX
    clc
    adc #PLAYER_RESPAWN_X_MARGIN
    sta.l PlayerEntity_PosX
    rts

; ----------------------------------------------------------------------
; Phase G4 (plan_game.md 4): full stage (re)load. See this file's own Phase
; G4 header for why this is a full blocking boot-style reload rather than
; the live per-frame streaming path, and why AI entities need no explicit
; reset here. Caller (Game_State_Play__stageclear) must set
; Bg_LoadScene_StageIndex to the stage to load BEFORE calling this.
; Entry/exit convention: .a16/.i16 (Game_State_Play's).
; ----------------------------------------------------------------------
Stage_Load:
    php
    sei

    ; --- Core_Nmi_Stop: THIS IS THE LOAD-BEARING FIX, not sei above. `sei`
    ; masks IRQ, but NMI is NON-MASKABLE -- CLAUDE.md/memory nmi_handler_
    ; no_register_save_reentrancy already flagged this exact gap as
    ; "unverified since sei can't mask NMI", and this routine is where it
    ; finally bit: a real vblank landing mid-load fires Core_Nmi_Play (NMI
    ; is genuinely enabled during live gameplay, unlike at boot, where
    ; Core_Nmi_Init hasn't run yet and this same sei-only pattern in Bg_
    ; LoadScene/Bg_LoadSceneFp_Streaming happens to be safe for that
    ; reason alone). Core_Nmi_Play's own commit bracket writes CGRAM color
    ; 0 every vblank (core/nmi.pasm) -- interrupting Bg_LoadSceneFp_
    ; Streaming's own CGADD=4 palette-write loop mid-sequence left CGADD
    ; wherever Core_Nmi_Play's own write left it, scrambling every
    ; subsequent color in that loop. Confirmed via a byte-level Mesen2 CGRAM
    ; dump: some colors landed correct-value-wrong-slot, others simply
    ; unwritten -- exactly the signature of a stray interleaved write
    ; corrupting an auto-incrementing hardware pointer mid-sequence, not a
    ; fixed off-by-N bug. Core_Nmi_Stop/Core_Nmi_Start (core/nmi.pasm)
    ; already exist for exactly this documented purpose ("useful around a
    ; sequence that would be corrupted by an NMI firing mid-way through")
    ; -- this is their first real caller. ---
    jsr Core_Nmi_Stop

    ; --- force blank too, on top of Core_Nmi_Stop above: writing to CGRAM/
    ; VRAM outside of vblank or forced blank is independently a real PPU
    ; hazard (the renderer is concurrently reading the same RAM to draw the
    ; current scanline) even with NMI fully disabled -- boot gets this for
    ; free (the screen is genuinely off, Core_Nmi_Init hasn't run yet, for
    ; every earlier load in this file); a stage transition runs from live
    ; gameplay with the screen ON, so it has to ask for it explicitly. ---
    sep #$20
.a8
    lda #$80
    sta $2100
    rep #$31
.a16
.i16

    ; --- re-init both streaming tile caches -- idempotent (Core_StreamCache_
    ; Init/Core_StreamCacheFp_Init are already re-run-safe: they just refill
    ; their own Tile2Slot/Slot2Tile/SlotStamp tables with sentinel values,
    ; same as at boot) so the new stage starts with a genuinely empty cache,
    ; not the old stage's stale tile residency. ---
    jsr Core_StreamCache_Init
    jsr Core_StreamCacheFp_Init

    ; --- StreamScroll_Enabled/StreamScrollFp_Enabled/StreamScrollFp_
    ; ColPending: unconditionally re-zeroed before Bg_LoadScene runs, same
    ; reasoning as scpu_boot's own equivalent zeroing (main.pasm, msu1_done
    ; area) -- Bg_LoadScene_Streaming/Bg_LoadSceneFp_Streaming below will
    ; re-set these to 1 if and when the new stage actually needs them, but
    ; a stage transitioning FROM a streaming level TO a static one (or one
    ; with no frontpanel) would otherwise leave the old stage's flags set. ---
    rep #$31
.a16
.i16
    sep #$20
.a8
    lda #0
    sta StreamScroll_Enabled
    sta StreamScrollFp_Enabled
    sta StreamScrollFp_ColPending
    rep #$31
.a16
.i16

    ; --- load this stage's BG1 tileset/tilemap/palette + BG3 HUD tileset.
    ; Bg_LoadScene_StageIndex already set by the caller. This also copies
    ; the new stage's own Spawn_MsuOffsetLo/Hi/Spawn_Count out of its bg
    ; record (see main.pasm's Bg_LoadScene, and core/spawn.pasm's header). ---
    jsr Bg_LoadScene

    ; --- BG3 tilemap clear: identical to scpu_boot's own scpu_bg3_map loop
    ; (main.pasm) -- needed here too, since Bg_LoadScene only ever touches
    ; BG1 (see that routine's own header); the OLD stage's HUD/frontpanel
    ; tilemap entries are still sitting in VRAM otherwise. $2115 (VMAIN,
    ; +1 word after $2119) is already set by Bg_LoadScene's own boot-time-
    ; style setup right at its own entry, so no need to re-set it here. ---
    sep #$20
.a8
    lda #BG3_TILEMAP_VRAM_WORD
    rep #$31
.a16
.i16
    sta $2116
    ldx #BG3_TILEMAP_WORDS
    lda #$0000
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Stage_Load__bg3_clear:
    sta $2118
    dex
    bne Stage_Load__bg3_clear

    ; --- conditional frontpanel load, same fp_offset-nonzero gate as
    ; scpu_boot's own Boot_LoadFp block ---
    sep #$20
.a8
    lda.l BgRecordStaging+28
    ora.l BgRecordStaging+29
    ora.l BgRecordStaging+30
    beq Stage_Load__skip_fp
    rep #$31
.a16
.i16
    jsr Bg_LoadSceneFp_Streaming
    bra Stage_Load__fp_done
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Stage_Load__skip_fp:
    rep #$31
.a16
.i16
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Stage_Load__fp_done:

    ; --- this stage's own spawn queue (Spawn_MsuOffsetLo/Hi/Spawn_Count
    ; already populated by Bg_LoadScene above) ---
    jsr Spawn_Init

    ; --- force the next Hud_Play call to redraw unconditionally: the BG3
    ; clear above just wiped the HUD's own tilemap entries, and the
    ; player's HP may well be unchanged across the transition (dirty-gating
    ; on HP alone would then skip the redraw entirely). ---
    sep #$20
.a8
    lda #1
    sta.l HudDirty

    ; --- playfield border for the new stage: same static-vs-streaming
    ; width dispatch main.pasm's own Boot_SetPlayfieldBorder uses, kept as
    ; a separate copy here rather than a shared jsr'd routine -- see this
    ; file's own Phase G4 header on why a full, independent, boot-style
    ; reload was chosen; main.pasm's own Msu1_LoadFrame documents this
    ; project's standing preference for a small duplicated block over a
    ; parameterized shared one when the two call sites' surrounding state
    ; differs (there: WRAM scratch cell choice; here: needing to also
    ; capture Stage_TrueMaxX and apply the win-condition hold-clamp, which
    ; boot's own copy has no reason to do). ---
    lda.l StreamScroll_Enabled
    bne Stage_Load__streaming
    rep #$31
.a16
.i16
    ldy #WORLD_CONTENT_WIDTH
    bra Stage_Load__border_go
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Stage_Load__streaming:
    rep #$31
.a16
.i16
    lda.l StreamScroll_WidthTiles
    asl a
    asl a
    asl a                        ; tiles -> pixels (*8)
    tay
    nop                     ; workaround: Poppy branch-target label misalignment (see poppy bug #4)
Stage_Load__border_go:
    rep #$31
.a16
.i16
    lda #0
    ldx #0
    jsr Core_Screen_SetPlayfieldBorder

    ; --- WorldMaxX (player's own walk clamp, independent of the camera --
    ; see main.pasm's WorldMaxX declaration): always the stage's TRUE full
    ; width, never soft-held. Only the camera clamp (Screen_MaxX, below)
    ; gets the pre-clear hold -- see this file's Phase G4 header for why
    ; that's enough: a locked camera already reads as "you can't proceed
    ; further" even though the player can still walk to the current screen's
    ; own right edge. ---
    tya
    sec
    sbc #(256 - PLAYER_MAX_X)
    sta.l WorldMaxX

    ; --- Stage_TrueMaxX capture + pre-clear hold-clamp + Stage_Cleared
    ; reset: shared with boot's own stage-0 setup, see Stage_ApplyWinClamp's
    ; own header for why this is a jsr, not inlined twice. ---
    jsr Stage_ApplyWinClamp

    ; --- reset the camera to this stage's left edge. Screen_FocusNum/Id/
    ; Slot (core/screen.pasm) are untouched -- they already point at the
    ; player entity (never recreated across a stage transition, still
    ; entity 0), so Core_Screen_Play's normal per-frame easing picks up
    ; correctly from here with no explicit re-focus call needed. ---
    rep #$31
.a16
.i16
    lda #0
    sta.l Screen_PosX
    sta.l Screen_PosXFrac

    ; --- full player reset at the new stage's left edge (HP, hit-stun,
    ; facing, animation-selection, invuln window, position) -- reuses
    ; Game_State_RespawnPlayer verbatim; it reads Screen_PosX, which is
    ; now correctly 0 for the new stage. ---
    jsr Game_State_RespawnPlayer

    ; --- restore the real screen brightness (Nmi_ScreenBrightness's cached
    ; value, not a hardcoded constant -- matches whatever boot originally
    ; configured) now that every VRAM/CGRAM write above is done. See this
    ; routine's own entry comment for why forced blank was asserted at all. ---
    sep #$20
.a8
    lda.l Nmi_ScreenBrightness
    sta $2100
    rep #$31
.a16
.i16

    ; --- re-enable NMI (see this routine's own entry comment on Core_Nmi_
    ; Stop) now that every VRAM/CGRAM write this reload needed is done. ---
    jsr Core_Nmi_Start

    plp
    rts

; ----------------------------------------------------------------------
; Phase G4: captures Stage_TrueMaxX from the just-computed real Screen_MaxX,
; applies the pre-clear hold-clamp from Spawn_LastTriggerX, and zeroes
; Stage_Cleared. Shared by BOTH boot (right after its own inline playfield-
; border computation + Spawn_Init) and Stage_Load (same relative position)
; -- a jsr, not two inline copies, specifically because boot's own call site
; sits ahead of nmi_handler's fixed .org with no spare byte budget (an
; inline first draft here pushed that .org past $FC00-emitted bytes and
; failed to assemble). Caller must have already run Core_Screen_
; SetPlayfieldBorder (Screen_MaxX holds the stage's true width) and
; Spawn_Init (Spawn_LastTriggerX holds this stage's last spawn record's
; trigger_x, or 0 if it packs no spawn table at all) before calling this.
; Entry/exit convention: .a16/.i16.
; ----------------------------------------------------------------------
Stage_ApplyWinClamp:
    php
    rep #$31
.a16
.i16
    lda Screen_MaxX
    sta.l Stage_TrueMaxX

    ; --- a stage with no spawn table (Spawn_Count == 0) has Spawn_
    ; LastTriggerX forced to 0 by Spawn_Init -- guard against holding the
    ; camera at the very start forever by only applying the hold when it's
    ; nonzero and actually less than the true width. ---
    lda.l Spawn_LastTriggerX
    beq Stage_ApplyWinClamp__no_hold
    cmp.l Stage_TrueMaxX
    bcs Stage_ApplyWinClamp__no_hold   ; hold point >= true max -- nothing to hold
    sta Screen_MaxX
Stage_ApplyWinClamp__no_hold:
    sep #$20
.a8
    lda #0
    sta.l Stage_Cleared
    plp
    rep #$31
.a16
.i16
    rts
