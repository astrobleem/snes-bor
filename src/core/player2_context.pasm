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

; Fixed pre-game session entry. Called from the character-select WAIT state
; when JOY2 Start has an edge. Slot 1 already owns its accepted OBJ palette
; and tile allocation from boot; this changes only its player role and loads
; the fixed LEO roster record through the ordinary production loader.
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
    jmp G13_EnableP2Session__init_slot

G13_EnableP2Session__already_enabled:
    jmp G13_EnableP2Session__done

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
    beq G13_EnsureP2AfterStage__done

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
    lda #12                         ; fixed preselected LEO roster entry
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
    lda #12
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

; G13 score leaf. It lives with the P2 context helpers so the tight bank-0
; gameplay region retains its layout margin. Entry is A8; it returns RTL.
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
    beq G13_Game_Score_Award__p2
    sep #$20
.a8
    pla
    bra G13_Game_Score_Award__original
G13_Game_Score_Award__p2:
    sep #$20
.a8
    pla
    jsl G13_P2Score_Award
    ply
    plx
    plp
    rtl
G13_Game_Score_Award__original:
    rep #$31
.a16
.i16
    and #$00FF
    beq G13_Game_Score_Award__hit_only
    lda #HIT_SCORE + KILL_SCORE
    bra G13_Game_Score_Award__have_award
G13_Game_Score_Award__hit_only:
    lda #HIT_SCORE
G13_Game_Score_Award__have_award:
    sta.l Game_ScoreAwardScratch
    lda.l Game_Score
    tax
    lda #EXTEND_LIFE_SCORE
    jsl G13_Core_Math_Div_Long
    sta.l Game_ScoreOldQuotientScratch
    lda.l Game_Score
    clc
    adc.l Game_ScoreAwardScratch
    bcc G13_Game_Score_Award__no_overflow
    lda #$FFFF
G13_Game_Score_Award__no_overflow:
    sta.l Game_Score
    lda.l Game_Score
    tax
    lda #EXTEND_LIFE_SCORE
    jsl G13_Core_Math_Div_Long
    cmp.l Game_ScoreOldQuotientScratch
    beq G13_Game_Score_Award__done
    sep #$20
.a8
    lda.l Game_Lives
    inc a
    sta.l Game_Lives
G13_Game_Score_Award__done:
    ply
    plx
    plp
    rtl

; P2-owned combat score leaf. The dispatcher preserves the caller's kill
; flag in A while selecting this actor-owned path.
G13_P2Score_Award:
    php
    phx
    phy
    rep #$31
.a16
.i16
    and #$00FF
    beq G13_P2Score_Award__hit
    lda #HIT_SCORE + KILL_SCORE
    bra G13_P2Score_Award__add
G13_P2Score_Award__hit:
    lda #HIT_SCORE
G13_P2Score_Award__add:
    clc
    adc.l G13_P2Score
    bcc G13_P2Score_Award__store
    lda #$FFFF
G13_P2Score_Award__store:
    sta.l G13_P2Score
    ply
    plx
    plp
    rtl
