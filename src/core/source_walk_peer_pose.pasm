; Entered only by the original proxy's non-attack branch. Attack path
; retains identical instructions and cycles. Native role/key already formed.
SourceWalkPeer_Normal:
.a16
.i16
    cmp #1
    bne SourceWalkPeer_NormalDone
    phx
    lda.l SourceVisual_ServiceOnly
    bne SourceWalkPeer_NormalRestore
    lda.l SourceReserve_Valid
    cmp #SourceGround_InitialIdlePhase
    bne SourceWalkPeer_NormalRestore
    lda.l SourceVisual_Key+2
    cmp #2
    bcc SourceWalkPeer_NormalRestore
    cmp #10
    bcs SourceWalkPeer_NormalRestore
    jsl SourceWalkPeer_PreferFirst
SourceWalkPeer_NormalRestore:
.a16
.i16
    plx
SourceWalkPeer_NormalDone:
.a16
.i16
    jml SourceIdleFitProxy__done
SourceWalkPeer_PreferFirst:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    sep #$20
    lda #$39
    pha
    plb
    rep #$20
    tdc
    cmp #$0A00
    beq SourceWalkPeer_P1
    cmp #$0A85
    beq SourceWalkPeer_P2
    brl SourceWalkPeer_No
SourceWalkPeer_P1:
.a16
.i16
    ldx #0
    bra SourceWalkPeer_Common
SourceWalkPeer_P2:
.a16
.i16
    ldx #133
SourceWalkPeer_Common:
.a16
.i16
    lda.l SourceVisual_Key
    cmp #278
    beq SourceWalkPeer_G1
    brl SourceWalkPeer_No
SourceWalkPeer_G1:
.a16
.i16
    lda.l SourceVisual_Key+2
    and #255
    cmp #10
    bcc SourceWalkPeer_G2
    brl SourceWalkPeer_No
SourceWalkPeer_G2:
.a16
.i16
    lda.l SourceVisual_Key+3
    and #255
    cmp #0
    beq SourceWalkPeer_G3
    brl SourceWalkPeer_No
SourceWalkPeer_G3:
.a16
.i16
    lda.l $7E46DE
    cmp #0
    beq SourceWalkPeer_G4
    brl SourceWalkPeer_No
SourceWalkPeer_G4:
.a16
.i16
    jsl SourceWalkPeer_ScopeLong
    bcs SourceWalkPeer_Scope
    brl SourceWalkPeer_No
SourceWalkPeer_Scope:
.a16
.i16
    lda.l Game_StageIndex
    cmp #0
    beq SourceWalkPeer_G5
    brl SourceWalkPeer_No
SourceWalkPeer_G5:
.a16
.i16
    lda.l $7E0A00+CHAR_HP,x
    and #255
    cmp #0
    bne SourceWalkPeer_G6
    brl SourceWalkPeer_No
SourceWalkPeer_G6:
.a16
.i16
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    and #255
    cmp #1
    beq SourceWalkPeer_G7
    brl SourceWalkPeer_No
SourceWalkPeer_G7:
.a16
.i16
    lda.l $7E0A00+CHAR_ROSTER_INDEX,x
    and #255
    cmp #22
    beq SourceWalkPeer_G8
    brl SourceWalkPeer_No
SourceWalkPeer_G8:
.a16
.i16
    lda.l $7E0A00+CHAR_MAP_INDEX,x
    and #255
    cmp #0
    beq SourceWalkPeer_G9
    brl SourceWalkPeer_No
SourceWalkPeer_G9:
.a16
.i16
    lda.l $7E0A00+CHAR_SELECTED,x
    and #255
    cmp #3
    bcc SourceWalkPeer_G10
    brl SourceWalkPeer_No
SourceWalkPeer_G10:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy,x
    and #255
    cmp #2
    beq SourceWalkPeer_G11
    brl SourceWalkPeer_No
SourceWalkPeer_G11:
.a16
.i16
    cpx #0
    beq SourceWalkPeer_P1Picture
    brl SourceWalkPeer_P2Picture
SourceWalkPeer_P1Picture:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    cmp #1
    beq SourceWalkPeer_G12
    brl SourceWalkPeer_No
SourceWalkPeer_G12:
.a16
.i16
    lda.l SourceVisual_CompletedStage
    cmp #0
    beq SourceWalkPeer_G13
    brl SourceWalkPeer_No
SourceWalkPeer_G13:
.a16
.i16
    lda.l SourceVisual_CompletedRoster
    cmp #22
    beq SourceWalkPeer_G14
    brl SourceWalkPeer_No
SourceWalkPeer_G14:
.a16
.i16
    lda.l SourceVisual_CompletedEntry
    and #255
    cmp #22
    beq SourceWalkPeer_G15
    brl SourceWalkPeer_No
SourceWalkPeer_G15:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+1
    and #255
    cmp #0
    beq SourceWalkPeer_G16
    brl SourceWalkPeer_No
SourceWalkPeer_G16:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+3
    and #255
    cmp #0
    beq SourceWalkPeer_G17
    brl SourceWalkPeer_No
SourceWalkPeer_G17:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+12
    and #255
    cmp #0
    bne SourceWalkPeer_G18
    brl SourceWalkPeer_No
SourceWalkPeer_G18:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+12
    and #255
    cmp #66
    bcc SourceWalkPeer_G19
    brl SourceWalkPeer_No
