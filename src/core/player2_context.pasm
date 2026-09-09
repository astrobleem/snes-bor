; G13 bounded P2 context bridge.
;
; The mature character routines still use the accepted P1 globals for input
; and jump-family state. Slot 1 is the only P2 window, so swap those globals
; around one character dispatch. All actor-local fields remain in the current
; DP window. This is deliberately not an allocator or a second transport.

G13_Player2_ContextEnter:
    php
    phx
    rep #$31
.a16
.i16
    ; Save P1 input state and standalone jump state.
    lda.l Input_press_Addr
    sta.l G13_ContextSaveInput+0
    lda.l Input_trigger_Addr
    sta.l G13_ContextSaveInput+2
    lda.l Input_old_Addr
    sta.l G13_ContextSaveInput+4
    sep #$20
.a8
    lda.l Player_JumpFCount
    sta.l G13_ContextSaveJump+0
    lda.l Player_JumpDelay
    sta.l G13_ContextSaveJump+1
    lda.l Player_JumpAttackFCount
    sta.l G13_ContextSaveJump+2
    lda.l Player_JumpAttackDelay
    sta.l G13_ContextSaveJump+3
    lda.l Player_JumpAttack2FCount
    sta.l G13_ContextSaveJump+4
    lda.l Player_JumpAttack2Delay
    sta.l G13_ContextSaveJump+5
    lda.l Player_JumpBaseLo
    sta.l G13_ContextSaveJump+6
    lda.l Player_JumpBaseLo+1
    sta.l G13_ContextSaveJump+7
    lda.l Player_JumpBaseHi
    sta.l G13_ContextSaveJump+8
    lda.l Player_JumpAttackBaseLo
    sta.l G13_ContextSaveJump+9
    lda.l Player_JumpAttackBaseLo+1
    sta.l G13_ContextSaveJump+10
    lda.l Player_JumpAttackBaseHi
    sta.l G13_ContextSaveJump+11
    lda.l Player_JumpAttack2BaseLo
    sta.l G13_ContextSaveJump+12
    lda.l Player_JumpAttack2BaseLo+1
    sta.l G13_ContextSaveJump+13
    lda.l Player_JumpAttack2BaseHi
    sta.l G13_ContextSaveJump+14
    lda.l Player_JumpAnimMode
    sta.l G13_ContextSaveJump+15

    rep #$31
.a16
.i16
    lda.l Input2_press_Addr
    sta.l Input_press_Addr
    lda.l Input2_trigger_Addr
    sta.l Input_trigger_Addr
    lda.l Input2_old_Addr
    sta.l Input_old_Addr
    sep #$20
.a8
    lda.l Player2_JumpFCount
    sta.l Player_JumpFCount
    lda.l Player2_JumpDelay
    sta.l Player_JumpDelay
    lda.l Player2_JumpAttackFCount
    sta.l Player_JumpAttackFCount
    lda.l Player2_JumpAttackDelay
    sta.l Player_JumpAttackDelay
    lda.l Player2_JumpAttack2FCount
    sta.l Player_JumpAttack2FCount
    lda.l Player2_JumpAttack2Delay
    sta.l Player_JumpAttack2Delay
    lda.l Player2_JumpBaseLo
    sta.l Player_JumpBaseLo
    lda.l Player2_JumpBaseLo+1
    sta.l Player_JumpBaseLo+1
    lda.l Player2_JumpBaseHi
    sta.l Player_JumpBaseHi
    lda.l Player2_JumpAttackBaseLo
    sta.l Player_JumpAttackBaseLo
    lda.l Player2_JumpAttackBaseLo+1
    sta.l Player_JumpAttackBaseLo+1
    lda.l Player2_JumpAttackBaseHi
    sta.l Player_JumpAttackBaseHi
    lda.l Player2_JumpAttack2BaseLo
    sta.l Player_JumpAttack2BaseLo
    lda.l Player2_JumpAttack2BaseLo+1
    sta.l Player_JumpAttack2BaseLo+1
    lda.l Player2_JumpAttack2BaseHi
    sta.l Player_JumpAttack2BaseHi
    lda.l Player2_JumpAnimMode
    sta.l Player_JumpAnimMode
    plx
    plp
    rtl

G13_Player2_ContextExit:
    php
    phx
    rep #$31
.a16
.i16
    ; Commit the P2 context back to its owned fields.
    lda.l Input_press_Addr
    sta.l Input2_press_Addr
    lda.l Input_trigger_Addr
    sta.l Input2_trigger_Addr
    lda.l Input_old_Addr
    sta.l Input2_old_Addr
    sep #$20
.a8
    lda.l Player_JumpFCount
    sta.l Player2_JumpFCount
    lda.l Player_JumpDelay
    sta.l Player2_JumpDelay
    lda.l Player_JumpAttackFCount
    sta.l Player2_JumpAttackFCount
    lda.l Player_JumpAttackDelay
    sta.l Player2_JumpAttackDelay
    lda.l Player_JumpAttack2FCount
    sta.l Player2_JumpAttack2FCount
    lda.l Player_JumpAttack2Delay
    sta.l Player2_JumpAttack2Delay
    lda.l Player_JumpBaseLo
    sta.l Player2_JumpBaseLo
    lda.l Player_JumpBaseLo+1
    sta.l Player2_JumpBaseLo+1
    lda.l Player_JumpBaseHi
    sta.l Player2_JumpBaseHi
    lda.l Player_JumpAttackBaseLo
    sta.l Player2_JumpAttackBaseLo
    lda.l Player_JumpAttackBaseLo+1
    sta.l Player2_JumpAttackBaseLo+1
    lda.l Player_JumpAttackBaseHi
    sta.l Player2_JumpAttackBaseHi
    lda.l Player_JumpAttack2BaseLo
    sta.l Player2_JumpAttack2BaseLo
    lda.l Player_JumpAttack2BaseLo+1
    sta.l Player2_JumpAttack2BaseLo+1
    lda.l Player_JumpAttack2BaseHi
    sta.l Player2_JumpAttack2BaseHi
    lda.l Player_JumpAnimMode
    sta.l Player2_JumpAnimMode

    ; Restore P1's exact pre-dispatch state.
    rep #$31
.a16
.i16
    lda.l G13_ContextSaveInput+0
    sta.l Input_press_Addr
    lda.l G13_ContextSaveInput+2
    sta.l Input_trigger_Addr
    lda.l G13_ContextSaveInput+4
    sta.l Input_old_Addr
    sep #$20
.a8
    lda.l G13_ContextSaveJump+0
    sta.l Player_JumpFCount
    lda.l G13_ContextSaveJump+1
    sta.l Player_JumpDelay
    lda.l G13_ContextSaveJump+2
    sta.l Player_JumpAttackFCount
    lda.l G13_ContextSaveJump+3
    sta.l Player_JumpAttackDelay
    lda.l G13_ContextSaveJump+4
    sta.l Player_JumpAttack2FCount
    lda.l G13_ContextSaveJump+5
    sta.l Player_JumpAttack2Delay
    lda.l G13_ContextSaveJump+6
    sta.l Player_JumpBaseLo
    lda.l G13_ContextSaveJump+7
    sta.l Player_JumpBaseLo+1
    lda.l G13_ContextSaveJump+8
    sta.l Player_JumpBaseHi
    lda.l G13_ContextSaveJump+9
    sta.l Player_JumpAttackBaseLo
    lda.l G13_ContextSaveJump+10
    sta.l Player_JumpAttackBaseLo+1
    lda.l G13_ContextSaveJump+11
    sta.l Player_JumpAttackBaseHi
    lda.l G13_ContextSaveJump+12
    sta.l Player_JumpAttack2BaseLo
    lda.l G13_ContextSaveJump+13
    sta.l Player_JumpAttack2BaseLo+1
    lda.l G13_ContextSaveJump+14
    sta.l Player_JumpAttack2BaseHi
    lda.l G13_ContextSaveJump+15
    sta.l Player_JumpAnimMode
    plx
    plp
    rtl

; Source-normal pre-game P2 session entry. Called from the character-select
; WAIT state when JOY2 Start has an edge. Slot 1 already owns its accepted
; OBJ palette and tile allocation from boot; this changes its player role and
; loads the physical roster slot selected by the independent P2 cursor.
G13_EnableP2Session:
    php
    phx
    rep #$31
.a16
.i16
    lda.l G13_TwoPlayerEnabled
    and #$00FF
    bne G13_EnableP2Session__already_enabled
    lda #1
    sta.l G13_TwoPlayerEnabled
    lda #0
    sta.l G13_P1Out
    sta.l G13_P2Out
    sta.l BorSelect_P2Ordinal
    sep #$20
.a8
    lda #$FF
    sta.l HudCachedP2Hp
    sta.l HudCachedP2Lives
    rep #$31
.a16
.i16
    lda #$FFFF
    sta.l HudCachedP2Score
    jmp G13_EnableP2Session__init_slot

G13_EnableP2Session__already_enabled:
    jmp G13_EnableP2Session__init_slot

; Re-establish the reserved P2 actor after Stage_Load has reinitialized the
; ordinary NPC windows.  This is a mode-owned lifecycle hook, not a second
; spawn path: it uses the same actor fields and Anim_LoadCharacter contract.
G13_EnsureP2AfterStage:
    php
    phx
    rep #$31
.a16
.i16
    lda.l G13_TwoPlayerEnabled
    and #$00FF
    bne G13_EnableP2Session__init_slot
    jmp G13_EnsureP2AfterStage__done

G13_EnableP2Session__init_slot:
    lda.l CharSelect_RosterCount
    pha
    lda.l CharSelect_Index
    pha

    ; The fixed-session edge is taken before CHARSELECT has reloaded the
    ; player's current roster for this run.  Re-establish P1's standalone
    ; jump-family globals from the already-selected P1 record first; otherwise
    ; the subsequent P2 context save can preserve stale bring-up data (for
    ; example LEO's family while actor 0 is RALF).  This is the existing
    ; loader, not a second data path, and it runs before switching to actor 1.
    phd
    pea $0A00
    pld
    lda CHAR_ROSTER_INDEX
    sta.l CharSelect_Index
    jsl Anim_LoadCharacter_Long
    pld

    sep #$20
.a8
    ; Resolve the independent source-normal P2 cursor after the P1 context
    ; restore above.  This keeps the bridge implementation separate from
    ; player-selection policy and removes the old fixed-Leo identity.
    sep #$20
.a8
    lda.l BorSelect_P2Ordinal
    tax
    lda.l BorSelect_RuntimeMap,x
    sta.l CharSelect_Index
    ; Switch DP to Entity 1 while preserving the caller's player-select DP.
    phd
    pea $0A85
    pld
    lda #1
    sta CHAR_INPUT_DRIVEN
    lda #CHAR_HP_MAX
    sta CHAR_HP
    lda #PLAYER_RESPAWN_INVULN_FRAMES
    sta.l G13_P2_InvulnFrames
    lda #0
    sta CHAR_SELECTED
    sta CHAR_ATTACK_VARIANT
    sta CHAR_GRAB_TIMER
    sta CHAR_PICKUP_TYPE
    lda #$FF
    sta CHAR_FRAME_INDEX
    sta CHAR_GRAB_TARGET
    sta CHAR_GRABBED_BY
    lda #80
    sta CHAR_POS_X
    stz CHAR_POS_X_HI
    lda #150
    sta CHAR_POS_Y
    lda.l CharSelect_Index
    sta CHAR_ROSTER_INDEX
    lda #0
    sta.l Entity1_IsBoss

    ; Anim_LoadCharacter writes P1-named standalone jump fields. Run it
    ; inside the same ownership bridge used by CharacterEntity_Play so the
    ; loaded LEO family is committed to Player2_Jump* and P1 is restored.
    jsl G13_Player2_ContextEnter
    ; This module is bank 7; Anim_LoadCharacter is bank 0 and returns RTS.
    ; Use the existing bank-0 JSR/RTL trampoline so the loader executes in
    ; its owning bank without leaving the long-call return byte on the stack.
    jsl Anim_LoadCharacter_Long
    jsl G13_Player2_ContextExit
    pld

    rep #$31
.a16
.i16
    ; Loading the roster is still required for a future continue, but an
    ; exhausted player must remain OUT across the stage boundary.
    jsl G13_ReapplyP2Out
    pla
    sta.l CharSelect_Index
    pla
    sta.l CharSelect_RosterCount
    plx
    plp
    rtl
G13_EnableP2Session__done:
    plx
    plp
    rtl
G13_EnsureP2AfterStage__done:
    plx
    plp
    rtl

; Respawn the reserved P2 actor inside the current shared viewport.  This is
; the P2 counterpart of Game_State_RespawnPlayer and deliberately reuses the
; actor record rather than introducing a second player object.
G13_RespawnP2:
    php
    phd
    pea $0A85
    pld
    sep #$20
.a8
    lda #CHAR_HP_MAX
    sta CHAR_HP
    lda #0
    sta CHAR_HIT_STUN
    sta CHAR_FACING_LEFT
    sta CHAR_SELECTED
    sta CHAR_ATTACK_VARIANT
    sta CHAR_HIT_APPLIED
    sta CHAR_GRAB_TIMER
    sta CHAR_THROW_ZPOS
    sta CHAR_THROW_ZVEL
    lda #$FF
    sta CHAR_FRAME_INDEX
    sta CHAR_GRAB_TARGET
    sta CHAR_GRABBED_BY
    lda #PLAYER_RESPAWN_INVULN_FRAMES
    sta.l G13_P2_InvulnFrames
    lda #0
    sta.l G13_P2Out
    lda #PLAYER_RESPAWN_Y
    sta CHAR_POS_Y
    rep #$31
.a16
.i16
    lda.l Screen_PosX
    clc
    adc #80
    sta CHAR_POS_X
    pld
    plp
    rtl

; Return carry set when the currently selected player actor is explicitly OUT.
; D remains the caller's actor window; this predicate is shared by gameplay
; and rendering so OUT state cannot diverge between the two paths.
G13_PlayerLifecycleIsOut:
    rep #$31
.a16
.i16
    tdc
    cmp #$0A00
    bne G13_PlayerLifecycleIsOut__p2
    lda.l G13_P1Out
    and #$0001
    beq G13_PlayerLifecycleIsOut__clear
    sec
    rtl
G13_PlayerLifecycleIsOut__p2:
    rep #$31
.a16
.i16
    cmp #$0A85
    bne G13_PlayerLifecycleIsOut__none
    ; Slot 1 is an ordinary NPC in 1P mode.  P2Out is meaningful only
    ; while the fixed two-player session owns this actor window.
    lda.l G13_TwoPlayerEnabled
    and #$0001
    beq G13_PlayerLifecycleIsOut__none
    lda.l G13_P2Out
    and #$0001
    beq G13_PlayerLifecycleIsOut__clear
    sec
    rtl
G13_PlayerLifecycleIsOut__none:
G13_PlayerLifecycleIsOut__clear:
    clc
    rtl

; P2's death/life-stock counterpart. Slot 1 remains reserved after OUT.
G13_HandleP2Death:
    php
    rep #$31
.a16
.i16
    ; This shared entry owns both player death checks. In 1P mode it exactly
    ; retains the established P1 lives/game-over semantics; in 2P mode each
    ; player has independent stock and only the second OUT enters GAMEOVER.
    lda.l G13_TwoPlayerEnabled
    and #$00FF
    bne G13_HandleP2Death__two_player
    lda.l PlayerEntity_Hp
    and #$00FF
    beq G13_HandleP2Death__p1_dead
    brl G13_HandleP2Death__return
G13_HandleP2Death__p1_dead:
    rep #$31
.a16
.i16
    lda.l Game_Lives
    and #$00FF
    beq G13_HandleP2Death__one_gameover
    sep #$20
.a8
    dec a
    sta.l Game_Lives
    jsl G13_RespawnP1
    jmp G13_HandleP2Death__gameover_return
G13_HandleP2Death__one_gameover:
    rep #$31
.a16
.i16
    lda #GAME_OVER_CONTINUE_FRAMES
    sta.l GameOver_ContinueTimer
    lda #GAME_STATE_GAMEOVER
    sta.l Game_State
    jmp G13_HandleP2Death__gameover_return
G13_HandleP2Death__two_player:
    rep #$31
.a16
.i16
    lda.l G13_P1Out
    and #$00FF
    bne G13_HandleP2Death__check_p2
    lda.l PlayerEntity_Hp
    and #$00FF
    bne G13_HandleP2Death__check_p2
    lda.l Game_Lives
    and #$00FF
    beq G13_HandleP2Death__p1_out
    sep #$20
.a8
    dec a
    sta.l Game_Lives
    jsl G13_RespawnP1
    bra G13_HandleP2Death__check_p2
G13_HandleP2Death__p1_out:
    sep #$20
.a8
    lda #1
    sta.l G13_P1Out
    jsl G13_ReapplyP1Out
G13_HandleP2Death__check_p2:
    rep #$31
.a16
.i16
    lda.l G13_P2Out
    and #$00FF
    bne G13_HandleP2Death__check_both_out
    ; A living P2 is not a death candidate.  This shared handler runs once
    ; per PLAYING service, so P2's life stock must not be consumed merely
    ; because this call was reached while checking P1.
    lda.l Entity1_Hp
    and #$00FF
    bne G13_HandleP2Death__return
    lda.l G13_P2Lives
    and #$00FF
    beq G13_HandleP2Death__out
    sep #$20
.a8
    dec a
    sta.l G13_P2Lives
    jsl G13_RespawnP2
    plp
    rtl
G13_HandleP2Death__out:
    sep #$20
.a8
    lda #1
    sta.l G13_P2Out
    lda #0
    sta.l Entity1_Hp
    sta.l Entity1_Selected
    lda #$FF
    sta.l Entity1_GrabTarget
    sta.l Entity1_GrabbedBy
    jsl G13_ReapplyP2Out
G13_HandleP2Death__check_both_out:
    sep #$20
.a8
    lda.l G13_P1Out
    beq G13_HandleP2Death__return
    lda.l G13_P2Out
    beq G13_HandleP2Death__return
    rep #$31
.a16
.i16
    lda #GAME_OVER_CONTINUE_FRAMES
    sta.l GameOver_ContinueTimer
    lda #GAME_STATE_GAMEOVER
    sta.l Game_State
G13_HandleP2Death__gameover_return:
    plp
    sec
    rtl
G13_HandleP2Death__return:
    plp
    clc
    rtl

G13_RespawnP1:
    sep #$20
.a8
    lda #CHAR_HP_MAX
    sta.l PlayerEntity_Hp
    lda #0
    sta.l PlayerEntity_HitStun
    sta.l PlayerEntity_FacingLeft
    sta.l PlayerEntity_Selected
    sta.l PlayerEntity_AttackVariant
    sta.l PlayerEntity_HitApplied
    sta.l PlayerEntity_GrabTimer
    sta.l PlayerEntity_ThrowZPos
    sta.l PlayerEntity_ThrowZVel
    sta.l PlayerEntity_AttackVariant
    sta.l PlayerEntity_HitApplied
    sta.l G13_P1Out
    lda #$FF
    sta.l PlayerEntity_FrameIndex
    sta.l PlayerEntity_GrabTarget
    sta.l PlayerEntity_GrabbedBy
    lda #PLAYER_RESPAWN_INVULN_FRAMES
    sta.l Player_InvulnFrames
    lda #PLAYER_RESPAWN_Y
    sta.l PlayerEntity_PosY
    rep #$31
.a16
.i16
    lda.l Screen_PosX
    clc
    adc #PLAYER_RESPAWN_X_MARGIN
    sta.l PlayerEntity_PosX
    rtl

; Stage_Load respawns slot 0 as part of its historical one-player setup.
; Reassert an already exhausted P1 after that load without changing the
; resident roster or the fixed actor layout.
G13_ReapplyP1Out:
    php
    sep #$20
.a8
    lda.l G13_P1Out
    beq G13_ReapplyP1Out__done
    lda #0
    sta.l PlayerEntity_Hp
    sta.l PlayerEntity_Selected
    sta.l PlayerEntity_AttackVariant
    sta.l PlayerEntity_HitApplied
    sta.l PlayerEntity_HitStun
    sta.l PlayerEntity_GrabTimer
    sta.l PlayerEntity_ThrowZPos
    sta.l PlayerEntity_ThrowZVel
    lda #$FF
    sta.l PlayerEntity_GrabTarget
    sta.l PlayerEntity_GrabbedBy
G13_ReapplyP1Out__done:
    plp
    rtl

; Same post-load reassertion for reserved slot 1.  P2's roster and jump
; family remain resident so its later continue can use normal respawn code.
G13_ReapplyP2Out:
    php
    sep #$20
.a8
    lda.l G13_P2Out
    beq G13_ReapplyP2Out__done
    phd
    pea $0A85
    pld
    lda #0
    sta CHAR_HP
    sta CHAR_SELECTED
    sta CHAR_ATTACK_VARIANT
    sta CHAR_HIT_APPLIED
    sta CHAR_HIT_STUN
    sta CHAR_GRAB_TIMER
    sta CHAR_THROW_ZPOS
    sta CHAR_THROW_ZVEL
    lda #$FF
    sta CHAR_GRAB_TARGET
    sta CHAR_GRABBED_BY
    pld
G13_ReapplyP2Out__done:
    plp
    rtl

; Clear non-player runtime state before a new stage's queue is allowed to
; reuse the actor windows. Input role and resident roster identity remain
; intact so the existing prop-art restoration contract is preserved.
G13_ClearOldStageActors:
    php
    ; Per-slot PHD/PLD pairs preserve caller D. Keep one-byte NOP here
    ; to preserve established bank-7 layout; an outer PHD would be unmatched.
    nop
    sep #$20
.a8
    lda.l G13_TwoPlayerEnabled
    bne G13_ClearOldStageActors__slot2
    phd
    pea $0A85
    pld
    jsr G13_ClearOldStageActors__one
    lda #0
    sta.l Actor_InvulnFrames+1
    pld
G13_ClearOldStageActors__after_slot1:
G13_ClearOldStageActors__slot2:
    sep #$20
.a8
    phd
    pea $0B0A
    pld
    jsr G13_ClearOldStageActors__one
    lda #0
    sta.l Actor_InvulnFrames+2
    pld
G13_ClearOldStageActors__after_slot2:
    phd
    pea $0B8D
    pld
    jsr G13_ClearOldStageActors__one
    lda #0
    sta.l Actor_InvulnFrames+3
    pld
G13_ClearOldStageActors__after_slot3:
    phd
    pea $0C10
    pld
    jsr G13_ClearOldStageActors__one
    lda #0
    sta.l Actor_InvulnFrames+4
    sta.l Entity4_ItemRosterIdx
    pld
G13_ClearOldStageActors__after_slot4:
    phd
    pea $0C93
    pld
    jsr G13_ClearOldStageActors__one
    lda #0
    sta.l Actor_InvulnFrames+5
    sta.l Entity5_ItemRosterIdx
    pld
G13_ClearOldStageActors__after_slot5:
    plp
    rtl
G13_ClearOldStageActors__one:
    sep #$20
.a8
    lda #0
    sta CHAR_HP
    sta CHAR_SELECTED
    sta CHAR_ATTACK_VARIANT
    sta CHAR_HIT_APPLIED
    sta CHAR_HIT_STUN
    sta CHAR_GRAB_TIMER
    sta CHAR_PICKUP_TYPE
    sta CHAR_KNOCKDOWN_COUNT
    sta CHAR_KNOCKDOWN_TIMER
    stz CHAR_THROW_ZPOS
    stz CHAR_THROW_ZPOS+1
    stz CHAR_THROW_ZVEL
    stz CHAR_THROW_ZVEL+1
    lda #$FF
    sta CHAR_GRAB_TARGET
    sta CHAR_GRABBED_BY
    rts

; Consume an OUT player's own Start as a continue while the partner remains
; in PLAYING.  Carry set means the caller must skip pause and gameplay for
; this update, preventing one edge from doing two actions.
G13_HandleOutContinue:
    php
    rep #$31
.a16
.i16
    lda.l G13_TwoPlayerEnabled
    and #$00FF
    beq G13_HandleOutContinue__no
    lda.l G13_P1Out
    and #$00FF
    beq G13_HandleOutContinue__p2
    lda.l Input_trigger+1
    and #$0010
    beq G13_HandleOutContinue__p2
    lda #GAME_LIVES_START
    sta.l Game_Lives
    jsl G13_RespawnP1
    bra G13_HandleOutContinue__yes
G13_HandleOutContinue__p2:
    rep #$31
.a16
.i16
    lda.l G13_P2Out
    and #$00FF
    beq G13_HandleOutContinue__no
    lda.l Input2_trigger+1
    and #$0010
    beq G13_HandleOutContinue__no
    lda #GAME_LIVES_START
    sta.l G13_P2Lives
    jsl G13_RespawnP2
G13_HandleOutContinue__yes:
    plp
    sec
    rtl
G13_HandleOutContinue__no:
    plp
    clc
    rtl

; Player-owned GAMEOVER continue.  The global menu state is shared, but the
; continuing controller restores only its own player.  If both edges arrive
; together both players are restored once.
G13_HandleGameoverContinue:
    php
    rep #$31
.a16
.i16
    lda.l Input_trigger+1
    and #$0010
    pha
    lda.l Input2_trigger+1
    and #$0010
    beq G13_HandleGameoverContinue__p1_only
    lda.l G13_TwoPlayerEnabled
    and #$00FF
    beq G13_HandleGameoverContinue__p1_only
    lda #GAME_LIVES_START
    sta.l G13_P2Lives
    jsl G13_RespawnP2
    pla
    beq G13_HandleGameoverContinue__finish
    lda #GAME_LIVES_START
    sta.l Game_Lives
    jsl G13_RespawnP1
    bra G13_HandleGameoverContinue__finish
G13_HandleGameoverContinue__p1_only:
    rep #$31
.a16
.i16
    pla
    beq G13_HandleGameoverContinue__no
    lda #GAME_LIVES_START
    sta.l Game_Lives
    jsl G13_RespawnP1
G13_HandleGameoverContinue__finish:
    rep #$31
.a16
.i16
    lda #GAME_STATE_PLAYING
    sta.l Game_State
    plp
    sec
    rtl
G13_HandleGameoverContinue__no:
    plp
    clc
    rtl

; End a fixed two-player session when the game returns to TITLE.  This makes
; the next new game a genuine one-player session again: slot 1 is released
; to Spawn_Play instead of retaining a live P2 actor across the state
; boundary.  The character record layout and normal spawn initializer remain
; unchanged.
G13_DisableP2Session:
    php
    phx
    rep #$31
.a16
.i16
    lda.l G13_TwoPlayerEnabled
    and #$00FF
    beq G13_DisableP2Session__done
    sep #$20
.a8
    lda #0
    sta.l G13_TwoPlayerEnabled
    lda #0
    sta.l G13_P1Out
    sta.l G13_P2Out
    phd
    pea $0A85
    pld
    lda #CHAR_INPUT_DRIVEN_AI
    sta CHAR_INPUT_DRIVEN
    stz CHAR_HP
    stz CHAR_SELECTED
    lda #$FF
    sta CHAR_GRAB_TARGET
    sta CHAR_GRABBED_BY
    stz CHAR_GRAB_TIMER
    stz CHAR_PICKUP_TYPE
    lda #0
    sta.l G13_P2_InvulnFrames
    lda #0
    sta.l Entity1_ItemRosterIdx
    pld
    plx
    plp
    rtl
G13_DisableP2Session__done:
    plx
    plp
    rtl

; Select the nearest live player for the current AI actor.  Distance is the
; unsigned Manhattan distance in world X plus ground Y; ties retain slot 0.
; The result is shared by this actor's seek, movement, and hit pass during
; the current frame.  P2's context bridge is not involved because AI actors
; are never input-driven.
G13_AiChooseTarget:
    php
    phx
    phy
    rep #$31
.a16
.i16
    lda CHAR_POS_X
    sta.l G13_ContextSaveJump+0
    sep #$20
.a8
    lda CHAR_POS_Y
    sta.l G13_ContextSaveJump+2
    lda #0
    sta.l G13_ContextSaveJump+3
    sta.l G13_ContextSaveJump+9
    rep #$31
.a16
.i16
    lda #$FFFF
    sta.l G13_ContextSaveJump+4
    sep #$20
.a8
    lda #$FF
    sta.l G13_AiTargetSlot

    ; Candidate P1.
    lda.l PlayerEntity_Hp
    beq G13_AiChooseTarget__candidate1
    rep #$20
.a16
    lda.l PlayerEntity_PosX
    cmp.l G13_ContextSaveJump+0
    bcs G13_AiChooseTarget__p1_x_ge
    lda.l G13_ContextSaveJump+0
    sec
    sbc.l PlayerEntity_PosX
    bra G13_AiChooseTarget__p1_x_done
G13_AiChooseTarget__p1_x_ge:
    sec
    sbc.l G13_ContextSaveJump+0
G13_AiChooseTarget__p1_x_done:
    sta.l G13_ContextSaveJump+6
    sep #$20
.a8
    lda.l PlayerEntity_PosY
    cmp.l G13_ContextSaveJump+2
    bcs G13_AiChooseTarget__p1_y_ge
    lda.l G13_ContextSaveJump+2
    sec
    sbc.l PlayerEntity_PosY
    bra G13_AiChooseTarget__p1_y_done
G13_AiChooseTarget__p1_y_ge:
    sec
    sbc.l G13_ContextSaveJump+2
G13_AiChooseTarget__p1_y_done:
    sta.l G13_ContextSaveJump+8
    rep #$20
.a16
    lda.l G13_ContextSaveJump+6
    clc
    adc.l G13_ContextSaveJump+8
    sta.l G13_ContextSaveJump+4
    lda #0
    sta.l G13_AiTargetSlot

G13_AiChooseTarget__candidate1:
    sep #$20
.a8
    lda.l G13_TwoPlayerEnabled
    beq G13_AiChooseTarget__finish
    lda.l Entity1_InputDriven
    cmp #1
    bne G13_AiChooseTarget__finish
    lda.l Entity1_Hp
    beq G13_AiChooseTarget__finish
    rep #$20
.a16
    lda.l Entity1_PosX
    cmp.l G13_ContextSaveJump+0
    bcs G13_AiChooseTarget__p2_x_ge
    lda.l G13_ContextSaveJump+0
    sec
    sbc.l Entity1_PosX
    bra G13_AiChooseTarget__p2_x_done
G13_AiChooseTarget__p2_x_ge:
    sec
    sbc.l G13_ContextSaveJump+0
G13_AiChooseTarget__p2_x_done:
    sta.l G13_ContextSaveJump+6
    sep #$20
.a8
    lda.l Entity1_PosY
    cmp.l G13_ContextSaveJump+2
    bcs G13_AiChooseTarget__p2_y_ge
    lda.l G13_ContextSaveJump+2
    sec
    sbc.l Entity1_PosY
    bra G13_AiChooseTarget__p2_y_done
G13_AiChooseTarget__p2_y_ge:
    sec
    sbc.l G13_ContextSaveJump+2
G13_AiChooseTarget__p2_y_done:
    sta.l G13_ContextSaveJump+8
    rep #$20
.a16
    lda.l G13_ContextSaveJump+6
    clc
    adc.l G13_ContextSaveJump+8
    cmp.l G13_ContextSaveJump+4
    bcs G13_AiChooseTarget__finish
    sta.l G13_ContextSaveJump+4
    sep #$20
.a8
    lda #1
    sta.l G13_AiTargetSlot
G13_AiChooseTarget__finish:
    rep #$31
.a16
.i16
    lda.l G13_AiTargetSlot
    and #$00FF
    cmp #$00FF
    beq G13_AiChooseTarget__no_target
    cmp #$0000
    beq G13_AiChooseTarget__p1_result
    sep #$20
.a8
    lda #CHAR_ZP_LEN
    sta.l G13_AiTargetOffset
    rep #$20
.a16
    lda #CHAR_ZP_LEN
    sta.l G13_AiTargetOffset
    lda.l Entity1_PosX
    sta.l G13_AiTargetX
    sep #$20
.a8
    lda.l Entity1_PosY
    sta.l G13_AiTargetY
    bra G13_AiChooseTarget__return
G13_AiChooseTarget__p1_result:
    rep #$20
.a16
    lda #0
    sta.l G13_AiTargetOffset
    lda.l PlayerEntity_PosX
    sta.l G13_AiTargetX
    sep #$20
.a8
    lda.l PlayerEntity_PosY
    sta.l G13_AiTargetY
G13_AiChooseTarget__return:
    ply
    plx
    plp
    rtl
G13_AiChooseTarget__no_target:
    bra G13_AiChooseTarget__return

; Return carry set iff the current AI dispatch has a valid player target.
; Character_PlayFrame uses this before consuming the transient target X/Y;
; no-target deliberately leaves those coordinates stale for diagnostics.
G13_AiTargetValid:
    sep #$20
.a8
    lda.l G13_AiTargetSlot
    cmp #$FF
    beq G13_AiTargetValid__invalid
    sec
    rtl
G13_AiTargetValid__invalid:
    clc
    rtl

; G13 shared-camera target helper. Called by Core_Screen__SetTargetPosition
; with A/I 16-bit. It returns through the screen routine's carry contract;
; the normal screen clamp remains the sole owner of final bounds.
G13_Screen_SetTargetPosition:
    php
    rep #$31
.a16
.i16
    lda.l PlayerEntity_Hp
    beq G13_Screen_SetTargetPosition__p2
    lda.l Entity1_Hp
    beq G13_Screen_SetTargetPosition__p1
    lda.l PlayerEntity_PosX
    cmp.l Entity1_PosX
    bcs G13_Screen_SetTargetPosition__p2_min
    sta.l Screen__Half
    lda.l Entity1_PosX
    bra G13_Screen_SetTargetPosition__mid
G13_Screen_SetTargetPosition__p2_min:
    sta.l Screen__Half
    lda.l Entity1_PosX
G13_Screen_SetTargetPosition__mid:
    clc
    adc.l Screen__Half
    lsr a
    bra G13_Screen_SetTargetPosition__set_x
G13_Screen_SetTargetPosition__p1:
    lda.l PlayerEntity_PosX
    bra G13_Screen_SetTargetPosition__set_x
G13_Screen_SetTargetPosition__p2:
    lda.l Entity1_PosX
G13_Screen_SetTargetPosition__set_x:
	rep #$31
	.a16
	.i16
	pha
	lda Screen_SizeX
	lsr a
	sta Screen__Half
	pla
    sec
    sbc Screen__Half
    bcs G13_Screen_SetTargetPosition__x_ok
    lda #0
G13_Screen_SetTargetPosition__x_ok:
	rep #$31
	.a16
	.i16
    sta Screen_TargetX
    lda.l PlayerEntity_Hp
    beq G13_Screen_SetTargetPosition__y_p2
    lda.l PlayerEntity_PosY
    bra G13_Screen_SetTargetPosition__set_y
G13_Screen_SetTargetPosition__y_p2:
    lda.l Entity1_PosY
G13_Screen_SetTargetPosition__set_y:
	rep #$31
	.a16
	.i16
	pha
	lda Screen_SizeY
	lsr a
	sta Screen__Half
	pla
    sec
    sbc Screen__Half
    bcs G13_Screen_SetTargetPosition__y_ok
    lda #0
G13_Screen_SetTargetPosition__y_ok:
	rep #$31
	.a16
	.i16
    sta Screen_TargetY
    lda #SCREEN_MODE_GROUNDED
    sta Screen_Mode
    plp
    rtl

; Clamp the proposed player X in A to the current shared viewport.  Entry is
; in the actor's DP window and A16; the caller's D/DBR/stack remain intact.
; Non-player actors and one-player mode return the proposed coordinate
; unchanged.  This lives beside the shared-camera helper to keep the hot
; bank-0 movement path within its fixed arena.
G13_TetherPlayerX:
    php
    rep #$31
.a16
.i16
    sta.l G13_PickupTargetX
    lda.l G13_TwoPlayerEnabled
    and #$00FF
    beq G13_TetherPlayerX__unchanged
    tdc
    cmp #$0A00
    beq G13_TetherPlayerX__player
    cmp #$0A85
    bne G13_TetherPlayerX__unchanged
G13_TetherPlayerX__player:
	rep #$31
	.a16
	.i16
    lda.l G13_PickupTargetX
    cmp.l Screen_PosX
    bcs G13_TetherPlayerX__left_ok
    lda.l Screen_PosX
    clc
    adc #16
    bra G13_TetherPlayerX__upper
G13_TetherPlayerX__left_ok:
    lda.l G13_PickupTargetX
G13_TetherPlayerX__upper:
	rep #$31
	.a16
	.i16
    sta.l G13_PickupTargetX
    lda.l Screen_PosX
    clc
    adc Screen_SizeX
    sec
    sbc #32
    cmp.l G13_PickupTargetX
    bcs G13_TetherPlayerX__return
    sta.l G13_PickupTargetX
G13_TetherPlayerX__return:
    lda.l G13_PickupTargetX
    plp
    rtl
G13_TetherPlayerX__unchanged:
    lda.l G13_PickupTargetX
    plp
    rtl

; Run the existing production pickup overlap pass once for each live player.
; The pass itself remains unchanged apart from reading these explicit target
; coordinates and reward-owner selectors, so one-player mode is exactly the
; original single call and two-player mode cannot credit P2 to P1.
G13_Pickup_CheckPlayers:
    php
    phx
    phy
    rep #$31
.a16
.i16
    sep #$20
.a8
    lda #0
    sta.l G13_PickupForP2
    rep #$20
.a16
    lda.l PlayerEntity_PosX
    sta.l G13_PickupTargetX
    sep #$20
.a8
    lda.l PlayerEntity_PosY
    sta.l G13_PickupTargetY
    lda #0
    sta.l G13_PickupTargetY+1
    jsl Character_Pickup_CheckOverlap
    ; Character_Pickup_CheckOverlap returns A16/I16.  The mode and actor
    ; role below are byte-owned fields; restore the byte contract before
    ; testing the P2 collection path.
    sep #$20
.a8
    lda.l G13_TwoPlayerEnabled
    beq G13_Pickup_CheckPlayers__done
    lda.l Entity1_InputDriven
    cmp #1
    bne G13_Pickup_CheckPlayers__done
    lda.l Entity1_Hp
    beq G13_Pickup_CheckPlayers__done
    lda #1
    sta.l G13_PickupForP2
    rep #$20
.a16
    lda.l Entity1_PosX
    sta.l G13_PickupTargetX
    sep #$20
.a8
    lda.l Entity1_PosY
    sta.l G13_PickupTargetY
    lda #0
    sta.l G13_PickupTargetY+1
    jsl Character_Pickup_CheckOverlap
G13_Pickup_CheckPlayers__done:
    sep #$20
.a8
    lda #0
    sta.l G13_PickupForP2
    ply
    plx
    plp
    rtl

; One owner-aware score-add leaf for combat and pickups.  Entry is A16 with
; A=amount and G13_PickupForP2 selecting the owner (0=P1, 1=P2).  The owner
; selector is already bounded, non-reentrant pickup transaction state and is
; explicitly cleared by each transaction wrapper.  This preserves the
; original quotient-changed => exactly one extra-life contract for every
; score source, including money and gold.
G13_PlayerScore_Add:
    php
    phx
    phy
    rep #$31
.a16
.i16
    sta.l Game_ScoreAwardScratch
    lda.l G13_PickupForP2
    and #$00FF
    beq G13_PlayerScore_Add__p1
    lda.l G13_P2Score
    tax
    lda #EXTEND_LIFE_SCORE
    jsl G13_Core_Math_Div_Long
    sta.l Game_ScoreOldQuotientScratch
    lda.l G13_P2Score
    clc
    adc.l Game_ScoreAwardScratch
    bcc G13_PlayerScore_Add__p2_no_overflow
    lda #$FFFF
G13_PlayerScore_Add__p2_no_overflow:
    rep #$31
.a16
.i16
    sta.l G13_P2Score
    lda.l G13_P2Score
    tax
    lda #EXTEND_LIFE_SCORE
    jsl G13_Core_Math_Div_Long
    cmp.l Game_ScoreOldQuotientScratch
    beq G13_PlayerScore_Add__done
    sep #$20
.a8
    lda.l G13_P2Lives
    inc a
    sta.l G13_P2Lives
    bra G13_PlayerScore_Add__done
G13_PlayerScore_Add__p1:
    rep #$31
.a16
.i16
    lda.l Game_Score
    tax
    lda #EXTEND_LIFE_SCORE
    jsl G13_Core_Math_Div_Long
    sta.l Game_ScoreOldQuotientScratch
    lda.l Game_Score
    clc
    adc.l Game_ScoreAwardScratch
    bcc G13_PlayerScore_Add__p1_no_overflow
    lda #$FFFF
G13_PlayerScore_Add__p1_no_overflow:
    rep #$31
.a16
.i16
    sta.l Game_Score
    lda.l Game_Score
    tax
    lda #EXTEND_LIFE_SCORE
    jsl G13_Core_Math_Div_Long
    cmp.l Game_ScoreOldQuotientScratch
    beq G13_PlayerScore_Add__done
    sep #$20
.a8
    lda.l Game_Lives
    inc a
    sta.l Game_Lives
G13_PlayerScore_Add__done:
    ply
    plx
    plp
    rtl

; Combat wrapper: derive ownership from the dispatcher's actor DP, convert
; the kill flag to the established hit/kill amount, and route both players
; through the shared score/life semantics above.
G13_Game_Score_Award:
    php
    phx
    phy
    pha
    rep #$31
.a16
.i16
    tdc
    cmp #$0A85
    bne G13_Game_Score_Award__p1_owner
    sep #$20
.a8
    lda.l G13_TwoPlayerEnabled
    beq G13_Game_Score_Award__p1_owner
    lda #1
    sta.l G13_PickupForP2
    bra G13_Game_Score_Award__amount
G13_Game_Score_Award__p1_owner:
    sep #$20
.a8
    lda #0
    sta.l G13_PickupForP2
G13_Game_Score_Award__amount:
    pla
    rep #$31
.a16
.i16
    and #$00FF
    beq G13_Game_Score_Award__hit_only
    lda #HIT_SCORE + KILL_SCORE
    bra G13_Game_Score_Award__add
G13_Game_Score_Award__hit_only:
    rep #$31
.a16
.i16
    lda #HIT_SCORE
G13_Game_Score_Award__add:
    jsl G13_PlayerScore_Add
    sep #$20
.a8
    lda #0
    sta.l G13_PickupForP2
    ply
    plx
    plp
    rtl
