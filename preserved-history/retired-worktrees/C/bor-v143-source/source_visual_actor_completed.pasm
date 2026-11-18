; Original-BOR presentation-only completed poses for physical slots 1..5.
; Production world/worker fixtures use banks40/41 and do not access bank43.
; This explicitly gated arena is $430000..$4325FF of the installed256KiB
; BW-RAM. Foreign workspace/campaign consumers never enter these routines.
; Five $500-byte snapshots retain all65 pieces, palette lease and block map.
; Separate held/retiring owner bytes extend the full8-bit legacy owner field.
; Retiring bytes clear ONLY after both actual OAM DMA rows have drained.
SVActor_Data = $430000
SVActor_HeldBlocks = $432000
SVActor_OldBlocks = $432200
SVActor_HeldPalettes = $432400
SVActor_OldPalettes = $432440
SVActor_Magic = $432500
SVActor_Await = $432502
SVActor_Pending = $432504
SVActor_Base = $432510
SVActor_Bit = $432512
SVActor_Not = $432514
SVActor_Count = $432516
SVActor_Index = $432518
SVActor_Temp = $43251A
SVActor_Scan = $43251C
SVActor_Slot = $43251E
SVActor_SavedEntry = $432540
SVActor_Captures = $432580
SVActor_Fallbacks = $432590
SVActor_LeaseScratch = SourceVisual_CompletedSavedEntry
SVActor_Valid = 1162
SVActor_Stage = 1164
SVActor_Roster = 1166
SVActor_Pieces = 56
SVActor_Map = 1096

SVActor_Init:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq SVActor_Init__campaign
    brl SVActor_Init__done
SVActor_Init__campaign:
.a16
.i16
    lda #0
    sta.l SVActor_Magic
    sta.l SVActor_Await
    sta.l SVActor_Pending
    sta.l SVActor_LoadOwner
    sta.l SVActor_LoadEntry
    sta.l SVActor_MetaHits
    sta.l SVActor_MetaEntryHits
    sta.l SourcePressure_HistoryMagic
    sta.l SourcePressure_Hold
    sta.l SourcePacket_ActiveValid
    sta.l SourcePacket_CopyBusy
    sta.l SourcePacket_ThisFrame
    ldx #0
SVActor_Init__metadata:
.a16
.i16
    lda #0
    sta.l SVActor_MetaData+SVActor_MetaValid,x
    txa
    clc
    adc #$0500
    tax
    cpx #$1E00
    bcc SVActor_Init__metadata
    lda #0
    ldx #0
SVActor_Init__owners:
.a16
.i16
    sta.l SVActor_HeldBlocks,x
    sta.l SVActor_OldBlocks,x
    inx
    inx
    cpx #512
    bcc SVActor_Init__owners
    ldx #0
SVActor_Init__palettes:
.a16
.i16
    sta.l SVActor_HeldPalettes,x
    sta.l SVActor_OldPalettes,x
    inx
    inx
    cpx #64
    bcc SVActor_Init__palettes
    ldx #0
SVActor_Init__snapshots:
.a16
.i16
    lda #0
    sta.l SVActor_Data+SVActor_Valid,x
    txa
    clc
    adc #$0500
    tax
    cpx #$1900
    bcc SVActor_Init__snapshots
    ldx #0
    lda #0
SVActor_Init__counters:
.a16
.i16
    sta.l SVActor_Captures,x
    sta.l SVActor_Fallbacks,x
    inx
    inx
    cpx #10
    bcc SVActor_Init__counters
    lda #$AC19
    sta.l SVActor_Magic
SVActor_Init__done:
.a16
.i16
    ply
    plx
    pla
    plp
    rts

SVActor_Enabled:
.a16
.i16
    jsr SourceVisual_CompletedEnabled
    bcc SVActor_Enabled__no
    lda.l SVActor_Magic
    cmp #$AC19
    bne SVActor_Enabled__no
    sec
    rts
SVActor_Enabled__no:
.a16
.i16
    clc
    rts

; A=physical slot1..5; no DP or caller presentation globals are modified.
SVActor_Select:
.a16
.i16
    sta.l SVActor_Slot
    dec a
    cmp #5
    bcs SVActor_Select__no
    asl a
    tax
    lda.l SVActor_Bases,x
    sta.l SVActor_Base
    lda.l SVActor_Bits,x
    sta.l SVActor_Bit
    eor #$00FF
    sta.l SVActor_Not
    sec
    rts
SVActor_Select__no:
.a16
.i16
    clc
    rts
SVActor_Current:
.a16
.i16
    jsr SVActor_Enabled
    bcc SVActor_Select__no
    lda.l SourceVisual_ActorSlot
    jmp SVActor_Select
SVActor_Bases:
    .dw $0000,$0500,$0A00,$0F00,$1400
SVActor_Bits:
    .dw $0002,$0004,$0008,$0010,$0020
SVActor_Dps:
    .dw $0A85,$0B0A,$0B8F,$0C14,$0C99

; X=cache row byte offset. Preserve caller A/P width and X; C=protected.
SVActor_ProtectBlocks:
    php
    rep #$30
.a16
.i16
    pha
    jsr SVActor_Enabled
    bcc SVActor_ProtectBlocks__no
    lda.l SVActor_HeldBlocks,x
    ora.l SVActor_OldBlocks,x
    and #$00FF
    beq SVActor_ProtectBlocks__no
    pla
    plp
    sec
    rts
SVActor_ProtectBlocks__no:
.a16
.i16
    pla
    plp
    clc
    rts
SVActor_ProtectPalettes:
    php
    rep #$30
.a16
.i16
    pha
    jsr SVActor_Enabled
    bcc SVActor_ProtectPalettes__no
    lda.l SVActor_HeldPalettes,x
    ora.l SVActor_OldPalettes,x
    and #$00FF
    beq SVActor_ProtectPalettes__no
    pla
    plp
    sec
    rts
SVActor_ProtectPalettes__no:
.a16
.i16
    pla
    plp
    clc
    rts

; Transfer this actor's previous completed pins into the OAM retirement set.
SVActor_Rotate:
.a16
.i16
    ldx #0
SVActor_Rotate__blocks:
.a16
.i16
    lda.l SVActor_HeldBlocks,x
    and.l SVActor_Bit
    ora.l SVActor_OldBlocks,x
    sta.l SVActor_OldBlocks,x
    lda.l SVActor_HeldBlocks,x
    and.l SVActor_Not
    sta.l SVActor_HeldBlocks,x
    txa
    clc
    adc #8
    tax
    cpx #512
    bcc SVActor_Rotate__blocks
    ldx #0
SVActor_Rotate__palettes:
.a16
.i16
    lda.l SVActor_HeldPalettes,x
    and.l SVActor_Bit
    ora.l SVActor_OldPalettes,x
    sta.l SVActor_OldPalettes,x
    lda.l SVActor_HeldPalettes,x
    and.l SVActor_Not
    sta.l SVActor_HeldPalettes,x
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SVActor_Rotate__palettes
    lda.l SVActor_Await
    ora.l SVActor_Bit
    sta.l SVActor_Await
    lda #1
    sta.l SourceVisual_CompletedAwait
    rts

SVActor_Invalidate:
.a16
.i16
    lda.l SVActor_Base
    tax
    lda.l SVActor_Data+SVActor_Valid,x
    beq SVActor_Invalidate__done
    lda #0
    sta.l SVActor_Data+SVActor_Valid,x
    jsr SVActor_Rotate
SVActor_Invalidate__done:
.a16
.i16
    rts

; X=native entity offset; unlink/offscreen retirement keeps old hardware pins.
SVActor_RetireOffset:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    jsr SVActor_Enabled
    bcc SVActor_RetireOffset__done
    txa
    ldy #0
SVActor_RetireOffset__slot:
.a16
.i16
    cmp #0
    beq SVActor_RetireOffset__found
    sec
    sbc #133
    bcc SVActor_RetireOffset__done
    iny
    cpy #6
    bcc SVActor_RetireOffset__slot
    bra SVActor_RetireOffset__done
SVActor_RetireOffset__found:
.a16
.i16
    tya
    inc a
    cmp.l SVActor_LoadOwner
    bne SVActor_RetireOffset__select
    lda #0
    sta.l SVActor_LoadOwner
SVActor_RetireOffset__select:
.a16
.i16
    tya
    jsr SVActor_Select
    bcc SVActor_RetireOffset__done
    jsr SVActor_Invalidate
SVActor_RetireOffset__done:
.a16
.i16
    ply
    plx
    pla
    plp
    rts

; Main-frame lifecycle sweep: dead/rebound actor snapshots cannot remain live.
SVActor_Observe:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    jsr SVActor_Enabled
    bcc SVActor_Observe__done
    jsr SVActor_LoadObserve
    lda #1
    sta.l SVActor_Scan
SVActor_Observe__actor:
.a16
.i16
    lda.l SVActor_Scan
    jsr SVActor_Select
    lda.l SVActor_Base
    tax
    lda.l SVActor_Data+SVActor_Valid,x
    beq SVActor_Observe__next
    lda.l SVActor_Data+SVActor_Stage,x
    cmp.l Game_StageIndex
    bne SVActor_Observe__retire
    lda.l SVActor_Data+SVActor_Roster,x
    sta.l SVActor_Temp
    lda.l SVActor_Scan
    dec a
    asl a
    tax
    lda.l SVActor_Dps,x
    tax
    lda.l $7E0000+CHAR_HP,x
    and #$00FF
    beq SVActor_Observe__retire
    lda.l $7E0000+CHAR_ROSTER_INDEX,x
    and #$00FF
    cmp.l SVActor_Temp
    beq SVActor_Observe__next
SVActor_Observe__retire:
.a16
.i16
    jsr SVActor_Invalidate
SVActor_Observe__next:
.a16
.i16
    lda.l SVActor_Scan
    inc a
    sta.l SVActor_Scan
    cmp #6
    bcc SVActor_Observe__actor
SVActor_Observe__done:
.a16
.i16
    ply
    plx
    pla
    plp
    rts

; Called under the existing short OAM enqueue gate only AFTER both rows exist.
SVActor_Queued:
.a16
.i16
    lda.l SVActor_Await
    ora.l SVActor_Pending
    sta.l SVActor_Pending
    lda #0
    sta.l SVActor_Await
    rts

; Called only at the real both-row drained witness in CompletedObserve.
SVActor_Drained:
.a16
.i16
    lda.l SVActor_Pending
    eor #$00FF
    sta.l SVActor_Not
    ldx #0
SVActor_Drained__blocks:
.a16
.i16
    lda.l SVActor_OldBlocks,x
    and.l SVActor_Not
    sta.l SVActor_OldBlocks,x
    txa
    clc
    adc #8
    tax
    cpx #512
    bcc SVActor_Drained__blocks
    ldx #0
SVActor_Drained__palettes:
.a16
.i16
    lda.l SVActor_OldPalettes,x
    and.l SVActor_Not
    sta.l SVActor_OldPalettes,x
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SVActor_Drained__palettes
    lda #0
    sta.l SVActor_Pending
    rts

SVActor_CanPublish:
.a16
.i16
    jsr SVActor_Current
    bcc SVActor_CanPublish__yes
    lda.l SourceVisual_CompletedPending
    bne SVActor_CanPublish__no
    lda.l SVActor_Await
    ora.l SVActor_Pending
    and.l SVActor_Bit
    bne SVActor_CanPublish__no
SVActor_CanPublish__yes:
.a16
.i16
    sec
    rts
SVActor_CanPublish__no:
.a16
.i16
    clc
    rts

SVActor_Capture:
.a16
.i16
    jsr SVActor_Current
    bcs SVActor_Capture__begin
    rts
SVActor_Capture__begin:
.a16
.i16
    phb
    lda.l SVActor_Base
    tax
    lda #0
    sta.l SVActor_Data+SVActor_Valid,x
    jsr SVActor_Rotate
    ldx #0
SVActor_Capture__blocks:
.a16
.i16
    lda.l SourceVisual_BlockCache+4,x
    and.l SVActor_Bit
    ora.l SVActor_HeldBlocks,x
    sta.l SVActor_HeldBlocks,x
    txa
    clc
    adc #8
    tax
    cpx #512
    bcc SVActor_Capture__blocks
    ldx #0
SVActor_Capture__palettes:
.a16
.i16
    lda.l SourceVisual_PaletteCache+4,x
    and.l SVActor_Bit
    ora.l SVActor_HeldPalettes,x
    sta.l SVActor_HeldPalettes,x
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SVActor_Capture__palettes
    lda.l SVActor_Base
    tay
    ldx #(SourceVisual_EntryScratch-$7E0000)
    lda #23
    mvn $43,$7E
    lda.l SVActor_Base
    clc
    adc #24
    tay
    lda.l SourceVisual_Record
    clc
    adc #(SourceVisual_State-$7E0000)
    tax
    lda #31
    mvn $43,$7E
    lda.l SourceVisual_PieceCount
    asl a
    asl a
    asl a
    asl a
    sta.l SVActor_Count
    beq SVActor_Capture__map
    lda.l SVActor_Base
    clc
    adc #SVActor_Pieces
    tay
    ldx #(SourceVisual_PieceTable-$7E0000)
    lda.l SVActor_Count
    dec a
    mvn $43,$7E
SVActor_Capture__map:
.a16
.i16
    lda.l SVActor_Base
    clc
    adc #SVActor_Map
    tay
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    clc
    adc.l SourceVisual_ActorSlot
    clc
    adc #(SourceVisual_ActorPieceMap-$7E0000)
    tax
    lda #64
    mvn $43,$7E
    lda.l SVActor_Base
    tax
    lda.l Game_StageIndex
    sta.l SVActor_Data+SVActor_Stage,x
    lda CHAR_ROSTER_INDEX
    and #$00FF
    sta.l SVActor_Data+SVActor_Roster,x
    lda #1
    sta.l SVActor_Data+SVActor_Valid,x
    lda.l SVActor_Slot
    dec a
    asl a
    tax
    lda.l SVActor_Captures,x
    inc a
    sta.l SVActor_Captures,x
    plb
    rts

; Validate every piece, including clipped pieces, before using old metadata.
SVActor_Validate:
.a16
.i16
    lda.l SVActor_Base
    tax
    lda.l SVActor_Data+SVActor_Valid,x
    cmp #1
    beq SVActor_Validate__identity
    brl SVActor_Validate__bad
SVActor_Validate__identity:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage,x
    cmp.l Game_StageIndex
    bne SVActor_Validate__identity_bad
    lda CHAR_ROSTER_INDEX
    and #$00FF
    cmp.l SVActor_Data+SVActor_Roster,x
    bne SVActor_Validate__identity_bad
    lda.l SVActor_Data+12,x
    and #$00FF
    cmp #66
    bcc SVActor_Validate__count
SVActor_Validate__identity_bad:
.a16
.i16
    brl SVActor_Validate__bad
SVActor_Validate__count:
.a16
.i16
    sta.l SVActor_Count
    lda #0
    sta.l SVActor_Index
SVActor_Validate__piece:
.a16
.i16
    lda.l SVActor_Index
    cmp.l SVActor_Count
    bcc SVActor_Validate__have_piece
    sec
    rts
SVActor_Validate__have_piece:
.a16
.i16
    clc
    adc.l SVActor_Base
    tax
    lda.l SVActor_Data+SVActor_Map,x
    and #$00FF
    cmp #64
    bcc SVActor_Validate__block_slot
    brl SVActor_Validate__bad
SVActor_Validate__block_slot:
.a16
.i16
    asl a
    asl a
    asl a
    tay
    lda.l SVActor_Index
    asl a
    asl a
    asl a
    asl a
    clc
    adc.l SVActor_Base
    tax
    lda.l SVActor_Data+SVActor_Pieces+12,x
    sta.l SVActor_Temp
    tya
    tax
    lda.l SourceVisual_BlockCache+2,x
    cmp #2
    bne SVActor_Validate__block_bad
    lda.l SourceVisual_BlockCache,x
    cmp.l SVActor_Temp
    bne SVActor_Validate__block_bad
    lda.l SVActor_HeldBlocks,x
    and.l SVActor_Bit
    bne SVActor_Validate__palette
SVActor_Validate__block_bad:
.a16
.i16
    brl SVActor_Validate__bad
SVActor_Validate__palette:
.a16
.i16
    lda.l SVActor_Index
    asl a
    asl a
    asl a
    asl a
    clc
    adc.l SVActor_Base
    tax
    lda.l SVActor_Data+SVActor_Pieces+10,x
    sta.l SVActor_Temp
    lda.l SVActor_Data+SVActor_Pieces+8,x
    and #$00FF
    cmp #8
    bcs SVActor_Validate__bad
    clc
    adc.l SVActor_Base
    tax
    lda.l SVActor_Data+24+16,x
    and #$00FF
    beq SVActor_Validate__bad
    cmp #9
    bcs SVActor_Validate__bad
    dec a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_PaletteCache,x
    cmp.l SVActor_Temp
    bne SVActor_Validate__bad
    lda.l SourceVisual_PaletteCache+3,x
    and #$00FF
    cmp #1
    bne SVActor_Validate__bad
    lda.l SVActor_HeldPalettes,x
    and.l SVActor_Bit
    beq SVActor_Validate__bad
    lda.l SVActor_Index
    inc a
    sta.l SVActor_Index
    brl SVActor_Validate__piece
SVActor_Validate__bad:
.a16
.i16
    clc
    rts

SVActor_Reuse:
.a16
.i16
    jsr SVActor_Current
    bcc SVActor_Reuse__no
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+28,x
    and #$00FF
    beq SVActor_Reuse__no
    lda.l SourceVisual_EntryIndexSaved
    sta.l SVActor_Temp
    lda.l SVActor_Base
    tax
    lda.l SVActor_Data+24,x
    cmp.l SVActor_Temp
    bne SVActor_Reuse__no
    jsr SVActor_Validate
    bcc SVActor_Reuse__no
    lda.l SourceVisual_ServiceOnly
    beq SVActor_Reuse__emit
    sec
    rts
SVActor_Reuse__emit:
.a16
.i16
    jmp SVActor_Emit__begin
SVActor_Reuse__no:
.a16
.i16
    clc
    rts

SVActor_Emit:
.a16
.i16
    lda.l SourceVisual_ServiceOnly
    bne SVActor_Reuse__no
    lda.l SourceVisual_Error
    and #$00FF
    cmp #$24
    beq SVActor_Emit__check
    cmp #$27
    bne SVActor_Reuse__no
SVActor_Emit__check:
.a16
.i16
    jsr SVActor_Current
    bcc SVActor_Reuse__no
    jsr SVActor_Validate
    bcc SVActor_Reuse__no
SVActor_Emit__begin:
.a16
.i16
    lda.l SourceVisual_Record
    pha
    lda.l SourceVisual_BaseTile
    pha
    lda.l SourceVisual_PieceCount
    pha
    phb
    ldx #(SourceVisual_EntryScratch-$7E0000)
    ldy #(SVActor_SavedEntry-$430000)
    lda #23
    mvn $43,$7E
    lda.l SVActor_Base
    tax
    ldy #(SourceVisual_EntryScratch-$7E0000)
    lda #23
    mvn $7E,$43
    lda.l SVActor_Base
    clc
    adc #24
    tax
    ldy #(SVActor_LeaseScratch-$7E0000)
    lda #31
    mvn $7E,$43
    lda.l SVActor_Count
    asl a
    asl a
    asl a
    asl a
    sta.l SVActor_Temp
    beq SVActor_Emit__pieces_done
    lda.l SVActor_Base
    clc
    adc #SVActor_Pieces
    tax
    ldy #(SourceVisual_PieceTable-$7E0000)
    lda.l SVActor_Temp
    dec a
    mvn $7E,$43
SVActor_Emit__pieces_done:
.a16
.i16
    plb
    lda #(SVActor_LeaseScratch-SourceVisual_State)
    sta.l SourceVisual_Record
    lda.l SVActor_LeaseScratch+8
    sta.l SourceVisual_BaseTile
    lda.l SVActor_Count
    sta.l SourceVisual_PieceCount
    jsr SourceVisual_Emit
    lda #0
    rol a
    sta.l SVActor_Temp
    phb
    ldx #(SVActor_SavedEntry-$430000)
    ldy #(SourceVisual_EntryScratch-$7E0000)
    lda #23
    mvn $7E,$43
    plb
    pla
    sta.l SourceVisual_PieceCount
    pla
    sta.l SourceVisual_BaseTile
    pla
    sta.l SourceVisual_Record
    lda.l SVActor_Temp
    beq SVActor_Emit__no
    lda.l SVActor_Slot
    dec a
    asl a
    tax
    lda.l SVActor_Fallbacks,x
    inc a
    sta.l SVActor_Fallbacks,x
    sec
    rts
SVActor_Emit__no:
.a16
.i16
    clc
    rts

; P2 has the same initial-picture and physical jump deadline as P1. Run only
; from the already guarded once-per-field relay opportunity; never emit OAM.
SVActor_ServiceP2:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    phd
    jsr SVActor_Enabled
    bcc SVActor_ServiceP2__done
    lda.l SourceInput_Magic
    cmp #$1A60
    bne SVActor_ServiceP2__done
    lda.l $7E0A85+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    bne SVActor_ServiceP2__done
    lda.l $7E0A85+CHAR_HP
    and #$00FF
    beq SVActor_ServiceP2__done
    lda.l SVActor_Data+SVActor_Valid
    beq SVActor_ServiceP2__service
    lda.l $7E0A85+CHAR_SELECTED
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
    bne SVActor_ServiceP2__done
SVActor_ServiceP2__service:
.a16
.i16
    lda #$0A85
    tcd
    jsl SourceVisual_ServiceCurrent
SVActor_ServiceP2__done:
.a16
.i16
    jsr SVActor_ServiceOwner
    pld
    ply
    plx
    pla
    plp
    rtl

; One whole desired pose owns new resource admission. Without this lease,
; several unfinished actors can pin every physical slot without any actor
; having enough remaining space to finish. Completed pictures remain held.
SVActor_LoadOwner = $4325A0 ; zero or physical actor slot+1 (P1=1,P2=2)
SVActor_LoadEntry = $4325A2
SVActor_LoadCandidate = $4325A4

; Carry set only for an NPC producer without a completed picture.
; No shared globals, queue, ownership or pins are changed.
SVActor_LoadOwnerNeedsFirstPicture:
.a16
.i16
    lda.l SVActor_LoadOwner
    cmp #3
    bcc SVActor_LoadOwnerNeedsFirstPicture__no
    cmp #7
    bcs SVActor_LoadOwnerNeedsFirstPicture__no
    dec a
    dec a
    asl a
    tax
    lda.l SVActor_Bases,x
    tax
    lda.l SVActor_Data+SVActor_Valid,x
    cmp #1
    beq SVActor_LoadOwnerNeedsFirstPicture__no
    sec
    rts
SVActor_LoadOwnerNeedsFirstPicture__no:
.a16
.i16
    clc
    rts

SVActor_LoadEnter:
.a16
.i16
    jsr SVActor_Enabled
    bcc SVActor_LoadEnter__yes
    lda.l SourceInput_Magic
    cmp #$1A60
    bne SVActor_LoadEnter__yes
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+6,x
    cmp #2
    beq SVActor_LoadEnter__yes
    ; An incomplete NPC compositor never allocates resources. Its existing
    ; deferral runs unchanged without taking the producer lease.
    lda.l SourceVisual_ServiceOnly
    bne SVActor_LoadEnter__producer
    lda.l SourceVisual_ActorSlot
    beq SVActor_LoadEnter__producer
    cmp #2
    bcs SVActor_LoadEnter__yes
    ; P2 keeps its historical compositor path except while a first NPC
    ; producer needs the remaining space to finish its initial packet.
    jsr SVActor_LoadOwnerNeedsFirstPicture
    bcc SVActor_LoadEnter__yes
SVActor_LoadEnter__producer:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    inc a
    sta.l SVActor_LoadCandidate
    lda.l SVActor_LoadOwner
    beq SVActor_LoadEnter__unowned
    cmp.l SVActor_LoadCandidate
    beq SVActor_LoadEnter__acquire
    jsr SVActor_LoadPreempt
    bcs SVActor_LoadEnter__acquire
    bra SVActor_LoadEnter__no
SVActor_LoadEnter__unowned:
.a16
.i16
    jsr SVActor_LoadInitialTurn
    bcc SVActor_LoadEnter__no
SVActor_LoadEnter__acquire:
.a16
.i16
    lda.l SVActor_LoadCandidate
    sta.l SVActor_LoadOwner
    lda.l SourceVisual_EntryIndexSaved
    sta.l SVActor_LoadEntry
SVActor_LoadEnter__yes:
.a16
.i16
    sec
    rts
SVActor_LoadEnter__no:
.a16
.i16
    clc
    rts

; Preserve the producer across an actual pending block/palette. Ready or
; unsupported jobs release it; the caller restores the original result C.
SVActor_LoadLeave:
.a16
.i16
    php
    jsr SVActor_Enabled
    bcs SVActor_LoadLeave__enabled
    plp
    rts
SVActor_LoadLeave__enabled:
.a16
.i16
    plp
    bcs SVActor_LoadLeave__complete
    lda.l SourceVisual_Error
    and #$00FF
    cmp #$27
    beq SVActor_LoadLeave__done
    cmp #$24
    beq SVActor_LoadLeave__done
SVActor_LoadLeave__complete:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    inc a
    cmp.l SVActor_LoadOwner
    bne SVActor_LoadLeave__done
    lda #0
    sta.l SVActor_LoadOwner
