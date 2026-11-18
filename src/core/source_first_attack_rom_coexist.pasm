; At the ROM-only player admission callsite, preserve the original first-NPC
; predicate on every ordinary request. An eligible first player attack may
; coexist; it never takes, cancels, resets or releases the NPC's producer.
SourceCoexist_FirstPictureGate:
.a16
.i16
    lda.l SVActor_LoadOwner
    cmp #3
    bcc SourceCoexist_GateNo
    cmp #7
    bcs SourceCoexist_GateNo
    dec a
    dec a
    asl a
    tax
    lda.l SVActor_Bases,x
    tax
    lda.l SVActor_Data+SVActor_Valid,x
    cmp #1
    beq SourceCoexist_GateNo
    jsl SourceCoexist_UrgentGuard
    rtl
SourceCoexist_GateNo:
.a16
.i16
    clc
    rtl

SourceCoexist_UrgentGuard:
.a16
.i16
    php
    rep #$30
    cld
    pha
    phx
    phy
    tdc
    cmp #$0A00
    beq SourceCoexist_P1
    cmp #$0A85
    beq SourceCoexist_P2
    brl SourceCoexist_No
SourceCoexist_P1:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #0
    beq SourceCoexist_G101
    brl SourceCoexist_No
SourceCoexist_G101:
.a16
.i16
    lda.l SourceVisual_Record
    cmp #0
    beq SourceCoexist_G102
    brl SourceCoexist_No
SourceCoexist_G102:
.a16
.i16
    ldx #0
    bra SourceCoexist_Common
SourceCoexist_P2:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #1
    beq SourceCoexist_G103
    brl SourceCoexist_No
SourceCoexist_G103:
.a16
.i16
    lda.l SourceVisual_Record
    cmp #32
    beq SourceCoexist_G104
    brl SourceCoexist_No
SourceCoexist_G104:
.a16
.i16
    ldx #133
SourceCoexist_Common:
.a16
.i16
    lda.l SourceRom_PlayerMode
    cmp #1
    beq SourceCoexist_G105
    brl SourceCoexist_No
SourceCoexist_G105:
.a16
.i16
    lda.l SourceVisual_Key
    cmp #534
    beq SourceCoexist_G1
    brl SourceCoexist_No
SourceCoexist_G1:
.a16
.i16
    lda.l SourceVisual_Key+2
    and #255
    cmp #6
    bcc SourceCoexist_G2
    brl SourceCoexist_No
SourceCoexist_G2:
.a16
.i16
    lda.l SourceVisual_Key+3
    and #255
    cmp #0
    beq SourceCoexist_G3
    brl SourceCoexist_No
SourceCoexist_G3:
.a16
.i16
    lda.l $7E46DE
    cmp #0
    beq SourceCoexist_G4
    brl SourceCoexist_No
SourceCoexist_G4:
.a16
.i16
    jsr SourceNpc_Scope
    bcs SourceCoexist_Scope
    brl SourceCoexist_No
SourceCoexist_Scope:
.a16
.i16
    lda.l Game_StageIndex
    cmp #0
    beq SourceCoexist_G5
    brl SourceCoexist_No
SourceCoexist_G5:
.a16
.i16
    lda.l $7E0A00+CHAR_HP,x
    and #255
    cmp #0
    bne SourceCoexist_G6
    brl SourceCoexist_No
SourceCoexist_G6:
.a16
.i16
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    and #255
    cmp #1
    beq SourceCoexist_G7
    brl SourceCoexist_No
SourceCoexist_G7:
.a16
.i16
    lda.l $7E0A00+CHAR_ROSTER_INDEX,x
    and #255
    cmp #22
    beq SourceCoexist_G8
    brl SourceCoexist_No
SourceCoexist_G8:
.a16
.i16
    lda.l $7E0A00+CHAR_MAP_INDEX,x
    and #255
    cmp #0
    beq SourceCoexist_G9
    brl SourceCoexist_No
SourceCoexist_G9:
.a16
.i16
    lda.l $7E0A00+CHAR_SELECTED,x
    and #255
    cmp #3
    bcc SourceCoexist_G10
    brl SourceCoexist_No
SourceCoexist_G10:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy,x
    and #255
    cmp #2
    beq SourceCoexist_G11
    brl SourceCoexist_No
SourceCoexist_G11:
.a16
.i16
    lda.l SourceVisual_PieceCount
    cmp #0
    bne SourceCoexist_Nonempty
    brl SourceCoexist_No
SourceCoexist_Nonempty:
.a16
.i16
    cmp #66
    bcc SourceCoexist_BoundedCount
    brl SourceCoexist_No
SourceCoexist_BoundedCount:
.a16
.i16
    lda.l SourceVisual_Sa1RuntimeRole,x
    and #255
    cmp #2
    beq SourceCoexist_G106
    brl SourceCoexist_No
SourceCoexist_G106:
.a16
.i16
    lda.l SourceVisual_EntryScratch
    cmp.l SourceVisual_Key
    beq SourceCoexist_HeaderKey
    brl SourceCoexist_No
SourceCoexist_HeaderKey:
.a16
.i16
    lda.l SourceVisual_EntryScratch+2
    cmp.l SourceVisual_Key+2
    beq SourceCoexist_HeaderFrame
    brl SourceCoexist_No
SourceCoexist_HeaderFrame:
.a16
.i16
    lda.l SourceVisual_EntryScratch+12
    and #255
    cmp.l SourceVisual_PieceCount
    beq SourceCoexist_Count
    brl SourceCoexist_No
SourceCoexist_Count:
.a16
.i16
    lda.l SourceVisual_Key+2
    and #255
    asl a
    clc
    adc #781
    cmp.l SourceVisual_EntryIndexSaved
    beq SourceCoexist_Index
    brl SourceCoexist_No
SourceCoexist_Index:
.a16
.i16
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+6,x
    cmp #1
    beq SourceCoexist_G107
    brl SourceCoexist_No
SourceCoexist_G107:
.a16
.i16
    lda.l SourceVisual_State+28,x
    and #255
    cmp #0
    beq SourceCoexist_G108
    brl SourceCoexist_No
SourceCoexist_G108:
.a16
.i16
    lda.l SourceVisual_State+29,x
    cmp #534
    beq SourceCoexist_G109
    brl SourceCoexist_No
SourceCoexist_G109:
.a16
.i16
    lda.l SourceVisual_State,x
    cmp.l SourceVisual_EntryIndexSaved
    beq SourceCoexist_Request
    brl SourceCoexist_No
SourceCoexist_Request:
.a16
.i16
    tdc
    cmp #$0A00
    beq SourceCoexist_RestoreP1
    ldx #133
    bra SourceCoexist_Restored
SourceCoexist_RestoreP1:
.a16
.i16
    ldx #0
SourceCoexist_Restored:
.a16
.i16
    cpx #0
    beq SourceCoexist_P1Picture
    brl SourceCoexist_P2Picture
SourceCoexist_P1Picture:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    cmp #1
    beq SourceCoexist_G12
    brl SourceCoexist_No
SourceCoexist_G12:
.a16
.i16
    lda.l SourceVisual_CompletedStage
    cmp #0
    beq SourceCoexist_G13
    brl SourceCoexist_No
SourceCoexist_G13:
.a16
.i16
    lda.l SourceVisual_CompletedRoster
    cmp #22
    beq SourceCoexist_G14
    brl SourceCoexist_No
SourceCoexist_G14:
.a16
.i16
    lda.l SourceVisual_CompletedEntry
    and #255
    cmp #22
    beq SourceCoexist_G15
    brl SourceCoexist_No
SourceCoexist_G15:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+1
    and #255
    cmp #2
    bcc SourceCoexist_G16
    brl SourceCoexist_No
SourceCoexist_G16:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+3
    and #255
    cmp #0
    beq SourceCoexist_G17
    brl SourceCoexist_No
SourceCoexist_G17:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+12
    and #255
    cmp #0
    bne SourceCoexist_G18
    brl SourceCoexist_No
SourceCoexist_G18:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+12
    and #255
    cmp #66
    bcc SourceCoexist_G19
    brl SourceCoexist_No
SourceCoexist_G19:
.a16
.i16
    brl SourceCoexist_Change
SourceCoexist_P2Picture:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourceCoexist_G20
    brl SourceCoexist_No
SourceCoexist_G20:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage
    cmp #0
    beq SourceCoexist_G21
    brl SourceCoexist_No
SourceCoexist_G21:
.a16
.i16
    lda.l SVActor_Data+SVActor_Roster
    cmp #22
    beq SourceCoexist_G22
    brl SourceCoexist_No
SourceCoexist_G22:
.a16
.i16
    lda.l SVActor_Data
    and #255
    cmp #22
    beq SourceCoexist_G23
    brl SourceCoexist_No
SourceCoexist_G23:
.a16
.i16
    lda.l SVActor_Data+1
    and #255
    cmp #2
    bcc SourceCoexist_G24
    brl SourceCoexist_No
SourceCoexist_G24:
.a16
.i16
    lda.l SVActor_Data+3
    and #255
    cmp #0
    beq SourceCoexist_G25
    brl SourceCoexist_No
SourceCoexist_G25:
.a16
.i16
    lda.l SVActor_Data+12
    and #255
    cmp #0
    bne SourceCoexist_G26
    brl SourceCoexist_No
SourceCoexist_G26:
.a16
.i16
    lda.l SVActor_Data+12
    and #255
    cmp #66
    bcc SourceCoexist_G27
    brl SourceCoexist_No
SourceCoexist_G27:
.a16
.i16
SourceCoexist_Change:
.a16
.i16
SourceCoexist_Allowed:
    ply
    plx
    pla
    plp
    clc
    rtl
SourceCoexist_No:
.a16
.i16
    ply
    plx
    pla
    plp
    sec
    rtl
SourceCoexist_End:
