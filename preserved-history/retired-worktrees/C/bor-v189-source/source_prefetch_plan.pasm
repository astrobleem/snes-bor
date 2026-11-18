; Unhooked, read-only bounded prefetch planner. A=hot index0..21.
; No allocation, enqueue, Ready, actor, input, world or timing writes.
; Private foreground scratch occupies unused P1 raw-metadata tail.
SourcePrefetch_Plan = $433430
SourcePrefetch_PlanOnly:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    phd
    cmp #22
    bcc SourcePrefetch_PlanOnly__guard0
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard0:
.a16
.i16
    lda.l $7E46DE
    beq SourcePrefetch_PlanOnly__guard1
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard1:
.a16
.i16
    jsr SourceNpc_Scope
    bcs SourcePrefetch_PlanOnly__guard2
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard2:
.a16
.i16
    lda.l Game_StageIndex
    beq SourcePrefetch_PlanOnly__guard3
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard3:
.a16
.i16
    lda.l Nmi_FrameBusy
    and #$00FF
    cmp #2
    bcc SourcePrefetch_PlanOnly__guard4
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard4:
.a16
.i16
    lda.l SourcePrefetch_PhysicalPending
    beq SourcePrefetch_PlanOnly__guard5
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard5:
.a16
.i16
    lda.l $7E0A00+0+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    beq SourcePrefetch_PlanOnly__guard6
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard6:
.a16
.i16
    lda.l $7E0A00+0+CHAR_ROSTER_INDEX
    and #$00FF
    cmp #22
    beq SourcePrefetch_PlanOnly__guard7
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard7:
.a16
.i16
    lda.l $7E0A00+0+CHAR_MAP_INDEX
    and #$00FF
    cmp #0
    beq SourcePrefetch_PlanOnly__guard8
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard8:
.a16
.i16
    lda.l $7E0A00+0+CHAR_HP
    and #$00FF
    bne SourcePrefetch_PlanOnly__guard9
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard9:
.a16
.i16
    lda.l $7E0A00+0+CHAR_SELECTED
    and #$00FF
    cmp #3
    bcc SourcePrefetch_PlanOnly__guard10
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard10:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy+0
    and #$00FF
    cmp #2
    beq SourcePrefetch_PlanOnly__guard11
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard11:
.a16
.i16
    lda.l SourceVisual_Sa1RuntimeRole+0
    and #$00FF
    cmp #0
    beq SourcePrefetch_PlanOnly__guard12
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard12:
.a16
.i16
    lda.l SourceVisual_State+0+6
    cmp #2
    beq SourcePrefetch_PlanOnly__guard13
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard13:
.a16
.i16
    lda.l SourceVisual_State+0+28
    and #$00FF
    cmp #1
    beq SourcePrefetch_PlanOnly__guard14
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard14:
.a16
.i16
    lda.l SourceVisual_State+0+29
    cmp #22
    beq SourcePrefetch_PlanOnly__guard15
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard15:
.a16
.i16
    lda.l $7E0A00+133+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    beq SourcePrefetch_PlanOnly__guard16
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard16:
.a16
.i16
    lda.l $7E0A00+133+CHAR_ROSTER_INDEX
    and #$00FF
    cmp #22
    beq SourcePrefetch_PlanOnly__guard17
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard17:
.a16
.i16
    lda.l $7E0A00+133+CHAR_MAP_INDEX
    and #$00FF
    cmp #0
    beq SourcePrefetch_PlanOnly__guard18
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard18:
.a16
.i16
    lda.l $7E0A00+133+CHAR_HP
    and #$00FF
    bne SourcePrefetch_PlanOnly__guard19
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard19:
.a16
.i16
    lda.l $7E0A00+133+CHAR_SELECTED
    and #$00FF
    cmp #3
    bcc SourcePrefetch_PlanOnly__guard20
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard20:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy+133
    and #$00FF
    cmp #2
    beq SourcePrefetch_PlanOnly__guard21
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard21:
.a16
.i16
    lda.l SourceVisual_Sa1RuntimeRole+133
    and #$00FF
    cmp #0
    beq SourcePrefetch_PlanOnly__guard22
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard22:
.a16
.i16
    lda.l SourceVisual_State+32+6
    cmp #2
    beq SourcePrefetch_PlanOnly__guard23
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard23:
.a16
.i16
    lda.l SourceVisual_State+32+28
    and #$00FF
    cmp #1
    beq SourcePrefetch_PlanOnly__guard24
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard24:
.a16
.i16
    lda.l SourceVisual_State+32+29
    cmp #22
    beq SourcePrefetch_PlanOnly__guard25
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard25:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    cmp #1
    beq SourcePrefetch_PlanOnly__guard26
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard26:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourcePrefetch_PlanOnly__guard27
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard27:
.a16
.i16
    lda.l $434E7E
    cmp #$4D50
    beq SourcePrefetch_PlanOnly__snapshot_magic
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__snapshot_magic:
.a16
.i16
    lda.l $434E2C
    cmp #0
    beq SourcePrefetch_PlanOnly__snapshot0
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__snapshot0:
.a16
.i16
    lda.l $434E9C
    cmp #0
    beq SourcePrefetch_PlanOnly__snapshot1
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__snapshot1:
.a16
.i16
    lda.l $434E9E
    cmp #133
    beq SourcePrefetch_PlanOnly__snapshot2
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__snapshot2:
.a16
.i16
    lda.l $434E3C
    cmp #9
    beq SourcePrefetch_PlanOnly__snapshot3
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__snapshot3:
.a16
.i16
    lda.l $434E40
    cmp #1
    beq SourcePrefetch_PlanOnly__snapshot4
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__snapshot4:
.a16
.i16
    lda.l $434E42
    cmp #0
    beq SourcePrefetch_PlanOnly__snapshot5
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__snapshot5:
.a16
.i16
    lda.l $434E4A
    cmp #2
    beq SourcePrefetch_PlanOnly__snapshot6
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__snapshot6:
.a16
.i16
    lda.l $434E50
    cmp #0
    beq SourcePrefetch_PlanOnly__snapshot7
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__snapshot7:
.a16
.i16
    lda.l $434E54
    cmp #8
    beq SourcePrefetch_PlanOnly__snapshot8
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__snapshot8:
.a16
.i16
    lda.l $434E60
    cmp #9
    beq SourcePrefetch_PlanOnly__snapshot9
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__snapshot9:
.a16
.i16
    lda.l $434E64
    cmp #1
    beq SourcePrefetch_PlanOnly__snapshot10
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__snapshot10:
.a16
.i16
    lda.l $434E66
    cmp #0
    beq SourcePrefetch_PlanOnly__snapshot11
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__snapshot11:
.a16
.i16
    lda.l $434E6E
    cmp #2
    beq SourcePrefetch_PlanOnly__snapshot12
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__snapshot12:
.a16
.i16
    lda.l $434E74
    cmp #0
    beq SourcePrefetch_PlanOnly__snapshot13
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__snapshot13:
.a16
.i16
    lda.l $434E78
    cmp #8
    beq SourcePrefetch_PlanOnly__snapshot14
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__snapshot14:
.a16
.i16
    lda.l $434E7C
    bit #1
    beq SourcePrefetch_PlanOnly__snapshot_even
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__snapshot_even:
.a16
.i16
    sta.l SourcePrefetch_Plan+30
    lda 8,s
    asl a
    tax
    lda.l SourcePrefetch_HotIds,x
    sta.l SourcePrefetch_Plan
    lda.l SourcePrefetch_HotBanks,x
    sta.l SourcePrefetch_Plan+2
    lda.l SourcePrefetch_HotAddresses,x
    sta.l SourcePrefetch_Plan+4
    lda.l SourceInput_Producer
    cmp #64
    bcc SourcePrefetch_PlanOnly__guard28
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard28:
.a16
.i16
    sta.l SourcePrefetch_Plan+12
    lda.l SourceInput_Consumer
    cmp #64
    bcc SourcePrefetch_PlanOnly__guard29
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard29:
.a16
.i16
    sta.l SourcePrefetch_Plan+14
SourcePrefetch_PlanOnly__input:
.a16
.i16
    lda.l SourcePrefetch_Plan+14
    cmp.l SourcePrefetch_Plan+12
    beq SourcePrefetch_PlanOnly__latest
    asl a
    asl a
    tax
    lda.l SourceInput_Ring,x
    ora.l SourceInput_Ring+2,x
    beq SourcePrefetch_PlanOnly__guard30
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard30:
.a16
.i16
    lda.l SourcePrefetch_Plan+14
    inc a
    and #63
    sta.l SourcePrefetch_Plan+14
    brl SourcePrefetch_PlanOnly__input
SourcePrefetch_PlanOnly__latest:
.a16
.i16
    lda.l SourcePrefetch_Plan+12
    dec a
    and #63
    asl a
    asl a
    tax
    lda.l SourceInput_Ring,x
    ora.l SourceInput_Ring+2,x
    beq SourcePrefetch_PlanOnly__guard31
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard31:
.a16
.i16
    lda #0
    sta.l SourcePrefetch_Plan+16
    sta.l SourcePrefetch_Plan+18
    ldx #0
SourcePrefetch_PlanOnly__queue:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourcePrefetch_PlanOnly__queue_active
    brl SourcePrefetch_PlanOnly__queue_next
SourcePrefetch_PlanOnly__queue_active:
.a16
.i16
    phx
    txa
    lsr a
    lsr a
    lsr a
    tax
    lda.l DmaQueue_Owner,x
    and #$00FF
    plx
    beq SourcePrefetch_PlanOnly__guard32
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard32:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$00FF
    cmp #$40
    beq SourcePrefetch_PlanOnly__vram
    cmp #$41
    beq SourcePrefetch_PlanOnly__oam
    cmp #$42
    beq SourcePrefetch_PlanOnly__guard33
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard33:
.a16
.i16
    lda.l DmaQueue,x
    cmp #1
    bcs SourcePrefetch_PlanOnly__guard34
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard34:
.a16
.i16
    cmp #33
    bcc SourcePrefetch_PlanOnly__guard35
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard35:
.a16
.i16
    clc
    adc.l DmaQueue+2,x
    bcc SourcePrefetch_PlanOnly__guard36
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard36:
.a16
.i16
    cmp #513
    bcc SourcePrefetch_PlanOnly__guard37
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard37:
.a16
.i16
    brl SourcePrefetch_PlanOnly__queue_add
SourcePrefetch_PlanOnly__oam:
.a16
.i16
    lda.l DmaQueue,x
    cmp #1
    bcs SourcePrefetch_PlanOnly__guard38
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard38:
.a16
.i16
    cmp #545
    bcc SourcePrefetch_PlanOnly__guard39
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard39:
.a16
.i16
    lda.l DmaQueue+2,x
    beq SourcePrefetch_PlanOnly__guard40
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard40:
.a16
.i16
    brl SourcePrefetch_PlanOnly__queue_add
SourcePrefetch_PlanOnly__vram:
.a16
.i16
    lda.l DmaQueue,x
    cmp #1
    bcs SourcePrefetch_PlanOnly__guard41
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard41:
.a16
.i16
    cmp #257
    bcc SourcePrefetch_PlanOnly__guard42
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard42:
.a16
.i16
    dec a
    clc
    adc.l DmaQueue+2,x
    bcc SourcePrefetch_PlanOnly__guard43
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard43:
.a16
.i16
    cmp #$8000
    bcc SourcePrefetch_PlanOnly__queue_add
    lda.l DmaQueue+2,x
    cmp #$C000
    bcs SourcePrefetch_PlanOnly__guard44
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard44:
.a16
.i16
SourcePrefetch_PlanOnly__queue_add:
.a16
.i16
    lda.l DmaQueue,x
    clc
    adc.l SourcePrefetch_Plan+16
    bcc SourcePrefetch_PlanOnly__guard45
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard45:
.a16
.i16
    sta.l SourcePrefetch_Plan+16
    lda.l SourcePrefetch_Plan+18
    inc a
    sta.l SourcePrefetch_Plan+18
SourcePrefetch_PlanOnly__queue_next:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcs SourcePrefetch_PlanOnly__queue_done
    brl SourcePrefetch_PlanOnly__queue
SourcePrefetch_PlanOnly__queue_done:
.a16
.i16
    lda.l SourcePrefetch_Plan+16
    cmp.l DmaQueue_BudgetTotal
    beq SourcePrefetch_PlanOnly__guard46
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard46:
.a16
.i16
    cmp #1025
    bcc SourcePrefetch_PlanOnly__guard47
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard47:
.a16
.i16
    lda.l SourcePrefetch_Plan+18
    cmp #7
    bcc SourcePrefetch_PlanOnly__guard48
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard48:
.a16
.i16
    lda.l DmaQueue_CurrentSlot
    and #7
    beq SourcePrefetch_PlanOnly__guard49
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard49:
.a16
.i16
    ldx #0
SourcePrefetch_PlanOnly__cache:
.a16
.i16
    lda.l SourceVisual_BlockCache+2,x
    beq SourcePrefetch_PlanOnly__cache_next
    cmp #1
    beq SourcePrefetch_PlanOnly__pending
    cmp #2
    beq SourcePrefetch_PlanOnly__guard50
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard50:
.a16
.i16
    bra SourcePrefetch_PlanOnly__present
SourcePrefetch_PlanOnly__pending:
.a16
.i16
    lda.l SourceVisual_BlockCache+5,x
    and #$00FF
    cmp #4
    beq SourcePrefetch_PlanOnly__guard51
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard51:
.a16
.i16
    lda.l SourceVisual_BlockCache+6,x
    cmp #1
    beq SourcePrefetch_PlanOnly__present
    cmp #2
    beq SourcePrefetch_PlanOnly__present
    cmp #$A702
    beq SourcePrefetch_PlanOnly__guard52
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard52:
.a16
.i16
SourcePrefetch_PlanOnly__present:
.a16
.i16
    lda.l SourceVisual_BlockCache,x
    cmp.l SourcePrefetch_Plan
    bne SourcePrefetch_PlanOnly__guard53
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard53:
.a16
.i16
SourcePrefetch_PlanOnly__cache_next:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #512
    bcs SourcePrefetch_PlanOnly__cache_done
    brl SourcePrefetch_PlanOnly__cache
SourcePrefetch_PlanOnly__cache_done:
.a16
.i16
    lda #64
    sta.l SourcePrefetch_Plan+24
    lda #266
    sta.l SourcePrefetch_Plan+26
    lda #1280
    sta.l SourcePrefetch_Plan+28
SourcePrefetch_PlanOnly__npc:
.a16
.i16
    lda.l SourcePrefetch_Plan+24
    tax
    lda.l SourceVisual_State+6,x
    beq SourcePrefetch_PlanOnly__npc_next
    lda.l SourcePrefetch_Plan+26
    tax
    lda.l $7E0A00+CHAR_HP,x
    and #$00FF
    beq SourcePrefetch_PlanOnly__npc_next
    lda.l SourceVisual_Sa1OwnerPolicy,x
    and #$00FF
    cmp #2
    bne SourcePrefetch_PlanOnly__npc_next
    lda.l SourcePrefetch_Plan+28
    tax
    lda.l SVActor_Data+SVActor_Valid,x
    cmp #1
    beq SourcePrefetch_PlanOnly__guard54
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard54:
.a16
.i16
SourcePrefetch_PlanOnly__npc_next:
.a16
.i16
    lda.l SourcePrefetch_Plan+26
    clc
    adc #133
    sta.l SourcePrefetch_Plan+26
    lda.l SourcePrefetch_Plan+28
    clc
    adc #1280
    sta.l SourcePrefetch_Plan+28
    lda.l SourcePrefetch_Plan+24
    clc
    adc #32
    sta.l SourcePrefetch_Plan+24
    cmp #192
    bcs SourcePrefetch_PlanOnly__find_empty
    brl SourcePrefetch_PlanOnly__npc
SourcePrefetch_PlanOnly__find_empty:
.a16
.i16
    ldx #504
SourcePrefetch_PlanOnly__empty:
.a16
.i16
    lda.l SourceVisual_BlockCache+2,x
    bne SourcePrefetch_PlanOnly__empty_next
    lda.l SourceVisual_BlockCache+4,x
    and #$00FF
    bne SourcePrefetch_PlanOnly__empty_next
    lda.l SVActor_HeldBlocks,x
    ora.l SVActor_OldBlocks,x
    and #$00FF
    beq SourcePrefetch_PlanOnly__found
SourcePrefetch_PlanOnly__empty_next:
.a16
.i16
    txa
    sec
    sbc #8
    bcc SourcePrefetch_PlanOnly__no_near
    tax
    bra SourcePrefetch_PlanOnly__empty
SourcePrefetch_PlanOnly__no_near:
.a16
.i16
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__found:
.a16
.i16
    txa
    sta.l SourcePrefetch_Plan+6
    lsr a
    lsr a
    lsr a
    sta.l SourcePrefetch_Plan+8
    lda.l SourceInput_Producer
    cmp.l SourcePrefetch_Plan+12
    beq SourcePrefetch_PlanOnly__guard55
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__guard55:
.a16
.i16
    lda.l $434E7C
    cmp.l SourcePrefetch_Plan+30
    beq SourcePrefetch_PlanOnly__snapshot_still_current
    brl SourcePrefetch_PlanOnly__no
SourcePrefetch_PlanOnly__snapshot_still_current:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    sec
    rtl
SourcePrefetch_PlanOnly__no:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    clc
    rtl
SourcePrefetch_PlanEnd:
.a16
.i16