SVActor_LoadLeave__done:
.a16
.i16
    rts

; Death, unlink, rebind and readiness cannot strand the frame producer.
SVActor_LoadObserve:
.a16
.i16
    lda.l SVActor_LoadOwner
    beq SVActor_LoadObserve__done
    dec a
    cmp #6
    bcs SVActor_LoadObserve__release
    asl a
    tay
    tax
    lda.l SVActor_LoadDps,x
    tax
    lda.l $7E0000+CHAR_HP,x
    and #$00FF
    beq SVActor_LoadObserve__release
    tya
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_State+6,x
    cmp #1
    bne SVActor_LoadObserve__release
    lda.l SourceVisual_State,x
    cmp.l SVActor_LoadEntry
    beq SVActor_LoadObserve__done
SVActor_LoadObserve__release:
.a16
.i16
    lda #0
    sta.l SVActor_LoadOwner
SVActor_LoadObserve__done:
.a16
.i16
    rts
SVActor_LoadDps:
    .dw $0A00,$0A85,$0B0A,$0B8F,$0C14,$0C99

; Initial visible actors precede refreshes of already drawable actors.
; Physical jumps retain their landing deadline; neither player's initial
; picture nor an in-progress jump may be preempted by the other player.
SVActor_LoadInitialTurn:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #2
    bcs SVActor_LoadInitialTurn__picture
    lda CHAR_SELECTED
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
    beq SVActor_LoadInitialTurn__allow
SVActor_LoadInitialTurn__picture:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    bne SVActor_LoadInitialTurn__other
    lda.l SourceVisual_CompletedValid
    bra SVActor_LoadInitialTurn__known
SVActor_LoadInitialTurn__other:
.a16
.i16
    jsr SVActor_Current
    lda.l SVActor_Base
    tax
    lda.l SVActor_Data+SVActor_Valid,x
SVActor_LoadInitialTurn__known:
.a16
.i16
    bne SVActor_LoadInitialTurn__priority
SVActor_LoadInitialTurn__allow:
.a16
.i16
    sec
    rts
; First missing player attack pictures precede already drawable refreshes.
; Initial NPC pictures and physical jumps retain their earlier priority.
; Once that attack picture exists, repeated frame changes cannot monopolize
; priority over the other player's first attack picture.
SVActor_LoadInitialTurn__priority:
.a16
.i16
    jsr SVActor_FirstAttack
    beq SVActor_LoadInitialTurn__scan
    cmp.l SVActor_LoadCandidate
    beq SVActor_LoadInitialTurn__scan
    clc
    rts
SVActor_LoadInitialTurn__scan:
.a16
.i16
    ldy #0
SVActor_LoadInitialTurn__actor:
.a16
.i16
    tya
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_State+6,x
    cmp #1
    bne SVActor_LoadInitialTurn__next
    tya
    asl a
    tax
    lda.l SVActor_LoadBits,x
    and.l SourceVisual_RetireMask
    and #$00FF
    bne SVActor_LoadInitialTurn__next
    lda.l SVActor_LoadDps,x
    tax
    lda.l $7E0000+CHAR_HP,x
    and #$00FF
    beq SVActor_LoadInitialTurn__next
    lda.l $7E0000+CHAR_POS_X,x
    sec
    sbc.l Screen_PosX
    bmi SVActor_LoadInitialTurn__left
    cmp #352
    bcs SVActor_LoadInitialTurn__next
    bra SVActor_LoadInitialTurn__visible
SVActor_LoadInitialTurn__left:
.a16
.i16
    cmp #$FFA0
    bcc SVActor_LoadInitialTurn__next
SVActor_LoadInitialTurn__visible:
.a16
.i16
    tya
    bne SVActor_LoadInitialTurn__snapshot
    lda.l SourceVisual_CompletedValid
    bra SVActor_LoadInitialTurn__valid
SVActor_LoadInitialTurn__snapshot:
.a16
.i16
    jsr SVActor_Select
    lda.l SVActor_Base
    tax
    lda.l SVActor_Data+SVActor_Valid,x
SVActor_LoadInitialTurn__valid:
.a16
.i16
    bne SVActor_LoadInitialTurn__next
    clc
    rts
SVActor_LoadInitialTurn__next:
.a16
.i16
    iny
    cpy #6
    bcs SVActor_LoadInitialTurn__finished
    brl SVActor_LoadInitialTurn__actor
SVActor_LoadInitialTurn__finished:
.a16
.i16
    sec
    rts
SVActor_LoadBits:
    .dw 1,2,4,8,16,32

SVActor_LoadPreempt:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #2
    bcs SVActor_LoadPreempt__npc_begin
    brl SVActor_LoadPreempt__player
SVActor_LoadPreempt__npc_begin:
.a16
.i16
    cmp #6
    bcs SVActor_LoadPreempt__npc_no
    ; Missing first NPC pictures outrank redundant updates to an already
    ; visible NPC. Another first picture remains protected; player repeat jobs
    ; may yield only through the exact completed-role cancellation guard.
    lda.l SourceVisual_ServiceOnly
    beq SVActor_LoadPreempt__npc_no
    lda.l SourceVisual_ActorSlot
    dec a
    asl a
    tax
    lda.l SVActor_Bases,x
    tax
    lda.l SVActor_Data+SVActor_Valid,x
    cmp #1
    beq SVActor_LoadPreempt__npc_no
    lda.l SVActor_LoadOwner
    cmp #3
    bcs SVActor_LoadPreempt__npc_owner
    ; Only the existing validated cancellation path may yield a player's
    ; redundant preparation. New roles, jump, first pictures and DMA stay held.
    jsr SVActor_YieldRepeatedPlayerForFirstNpc
    rts
SVActor_LoadPreempt__npc_owner:
.a16
.i16
    cmp #7
    bcs SVActor_LoadPreempt__npc_no
    dec a
    dec a
    asl a
    tax
    lda.l SVActor_Bases,x
    tax
    lda.l SVActor_Data+SVActor_Valid,x
    cmp #1
    bne SVActor_LoadPreempt__npc_no
    lda.l SourceVisual_ActorSlot
    dec a
    asl a
    tax
    lda.l SVActor_Bases,x
    tax
    lda.l SVActor_Data+SVActor_Valid,x
    cmp #1
    beq SVActor_LoadPreempt__npc_no
    brl SVActor_LoadPreempt__fence
SVActor_LoadPreempt__npc_no:
.a16
.i16
    clc
    rts
SVActor_LoadPreempt__player:
.a16
.i16
    lda CHAR_SELECTED
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
    beq SVActor_LoadPreempt__owner
    ; A first missing player punch cannot wait behind a whole NPC pose.
    ; Use the existing symmetric first-attack selector; do not preempt a
    ; player's startup/jump/attack producer or repeated completed punches.
    lda.l SVActor_LoadOwner
    cmp #3
    bcc SVActor_LoadPreempt__no_attack
    jsr SVActor_FirstAttack
    cmp.l SVActor_LoadCandidate
    bne SVActor_LoadPreempt__no_attack
    ; Repeated cold restarts made an authored enemy hittable but invisible.
    ; Finish its first picture before admitting an ordinary first punch.
    jsr SVActor_LoadOwnerNeedsFirstPicture
    bcs SVActor_LoadPreempt__no_attack
    brl SVActor_LoadPreempt__fence
SVActor_LoadPreempt__no_attack:
.a16
.i16
    clc
    rts
SVActor_LoadPreempt__owner:
.a16
.i16
    lda.l SVActor_LoadOwner
    cmp #3
    bcs SVActor_LoadPreempt__fence
    cmp #1
    bne SVActor_LoadPreempt__p2_picture
    lda.l SourceVisual_CompletedValid
    bra SVActor_LoadPreempt__picture
SVActor_LoadPreempt__p2_picture:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
SVActor_LoadPreempt__picture:
.a16
.i16
    bne SVActor_LoadPreempt__old_player
    clc
    rts
SVActor_LoadPreempt__old_player:
.a16
.i16
    lda.l SVActor_LoadOwner
    dec a
    asl a
    tax
    lda.l SVActor_LoadDps,x
    tax
    lda.l $7E0000+CHAR_SELECTED,x
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
    bne SVActor_LoadPreempt__fence
    clc
    rts
SVActor_LoadPreempt__fence:
.a16
.i16
    jsr SourceVisual_HasOwnedDma
    bcc SVActor_LoadPreempt__release
    clc
    rts
SVActor_LoadPreempt__release:
.a16
.i16
    ; No active tile/palette transfer can reference this partial producer.
    ; Drop only its desired ownership; old completed/hardware pins survive.
    lda.l SourceVisual_ActorSlot
    pha
    lda.l SourceVisual_Record
    pha
    lda.l SVActor_LoadOwner
    dec a
    sta.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l SourceVisual_Record
    jsr SourceVisual_ReleaseActorBlocks
    jsr SourceVisual_ReleaseActorPalettes
    pla
    sta.l SourceVisual_Record
    pla
    sta.l SourceVisual_ActorSlot
    lda #0
    sta.l SVActor_LoadOwner
    sec
    rts

; Cancel only obsolete non-jump work once a real completed picture exists.
; Do not restart a jump frame on each animation tick or abandon first pictures.
SVActor_JumpReplace:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #2
    bcs SVActor_JumpReplace__no
    ; FindEntry has already resolved the exact live source role. Attacks
    ; and physical jumps supersede an obsolete desired idle/walk pose.
    lda.l SourceVisual_Key+1
    and #$00FF
    cmp #7
    beq SVActor_JumpReplace__role
    cmp #2
    beq SVActor_JumpReplace__role
    ; Walking outranks unfinished idle bookkeeping once this player has a
    ; completed picture. Keep a pending walk until it emits once, including
    ; when the live source returns to idle, so brief movement cannot starve
    ; the first walking picture. Same-role frame changes never preempt.
    cmp #1
    bne SVActor_JumpReplace__no
    lda.l SourceVisual_State+30,x
    and #$00FF
    bne SVActor_JumpReplace__no
SVActor_JumpReplace__role:
.a16
.i16
    ; Role and the adjacent pin witness are independent byte fields.
    sep #$20
.a8
    lda.l SourceVisual_Key+1
    cmp.l SourceVisual_State+30,x
    rep #$31
.a16
.i16
    beq SVActor_JumpReplace__no
    phx
    lda.l SourceVisual_ActorSlot
    bne SVActor_JumpReplace__p2
    lda.l SourceVisual_CompletedValid
    bra SVActor_JumpReplace__valid
SVActor_JumpReplace__p2:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
SVActor_JumpReplace__valid:
.a16
.i16
    cmp #0
    beq SVActor_JumpReplace__invalid
    plx
    sec
    rts
SVActor_JumpReplace__invalid:
.a16
.i16
    plx
SVActor_JumpReplace__no:
.a16
.i16
    clc
    rts

; Advance exactly the current pose producer during the existing field relay.
; A service-only visit uses the normal viewport/retirement and DMA fences.
; Player startup/jump service already runs before this; skip those visits.
SVActor_ServiceOwner:
.a16
.i16
    jsr SVActor_Enabled
    bcs SVActor_ServiceOwner__enabled_scope
    brl SVActor_ServiceOwner__done
SVActor_ServiceOwner__enabled_scope:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SVActor_ServiceOwner__journal_scope
    brl SVActor_ServiceOwner__done
SVActor_ServiceOwner__journal_scope:
.a16
.i16
    ; Armed play defers redundant owner preparation until after submission.
    ; An NPC with no completed first picture retains wait-time continuation:
    ; starving that work would permit simulation/combat with an invisible NPC.
    lda.l $7E46DC ; S6Normal_NmiArm
    cmp #1
    bne SVActor_ServiceOwner__normal_owner
    lda.l SVActor_LoadOwner
    cmp #3
    bcc SVActor_ServiceOwner__done
    cmp #7
    bcs SVActor_ServiceOwner__done
    dec a
    dec a
    asl a
    tax
    lda.l SVActor_Bases,x
    tax
    lda.l SVActor_Data+SVActor_Valid,x
    cmp #1
    beq SVActor_ServiceOwner__done
SVActor_ServiceOwner__normal_owner:
.a16
.i16
    lda.l SVActor_LoadOwner
    cmp #1
    bcc SVActor_ServiceOwner__done
    cmp #7
    bcs SVActor_ServiceOwner__done
    cmp #3
    bcs SVActor_ServiceOwner__selected
    cmp #1
    bne SVActor_ServiceOwner__p2
    lda.l SourceVisual_CompletedValid
    beq SVActor_ServiceOwner__done
    bra SVActor_ServiceOwner__player
