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
    jsl SourceIdle_CanFinish
    bcs SourceIdle_Metadata__guard1
    brl SourceIdle_Metadata__restore_registers
SourceIdle_Metadata__guard1:
.a16
.i16
    lda.l SourceVisual_EntryScratch+12
    and #$00FF
    cmp #10
    beq SourceIdle_Metadata__guard2
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
    lda #10
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


; Synchronous exact ready-frame sharing, v179. No admission, IO, DMA,
; Ready-cache writes or early OAM publication. Existing ReadyLease and
; depth-sorted compositor still validate and publish P2. No queued wakeup
; survives cancellation: only the current matching live request is touched.
; The unused raw metadata tail is private foreground scratch, never a job.
SourceShare_TryReadyP2:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    lda.l SourceVisual_ActorSlot
    beq SourceShare__guard0
    brl SourceShare__done
SourceShare__guard0:
.a16
.i16
    lda.l SourceVisual_Record
    beq SourceShare__guard1
    brl SourceShare__done
SourceShare__guard1:
.a16
.i16
    lda.l SourceVisual_State+38
    cmp #1
    beq SourceShare__guard2
    brl SourceShare__done
SourceShare__guard2:
.a16
.i16
    lda.l $7E46DE
    beq SourceShare__guard3
    brl SourceShare__done
SourceShare__guard3:
.a16
.i16
    jsr SourceNpc_Scope
    bcs SourceShare__guard4
    brl SourceShare__done
SourceShare__guard4:
.a16
.i16
    lda.l Game_StageIndex
    beq SourceShare__guard5
    brl SourceShare__done
SourceShare__guard5:
.a16
.i16
    lda.l $7E0A00+CHAR_HP
    and #$00FF
    bne SourceShare__guard6
    brl SourceShare__done
SourceShare__guard6:
.a16
.i16
    lda.l $7E0A00+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    beq SourceShare__guard7
    brl SourceShare__done
SourceShare__guard7:
.a16
.i16
    lda.l $7E0A00+CHAR_ROSTER_INDEX
    and #$00FF
    cmp #22
    beq SourceShare__guard8
    brl SourceShare__done
SourceShare__guard8:
.a16
.i16
    lda.l $7E0A00+CHAR_MAP_INDEX
    and #$00FF
    cmp #0
    beq SourceShare__guard9
    brl SourceShare__done
SourceShare__guard9:
.a16
.i16
    lda.l $7E0A00+CHAR_SELECTED
    and #$00FF
    cmp #3
    bcc SourceShare__guard10
    brl SourceShare__done
SourceShare__guard10:
.a16
.i16
    lda.l $7E0A85+CHAR_HP
    and #$00FF
    bne SourceShare__guard11
    brl SourceShare__done
SourceShare__guard11:
.a16
.i16
    lda.l $7E0A85+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    beq SourceShare__guard12
    brl SourceShare__done
SourceShare__guard12:
.a16
.i16
    lda.l $7E0A85+CHAR_ROSTER_INDEX
    and #$00FF
    cmp #22
    beq SourceShare__guard13
    brl SourceShare__done
SourceShare__guard13:
.a16
.i16
    lda.l $7E0A85+CHAR_MAP_INDEX
    and #$00FF
    cmp #0
    beq SourceShare__guard14
    brl SourceShare__done
SourceShare__guard14:
.a16
.i16
    lda.l $7E0A85+CHAR_SELECTED
    and #$00FF
    cmp #3
    bcc SourceShare__guard15
    brl SourceShare__done
SourceShare__guard15:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy+0
    and #$00FF
    cmp #2
    beq SourceShare__guard16
    brl SourceShare__done
SourceShare__guard16:
.a16
.i16
    lda.l SourceVisual_Sa1RuntimeRole+0
    and #$00FF
    cmp #1
    beq SourceShare__guard17
    brl SourceShare__done
SourceShare__guard17:
.a16
.i16
    lda.l StageBounds_State+0
    beq SourceShare__guard18
    brl SourceShare__done
SourceShare__guard18:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy+133
    and #$00FF
    cmp #2
    beq SourceShare__guard19
    brl SourceShare__done
SourceShare__guard19:
.a16
.i16
    lda.l SourceVisual_Sa1RuntimeRole+133
    and #$00FF
    cmp #1
    beq SourceShare__guard20
    brl SourceShare__done
SourceShare__guard20:
.a16
.i16
    lda.l StageBounds_State+133
    beq SourceShare__guard21
    brl SourceShare__done
SourceShare__guard21:
.a16
.i16
    lda.l SourceVisual_State+6
    cmp #2
    beq SourceShare__guard22
    brl SourceShare__done
SourceShare__guard22:
.a16
.i16
    lda.l SourceVisual_State+14
    cmp #1
    beq SourceShare__guard23
    brl SourceShare__done
SourceShare__guard23:
.a16
.i16
    lda.l SourceVisual_Key
    cmp #$0116
    beq SourceShare__guard24
    brl SourceShare__done
SourceShare__guard24:
.a16
.i16
    lda.l SourceVisual_Key+2
    cmp #10
    bcc SourceShare__guard25
    brl SourceShare__done
SourceShare__guard25:
.a16
.i16
    lda.l SourceVisual_State
    cmp.l SourceVisual_State+32
    beq SourceShare__guard26
    brl SourceShare__done
SourceShare__guard26:
.a16
.i16
    cmp.l SourceVisual_EntryIndexSaved
    beq SourceShare__guard27
    brl SourceShare__done
SourceShare__guard27:
.a16
.i16
    cmp.l SVActor_MetaData+1280
    beq SourceShare__guard28
    brl SourceShare__done
SourceShare__guard28:
.a16
.i16
    lda.l SourceVisual_State+29
    and #$00FF
    cmp #22
    beq SourceShare__guard29
    brl SourceShare__done
SourceShare__guard29:
.a16
.i16
    lda.l SourceVisual_State+61
    cmp #$0116
    beq SourceShare__guard30
    brl SourceShare__done
SourceShare__guard30:
.a16
.i16
    lda.l SourceVisual_State+60
    and #$00FF
    beq SourceShare__guard31
    brl SourceShare__done
SourceShare__guard31:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourceShare__guard32
    brl SourceShare__done
SourceShare__guard32:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage
    beq SourceShare__guard33
    brl SourceShare__done
SourceShare__guard33:
.a16
.i16
    lda.l SVActor_Data+SVActor_Roster
    cmp #22
    beq SourceShare__guard34
    brl SourceShare__done
SourceShare__guard34:
.a16
.i16
    lda.l SVActor_Data
    cmp #22
    beq SourceShare__guard35
    brl SourceShare__done
SourceShare__guard35:
.a16
.i16
    lda.l SVActor_Data+3
    and #$00FF
    beq SourceShare__guard36
    brl SourceShare__done
SourceShare__guard36:
.a16
.i16
    lda.l SVActor_MetaData+1280+SVActor_MetaValid
    cmp #1
    beq SourceShare__guard37
    brl SourceShare__done
SourceShare__guard37:
.a16
.i16
    lda.l SVActor_MetaData+1280+SVActor_MetaStage
    beq SourceShare__guard38
    brl SourceShare__done
SourceShare__guard38:
.a16
.i16
    ldx #0
SourceShare__entry:
.a16
.i16
    lda.l SourceVisual_EntryScratch,x
    cmp.l SVActor_MetaData+1284,x
    beq SourceShare__guard39
    brl SourceShare__done
SourceShare__guard39:
.a16
.i16
    inx
    inx
    cpx #24
    bcc SourceShare__entry
    lda.l SourceVisual_EntryScratch
    cmp.l SourceVisual_Key
    beq SourceShare__guard40
    brl SourceShare__done
SourceShare__guard40:
.a16
.i16
    lda.l SourceVisual_EntryScratch+2
    cmp.l SourceVisual_Key+2
    beq SourceShare__guard41
    brl SourceShare__done
SourceShare__guard41:
.a16
.i16
    lda.l SourceVisual_EntryScratch+14
    cmp #1
    beq SourceShare__guard42
    brl SourceShare__done
SourceShare__guard42:
.a16
.i16
    lda.l SourceVisual_EntryScratch+12
    cmp #1
    bcs SourceShare__guard43
    brl SourceShare__done
SourceShare__guard43:
.a16
.i16
    cmp #13
    bcc SourceShare__guard44
    brl SourceShare__done
SourceShare__guard44:
.a16
.i16
    sta.l SVActor_MetaData+2352
    lda.l SourceVisual_State+16
    and #$00FF
    cmp #1
    bcs SourceShare__guard45
    brl SourceShare__done
SourceShare__guard45:
.a16
.i16
    cmp #9
    bcc SourceShare__guard46
    brl SourceShare__done
SourceShare__guard46:
.a16
.i16
    dec a
    asl a
    asl a
    asl a
    sta.l SVActor_MetaData+2354
    tax
    lda.l SourceVisual_PaletteCache+3,x
    and #$00FF
    cmp #1
    beq SourceShare__guard47
    brl SourceShare__done
SourceShare__guard47:
.a16
.i16
    lda.l SourceVisual_PaletteCache+4,x
    and #1
    bne SourceShare__guard48
    brl SourceShare__done
SourceShare__guard48:
.a16
.i16
    lda.l SourceVisual_PaletteCache,x
    sta.l SVActor_MetaData+2356
    lda #0
    sta.l SVActor_MetaData+2358
    sta.l SVActor_MetaData+2360
SourceShare__validate:
.a16
.i16
    lda.l SVActor_MetaData+2360
    tax
    lda.l SVActor_MetaData+1308+10,x
    cmp.l SVActor_MetaData+2356
    beq SourceShare__guard49
    brl SourceShare__done
SourceShare__guard49:
.a16
.i16
    lda.l SVActor_MetaData+1308+8,x
    and #$00FF
    beq SourceShare__guard50
    brl SourceShare__done
SourceShare__guard50:
.a16
.i16
    lda.l SVActor_MetaData+2358
    tax
    lda.l SourceVisual_ActorPieceMap,x
    and #$00FF
    cmp #64
    bcc SourceShare__guard51
    brl SourceShare__done
SourceShare__guard51:
.a16
.i16
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_BlockCache+2,x
    cmp #2
    beq SourceShare__guard52
    brl SourceShare__done
SourceShare__guard52:
.a16
.i16
    lda.l SourceVisual_BlockCache+4,x
    and #1
    bne SourceShare__guard53
    brl SourceShare__done
SourceShare__guard53:
.a16
.i16
    lda.l SourceVisual_BlockCache+5,x
    and #$00FF
    cmp #4
    beq SourceShare__guard54
    brl SourceShare__done
SourceShare__guard54:
.a16
.i16
    lda.l SourceVisual_BlockCache+6,x
    cmp #2
    beq SourceShare__guard55
    brl SourceShare__done
SourceShare__guard55:
.a16
.i16
    lda.l SourceVisual_BlockCache,x
    ldx.w #0
    tay
    lda.l SVActor_MetaData+2360
    tax
    tya
    cmp.l SVActor_MetaData+1308+12,x
    beq SourceShare__guard56
    brl SourceShare__done
SourceShare__guard56:
.a16
.i16
    lda.l SVActor_MetaData+2360
    clc
    adc #16
    sta.l SVActor_MetaData+2360
    lda.l SVActor_MetaData+2358
    inc a
    sta.l SVActor_MetaData+2358
    cmp.l SVActor_MetaData+2352
    bcs SourceShare__commit
    brl SourceShare__validate
SourceShare__commit:
.a16
.i16
    ldx #0
SourceShare__copy:
.a16
.i16
    lda.l SourceVisual_ActorPieceMap,x
    and #$00FF
    sep #$20
.a8
    sta.l SourceVisual_ActorPieceMap+65,x
    rep #$30
.a16
.i16
    phx
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l SourceVisual_BlockCache+4,x
    ora #2
    sta.l SourceVisual_BlockCache+4,x
    rep #$30
.a16
.i16
    plx
    inx
    txa
    cmp.l SVActor_MetaData+2352
    bcc SourceShare__copy
    lda.l SVActor_MetaData+2354
    tax
    sep #$20
.a8
    lda.l SourceVisual_PaletteCache+4,x
    ora #2
    sta.l SourceVisual_PaletteCache+4,x
    lda.l SourceVisual_State+16
    sta.l SourceVisual_State+48
    lda #1
    sta.l SourceVisual_State+63
    rep #$30
.a16
.i16
    lda #0
    sta.l SourceVisual_State+44
    lda #1
    sta.l SourceVisual_State+46
    sta.l SourceVisual_State+36
    lda #2
    sta.l SourceVisual_State+38
SourceShare__done:
.a16
.i16
    ply
    plx
    pla
    plp
    rtl

; Keep completed immutable source blocks and Kula palette361 while
; both physical players are live Kula on Original stage0. These
; rows remain UNOWNED and ordinary mandatory allocations may evict them.
; No pins, jobs, new payloads or Ready writes are introduced.
SourceIdle_KeepBlock:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    txa
    cmp #512
    bcc SourceIdle_KeepBlock__guard0
    brl SourceIdle_KeepBlock__no
SourceIdle_KeepBlock__guard0:
.a16
.i16
    and #7
    beq SourceIdle_KeepBlock__guard1
    brl SourceIdle_KeepBlock__no
SourceIdle_KeepBlock__guard1:
.a16
.i16
    lda.l SourceVisual_BlockCache+2,x
    cmp #2
    beq SourceIdle_KeepBlock__guard2
    brl SourceIdle_KeepBlock__no
SourceIdle_KeepBlock__guard2:
.a16
.i16
    lda.l SourceVisual_BlockCache+4,x
    cmp #$0400
    beq SourceIdle_KeepBlock__guard3
    brl SourceIdle_KeepBlock__no
SourceIdle_KeepBlock__guard3:
.a16
.i16
    ; A completed startup WRAM upload is equally immutable in VRAM.
    ; Both kinds still require Ready, all four physical quarters, no tag,
    ; no owners, an in-catalog identity and the scoped normal source owner.
    lda.l SourceVisual_BlockCache+6,x
    cmp #1
    beq SourceIdle_KeepBlock__guard4
    cmp #2
    beq SourceIdle_KeepBlock__guard4
    brl SourceIdle_KeepBlock__no
SourceIdle_KeepBlock__guard4:
.a16
.i16
    ; Ready VRAM rows are immutable until the ordinary allocator evicts
    ; them. Keep every in-catalog identity as an UNOWNED eviction candidate,
    ; rather than clearing resident artwork on an unrelated actor release.
    ; State2/progress4/kind1-or2/tag0/owner0 were all checked above.
    lda.l SourceVisual_BlockCache,x
    cmp #SOURCE_VISUAL_BLOCK_COUNT
    bcc SourceIdle_KeepBlock__match
    brl SourceIdle_KeepBlock__no
SourceIdle_KeepBlock__match:
.a16
.i16
    jsr SourceIdle_KeepScope
    bcc SourceIdle_KeepBlock__no
SourceIdle_KeepBlock__yes:
.a16
.i16
    ply
    plx
    pla
    plp
    sec
    rtl
SourceIdle_KeepBlock__no:
.a16
.i16
    ply
    plx
    pla
    plp
    clc
    rtl

SourceIdle_KeepPalette:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    txa
    cmp #64
    bcc SourceIdle_KeepPalette__guard0
    brl SourceIdle_KeepPalette__no
SourceIdle_KeepPalette__guard0:
.a16
.i16
    and #7
    beq SourceIdle_KeepPalette__guard1
    brl SourceIdle_KeepPalette__no
SourceIdle_KeepPalette__guard1:
.a16
.i16
    lda.l SourceVisual_PaletteCache+3,x
    cmp #1
    beq SourceIdle_KeepPalette__guard2
    brl SourceIdle_KeepPalette__no
SourceIdle_KeepPalette__guard2:
.a16
.i16
    lda.l SourceVisual_PaletteCache,x
    cmp #361
    beq SourceIdle_KeepPalette__guard3
    brl SourceIdle_KeepPalette__no
SourceIdle_KeepPalette__guard3:
.a16
.i16

    jsr SourceIdle_KeepScope
    bcc SourceIdle_KeepPalette__no
SourceIdle_KeepPalette__yes:
.a16
.i16
    ply
    plx
    pla
    plp
    sec
    rtl
SourceIdle_KeepPalette__no:
.a16
.i16
    ply
    plx
    pla
    plp
    clc
    rtl

SourceIdle_KeepScope:
.a16
.i16
    lda.l $7E46DE
    beq SourceIdle_KeepScope__guard0
    brl SourceIdle_KeepScope__no
SourceIdle_KeepScope__guard0:
.a16
.i16
    lda.l Game_StageIndex
    beq SourceIdle_KeepScope__guard1
    brl SourceIdle_KeepScope__no
SourceIdle_KeepScope__guard1:
.a16
.i16
    jsr SourceNpc_Scope
    bcs SourceIdle_KeepScope__guard2
    brl SourceIdle_KeepScope__no
SourceIdle_KeepScope__guard2:
.a16
.i16
    ldx #0
SourceIdle_KeepScope__player:
.a16
.i16
    lda.l $7E0A00+CHAR_HP,x
    and #$00FF
    bne SourceIdle_KeepScope__native0
    brl SourceIdle_KeepScope__no
SourceIdle_KeepScope__native0:
.a16
.i16
    lda.l $7E0A00+CHAR_INPUT_DRIVEN,x
    and #$00FF
    cmp #1
    beq SourceIdle_KeepScope__native1
    brl SourceIdle_KeepScope__no
SourceIdle_KeepScope__native1:
.a16
.i16
    lda.l $7E0A00+CHAR_ROSTER_INDEX,x
    and #$00FF
    cmp #22
    beq SourceIdle_KeepScope__native2
    brl SourceIdle_KeepScope__no
SourceIdle_KeepScope__native2:
.a16
.i16
    lda.l $7E0A00+CHAR_MAP_INDEX,x
    and #$00FF
    beq SourceIdle_KeepScope__native3
    brl SourceIdle_KeepScope__no
SourceIdle_KeepScope__native3:
.a16
.i16
    ; Cache validity is independent of a live player's current pose.
    ; Attacks, hurt and jumps may reuse the same immutable rows later.
    ; Live HP/input/model/map and normal source ownership remain required.
    bra SourceIdle_KeepScope__native4
SourceIdle_KeepScope__native4:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy,x
    and #$00FF
    cmp #2
    beq SourceIdle_KeepScope__native5
    brl SourceIdle_KeepScope__no
SourceIdle_KeepScope__native5:
.a16
.i16
    bra SourceIdle_KeepScope__native6
SourceIdle_KeepScope__native6:
.a16
.i16
    txa
    clc
    adc #133
    tax
    cpx #266
    bcs SourceIdle_KeepScope__yes
    brl SourceIdle_KeepScope__player
SourceIdle_KeepScope__yes:
.a16
.i16
    sec
    rts
SourceIdle_KeepScope__no:
.a16
.i16
    clc
    rts
SourceIdle_KeepIds:
    .dw 559,559,3618,559,12228,559,559,559,559,2633,8842,559,559,559,559,559,559,559,559,559,559,559,559,559,1592,559,559,559,559,559,5886,559
SourceIdle_KeepIdsSecond:
    .dw 559,559,559,559,559,559,559,559,559,7241,559,559,559,559,559,11343,559,559,559,559,559,559,559,559,13304,559,559,559,559,559,559,559


; Avoid redoing the same first-walk preparation for P2 while P1 is
; already its live producer. No queued wakeup, ownership, readiness, media
; or request writes. Cancellation/role/key changes immediately resume the
; original P2 path. P1 still uses the ordinary loader and physical fences.
SourceShare_DeferDuplicateP2:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    lda.l SourceVisual_ActorSlot
    cmp #1
    beq SourceShare_Defer__guard0
    brl SourceShare_Defer__no
SourceShare_Defer__guard0:
.a16
.i16
    lda.l SourceVisual_Record
    cmp #32
    beq SourceShare_Defer__guard1
    brl SourceShare_Defer__no
SourceShare_Defer__guard1:
.a16
.i16
    lda.l $7E46DE
    beq SourceShare_Defer__guard2
    brl SourceShare_Defer__no
SourceShare_Defer__guard2:
.a16
.i16
    jsr SourceNpc_Scope
    bcs SourceShare_Defer__guard3
    brl SourceShare_Defer__no
SourceShare_Defer__guard3:
.a16
.i16
    lda.l Game_StageIndex
    beq SourceShare_Defer__guard4
    brl SourceShare_Defer__no
SourceShare_Defer__guard4:
.a16
.i16
    lda.l $7E0A00+0+CHAR_HP
    and #$00FF
    bne SourceShare_Defer__guard5
    brl SourceShare_Defer__no
SourceShare_Defer__guard5:
.a16
.i16
    lda.l $7E0A00+0+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    beq SourceShare_Defer__guard6
    brl SourceShare_Defer__no
SourceShare_Defer__guard6:
.a16
.i16
    lda.l $7E0A00+0+CHAR_ROSTER_INDEX
    and #$00FF
    cmp #22
    beq SourceShare_Defer__guard7
    brl SourceShare_Defer__no
SourceShare_Defer__guard7:
.a16
.i16
    lda.l $7E0A00+0+CHAR_MAP_INDEX
    and #$00FF
    cmp #0
    beq SourceShare_Defer__guard8
    brl SourceShare_Defer__no
SourceShare_Defer__guard8:
.a16
.i16
    lda.l $7E0A00+0+CHAR_SELECTED
    and #$00FF
    cmp #3
    bcc SourceShare_Defer__guard9
    brl SourceShare_Defer__no
SourceShare_Defer__guard9:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy+0
    and #$00FF
    cmp #2
    beq SourceShare_Defer__guard10
    brl SourceShare_Defer__no
SourceShare_Defer__guard10:
.a16
.i16
    lda.l SourceVisual_Sa1RuntimeRole+0
    and #$00FF
    cmp #1
    beq SourceShare_Defer__guard11
    brl SourceShare_Defer__no
SourceShare_Defer__guard11:
.a16
.i16
    lda.l StageBounds_State+0
    beq SourceShare_Defer__guard12
    brl SourceShare_Defer__no
SourceShare_Defer__guard12:
.a16
.i16
    lda.l $7E0A00+133+CHAR_HP
    and #$00FF
    bne SourceShare_Defer__guard13
    brl SourceShare_Defer__no
SourceShare_Defer__guard13:
.a16
.i16
    lda.l $7E0A00+133+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    beq SourceShare_Defer__guard14
    brl SourceShare_Defer__no
SourceShare_Defer__guard14:
.a16
.i16
    lda.l $7E0A00+133+CHAR_ROSTER_INDEX
    and #$00FF
    cmp #22
    beq SourceShare_Defer__guard15
    brl SourceShare_Defer__no
SourceShare_Defer__guard15:
.a16
.i16
    lda.l $7E0A00+133+CHAR_MAP_INDEX
    and #$00FF
    cmp #0
    beq SourceShare_Defer__guard16
    brl SourceShare_Defer__no
SourceShare_Defer__guard16:
.a16
.i16
    lda.l $7E0A00+133+CHAR_SELECTED
    and #$00FF
    cmp #3
    bcc SourceShare_Defer__guard17
    brl SourceShare_Defer__no
SourceShare_Defer__guard17:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy+133
    and #$00FF
    cmp #2
    beq SourceShare_Defer__guard18
    brl SourceShare_Defer__no
SourceShare_Defer__guard18:
.a16
.i16
    lda.l SourceVisual_Sa1RuntimeRole+133
    and #$00FF
    cmp #1
    beq SourceShare_Defer__guard19
    brl SourceShare_Defer__no
SourceShare_Defer__guard19:
.a16
.i16
    lda.l StageBounds_State+133
    beq SourceShare_Defer__guard20
    brl SourceShare_Defer__no
SourceShare_Defer__guard20:
.a16
.i16
    lda.l SourceVisual_State+0+6
    cmp #1
    beq SourceShare_Defer__guard21
    brl SourceShare_Defer__no
SourceShare_Defer__guard21:
.a16
.i16
    lda.l SourceVisual_State+0+28
    and #$00FF
    beq SourceShare_Defer__guard22
    brl SourceShare_Defer__no
SourceShare_Defer__guard22:
.a16
.i16
    lda.l SourceVisual_State+0+29
    cmp #$0116
    beq SourceShare_Defer__guard23
    brl SourceShare_Defer__no
SourceShare_Defer__guard23:
.a16
.i16
    lda.l SourceVisual_State+32+6
    cmp #1
    beq SourceShare_Defer__guard24
    brl SourceShare_Defer__no
SourceShare_Defer__guard24:
.a16
.i16
    lda.l SourceVisual_State+32+28
    and #$00FF
    beq SourceShare_Defer__guard25
    brl SourceShare_Defer__no
SourceShare_Defer__guard25:
.a16
.i16
    lda.l SourceVisual_State+32+29
    cmp #$0116
    beq SourceShare_Defer__guard26
    brl SourceShare_Defer__no
SourceShare_Defer__guard26:
.a16
.i16
    ; Mode1 alone is only an intent. Do not suppress P2's first useful
    ; preparation before P1 has executed its lease-pinning visit.
    lda.l SourceVisual_State+31
    and #$00FF
    cmp #1
    beq SourceShare_Defer__producer_started
    brl SourceShare_Defer__no
SourceShare_Defer__producer_started:
.a16
.i16
    lda.l SourceVisual_Key
    cmp #$0116
    beq SourceShare_Defer__guard27
    brl SourceShare_Defer__no
SourceShare_Defer__guard27:
.a16
.i16
    lda.l SourceVisual_Key+2
    cmp #10
    bcc SourceShare_Defer__guard28
    brl SourceShare_Defer__no
SourceShare_Defer__guard28:
.a16
.i16
    lda.l SourceVisual_State
    cmp.l SourceVisual_State+32
    beq SourceShare_Defer__guard29
    brl SourceShare_Defer__no
SourceShare_Defer__guard29:
.a16
.i16
    cmp.l SourceVisual_EntryIndexSaved
    beq SourceShare_Defer__guard30
    brl SourceShare_Defer__no
SourceShare_Defer__guard30:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    cmp #1
    beq SourceShare_Defer__guard31
    brl SourceShare_Defer__no
SourceShare_Defer__guard31:
.a16
.i16
    lda.l SourceVisual_CompletedStage
    beq SourceShare_Defer__guard32
    brl SourceShare_Defer__no
SourceShare_Defer__guard32:
.a16
.i16
    lda.l SourceVisual_CompletedRoster
    cmp #22
    beq SourceShare_Defer__guard33
    brl SourceShare_Defer__no
SourceShare_Defer__guard33:
.a16
.i16
    lda.l SourceVisual_CompletedEntry
    cmp #22
    beq SourceShare_Defer__guard34
    brl SourceShare_Defer__no
SourceShare_Defer__guard34:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+3
    and #$00FF
    beq SourceShare_Defer__guard35
    brl SourceShare_Defer__no
SourceShare_Defer__guard35:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourceShare_Defer__guard36
    brl SourceShare_Defer__no
SourceShare_Defer__guard36:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage
    beq SourceShare_Defer__guard37
    brl SourceShare_Defer__no
SourceShare_Defer__guard37:
.a16
.i16
    lda.l SVActor_Data+SVActor_Roster
    cmp #22
    beq SourceShare_Defer__guard38
    brl SourceShare_Defer__no
SourceShare_Defer__guard38:
.a16
.i16
    lda.l SVActor_Data
    cmp #22
    beq SourceShare_Defer__guard39
    brl SourceShare_Defer__no
SourceShare_Defer__guard39:
.a16
.i16
    lda.l SVActor_Data+3
    and #$00FF
    beq SourceShare_Defer__guard40
    brl SourceShare_Defer__no
SourceShare_Defer__guard40:
.a16
.i16
    ply
    plx
    pla
    plp
    sec
    rtl
SourceShare_Defer__no:
.a16
.i16
    ply
    plx
    pla
    plp
    clc
    rtl
