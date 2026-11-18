; Only select authored first attack0 when the peer has the exact in-flight
; catalog781/header/pieces already cached, and this actor still shows ground.
; No metadata copy or physical-ready shortcut. Original loader remains in charge.
SourceFirstPeer_Dispatch:
.a16
.i16
    jsl SourceFirstPeer_PreferFirst
    lda.l SourceVisual_Key+2
    cmp #1
    jml SourceFirstPeer_OriginalFrameTest
; First visible default-player attack starts with authored frame0, allowing
; both players to use the same immutable ten-block image. Never changes role,
; input, world, ownership, Ready, palette or publication. The caller already
; formed an accepted native/coherent-service attack key before this seam.
SourceFirstPeer_PreferFirst:
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
    beq SourceFirstPeer_P1
    cmp #$0A85
    beq SourceFirstPeer_P2
    brl SourceFirstPeer_No
SourceFirstPeer_P1:
.a16
.i16
    ldx #0
    bra SourceFirstPeer_Common
SourceFirstPeer_P2:
.a16
.i16
    ldx #133
SourceFirstPeer_Common:
.a16
.i16
    lda.l SourceVisual_Key
    cmp #534
    beq SourceFirstPeer_G1
    brl SourceFirstPeer_No
SourceFirstPeer_G1:
.a16
.i16
    lda.l SourceVisual_Key+2
    and #255
    cmp #6
    bcc SourceFirstPeer_G2
    brl SourceFirstPeer_No
SourceFirstPeer_G2:
.a16
.i16
    lda.l SourceVisual_Key+3
    and #255
    cmp #0
    beq SourceFirstPeer_G3
    brl SourceFirstPeer_No
SourceFirstPeer_G3:
.a16
.i16
    lda.l $7E46DE
    cmp #0
    beq SourceFirstPeer_G4
    brl SourceFirstPeer_No
SourceFirstPeer_G4:
.a16
.i16
    jsl SourceFirstPeer_ScopeLong
    bcs SourceFirstPeer_Scope
    brl SourceFirstPeer_No
SourceFirstPeer_Scope:
.a16
.i16
    lda.l Game_StageIndex
    cmp #0
    beq SourceFirstPeer_G5
    brl SourceFirstPeer_No
SourceFirstPeer_G5:
.a16
.i16
    lda.l $7E0A00+CHAR_HP,x
    and #255
    cmp #0
    bne SourceFirstPeer_G6
    brl SourceFirstPeer_No
SourceFirstPeer_G6:
.a16
.i16
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    and #255
    cmp #1
    beq SourceFirstPeer_G7
    brl SourceFirstPeer_No
SourceFirstPeer_G7:
.a16
.i16
    lda.l $7E0A00+CHAR_ROSTER_INDEX,x
    and #255
    cmp #22
    beq SourceFirstPeer_G8
    brl SourceFirstPeer_No
SourceFirstPeer_G8:
.a16
.i16
    lda.l $7E0A00+CHAR_MAP_INDEX,x
    and #255
    cmp #0
    beq SourceFirstPeer_G9
    brl SourceFirstPeer_No
SourceFirstPeer_G9:
.a16
.i16
    lda.l $7E0A00+CHAR_SELECTED,x
    and #255
    cmp #3
    bcc SourceFirstPeer_G10
    brl SourceFirstPeer_No
SourceFirstPeer_G10:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy,x
    and #255
    cmp #2
    beq SourceFirstPeer_G11
    brl SourceFirstPeer_No
SourceFirstPeer_G11:
.a16
.i16
    cpx #0
    beq SourceFirstPeer_P1Picture
    brl SourceFirstPeer_P2Picture
SourceFirstPeer_P1Picture:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    cmp #1
    beq SourceFirstPeer_G12
    brl SourceFirstPeer_No
SourceFirstPeer_G12:
.a16
.i16
    lda.l SourceVisual_CompletedStage
    cmp #0
    beq SourceFirstPeer_G13
    brl SourceFirstPeer_No
SourceFirstPeer_G13:
.a16
.i16
    lda.l SourceVisual_CompletedRoster
    cmp #22
    beq SourceFirstPeer_G14
    brl SourceFirstPeer_No
SourceFirstPeer_G14:
.a16
.i16
    lda.l SourceVisual_CompletedEntry
    and #255
    cmp #22
    beq SourceFirstPeer_G15
    brl SourceFirstPeer_No
SourceFirstPeer_G15:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+1
    and #255
    cmp #2
    bcc SourceFirstPeer_G16
    brl SourceFirstPeer_No
SourceFirstPeer_G16:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+3
    and #255
    cmp #0
    beq SourceFirstPeer_G17
    brl SourceFirstPeer_No
SourceFirstPeer_G17:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+12
    and #255
    cmp #0
    bne SourceFirstPeer_G18
    brl SourceFirstPeer_No
SourceFirstPeer_G18:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+12
    and #255
    cmp #66
    bcc SourceFirstPeer_G19
    brl SourceFirstPeer_No
SourceFirstPeer_G19:
.a16
.i16
    brl SourceFirstPeer_Change
SourceFirstPeer_P2Picture:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourceFirstPeer_G20
    brl SourceFirstPeer_No
SourceFirstPeer_G20:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage
    cmp #0
    beq SourceFirstPeer_G21
    brl SourceFirstPeer_No
SourceFirstPeer_G21:
.a16
.i16
    lda.l SVActor_Data+SVActor_Roster
    cmp #22
    beq SourceFirstPeer_G22
    brl SourceFirstPeer_No
SourceFirstPeer_G22:
.a16
.i16
    lda.l SVActor_Data
    and #255
    cmp #22
    beq SourceFirstPeer_G23
    brl SourceFirstPeer_No
SourceFirstPeer_G23:
.a16
.i16
    lda.l SVActor_Data+1
    and #255
    cmp #2
    bcc SourceFirstPeer_G24
    brl SourceFirstPeer_No
SourceFirstPeer_G24:
.a16
.i16
    lda.l SVActor_Data+3
    and #255
    cmp #0
    beq SourceFirstPeer_G25
    brl SourceFirstPeer_No
SourceFirstPeer_G25:
.a16
.i16
    lda.l SVActor_Data+12
    and #255
    cmp #0
    bne SourceFirstPeer_G26
    brl SourceFirstPeer_No
SourceFirstPeer_G26:
.a16
.i16
    lda.l SVActor_Data+12
    and #255
    cmp #66
    bcc SourceFirstPeer_G27
    brl SourceFirstPeer_No
SourceFirstPeer_G27:
.a16
.i16
SourceFirstPeer_Change:
.a16
.i16
    jsr SourceFirstPeer_Pending
    bcs SourceFirstPeer_Confirmed
    brl SourceFirstPeer_No
SourceFirstPeer_Confirmed:
.a16
.i16
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_Key+2
    rep #$30
.a16
.i16
SourceFirstPeer_Changed:
.a16
.i16
SourceFirstPeer_No:
.a16
.i16
    plb
    ply
    plx
    pla
    plp
    rtl
SourceFirstPeer_End:

SourceFirstPeer_ScopeLong:
.a16
.i16
    phk
    .db $F4
    .dw ((SourceFirstPeer_ScopeReturned-1)&$FFFF)
    .db $F4
    .dw ((SourceWarm_ReadAttack__miss+8)&$FFFF)
    jml SourceNpc_Scope
SourceFirstPeer_ScopeReturned:
.a16
.i16
    rtl
SourceFirstPeer_Pending:
.a16
.i16
    tdc
    cmp #$0A00
    beq SourceFirstPeer_Peer2
    ldx #0
    bra SourceFirstPeer_PeerState
SourceFirstPeer_Peer2:
.a16
.i16
    ldx #32
SourceFirstPeer_PeerState:
.a16
.i16
    lda.l SourceVisual_State+6,x
    cmp #1
    beq SourceFirstPeer_PeerMode
    cmp #2
    beq SourceFirstPeer_PeerMode
    brl SourceFirstPeer_PeerNo
SourceFirstPeer_PeerMode:
.a16
.i16
    lda.l SourceVisual_State,x
    cmp #781
    beq SourceFirstPeer_PeerIndex
    brl SourceFirstPeer_PeerNo
SourceFirstPeer_PeerIndex:
.a16
.i16
    lda.l SourceVisual_State+29,x
    cmp #$0216
    beq SourceFirstPeer_PeerKey
    brl SourceFirstPeer_PeerNo
SourceFirstPeer_PeerKey:
.a16
.i16
    cpx #0
    beq SourceFirstPeer_PeerRaw
    ldx #1280
SourceFirstPeer_PeerRaw:
.a16
.i16
    lda.l SVActor_MetaData+SVActor_MetaValid,x
    cmp #1
    bne SourceFirstPeer_PeerNo
    lda.l SVActor_MetaData+SVActor_MetaStage,x
    bne SourceFirstPeer_PeerNo
    lda.l SVActor_MetaData,x
    cmp #781
    bne SourceFirstPeer_PeerNo
    lda.l SVActor_MetaData+2,x
    cmp #10
    bne SourceFirstPeer_PeerNo
    ldy #0
SourceFirstPeer_Header:
.a16
.i16
    lda.l SVActor_MetaData+4,x
    cmp.w SourceFirstPeer_EntryLo,y
    bne SourceFirstPeer_PeerNo
    inx
    inx
    iny
    iny
    cpy #24
    bcc SourceFirstPeer_Header
    sec
    rts
SourceFirstPeer_PeerNo:
.a16
.i16
    clc
    rts
SourceFirstPeer_EntryLo = SourceFirstPeer_Entry & $FFFF
SourceFirstPeer_Entry:
    .db $16,$02,$00,$00,$62,$00,$68,$00,$17,$00,$65,$00,$0A,$00,$01,$00,$0D,$2B,$00,$00,$67,$04,$00,$00
SourceFirstPeer_ModuleEnd:
