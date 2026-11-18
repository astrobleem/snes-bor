; Exact same first attack0: one already-started donor prepares shared media.
; If both started, P1 wins the tie. No new jobs/RAM/ownership/Ready writes.
; The unchanged caller still runs the original pending-DMA retirement scan.
SourceAttackDefer_Try:
.a16
.i16
    jsl SourceShare_DeferDuplicateP2
    bcc SourceAttackDefer_Duplicate
    rtl
SourceAttackDefer_Duplicate:
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
    beq SourceAttackDefer_P1
    cmp #$0A85
    beq SourceAttackDefer_P2
    brl SourceAttackDefer_No
SourceAttackDefer_P1:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #0
    beq SourceAttackDefer_G1
    brl SourceAttackDefer_No
SourceAttackDefer_G1:
.a16
.i16
    lda.l SourceVisual_Record
    cmp #0
    beq SourceAttackDefer_G2
    brl SourceAttackDefer_No
SourceAttackDefer_G2:
.a16
.i16
    lda.l SourceVisual_State+63
    and #255
    cmp #1
    beq SourceAttackDefer_G3
    brl SourceAttackDefer_No
SourceAttackDefer_G3:
.a16
.i16
    lda.l SourceVisual_State+31
    and #255
    cmp #0
    beq SourceAttackDefer_G4
    brl SourceAttackDefer_No
SourceAttackDefer_G4:
.a16
.i16
    brl SourceAttackDefer_Context
SourceAttackDefer_P2:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #1
    beq SourceAttackDefer_G5
    brl SourceAttackDefer_No
SourceAttackDefer_G5:
.a16
.i16
    lda.l SourceVisual_Record
    cmp #32
    beq SourceAttackDefer_G6
    brl SourceAttackDefer_No
SourceAttackDefer_G6:
.a16
.i16
    lda.l SourceVisual_State+31
    and #255
    cmp #1
    beq SourceAttackDefer_G7
    brl SourceAttackDefer_No
SourceAttackDefer_G7:
.a16
.i16
SourceAttackDefer_Context:
.a16
.i16
    lda.l $7E46DE
    cmp #0
    beq SourceAttackDefer_G8
    brl SourceAttackDefer_No
SourceAttackDefer_G8:
.a16
.i16
    jsr SourceNpc_Scope
    bcs SourceAttackDefer_Scope
    brl SourceAttackDefer_No
SourceAttackDefer_Scope:
.a16
.i16
    lda.l Game_StageIndex
    cmp #0
    beq SourceAttackDefer_G9
    brl SourceAttackDefer_No
SourceAttackDefer_G9:
.a16
.i16
    lda.l SourceVisual_Key
    cmp #534
    beq SourceAttackDefer_G10
    brl SourceAttackDefer_No
SourceAttackDefer_G10:
.a16
.i16
    lda.l SourceVisual_Key+2
    cmp #0
    beq SourceAttackDefer_G11
    brl SourceAttackDefer_No
SourceAttackDefer_G11:
.a16
.i16
    lda.l SourceVisual_EntryScratch
    cmp #534
    beq SourceAttackDefer_G12
    brl SourceAttackDefer_No
SourceAttackDefer_G12:
.a16
.i16
    lda.l SourceVisual_EntryScratch+2
    cmp #0
    beq SourceAttackDefer_G13
    brl SourceAttackDefer_No
SourceAttackDefer_G13:
.a16
.i16
    lda.l SourceVisual_EntryIndexSaved
    cmp #SOURCE_VISUAL_CATALOG_COUNT
    bcc SourceAttackDefer_G14
    brl SourceAttackDefer_No
SourceAttackDefer_G14:
.a16
.i16
    lda.l SourceVisual_State+6
    cmp #1
    beq SourceAttackDefer_G15
    brl SourceAttackDefer_No
SourceAttackDefer_G15:
.a16
.i16
    lda.l SourceVisual_State+28
    and #255
    cmp #0
    beq SourceAttackDefer_G16
    brl SourceAttackDefer_No
SourceAttackDefer_G16:
.a16
.i16
    lda.l SourceVisual_State+29
    cmp #534
    beq SourceAttackDefer_G17
    brl SourceAttackDefer_No
SourceAttackDefer_G17:
.a16
.i16
    lda.l SourceVisual_State+0
    cmp.l SourceVisual_EntryIndexSaved
    beq SourceAttackDefer_Entry0
    brl SourceAttackDefer_No
SourceAttackDefer_Entry0:
.a16
.i16
    lda.l SourceVisual_State+38
    cmp #1
    beq SourceAttackDefer_G18
    brl SourceAttackDefer_No
SourceAttackDefer_G18:
.a16
.i16
    lda.l SourceVisual_State+60
    and #255
    cmp #0
    beq SourceAttackDefer_G19
    brl SourceAttackDefer_No
SourceAttackDefer_G19:
.a16
.i16
    lda.l SourceVisual_State+61
    cmp #534
    beq SourceAttackDefer_G20
    brl SourceAttackDefer_No
SourceAttackDefer_G20:
.a16
.i16
    lda.l SourceVisual_State+32
    cmp.l SourceVisual_EntryIndexSaved
    beq SourceAttackDefer_Entry32
    brl SourceAttackDefer_No
SourceAttackDefer_Entry32:
.a16
.i16
    lda.l $7E0A00+0+CHAR_HP
    and #255
    cmp #0
    bne SourceAttackDefer_G21
    brl SourceAttackDefer_No
SourceAttackDefer_G21:
.a16
.i16
    lda.l $7E0A00+0+CHAR_INPUT_DRIVEN
    and #255
    cmp #1
    beq SourceAttackDefer_G22
    brl SourceAttackDefer_No
SourceAttackDefer_G22:
.a16
.i16
    lda.l $7E0A00+0+CHAR_ROSTER_INDEX
    and #255
    cmp #22
    beq SourceAttackDefer_G23
    brl SourceAttackDefer_No
SourceAttackDefer_G23:
.a16
.i16
    lda.l $7E0A00+0+CHAR_MAP_INDEX
    and #255
    cmp #0
    beq SourceAttackDefer_G24
    brl SourceAttackDefer_No
SourceAttackDefer_G24:
.a16
.i16
    lda.l $7E0A00+0+CHAR_SELECTED
    and #255
    cmp #3
    bcc SourceAttackDefer_G25
    brl SourceAttackDefer_No
SourceAttackDefer_G25:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy+0
    and #255
    cmp #2
    beq SourceAttackDefer_G26
    brl SourceAttackDefer_No
SourceAttackDefer_G26:
.a16
.i16
    lda.l SourceVisual_Sa1RuntimeRole+0
    and #255
    cmp #2
    beq SourceAttackDefer_G27
    brl SourceAttackDefer_No
SourceAttackDefer_G27:
.a16
.i16
    lda.l StageBounds_State+0
    cmp #0
    beq SourceAttackDefer_G28
    brl SourceAttackDefer_No
SourceAttackDefer_G28:
.a16
.i16
    lda.l $7E0A00+133+CHAR_HP
    and #255
    cmp #0
    bne SourceAttackDefer_G29
    brl SourceAttackDefer_No
SourceAttackDefer_G29:
.a16
.i16
    lda.l $7E0A00+133+CHAR_INPUT_DRIVEN
    and #255
    cmp #1
    beq SourceAttackDefer_G30
    brl SourceAttackDefer_No
SourceAttackDefer_G30:
.a16
.i16
    lda.l $7E0A00+133+CHAR_ROSTER_INDEX
    and #255
    cmp #22
    beq SourceAttackDefer_G31
    brl SourceAttackDefer_No
SourceAttackDefer_G31:
.a16
.i16
    lda.l $7E0A00+133+CHAR_MAP_INDEX
    and #255
    cmp #0
    beq SourceAttackDefer_G32
    brl SourceAttackDefer_No
SourceAttackDefer_G32:
.a16
.i16
    lda.l $7E0A00+133+CHAR_SELECTED
    and #255
    cmp #3
    bcc SourceAttackDefer_G33
    brl SourceAttackDefer_No
SourceAttackDefer_G33:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy+133
    and #255
    cmp #2
    beq SourceAttackDefer_G34
    brl SourceAttackDefer_No
SourceAttackDefer_G34:
.a16
.i16
    lda.l SourceVisual_Sa1RuntimeRole+133
    and #255
    cmp #2
    beq SourceAttackDefer_G35
    brl SourceAttackDefer_No
SourceAttackDefer_G35:
.a16
.i16
    lda.l StageBounds_State+133
    cmp #0
    beq SourceAttackDefer_G36
    brl SourceAttackDefer_No
SourceAttackDefer_G36:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    cmp #1
    beq SourceAttackDefer_G37
    brl SourceAttackDefer_No
SourceAttackDefer_G37:
.a16
.i16
    lda.l SourceVisual_CompletedStage
    cmp #0
    beq SourceAttackDefer_G38
    brl SourceAttackDefer_No
SourceAttackDefer_G38:
.a16
.i16
    lda.l SourceVisual_CompletedRoster
    cmp #22
    beq SourceAttackDefer_G39
    brl SourceAttackDefer_No
SourceAttackDefer_G39:
.a16
.i16
    lda.l SourceVisual_CompletedEntry
    and #255
    cmp #22
    beq SourceAttackDefer_G40
    brl SourceAttackDefer_No
SourceAttackDefer_G40:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+1
    and #255
    cmp #2
    bcc SourceAttackDefer_G41
    brl SourceAttackDefer_No
SourceAttackDefer_G41:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+3
    and #255
    cmp #0
    beq SourceAttackDefer_G42
    brl SourceAttackDefer_No
SourceAttackDefer_G42:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+12
    and #255
    cmp #0
    bne SourceAttackDefer_G43
    brl SourceAttackDefer_No
SourceAttackDefer_G43:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+12
    and #255
    cmp #66
    bcc SourceAttackDefer_G44
    brl SourceAttackDefer_No
SourceAttackDefer_G44:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourceAttackDefer_G45
    brl SourceAttackDefer_No
SourceAttackDefer_G45:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage
    cmp #0
    beq SourceAttackDefer_G46
    brl SourceAttackDefer_No
SourceAttackDefer_G46:
.a16
.i16
    lda.l SVActor_Data+SVActor_Roster
    cmp #22
    beq SourceAttackDefer_G47
    brl SourceAttackDefer_No
SourceAttackDefer_G47:
.a16
.i16
    lda.l SVActor_Data
    and #255
    cmp #22
    beq SourceAttackDefer_G48
    brl SourceAttackDefer_No
SourceAttackDefer_G48:
.a16
.i16
    lda.l SVActor_Data+1
    and #255
    cmp #2
    bcc SourceAttackDefer_G49
    brl SourceAttackDefer_No
SourceAttackDefer_G49:
.a16
.i16
    lda.l SVActor_Data+3
    and #255
    cmp #0
    beq SourceAttackDefer_G50
    brl SourceAttackDefer_No
SourceAttackDefer_G50:
.a16
.i16
    lda.l SVActor_Data+12
    and #255
    cmp #0
    bne SourceAttackDefer_G51
    brl SourceAttackDefer_No
SourceAttackDefer_G51:
.a16
.i16
    lda.l SVActor_Data+12
    and #255
    cmp #66
    bcc SourceAttackDefer_G52
    brl SourceAttackDefer_No
SourceAttackDefer_G52:
.a16
.i16
SourceAttackDefer_Yes:
.a16
.i16
    ply
    plx
    pla
    plp
    sec
    rtl
SourceAttackDefer_No:
.a16
.i16
    ply
    plx
    pla
    plp
    clc
    rtl
SourceAttackDefer_End:
.a16
.i16
