; Read-only source admission hint. Never sample buttons, simulate an action,
; emit OAM, acknowledge DMA, change native actor/world fields, or take a lease.
; Existing one-job wait scheduler and normal loader/retirement stay authoritative.
SourceWarm_Slot = $7EEFD4
SourceWarm_Seq = $7EEFD6
SourceWarm_Frame = $7EEFD8
SourceWarm_Stage = $7EEFDA
SourceWarm_Row = $7EEFDC
SourceWarm_Native = $7EEFDE
SourceWarm_Mode = $7EEFFA ; overwritten after foreground check before every use
; Public entry preserves the original full accumulator, including high byte.
SourceWarm_ReadAttack:
.a16
.i16
    php
    rep #$30
    pha
    and #$00FF
    jsl SourceWarm_ReadCommon
    bcc SourceWarm_ReadEntry__no
    bra SourceWarm_ReadEntry__yes
SourceWarm_ReadIdle:
.a16
.i16
    php
    rep #$30
    pha
    and #$00FF
    ora #$0100
    jsl SourceWarm_ReadCommon
    bcc SourceWarm_ReadEntry__no
SourceWarm_ReadEntry__yes:
.a16
.i16
    pla
    plp
    sec
    rtl
SourceWarm_ReadEntry__no:
.a16
.i16
    pla
    plp
    clc
    rtl
SourceWarm_ReadCommon:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    phd
    pha
    lda.l $7E46DE
    beq SourceWarm_ReadCommon__foreground
    pla
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadCommon__foreground:
.a16
.i16
    pla
    pha
    and #$0100
    beq SourceWarm_ReadCommon__attack
    lda #0
    bra SourceWarm_ReadCommon__mode
SourceWarm_ReadCommon__attack:
.a16
.i16
    lda #2
SourceWarm_ReadCommon__mode:
.a16
.i16
    sta.l SourceWarm_Mode
    pla
    and #$00FF
    cmp #2
    bcc SourceWarm_ReadAttack__slot
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__slot:
.a16
.i16
    pha
SourceWarm_ReadAttack__foreground:
.a16
.i16
    jsr SourceNpc_Scope
    bcs SourceWarm_ReadAttack__scope
    brl SourceWarm_ReadAttack__pop_miss
SourceWarm_ReadAttack__scope:
.a16
.i16
    lda.l SourceWarm_Mode
    bne SourceWarm_ReadCommon__idle_buttons_ok
    ; Idle admission never competes with a currently cached player control.
    ; Read existing cached words only; do not poll or modify input history.
    lda.l Input_press_Addr
    ora.l Input2_press_Addr
    beq SourceWarm_ReadCommon__idle_buttons_ok
    brl SourceWarm_ReadAttack__pop_miss
SourceWarm_ReadCommon__idle_buttons_ok:
.a16
.i16
    lda.l $7E0000+2560+CHAR_HP
    and #$00FF
    beq SourceWarm_ReadAttack__no_jump0
    lda.l $7E0000+2560+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    bne SourceWarm_ReadAttack__no_jump0
    lda.l $7E0000+2560+CHAR_SELECTED
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
    bne SourceWarm_ReadAttack__no_jump0
    brl SourceWarm_ReadAttack__pop_miss
SourceWarm_ReadAttack__no_jump0:
.a16
.i16
    lda.l $7E0000+2693+CHAR_HP
    and #$00FF
    beq SourceWarm_ReadAttack__no_jump1
    lda.l $7E0000+2693+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    bne SourceWarm_ReadAttack__no_jump1
    lda.l $7E0000+2693+CHAR_SELECTED
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
    bne SourceWarm_ReadAttack__no_jump1
    brl SourceWarm_ReadAttack__pop_miss
SourceWarm_ReadAttack__no_jump1:
.a16
.i16
    lda.l SVActor_LoadOwner
    cmp #3
    bcc SourceWarm_ReadAttack__no_first_npc
    cmp #7
    bcs SourceWarm_ReadAttack__no_first_npc
    dec a
    dec a
    asl a
    tax
    lda.l SVActor_Bases,x
    tax
    lda.l SVActor_Data+SVActor_Valid,x
    cmp #1
    beq SourceWarm_ReadAttack__no_first_npc
    brl SourceWarm_ReadAttack__pop_miss
SourceWarm_ReadAttack__no_first_npc:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    beq SourceWarm_ReadAttack__motion
    brl SourceWarm_ReadAttack__pop_miss
SourceWarm_ReadAttack__motion:
.a16
.i16
    lda.l $434E7C
    and #1
    beq SourceWarm_ReadAttack__even
    brl SourceWarm_ReadAttack__pop_miss
SourceWarm_ReadAttack__even:
.a16
.i16
    pla
    sta.l SourceWarm_Slot
    lda.l $434E7C
    sta.l SourceWarm_Seq
    and #1
    beq SourceWarm_ReadAttack__seq
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__seq:
.a16
.i16
    lda.l $434E2C
    sta.l SourceWarm_Stage
    cmp.l Game_StageIndex
    beq SourceWarm_ReadAttack__stage
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__stage:
.a16
.i16
    lda.l SourceWarm_Slot
    asl a
    tax
    lda.l SourceWarm_Rows,x
    sta.l SourceWarm_Row
    lda.l SourceWarm_Natives,x
    sta.l SourceWarm_Native
    tax
    lda.l $7E0A00+CHAR_HP,x
    and #$00FF
    bne SourceWarm_ReadAttack__native0
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__native0:
.a16
.i16
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    and #$00FF
    cmp #1
    beq SourceWarm_ReadAttack__native1
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__native1:
.a16
.i16
    lda.l $7E0A00+CHAR_ROSTER_INDEX,x
    and #$00FF
    cmp #22
    beq SourceWarm_ReadAttack__native2
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__native2:
.a16
.i16
    lda.l $7E0A00+CHAR_MAP_INDEX,x
    and #$00FF
    beq SourceWarm_ReadAttack__native3
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__native3:
.a16
.i16
    lda.l $7E0A00+CHAR_SELECTED,x
    and #$00FF
    cmp #3
    bcc SourceWarm_ReadAttack__native4
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__native4:
.a16
.i16
    lda.l StageBounds_State,x
    beq SourceWarm_ReadAttack__native5
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__native5:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy,x
    and #$00FF
    cmp #2
    beq SourceWarm_ReadAttack__native6
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__native6:
.a16
.i16
    lda.l SourceVisual_Sa1RuntimeRole,x
    and #$00FF
    jsr SourceWarm_CheckNativeRole
    bcc SourceWarm_ReadAttack__native7
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__native7:
.a16
.i16
    lda.l SourceWarm_Slot
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_State+6,x
    bne SourceWarm_ReadAttack__desired0
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__desired0:
.a16
.i16
    cmp #3
    bcc SourceWarm_ReadAttack__desired1
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__desired1:
.a16
.i16
    lda.l SourceVisual_State+30,x
    and #$00FF
    cmp #2
    bcc SourceWarm_ReadAttack__desired2
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__desired2:
.a16
.i16
    lda.l SourceWarm_Slot
    bne SourceWarm_ReadAttack__p2
    lda.l SourceVisual_CompletedValid
    cmp #1
    beq SourceWarm_ReadAttack__p10
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__p10:
.a16
.i16
    lda.l SourceVisual_CompletedStage
    cmp.l Game_StageIndex
    beq SourceWarm_ReadAttack__p11
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__p11:
.a16
.i16
    lda.l SourceVisual_CompletedRoster
    cmp #22
    beq SourceWarm_ReadAttack__p12
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__p12:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+1
    and #$00FF
    jsr SourceWarm_CheckPriorRole
    bcs SourceWarm_ReadAttack__p13
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__p13:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+12
    and #$00FF
    bne SourceWarm_ReadAttack__p14
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__p14:
.a16
.i16
    cmp #66
    bcc SourceWarm_ReadAttack__p15
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__p15:
.a16
.i16
    brl SourceWarm_ReadAttack__read
SourceWarm_ReadAttack__p2:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourceWarm_ReadAttack__p20
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__p20:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage
    cmp.l Game_StageIndex
    beq SourceWarm_ReadAttack__p21
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__p21:
.a16
.i16
    lda.l SVActor_Data+SVActor_Roster
    cmp #22
    beq SourceWarm_ReadAttack__p22
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__p22:
.a16
.i16
    lda.l SVActor_Data+1
    and #$00FF
    jsr SourceWarm_CheckPriorRole
    bcs SourceWarm_ReadAttack__p23
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__p23:
.a16
.i16
    lda.l SVActor_Data+12
    and #$00FF
    bne SourceWarm_ReadAttack__p24
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__p24:
.a16
.i16
    cmp #66
    bcc SourceWarm_ReadAttack__p25
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__p25:
.a16
.i16
    brl SourceWarm_ReadAttack__read
SourceWarm_ReadAttack__read:
.a16
.i16
    sep #$20
.a8
    lda #$43
    pha
    plb
    rep #$30
.a16
.i16
    lda.l SourceWarm_Row
    tay
    lda.w $4E40,y
    cmp #1
    beq SourceWarm_ReadAttack__row0
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__row0:
.a16
.i16
    lda.w $4E42,y
    beq SourceWarm_ReadAttack__row1
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__row1:
.a16
.i16
    lda.w $4E44,y
    bne SourceWarm_ReadAttack__row2
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__row2:
.a16
.i16
    cmp #256
    bcc SourceWarm_ReadAttack__row3
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__row3:
.a16
.i16
    lda.w $4E3C,y
    beq SourceWarm_ReadAttack__row4
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__row4:
.a16
.i16
    lda.w $4E4A,y
    and #$00FF
    cmp #2 ; source ownership policy stays SA-1 for attack AND idle
    beq SourceWarm_ReadAttack__row5
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__row5:
.a16
.i16
    lda.w $4E50,y
    and #$00FF
    cmp.l SourceWarm_Mode
    beq SourceWarm_ReadAttack__row6
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__row6:
.a16
.i16
    lda.w $4E54,y
    and #$00FF
    sec
    sbc #8
    asl a
    cmp.l SourceWarm_Mode
    beq SourceWarm_ReadAttack__row7
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__row7:
.a16
.i16
    lda.w $4E4E,y
    and #$00FF
    cmp #6
    bcc SourceWarm_ReadAttack__row8
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__row8:
.a16
.i16
    sta.l SourceWarm_Frame
    lda.l SourceWarm_Slot
    asl a
    tax
    lda.l $434E9C,x
    cmp.l SourceWarm_Native
    beq SourceWarm_ReadAttack__binding
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__binding:
.a16
.i16
    lda.l $434E7C
    cmp.l SourceWarm_Seq
    beq SourceWarm_ReadAttack__same_seq
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__same_seq:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    beq SourceWarm_ReadAttack__same_magic
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__same_magic:
.a16
.i16
    lda.l SourceWarm_Stage
    cmp.l Game_StageIndex
    beq SourceWarm_ReadAttack__same_stage
    brl SourceWarm_ReadAttack__miss
SourceWarm_ReadAttack__same_stage:
.a16
.i16
    lda.l SourceWarm_Mode
    bne SourceWarm_ReadAttack__hit
    brl SourceWarm_ReadIdle__hit
SourceWarm_ReadAttack__hit:
.a16
.i16
    rep #$30
    pld
    plb
    ply
    plx
    pla
    plp
    sec
    rtl
SourceWarm_ReadIdle__hit:
.a16
.i16
    rep #$30
    pld
    plb
    ply
    plx
    pla
    plp
    sec
    rtl
SourceWarm_ReadAttack__miss:
.a16
.i16
    rep #$30
    pld
    plb
    ply
    plx
    pla
    plp
    clc
    rtl
SourceWarm_ReadAttack__pop_miss:
.a16
.i16
    pla
    brl SourceWarm_ReadAttack__miss
SourceWarm_Rows:
    .dw 0,36
SourceWarm_Natives:
    .dw 0,133

; For accepted idle, only a previously displayed walk picture qualifies.
; An unfinished or displayed attack/jump cannot be superseded by this hint.
SourceWarm_CheckPriorRole:
.a16
.i16
    cmp #2
    bcs SourceWarm_CheckPriorRole__no
    pha
    lda.l SourceWarm_Mode
    bne SourceWarm_CheckPriorRole__any
    pla
    cmp #1
    bne SourceWarm_CheckPriorRole__no
    sec
    rts
SourceWarm_CheckPriorRole__any:
.a16
.i16
    pla
    sec
    rts
SourceWarm_CheckPriorRole__no:
.a16
.i16
    clc
    rts
SourceWarm_CheckNativeRole:
.a16
.i16
    pha
    lda.l SourceWarm_Mode
    beq SourceWarm_CheckNativeRole__idle
    pla
    cmp #3
    rts
SourceWarm_CheckNativeRole__idle:
.a16
.i16
    pla
    cmp #2
    rts

; Replace only an unfinished player WALK lease with the accepted IDLE key.
; Existing replacement DMA fence and completed/retiring leases remain in force.
SourceWarm_IdleCanReplace:
.a16
.i16
    php
    rep #$30
    pha
    phx
    lda.l SourceVisual_ServiceOnly
    cmp #1
    bne SourceWarm_IdleCanReplace__no
    lda.l SourceVisual_Key+1
    and #$00FF
    bne SourceWarm_IdleCanReplace__no
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+30,x
    and #$00FF
    cmp #1
    bne SourceWarm_IdleCanReplace__no
    lda.l SourceVisual_ActorSlot
    cmp #2
    bcs SourceWarm_IdleCanReplace__no
    jsl SourceWarm_ReadIdle
    bcc SourceWarm_IdleCanReplace__no
    lda.l SourceVisual_Key+2
    and #$00FF
    cmp.l SourceWarm_Frame
    bne SourceWarm_IdleCanReplace__no
    plx
    pla
    plp
    sec
    rtl
SourceWarm_IdleCanReplace__no:
.a16
.i16
    plx
    pla
    plp
    clc
    rtl
