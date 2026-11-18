; Admission only: attack keeps priority, then accepted idle0 after a
; completed walking picture, ahead of a lagging grounded native mirror.
; Only one existing loader visit. No physics/input/OAM/Ready writes.
SourceIdleReady_Role = $7E46FA
SourceIdleReady_Admission:
.a16
.i16
    php
    rep #$30
    pha
    jsl SourceWarm_ReadAttack
    bcc SourceIdleReady_Admission__walk
    lda.l SourceWarm_Frame
    sta.l SourceIdleReady_Frame
    lda #2
    sta.l SourceIdleReady_Role
    pla
    plp
    sec
    rtl
SourceIdleReady_Admission__walk:
.a16
.i16
    pla
    plp
    jml SourceIdleReady_ReadIdle
; Read-only source admission hint. Never sample buttons, simulate an action,
; emit OAM, acknowledge DMA, change native actor/world fields, or take a lease.
; Existing one-job wait scheduler and normal loader/retirement stay authoritative.
SourceIdleReady_Slot = $7E46EE
SourceIdleReady_Seq = $7E46F0
SourceIdleReady_Frame = $7E46F2
SourceIdleReady_Stage = $7E46F4
SourceIdleReady_Row = $7E46F6
SourceIdleReady_Native = $7E46F8
SourceIdleReady_ReadIdle:
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
    bcc SourceIdleReady_ReadIdle__slot
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__slot:
.a16
.i16
    pha
    lda.l $7E46DE ; S6Normal_NmiContext: never expand work inside NMI
    cmp #0
    beq SourceIdleReady_ReadIdle__foreground
    brl SourceIdleReady_ReadIdle__pop_miss
SourceIdleReady_ReadIdle__foreground:
.a16
.i16
    jsr SourceNpc_Scope
    bcs SourceIdleReady_ReadIdle__scope
    brl SourceIdleReady_ReadIdle__pop_miss
SourceIdleReady_ReadIdle__scope:
.a16
.i16
    lda.l $7E0000+2560+CHAR_HP
    and #$00FF
    beq SourceIdleReady_ReadIdle__no_jump0
    lda.l $7E0000+2560+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    bne SourceIdleReady_ReadIdle__no_jump0
    lda.l $7E0000+2560+CHAR_SELECTED
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
    bne SourceIdleReady_ReadIdle__no_jump0
    brl SourceIdleReady_ReadIdle__pop_miss
SourceIdleReady_ReadIdle__no_jump0:
.a16
.i16
    lda.l $7E0000+2693+CHAR_HP
    and #$00FF
    beq SourceIdleReady_ReadIdle__no_jump1
    lda.l $7E0000+2693+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    bne SourceIdleReady_ReadIdle__no_jump1
    lda.l $7E0000+2693+CHAR_SELECTED
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
    bne SourceIdleReady_ReadIdle__no_jump1
    brl SourceIdleReady_ReadIdle__pop_miss
SourceIdleReady_ReadIdle__no_jump1:
.a16
.i16
    lda.l SVActor_LoadOwner
    cmp #3
    bcc SourceIdleReady_ReadIdle__no_first_npc
    cmp #7
    bcs SourceIdleReady_ReadIdle__no_first_npc
    dec a
    dec a
    asl a
    tax
    lda.l SVActor_Bases,x
    tax
    lda.l SVActor_Data+SVActor_Valid,x
    cmp #1
    beq SourceIdleReady_ReadIdle__no_first_npc
    brl SourceIdleReady_ReadIdle__pop_miss
SourceIdleReady_ReadIdle__no_first_npc:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    beq SourceIdleReady_ReadIdle__motion
    brl SourceIdleReady_ReadIdle__pop_miss
SourceIdleReady_ReadIdle__motion:
.a16
.i16
    lda.l $434E7C
    and #1
    beq SourceIdleReady_ReadIdle__even
    brl SourceIdleReady_ReadIdle__pop_miss
SourceIdleReady_ReadIdle__even:
.a16
.i16
    pla
    sta.l SourceIdleReady_Slot
    lda.l $434E7C
    sta.l SourceIdleReady_Seq
    and #1
    beq SourceIdleReady_ReadIdle__seq
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__seq:
.a16
.i16
    lda.l $434E2C
    sta.l SourceIdleReady_Stage
    cmp.l Game_StageIndex
    beq SourceIdleReady_ReadIdle__stage
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__stage:
.a16
.i16
    lda.l SourceIdleReady_Slot
    asl a
    tax
    lda.l SourceIdleReady_Rows,x
    sta.l SourceIdleReady_Row
    lda.l SourceIdleReady_Natives,x
    sta.l SourceIdleReady_Native
    tax
    lda.l $7E0A00+CHAR_HP,x
    and #$00FF
    bne SourceIdleReady_ReadIdle__native0
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__native0:
.a16
.i16
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    and #$00FF
    cmp #1
    beq SourceIdleReady_ReadIdle__native1
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__native1:
.a16
.i16
    lda.l $7E0A00+CHAR_ROSTER_INDEX,x
    and #$00FF
    cmp #22
    beq SourceIdleReady_ReadIdle__native2
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__native2:
.a16
.i16
    lda.l $7E0A00+CHAR_MAP_INDEX,x
    and #$00FF
    beq SourceIdleReady_ReadIdle__native3
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__native3:
.a16
.i16
    lda.l $7E0A00+CHAR_SELECTED,x
    and #$00FF
    cmp #3
    bcc SourceIdleReady_ReadIdle__native4
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__native4:
.a16
.i16
    lda.l StageBounds_State,x
    beq SourceIdleReady_ReadIdle__native5
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__native5:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy,x
    and #$00FF
    cmp #2
    beq SourceIdleReady_ReadIdle__native6
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__native6:
.a16
.i16
    lda.l SourceVisual_Sa1RuntimeRole,x
    and #$00FF
    cmp #2
    bcc SourceIdleReady_ReadIdle__native7
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__native7:
.a16
.i16
    lda.l SourceIdleReady_Slot
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_State+6,x
    bne SourceIdleReady_ReadIdle__desired0
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__desired0:
.a16
.i16
    cmp #3
    bcc SourceIdleReady_ReadIdle__desired1
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__desired1:
.a16
.i16
    lda.l SourceVisual_State+30,x
    and #$00FF
    cmp #2
    bcc SourceIdleReady_ReadIdle__desired2
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__desired2:
.a16
.i16
    lda.l SourceIdleReady_Slot
    bne SourceIdleReady_ReadIdle__p2
    lda.l SourceVisual_CompletedValid
    cmp #1
    beq SourceIdleReady_ReadIdle__p10
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__p10:
.a16
.i16
    lda.l SourceVisual_CompletedStage
    cmp.l Game_StageIndex
    beq SourceIdleReady_ReadIdle__p11
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__p11:
.a16
.i16
    lda.l SourceVisual_CompletedRoster
    cmp #22
    beq SourceIdleReady_ReadIdle__p12
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__p12:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+1
    and #$00FF
    cmp #1
    beq SourceIdleReady_ReadIdle__p13
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__p13:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+12
    and #$00FF
    bne SourceIdleReady_ReadIdle__p14
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__p14:
.a16
.i16
    cmp #66
    bcc SourceIdleReady_ReadIdle__p15
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__p15:
.a16
.i16
    brl SourceIdleReady_ReadIdle__read
SourceIdleReady_ReadIdle__p2:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourceIdleReady_ReadIdle__p20
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__p20:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage
    cmp.l Game_StageIndex
    beq SourceIdleReady_ReadIdle__p21
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__p21:
.a16
.i16
    lda.l SVActor_Data+SVActor_Roster
    cmp #22
    beq SourceIdleReady_ReadIdle__p22
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__p22:
.a16
.i16
    lda.l SVActor_Data+1
    and #$00FF
    cmp #1
    beq SourceIdleReady_ReadIdle__p23
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__p23:
.a16
.i16
    lda.l SVActor_Data+12
    and #$00FF
    bne SourceIdleReady_ReadIdle__p24
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__p24:
.a16
.i16
    cmp #66
    bcc SourceIdleReady_ReadIdle__p25
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__p25:
.a16
.i16
    brl SourceIdleReady_ReadIdle__read
SourceIdleReady_ReadIdle__read:
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
    lda.l SourceIdleReady_Row
    tay
    lda.w $4E40,y
    cmp #1
    beq SourceIdleReady_ReadIdle__row0
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__row0:
.a16
.i16
    lda.w $4E42,y
    beq SourceIdleReady_ReadIdle__row1
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__row1:
.a16
.i16
    lda.w $4E44,y
    bne SourceIdleReady_ReadIdle__row2
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__row2:
.a16
.i16
    cmp #256
    bcc SourceIdleReady_ReadIdle__row3
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__row3:
.a16
.i16
    lda.w $4E3C,y
    cmp #9
    beq SourceIdleReady_ReadIdle__row4
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__row4:
.a16
.i16
    lda.w $4E4A,y
    and #$00FF
    cmp #2
    beq SourceIdleReady_ReadIdle__row5
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__row5:
.a16
.i16
    lda.w $4E4B,y
    and #$00FF
    cmp #1
    beq SourceIdleReady_DriverOK
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_DriverOK:
.a16
.i16
    lda.w $4E50,y
    and #$00FF
    cmp #0
    beq SourceIdleReady_ReadIdle__row6
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__row6:
.a16
.i16
    lda.w $4E54,y
    and #$00FF
    cmp #8
    beq SourceIdleReady_ReadIdle__row7
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__row7:
.a16
.i16
    lda.w $4E4E,y
    and #$00FF
    cmp #18
    bcc SourceIdleReady_ReadIdle__row8
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__row8:
.a16
.i16
    sta.l SourceIdleReady_Frame
    lda.l SourceIdleReady_Slot
    asl a
    tax
    lda.l $434E9C,x
    cmp.l SourceIdleReady_Native
    beq SourceIdleReady_ReadIdle__binding
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__binding:
.a16
.i16
    lda.l $434E7C
    cmp.l SourceIdleReady_Seq
    beq SourceIdleReady_ReadIdle__same_seq
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__same_seq:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    beq SourceIdleReady_ReadIdle__same_magic
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__same_magic:
.a16
.i16
    lda.l SourceIdleReady_Stage
    cmp.l Game_StageIndex
    beq SourceIdleReady_ReadIdle__same_stage
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_ReadIdle__same_stage:
.a16
.i16
SourceIdleReady_ReadIdle__hit:
.a16
.i16
    lda #0
    sta.l SourceIdleReady_Role
    sta.l SourceIdleReady_Frame
    rep #$30
    pld
    plb
    ply
    plx
    pla
    plp
    sec
    rtl
SourceIdleReady_ReadIdle__miss:
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
SourceIdleReady_ReadIdle__pop_miss:
.a16
.i16
    pla
    brl SourceIdleReady_ReadIdle__miss
SourceIdleReady_Rows:
    .dw 0,36
SourceIdleReady_Natives:
    .dw 0,133


; All-ready demand guard: no cache writes, pin claims, new IO or DMA.
; Normal ServiceCurrent rechecks identities and acquires its normal lease.
SourceIdleReady_Resident:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    phk
    plb
    ldy #0
SourceIdleReady_Resident__id:
.a16
.i16
    ldx #0
SourceIdleReady_Resident__scan:
.a16
.i16
    lda.l SourceVisual_BlockCache,x
    cmp.w SourceIdleReady_Ids,y
    bne SourceIdleReady_Resident__next
    lda.l SourceVisual_BlockCache+2,x
    cmp #2
    bne SourceIdleReady_Resident__next
    lda.l SourceVisual_BlockCache+5,x
    and #$00FF
    cmp #4
    bne SourceIdleReady_Resident__next
    iny
    iny
    cpy #20
    bcc SourceIdleReady_Resident__id
    ldx #0
    bra SourceIdleReady_Resident__palette
SourceIdleReady_Resident__next:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #512
    bcc SourceIdleReady_Resident__scan
    bra SourceIdleReady_Resident__no
SourceIdleReady_Resident__palette:
.a16
.i16
    lda.l SourceVisual_PaletteCache,x
    cmp #361
    bne SourceIdleReady_Resident__palnext
    lda.l SourceVisual_PaletteCache+3,x
    and #$00FF
    cmp #1
    beq SourceIdleReady_Resident__yes
SourceIdleReady_Resident__palnext:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourceIdleReady_Resident__palette
SourceIdleReady_Resident__no:
.a16
.i16
    plb
    ply
    plx
    pla
    plp
    clc
    rtl
SourceIdleReady_Resident__yes:
.a16
.i16
    plb
    ply
    plx
    pla
    plp
    sec
    rtl
SourceIdleReady_Ids:
    .dw 559,1592,2633,3618,5886,7241,8842,11343,12228,13304

; Called only after the existing attack/first-NPC priorities decline.
; Borrow one existing bounded visit; do not add a second loader or prefetch.
SourceIdleReady_FirstIdle:
.a16
.i16
    jsl SourceIdleReady_Resident
    bcc SourceIdleReady_FirstIdle__none
    lda #0
    jsl SourceIdleReady_ReadIdle
    bcs SourceIdleReady_FirstIdle__p1
    lda #1
    jsl SourceIdleReady_ReadIdle
    bcs SourceIdleReady_FirstIdle__p2
SourceIdleReady_FirstIdle__none:
.a16
.i16
    lda #0
    clc
    rtl
SourceIdleReady_FirstIdle__p1:
.a16
.i16
    lda #2560
    sec
    rtl
SourceIdleReady_FirstIdle__p2:
.a16
.i16
    lda #2693
    sec
    rtl

; Replace exactly one original LDA nativeRole,X in Idle_Eligible.
; Only a service visit may use the coherent idle accepted ahead of native walk.
; Preserve original LDA behavior everywhere else, including all normal renders.
SourceIdleReady_EligibleRole:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    phd
    lda.l SourceVisual_ServiceOnly
    cmp #1
    bne SourceIdleReady_EligibleRole__original
    lda.l SourceVisual_Sa1RuntimeRole,x
    and #$00FF
    cmp #1
    bne SourceIdleReady_EligibleRole__original
    cpx #0
    beq SourceIdleReady_EligibleRole__p1
    cpx #133
    bne SourceIdleReady_EligibleRole__original
    lda #1
    bra SourceIdleReady_EligibleRole__read
SourceIdleReady_EligibleRole__p1:
.a16
.i16
    lda #0
SourceIdleReady_EligibleRole__read:
.a16
.i16
    jsl SourceIdleReady_ReadIdle
    bcc SourceIdleReady_EligibleRole__original
    pld
    plb
    ply
    plx
    pla
    plp
    lda #0
    rtl
SourceIdleReady_EligibleRole__original:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    lda.l SourceVisual_Sa1RuntimeRole,x
    rtl
SourceIdleReady_End:
