; One common native/scope/metadata pass and one coherent selected+peer
; source read. Avoid comparing a fresh walking read to an older priority epoch.
SourceGround_Role = $7E46FA
SourceGround_Admission:
.a16
.i16
    php
    rep #$30
    pha
    jsl SourceGround_Read
    bcc SourceGround_AdmissionMiss
    lda.l SourceGround_Role
    cmp #2
    beq SourceGround_AdmissionHit
    lda 1,s
    and #255
    beq SourceGround_PendingPeer2
    jsr SourceGround_PeerP1
    bra SourceGround_PendingChecked
SourceGround_PendingPeer2:
.a16
.i16
    jsr SourceGround_PeerP2
SourceGround_PendingChecked:
.a16
.i16
    bcs SourceGround_AdmissionMiss
    lda.l $434E7E
    cmp #$4D50
    bne SourceGround_AdmissionMiss
    lda.l $434E7C
    cmp.l SourceGround_Seq
    bne SourceGround_AdmissionMiss
SourceGround_AdmissionHit:
.a16
.i16
    pla
    plp
    sec
    rtl
SourceGround_AdmissionMiss:
.a16
.i16
    pla
    plp
    clc
    rtl
SourceGround_SetRole:
.a8
.i16
    php
    lda.l SourceGround_Role
    sta.l SourceVisual_Key+1
    plp
    lda.l SourceVisual_Key+1
    rtl
SourceGround_ScopeLong:
.a16
.i16
    phk
    .db $F4
    .dw ((SourceGround_ScopeReturned-1)&$FFFF)
    .db $F4
    .dw ((SourceWarm_ReadAttack__miss+8)&$FFFF)
    jml SourceNpc_Scope
SourceGround_ScopeReturned:
.a16
.i16
    rtl

SourceGround_PeerP1:
.a16
.i16
    lda.l $7E0000+2560+CHAR_HP
    and #$00FF
    bne SourceGround_PeerP1_guard0
    brl SourceGround_PeerP1_no
SourceGround_PeerP1_guard0:
.a16
.i16
    lda.l $7E0000+2560+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    beq SourceGround_PeerP1_guard1
    brl SourceGround_PeerP1_no
SourceGround_PeerP1_guard1:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy+0
    and #$00FF
    cmp #2
    beq SourceGround_PeerP1_guard2
    brl SourceGround_PeerP1_no
SourceGround_PeerP1_guard2:
.a16
.i16
SourceGround_PeerP1_ordinary:
.a16
.i16
    lda.l SourceVisual_State+6
    cmp #1
    beq SourceGround_PeerP1_guard3
    brl SourceGround_PeerP1_no
SourceGround_PeerP1_guard3:
.a16
.i16
    lda.l SourceVisual_State+28
    and #$00FF
    cmp #0
    beq SourceGround_PeerP1_guard4
    brl SourceGround_PeerP1_no
SourceGround_PeerP1_guard4:
.a16
.i16
    lda.l SourceVisual_State+30
    and #$00FF
    cmp #2
    beq SourceGround_PeerP1_guard5
    brl SourceGround_PeerP1_no
SourceGround_PeerP1_guard5:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    cmp #1
    bne SourceGround_PeerP1_no
    lda.l SourceVisual_CompletedStage
    cmp.l Game_StageIndex
    bne SourceGround_PeerP1_no
    lda.l $7E0000+2560+CHAR_ROSTER_INDEX
    and #$00FF
    cmp.l SourceVisual_CompletedRoster
    bne SourceGround_PeerP1_no
    lda.l SourceVisual_CompletedEntry+12
    and #$00FF
    beq SourceGround_PeerP1_no
    cmp #66
    bcs SourceGround_PeerP1_no
    lda.l SourceVisual_CompletedEntry+1
    and #$00FF
    cmp #2
    beq SourceGround_PeerP1_no
    lda #2560
    sec
    rts
SourceGround_PeerP1_no:
.a16
.i16
    clc
    rts

SourceGround_PeerP2:
.a16
.i16
    lda.l $7E0000+2693+CHAR_HP
    and #$00FF
    bne SourceGround_PeerP2_guard0
    brl SourceGround_PeerP2_no
SourceGround_PeerP2_guard0:
.a16
.i16
    lda.l $7E0000+2693+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    beq SourceGround_PeerP2_guard1
    brl SourceGround_PeerP2_no
SourceGround_PeerP2_guard1:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy+133
    and #$00FF
    cmp #2
    beq SourceGround_PeerP2_guard2
    brl SourceGround_PeerP2_no
SourceGround_PeerP2_guard2:
.a16
.i16
SourceGround_PeerP2_ordinary:
.a16
.i16
    lda.l SourceVisual_State+38
    cmp #1
    beq SourceGround_PeerP2_guard3
    brl SourceGround_PeerP2_no
SourceGround_PeerP2_guard3:
.a16
.i16
    lda.l SourceVisual_State+60
    and #$00FF
    cmp #0
    beq SourceGround_PeerP2_guard4
    brl SourceGround_PeerP2_no
SourceGround_PeerP2_guard4:
.a16
.i16
    lda.l SourceVisual_State+62
    and #$00FF
    cmp #2
    beq SourceGround_PeerP2_guard5
    brl SourceGround_PeerP2_no
SourceGround_PeerP2_guard5:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    bne SourceGround_PeerP2_no
    lda.l SVActor_Data+SVActor_Stage
    cmp.l Game_StageIndex
    bne SourceGround_PeerP2_no
    lda.l $7E0000+2693+CHAR_ROSTER_INDEX
    and #$00FF
    cmp.l SVActor_Data+SVActor_Roster
    bne SourceGround_PeerP2_no
    lda.l SVActor_Data+12
    and #$00FF
    beq SourceGround_PeerP2_no
    cmp #66
    bcs SourceGround_PeerP2_no
    lda.l SVActor_Data+1
    and #$00FF
    cmp #2
    beq SourceGround_PeerP2_no
    lda #2693
    sec
    rts
SourceGround_PeerP2_no:
.a16
.i16
    clc
    rts
; Read-only source admission hint. Never sample buttons, simulate an action,
; emit OAM, acknowledge DMA, change native actor/world fields, or take a lease.
; Existing one-job wait scheduler and normal loader/retirement stay authoritative.
SourceGround_Slot = $7E46EE
SourceGround_Seq = $7E46F0
SourceGround_Frame = $7E46F2
SourceGround_Stage = $7E46F4
SourceGround_Row = $7E46F6
SourceGround_Native = $7E46F8
SourceGround_Read:
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
    bcc SourceGround_Read__slot
    brl SourceGround_Read__miss
SourceGround_Read__slot:
.a16
.i16
    pha
    lda.l $7E46DE ; S6Normal_NmiContext: never expand work inside NMI
    cmp #0
    beq SourceGround_Read__foreground
    brl SourceGround_Read__pop_miss
SourceGround_Read__foreground:
.a16
.i16
    jsl SourceGround_ScopeLong
    bcs SourceGround_Read__scope
    brl SourceGround_Read__pop_miss
SourceGround_Read__scope:
.a16
.i16
    lda.l $7E0000+2560+CHAR_HP
    and #$00FF
    beq SourceGround_Read__no_jump0
    lda.l $7E0000+2560+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    bne SourceGround_Read__no_jump0
    lda.l $7E0000+2560+CHAR_SELECTED
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
    bne SourceGround_Read__no_jump0
    brl SourceGround_Read__pop_miss
SourceGround_Read__no_jump0:
.a16
.i16
    lda.l $7E0000+2693+CHAR_HP
    and #$00FF
    beq SourceGround_Read__no_jump1
    lda.l $7E0000+2693+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    bne SourceGround_Read__no_jump1
    lda.l $7E0000+2693+CHAR_SELECTED
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
    bne SourceGround_Read__no_jump1
    brl SourceGround_Read__pop_miss
SourceGround_Read__no_jump1:
.a16
.i16
    lda.l SVActor_LoadOwner
    cmp #3
    bcc SourceGround_Read__no_first_npc
    cmp #7
    bcs SourceGround_Read__no_first_npc
    dec a
    dec a
    asl a
    tax
    lda.l SVActor_Bases,x
    tax
    lda.l SVActor_Data+SVActor_Valid,x
    cmp #1
    beq SourceGround_Read__no_first_npc
    brl SourceGround_Read__pop_miss
SourceGround_Read__no_first_npc:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    beq SourceGround_Read__motion
    brl SourceGround_Read__pop_miss
SourceGround_Read__motion:
.a16
.i16
    lda.l $434E7C
    and #1
    beq SourceGround_Read__even
    brl SourceGround_Read__pop_miss
SourceGround_Read__even:
.a16
.i16
    pla
    sta.l SourceGround_Slot
    lda.l $434E7C
    sta.l SourceGround_Seq
    and #1
    beq SourceGround_Read__seq
    brl SourceGround_Read__miss
SourceGround_Read__seq:
.a16
.i16
    lda.l $434E2C
    sta.l SourceGround_Stage
    cmp.l Game_StageIndex
    beq SourceGround_Read__stage
    brl SourceGround_Read__miss
SourceGround_Read__stage:
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
    bne SourceGround_Read__native0
    brl SourceGround_Read__miss
SourceGround_Read__native0:
.a16
.i16
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    and #$00FF
    cmp #1
    beq SourceGround_Read__native1
    brl SourceGround_Read__miss
SourceGround_Read__native1:
.a16
.i16
    lda.l $7E0A00+CHAR_ROSTER_INDEX,x
    and #$00FF
    cmp #22
    beq SourceGround_Read__native2
    brl SourceGround_Read__miss
SourceGround_Read__native2:
.a16
.i16
    lda.l $7E0A00+CHAR_MAP_INDEX,x
    and #$00FF
    beq SourceGround_Read__native3
    brl SourceGround_Read__miss
SourceGround_Read__native3:
.a16
.i16
    lda.l $7E0A00+CHAR_SELECTED,x
    and #$00FF
    cmp #3
    bcc SourceGround_Read__native4
    brl SourceGround_Read__miss
SourceGround_Read__native4:
.a16
.i16
    lda.l StageBounds_State,x
    beq SourceGround_Read__native5
    brl SourceGround_Read__miss
SourceGround_Read__native5:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy,x
    and #$00FF
    cmp #2
    beq SourceGround_Read__native6
    brl SourceGround_Read__miss
SourceGround_Read__native6:
.a16
.i16
    lda.l SourceVisual_Sa1RuntimeRole,x
    and #$00FF
    cmp #3
    bcc SourceGround_Read__native7
    brl SourceGround_Read__miss
SourceGround_Read__native7:
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
    bne SourceGround_Read__desired0
    brl SourceGround_Read__miss
SourceGround_Read__desired0:
.a16
.i16
    cmp #3
    bcc SourceGround_Read__desired1
    brl SourceGround_Read__miss
SourceGround_Read__desired1:
.a16
.i16
    lda.l SourceVisual_State+30,x
    and #$00FF
    cmp #2
    bcc SourceGround_Read__desired2
    brl SourceGround_Read__miss
SourceGround_Read__desired2:
.a16
.i16
    lda.l SourceGround_Slot
    bne SourceGround_Read__p2
    lda.l SourceVisual_CompletedValid
    cmp #1
    beq SourceGround_Read__p10
    brl SourceGround_Read__miss
SourceGround_Read__p10:
.a16
.i16
    lda.l SourceVisual_CompletedStage
    cmp.l Game_StageIndex
    beq SourceGround_Read__p11
    brl SourceGround_Read__miss
SourceGround_Read__p11:
.a16
.i16
    lda.l SourceVisual_CompletedRoster
    cmp #22
    beq SourceGround_Read__p12
    brl SourceGround_Read__miss
SourceGround_Read__p12:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+1
    and #$00FF
    cmp #2
    bcc SourceGround_Read__p13
    brl SourceGround_Read__miss
SourceGround_Read__p13:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+12
    and #$00FF
    bne SourceGround_Read__p14
    brl SourceGround_Read__miss
SourceGround_Read__p14:
.a16
.i16
    cmp #66
    bcc SourceGround_Read__p15
    brl SourceGround_Read__miss
SourceGround_Read__p15:
.a16
.i16
    brl SourceGround_Read__read
SourceGround_Read__p2:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourceGround_Read__p20
    brl SourceGround_Read__miss
SourceGround_Read__p20:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage
    cmp.l Game_StageIndex
    beq SourceGround_Read__p21
    brl SourceGround_Read__miss
SourceGround_Read__p21:
.a16
.i16
    lda.l SVActor_Data+SVActor_Roster
    cmp #22
    beq SourceGround_Read__p22
    brl SourceGround_Read__miss
SourceGround_Read__p22:
.a16
.i16
    lda.l SVActor_Data+1
    and #$00FF
    cmp #2
    bcc SourceGround_Read__p23
    brl SourceGround_Read__miss
SourceGround_Read__p23:
.a16
.i16
    lda.l SVActor_Data+12
    and #$00FF
    bne SourceGround_Read__p24
    brl SourceGround_Read__miss
SourceGround_Read__p24:
.a16
.i16
    cmp #66
    bcc SourceGround_Read__p25
    brl SourceGround_Read__miss
SourceGround_Read__p25:
.a16
.i16
    brl SourceGround_Read__read
SourceGround_Read__read:
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
    beq SourceGround_Read__row0
    brl SourceGround_Read__miss
SourceGround_Read__row0:
.a16
.i16
    lda.w $4E42,y
    beq SourceGround_Read__row1
    brl SourceGround_Read__miss
SourceGround_Read__row1:
.a16
.i16
    lda.w $4E44,y
    bne SourceGround_Read__row2
    brl SourceGround_Read__miss
SourceGround_Read__row2:
.a16
.i16
    cmp #256
    bcc SourceGround_Read__row3
    brl SourceGround_Read__miss
SourceGround_Read__row3:
.a16
.i16
    lda.w $4E3C,y
    beq SourceGround_AttackKind
    cmp #18
    beq SourceGround_WalkKind
    brl SourceGround_Read__miss
SourceGround_AttackKind:
.a16
.i16
    lda #2
    sta.l SourceGround_Role
    brl SourceGround_Read__row4
SourceGround_WalkKind:
.a16
.i16
    ; Initial current/next preload only. The first idle reservation must
    ; still be unused; later walking keeps its original scheduling.
    lda.l SourceReserve_Valid
    cmp #$A11D
    beq SourceGround_InitialWalk
    brl SourceGround_Read__miss
SourceGround_InitialWalk:
.a16
.i16
    lda.l SourceGround_Native
    tax
    lda.l SourceVisual_Sa1RuntimeRole,x
    and #255
    cmp #2
    bcc SourceGround_WalkNative
    brl SourceGround_Read__miss
SourceGround_WalkNative:
.a16
.i16
    lda.l SourceGround_Slot
    bne SourceGround_WalkP2
    lda.l SourceVisual_CompletedEntry+1
    bra SourceGround_WalkCompleted
SourceGround_WalkP2:
.a16
.i16
    lda.l SVActor_Data+1
SourceGround_WalkCompleted:
.a16
.i16
    and #255
    beq SourceGround_WalkIdlePicture
    brl SourceGround_Read__miss
SourceGround_WalkIdlePicture:
.a16
.i16
    lda.w $4E4B,y
    and #255
    cmp #1
    beq SourceGround_WalkDriver
    brl SourceGround_Read__miss
SourceGround_WalkDriver:
.a16
.i16
    lda.w $4E4A,y
    and #255
    cmp #2
    beq SourceGround_WalkPolicy
    brl SourceGround_Read__miss
SourceGround_WalkPolicy:
.a16
.i16
    lda.w $4E50,y
    and #255
    cmp #1
    beq SourceGround_WalkRole
    brl SourceGround_Read__miss
SourceGround_WalkRole:
.a16
.i16
    lda.w $4E54,y
    and #255
    cmp #8
    beq SourceGround_WalkRoot
    brl SourceGround_Read__miss
SourceGround_WalkRoot:
.a16
.i16
    lda.w $4E4E,y
    and #255
    cmp #10
    bcc SourceGround_WalkFrame
    brl SourceGround_Read__miss
SourceGround_WalkFrame:
.a16
.i16
    lda #1
    sta.l SourceGround_Frame
    lda #1
    sta.l SourceGround_Role
    ; Peer critical priority belongs to this SAME captured generation.
    lda.l SourceGround_Slot
    beq SourceGround_CheckPeer2
    ldx #0
    bra SourceGround_CheckPeer
SourceGround_CheckPeer2:
.a16
.i16
    ldx #36
SourceGround_CheckPeer:
.a16
.i16
    lda.l $434E50,x
    and #255
    cmp #2
    beq SourceGround_PeerCritical
    cmp #7
    bne SourceGround_NoPeerCritical
SourceGround_PeerCritical:
.a16
.i16
    lda.l $434E40,x
    cmp #1
    bne SourceGround_NoPeerCritical
    lda.l $434E44,x
    beq SourceGround_NoPeerCritical
    cmp #256
    bcs SourceGround_NoPeerCritical
    brl SourceGround_Read__miss
SourceGround_NoPeerCritical:
.a16
.i16
    brl SourceGround_Read__bind_start
SourceGround_Read__row4:
.a16
.i16
    lda.w $4E4A,y
    and #$00FF
    cmp #2
    beq SourceGround_Read__row5
    brl SourceGround_Read__miss
SourceGround_Read__row5:
.a16
.i16
    lda.w $4E50,y
    and #$00FF
    cmp #2
    beq SourceGround_Read__row6
    brl SourceGround_Read__miss
SourceGround_Read__row6:
.a16
.i16
    lda.w $4E54,y
    and #$00FF
    cmp #9
    beq SourceGround_Read__row7
    brl SourceGround_Read__miss
SourceGround_Read__row7:
.a16
.i16
    lda.w $4E4E,y
    and #$00FF
    cmp #6
    bcc SourceGround_Read__row8
    brl SourceGround_Read__miss
SourceGround_Read__row8:
.a16
.i16
    sta.l SourceGround_Frame
SourceGround_Read__bind_start:
.a16
.i16
    lda.l SourceGround_Slot
    asl a
    tax
    lda.l $434E9C,x
    cmp.l SourceGround_Native
    beq SourceGround_Read__binding
    brl SourceGround_Read__miss
SourceGround_Read__binding:
.a16
.i16
    lda.l $434E7C
    cmp.l SourceGround_Seq
    beq SourceGround_Read__same_seq
    brl SourceGround_Read__miss
SourceGround_Read__same_seq:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    beq SourceGround_Read__same_magic
    brl SourceGround_Read__miss
SourceGround_Read__same_magic:
.a16
.i16
    lda.l SourceGround_Stage
    cmp.l Game_StageIndex
    beq SourceGround_Read__same_stage
    brl SourceGround_Read__miss
SourceGround_Read__same_stage:
.a16
.i16
SourceGround_Read__hit:
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
SourceGround_Read__miss:
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
SourceGround_Read__pop_miss:
.a16
.i16
    pla
    brl SourceGround_Read__miss
SourceGround_Rows:
    .dw 0,36
SourceGround_Natives:
    .dw 0,133

SourceGround_End:
