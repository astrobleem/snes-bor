; First visible default-player attack starts with authored frame0, allowing
; both players to use the same immutable ten-block image. Never changes role,
; input, world, ownership, Ready, palette or publication. The caller already
; formed an accepted native/coherent-service attack key before this seam.
SourceAttack0_PreferFirst:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    tdc
    cmp #$0A00
    beq SourceAttack0_P1
    cmp #$0A85
    beq SourceAttack0_P2
    brl SourceAttack0_No
SourceAttack0_P1:
.a16
.i16
    ldx #0
    bra SourceAttack0_Common
SourceAttack0_P2:
.a16
.i16
    ldx #133
SourceAttack0_Common:
.a16
.i16
    lda.l SourceVisual_Key
    cmp #534
    beq SourceAttack0_G1
    brl SourceAttack0_No
SourceAttack0_G1:
.a16
.i16
    lda.l SourceVisual_Key+2
    and #255
    cmp #6
    bcc SourceAttack0_G2
    brl SourceAttack0_No
SourceAttack0_G2:
.a16
.i16
    lda.l SourceVisual_Key+3
    and #255
    cmp #0
    beq SourceAttack0_G3
    brl SourceAttack0_No
SourceAttack0_G3:
.a16
.i16
    lda.l $7E46DE
    cmp #0
    beq SourceAttack0_G4
    brl SourceAttack0_No
SourceAttack0_G4:
.a16
.i16
    jsr SourceNpc_Scope
    bcs SourceAttack0_Scope
    brl SourceAttack0_No
SourceAttack0_Scope:
.a16
.i16
    lda.l Game_StageIndex
    cmp #0
    beq SourceAttack0_G5
    brl SourceAttack0_No
SourceAttack0_G5:
.a16
.i16
    lda.l $7E0A00+CHAR_HP,x
    and #255
    cmp #0
    bne SourceAttack0_G6
    brl SourceAttack0_No
SourceAttack0_G6:
.a16
.i16
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    and #255
    cmp #1
    beq SourceAttack0_G7
    brl SourceAttack0_No
SourceAttack0_G7:
.a16
.i16
    lda.l $7E0A00+CHAR_ROSTER_INDEX,x
    and #255
    cmp #22
    beq SourceAttack0_G8
    brl SourceAttack0_No
SourceAttack0_G8:
.a16
.i16
    lda.l $7E0A00+CHAR_MAP_INDEX,x
    and #255
    cmp #0
    beq SourceAttack0_G9
    brl SourceAttack0_No
SourceAttack0_G9:
.a16
.i16
    lda.l $7E0A00+CHAR_SELECTED,x
    and #255
    cmp #3
    bcc SourceAttack0_G10
    brl SourceAttack0_No
SourceAttack0_G10:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy,x
    and #255
    cmp #2
    beq SourceAttack0_G11
    brl SourceAttack0_No
SourceAttack0_G11:
.a16
.i16
    cpx #0
    beq SourceAttack0_P1Picture
    brl SourceAttack0_P2Picture
SourceAttack0_P1Picture:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    cmp #1
    beq SourceAttack0_G12
    brl SourceAttack0_No
SourceAttack0_G12:
.a16
.i16
    lda.l SourceVisual_CompletedStage
    cmp #0
    beq SourceAttack0_G13
    brl SourceAttack0_No
SourceAttack0_G13:
.a16
.i16
    lda.l SourceVisual_CompletedRoster
    cmp #22
    beq SourceAttack0_G14
    brl SourceAttack0_No
SourceAttack0_G14:
.a16
.i16
    lda.l SourceVisual_CompletedEntry
    and #255
    cmp #22
    beq SourceAttack0_G15
    brl SourceAttack0_No
SourceAttack0_G15:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+1
    and #255
    cmp #2
    bcc SourceAttack0_G16
    brl SourceAttack0_No
SourceAttack0_G16:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+3
    and #255
    cmp #0
    beq SourceAttack0_G17
    brl SourceAttack0_No
SourceAttack0_G17:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+12
    and #255
    cmp #0
    bne SourceAttack0_G18
    brl SourceAttack0_No
SourceAttack0_G18:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+12
    and #255
    cmp #66
    bcc SourceAttack0_G19
    brl SourceAttack0_No
SourceAttack0_G19:
.a16
.i16
    brl SourceAttack0_Change
SourceAttack0_P2Picture:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourceAttack0_G20
    brl SourceAttack0_No
SourceAttack0_G20:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage
    cmp #0
    beq SourceAttack0_G21
    brl SourceAttack0_No
SourceAttack0_G21:
.a16
.i16
    lda.l SVActor_Data+SVActor_Roster
    cmp #22
    beq SourceAttack0_G22
    brl SourceAttack0_No
SourceAttack0_G22:
.a16
.i16
    lda.l SVActor_Data
    and #255
    cmp #22
    beq SourceAttack0_G23
    brl SourceAttack0_No
SourceAttack0_G23:
.a16
.i16
    lda.l SVActor_Data+1
    and #255
    cmp #2
    bcc SourceAttack0_G24
    brl SourceAttack0_No
SourceAttack0_G24:
.a16
.i16
    lda.l SVActor_Data+3
    and #255
    cmp #0
    beq SourceAttack0_G25
    brl SourceAttack0_No
SourceAttack0_G25:
.a16
.i16
    lda.l SVActor_Data+12
    and #255
    cmp #0
    bne SourceAttack0_G26
    brl SourceAttack0_No
SourceAttack0_G26:
.a16
.i16
    lda.l SVActor_Data+12
    and #255
    cmp #66
    bcc SourceAttack0_G27
    brl SourceAttack0_No
SourceAttack0_G27:
.a16
.i16
SourceAttack0_Change:
.a16
.i16
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_Key+2
    rep #$30
.a16
.i16
SourceAttack0_Changed:
.a16
.i16
SourceAttack0_No:
.a16
.i16
    ply
    plx
    pla
    plp
    rtl
SourceAttack0_End:

; Avoid the full first-attack predicate for every ordinary ground lookup.
SourceAttack0_BeforeLookup:
.a16
.i16
    php
    rep #$30
    pha
    lda.l SourceVisual_Key
    cmp #$0216
    beq SourceAttack0_LookupAttack
    pla
    plp
    jml SourceVisual_PreferSharedFirstIdle
SourceAttack0_LookupAttack:
.a16
.i16
    pla
    plp
    jsl SourceAttack0_PreferFirst
    jml SourceVisual_PreferSharedFirstIdle
SourceAttackWarm_End:
