; Admission only: existing attack hint has priority, then exact accepted
; first walk0 ahead of an idle native mirror. No physics/input/OAM/DMA writes.
SourceGround_Role = $7E46FA
SourceGround_Admission:
.a16
.i16
    php
    rep #$30
    pha
    jsl SourceWarm_ReadAttack
    bcc SourceGround_Admission__walk
    lda.l SourceWarm_Frame
    sta.l SourceGround_Frame
    lda #2
    sta.l SourceGround_Role
    pla
    plp
    sec
    rtl
SourceGround_Admission__walk:
.a16
.i16
    pla
    plp
    jml SourceGround_ReadWalk
; Read-only source admission hint. Never sample buttons, simulate an action,
; emit OAM, acknowledge DMA, change native actor/world fields, or take a lease.
; Existing one-job wait scheduler and normal loader/retirement stay authoritative.
SourceGround_Slot = $7E46EE
SourceGround_Seq = $7E46F0
SourceGround_Frame = $7E46F2
SourceGround_Stage = $7E46F4
SourceGround_Row = $7E46F6
SourceGround_Native = $7E46F8
SourceGround_ReadWalk:
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
    bcc SourceGround_ReadWalk__slot
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__slot:
.a16
.i16
    pha
    lda.l $7E46DE ; S6Normal_NmiContext: never expand work inside NMI
    cmp #0
    beq SourceGround_ReadWalk__foreground
    brl SourceGround_ReadWalk__pop_miss
SourceGround_ReadWalk__foreground:
.a16
.i16
    jsr SourceNpc_Scope
    bcs SourceGround_ReadWalk__scope
    brl SourceGround_ReadWalk__pop_miss
SourceGround_ReadWalk__scope:
.a16
.i16
    lda.l $7E0000+2560+CHAR_HP
    and #$00FF
    beq SourceGround_ReadWalk__no_jump0
    lda.l $7E0000+2560+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    bne SourceGround_ReadWalk__no_jump0
    lda.l $7E0000+2560+CHAR_SELECTED
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
    bne SourceGround_ReadWalk__no_jump0
    brl SourceGround_ReadWalk__pop_miss
SourceGround_ReadWalk__no_jump0:
.a16
.i16
    lda.l $7E0000+2693+CHAR_HP
    and #$00FF
    beq SourceGround_ReadWalk__no_jump1
    lda.l $7E0000+2693+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    bne SourceGround_ReadWalk__no_jump1
    lda.l $7E0000+2693+CHAR_SELECTED
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
    bne SourceGround_ReadWalk__no_jump1
    brl SourceGround_ReadWalk__pop_miss
SourceGround_ReadWalk__no_jump1:
.a16
.i16
    lda.l SVActor_LoadOwner
    cmp #3
    bcc SourceGround_ReadWalk__no_first_npc
    cmp #7
    bcs SourceGround_ReadWalk__no_first_npc
    dec a
    dec a
    asl a
    tax
    lda.l SVActor_Bases,x
    tax
    lda.l SVActor_Data+SVActor_Valid,x
    cmp #1
    beq SourceGround_ReadWalk__no_first_npc
    brl SourceGround_ReadWalk__pop_miss
SourceGround_ReadWalk__no_first_npc:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    beq SourceGround_ReadWalk__motion
    brl SourceGround_ReadWalk__pop_miss
SourceGround_ReadWalk__motion:
.a16
.i16
    lda.l $434E7C
    and #1
    beq SourceGround_ReadWalk__even
    brl SourceGround_ReadWalk__pop_miss
SourceGround_ReadWalk__even:
.a16
.i16
    pla
    sta.l SourceGround_Slot
    lda.l $434E7C
    sta.l SourceGround_Seq
    and #1
    beq SourceGround_ReadWalk__seq
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__seq:
.a16
.i16
    lda.l $434E2C
    sta.l SourceGround_Stage
    cmp.l Game_StageIndex
    beq SourceGround_ReadWalk__stage
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__stage:
.a16
.i16
    lda.l SourceGround_Slot
    asl a
    tax
    lda.l SourceGround_Rows,x
    sta.l SourceGround_Row
    lda.l SourceGround_Natives,x
    sta.l SourceGround_Native
    tax
    lda.l $7E0A00+CHAR_HP,x
    and #$00FF
    bne SourceGround_ReadWalk__native0
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__native0:
.a16
.i16
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    and #$00FF
    cmp #1
    beq SourceGround_ReadWalk__native1
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__native1:
.a16
.i16
    lda.l $7E0A00+CHAR_ROSTER_INDEX,x
    and #$00FF
    cmp #22
    beq SourceGround_ReadWalk__native2
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__native2:
.a16
.i16
    lda.l $7E0A00+CHAR_MAP_INDEX,x
    and #$00FF
    beq SourceGround_ReadWalk__native3
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__native3:
.a16
.i16
    lda.l $7E0A00+CHAR_SELECTED,x
    and #$00FF
    cmp #3
    bcc SourceGround_ReadWalk__native4
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__native4:
.a16
.i16
    lda.l StageBounds_State,x
    beq SourceGround_ReadWalk__native5
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__native5:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy,x
    and #$00FF
    cmp #2
    beq SourceGround_ReadWalk__native6
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__native6:
.a16
.i16
    lda.l SourceVisual_Sa1RuntimeRole,x
    and #$00FF
    cmp #0
    beq SourceGround_ReadWalk__native7
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__native7:
.a16
.i16
    lda.l SourceGround_Slot
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_State+6,x
    bne SourceGround_ReadWalk__desired0
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__desired0:
.a16
.i16
    cmp #3
    bcc SourceGround_ReadWalk__desired1
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__desired1:
.a16
.i16
    lda.l SourceVisual_State+30,x
    and #$00FF
    cmp #0
    beq SourceGround_ReadWalk__desired2
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__desired2:
.a16
.i16
    lda.l SourceGround_Slot
    bne SourceGround_ReadWalk__p2
    lda.l SourceVisual_CompletedValid
    cmp #1
    beq SourceGround_ReadWalk__p10
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__p10:
.a16
.i16
    lda.l SourceVisual_CompletedStage
    cmp.l Game_StageIndex
    beq SourceGround_ReadWalk__p11
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__p11:
.a16
.i16
    lda.l SourceVisual_CompletedRoster
    cmp #22
    beq SourceGround_ReadWalk__p12
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__p12:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+1
    and #$00FF
    cmp #0
    beq SourceGround_ReadWalk__p13
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__p13:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+12
    and #$00FF
    bne SourceGround_ReadWalk__p14
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__p14:
.a16
.i16
    cmp #66
    bcc SourceGround_ReadWalk__p15
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__p15:
.a16
.i16
    brl SourceGround_ReadWalk__read
SourceGround_ReadWalk__p2:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourceGround_ReadWalk__p20
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__p20:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage
    cmp.l Game_StageIndex
    beq SourceGround_ReadWalk__p21
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__p21:
.a16
.i16
    lda.l SVActor_Data+SVActor_Roster
    cmp #22
    beq SourceGround_ReadWalk__p22
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__p22:
.a16
.i16
    lda.l SVActor_Data+1
    and #$00FF
    cmp #0
    beq SourceGround_ReadWalk__p23
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__p23:
.a16
.i16
    lda.l SVActor_Data+12
    and #$00FF
    bne SourceGround_ReadWalk__p24
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__p24:
.a16
.i16
    cmp #66
    bcc SourceGround_ReadWalk__p25
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__p25:
.a16
.i16
    brl SourceGround_ReadWalk__read
SourceGround_ReadWalk__read:
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
    lda.l SourceGround_Row
    tay
    lda.w $4E40,y
    cmp #1
    beq SourceGround_ReadWalk__row0
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__row0:
.a16
.i16
    lda.w $4E42,y
    beq SourceGround_ReadWalk__row1
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__row1:
.a16
.i16
    lda.w $4E44,y
    bne SourceGround_ReadWalk__row2
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__row2:
.a16
.i16
    cmp #256
    bcc SourceGround_ReadWalk__row3
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__row3:
.a16
.i16
    lda.w $4E3C,y
    cmp #18
    beq SourceGround_ReadWalk__row4
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__row4:
.a16
.i16
    lda.w $4E4A,y
    and #$00FF
    cmp #2
    beq SourceGround_ReadWalk__row5
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__row5:
.a16
.i16
    lda.w $4E4B,y
    and #$00FF
    cmp #1
    beq SourceGround_DriverOK
    brl SourceGround_ReadWalk__miss
SourceGround_DriverOK:
.a16
.i16
    lda.w $4E50,y
    and #$00FF
    cmp #1
    beq SourceGround_ReadWalk__row6
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__row6:
.a16
.i16
    lda.w $4E54,y
    and #$00FF
    cmp #8
    beq SourceGround_ReadWalk__row7
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__row7:
.a16
.i16
    lda.w $4E4E,y
    and #$00FF
    cmp #0
    beq SourceGround_ReadWalk__row8
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__row8:
.a16
.i16
    sta.l SourceGround_Frame
    lda.l SourceGround_Slot
    asl a
    tax
    lda.l $434E9C,x
    cmp.l SourceGround_Native
    beq SourceGround_ReadWalk__binding
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__binding:
.a16
.i16
    lda.l $434E7C
    cmp.l SourceGround_Seq
    beq SourceGround_ReadWalk__same_seq
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__same_seq:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    beq SourceGround_ReadWalk__same_magic
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__same_magic:
.a16
.i16
    lda.l SourceGround_Stage
    cmp.l Game_StageIndex
    beq SourceGround_ReadWalk__same_stage
    brl SourceGround_ReadWalk__miss
SourceGround_ReadWalk__same_stage:
.a16
.i16
SourceGround_ReadWalk__hit:
.a16
.i16
    lda #1
    sta.l SourceGround_Role
    rep #$30
    pld
    plb
    ply
    plx
    pla
    plp
    sec
    rtl
SourceGround_ReadWalk__miss:
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
SourceGround_ReadWalk__pop_miss:
.a16
.i16
    pla
    brl SourceGround_ReadWalk__miss
SourceGround_Rows:
    .dw 0,36
SourceGround_Natives:
    .dw 0,133
