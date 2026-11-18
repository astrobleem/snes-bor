; A completed desired lease need not wait for a DIFFERENT producer's
; staging transaction. This path neither allocates nor retires any resource.
; Every referenced tile and palette must already have its real ready state,
; exact immutable identity and this actor's desired-owner pin. Incomplete or
; inconsistent leases use the original shared-DMA path unchanged.
SVActor_ReadyLease:
.a16
.i16
    jsr SVActor_Enabled
    bcs SVActor_ReadyLease__scope
    brl SVActor_ReadyLease__no
SVActor_ReadyLease__scope:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SVActor_ReadyLease__input
    brl SVActor_ReadyLease__no
SVActor_ReadyLease__input:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #6
    bcc SVActor_ReadyLease__actor
    brl SVActor_ReadyLease__no
SVActor_ReadyLease__actor:
.a16
.i16
    asl a
    asl a
    asl a
    asl a
    asl a
    cmp.l SourceVisual_Record
    beq SVActor_ReadyLease__record
    brl SVActor_ReadyLease__no
SVActor_ReadyLease__record:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    asl a
    tax
    lda.l SVActor_LoadBits,x
    sep #$20
.a8
    sta.l SourceVisual_BlockActorMask
    rep #$30
.a16
.i16
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+6,x
    cmp #2
    beq SVActor_ReadyLease__ready
    brl SVActor_ReadyLease__no
SVActor_ReadyLease__ready:
.a16
.i16
    lda.l SourceVisual_State+4,x
    cmp #1
    beq SVActor_ReadyLease__palette_queued
    brl SVActor_ReadyLease__no
SVActor_ReadyLease__palette_queued:
.a16
.i16
    lda.l SourceVisual_State,x
    cmp.l SourceVisual_EntryIndexSaved
    beq SVActor_ReadyLease__identity
    brl SVActor_ReadyLease__no
SVActor_ReadyLease__identity:
.a16
.i16
    lda.l SourceVisual_PieceCount
    beq SVActor_ReadyLease__bad_count
    cmp #66
    bcc SVActor_ReadyLease__count
SVActor_ReadyLease__bad_count:
.a16
.i16
    brl SVActor_ReadyLease__no
SVActor_ReadyLease__count:
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
    sta.l SourceVisual_PieceIndex
SVActor_ReadyLease__piece:
.a16
.i16
    lda.l SourceVisual_PieceIndex
    cmp.l SourceVisual_PieceCount
    bcc SVActor_ReadyLease__piece_present
    brl SVActor_ReadyLease__yes
SVActor_ReadyLease__piece_present:
.a16
.i16
    asl a
    asl a
    asl a
    asl a
    sta.l SourceVisual_Temp
    tax
    lda.l SourceVisual_PieceTable+12,x
    sta.l SourceVisual_BlockIndex
    lda.l SourceVisual_PieceIndex
    clc
    adc.l SourceVisual_ActorMapBase
    tax
    lda.l SourceVisual_ActorPieceMap,x
    and #$00FF
    cmp #64
    bcc SVActor_ReadyLease__block_slot
    brl SVActor_ReadyLease__no
SVActor_ReadyLease__block_slot:
.a16
.i16
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_BlockCache+2,x
    cmp #2
    beq SVActor_ReadyLease__block_ready
    brl SVActor_ReadyLease__no
SVActor_ReadyLease__block_ready:
.a16
.i16
    lda.l SourceVisual_BlockCache,x
    cmp.l SourceVisual_BlockIndex
    beq SVActor_ReadyLease__block_identity
    brl SVActor_ReadyLease__no
SVActor_ReadyLease__block_identity:
.a16
.i16
    lda.l SourceVisual_BlockCache+4,x
    and #$00FF
    and.l SourceVisual_BlockActorMask
    bne SVActor_ReadyLease__block_pin
    brl SVActor_ReadyLease__no
SVActor_ReadyLease__block_pin:
.a16
.i16
    lda.l SourceVisual_Temp
    tax
    lda.l SourceVisual_PieceTable+10,x
    sta.l SourceVisual_PaletteGlobalIndex
    lda.l SourceVisual_PieceTable+8,x
    and #$00FF
    cmp #8
    bcc SVActor_ReadyLease__palette_local
    brl SVActor_ReadyLease__no
SVActor_ReadyLease__palette_local:
.a16
.i16
    clc
    adc.l SourceVisual_Record
    clc
    adc #16
    tax
    lda.l SourceVisual_State,x
    and #$00FF
    bne SVActor_ReadyLease__palette_mapped
    brl SVActor_ReadyLease__no
SVActor_ReadyLease__palette_mapped:
.a16
.i16
    dec a
    cmp #8
    bcc SVActor_ReadyLease__palette_slot
    brl SVActor_ReadyLease__no
SVActor_ReadyLease__palette_slot:
.a16
.i16
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_PaletteCache,x
    cmp.l SourceVisual_PaletteGlobalIndex
    beq SVActor_ReadyLease__palette_identity
    brl SVActor_ReadyLease__no
SVActor_ReadyLease__palette_identity:
.a16
.i16
    lda.l SourceVisual_PaletteCache+3,x
    and #$00FF
    cmp #1
    beq SVActor_ReadyLease__palette_ready
    brl SVActor_ReadyLease__no
SVActor_ReadyLease__palette_ready:
.a16
.i16
    lda.l SourceVisual_PaletteCache+4,x
    and #$00FF
    and.l SourceVisual_BlockActorMask
    beq SVActor_ReadyLease__no
    lda.l SourceVisual_PieceIndex
    inc a
    sta.l SourceVisual_PieceIndex
    brl SVActor_ReadyLease__piece
SVActor_ReadyLease__yes:
.a16
.i16
    ; Rebuild only the source piece -> existing physical-tile words.
    ; The unchanged emitter/capture still validates and rotates OAM pins.
    jsr SourceVisual_PrepareBlocks__apply_all
    sec
    rts
SVActor_ReadyLease__no:
.a16
.i16
    clc
    rts
