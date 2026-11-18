; First idle handoff after a completed walk. No simulation/input/Ready writes.
; Retain the existing rule that a player's FIRST walking picture must publish.
; Once a complete walk exists, later unfinished walking frames may yield to
; the native accepted idle role through the original DMA replacement fence.
; Keep that first idle request at authored frame0 until one idle packet exists.
; No prefetch jobs, ownership bits, private RAM, palettes or asset data added.

SourceIdle_PreferFirst:
.a16
.i16
    php
    rep #$30
    pha
    lda.l SourceVisual_Key+1
    and #$00FF
    bne SourceIdle_PreferFirst__done
    lda.l SourceVisual_Key+2
    and #$00FF
    beq SourceIdle_PreferFirst__done
    phx
    phy
    jsr SourceIdle_Eligible
    bcc SourceIdle_PreferFirst__restore
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_Key+2
SourceIdle_PreferFirst__changed:
.a8
.i16
    rep #$30
.a16
.i16
SourceIdle_PreferFirst__restore:
.a16
.i16
    ply
    plx
SourceIdle_PreferFirst__done:
.a16
.i16
    pla
    plp
    rtl

SourceIdle_CanReplace:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    jsr SourceIdle_Eligible
    bcc SourceIdle_CanReplace__no
    lda.l SourceVisual_Key+2
    and #$00FF
    bne SourceIdle_CanReplace__no
    txa
    cmp.l SourceVisual_Record
    bne SourceIdle_CanReplace__no
    lda.l SourceVisual_ActorSlot
    cmp #2
    bcs SourceIdle_CanReplace__no
    asl a
    asl a
    asl a
    asl a
    asl a
    cmp.l SourceVisual_Record
    bne SourceIdle_CanReplace__no
    lda.l SourceVisual_State+6,x
    cmp #1
    beq SourceIdle_CanReplace__mode
    cmp #2
    bne SourceIdle_CanReplace__no
SourceIdle_CanReplace__mode:
.a16
.i16
    lda.l SourceVisual_State+28,x
    and #$00FF
    bne SourceIdle_CanReplace__no
    lda.l SourceVisual_State+30,x
    and #$00FF
    cmp #1
    bne SourceIdle_CanReplace__no
SourceIdle_CanReplace__yes:
.a16
.i16
    ply
    plx
    pla
    plp
    sec
    rtl
SourceIdle_CanReplace__no:
.a16
.i16
    ply
    plx
    pla
    plp
    clc
    rtl

; A first idle lease may use the existing compositor completion check.
; This predicate does not retire, allocate or publish anything. The caller
; still proves raw metadata identity and every physical block completion,
; then follows ordinary LoadResources, palette and completed-picture fences.
SourceIdle_CanFinish:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    jsr SourceIdle_Eligible
    bcc SourceIdle_CanFinish__no
    lda.l SourceVisual_Key+2
    and #$00FF
    bne SourceIdle_CanFinish__no
    txa
    cmp.l SourceVisual_Record
    bne SourceIdle_CanFinish__no
    lda.l SourceVisual_ActorSlot
    cmp #2
    bcs SourceIdle_CanFinish__no
    asl a
    asl a
    asl a
    asl a
    asl a
    cmp.l SourceVisual_Record
    bne SourceIdle_CanFinish__no
    lda.l SourceVisual_State,x
    cmp.l SourceVisual_EntryIndexSaved
    bne SourceIdle_CanFinish__no
    lda.l SourceVisual_State+6,x
    cmp #1
    bne SourceIdle_CanFinish__no
    lda.l SourceVisual_State+28,x
    and #$00FF
    bne SourceIdle_CanFinish__no
    lda.l SourceVisual_State+30,x
    and #$00FF
    bne SourceIdle_CanFinish__no
    ply
    plx
    pla
    plp
    sec
    rtl
SourceIdle_CanFinish__no:
.a16
.i16
    ply
    plx
    pla
    plp
    clc
    rtl

; A16/I16. C1 returns X=the exact player record0/32. Public entries preserve
; all caller registers. BW-RAM reads follow original campaign/ownership scope.
SourceIdle_Eligible:
.a16
.i16
    lda.l SourceVisual_Key
    and #$00FF
    cmp #22
    beq SourceIdle_Eligible__guard0
    brl SourceIdle_Eligible__no
SourceIdle_Eligible__guard0:
.a16
.i16
    lda.l SourceVisual_Key+1
    and #$00FF
    beq SourceIdle_Eligible__guard1
    brl SourceIdle_Eligible__no
SourceIdle_Eligible__guard1:
.a16
.i16
    lda.l SourceVisual_Key+3
    and #$00FF
    beq SourceIdle_Eligible__guard2
    brl SourceIdle_Eligible__no
SourceIdle_Eligible__guard2:
.a16
.i16
    tdc
    cmp #$0A00
    beq SourceIdle_Eligible__p1_native
    cmp #$0A85
    beq SourceIdle_Eligible__guard3
    brl SourceIdle_Eligible__no
SourceIdle_Eligible__guard3:
.a16
.i16
    ldx #133
    ldy #32
    bra SourceIdle_Eligible__scope
SourceIdle_Eligible__p1_native:
.a16
.i16
    ldx #0
    ldy #0
SourceIdle_Eligible__scope:
.a16
.i16
    lda.l $7E46DE
    beq SourceIdle_Eligible__guard4
    brl SourceIdle_Eligible__no
SourceIdle_Eligible__guard4:
.a16
.i16
    jsr SourceNpc_Scope
    bcs SourceIdle_Eligible__guard5
    brl SourceIdle_Eligible__no
SourceIdle_Eligible__guard5:
.a16
.i16
    lda.l Game_StageIndex
    beq SourceIdle_Eligible__guard6
    brl SourceIdle_Eligible__no
SourceIdle_Eligible__guard6:
.a16
.i16
    lda.l $7E0A00+CHAR_HP,x
    and #$00FF
    bne SourceIdle_Eligible__guard7
    brl SourceIdle_Eligible__no
SourceIdle_Eligible__guard7:
.a16
.i16
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    and #$00FF
    cmp #1
    beq SourceIdle_Eligible__guard8
    brl SourceIdle_Eligible__no
SourceIdle_Eligible__guard8:
.a16
.i16
    lda.l $7E0A00+CHAR_ROSTER_INDEX,x
    and #$00FF
    cmp #22
    beq SourceIdle_Eligible__guard9
    brl SourceIdle_Eligible__no
SourceIdle_Eligible__guard9:
.a16
.i16
    lda.l $7E0A00+CHAR_MAP_INDEX,x
    and #$00FF
    beq SourceIdle_Eligible__guard10
    brl SourceIdle_Eligible__no
SourceIdle_Eligible__guard10:
.a16
.i16
    lda.l $7E0A00+CHAR_SELECTED,x
    and #$00FF
    cmp #3
    bcc SourceIdle_Eligible__guard11
    brl SourceIdle_Eligible__no
SourceIdle_Eligible__guard11:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy,x
    and #$00FF
    cmp #2
    beq SourceIdle_Eligible__guard12
    brl SourceIdle_Eligible__no
SourceIdle_Eligible__guard12:
.a16
.i16
    lda.l SourceVisual_Sa1RuntimeRole,x
    and #$00FF
    beq SourceIdle_Eligible__guard13
    brl SourceIdle_Eligible__no
SourceIdle_Eligible__guard13:
.a16
.i16
    lda.l StageBounds_State,x
    beq SourceIdle_Eligible__guard14
    brl SourceIdle_Eligible__no
SourceIdle_Eligible__guard14:
.a16
.i16
    tya
    beq SourceIdle_Eligible__p1_picture
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourceIdle_Eligible__guard15
    brl SourceIdle_Eligible__no
SourceIdle_Eligible__guard15:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage
    beq SourceIdle_Eligible__guard16
    brl SourceIdle_Eligible__no
SourceIdle_Eligible__guard16:
.a16
.i16
    lda.l SVActor_Data+SVActor_Roster
    cmp #22
    beq SourceIdle_Eligible__guard17
    brl SourceIdle_Eligible__no
SourceIdle_Eligible__guard17:
.a16
.i16
    lda.l SVActor_Data+1
    and #$00FF
    cmp #1
    beq SourceIdle_Eligible__guard18
    brl SourceIdle_Eligible__no
SourceIdle_Eligible__guard18:
.a16
.i16
    lda.l SVActor_Data+3
    and #$00FF
    beq SourceIdle_Eligible__guard19
    brl SourceIdle_Eligible__no
SourceIdle_Eligible__guard19:
.a16
.i16
    lda.l SVActor_Data+12
    and #$00FF
    bne SourceIdle_Eligible__guard20
    brl SourceIdle_Eligible__no
SourceIdle_Eligible__guard20:
.a16
.i16
    cmp #66
    bcc SourceIdle_Eligible__guard21
    brl SourceIdle_Eligible__no
SourceIdle_Eligible__guard21:
.a16
.i16
    bra SourceIdle_Eligible__yes
SourceIdle_Eligible__p1_picture:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    cmp #1
    beq SourceIdle_Eligible__guard22
    brl SourceIdle_Eligible__no
SourceIdle_Eligible__guard22:
.a16
.i16
    lda.l SourceVisual_CompletedStage
    beq SourceIdle_Eligible__guard23
    brl SourceIdle_Eligible__no
SourceIdle_Eligible__guard23:
.a16
.i16
    lda.l SourceVisual_CompletedRoster
    cmp #22
    beq SourceIdle_Eligible__guard24
    brl SourceIdle_Eligible__no
SourceIdle_Eligible__guard24:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+1
    and #$00FF
    cmp #1
    beq SourceIdle_Eligible__guard25
    brl SourceIdle_Eligible__no
SourceIdle_Eligible__guard25:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+3
    and #$00FF
    beq SourceIdle_Eligible__guard26
    brl SourceIdle_Eligible__no
SourceIdle_Eligible__guard26:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+12
    and #$00FF
    bne SourceIdle_Eligible__guard27
    brl SourceIdle_Eligible__no
SourceIdle_Eligible__guard27:
.a16
.i16
    cmp #66
    bcc SourceIdle_Eligible__guard28
    brl SourceIdle_Eligible__no
SourceIdle_Eligible__guard28:
.a16
.i16
SourceIdle_Eligible__yes:
.a16
.i16
    tya
    tax
    sec
    rts
SourceIdle_Eligible__no:
.a16
.i16
    clc
    rts

; Foreground-only first-idle metadata admission. No tiles, allocations, DMA,
; palettes or readiness writes. Existing raw cache identity is reused when
; present. A miss reads exactly ten immutable 16-byte SVIS piece rows once.
SourceCritical_Bridge_SourceIdleMetadata:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    lda.l SourceVisual_ServiceOnly
    beq SourceIdle_Metadata__guard0
    brl SourceIdle_Metadata__restore_registers
SourceIdle_Metadata__guard0:
.a16
.i16
    jsl SourceGround_CanFinish
    bcs SourceIdle_Metadata__guard1
    brl SourceIdle_Metadata__restore_registers
SourceIdle_Metadata__guard1:
.a16
.i16
    lda.l SourceVisual_Key+1
    and #$00FF
    bne SourceIdle_Metadata__walk_count
    lda.l SourceVisual_EntryScratch+12
    and #$00FF
    cmp #10
    beq SourceIdle_Metadata__guard2
    brl SourceIdle_Metadata__restore_registers
SourceIdle_Metadata__walk_count:
.a16
.i16
    lda.l SourceVisual_EntryScratch+12
    and #$00FF
    cmp #1
    bcc SourceIdle_Metadata__walk_bad
    cmp #13
    bcc SourceIdle_Metadata__guard3
SourceIdle_Metadata__walk_bad:
.a16
.i16
    brl SourceIdle_Metadata__restore_registers
SourceIdle_Metadata__guard2:
.a16
.i16
    lda.l SourceVisual_EntryScratch+2
    and #$00FF
    beq SourceIdle_Metadata__guard3
    brl SourceIdle_Metadata__restore_registers
SourceIdle_Metadata__guard3:
.a16
.i16
    phb
    sep #$20
.a8
    lda #0
    pha
    plb
    rep #$30
.a16
.i16
    lda.l SourceVisual_Offset
    pha
    lda.l SourceVisual_Offset+2
    pha
    lda.l SourceVisual_Temp
    pha
    lda.l SourceVisual_PieceCount
    pha
    lda.l SourceVisual_PieceIndex
    pha
    lda.l SVActor_MetaBase
    pha
    lda.l SVActor_MetaBytes
    pha
    jsl SourceCritical_Bridge_SVActor_MetaMatch
    bcs SourceIdle_Metadata__restore_scratch
    lda.l SourceVisual_EntryScratch+12
    and #$00FF
    sta.l SourceVisual_PieceCount
    jsl SourceCritical_Bridge_ReadIdlePieces
SourceIdle_Metadata__restore_scratch:
.a16
.i16
    rep #$30
    pla
    sta.l SVActor_MetaBytes
    pla
    sta.l SVActor_MetaBase
    pla
    sta.l SourceVisual_PieceIndex
    pla
    sta.l SourceVisual_PieceCount
    pla
    sta.l SourceVisual_Temp
    pla
    sta.l SourceVisual_Offset+2
    pla
    sta.l SourceVisual_Offset
    plb
SourceIdle_Metadata__restore_registers:
.a16
.i16
    ply
    plx
    pla
    plp
    rtl

; First walking picture after a completed idle, using the same completion
; and immutable metadata path. Later walk-frame churn remains loader-only.
SourceWalk_CanFinish:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    jsr SourceWalk_Eligible
    bcc SourceWalk_CanFinish__no
    lda.l SourceVisual_Key+2
    and #$00FF
    cmp #10
    bcs SourceWalk_CanFinish__no
    lda.l SourceVisual_EntryScratch
    cmp.l SourceVisual_Key
    bne SourceWalk_CanFinish__no
    lda.l SourceVisual_EntryScratch+2
    cmp.l SourceVisual_Key+2
    bne SourceWalk_CanFinish__no
    txa
    cmp.l SourceVisual_Record
    bne SourceWalk_CanFinish__no
    lda.l SourceVisual_ActorSlot
    cmp #2
    bcs SourceWalk_CanFinish__no
    asl a
    asl a
    asl a
    asl a
    asl a
    cmp.l SourceVisual_Record
    bne SourceWalk_CanFinish__no
    lda.l SourceVisual_State,x
    cmp.l SourceVisual_EntryIndexSaved
    bne SourceWalk_CanFinish__no
    lda.l SourceVisual_State+6,x
    cmp #1
    bne SourceWalk_CanFinish__no
    lda.l SourceVisual_State+28,x
    and #$00FF
    bne SourceWalk_CanFinish__no
    lda.l SourceVisual_State+30,x
    and #$00FF
    cmp #1
    bne SourceWalk_CanFinish__no
    ply
    plx
    pla
    plp
    sec
    rtl
SourceWalk_CanFinish__no:
.a16
.i16
    ply
    plx
    pla
    plp
    clc
    rtl

SourceWalk_Eligible:
.a16
.i16
    lda.l SourceVisual_Key
    and #$00FF
    cmp #22
    beq SourceWalk_Eligible__guard0
    brl SourceWalk_Eligible__no
SourceWalk_Eligible__guard0:
.a16
.i16
    lda.l SourceVisual_Key+1
    and #$00FF
    cmp #1
    beq SourceWalk_Eligible__guard1
    brl SourceWalk_Eligible__no
SourceWalk_Eligible__guard1:
.a16
.i16
    lda.l SourceVisual_Key+3
    and #$00FF
    beq SourceWalk_Eligible__guard2
    brl SourceWalk_Eligible__no
SourceWalk_Eligible__guard2:
.a16
.i16
    tdc
    cmp #$0A00
    beq SourceWalk_Eligible__p1_native
    cmp #$0A85
    beq SourceWalk_Eligible__guard3
    brl SourceWalk_Eligible__no
SourceWalk_Eligible__guard3:
.a16
.i16
    ldx #133
    ldy #32
    bra SourceWalk_Eligible__scope
SourceWalk_Eligible__p1_native:
.a16
.i16
    ldx #0
    ldy #0
SourceWalk_Eligible__scope:
.a16
.i16
    lda.l $7E46DE
    beq SourceWalk_Eligible__guard4
    brl SourceWalk_Eligible__no
SourceWalk_Eligible__guard4:
.a16
.i16
    jsr SourceNpc_Scope
    bcs SourceWalk_Eligible__guard5
    brl SourceWalk_Eligible__no
SourceWalk_Eligible__guard5:
.a16
.i16
    lda.l Game_StageIndex
    beq SourceWalk_Eligible__guard6
    brl SourceWalk_Eligible__no
SourceWalk_Eligible__guard6:
.a16
.i16
    lda.l $7E0A00+CHAR_HP,x
    and #$00FF
    bne SourceWalk_Eligible__guard7
    brl SourceWalk_Eligible__no
SourceWalk_Eligible__guard7:
.a16
.i16
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    and #$00FF
    cmp #1
    beq SourceWalk_Eligible__guard8
    brl SourceWalk_Eligible__no
SourceWalk_Eligible__guard8:
.a16
.i16
    lda.l $7E0A00+CHAR_ROSTER_INDEX,x
    and #$00FF
    cmp #22
    beq SourceWalk_Eligible__guard9
    brl SourceWalk_Eligible__no
SourceWalk_Eligible__guard9:
.a16
.i16
    lda.l $7E0A00+CHAR_MAP_INDEX,x
    and #$00FF
    beq SourceWalk_Eligible__guard10
    brl SourceWalk_Eligible__no
SourceWalk_Eligible__guard10:
.a16
.i16
    lda.l $7E0A00+CHAR_SELECTED,x
    and #$00FF
    cmp #3
    bcc SourceWalk_Eligible__guard11
    brl SourceWalk_Eligible__no
SourceWalk_Eligible__guard11:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy,x
    and #$00FF
    cmp #2
    beq SourceWalk_Eligible__guard12
    brl SourceWalk_Eligible__no
SourceWalk_Eligible__guard12:
.a16
.i16
    lda.l SourceVisual_Sa1RuntimeRole,x
    and #$00FF
    cmp #1
    beq SourceWalk_Eligible__guard13
    brl SourceWalk_Eligible__no
SourceWalk_Eligible__guard13:
.a16
.i16
    lda.l StageBounds_State,x
    beq SourceWalk_Eligible__guard14
    brl SourceWalk_Eligible__no
SourceWalk_Eligible__guard14:
.a16
.i16
    tya
    beq SourceWalk_Eligible__p1_picture
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourceWalk_Eligible__guard15
    brl SourceWalk_Eligible__no
SourceWalk_Eligible__guard15:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage
    beq SourceWalk_Eligible__guard16
    brl SourceWalk_Eligible__no
SourceWalk_Eligible__guard16:
.a16
.i16
    lda.l SVActor_Data+SVActor_Roster
    cmp #22
    beq SourceWalk_Eligible__guard17
    brl SourceWalk_Eligible__no
SourceWalk_Eligible__guard17:
.a16
.i16
    lda.l SVActor_Data+1
    and #$00FF
    cmp #0
    beq SourceWalk_Eligible__guard18
    brl SourceWalk_Eligible__no
SourceWalk_Eligible__guard18:
.a16
.i16
    lda.l SVActor_Data+3
    and #$00FF
    beq SourceWalk_Eligible__guard19
    brl SourceWalk_Eligible__no
SourceWalk_Eligible__guard19:
.a16
.i16
    lda.l SVActor_Data+12
    and #$00FF
    bne SourceWalk_Eligible__guard20
    brl SourceWalk_Eligible__no
SourceWalk_Eligible__guard20:
.a16
.i16
    cmp #66
    bcc SourceWalk_Eligible__guard21
    brl SourceWalk_Eligible__no
SourceWalk_Eligible__guard21:
.a16
.i16
    bra SourceWalk_Eligible__yes
SourceWalk_Eligible__p1_picture:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    cmp #1
    beq SourceWalk_Eligible__guard22
    brl SourceWalk_Eligible__no
SourceWalk_Eligible__guard22:
.a16
.i16
    lda.l SourceVisual_CompletedStage
    beq SourceWalk_Eligible__guard23
    brl SourceWalk_Eligible__no
SourceWalk_Eligible__guard23:
.a16
.i16
    lda.l SourceVisual_CompletedRoster
    cmp #22
    beq SourceWalk_Eligible__guard24
    brl SourceWalk_Eligible__no
SourceWalk_Eligible__guard24:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+1
    and #$00FF
    cmp #0
    beq SourceWalk_Eligible__guard25
    brl SourceWalk_Eligible__no
SourceWalk_Eligible__guard25:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+3
    and #$00FF
    beq SourceWalk_Eligible__guard26
    brl SourceWalk_Eligible__no
SourceWalk_Eligible__guard26:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+12
    and #$00FF
    bne SourceWalk_Eligible__guard27
    brl SourceWalk_Eligible__no
SourceWalk_Eligible__guard27:
.a16
.i16
    cmp #66
    bcc SourceWalk_Eligible__guard28
    brl SourceWalk_Eligible__no
SourceWalk_Eligible__guard28:
.a16
.i16
SourceWalk_Eligible__yes:
.a16
.i16
    tya
    tax
    sec
    rts
SourceWalk_Eligible__no:
.a16
.i16
    clc
    rts


SourceGround_CanFinish:
.a16
.i16
    php
    rep #$30
    pha
    lda.l SourceVisual_Key+1
    and #$00FF
    beq SourceGround_CanFinish__idle
    cmp #1
    bne SourceGround_CanFinish__no
    jsl SourceWalk_P2Handoff
    bcs SourceGround_CanFinish__yes
    bra SourceGround_CanFinish__no
SourceGround_CanFinish__idle:
.a16
.i16
    jsl SourceIdle_CanFinish
    bcc SourceGround_CanFinish__no
SourceGround_CanFinish__yes:
.a16
.i16
    pla
    plp
    sec
    rtl
SourceGround_CanFinish__no:
.a16
.i16
    pla
    plp
    clc
    rtl


; P1 already has its ordinary foreground loader. Do not delay that loader by
; trying a second first-walk completion path. P2 can reuse physically ready
; shared walk media only after P1 has a completed walk and still wants walk.
; This fast veto reads WRAM only; the callee retains full native/BW guards.
SourceWalk_P2Handoff:
.a16
.i16
    php
    rep #$30
    pha
    lda.l SourceVisual_ActorSlot
    cmp #1
    bne SourceWalk_P2Handoff__no
    lda.l SourceVisual_CompletedValid
    cmp #1
    bne SourceWalk_P2Handoff__no
    lda.l SourceVisual_CompletedStage
    bne SourceWalk_P2Handoff__no
    lda.l SourceVisual_CompletedRoster
    cmp #22
    bne SourceWalk_P2Handoff__no
    lda.l SourceVisual_CompletedEntry+1
    and #$00FF
    cmp #1
    bne SourceWalk_P2Handoff__no
    lda.l SourceVisual_State+30
    and #$00FF
    cmp #1
    bne SourceWalk_P2Handoff__no
    jsl SourceWalk_CanFinish
    bcc SourceWalk_P2Handoff__no
    pla
    plp
    sec
    rtl
SourceWalk_P2Handoff__no:
.a16
.i16
    pla
    plp
    clc
    rtl