SourceWalkPeer_G19:
.a16
.i16
    brl SourceWalkPeer_Change
SourceWalkPeer_P2Picture:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourceWalkPeer_G20
    brl SourceWalkPeer_No
SourceWalkPeer_G20:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage
    cmp #0
    beq SourceWalkPeer_G21
    brl SourceWalkPeer_No
SourceWalkPeer_G21:
.a16
.i16
    lda.l SVActor_Data+SVActor_Roster
    cmp #22
    beq SourceWalkPeer_G22
    brl SourceWalkPeer_No
SourceWalkPeer_G22:
.a16
.i16
    lda.l SVActor_Data
    and #255
    cmp #22
    beq SourceWalkPeer_G23
    brl SourceWalkPeer_No
SourceWalkPeer_G23:
.a16
.i16
    lda.l SVActor_Data+1
    and #255
    cmp #0
    beq SourceWalkPeer_G24
    brl SourceWalkPeer_No
SourceWalkPeer_G24:
.a16
.i16
    lda.l SVActor_Data+3
    and #255
    cmp #0
    beq SourceWalkPeer_G25
    brl SourceWalkPeer_No
SourceWalkPeer_G25:
.a16
.i16
    lda.l SVActor_Data+12
    and #255
    cmp #0
    bne SourceWalkPeer_G26
    brl SourceWalkPeer_No
SourceWalkPeer_G26:
.a16
.i16
    lda.l SVActor_Data+12
    and #255
    cmp #66
    bcc SourceWalkPeer_G27
    brl SourceWalkPeer_No
SourceWalkPeer_G27:
.a16
.i16
SourceWalkPeer_Change:
.a16
.i16
    jsr SourceWalkPeer_Pending
    bcs SourceWalkPeer_Confirmed
    brl SourceWalkPeer_No
SourceWalkPeer_Confirmed:
.a16
.i16
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_Key+2
    rep #$30
.a16
.i16
SourceWalkPeer_Changed:
.a16
.i16
SourceWalkPeer_No:
.a16
.i16
    plb
    ply
    plx
    pla
    plp
    rtl
SourceWalkPeer_End:

SourceWalkPeer_ScopeLong:
.a16
.i16
    phk
    .db $F4
    .dw ((SourceWalkPeer_ScopeReturned-1)&$FFFF)
    .db $F4
    .dw ((SourceWarm_ReadAttack__miss+8)&$FFFF)
    jml SourceNpc_Scope
SourceWalkPeer_ScopeReturned:
.a16
.i16
    rtl
SourceWalkPeer_Pending:
.a16
.i16
    tdc
    cmp #$0A00
    beq SourceWalkPeer_Peer2
    ldx #0
    bra SourceWalkPeer_PeerState
SourceWalkPeer_Peer2:
.a16
.i16
    ldx #32
SourceWalkPeer_PeerState:
.a16
.i16
    lda.l SourceVisual_State+6,x
    cmp #1
    beq SourceWalkPeer_PeerMode
    cmp #2
    beq SourceWalkPeer_PeerMode
    brl SourceWalkPeer_PeerNo
SourceWalkPeer_PeerMode:
.a16
.i16
    lda.l SourceVisual_State+28,x
    and #255
    beq SourceWalkPeer_Unemitted
    brl SourceWalkPeer_PeerNo
SourceWalkPeer_Unemitted:
.a16
.i16
    lda.l SourceVisual_State,x
    cmp #1045
    beq SourceWalkPeer_PeerIndex
    brl SourceWalkPeer_PeerNo
SourceWalkPeer_PeerIndex:
.a16
.i16
    lda.l SourceVisual_State+29,x
    cmp #$0116
    beq SourceWalkPeer_PeerKey
    brl SourceWalkPeer_PeerNo
SourceWalkPeer_PeerKey:
.a16
.i16
    cpx #0
    beq SourceWalkPeer_PeerRaw
    ldx #1280
SourceWalkPeer_PeerRaw:
.a16
.i16
    lda.l SVActor_MetaData+SVActor_MetaValid,x
    cmp #1
    bne SourceWalkPeer_PeerNo
    lda.l SVActor_MetaData+SVActor_MetaStage,x
    bne SourceWalkPeer_PeerNo
    lda.l SVActor_MetaData,x
    cmp #1045
    bne SourceWalkPeer_PeerNo
    lda.l SVActor_MetaData+2,x
    cmp #10
    bne SourceWalkPeer_PeerNo
    ldy #0
SourceWalkPeer_Header:
.a16
.i16
    lda.l SVActor_MetaData+4,x
    .db $D9 ; CMP absolute,Y
    .dw (SourceWalkPeer_Entry&$FFFF)
    bne SourceWalkPeer_PeerNo
    inx
    inx
    iny
    iny
    cpy #24
    bcc SourceWalkPeer_Header
    sec
    rts
SourceWalkPeer_PeerNo:
.a16
.i16
    clc
    rts
SourceWalkPeer_EntryLo = SourceWalkPeer_Entry & $FFFF
SourceWalkPeer_Entry:
    .db $16,$01,$01,$00,$37,$00,$6A,$00,$1A,$00,$68,$00,$0A,$00,$01,$00,$15,$39,$00,$00,$19,$02,$00,$00
SourceWalkPeer_ModuleEnd:
