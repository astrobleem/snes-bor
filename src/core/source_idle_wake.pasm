; Admission only: attack keeps priority, then accepted idle0 after a
; completed walking picture, ahead of a lagging grounded native mirror.
; Only one existing loader visit. No physics/input/OAM/Ready writes.
SourceIdleWake_Role = $7E46FA
SourceIdleWake_Admission:
.a16
.i16
    php
    rep #$30
    pha
    jsl SourceWarm_ReadAttack
    bcc SourceIdleWake_Admission__walk
    lda.l SourceWarm_Frame
    sta.l SourceIdleWake_Frame
    lda #2
    sta.l SourceIdleWake_Role
    pla
    plp
    sec
    rtl
SourceIdleWake_Admission__walk:
.a16
.i16
    pla
    plp
    jml SourceIdleWake_ReadIdle
; Read-only source admission hint. Never sample buttons, simulate an action,
; emit OAM, acknowledge DMA, change native actor/world fields, or take a lease.
; Existing one-job wait scheduler and normal loader/retirement stay authoritative.
SourceIdleWake_Slot = $7E46EE
SourceIdleWake_Seq = $7E46F0
SourceIdleWake_Frame = $7E46F2
SourceIdleWake_Stage = $7E46F4
SourceIdleWake_Row = $7E46F6
SourceIdleWake_Native = $7E46F8
SourceIdleWake_ReadIdle:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    phd
    and #$00FF
    cmp #2
    bcc SourceIdleWake_ReadIdle__slot
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__slot:
.a16
.i16
    pha
    lda.l $7E46DE ; S6Normal_NmiContext: never expand work inside NMI
    cmp #0
    beq SourceIdleWake_ReadIdle__foreground
    brl SourceIdleWake_ReadIdle__pop_miss
SourceIdleWake_ReadIdle__foreground:
.a16
.i16
    jsr SourceNpc_Scope
    bcs SourceIdleWake_ReadIdle__scope
    brl SourceIdleWake_ReadIdle__pop_miss
SourceIdleWake_ReadIdle__scope:
.a16
.i16
    lda.l $7E0000+2560+CHAR_HP
    and #$00FF
    beq SourceIdleWake_ReadIdle__no_jump0
    lda.l $7E0000+2560+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    bne SourceIdleWake_ReadIdle__no_jump0
    lda.l $7E0000+2560+CHAR_SELECTED
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
    bne SourceIdleWake_ReadIdle__no_jump0
    brl SourceIdleWake_ReadIdle__pop_miss
SourceIdleWake_ReadIdle__no_jump0:
.a16
.i16
    lda.l $7E0000+2693+CHAR_HP
    and #$00FF
    beq SourceIdleWake_ReadIdle__no_jump1
    lda.l $7E0000+2693+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    bne SourceIdleWake_ReadIdle__no_jump1
    lda.l $7E0000+2693+CHAR_SELECTED
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
    bne SourceIdleWake_ReadIdle__no_jump1
    brl SourceIdleWake_ReadIdle__pop_miss
SourceIdleWake_ReadIdle__no_jump1:
.a16
.i16
    lda.l SVActor_LoadOwner
    cmp #3
    bcc SourceIdleWake_ReadIdle__no_first_npc
    cmp #7
    bcs SourceIdleWake_ReadIdle__no_first_npc
    dec a
    dec a
    asl a
    tax
    lda.l SVActor_Bases,x
    tax
    lda.l SVActor_Data+SVActor_Valid,x
    cmp #1
    beq SourceIdleWake_ReadIdle__no_first_npc
    brl SourceIdleWake_ReadIdle__pop_miss
SourceIdleWake_ReadIdle__no_first_npc:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    beq SourceIdleWake_ReadIdle__motion
    brl SourceIdleWake_ReadIdle__pop_miss
SourceIdleWake_ReadIdle__motion:
.a16
.i16
    lda.l $434E7C
    and #1
    beq SourceIdleWake_ReadIdle__even
    brl SourceIdleWake_ReadIdle__pop_miss
SourceIdleWake_ReadIdle__even:
.a16
.i16
    pla
    sta.l SourceIdleWake_Slot
    lda.l $434E7C
    sta.l SourceIdleWake_Seq
    and #1
    beq SourceIdleWake_ReadIdle__seq
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__seq:
.a16
.i16
    lda.l $434E2C
    sta.l SourceIdleWake_Stage
    cmp.l Game_StageIndex
    beq SourceIdleWake_ReadIdle__stage
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__stage:
.a16
.i16
    lda.l SourceIdleWake_Slot
    asl a
    tax
    lda.l SourceIdleWake_Rows,x
    sta.l SourceIdleWake_Row
    lda.l SourceIdleWake_Natives,x
    sta.l SourceIdleWake_Native
    tax
    lda.l $7E0A00+CHAR_HP,x
    and #$00FF
    bne SourceIdleWake_ReadIdle__native0
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__native0:
.a16
.i16
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    and #$00FF
    cmp #1
    beq SourceIdleWake_ReadIdle__native1
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__native1:
.a16
.i16
    lda.l $7E0A00+CHAR_ROSTER_INDEX,x
    and #$00FF
    cmp #22
    beq SourceIdleWake_ReadIdle__native2
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__native2:
.a16
.i16
    lda.l $7E0A00+CHAR_MAP_INDEX,x
    and #$00FF
    beq SourceIdleWake_ReadIdle__native3
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__native3:
.a16
.i16
    lda.l $7E0A00+CHAR_SELECTED,x
    and #$00FF
    cmp #3
    bcc SourceIdleWake_ReadIdle__native4
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__native4:
.a16
.i16
    lda.l StageBounds_State,x
    beq SourceIdleWake_ReadIdle__native5
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__native5:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy,x
    and #$00FF
    cmp #2
    beq SourceIdleWake_ReadIdle__native6
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__native6:
.a16
.i16
    lda.l SourceVisual_Sa1RuntimeRole,x
    and #$00FF
    cmp #2
    bcc SourceIdleWake_ReadIdle__native7
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__native7:
.a16
.i16
    lda.l SourceIdleWake_Slot
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_State+6,x
    bne SourceIdleWake_ReadIdle__desired0
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__desired0:
.a16
.i16
    cmp #3
    bcc SourceIdleWake_ReadIdle__desired1
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__desired1:
.a16
.i16
    lda.l SourceVisual_State+30,x
    and #$00FF
    cmp #2
    bcc SourceIdleWake_ReadIdle__desired2
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__desired2:
.a16
.i16
    lda.l SourceIdleWake_Slot
    bne SourceIdleWake_ReadIdle__p2
    lda.l SourceVisual_CompletedValid
    cmp #1
    beq SourceIdleWake_ReadIdle__p10
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__p10:
.a16
.i16
    lda.l SourceVisual_CompletedStage
    cmp.l Game_StageIndex
    beq SourceIdleWake_ReadIdle__p11
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__p11:
.a16
.i16
    lda.l SourceVisual_CompletedRoster
    cmp #22
    beq SourceIdleWake_ReadIdle__p12
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__p12:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+1
    and #$00FF
    cmp #1
    beq SourceIdleWake_ReadIdle__p13
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__p13:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+12
    and #$00FF
    bne SourceIdleWake_ReadIdle__p14
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__p14:
.a16
.i16
    cmp #66
    bcc SourceIdleWake_ReadIdle__p15
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__p15:
.a16
.i16
    brl SourceIdleWake_ReadIdle__read
SourceIdleWake_ReadIdle__p2:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourceIdleWake_ReadIdle__p20
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__p20:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage
    cmp.l Game_StageIndex
    beq SourceIdleWake_ReadIdle__p21
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__p21:
.a16
.i16
    lda.l SVActor_Data+SVActor_Roster
    cmp #22
    beq SourceIdleWake_ReadIdle__p22
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__p22:
.a16
.i16
    lda.l SVActor_Data+1
    and #$00FF
    cmp #1
    beq SourceIdleWake_ReadIdle__p23
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__p23:
.a16
.i16
    lda.l SVActor_Data+12
    and #$00FF
    bne SourceIdleWake_ReadIdle__p24
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__p24:
.a16
.i16
    cmp #66
    bcc SourceIdleWake_ReadIdle__p25
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__p25:
.a16
.i16
    brl SourceIdleWake_ReadIdle__read
SourceIdleWake_ReadIdle__read:
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
    lda.l SourceIdleWake_Row
    tay
    lda.w $4E40,y
    cmp #1
    beq SourceIdleWake_ReadIdle__row0
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__row0:
.a16
.i16
    lda.w $4E42,y
    beq SourceIdleWake_ReadIdle__row1
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__row1:
.a16
.i16
    lda.w $4E44,y
    bne SourceIdleWake_ReadIdle__row2
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__row2:
.a16
.i16
    cmp #256
    bcc SourceIdleWake_ReadIdle__row3
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__row3:
.a16
.i16
    lda.w $4E3C,y
    cmp #9
    beq SourceIdleWake_ReadIdle__row4
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__row4:
.a16
.i16
    lda.w $4E4A,y
    and #$00FF
    cmp #2
    beq SourceIdleWake_ReadIdle__row5
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__row5:
.a16
.i16
    lda.w $4E4B,y
    and #$00FF
    cmp #1
    beq SourceIdleWake_DriverOK
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_DriverOK:
.a16
.i16
    lda.w $4E50,y
    and #$00FF
    cmp #0
    beq SourceIdleWake_ReadIdle__row6
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__row6:
.a16
.i16
    lda.w $4E54,y
    and #$00FF
    cmp #8
    beq SourceIdleWake_ReadIdle__row7
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__row7:
.a16
.i16
    lda.w $4E4E,y
    and #$00FF
    cmp #18
    bcc SourceIdleWake_ReadIdle__row8
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__row8:
.a16
.i16
    sta.l SourceIdleWake_Frame
    lda.l SourceIdleWake_Slot
    asl a
    tax
    lda.l $434E9C,x
    cmp.l SourceIdleWake_Native
    beq SourceIdleWake_ReadIdle__binding
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__binding:
.a16
.i16
    lda.l $434E7C
    cmp.l SourceIdleWake_Seq
    beq SourceIdleWake_ReadIdle__same_seq
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__same_seq:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    beq SourceIdleWake_ReadIdle__same_magic
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__same_magic:
.a16
.i16
    lda.l SourceIdleWake_Stage
    cmp.l Game_StageIndex
    beq SourceIdleWake_ReadIdle__same_stage
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_ReadIdle__same_stage:
.a16
.i16
SourceIdleWake_ReadIdle__hit:
.a16
.i16
    lda #0
    sta.l SourceIdleWake_Role
    sta.l SourceIdleWake_Frame
    rep #$30
    pld
    plb
    ply
    plx
    pla
    plp
    sec
    rtl
SourceIdleWake_ReadIdle__miss:
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
SourceIdleWake_ReadIdle__pop_miss:
.a16
.i16
    pla
    brl SourceIdleWake_ReadIdle__miss
SourceIdleWake_Rows:
    .dw 0,36
SourceIdleWake_Natives:
    .dw 0,133

; The existing selector has already exhausted both attack candidates, or
; excluded jumps/unseen owner. ReadIdle independently rechecks those guards.
; Reuse one existing loader slot; preserve its current P2 producer preference.
SourceIdleWake_FirstIdle:
.a16
.i16
    lda.l SVActor_LoadOwner
    cmp #2
    beq SourceIdleWake_FirstIdle__p2first
    lda #0
    jsl SourceIdleWake_ReadIdle
    bcs SourceIdleWake_FirstIdle__p1yes
    lda #1
    jsl SourceIdleWake_ReadIdle
    bcs SourceIdleWake_FirstIdle__p2yes
    bra SourceIdleWake_FirstIdle__none
SourceIdleWake_FirstIdle__p2first:
.a16
.i16
    lda #1
    jsl SourceIdleWake_ReadIdle
    bcs SourceIdleWake_FirstIdle__p2yes
    lda #0
    jsl SourceIdleWake_ReadIdle
    bcs SourceIdleWake_FirstIdle__p1yes
SourceIdleWake_FirstIdle__none:
.a16
.i16
    lda #0
    clc
    rtl
SourceIdleWake_FirstIdle__p1yes:
.a16
.i16
    lda #2560
    sec
    rtl
SourceIdleWake_FirstIdle__p2yes:
.a16
.i16
    lda #2693
    sec
    rtl
SourceIdleWake_End:
