; Foreground completion only. Never allocate/read a tile payload or bypass
; an active DMA fence. Normal LoadResources/palette/emission/retirement remains
; the sole publication path. Only a physical player attack or live jump.
SourceCritical_Completing = $7E5F40
SourceCritical_Entry = $7E5F42
SourceCritical_Stage = $7E5F44
SourceCritical_Meta = $7E5F46
SourceCritical_Count = $7E5F48
SourceCritical_Index = $7E5F4A
SourceCritical_Owner = $7E5F4C
SourceCritical_Role = $7E5F4E
SourceCritical_CompleteReady:
.a16
.i16
    ; Do not touch BW-RAM during legacy CC-DMA/startup. The persistent
    ; worker disables conversion before declaring ownership state2.
    php
    rep #$30
    phx
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq SourceCritical_Preflight0
    brl SourceCritical_Preflight__no
SourceCritical_Preflight0:
.a16
.i16
    lda.l Game_State
    cmp #0
    beq SourceCritical_Preflight1
    brl SourceCritical_Preflight__no
SourceCritical_Preflight1:
.a16
.i16
    lda.l SourceVisual_ServiceOnly
    cmp #0
    beq SourceCritical_Preflight2
    brl SourceCritical_Preflight__no
SourceCritical_Preflight2:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SourceCritical_Preflight3
    brl SourceCritical_Preflight__no
SourceCritical_Preflight3:
.a16
.i16
    lda.l $7E1760
    cmp #1
    beq SourceCritical_Preflight4
    brl SourceCritical_Preflight__no
SourceCritical_Preflight4:
.a16
.i16
    lda.l $7E175E
    cmp #2
    beq SourceCritical_Preflight5
    brl SourceCritical_Preflight__no
SourceCritical_Preflight5:
.a16
.i16
    lda.l $7E46DC
    cmp #1
    beq SourceCritical_Preflight6
    brl SourceCritical_Preflight__no
SourceCritical_Preflight6:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #2
    bcc SourceCritical_Preflight7
    brl SourceCritical_Preflight__no
SourceCritical_Preflight7:
.a16
.i16
    asl a
    asl a
    asl a
    asl a
    asl a
    cmp.l SourceVisual_Record
    beq SourceCritical_Preflight8
    brl SourceCritical_Preflight__no
SourceCritical_Preflight8:
.a16
.i16
    tax
    lda.l SourceVisual_State+6,x
    cmp #1
    beq SourceCritical_Preflight9
    brl SourceCritical_Preflight__no
SourceCritical_Preflight9:
.a16
.i16
    lda.l SourceVisual_State+30,x
    and #$00FF
    cmp #2
    beq SourceCritical_Preflight__yes
    cmp #7
    beq SourceCritical_Preflight__yes
    cmp #0
    bne SourceCritical_Preflight__no
    jsl SourceIdle_CanFinish
    bcs SourceCritical_Preflight__yes
SourceCritical_Preflight__no:
.a16
.i16
    plx
    plp
    clc
    rtl
SourceCritical_Preflight__yes:
.a16
.i16
    plx
    plp
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq SourceCritical_CompleteReady__enter
    clc
    rtl
SourceCritical_CompleteReady__enter:
.a16
.i16
    php
    rep #$30
    phx
    phy
    lda.l SourceVisual_BlockIndex
    pha
    lda.l SourceVisual_BlockRecord
    pha
    lda.l SourceVisual_BlockSlot
    pha
    lda.l SourceVisual_PieceIndex
    pha
    lda.l SourceVisual_ActorMapBase
    pha
    lda.l SourceVisual_BlockScan
    pha
    lda.l SourceRom_Index
    pha
    lda.l SourceRom_Bank
    pha
    lda.l SourceRom_Address
    pha
    lda.l SourceRom_DmaScan
    pha
    lda.l SourceVisual_BucketBase
    pha
    lda.l SourceVisual_BucketBits
    pha
    lda.l SourceVisual_BucketMask
    pha
    lda.l SVActor_MetaBase
    pha
    lda #0
    sta.l SourceCritical_Completing
    lda.l SourceVisual_CompletedMagic
    cmp #$C04D
    beq SourceCritical_CompleteReady__guard0
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard0:
.a16
.i16
    lda.l SVActor_Magic
    cmp #$AC19
    beq SourceCritical_CompleteReady__guard1
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard1:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SourceCritical_CompleteReady__guard2
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard2:
.a16
.i16
    lda.l Game_State
    cmp #0
    beq SourceCritical_CompleteReady__guard3
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard3:
.a16
.i16
    lda.l Stage_Mirror
    and #$00FF
    cmp #0
    beq SourceCritical_CompleteReady__guard4
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard4:
.a16
.i16
    lda.l SourceVisual_ServiceOnly
    cmp #0
    beq SourceCritical_CompleteReady__guard5
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard5:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #2
    bcc SourceCritical_CompleteReady__guard6
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard6:
.a16
.i16
    inc a
    sta.l SourceCritical_Owner
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    asl a
    cmp.l SourceVisual_Record
    beq SourceCritical_CompleteReady__guard7
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard7:
.a16
.i16
    tax
    lda.l SourceVisual_State,x
    cmp.l SourceVisual_EntryIndexSaved
    beq SourceCritical_CompleteReady__guard8
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard8:
.a16
.i16
    lda.l SourceVisual_State+6,x
    cmp #1
    beq SourceCritical_CompleteReady__guard9
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard9:
.a16
.i16
    lda.l SourceVisual_State+28,x
    and #$00FF
    beq SourceCritical_CompleteReady__guard10
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard10:
.a16
.i16
    sep #$20
.a8
    lda CHAR_ROSTER_INDEX
    cmp.l SourceVisual_State+29,x
    rep #$30
.a16
.i16
    beq SourceCritical_CompleteReady__guard11
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard11:
.a16
.i16
    lda.l SourceVisual_State+30,x
    and #$00FF
    sta.l SourceCritical_Role
    cmp #2
    beq SourceCritical_CompleteReady__attack
    cmp #7
    beq SourceCritical_CompleteReady__jump
    cmp #0
    beq SourceCritical_CompleteReady__first_idle
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__first_idle:
.a16
.i16
    jsl SourceIdle_CanFinish
    bcs SourceCritical_CompleteReady__idle_eligible
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__idle_eligible:
.a16
.i16
    brl SourceCritical_CompleteReady__physical
SourceCritical_CompleteReady__jump:
.a16
.i16
    lda CHAR_SELECTED
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
    beq SourceCritical_CompleteReady__guard12
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard12:
.a16
.i16
    bra SourceCritical_CompleteReady__physical
SourceCritical_CompleteReady__attack:
.a16
.i16
    lda CHAR_SELECTED
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
    bne SourceCritical_CompleteReady__guard13
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard13:
.a16
.i16
SourceCritical_CompleteReady__physical:
.a16
.i16
    lda CHAR_HP
    and #$00FF
    bne SourceCritical_CompleteReady__guard14
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard14:
.a16
.i16
    lda CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    beq SourceCritical_CompleteReady__guard15
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard15:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    beq SourceCritical_CompleteReady__p1
    tdc
    cmp #$0A85
    beq SourceCritical_CompleteReady__dp
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__p1:
.a16
.i16
    tdc
    cmp #$0A00
    beq SourceCritical_CompleteReady__dp
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__dp:
.a16
.i16
    tdc
    sec
    sbc #$0A00
    tax
    lda.l SourceVisual_Sa1OwnerPolicy,x
    and #$00FF
    cmp #2
    beq SourceCritical_CompleteReady__guard16
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard16:
.a16
.i16
    ; First idle may still have the previous walk's raw metadata, even when
    ; all idle blocks remain physically resident. Warm only its ten rows.
    lda.l SourceCritical_Role
    bne SourceCritical_CompleteReady__metadata_warm
    jsl SourceCritical_Bridge_SourceIdleMetadata
SourceCritical_CompleteReady__metadata_warm:
.a16
.i16
    jsl SourceCritical_Bridge_SVActor_MetaMatch
    bcs SourceCritical_CompleteReady__guard17
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard17:
.a16
.i16
    txa
    sta.l SourceCritical_Meta
    lda.l SVActor_MetaData+2,x
    cmp #1
    bcs SourceCritical_CompleteReady__guard18
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard18:
.a16
.i16
    cmp #66
    bcc SourceCritical_CompleteReady__guard19
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard19:
.a16
.i16
    sta.l SourceCritical_Count
    lda.l SourceVisual_EntryScratch+12
    and #$00FF
    cmp.l SourceCritical_Count
    beq SourceCritical_CompleteReady__guard20
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard20:
.a16
.i16
    sep #$20
.a8
    lda CHAR_ROSTER_INDEX
    cmp.l SVActor_MetaData+4,x
    rep #$30
.a16
.i16
    beq SourceCritical_CompleteReady__guard21
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard21:
.a16
.i16
    sep #$20
.a8
    lda CHAR_MAP_INDEX
    cmp.l SVActor_MetaData+7,x
    rep #$30
.a16
.i16
    beq SourceCritical_CompleteReady__guard22
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard22:
.a16
.i16
    lda.l SVActor_MetaData+5,x
    and #$00FF
    cmp.l SourceCritical_Role
    beq SourceCritical_CompleteReady__guard23
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard23:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    clc
    adc.l SourceVisual_ActorSlot
    sta.l SourceVisual_ActorMapBase
    lda #0
    sta.l SourceCritical_Index
SourceCritical_CompleteReady__piece:
.a16
.i16
    lda.l SourceCritical_Index
    sta.l SourceVisual_PieceIndex
    asl a
    asl a
    asl a
    asl a
    clc
    adc.l SourceCritical_Meta
    tax
    lda.l SVActor_MetaData+40,x
    sta.l SourceVisual_BlockIndex
    jsl SourceCritical_Bridge_SourceVisual_FindBlock
    bcs SourceCritical_CompleteReady__guard24
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard24:
.a16
.i16
    lda.l SourceVisual_BlockCache+2,x
    cmp #2
    bne SourceCritical_CompleteReady__not_ready
    brl SourceCritical_CompleteReady__next
SourceCritical_CompleteReady__not_ready:
.a16
.i16
    cmp #1
    beq SourceCritical_CompleteReady__guard25
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard25:
.a16
.i16
    lda.l SourceVisual_BlockCache+5,x
    and #$00FF
    cmp #4
    beq SourceCritical_CompleteReady__guard26
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard26:
.a16
.i16
    lda.l SourceVisual_BlockCache+6,x
    and #$00FF
    cmp #2
    beq SourceCritical_CompleteReady__rom
    cmp #1
    beq SourceCritical_CompleteReady__wram
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__rom:
.a16
.i16
    jsl SourceCritical_Bridge_SourceRom_ResolveTagged
    bcs SourceCritical_CompleteReady__guard27
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard27:
.a16
.i16
    jsl SourceCritical_Bridge_SourceRom_HasBlockDma
    bcc SourceCritical_CompleteReady__guard28
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard28:
.a16
.i16
    bra SourceCritical_CompleteReady__retired
SourceCritical_CompleteReady__wram:
.a16
.i16
    lda.l SourceRom_StagingMagic
    cmp #$5357
    beq SourceCritical_CompleteReady__guard29
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard29:
.a16
.i16
    lda.l SourceRom_StagingRecord
    cmp.l SourceVisual_BlockRecord
    beq SourceCritical_CompleteReady__guard30
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard30:
.a16
.i16
    lda.l SourceRom_StagingBlock
    cmp.l SourceVisual_BlockIndex
    beq SourceCritical_CompleteReady__guard31
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard31:
.a16
.i16
    jsl SourceCritical_Bridge_SourceRom_HasStagingDma
    bcc SourceCritical_CompleteReady__guard32
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__guard32:
.a16
.i16
SourceCritical_CompleteReady__retired:
.a16
.i16
    lda.l SourceVisual_BlockRecord
    tax
    jsl SourcePrefetch_CanRetire
    bcs SourceCritical_CompleteReady__retire_allowed
    brl SourceCritical_CompleteReady__done
SourceCritical_CompleteReady__retire_allowed:
.a16
.i16
    lda #2
    sta.l SourceVisual_BlockCache+2,x
SourceCritical_CompleteReady__next:
.a16
.i16
    lda.l SourceCritical_Index
    inc a
    sta.l SourceCritical_Index
    cmp.l SourceCritical_Count
    bcs SourceCritical_CompleteReady__ready
    brl SourceCritical_CompleteReady__piece
SourceCritical_CompleteReady__ready:
.a16
.i16
    lda.l SourceVisual_EntryIndexSaved
    sta.l SourceCritical_Entry
    lda.l Game_StageIndex
    sta.l SourceCritical_Stage
    lda #1
    sta.l SourceCritical_Completing
SourceCritical_CompleteReady__done:
.a16
.i16
    pla
    sta.l SVActor_MetaBase
    pla
    sta.l SourceVisual_BucketMask
    pla
    sta.l SourceVisual_BucketBits
    pla
    sta.l SourceVisual_BucketBase
    pla
    sta.l SourceRom_DmaScan
    pla
    sta.l SourceRom_Address
    pla
    sta.l SourceRom_Bank
    pla
    sta.l SourceRom_Index
    pla
    sta.l SourceVisual_BlockScan
    pla
    sta.l SourceVisual_ActorMapBase
    pla
    sta.l SourceVisual_PieceIndex
    pla
    sta.l SourceVisual_BlockSlot
    pla
    sta.l SourceVisual_BlockRecord
    pla
    sta.l SourceVisual_BlockIndex
    ply
    plx
    plp
    lda.l SourceCritical_Completing
    cmp #1
    beq SourceCritical_Return__yes
    clc
    rtl
SourceCritical_Return__yes:
.a16
.i16
    sec
    rtl

SourceCritical_CodeEnd:
