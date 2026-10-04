; Shared grounded P1 reset for stage, stock and continue boundaries.
; Kept out of the full bank-0 runtime; all data accesses are absolute-long.
Game_State_RespawnPlayer_Long:
    sep #$20
.a8
    lda #CHAR_HP_MAX
    sta.l PlayerEntity_Hp
    lda #0
    sta.l PlayerEntity_HitStun
    sta.l G13_P1Out
    lda.l Stage_ScrollDirection
    lsr a
    sta.l PlayerEntity_FacingLeft
    sta.l PlayerEntity_Selected
    lda #$FF
    sta.l PlayerEntity_FrameIndex
    lda #1
    sta.l PlayerEntity_TickCounter
    lda #PLAYER_RESPAWN_INVULN_FRAMES
    sta.l Player_InvulnFrames
    lda #0
    sta.l Player_JumpAnimMode
    sta.l Player_JumpFCount
    rep #$31
.a16
    lda #PLAYER_RESPAWN_Y
    sta.l PlayerEntity_PosY
    ; Clear the complete Y word: a prior source projection can leave a high
    ; byte that an eight-bit reset would import into the next source world.
    ; This reset selects a grounded player state.  Clear both complete Q8.8
    ; words so a prior jump cannot survive the stage/death respawn boundary.
    lda #0
    sta.l $7E0A00+CHAR_THROW_ZPOS
    sta.l $7E0A00+CHAR_THROW_ZVEL
    jsl Stage_RespawnP1Position
    rtl