SVActor_ServiceOwner__p2:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    beq SVActor_ServiceOwner__done
SVActor_ServiceOwner__player:
.a16
.i16
    lda.l SVActor_LoadOwner
    dec a
    asl a
    tax
    lda.l SVActor_LoadDps,x
    tax
    lda.l $7E0000+CHAR_SELECTED,x
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
    beq SVActor_ServiceOwner__done
    lda.l SVActor_LoadOwner
SVActor_ServiceOwner__selected:
.a16
.i16
    dec a
    asl a
    tax
    lda.l SVActor_LoadDps,x
    tcd
    lda CHAR_HP
    and #$00FF
    beq SVActor_ServiceOwner__dead
    jsr SVActor_ContinueMedia
    bcc SVActor_ServiceOwner__done
    jsl SourceVisual_ServiceCurrent
SVActor_ServiceOwner__done:
.a16
.i16
    rts
SVActor_ServiceOwner__dead:
.a16
.i16
    lda #0
    sta.l SVActor_LoadOwner
    rts

; State+31 is the one-byte pin-scan witness for a full-pose desired lease.
; With the single producer, other jobs cannot allocate its future pieces
; between visits. PrepareBlocks pins every newly found/allocated block.
; Lease replacement, retirement and preemption all invalidate the witness
; through ReleaseActorBlocks before relinquishing any actor ownership.
SVActor_PinLeaseOnce:
.a16
.i16
    jsr SVActor_Enabled
    bcc SVActor_PinLeaseOnce__scan
    lda.l SourceInput_Magic
    cmp #$1A60
    bne SVActor_PinLeaseOnce__scan
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+31,x
    and #$00FF
    beq SVActor_PinLeaseOnce__first
    clc
    rts
SVActor_PinLeaseOnce__first:
.a16
.i16
    sep #$20
.a8
    lda #1
    sta.l SourceVisual_State+31,x
    rep #$30
.a16
.i16
SVActor_PinLeaseOnce__scan:
.a16
.i16
    sec
    rts
SVActor_ReleasePinLease:
.a16
.i16
    jsr SVActor_Enabled
    bcc SVActor_ReleasePinLease__done
    lda.l SourceInput_Magic
    cmp #$1A60
    bne SVActor_ReleasePinLease__done
    lda.l SourceVisual_Record
    tax
    sep #$20
.a8
    lda #0
    sta.l SourceVisual_State+31,x
    rep #$30
.a16
.i16
SVActor_ReleasePinLease__done:
.a16
.i16
    rts

; A=physical player slot+1 needing its first source attack picture, or0.
SVActor_FirstAttack:
.a16
.i16
    lda.l $7E0A00+CHAR_HP
    and #$00FF
    beq SVActor_FirstAttack__p2
    lda.l SourceVisual_State+6
    cmp #1
    bne SVActor_FirstAttack__p2
    lda.l SourceVisual_State+30
    and #$00FF
    cmp #2
    bne SVActor_FirstAttack__p2
    lda.l SourceVisual_CompletedValid
    beq SVActor_FirstAttack__p2
    lda.l SourceVisual_CompletedEntry+1
    and #$00FF
    cmp #2
    beq SVActor_FirstAttack__p2
    lda #1
    rts
SVActor_FirstAttack__p2:
.a16
.i16
    lda.l $7E0A85+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    bne SVActor_FirstAttack__none
    lda.l $7E0A85+CHAR_HP
    and #$00FF
    beq SVActor_FirstAttack__none
    lda.l SourceVisual_State+32+6
    cmp #1
    bne SVActor_FirstAttack__none
    lda.l SourceVisual_State+32+30
    and #$00FF
    cmp #2
    bne SVActor_FirstAttack__none
    lda.l SVActor_Data+SVActor_Valid
    beq SVActor_FirstAttack__none
    lda.l SVActor_Data+1
    and #$00FF
    cmp #2
    beq SVActor_FirstAttack__none
    lda #2
    rts
SVActor_FirstAttack__none:
.a16
.i16
    lda #0
    rts

; Once world ticks have completed, return promptly to the snapshot/renderer
; instead of extending that wait with ordinary idle/walk refreshes. Initial
; NPC pictures and admitted player attacks keep their visible deadlines;
; player startup/jump service already runs before this optional producer.
; These are the same requested/completed tick words read by Relay_Wait_Ticks.
SVActor_ContinueMedia:
.a16
.i16
    lda.l $412002
    cmp.l $412004
    bne SVActor_ContinueMedia__yes
    lda.l SVActor_LoadOwner
    dec a
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_State+30,x
    and #$00FF
    cmp #2
    beq SVActor_ContinueMedia__yes
    lda.l SVActor_LoadOwner
    cmp #3
    bcc SVActor_ContinueMedia__no
    dec a
    dec a
    asl a
    tax
    lda.l SVActor_Bases,x
    tax
    lda.l SVActor_Data+SVActor_Valid,x
    beq SVActor_ContinueMedia__yes
SVActor_ContinueMedia__no:
.a16
.i16
    clc
    rts
SVActor_ContinueMedia__yes:
.a16
.i16
    sec
    rts

; Immutable raw source metadata, six physical actor rows of$500 bytes.
; Explicit Original-BOR-only extension $433000..$434DFF in installed BW-RAM.
; Rows hold exact catalog index/count, entry24 and at most65 raw pieces16.
; They never contain OBJ identities or DMA payloads. Stage/index must match;
; fresh live-key lookup still runs and unsupported live keys remain closed.
SVActor_MetaData = $433000
SVActor_MetaValid = 1068
SVActor_MetaStage = 1070
SVActor_MetaBase = $4325A8
SVActor_MetaBytes = $4325AA
SVActor_MetaHits = $4325AC
SVActor_MetaEntryHits = $4325AE
SVActor_MetaBases:
    .dw $0000,$0500,$0A00,$0F00,$1400,$1900
SVActor_MetaSelect:
.a16
.i16
    jsr SVActor_Enabled
    bcc SVActor_MetaSelect__no
    lda.l SourceInput_Magic
    cmp #$1A60
    bne SVActor_MetaSelect__no
    lda.l SourceVisual_ActorSlot
    cmp #6
    bcs SVActor_MetaSelect__no
    asl a
    tax
    lda.l SVActor_MetaBases,x
    sta.l SVActor_MetaBase
    tax
    sec
    rts
SVActor_MetaSelect__no:
.a16
.i16
    clc
    rts
SVActor_MetaMatch:
.a16
.i16
    jsr SVActor_MetaSelect
    bcc SVActor_MetaMatch__no
    lda.l SVActor_MetaData+SVActor_MetaValid,x
    cmp #1
    bne SVActor_MetaMatch__no
    lda.l SVActor_MetaData+SVActor_MetaStage,x
    cmp.l Game_StageIndex
    bne SVActor_MetaMatch__no
    lda.l SVActor_MetaData,x
    cmp.l SourceVisual_EntryIndexSaved
    bne SVActor_MetaMatch__no
    sec
    rts
SVActor_MetaMatch__no:
.a16
.i16
    clc
    rts
SVActor_MetaEntry:
.a16
.i16
    jsr SVActor_MetaMatch
    bcc SVActor_MetaEntry__no
    phb
    lda.l SVActor_MetaBase
    clc
    adc #((SVActor_MetaData+4)&$FFFF)
    tax
    ldy #(SourceVisual_EntryScratch&$FFFF)
    lda #23
    mvn $7E,$43
    plb
    lda.l SVActor_MetaEntryHits
    inc a
    sta.l SVActor_MetaEntryHits
    sec
    rts
SVActor_MetaEntry__no:
.a16
.i16
    clc
    rts
SVActor_MetaPieces:
.a16
.i16
    jsr SVActor_MetaMatch
    bcc SVActor_MetaPieces__no
    lda.l SVActor_MetaData+2,x
    cmp.l SourceVisual_PieceCount
    bne SVActor_MetaPieces__no
    asl a
    asl a
    asl a
    asl a
    beq SVActor_MetaPieces__yes
    sta.l SVActor_MetaBytes
    phb
    lda.l SVActor_MetaBase
    clc
    adc #((SVActor_MetaData+28)&$FFFF)
    tax
    ldy #(SourceVisual_PieceTable&$FFFF)
    lda.l SVActor_MetaBytes
    dec a
    mvn $7E,$43
    plb
SVActor_MetaPieces__yes:
.a16
.i16
    lda.l SVActor_MetaHits
    inc a
    sta.l SVActor_MetaHits
    sec
    rts
SVActor_MetaPieces__no:
.a16
.i16
    clc
    rts
SVActor_MetaSave:
.a16
.i16
    jsr SVActor_MetaSelect
    bcc SVActor_MetaSave__done
    lda.l SourceVisual_PieceCount
    cmp #66
    bcs SVActor_MetaSave__done
    lda #0
    sta.l SVActor_MetaData+SVActor_MetaValid,x
    lda.l SourceVisual_PieceCount
    sta.l SVActor_MetaData+2,x
    lda.l SourceVisual_EntryIndexSaved
    sta.l SVActor_MetaData,x
    lda.l Game_StageIndex
    sta.l SVActor_MetaData+SVActor_MetaStage,x
    phb
    lda.l SVActor_MetaBase
    clc
    adc #((SVActor_MetaData+4)&$FFFF)
    tay
    ldx #(SourceVisual_EntryScratch&$FFFF)
    lda #23
    mvn $43,$7E
    lda.l SourceVisual_PieceCount
    asl a
    asl a
    asl a
    asl a
    beq SVActor_MetaSave__valid
    sta.l SVActor_MetaBytes
    lda.l SVActor_MetaBase
    clc
    adc #((SVActor_MetaData+28)&$FFFF)
    tay
    ldx #(SourceVisual_PieceTable&$FFFF)
    lda.l SVActor_MetaBytes
    dec a
    mvn $43,$7E
SVActor_MetaSave__valid:
.a16
.i16
    lda.l SVActor_MetaBase
    tax
    lda #1
    sta.l SVActor_MetaData+SVActor_MetaValid,x
    plb
SVActor_MetaSave__done:
.a16
.i16
    rts

; A completed desired lease need not wait for a DIFFERENT producer's
; staging transaction. This path neither allocates nor retires any resource.
; Every referenced tile and palette must already have its real ready state,
; exact immutable identity and this actor's desired-owner pin. Incomplete or
; inconsistent leases use the original shared-DMA path unchanged.
SVActor_ReadyLease:
.a16
.i16
    ; An incomplete lease cannot use this path. Avoid the full scope and
    ; identity walk on every pending block service; READY still runs every
    ; check below before any mapped piece can be used.
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+6,x
    cmp #2
    beq SVActor_ReadyLease__candidate
    clc
    rts
SVActor_ReadyLease__candidate:
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


; Advance one missing NPC picture during the main thread's existing frame
; wait. One call per wait, never from NMI or the audio busy-pump loop. The
; saved wait counter predates this work, so crossing vblank completes the
; same wait. Published NPC updates and all player jobs retain their budgets.
SVActor_ServiceFirstNpcDuringWait:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    phb
    phd
    sep #$20
.a8
    lda #0
    pha
    plb
    rep #$30
.a16
.i16
    jsr SVActor_Enabled
    bcs SVActor_ServiceFirstNpcDuringWait__enabled
    brl SVActor_ServiceFirstNpcDuringWait__done
SVActor_ServiceFirstNpcDuringWait__enabled:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SVActor_ServiceFirstNpcDuringWait__journal
    brl SVActor_ServiceFirstNpcDuringWait__done
SVActor_ServiceFirstNpcDuringWait__journal:
.a16
.i16
    lda.l $7E1760
    cmp #1
    beq SVActor_ServiceFirstNpcDuringWait__normal
    brl SVActor_ServiceFirstNpcDuringWait__done
SVActor_ServiceFirstNpcDuringWait__normal:
.a16
.i16
    lda.l Game_State
    cmp #0
    beq SVActor_ServiceFirstNpcDuringWait__playing
    brl SVActor_ServiceFirstNpcDuringWait__done
SVActor_ServiceFirstNpcDuringWait__playing:
.a16
.i16
    lda.l $7E46DC
    cmp #1
    beq SVActor_ServiceFirstNpcDuringWait__armed
    brl SVActor_ServiceFirstNpcDuringWait__done
SVActor_ServiceFirstNpcDuringWait__armed:
.a16
.i16
    ; Continue a missing first punch in this otherwise-idle foreground slot.
    ; Physical jumps and first NPC producers retain their existing priority.
    jsr SourceVisual_FirstMissingPlayerAttack
    cmp #0
    beq SVActor_ServiceFirstNpcDuringWait__walk_opportunity
    tcd
    jsl SourceVisual_ServiceCurrent
    brl SVActor_ServiceFirstNpcDuringWait__done
SVActor_ServiceFirstNpcDuringWait__walk_opportunity:
.a16
.i16
    jsr SourceVisual_FirstMissingPlayerWalk
    cmp #0
    beq SVActor_ServiceFirstNpcDuringWait__no_player_walk
    tcd
    jsl SourceVisual_ServiceCurrent
    brl SVActor_ServiceFirstNpcDuringWait__done
SVActor_ServiceFirstNpcDuringWait__no_player_walk:
.a16
.i16
    ; Keep the initial spawn's original budget during opening controls.
    ; Once the authored queue admits later arrivals, missing first pictures
    ; may consume one otherwise-idle main wait opportunity.
    lda.l Spawn_Index
    and #$00FF
    cmp #2
    bcs SVActor_ServiceFirstNpcDuringWait__later_spawn
    brl SVActor_ServiceFirstNpcDuringWait__done
SVActor_ServiceFirstNpcDuringWait__later_spawn:
.a16
.i16
    lda.l SVActor_LoadOwner
    cmp #3
    bcs SVActor_ServiceFirstNpcDuringWait__owner_min
    brl SVActor_ServiceFirstNpcDuringWait__done
SVActor_ServiceFirstNpcDuringWait__owner_min:
.a16
.i16
    lda.l SVActor_LoadOwner
    cmp #7
    bcc SVActor_ServiceFirstNpcDuringWait__owner_max
    brl SVActor_ServiceFirstNpcDuringWait__done
SVActor_ServiceFirstNpcDuringWait__owner_max:
.a16
.i16
    dec a
    dec a
    asl a
    tax
    lda.l SVActor_Bases,x
    tax
    lda.l SVActor_Data+SVActor_Valid,x
    cmp #1
    bne SVActor_ServiceFirstNpcDuringWait__first
    brl SVActor_ServiceFirstNpcDuringWait__done
SVActor_ServiceFirstNpcDuringWait__first:
.a16
.i16
    jsr SVActor_ServiceOwner
SVActor_ServiceFirstNpcDuringWait__done:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    rtl

; A=real DP for one missing walking role, or0. No OAM, memory writes or
; ownership changes. One caller service per existing main wait. P1 first,
; then P2; already-ready walks and new attack/jump work are never repeated.
SourceVisual_FirstMissingPlayerWalk:
.a16
.i16
    lda.l $7E0A00+CHAR_HP
    and #$00FF
    bne SourceVisual_FirstMissingPlayerWalk__p1_alive
    brl SourceVisual_FirstMissingPlayerWalk__p2
SourceVisual_FirstMissingPlayerWalk__p1_alive:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy+0
    and #$00FF
    cmp #2
    beq SourceVisual_FirstMissingPlayerWalk__p1_source_owner
    brl SourceVisual_FirstMissingPlayerWalk__p2
SourceVisual_FirstMissingPlayerWalk__p1_source_owner:
.a16
.i16
    lda.l $7E0A00+CHAR_SELECTED
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
    bne SourceVisual_FirstMissingPlayerWalk__p1_not_jump
    brl SourceVisual_FirstMissingPlayerWalk__p2
SourceVisual_FirstMissingPlayerWalk__p1_not_jump:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    bne SourceVisual_FirstMissingPlayerWalk__p1_picture
    brl SourceVisual_FirstMissingPlayerWalk__p2
SourceVisual_FirstMissingPlayerWalk__p1_picture:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+1
    and #$00FF
    cmp #1
    bne SourceVisual_FirstMissingPlayerWalk__p1_missing
    brl SourceVisual_FirstMissingPlayerWalk__p2
SourceVisual_FirstMissingPlayerWalk__p1_missing:
.a16
.i16
    lda.l SourceVisual_State+6
    cmp #2
    bne SourceVisual_FirstMissingPlayerWalk__p1_not_ready_walk
    lda.l SourceVisual_State+30
    and #$00FF
    cmp #1
    bne SourceVisual_FirstMissingPlayerWalk__p1_not_ready_walk
    brl SourceVisual_FirstMissingPlayerWalk__p2
SourceVisual_FirstMissingPlayerWalk__p1_not_ready_walk:
.a16
.i16
    lda.l SourceVisual_State+6
    cmp #1
    bne SourceVisual_FirstMissingPlayerWalk__p1_role
    lda.l SourceVisual_State+28
    and #$00FF
    bne SourceVisual_FirstMissingPlayerWalk__p1_role
    lda.l SourceVisual_State+30
    and #$00FF
    cmp #2
    bne SourceVisual_FirstMissingPlayerWalk__p1_not_attack
    brl SourceVisual_FirstMissingPlayerWalk__p2
SourceVisual_FirstMissingPlayerWalk__p1_not_attack:
.a16
.i16
    cmp #7
    bne SourceVisual_FirstMissingPlayerWalk__p1_role
    brl SourceVisual_FirstMissingPlayerWalk__p2
SourceVisual_FirstMissingPlayerWalk__p1_role:
.a16
.i16
    lda.l SourceVisual_Sa1RuntimeRole+0
    and #$00FF
    cmp #1
    beq SourceVisual_FirstMissingPlayerWalk__p1_choose
    cmp #0
    beq SourceVisual_FirstMissingPlayerWalk__p1_released
    brl SourceVisual_FirstMissingPlayerWalk__p2
SourceVisual_FirstMissingPlayerWalk__p1_released:
.a16
.i16
    lda.l SourceVisual_State+6
    cmp #1
    beq SourceVisual_FirstMissingPlayerWalk__p1_pending
    brl SourceVisual_FirstMissingPlayerWalk__p2
SourceVisual_FirstMissingPlayerWalk__p1_pending:
.a16
.i16
    lda.l SourceVisual_State+28
    and #$00FF
    beq SourceVisual_FirstMissingPlayerWalk__p1_unseen
    brl SourceVisual_FirstMissingPlayerWalk__p2
SourceVisual_FirstMissingPlayerWalk__p1_unseen:
.a16
.i16
    lda.l SourceVisual_State+30
    and #$00FF
    cmp #1
    beq SourceVisual_FirstMissingPlayerWalk__p1_held_walk
    brl SourceVisual_FirstMissingPlayerWalk__p2
SourceVisual_FirstMissingPlayerWalk__p1_held_walk:
.a16
.i16
SourceVisual_FirstMissingPlayerWalk__p1_choose:
.a16
.i16
    lda #$0A00
    rts
SourceVisual_FirstMissingPlayerWalk__p2:
.a16
.i16
    lda.l $7E0A85+CHAR_HP
    and #$00FF
    bne SourceVisual_FirstMissingPlayerWalk__p2_alive
    brl SourceVisual_FirstMissingPlayerWalk__none
SourceVisual_FirstMissingPlayerWalk__p2_alive:
.a16
.i16
    lda.l $7E0A85+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    beq SourceVisual_FirstMissingPlayerWalk__p2_driven
    brl SourceVisual_FirstMissingPlayerWalk__none
SourceVisual_FirstMissingPlayerWalk__p2_driven:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy+133
    and #$00FF
    cmp #2
    beq SourceVisual_FirstMissingPlayerWalk__p2_source_owner
    brl SourceVisual_FirstMissingPlayerWalk__none
SourceVisual_FirstMissingPlayerWalk__p2_source_owner:
.a16
.i16
    lda.l $7E0A85+CHAR_SELECTED
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
    bne SourceVisual_FirstMissingPlayerWalk__p2_not_jump
    brl SourceVisual_FirstMissingPlayerWalk__none
SourceVisual_FirstMissingPlayerWalk__p2_not_jump:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SourceVisual_FirstMissingPlayerWalk__p2_picture
    brl SourceVisual_FirstMissingPlayerWalk__none
SourceVisual_FirstMissingPlayerWalk__p2_picture:
.a16
.i16
    lda.l SVActor_Data+1
    and #$00FF
    cmp #1
    bne SourceVisual_FirstMissingPlayerWalk__p2_missing
    brl SourceVisual_FirstMissingPlayerWalk__none
SourceVisual_FirstMissingPlayerWalk__p2_missing:
.a16
.i16
    lda.l SourceVisual_State+38
    cmp #2
    bne SourceVisual_FirstMissingPlayerWalk__p2_not_ready_walk
    lda.l SourceVisual_State+62
    and #$00FF
    cmp #1
    bne SourceVisual_FirstMissingPlayerWalk__p2_not_ready_walk
    brl SourceVisual_FirstMissingPlayerWalk__none
SourceVisual_FirstMissingPlayerWalk__p2_not_ready_walk:
.a16
.i16
    lda.l SourceVisual_State+38
    cmp #1
    bne SourceVisual_FirstMissingPlayerWalk__p2_role
    lda.l SourceVisual_State+60
    and #$00FF
    bne SourceVisual_FirstMissingPlayerWalk__p2_role
    lda.l SourceVisual_State+62
    and #$00FF
    cmp #2
    bne SourceVisual_FirstMissingPlayerWalk__p2_not_attack
    brl SourceVisual_FirstMissingPlayerWalk__none
SourceVisual_FirstMissingPlayerWalk__p2_not_attack:
.a16
.i16
    cmp #7
    bne SourceVisual_FirstMissingPlayerWalk__p2_role
    brl SourceVisual_FirstMissingPlayerWalk__none
SourceVisual_FirstMissingPlayerWalk__p2_role:
.a16
.i16
    lda.l SourceVisual_Sa1RuntimeRole+133
    and #$00FF
    cmp #1
    beq SourceVisual_FirstMissingPlayerWalk__p2_choose
    cmp #0
    beq SourceVisual_FirstMissingPlayerWalk__p2_released
    brl SourceVisual_FirstMissingPlayerWalk__none
SourceVisual_FirstMissingPlayerWalk__p2_released:
.a16
.i16
    lda.l SourceVisual_State+38
    cmp #1
    beq SourceVisual_FirstMissingPlayerWalk__p2_pending
    brl SourceVisual_FirstMissingPlayerWalk__none
SourceVisual_FirstMissingPlayerWalk__p2_pending:
.a16
.i16
    lda.l SourceVisual_State+60
    and #$00FF
    beq SourceVisual_FirstMissingPlayerWalk__p2_unseen
    brl SourceVisual_FirstMissingPlayerWalk__none
SourceVisual_FirstMissingPlayerWalk__p2_unseen:
.a16
.i16
    lda.l SourceVisual_State+62
    and #$00FF
    cmp #1
    beq SourceVisual_FirstMissingPlayerWalk__p2_held_walk
    brl SourceVisual_FirstMissingPlayerWalk__none
SourceVisual_FirstMissingPlayerWalk__p2_held_walk:
.a16
.i16
SourceVisual_FirstMissingPlayerWalk__p2_choose:
.a16
.i16
    lda #$0A85
    rts
SourceVisual_FirstMissingPlayerWalk__none:
.a16
.i16
    lda #0
    rts

; Only invoked after ordinary allocation fails. Critical first/new-role work
; may cancel one unshown SAME-role foreign update with an existing completed
; picture, never a first picture, active jump or published desired lease.
; Completed/retiring pins are authoritative. Require source DMA idle and a
; genuinely exclusive, unpinned credit before changing any ownership.
SourceVisual_ReclaimRepeatedPose:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    lda.l SourceVisual_ActorSlot
    pha
    lda.l SourceVisual_Record
    pha
    lda.l SourceVisual_PieceIndex
    pha
    lda.l SourceVisual_BlockIndex
    pha
    lda.l SourceVisual_BlockRecord
    pha
    lda.l SourceVisual_BlockScan
    pha
    lda.l SourceVisual_BlockActorMask
    pha
    lda.l SourceVisual_BlockOther2
    pha
    lda.l SourceVisual_PaletteOwnerBit
    pha
    lda.l SourceVisual_PaletteScan
    pha
    lda.l SourceVisual_Temp
    pha
    jsr SVActor_Enabled
    bcs SourceVisual_ReclaimRepeatedPose__enabled
    brl SourceVisual_ReclaimRepeatedPose__no
SourceVisual_ReclaimRepeatedPose__enabled:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SourceVisual_ReclaimRepeatedPose__journal
    brl SourceVisual_ReclaimRepeatedPose__no
SourceVisual_ReclaimRepeatedPose__journal:
.a16
.i16
    lda.l $7E1760
    cmp #1
    beq SourceVisual_ReclaimRepeatedPose__host
    brl SourceVisual_ReclaimRepeatedPose__no
SourceVisual_ReclaimRepeatedPose__host:
.a16
.i16
    lda.l $7E46DE ; S6Normal_NmiContext: never reclaim from an interrupt
    cmp #0
    beq SourceVisual_ReclaimRepeatedPose__foreground
    brl SourceVisual_ReclaimRepeatedPose__no
SourceVisual_ReclaimRepeatedPose__foreground:
.a16
.i16
    lda.l Game_State
    cmp #0
    beq SourceVisual_ReclaimRepeatedPose__playing
    brl SourceVisual_ReclaimRepeatedPose__no
SourceVisual_ReclaimRepeatedPose__playing:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    cmp #6
    bcc SourceVisual_ReclaimRepeatedPose__caller_range
    brl SourceVisual_ReclaimRepeatedPose__no
SourceVisual_ReclaimRepeatedPose__caller_range:
.a16
.i16
    asl a
    tax
    lda.l SVActor_LoadDps,x
    sta.l SourceVisual_Temp
    tdc
    cmp.l SourceVisual_Temp
    beq SourceVisual_ReclaimRepeatedPose__caller_dp
    brl SourceVisual_ReclaimRepeatedPose__no
SourceVisual_ReclaimRepeatedPose__caller_dp:
.a16
.i16
    lda.l SourceVisual_Temp
    tax
    lda.l $7E0000+CHAR_HP,x
    and #$00FF
    bne SourceVisual_ReclaimRepeatedPose__caller_alive
    brl SourceVisual_ReclaimRepeatedPose__no
SourceVisual_ReclaimRepeatedPose__caller_alive:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    asl a
    cmp.l SourceVisual_Record
    beq SourceVisual_ReclaimRepeatedPose__caller_record
    brl SourceVisual_ReclaimRepeatedPose__no
SourceVisual_ReclaimRepeatedPose__caller_record:
.a16
.i16
    tax
    lda.l SourceVisual_State+6,x
    cmp #1
    beq SourceVisual_ReclaimRepeatedPose__caller_pending
    brl SourceVisual_ReclaimRepeatedPose__no
SourceVisual_ReclaimRepeatedPose__caller_pending:
.a16
.i16
    lda.l SourceVisual_State+30,x
    and #$00FF
    sta.l SourceVisual_Temp
    lda.l SourceVisual_State+29,x
    and #$00FF
    sta.l SourceVisual_BlockOther2
    lda.l SourceVisual_ActorSlot
    bne SourceVisual_ReclaimRepeatedPose__caller_other
    lda.l SourceVisual_CompletedValid
    bne SourceVisual_ReclaimRepeatedPose__caller_p1_valid
    brl SourceVisual_ReclaimRepeatedPose__critical
SourceVisual_ReclaimRepeatedPose__caller_p1_valid:
.a16
.i16
    lda.l SourceVisual_CompletedStage
    cmp.l Game_StageIndex
    beq SourceVisual_ReclaimRepeatedPose__caller_p1_stage
    brl SourceVisual_ReclaimRepeatedPose__no
SourceVisual_ReclaimRepeatedPose__caller_p1_stage:
.a16
.i16
    lda.l SourceVisual_CompletedEntry
    and #$00FF
    cmp.l SourceVisual_BlockOther2
    beq SourceVisual_ReclaimRepeatedPose__caller_p1_roster
    brl SourceVisual_ReclaimRepeatedPose__no
SourceVisual_ReclaimRepeatedPose__caller_p1_roster:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+1
    brl SourceVisual_ReclaimRepeatedPose__caller_role
SourceVisual_ReclaimRepeatedPose__caller_other:
.a16
.i16
    dec a
    asl a
    tax
    lda.l SVActor_Bases,x
    tax
    lda.l SVActor_Data+SVActor_Valid,x
    cmp #1
    beq SourceVisual_ReclaimRepeatedPose__caller_other_valid
    brl SourceVisual_ReclaimRepeatedPose__critical
SourceVisual_ReclaimRepeatedPose__caller_other_valid:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage,x
    cmp.l Game_StageIndex
    beq SourceVisual_ReclaimRepeatedPose__caller_other_stage
    brl SourceVisual_ReclaimRepeatedPose__no
SourceVisual_ReclaimRepeatedPose__caller_other_stage:
.a16
.i16
    lda.l SVActor_Data,x
    and #$00FF
    cmp.l SourceVisual_BlockOther2
    beq SourceVisual_ReclaimRepeatedPose__caller_other_roster
    brl SourceVisual_ReclaimRepeatedPose__no
SourceVisual_ReclaimRepeatedPose__caller_other_roster:
.a16
.i16
    lda.l SVActor_Data+1,x
SourceVisual_ReclaimRepeatedPose__caller_role:
.a16
.i16
    and #$00FF
    cmp.l SourceVisual_Temp
    bne SourceVisual_ReclaimRepeatedPose__caller_new_role
    brl SourceVisual_ReclaimRepeatedPose__no
SourceVisual_ReclaimRepeatedPose__caller_new_role:
.a16
.i16
    lda.l SourceVisual_Temp
    cmp #1
    beq SourceVisual_ReclaimRepeatedPose__critical
    cmp #2
    beq SourceVisual_ReclaimRepeatedPose__critical
    cmp #7
    beq SourceVisual_ReclaimRepeatedPose__critical
    brl SourceVisual_ReclaimRepeatedPose__no
SourceVisual_ReclaimRepeatedPose__critical:
.a16
.i16
    jsr SourceVisual_HasOwnedDma
    bcc SourceVisual_ReclaimRepeatedPose__source_dma_idle
    brl SourceVisual_ReclaimRepeatedPose__no
SourceVisual_ReclaimRepeatedPose__source_dma_idle:
.a16
.i16
    ldx #0
    ldy #0
SourceVisual_ReclaimRepeatedPose__dma_owner_scan:
.a16
.i16
    lda.l DmaQueue+4,x
    and #DMA_OPT_ACTIVE
    bne SourceVisual_ReclaimRepeatedPose__dma_active
    brl SourceVisual_ReclaimRepeatedPose__dma_owner_next
SourceVisual_ReclaimRepeatedPose__dma_active:
.a16
.i16
    phx
    tya
    tax
    lda.l DmaQueue_Owner,x
    and #$00FF
    plx
    cmp #0
    beq SourceVisual_ReclaimRepeatedPose__dma_unowned
    brl SourceVisual_ReclaimRepeatedPose__no
SourceVisual_ReclaimRepeatedPose__dma_unowned:
.a16
.i16
    ; Only standard OAM pairs and BG VRAM outside the OBJ window may
    ; coexist. Unknown types/options, all CGRAM and specialized jobs wait.
    lda.l DmaQueue+4,x
    and #$00FF
    cmp #(DMA_OPT_ACTIVE | DMA_TYPE_OAM)
    beq SourceVisual_ReclaimRepeatedPose__dma_oam
    cmp #(DMA_OPT_ACTIVE | DMA_TYPE_VRAM)
    beq SourceVisual_ReclaimRepeatedPose__dma_bg_vram
    brl SourceVisual_ReclaimRepeatedPose__no
SourceVisual_ReclaimRepeatedPose__dma_oam:
.a16
.i16
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$7E
    beq SourceVisual_ReclaimRepeatedPose__dma_oam_bank
    jsr SourcePacket_IsQueueRow
    bcc SourceVisual_ReclaimRepeatedPose__private_oam_no
    brl SourceVisual_ReclaimRepeatedPose__dma_owner_next
SourceVisual_ReclaimRepeatedPose__private_oam_no:
.a16
.i16
    brl SourceVisual_ReclaimRepeatedPose__no
SourceVisual_ReclaimRepeatedPose__dma_oam_bank:
.a16
.i16
    lda.l DmaQueue+5,x
    cmp #$5100
    beq SourceVisual_ReclaimRepeatedPose__dma_oam_main
    cmp #$5300
    beq SourceVisual_ReclaimRepeatedPose__dma_oam_hi
    brl SourceVisual_ReclaimRepeatedPose__no
SourceVisual_ReclaimRepeatedPose__dma_oam_main:
.a16
.i16
    lda.l DmaQueue+2,x
    beq SourceVisual_ReclaimRepeatedPose__dma_oam_main_target
    brl SourceVisual_ReclaimRepeatedPose__no
SourceVisual_ReclaimRepeatedPose__dma_oam_main_target:
.a16
.i16
    lda.l DmaQueue,x
    beq SourceVisual_ReclaimRepeatedPose__dma_oam_invalid
    cmp #513
    bcs SourceVisual_ReclaimRepeatedPose__dma_oam_invalid
    and #3
    beq SourceVisual_ReclaimRepeatedPose__dma_oam_valid
SourceVisual_ReclaimRepeatedPose__dma_oam_invalid:
.a16
.i16
    brl SourceVisual_ReclaimRepeatedPose__no
SourceVisual_ReclaimRepeatedPose__dma_oam_hi:
.a16
.i16
    lda.l DmaQueue+2,x
    cmp #$0100
    beq SourceVisual_ReclaimRepeatedPose__dma_oam_hi_target
    brl SourceVisual_ReclaimRepeatedPose__no
SourceVisual_ReclaimRepeatedPose__dma_oam_hi_target:
.a16
.i16
    lda.l DmaQueue,x
    beq SourceVisual_ReclaimRepeatedPose__dma_oam_invalid
    cmp #33
    bcc SourceVisual_ReclaimRepeatedPose__dma_oam_valid
    brl SourceVisual_ReclaimRepeatedPose__no
SourceVisual_ReclaimRepeatedPose__dma_oam_valid:
.a16
.i16
    brl SourceVisual_ReclaimRepeatedPose__dma_owner_next
SourceVisual_ReclaimRepeatedPose__dma_bg_vram:
.a16
.i16
    lda.l DmaQueue,x
    bne SourceVisual_ReclaimRepeatedPose__dma_bg_length_nonzero
    brl SourceVisual_ReclaimRepeatedPose__no
SourceVisual_ReclaimRepeatedPose__dma_bg_length_nonzero:
.a16
.i16
    cmp #$4000
    bcc SourceVisual_ReclaimRepeatedPose__dma_bg_length
    brl SourceVisual_ReclaimRepeatedPose__no
SourceVisual_ReclaimRepeatedPose__dma_bg_length:
.a16
.i16
    sta.l SourceVisual_Temp
    lda.l DmaQueue+2,x
    cmp #$C000
    bcs SourceVisual_ReclaimRepeatedPose__dma_bg_safe
    cmp #$8000
    bcc SourceVisual_ReclaimRepeatedPose__dma_bg_below
    brl SourceVisual_ReclaimRepeatedPose__no
SourceVisual_ReclaimRepeatedPose__dma_bg_below:
.a16
.i16
    clc
    adc.l SourceVisual_Temp
    cmp #$8001
    bcc SourceVisual_ReclaimRepeatedPose__dma_bg_safe
    brl SourceVisual_ReclaimRepeatedPose__no
SourceVisual_ReclaimRepeatedPose__dma_bg_safe:
.a16
.i16
    brl SourceVisual_ReclaimRepeatedPose__dma_owner_next
SourceVisual_ReclaimRepeatedPose__dma_owner_next:
.a16
.i16
    txa
    clc
    adc #8
    tax
    iny
    cpx #64
    bcs SourceVisual_ReclaimRepeatedPose__dma_owners_done
    brl SourceVisual_ReclaimRepeatedPose__dma_owner_scan
SourceVisual_ReclaimRepeatedPose__dma_owners_done:
.a16
.i16
    ldy #0
SourceVisual_ReclaimRepeatedPose__candidate:
.a16
.i16
    tya
    cmp.l SourceVisual_ActorSlot
    bne SourceVisual_ReclaimRepeatedPose__foreign
    brl SourceVisual_ReclaimRepeatedPose__next_candidate
SourceVisual_ReclaimRepeatedPose__foreign:
.a16
.i16
    tya
    asl a
    tax
    lda.l SVActor_LoadDps,x
    tax
    lda.l $7E0000+CHAR_HP,x
    and #$00FF
    bne SourceVisual_ReclaimRepeatedPose__victim_alive
    brl SourceVisual_ReclaimRepeatedPose__next_candidate
SourceVisual_ReclaimRepeatedPose__victim_alive:
.a16
.i16
    cpy #2
    bcs SourceVisual_ReclaimRepeatedPose__victim_not_jump
    lda.l $7E0000+CHAR_SELECTED,x
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
    bne SourceVisual_ReclaimRepeatedPose__victim_not_jump
    brl SourceVisual_ReclaimRepeatedPose__next_candidate
SourceVisual_ReclaimRepeatedPose__victim_not_jump:
.a16
.i16
    tya
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_State+6,x
    cmp #1
    beq SourceVisual_ReclaimRepeatedPose__victim_pending
    brl SourceVisual_ReclaimRepeatedPose__next_candidate
SourceVisual_ReclaimRepeatedPose__victim_pending:
.a16
.i16
    lda.l SourceVisual_State+28,x
    and #$00FF
    beq SourceVisual_ReclaimRepeatedPose__victim_unshown
    brl SourceVisual_ReclaimRepeatedPose__next_candidate
SourceVisual_ReclaimRepeatedPose__victim_unshown:
.a16
.i16
    lda.l SourceVisual_State+30,x
    and #$00FF
    cmp #7
    bne SourceVisual_ReclaimRepeatedPose__victim_not_jump_role
    brl SourceVisual_ReclaimRepeatedPose__next_candidate
SourceVisual_ReclaimRepeatedPose__victim_not_jump_role:
.a16
.i16
    sta.l SourceVisual_Temp
    lda.l SourceVisual_State+29,x
    and #$00FF
    sta.l SourceVisual_BlockOther2
    tya
    bne SourceVisual_ReclaimRepeatedPose__victim_other
    lda.l SourceVisual_CompletedValid
    bne SourceVisual_ReclaimRepeatedPose__victim_p1_valid
    brl SourceVisual_ReclaimRepeatedPose__next_candidate
SourceVisual_ReclaimRepeatedPose__victim_p1_valid:
.a16
.i16
    lda.l SourceVisual_CompletedStage
    cmp.l Game_StageIndex
    beq SourceVisual_ReclaimRepeatedPose__victim_p1_stage
    brl SourceVisual_ReclaimRepeatedPose__next_candidate
SourceVisual_ReclaimRepeatedPose__victim_p1_stage:
.a16
.i16
    lda.l SourceVisual_CompletedEntry
    and #$00FF
    cmp.l SourceVisual_BlockOther2
    beq SourceVisual_ReclaimRepeatedPose__victim_p1_roster
    brl SourceVisual_ReclaimRepeatedPose__next_candidate
SourceVisual_ReclaimRepeatedPose__victim_p1_roster:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+12
    and #$00FF
    bne SourceVisual_ReclaimRepeatedPose__victim_p1_nonempty
    brl SourceVisual_ReclaimRepeatedPose__next_candidate
SourceVisual_ReclaimRepeatedPose__victim_p1_nonempty:
.a16
.i16
    cmp #SOURCE_VISUAL_MAX_PIECES+1
    bcc SourceVisual_ReclaimRepeatedPose__victim_p1_nonempty_bounded
    brl SourceVisual_ReclaimRepeatedPose__next_candidate
SourceVisual_ReclaimRepeatedPose__victim_p1_nonempty_bounded:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+1
    brl SourceVisual_ReclaimRepeatedPose__victim_role
SourceVisual_ReclaimRepeatedPose__victim_other:
.a16
.i16
    dec a
    asl a
    tax
    lda.l SVActor_Bases,x
    tax
    lda.l SVActor_Data+SVActor_Valid,x
    cmp #1
    beq SourceVisual_ReclaimRepeatedPose__victim_other_valid
    brl SourceVisual_ReclaimRepeatedPose__next_candidate
SourceVisual_ReclaimRepeatedPose__victim_other_valid:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage,x
    cmp.l Game_StageIndex
    beq SourceVisual_ReclaimRepeatedPose__victim_other_stage
    brl SourceVisual_ReclaimRepeatedPose__next_candidate
SourceVisual_ReclaimRepeatedPose__victim_other_stage:
.a16
.i16
    lda.l SVActor_Data,x
    and #$00FF
    cmp.l SourceVisual_BlockOther2
    beq SourceVisual_ReclaimRepeatedPose__victim_other_roster
    brl SourceVisual_ReclaimRepeatedPose__next_candidate
SourceVisual_ReclaimRepeatedPose__victim_other_roster:
.a16
.i16
    lda.l SVActor_Data+12,x
    and #$00FF
    bne SourceVisual_ReclaimRepeatedPose__victim_other_nonempty
    brl SourceVisual_ReclaimRepeatedPose__next_candidate
SourceVisual_ReclaimRepeatedPose__victim_other_nonempty:
.a16
.i16
    cmp #SOURCE_VISUAL_MAX_PIECES+1
    bcc SourceVisual_ReclaimRepeatedPose__victim_other_nonempty_bounded
    brl SourceVisual_ReclaimRepeatedPose__next_candidate
SourceVisual_ReclaimRepeatedPose__victim_other_nonempty_bounded:
.a16
.i16
    lda.l SVActor_Data+1,x
SourceVisual_ReclaimRepeatedPose__victim_role:
.a16
.i16
    and #$00FF
    cmp.l SourceVisual_Temp
    beq SourceVisual_ReclaimRepeatedPose__same_role
    brl SourceVisual_ReclaimRepeatedPose__next_candidate
SourceVisual_ReclaimRepeatedPose__same_role:
.a16
.i16
    phy
    lda #1
SourceVisual_ReclaimRepeatedPose__bit:
.a16
.i16
    cpy #0
    beq SourceVisual_ReclaimRepeatedPose__bit_ready
    asl a
    dey
    bra SourceVisual_ReclaimRepeatedPose__bit
SourceVisual_ReclaimRepeatedPose__bit_ready:
.a16
.i16
    ply
    sta.l SourceVisual_BlockOther2
    ldx #0
SourceVisual_ReclaimRepeatedPose__credit:
.a16
.i16
    lda.l SourceVisual_BlockCache+2,x
    cmp #1
    beq SourceVisual_ReclaimRepeatedPose__credit_state
    cmp #2
    beq SourceVisual_ReclaimRepeatedPose__credit_state
    brl SourceVisual_ReclaimRepeatedPose__credit_next
SourceVisual_ReclaimRepeatedPose__credit_state:
.a16
.i16
    sep #$20
.a8
    lda.l SourceVisual_BlockCache+4,x
    cmp.l SourceVisual_BlockOther2
    bne SourceVisual_ReclaimRepeatedPose__credit_next8
    phy
    jsr SVActor_ProtectBlocks
    ply
    bcc SourceVisual_ReclaimRepeatedPose__credit_found8
SourceVisual_ReclaimRepeatedPose__credit_next8:
.a8
.i16
    rep #$30
SourceVisual_ReclaimRepeatedPose__credit_next:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #512
    bcs SourceVisual_ReclaimRepeatedPose__next_candidate
    brl SourceVisual_ReclaimRepeatedPose__credit
SourceVisual_ReclaimRepeatedPose__credit_found8:
.a8
.i16
    rep #$30
SourceVisual_ReclaimRepeatedPose__release:
.a16
.i16
    tya
    sta.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l SourceVisual_Record
    jsr SourceVisual_ReleaseActorBlocks
    jsr SourceVisual_ReleaseActorPalettes
    lda.l SourceVisual_Record
    tax
    lda #0
    sta.l SourceVisual_State+6,x
    sep #$20
.a8
    sta.l SourceVisual_State+28,x
    sta.l SourceVisual_State+31,x
    rep #$30
.a16
.i16
    lda.l SourceVisual_ActorSlot
    inc a
    cmp.l SVActor_LoadOwner
    bne SourceVisual_ReclaimRepeatedPose__released
    lda #0
    sta.l SVActor_LoadOwner
SourceVisual_ReclaimRepeatedPose__released:
.a16
.i16
    brl SourceVisual_ReclaimRepeatedPose__yes
SourceVisual_ReclaimRepeatedPose__next_candidate:
.a16
.i16
    iny
    cpy #6
    bcs SourceVisual_ReclaimRepeatedPose__no
    brl SourceVisual_ReclaimRepeatedPose__candidate
SourceVisual_ReclaimRepeatedPose__yes:
.a16
.i16
    pla
    sta.l SourceVisual_Temp
    pla
    sta.l SourceVisual_PaletteScan
    pla
    sta.l SourceVisual_PaletteOwnerBit
    pla
    sta.l SourceVisual_BlockOther2
    pla
    sta.l SourceVisual_BlockActorMask
    pla
    sta.l SourceVisual_BlockScan
    pla
    sta.l SourceVisual_BlockRecord
    pla
    sta.l SourceVisual_BlockIndex
    pla
    sta.l SourceVisual_PieceIndex
    pla
    sta.l SourceVisual_Record
    pla
    sta.l SourceVisual_ActorSlot
    ply
    plx
    pla
    plp
    sec
    rts
SourceVisual_ReclaimRepeatedPose__no:
.a16
.i16
    pla
    sta.l SourceVisual_Temp
    pla
    sta.l SourceVisual_PaletteScan
    pla
    sta.l SourceVisual_PaletteOwnerBit
    pla
    sta.l SourceVisual_BlockOther2
    pla
    sta.l SourceVisual_BlockActorMask
    pla
    sta.l SourceVisual_BlockScan
    pla
    sta.l SourceVisual_BlockRecord
    pla
    sta.l SourceVisual_BlockIndex
    pla
    sta.l SourceVisual_PieceIndex
    pla
    sta.l SourceVisual_Record
    pla
    sta.l SourceVisual_ActorSlot
    ply
    plx
    pla
    plp
    clc
    rts

; Called only for a missing first NPC picture from loader-only admission.
; First establish that the actual player owner is an unseen repeated role.
; Reclaim scans players before NPCs: at most two cancellations therefore
; reach that owner, while preserving every completed/retiring resource.

SVActor_YieldRepeatedPlayerForFirstNpc:
.a16
.i16
    lda.l SVActor_LoadOwner
    cmp #1
    bcs SVActor_YieldRepeatedPlayerForFirstNpc__guard_1
    brl SVActor_YieldRepeatedPlayerForFirstNpc__no
SVActor_YieldRepeatedPlayerForFirstNpc__guard_1:
.a16
.i16
    cmp #3
    bcc SVActor_YieldRepeatedPlayerForFirstNpc__guard_2
    brl SVActor_YieldRepeatedPlayerForFirstNpc__no
SVActor_YieldRepeatedPlayerForFirstNpc__guard_2:
.a16
.i16
    dec a
    asl a
    tax
    lda.l SVActor_LoadDps,x
    tax
    lda.l $7E0000+CHAR_HP,x
    and #$00FF
    bne SVActor_YieldRepeatedPlayerForFirstNpc__guard_3
    brl SVActor_YieldRepeatedPlayerForFirstNpc__no
SVActor_YieldRepeatedPlayerForFirstNpc__guard_3:
.a16
.i16
    lda.l $7E0000+CHAR_SELECTED,x
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
    bne SVActor_YieldRepeatedPlayerForFirstNpc__guard_4
    brl SVActor_YieldRepeatedPlayerForFirstNpc__no
SVActor_YieldRepeatedPlayerForFirstNpc__guard_4:
.a16
.i16
    lda.l SVActor_LoadOwner
    dec a
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_State+6,x
    cmp #1
    beq SVActor_YieldRepeatedPlayerForFirstNpc__guard_5
    brl SVActor_YieldRepeatedPlayerForFirstNpc__no
SVActor_YieldRepeatedPlayerForFirstNpc__guard_5:
.a16
.i16
    lda.l SourceVisual_State+28,x
    and #$00FF
    beq SVActor_YieldRepeatedPlayerForFirstNpc__guard_6
    brl SVActor_YieldRepeatedPlayerForFirstNpc__no
SVActor_YieldRepeatedPlayerForFirstNpc__guard_6:
.a16
.i16
    lda.l SVActor_LoadOwner
    cmp #1
    bne SVActor_YieldRepeatedPlayerForFirstNpc__p2
    lda.l SourceVisual_CompletedValid
    bne SVActor_YieldRepeatedPlayerForFirstNpc__guard_7
    brl SVActor_YieldRepeatedPlayerForFirstNpc__no
SVActor_YieldRepeatedPlayerForFirstNpc__guard_7:
.a16
.i16
    lda.l SourceVisual_CompletedStage
    cmp.l Game_StageIndex
    beq SVActor_YieldRepeatedPlayerForFirstNpc__guard_8
    brl SVActor_YieldRepeatedPlayerForFirstNpc__no
SVActor_YieldRepeatedPlayerForFirstNpc__guard_8:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+12
    and #$00FF
    bne SVActor_YieldRepeatedPlayerForFirstNpc__guard_9
    brl SVActor_YieldRepeatedPlayerForFirstNpc__no
SVActor_YieldRepeatedPlayerForFirstNpc__guard_9:
.a16
.i16
    cmp #66
    bcc SVActor_YieldRepeatedPlayerForFirstNpc__guard_10
    brl SVActor_YieldRepeatedPlayerForFirstNpc__no
SVActor_YieldRepeatedPlayerForFirstNpc__guard_10:
.a16
.i16
    lda.l SourceVisual_CompletedRoster
    sep #$20
.a8
    cmp.l SourceVisual_State+29,x
    rep #$30
.a16
.i16
    beq SVActor_YieldRepeatedPlayerForFirstNpc__guard_11
    brl SVActor_YieldRepeatedPlayerForFirstNpc__no
SVActor_YieldRepeatedPlayerForFirstNpc__guard_11:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+1
    bra SVActor_YieldRepeatedPlayerForFirstNpc__role
SVActor_YieldRepeatedPlayerForFirstNpc__p2:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SVActor_YieldRepeatedPlayerForFirstNpc__guard_12
    brl SVActor_YieldRepeatedPlayerForFirstNpc__no
SVActor_YieldRepeatedPlayerForFirstNpc__guard_12:
.a16
.i16
    lda.l SVActor_Data+SVActor_Stage
    cmp.l Game_StageIndex
    beq SVActor_YieldRepeatedPlayerForFirstNpc__guard_13
    brl SVActor_YieldRepeatedPlayerForFirstNpc__no
