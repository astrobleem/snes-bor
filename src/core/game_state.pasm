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
GAME_STATE_GAMEOVER   = 4   ; game over, continue countdown (stub)
GAME_STATE_STAGECLEAR = 5   ; stage cleared, transition (stub)
GAME_STATE_ENDING     = 6   ; credits (stub)

Game_State     = $7E2750   ; .dw -- current state, see GAME_STATE_* above
Game_StatePrev = $7E2752   ; .dw -- last frame's state, used only to detect
                           ; the transition edge into a non-playing state
                           ; (one-shot OAM clear+upload, then Core_Oam_Play
                           ; stops being called for the rest of that state)

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
    cmp #GAME_STATE_PLAYING
    beq Game_State_Play__playing
    cmp #GAME_STATE_TITLE
    beq Game_State_Play__title
    cmp #GAME_STATE_PAUSED
    beq Game_State_Play__paused
    ; CHARSELECT/GAMEOVER/STAGECLEAR/ENDING: explicit no-op stubs for this
    ; phase -- Core_Nmi_WaitFrame (scpu_main_loop) already keeps pacing
    ; correct, nothing else needs to run yet.
    jmp Game_State_Play__done

Game_State_Play__title:
    ; No title content yet (that's G5) -- just don't run gameplay. A
    ; forced Game_State write (debugger, or a future gate) can already
    ; land here safely: no entity/HUD/streaming call runs in this state.
    jmp Game_State_Play__done

Game_State_Play__paused:
    ; Frozen: gameplay subsystems below simply don't run. Music keeps
    ; playing (scpu_main_loop's Tad_Process/Tad_FinishLoadingData calls
    ; are outside this dispatch, unconditional every state) and input
    ; keeps being polled (also outside this dispatch), so a future pause
    ; menu can read Start/Select to resume without any change here.
    jmp Game_State_Play__done

Game_State_Play__playing:
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