SVActor_YieldRepeatedPlayerForFirstNpc__guard_13:
.a16
.i16
    lda.l SVActor_Data+12
    and #$00FF
    bne SVActor_YieldRepeatedPlayerForFirstNpc__guard_14
    brl SVActor_YieldRepeatedPlayerForFirstNpc__no
SVActor_YieldRepeatedPlayerForFirstNpc__guard_14:
.a16
.i16
    cmp #66
    bcc SVActor_YieldRepeatedPlayerForFirstNpc__guard_15
    brl SVActor_YieldRepeatedPlayerForFirstNpc__no
SVActor_YieldRepeatedPlayerForFirstNpc__guard_15:
.a16
.i16
    lda.l SVActor_Data+SVActor_Roster
    sep #$20
.a8
    cmp.l SourceVisual_State+29,x
    rep #$30
.a16
.i16
    beq SVActor_YieldRepeatedPlayerForFirstNpc__guard_16
    brl SVActor_YieldRepeatedPlayerForFirstNpc__no
SVActor_YieldRepeatedPlayerForFirstNpc__guard_16:
.a16
.i16
    lda.l SVActor_Data+1
SVActor_YieldRepeatedPlayerForFirstNpc__role:
.a16
.i16
    sep #$20
.a8
    cmp.l SourceVisual_State+30,x
    rep #$30
.a16
.i16
    beq SVActor_YieldRepeatedPlayerForFirstNpc__guard_17
    brl SVActor_YieldRepeatedPlayerForFirstNpc__no
SVActor_YieldRepeatedPlayerForFirstNpc__guard_17:
.a16
.i16
    ; Require actual exclusive unheld block credit in this owner, so two
    ; scans cannot cancel unrelated jobs while the real owner remains.
    lda.l SourceVisual_Temp
    pha
    lda.l SVActor_LoadOwner
    sta.l SourceVisual_Temp
    ldx #0
SVActor_YieldRepeatedPlayerForFirstNpc__credit:
.a16
.i16
    lda.l SourceVisual_BlockCache+4,x
    and #$00FF
    cmp.l SourceVisual_Temp
    bne SVActor_YieldRepeatedPlayerForFirstNpc__next_credit
    lda.l SourceVisual_BlockCache+2,x
    cmp #1
    beq SVActor_YieldRepeatedPlayerForFirstNpc__check_pins
    cmp #2
    bne SVActor_YieldRepeatedPlayerForFirstNpc__next_credit
SVActor_YieldRepeatedPlayerForFirstNpc__check_pins:
.a16
.i16
    phx
    jsr SVActor_ProtectBlocks
    plx
    bcs SVActor_YieldRepeatedPlayerForFirstNpc__next_credit
    jsr SourceVisual_ReclaimRepeatedPose
    bcc SVActor_YieldRepeatedPlayerForFirstNpc__restore_no
    lda.l SVActor_LoadOwner
    beq SVActor_YieldRepeatedPlayerForFirstNpc__restore_yes
    jsr SourceVisual_ReclaimRepeatedPose
    lda.l SVActor_LoadOwner
    bne SVActor_YieldRepeatedPlayerForFirstNpc__restore_no
SVActor_YieldRepeatedPlayerForFirstNpc__restore_yes:
.a16
.i16
    pla
    sta.l SourceVisual_Temp
    sec
    rts
SVActor_YieldRepeatedPlayerForFirstNpc__next_credit:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #512
    bcc SVActor_YieldRepeatedPlayerForFirstNpc__credit
SVActor_YieldRepeatedPlayerForFirstNpc__restore_no:
.a16
.i16
    pla
    sta.l SourceVisual_Temp
SVActor_YieldRepeatedPlayerForFirstNpc__no:
.a16
.i16
    clc
    rts

; Read-only first-punch selection, used only by the existing guarded main wait.
; Keep an in-progress player's producer, then P1. Never add idle work during
; either live player's physical jump or an NPC's missing first picture.
SourceVisual_FirstMissingPlayerAttack:
.a16
.i16
    lda.l $7E0000+2560+CHAR_HP
    and #$00FF
    beq SourceVisual_FirstMissingPlayerAttack__jump_next0
    lda.l $7E0000+2560+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    bne SourceVisual_FirstMissingPlayerAttack__jump_next0
    lda.l $7E0000+2560+CHAR_SELECTED
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
    bne SourceVisual_FirstMissingPlayerAttack__jump_next0
    brl SourceVisual_FirstMissingPlayerAttack__none
SourceVisual_FirstMissingPlayerAttack__jump_next0:
.a16
.i16
    lda.l $7E0000+2693+CHAR_HP
    and #$00FF
    beq SourceVisual_FirstMissingPlayerAttack__jump_next1
    lda.l $7E0000+2693+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    bne SourceVisual_FirstMissingPlayerAttack__jump_next1
    lda.l $7E0000+2693+CHAR_SELECTED
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
    bne SourceVisual_FirstMissingPlayerAttack__jump_next1
    brl SourceVisual_FirstMissingPlayerAttack__none
SourceVisual_FirstMissingPlayerAttack__jump_next1:
.a16
.i16
    jsr SVActor_LoadOwnerNeedsFirstPicture
    bcc SourceVisual_FirstMissingPlayerAttack__players
    brl SourceVisual_FirstMissingPlayerAttack__none
SourceVisual_FirstMissingPlayerAttack__players:
.a16
.i16
    lda.l SVActor_LoadOwner
    cmp #2
    beq SourceVisual_FirstMissingPlayerAttack__p2_first
    jsr SourceVisual_FirstMissingPlayerAttack__p1
    bcs SourceVisual_FirstMissingPlayerAttack__done
    jsr SourceVisual_FirstMissingPlayerAttack__p2
    bcs SourceVisual_FirstMissingPlayerAttack__done
    bra SourceVisual_FirstMissingPlayerAttack__none
SourceVisual_FirstMissingPlayerAttack__p2_first:
.a16
.i16
    jsr SourceVisual_FirstMissingPlayerAttack__p2
    bcs SourceVisual_FirstMissingPlayerAttack__done
    jsr SourceVisual_FirstMissingPlayerAttack__p1
    bcs SourceVisual_FirstMissingPlayerAttack__done
SourceVisual_FirstMissingPlayerAttack__none:
.a16
.i16
    lda #0
SourceVisual_FirstMissingPlayerAttack__done:
.a16
.i16
    rts
SourceVisual_FirstMissingPlayerAttack__p1:
.a16
.i16
    lda.l $7E0000+2560+CHAR_HP
    and #$00FF
    bne SourceVisual_FirstMissingPlayerAttack__p1_guard0
    brl SourceVisual_FirstMissingPlayerAttack__p1_no
SourceVisual_FirstMissingPlayerAttack__p1_guard0:
.a16
.i16
    lda.l $7E0000+2560+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    beq SourceVisual_FirstMissingPlayerAttack__p1_guard1
    brl SourceVisual_FirstMissingPlayerAttack__p1_no
SourceVisual_FirstMissingPlayerAttack__p1_guard1:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy+0
    and #$00FF
    cmp #2
    beq SourceVisual_FirstMissingPlayerAttack__p1_guard2
    brl SourceVisual_FirstMissingPlayerAttack__p1_no
SourceVisual_FirstMissingPlayerAttack__p1_guard2:
.a16
.i16
    lda.l SourceVisual_State+6
    cmp #1
    beq SourceVisual_FirstMissingPlayerAttack__p1_guard3
    brl SourceVisual_FirstMissingPlayerAttack__p1_no
SourceVisual_FirstMissingPlayerAttack__p1_guard3:
.a16
.i16
    lda.l SourceVisual_State+28
    and #$00FF
    cmp #0
    beq SourceVisual_FirstMissingPlayerAttack__p1_guard4
    brl SourceVisual_FirstMissingPlayerAttack__p1_no
SourceVisual_FirstMissingPlayerAttack__p1_guard4:
.a16
.i16
    lda.l SourceVisual_State+30
    and #$00FF
    cmp #2
    beq SourceVisual_FirstMissingPlayerAttack__p1_guard5
    brl SourceVisual_FirstMissingPlayerAttack__p1_no
SourceVisual_FirstMissingPlayerAttack__p1_guard5:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    cmp #1
    bne SourceVisual_FirstMissingPlayerAttack__p1_no
    lda.l SourceVisual_CompletedStage
    cmp.l Game_StageIndex
    bne SourceVisual_FirstMissingPlayerAttack__p1_no
    lda.l $7E0000+2560+CHAR_ROSTER_INDEX
    and #$00FF
    cmp.l SourceVisual_CompletedRoster
    bne SourceVisual_FirstMissingPlayerAttack__p1_no
    lda.l SourceVisual_CompletedEntry+12
    and #$00FF
    beq SourceVisual_FirstMissingPlayerAttack__p1_no
    cmp #66
    bcs SourceVisual_FirstMissingPlayerAttack__p1_no
    lda.l SourceVisual_CompletedEntry+1
    and #$00FF
    cmp #2
    beq SourceVisual_FirstMissingPlayerAttack__p1_no
    lda #2560
    sec
    rts
SourceVisual_FirstMissingPlayerAttack__p1_no:
.a16
.i16
    clc
    rts
SourceVisual_FirstMissingPlayerAttack__p2:
.a16
.i16
    lda.l $7E0000+2693+CHAR_HP
    and #$00FF
    bne SourceVisual_FirstMissingPlayerAttack__p2_guard0
    brl SourceVisual_FirstMissingPlayerAttack__p2_no
SourceVisual_FirstMissingPlayerAttack__p2_guard0:
.a16
.i16
    lda.l $7E0000+2693+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    beq SourceVisual_FirstMissingPlayerAttack__p2_guard1
    brl SourceVisual_FirstMissingPlayerAttack__p2_no
SourceVisual_FirstMissingPlayerAttack__p2_guard1:
.a16
.i16
    lda.l SourceVisual_Sa1OwnerPolicy+133
    and #$00FF
    cmp #2
    beq SourceVisual_FirstMissingPlayerAttack__p2_guard2
    brl SourceVisual_FirstMissingPlayerAttack__p2_no
SourceVisual_FirstMissingPlayerAttack__p2_guard2:
.a16
.i16
    lda.l SourceVisual_State+38
    cmp #1
    beq SourceVisual_FirstMissingPlayerAttack__p2_guard3
    brl SourceVisual_FirstMissingPlayerAttack__p2_no
SourceVisual_FirstMissingPlayerAttack__p2_guard3:
.a16
.i16
    lda.l SourceVisual_State+60
    and #$00FF
    cmp #0
    beq SourceVisual_FirstMissingPlayerAttack__p2_guard4
    brl SourceVisual_FirstMissingPlayerAttack__p2_no
SourceVisual_FirstMissingPlayerAttack__p2_guard4:
.a16
.i16
    lda.l SourceVisual_State+62
    and #$00FF
    cmp #2
    beq SourceVisual_FirstMissingPlayerAttack__p2_guard5
    brl SourceVisual_FirstMissingPlayerAttack__p2_no
SourceVisual_FirstMissingPlayerAttack__p2_guard5:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    bne SourceVisual_FirstMissingPlayerAttack__p2_no
    lda.l SVActor_Data+SVActor_Stage
    cmp.l Game_StageIndex
    bne SourceVisual_FirstMissingPlayerAttack__p2_no
    lda.l $7E0000+2693+CHAR_ROSTER_INDEX
    and #$00FF
    cmp.l SVActor_Data+SVActor_Roster
    bne SourceVisual_FirstMissingPlayerAttack__p2_no
    lda.l SVActor_Data+12
    and #$00FF
    beq SourceVisual_FirstMissingPlayerAttack__p2_no
    cmp #66
    bcs SourceVisual_FirstMissingPlayerAttack__p2_no
    lda.l SVActor_Data+1
    and #$00FF
    cmp #2
    beq SourceVisual_FirstMissingPlayerAttack__p2_no
    lda #2693
    sec
    rts
SourceVisual_FirstMissingPlayerAttack__p2_no:
.a16
.i16
    clc
    rts

.include "source_first_idle_reuse.pasm"

; Long-call bridges keep existing bank10 short-call ABI unchanged.
SourceCritical_Bridge_SVActor_MetaMatch:
.a16
.i16
    jsr SVActor_MetaMatch
    rtl
SourceCritical_Bridge_SourceVisual_FindBlock:
.a16
.i16
    jsr SourceVisual_FindBlock
    rtl
SourceCritical_Bridge_SourceRom_ResolveTagged:
.a16
.i16
    jsr SourceRom_ResolveTagged
    rtl
SourceCritical_Bridge_SourceRom_HasBlockDma:
.a16
.i16
    jsr SourceRom_HasBlockDma
    rtl
SourceCritical_Bridge_SourceRom_HasStagingDma:
.a16
.i16
    jsr SourceRom_HasStagingDma
    rtl
