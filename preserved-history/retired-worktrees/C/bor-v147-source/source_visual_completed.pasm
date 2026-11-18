; P1 completed source packet. $7EEB00-$7EEFFF is after the frontpanel's
; $7EEAB6 end and before G12's $7EF000 trace. No source/world state lives here.
SourceVisual_CompletedEntry = $7EEB00 ; 24 immutable catalog bytes
SourceVisual_CompletedLease = $7EEB18 ; 32-byte palette/entry lease snapshot
SourceVisual_CompletedPieces = $7EEB40 ; 65 * 16 bytes, ends $7EEF50
SourceVisual_CompletedMap = $7EEF50 ; 65 one-byte block mappings
SourceVisual_CompletedValid = $7EEFA0
SourceVisual_CompletedAwait = $7EEFA2
SourceVisual_CompletedPending = $7EEFA4
SourceVisual_CompletedRetire = $7EEFA6
SourceVisual_CompletedCommitRetire = $7EEFA8
SourceVisual_CompletedStage = $7EEFAA
SourceVisual_CompletedRoster = $7EEFAC
SourceVisual_CompletedSavedBusy = $7EEFAE
SourceVisual_CompletedHeld = $7EEFB0
SourceVisual_CompletedMagic = $7EEFB2
SourceVisual_CompletedResult = $7EEFB4
SourceVisual_CompletedIndex = $7EEFB6
SourceVisual_CompletedCount = $7EEFB8
SourceVisual_CompletedCaptures = $7EEFBA
SourceVisual_CompletedFallbacks = $7EEFBC
SourceVisual_CompletedAcks = $7EEFBE
SourceVisual_CompletedQueueMask = $7EEFC0
SourceVisual_CompletedOwners = $7EEFC2
SourceVisual_CompletedNewOwners = $7EEFC4
SourceVisual_CompletedEarly = $7EEFC6
SourceVisual_CompletedMainBytes = $7EEFC8
SourceVisual_LegacyCgramDrops = $7EEFCA
SourceVisual_CompletedSavedEntry = $7EEFE0 ; 24 bytes, ends $7EEFF8

; Owner bits 0..5 remain physical actors. Bit 6 pins the completed packet;
; bit 7 pins the previous hardware packet until BOTH OAM transfers retire.
; BeginResolve calls this before the new run. Old resource pins are released
; only after a real replacement/hidden OAM packet has been submitted/retired.
SourceVisual_CompletedInit:
    php
    rep #$30
.a16
.i16
    pha
    phx
    lda #0
    sta.l SourceVisual_LegacyCgramDrops
    sta.l SourceRom_StagingMagic
    sta.l SourcePending_KnownClear
    sta.l SourcePending_SawPending
    jsr SVActor_Init
    ldx #0
SourceVisual_CompletedInit__clear:
.a16
.i16
    sta.l SourceVisual_CompletedValid,x
    inx
    inx
    cpx #32
    bcc SourceVisual_CompletedInit__clear
    lda #$C04D
    sta.l SourceVisual_CompletedMagic
    lda #1
    sta.l SourceVisual_CompletedRetire
    sta.l SourceVisual_CompletedAwait
    ; An empty first packet must still establish the retirement boundary.
    ; Request the ordinary queued full upload; never write hardware here.
    sta.l Oam_NeedFullUpload
    plx
    pla
    plp
    rtl

SourceVisual_CompletedEnabled:
.a16
.i16
    lda.l SourceVisual_CompletedMagic
    cmp #$C04D
    bne SourceVisual_CompletedEnabled__no
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    bne SourceVisual_CompletedEnabled__no
    sec
    rts
SourceVisual_CompletedEnabled__no:
.a16
.i16
    clc
    rts

; S-CPU observer only. Oam_UploadFlag is cleared AFTER the NMI queue drain.
; Also inspect active OAM queue rows so a skipped/partial drain cannot retire
; a generation. No PPU writes, clocks, forced clears or ownership bypasses.
SourceVisual_CompletedObserve:
    rep #$31
.a16
.i16
    jsr SourceVisual_CompletedEnabled
    bcs SourceVisual_CompletedObserve__enabled
    rts
SourceVisual_CompletedObserve__enabled:
.a16
.i16
    lda.l SourceVisual_CompletedPending
    bne SourceVisual_CompletedObserve__pending
    brl SourceVisual_CompletedObserve__identity
SourceVisual_CompletedObserve__pending:
.a16
.i16
    lda.l Oam_UploadFlag
    beq SourceVisual_CompletedObserve__drained
    brl SourceVisual_CompletedObserve__identity
SourceVisual_CompletedObserve__drained:
.a16
.i16
    ldx #0
SourceVisual_CompletedObserve__queue:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$005F
    cmp #(DMA_OPT_ACTIVE | DMA_TYPE_OAM)
    bne SourceVisual_CompletedObserve__queue_next
    brl SourceVisual_CompletedObserve__identity
SourceVisual_CompletedObserve__queue_next:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourceVisual_CompletedObserve__queue
    jsr SVActor_Drained
    lda.l SourceVisual_CompletedCommitRetire
    beq SourceVisual_CompletedObserve__old_only
    lda #$003F
    bra SourceVisual_CompletedObserve__mask
SourceVisual_CompletedObserve__old_only:
.a16
.i16
    lda #$007F
SourceVisual_CompletedObserve__mask:
.a16
.i16
    sta.l SourceVisual_CompletedNewOwners
    ldx #0
SourceVisual_CompletedObserve__blocks:
    sep #$20
.a8
    lda.l SourceVisual_BlockCache+4,x
    and.l SourceVisual_CompletedNewOwners
    sta.l SourceVisual_BlockCache+4,x
    rep #$31
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #512
    bcc SourceVisual_CompletedObserve__blocks
    ldx #0
SourceVisual_CompletedObserve__palettes:
    sep #$20
.a8
    lda.l SourceVisual_PaletteCache+4,x
    and.l SourceVisual_CompletedNewOwners
    sta.l SourceVisual_PaletteCache+4,x
    rep #$31
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourceVisual_CompletedObserve__palettes
    lda #0
    sta.l SourceVisual_CompletedPending
    sta.l SourceVisual_CompletedCommitRetire
    lda.l SourceVisual_CompletedAcks
    inc a
    sta.l SourceVisual_CompletedAcks
SourceVisual_CompletedObserve__identity:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    beq SourceVisual_CompletedObserve__done
    lda.l Game_StageIndex
    cmp.l SourceVisual_CompletedStage
    bne SourceVisual_CompletedObserve__retire
    lda.l $7E0000+PlayerEntity_DpBase+CHAR_ROSTER_INDEX
    and #$00FF
    cmp.l SourceVisual_CompletedRoster
    beq SourceVisual_CompletedObserve__done
SourceVisual_CompletedObserve__retire:
.a16
.i16
    lda #0
    sta.l SourceVisual_CompletedValid
    lda #1
    sta.l SourceVisual_CompletedRetire
SourceVisual_CompletedObserve__done:
.a16
.i16
    rts

; A frame that intersects the viewport admits the COMPLETE P1 source packet.
; Otherwise motion can expose a never-loaded piece of the completed pose.
; NPC admission remains viewport-bounded; wholly offscreen actors still retire.
SourceVisual_ResidencyPiece:
.a16
.i16
    jsr SourceVisual_CompletedEnabled
    bcc SourceVisual_ResidencyPiece__viewport
    sec
    rts
SourceVisual_ResidencyPiece__viewport:
.a16
.i16
    jmp SourceVisual_ViewportPiece

SourceVisual_CompletedCanPublish:
.a16
.i16
    tdc
    cmp #$0A00
    beq SourceVisual_CompletedCanPublish__p1
    jmp SVActor_CanPublish
SourceVisual_CompletedCanPublish__p1:
.a16
.i16
    jsr SourceVisual_CompletedEnabled
    bcc SourceVisual_CompletedCanPublish__yes
    lda.l SourceVisual_CompletedAwait
    ora.l SourceVisual_CompletedPending
    ora.l SourceVisual_CompletedRetire
    bne SourceVisual_CompletedCanPublish__no
SourceVisual_CompletedCanPublish__yes:
.a16
.i16
    sec
    rts
SourceVisual_CompletedCanPublish__no:
.a16
.i16
    clc
    rts

; Called only after the desired packet has emitted successfully. Rotate pins
; before copying metadata. CanPublish guarantees the prior generation retired.
SourceVisual_CompletedCapture:
.a16
.i16
    tdc
    cmp #$0A00
    beq SourceVisual_CompletedCapture__p1
    jmp SVActor_Capture
SourceVisual_CompletedCapture__p1:
.a16
.i16
    jsr SourceVisual_CompletedEnabled
    bcs SourceVisual_CompletedCapture__enabled
    rts
SourceVisual_CompletedCapture__enabled:
.a16
.i16
    ; The old hardware picture stays protected by its retiring pins. Its
    ; mutable metadata is not a completed packet during this replacement.
    lda #0
    sta.l SourceVisual_CompletedValid
    ldx #0
SourceVisual_CompletedCapture__blocks:
    sep #$20
.a8
    lda.l SourceVisual_BlockCache+4,x
    jsr SourceVisual_CompletedRotateOwners
    sta.l SourceVisual_BlockCache+4,x
    rep #$31
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #512
    bcc SourceVisual_CompletedCapture__blocks
    ldx #0
SourceVisual_CompletedCapture__palettes:
    sep #$20
.a8
    lda.l SourceVisual_PaletteCache+4,x
    jsr SourceVisual_CompletedRotateOwners
    sta.l SourceVisual_PaletteCache+4,x
    rep #$31
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourceVisual_CompletedCapture__palettes
    ldx #0
SourceVisual_CompletedCapture__entry:
.a16
.i16
    lda.l SourceVisual_EntryScratch,x
    sta.l SourceVisual_CompletedEntry,x
    inx
    inx
    cpx #24
    bcc SourceVisual_CompletedCapture__entry
    ldx #0
SourceVisual_CompletedCapture__lease:
.a16
.i16
    lda.l SourceVisual_State,x
    sta.l SourceVisual_CompletedLease,x
    inx
    inx
    cpx #32
    bcc SourceVisual_CompletedCapture__lease
    lda.l SourceVisual_PieceCount
    asl a
    asl a
    asl a
    asl a
    sta.l SourceVisual_CompletedMainBytes
    beq SourceVisual_CompletedCapture__pieces_done
    ldx #0
SourceVisual_CompletedCapture__pieces:
.a16
.i16
    lda.l SourceVisual_PieceTable,x
    sta.l SourceVisual_CompletedPieces,x
    inx
    inx
    txa
    cmp.l SourceVisual_CompletedMainBytes
    bcc SourceVisual_CompletedCapture__pieces
SourceVisual_CompletedCapture__pieces_done:
.a16
.i16
    sep #$20
.a8
    ldx #0
SourceVisual_CompletedCapture__map:
.a8
.i16
    lda.l SourceVisual_ActorPieceMap,x
    sta.l SourceVisual_CompletedMap,x
    inx
    cpx #65
    bcc SourceVisual_CompletedCapture__map
    rep #$31
.a16
.i16
    lda.l Game_StageIndex
    sta.l SourceVisual_CompletedStage
    lda CHAR_ROSTER_INDEX
    and #$00FF
    sta.l SourceVisual_CompletedRoster
    lda #1
    sta.l SourceVisual_CompletedAwait
    sep #$20
.a8
    sta.l SourceVisual_CompletedLease+28
    rep #$31
.a16
.i16
    lda.l SourceVisual_CompletedCaptures
    inc a
    sta.l SourceVisual_CompletedCaptures
    ; Publish the flag last, after entry, lease, geometry and generation.
    lda #1
    sta.l SourceVisual_CompletedValid
    rts

; A8, X is preserved. Current actor-0 resources become bit6, old bit6 -> bit7.
SourceVisual_CompletedRotateOwners:
.a8
.i16
    sta.l SourceVisual_CompletedOwners
    and #$3F
    sta.l SourceVisual_CompletedNewOwners
    lda.l SourceVisual_CompletedOwners
    and #$40
    asl a
    ora.l SourceVisual_CompletedNewOwners
    sta.l SourceVisual_CompletedNewOwners
    lda.l SourceVisual_CompletedOwners
    and #1
    beq SourceVisual_CompletedRotateOwners__done
    lda.l SourceVisual_CompletedNewOwners
    ora #$40
    sta.l SourceVisual_CompletedNewOwners
SourceVisual_CompletedRotateOwners__done:
.a8
.i16
    lda.l SourceVisual_CompletedNewOwners
    rts

; Fail closed unless all completed pieces retain their exact resident blocks
; and palette identities. Full P1 admission makes this independent of movement.
SourceVisual_CompletedValidate:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+12
    and #$00FF
    cmp #66
    bcs SourceVisual_CompletedValidate__bad
    sta.l SourceVisual_CompletedCount
    lda #0
    sta.l SourceVisual_CompletedIndex
SourceVisual_CompletedValidate__piece:
.a16
.i16
    lda.l SourceVisual_CompletedIndex
    cmp.l SourceVisual_CompletedCount
    bcc SourceVisual_CompletedValidate__have_piece
    sec
    rts
SourceVisual_CompletedValidate__have_piece:
.a16
.i16
    tax
    lda.l SourceVisual_CompletedMap,x
    and #$00FF
    cmp #64
    bcs SourceVisual_CompletedValidate__bad
    asl a
    asl a
    asl a
    tay
    lda.l SourceVisual_CompletedIndex
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_CompletedPieces+12,x
    sta.l SourceVisual_CompletedOwners
    tya
    tax
    lda.l SourceVisual_BlockCache+2,x
    cmp #2
    bne SourceVisual_CompletedValidate__bad
    lda.l SourceVisual_BlockCache,x
    cmp.l SourceVisual_CompletedOwners
    bne SourceVisual_CompletedValidate__bad
    lda.l SourceVisual_BlockCache+4,x
    and #$0040
    beq SourceVisual_CompletedValidate__bad
    brl SourceVisual_CompletedValidate__palette
SourceVisual_CompletedValidate__bad:
.a16
.i16
    clc
    rts
SourceVisual_CompletedValidate__palette:
.a16
.i16
    lda.l SourceVisual_CompletedIndex
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_CompletedPieces+10,x
    sta.l SourceVisual_CompletedOwners
    lda.l SourceVisual_CompletedPieces+8,x
    and #$00FF
    cmp #8
    bcs SourceVisual_CompletedValidate__bad
    tax
    lda.l SourceVisual_CompletedLease+16,x
    and #$00FF
    beq SourceVisual_CompletedValidate__bad
    dec a
    cmp #8
    bcs SourceVisual_CompletedValidate__bad
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_PaletteCache,x
    cmp.l SourceVisual_CompletedOwners
    bne SourceVisual_CompletedValidate__bad
    lda.l SourceVisual_PaletteCache+3,x
    and #$00FF
    cmp #1
    bne SourceVisual_CompletedValidate__bad
    lda.l SourceVisual_PaletteCache+4,x
    and #$0040
    beq SourceVisual_CompletedValidate__bad
    lda.l SourceVisual_CompletedIndex
    inc a
    sta.l SourceVisual_CompletedIndex
    brl SourceVisual_CompletedValidate__piece

; Render the last completed SOURCE packet at the current accepted position.
; Do not mark the desired transaction published. Entry/lease globals are
; restored, so same-key lookup never mistakes cached metadata for desired data.
SourceVisual_EmitCompleted:
    rep #$31
.a16
.i16
    tdc
    cmp #$0A00
    beq SourceVisual_EmitCompleted__p1
    jmp SVActor_Emit
SourceVisual_EmitCompleted__p1:
.a16
.i16
    lda.l SourceVisual_ServiceOnly
    bne SourceVisual_EmitCompleted__no_near
    ; Hold only while a supported replacement waits for resources/commit.
    ; Unknown keys, oversized packets and malformed palettes stay fail-closed.
    lda.l SourceVisual_Error
    and #$00FF
    cmp #$27
    beq SourceVisual_EmitCompleted__resource_wait
    cmp #$24
    bne SourceVisual_EmitCompleted__no_near
SourceVisual_EmitCompleted__resource_wait:
.a16
.i16
    jsr SourceVisual_CompletedEnabled
    bcc SourceVisual_EmitCompleted__no_near
    lda.l SourceVisual_CompletedValid
    beq SourceVisual_EmitCompleted__no_near
    jsr SourceVisual_CompletedValidate
    bcs SourceVisual_EmitCompleted__begin
SourceVisual_EmitCompleted__no_near:
.a16
.i16
    clc
    rts
SourceVisual_EmitCompleted__begin:
.a16
.i16
    lda.l SourceVisual_Record
    pha
    lda.l SourceVisual_BaseTile
    pha
    lda.l SourceVisual_PieceCount
    pha
    ldx #0
SourceVisual_EmitCompleted__entry:
.a16
.i16
    lda.l SourceVisual_EntryScratch,x
    sta.l SourceVisual_CompletedSavedEntry,x
    lda.l SourceVisual_CompletedEntry,x
    sta.l SourceVisual_EntryScratch,x
    inx
    inx
    cpx #24
    bcc SourceVisual_EmitCompleted__entry
    lda.l SourceVisual_CompletedCount
    asl a
    asl a
    asl a
    asl a
    sta.l SourceVisual_CompletedMainBytes
    beq SourceVisual_EmitCompleted__pieces_done
    ldx #0
SourceVisual_EmitCompleted__pieces:
.a16
.i16
    lda.l SourceVisual_CompletedPieces,x
    sta.l SourceVisual_PieceTable,x
    inx
    inx
    txa
    cmp.l SourceVisual_CompletedMainBytes
    bcc SourceVisual_EmitCompleted__pieces
SourceVisual_EmitCompleted__pieces_done:
.a16
.i16
    lda #(SourceVisual_CompletedLease-SourceVisual_State)
    sta.l SourceVisual_Record
    lda.l SourceVisual_CompletedLease+8
    sta.l SourceVisual_BaseTile
    lda.l SourceVisual_CompletedCount
    sta.l SourceVisual_PieceCount
    jsr SourceVisual_Emit
    lda #0
    rol a
    sta.l SourceVisual_CompletedResult
    ldx #0
SourceVisual_EmitCompleted__restore_entry:
.a16
.i16
    lda.l SourceVisual_CompletedSavedEntry,x
    sta.l SourceVisual_EntryScratch,x
    inx
    inx
    cpx #24
    bcc SourceVisual_EmitCompleted__restore_entry
    pla
    sta.l SourceVisual_PieceCount
    pla
    sta.l SourceVisual_BaseTile
    pla
    sta.l SourceVisual_Record
    lda.l SourceVisual_CompletedResult
    beq SourceVisual_EmitCompleted__no
    lda.l SourceVisual_CompletedFallbacks
    inc a
    sta.l SourceVisual_CompletedFallbacks
    sec
    rts
SourceVisual_EmitCompleted__no:
.a16
.i16
    clc
    rts

; Compiler-owned OAM submit seam. Hold the existing NMI busy gate only across
; OAM enqueue and StageWater's matching table publication, never across loading.
SourceVisual_CompletedOamBegin:
    php
    rep #$30
.a16
.i16
    pha
    jsr SourceVisual_CompletedEnabled
    bcc SourceVisual_CompletedOamBegin__done
    lda.l SourceVisual_CompletedEarly
    beq SourceVisual_CompletedOamBegin__acquire
    pla
    plp
    rtl
SourceVisual_CompletedOamBegin__acquire:
.a16
.i16
    sep #$20
.a8
    lda.l Nmi_FrameBusy
    sta.l SourceVisual_CompletedSavedBusy
    lda #1
    sta.l SourceVisual_CompletedHeld
    sta.l Nmi_FrameBusy
    rep #$30
.a16
.i16
SourceVisual_CompletedOamBegin__done:
.a16
.i16
    pla
    plp
    jml StageWater_OamBegin

SourceVisual_CompletedOamEnd:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    ; This seam also runs in intro/title/selection, before BeginResolve.
    ; Never inspect uninitialized cache control or restore a spurious lease.
    jsr SourceVisual_CompletedEnabled
    bcs SourceVisual_CompletedOamEnd__enabled
    jsl StageWater_End
    brl SourceVisual_CompletedOamEnd__done
SourceVisual_CompletedOamEnd__enabled:
.a16
.i16
    lda.l SourceVisual_CompletedEarly
    beq SourceVisual_CompletedOamEnd__not_early
    brl SourceVisual_CompletedOamEnd__done
SourceVisual_CompletedOamEnd__not_early:
.a16
.i16
    ; Reused pictures also need their complete private high table preserved.
    jsl SourcePacket_CancelFrameHi
    lda.l SourceVisual_CompletedHeld
    and #$00FF
    beq SourceVisual_CompletedOamEnd__water_near
    lda.l SourceVisual_CompletedAwait
    ora.l SourceVisual_CompletedRetire
    beq SourceVisual_CompletedOamEnd__water_near
    lda.l Oam_UploadFlag
    bne SourceVisual_CompletedOamEnd__start_queue
    brl SourceVisual_CompletedOamEnd__retry
SourceVisual_CompletedOamEnd__water_near:
.a16
.i16
    brl SourceVisual_CompletedOamEnd__water
SourceVisual_CompletedOamEnd__start_queue:
.a16
.i16
    lda #0
    sta.l SourceVisual_CompletedQueueMask
    ldx #0
SourceVisual_CompletedOamEnd__queue:
.a16
.i16
    ; A single exact private544-byte row includes both OAM tables.
    ; Other descriptors retain the original two-row identity contract.
    jsr SourcePacket_IsQueueRow
    bcc SourceVisual_CompletedOamEnd__legacy_queue
    lda.l SourceVisual_CompletedQueueMask
    ora #3
    sta.l SourceVisual_CompletedQueueMask
    brl SourceVisual_CompletedOamEnd__next
SourceVisual_CompletedOamEnd__legacy_queue:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$005F
    cmp #(DMA_OPT_ACTIVE | DMA_TYPE_OAM)
    bne SourceVisual_CompletedOamEnd__next
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$007E
    bne SourceVisual_CompletedOamEnd__next
    lda.l DmaQueue+5,x
    cmp #$5100
    beq SourceVisual_CompletedOamEnd__main
    cmp #$5300
    bne SourceVisual_CompletedOamEnd__next
    lda.l DmaQueue+2,x
    cmp #$0100
    bne SourceVisual_CompletedOamEnd__next
    lda.l SourceVisual_CompletedQueueMask
    ora #2
    sta.l SourceVisual_CompletedQueueMask
    bra SourceVisual_CompletedOamEnd__next
SourceVisual_CompletedOamEnd__main:
.a16
.i16
    lda.l DmaQueue+2,x
    bne SourceVisual_CompletedOamEnd__next
    lda.l SourceVisual_CompletedQueueMask
    ora #1
    sta.l SourceVisual_CompletedQueueMask
SourceVisual_CompletedOamEnd__next:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourceVisual_CompletedOamEnd__queue
    lda.l SourceVisual_CompletedQueueMask
    cmp #3
    bne SourceVisual_CompletedOamEnd__retry
    jsr SVActor_Queued
    lda #1
    sta.l SourceVisual_CompletedPending
    lda.l SourceVisual_CompletedRetire
    sta.l SourceVisual_CompletedCommitRetire
    lda #0
    sta.l SourceVisual_CompletedAwait
    sta.l SourceVisual_CompletedRetire
    bra SourceVisual_CompletedOamEnd__water
SourceVisual_CompletedOamEnd__retry:
.a16
.i16
    ; Main or high OAM may have lacked a queue slot. Retry both through
    ; Core_Oam_Play, even when the next scene has zero visible sprites.
    lda #1
    sta.l Oam_NeedFullUpload
SourceVisual_CompletedOamEnd__water:
.a16
.i16
    jsl StageWater_End
    rep #$30
.a16
.i16
    lda.l SourceVisual_CompletedHeld
    and #$00FF
    beq SourceVisual_CompletedOamEnd__done
    lda #0
    sta.l SourceVisual_CompletedHeld
    sep #$20
.a8
    lda.l SourceVisual_CompletedSavedBusy
    sta.l Nmi_FrameBusy
    rep #$30
.a16
.i16
SourceVisual_CompletedOamEnd__done:
.a16
.i16
    ply
    plx
    pla
    plp
    rtl

; A normal source packet needs both OAM transfers or neither. This runs
; under CompletedOamBegin's short gate. NMI only drains, never produces;
; no queue producer can consume the admitted pair before Core_Oam_Play.
; Legacy/intro calls retain the original Core_Oam_Play_Long path.
SourceVisual_CompletedSubmit:
    rep #$30
.a16
.i16
    jsr SourceVisual_CompletedEnabled
    bcs SourceVisual_CompletedSubmit__enabled
    jml Core_Oam_Play_Long
SourceVisual_CompletedSubmit__enabled:
.a16
.i16
    php
    pha
    phx
    phy
    lda.l SourceVisual_CompletedEarly
    beq SourceVisual_CompletedSubmit__not_early
    brl SourceVisual_CompletedSubmit__done
SourceVisual_CompletedSubmit__not_early:
.a16
.i16
    lda.l SourceVisual_CompletedAwait
    ora.l SourceVisual_CompletedRetire
    beq SourceVisual_CompletedSubmit__slots
    lda #1
    sta.l Oam_NeedFullUpload
SourceVisual_CompletedSubmit__slots:
.a16
.i16
    lda #0
    sta.l SourceVisual_CompletedQueueMask
    ldx #0
SourceVisual_CompletedSubmit__scan:
.a16
.i16
    lda.l DmaQueue+4,x
    and #$0040
    bne SourceVisual_CompletedSubmit__next
    lda.l SourceVisual_CompletedQueueMask
    inc a
    sta.l SourceVisual_CompletedQueueMask
SourceVisual_CompletedSubmit__next:
.a16
.i16
    txa
    clc
    adc #8
    tax
    cpx #64
    bcc SourceVisual_CompletedSubmit__scan
    lda.l SourceVisual_CompletedQueueMask
    cmp #2
    bcc SourceVisual_CompletedSubmit__retry
    lda.l Oam_NeedFullUpload
    beq SourceVisual_CompletedSubmit__partial_size
    lda #544
    bra SourceVisual_CompletedSubmit__budget
SourceVisual_CompletedSubmit__partial_size:
.a16
.i16
    lda.l Oam_CurrentSlot
    cmp.l Oam_HighWaterSlot
    bcs SourceVisual_CompletedSubmit__main_size
    lda.l Oam_HighWaterSlot
SourceVisual_CompletedSubmit__main_size:
.a16
.i16
    cmp #513
    bcs SourceVisual_CompletedSubmit__retry
    sta.l SourceVisual_CompletedMainBytes
    clc
    adc #15
    lsr a
    lsr a
    lsr a
    lsr a
    clc
    adc.l SourceVisual_CompletedMainBytes
SourceVisual_CompletedSubmit__budget:
.a16
.i16
    clc
    adc.l DmaQueue_BudgetTotal
    cmp #DMA_TRANSFER_MAX_BYTES
    bcs SourceVisual_CompletedSubmit__retry
    jsl Core_Oam_Play_Long
    bra SourceVisual_CompletedSubmit__done
SourceVisual_CompletedSubmit__retry:
.a16
.i16
    lda #1
    sta.l Oam_NeedFullUpload
SourceVisual_CompletedSubmit__done:
.a16
.i16
    ply
    plx
    pla
    plp
    rtl

; Same-entry reuse never acknowledges a new transaction. It requires an
; already published P1 lease, exact completed entry identity, and the full
; block/palette state+ID+owner validation. SourceInput/NMI owns no resources.
SourceVisual_ReuseCompleted:
.a16
.i16
    tdc
    cmp #$0A00
    beq SourceVisual_ReuseCompleted__p1
    jmp SVActor_Reuse
SourceVisual_ReuseCompleted__p1:
.a16
.i16
    jsr SourceVisual_CompletedEnabled
    bcc SourceVisual_ReuseCompleted__no
    lda.l SourceVisual_CompletedValid
    beq SourceVisual_ReuseCompleted__no
    lda.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+28,x
    and #$00FF
    beq SourceVisual_ReuseCompleted__no
    lda.l SourceVisual_State,x
    cmp.l SourceVisual_CompletedLease
    bne SourceVisual_ReuseCompleted__no
    lda.l SourceVisual_EntryIndexSaved
    cmp.l SourceVisual_CompletedLease
    bne SourceVisual_ReuseCompleted__no
    lda.l SourceVisual_ServiceOnly
    beq SourceVisual_ReuseCompleted__emit
    ; Validate without emitting, loading, rotating pins or marking published.
    jsr SourceVisual_CompletedValidate
    rts
SourceVisual_ReuseCompleted__emit:
.a16
.i16
    ; Eligibility has been established by the same-entry checks above.
    ; The common emitter still validates every immutable hardware resource.
    jmp SourceVisual_EmitCompleted__resource_wait
SourceVisual_ReuseCompleted__no:
.a16
.i16
    clc
    rts

; A16/I16, X is the actual queue-row offset. Reject ONLY the verified native
; actor palette staging writer while original-BOR's source host is active.
; Its fixed actor-slot palette ignores the content-addressed palette leases.
; Compiler-owned $7E4900 staging, BG palettes and other campaigns pass through
; the unchanged hardware transfer. No source transfer is acknowledged/skipped.
SourceVisual_AllowCgramRequest:
    php
    rep #$30
.a16
.i16
    pha
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    bne SourceVisual_AllowCgramRequest__allow
    lda.l SourceInput_Magic
    cmp #$1A60
    bne SourceVisual_AllowCgramRequest__allow
    lda.l $7E1760
    cmp #1
    bne SourceVisual_AllowCgramRequest__allow
    lda.l DmaQueue+7,x
    and #$00FF
    cmp #$007E
    bne SourceVisual_AllowCgramRequest__allow
    lda.l DmaQueue+5,x
    cmp #(AnimPaletteStaging & $FFFF)
    bne SourceVisual_AllowCgramRequest__allow
    lda.l DmaQueue+2,x
    cmp #$0100
    bcc SourceVisual_AllowCgramRequest__allow
    cmp #$0200
    bcs SourceVisual_AllowCgramRequest__allow
    lda.l SourceVisual_LegacyCgramDrops
    inc a
    sta.l SourceVisual_LegacyCgramDrops
    pla
    plp
    clc
    rtl
SourceVisual_AllowCgramRequest__allow:
.a16
.i16
    pla
    plp
    sec
    rtl

; Begin exactly one presentation transaction per main pass. Historical and
; non-source paths retain their original StageWater begin/end placement.
SourceVisual_BeginPresentationFrame:
    php
    rep #$30
.a16
.i16
    pha
    jsr SVActor_Observe
    ; Reset before actor emission, never at the later OAM submission seam.
    jsl SourcePacket_FrameBegin
    lda #0
    sta.l SourceVisual_CompletedEarly
    pla
    plp
    jml StageWater_Begin

; Actor resources and OAM are complete, and Core_Screen_Play has accepted the
; camera. Publish before potentially multi-field BG streaming. Nothing below
; this seam emits actor OAM. The same atomic pair and retirement checks run;
; the old late sites become no-ops only after this full transaction returns.
SourceVisual_EarlySubmit:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    jsr SourceVisual_CompletedEnabled
    bcc SourceVisual_EarlySubmit__done
    lda.l SourceInput_Magic
    cmp #$1A60
    bne SourceVisual_EarlySubmit__done
    jsl SourceVisual_CompletedOamBegin
    jsl SourceVisual_CompletedSubmit
    jsl SourceVisual_CompletedOamEnd
    lda #1
    sta.l SourceVisual_CompletedEarly
    jsr SourceVisual_ServiceNpcsAfterSubmit
SourceVisual_EarlySubmit__done:
.a16
.i16
    ply
    plx
    pla
    plp
    rtl

; The OAM transaction is already queued. Service at most six live actors,
; preserving the depth-sorted compositor as the only OAM producer.
SourceRom_NpcMediaCursor = $7E46D0 ; SCPU-only, validated before use
; Both players remain first. Spread NPC media preparation across main passes;
; every actor's simulation and completed-pose rendering remain in the compositor.
; Private SCPU scheduler state; validated before use. No NMI/worker readers.
SourceRom_MediaPhase = $7E46D2
SourceRom_PlayerMediaCursor = $7E46D4
SourceRom_MediaCandidate = $7E46D6
SourceRom_MediaP1Class = $7E46D8
SourceRom_MediaP2Class = $7E46DA

; One preparation job per submitted picture. A new P1 jump wins player
; admission; other new roles precede redundant same-role work. Every third
; preparation turn remains available to NPCs, even during sustained input.
SourceVisual_ServiceNpcsAfterSubmit:
.a16
.i16
    phd
    lda.l SourceRom_MediaPhase
    cmp #3
    bcc SourceVisual_ServiceNpcsAfterSubmit__phase_valid
    lda #0
    sta.l SourceRom_MediaPhase
SourceVisual_ServiceNpcsAfterSubmit__phase_valid:
.a16
.i16
    lda #0
    jsr SourceVisual_PlayerMediaClass
    sta.l SourceRom_MediaP1Class
    lda #1
    jsr SourceVisual_PlayerMediaClass
    sta.l SourceRom_MediaP2Class
    jsr SourceVisual_ServiceFirstNpcBeforeRepeat
    bcc SourceVisual_ServiceNpcsAfterSubmit__normal_player_priority
    lda.l SourceRom_MediaPhase
    inc a
    cmp #3
    bcc SourceVisual_ServiceNpcsAfterSubmit__first_phase_store
    lda #0
SourceVisual_ServiceNpcsAfterSubmit__first_phase_store:
.a16
.i16
    sta.l SourceRom_MediaPhase
    brl SourceVisual_ServiceNpcsAfterSubmit__done
SourceVisual_ServiceNpcsAfterSubmit__normal_player_priority:
.a16
.i16
    lda.l SourceRom_MediaPhase
    cmp #2
    bne SourceVisual_ServiceNpcsAfterSubmit__players_check
    brl SourceVisual_ServiceNpcsAfterSubmit__npc_turn
SourceVisual_ServiceNpcsAfterSubmit__players_check:
.a16
.i16
    lda.l SourceRom_MediaP1Class
    cmp #3
    bne SourceVisual_ServiceNpcsAfterSubmit__p2_jump
    lda #0
    brl SourceVisual_ServiceNpcsAfterSubmit__choose_player
SourceVisual_ServiceNpcsAfterSubmit__p2_jump:
.a16
.i16
    lda.l SourceRom_MediaP2Class
    cmp #3
    bne SourceVisual_ServiceNpcsAfterSubmit__cursor_valid
    lda #1
    brl SourceVisual_ServiceNpcsAfterSubmit__choose_player
SourceVisual_ServiceNpcsAfterSubmit__cursor_valid:
.a16
.i16
    lda.l SourceRom_PlayerMediaCursor
    cmp #2
    bcc SourceVisual_ServiceNpcsAfterSubmit__cursor_ready
    lda #0
SourceVisual_ServiceNpcsAfterSubmit__cursor_ready:
.a16
.i16
    sta.l SourceRom_MediaCandidate
    asl a
    tax
    lda.l SourceRom_MediaP1Class,x
    cmp #2
    bcs SourceVisual_ServiceNpcsAfterSubmit__choose_candidate
    lda.l SourceRom_MediaCandidate
    eor #1
    asl a
    tax
    lda.l SourceRom_MediaP1Class,x
    cmp #2
    bcs SourceVisual_ServiceNpcsAfterSubmit__choose_other
    lda.l SourceRom_MediaCandidate
    asl a
    tax
    lda.l SourceRom_MediaP1Class,x
    bne SourceVisual_ServiceNpcsAfterSubmit__choose_candidate
    lda.l SourceRom_MediaCandidate
    eor #1
    asl a
    tax
    lda.l SourceRom_MediaP1Class,x
    bne SourceVisual_ServiceNpcsAfterSubmit__choose_other
    bra SourceVisual_ServiceNpcsAfterSubmit__npc_turn
SourceVisual_ServiceNpcsAfterSubmit__choose_other:
.a16
.i16
    lda.l SourceRom_MediaCandidate
    eor #1
    bra SourceVisual_ServiceNpcsAfterSubmit__choose_player
SourceVisual_ServiceNpcsAfterSubmit__choose_candidate:
.a16
.i16
    lda.l SourceRom_MediaCandidate
SourceVisual_ServiceNpcsAfterSubmit__choose_player:
.a16
.i16
    sta.l SourceRom_MediaCandidate
    eor #1
    sta.l SourceRom_PlayerMediaCursor
    lda.l SourceRom_MediaPhase
    inc a
    sta.l SourceRom_MediaPhase
    lda.l SourceRom_MediaCandidate
    asl a
    tax
    lda.l SVActor_LoadDps,x
    tcd
    jsl SourceVisual_ServiceCurrent
    brl SourceVisual_ServiceNpcsAfterSubmit__done
SourceVisual_ServiceNpcsAfterSubmit__npc_turn:
.a16
.i16
    lda #0
    sta.l SourceRom_MediaPhase
    lda.l SourceRom_NpcMediaCursor
    cmp #$0B0A
    beq SourceVisual_ServiceNpcsAfterSubmit__cursor
    cmp #$0B8F
    beq SourceVisual_ServiceNpcsAfterSubmit__cursor
    cmp #$0C14
    beq SourceVisual_ServiceNpcsAfterSubmit__cursor
    cmp #$0C99
    beq SourceVisual_ServiceNpcsAfterSubmit__cursor
    lda #$0B0A
SourceVisual_ServiceNpcsAfterSubmit__cursor:
.a16
.i16
    tax
    ldy #4
SourceVisual_ServiceNpcsAfterSubmit__npc:
.a16
.i16
    txa
    tcd
    clc
    adc #133
    cmp #$0D1E
    bcc SourceVisual_ServiceNpcsAfterSubmit__save_cursor
    lda #$0B0A
SourceVisual_ServiceNpcsAfterSubmit__save_cursor:
.a16
.i16
    sta.l SourceRom_NpcMediaCursor
    lda CHAR_HP
    and #$00FF
    bne SourceVisual_ServiceNpcsAfterSubmit__service
    lda.l SourceRom_NpcMediaCursor
    tax
    dey
    bne SourceVisual_ServiceNpcsAfterSubmit__npc
    bra SourceVisual_ServiceNpcsAfterSubmit__done
SourceVisual_ServiceNpcsAfterSubmit__service:
.a16
.i16
    jsl SourceVisual_ServiceCurrent
SourceVisual_ServiceNpcsAfterSubmit__done:
.a16
.i16
    ldx #$0D1E
    pld
    rts

; A=player index. Return0=no desired work,1=same-role pending,
; 2=first picture/new role,3=new jump. Read accepted state only.
SourceVisual_PlayerMediaClass:
.a16
.i16
    sta.l SourceRom_MediaCandidate
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_State+6,x
    cmp #1
    beq SourceVisual_PlayerMediaClass__pending
    brl SourceVisual_PlayerMediaClass__none
SourceVisual_PlayerMediaClass__pending:
.a16
.i16
    lda.l SourceRom_MediaCandidate
    asl a
    tax
    lda.l SVActor_LoadDps,x
    tax
    lda.l $7E0000+CHAR_HP,x
    and #$00FF
    bne SourceVisual_PlayerMediaClass__alive
    bra SourceVisual_PlayerMediaClass__none
SourceVisual_PlayerMediaClass__alive:
.a16
.i16
    lda.l SourceRom_MediaCandidate
    bne SourceVisual_PlayerMediaClass__p2
    lda.l SourceVisual_CompletedValid
    beq SourceVisual_PlayerMediaClass__first
    lda.l SourceVisual_CompletedEntry+1
    bra SourceVisual_PlayerMediaClass__published
SourceVisual_PlayerMediaClass__p2:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    beq SourceVisual_PlayerMediaClass__first
    lda.l SVActor_Data+1
SourceVisual_PlayerMediaClass__published:
.a16
.i16
    and #$00FF
    pha
    lda.l SourceRom_MediaCandidate
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    pla
    sta.l SourceRom_MediaCandidate
    lda.l SourceVisual_State+30,x
    and #$00FF
    cmp.l SourceRom_MediaCandidate
    bne SourceVisual_PlayerMediaClass__new_role
    lda #1
    rts
SourceVisual_PlayerMediaClass__first:
.a16
.i16
    lda.l SourceRom_MediaCandidate
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_State+30,x
    and #$00FF
SourceVisual_PlayerMediaClass__new_role:
.a16
.i16
    cmp #7
    beq SourceVisual_PlayerMediaClass__jump
    lda #2
    rts
SourceVisual_PlayerMediaClass__jump:
.a16
.i16
    lda #3
    rts
SourceVisual_PlayerMediaClass__none:
.a16
.i16
    lda #0
    rts


; Scoped caller already selected both player urgency classes. A first NPC
; picture outranks only class0/1 (idle/repeated animation), preserving new
; player roles/jumps and the existing one-job-per-submission bound.
SourceVisual_ServiceFirstNpcBeforeRepeat:
.a16
.i16
    ; Preserve the reserved NPC third turn, including during player urgency.
    lda.l SourceRom_MediaPhase
    cmp #2
    beq SourceVisual_ServiceFirstNpcBeforeRepeat__owner
    lda.l SourceRom_MediaP1Class
    cmp #2
    bcs SourceVisual_ServiceFirstNpcBeforeRepeat__no_near
    lda.l SourceRom_MediaP2Class
    cmp #2
    bcs SourceVisual_ServiceFirstNpcBeforeRepeat__no_near
SourceVisual_ServiceFirstNpcBeforeRepeat__owner:
.a16
.i16
    lda.l SVActor_LoadOwner
    cmp #3
    bcc SourceVisual_ServiceFirstNpcBeforeRepeat__scan
    cmp #7
    bcs SourceVisual_ServiceFirstNpcBeforeRepeat__scan
    dec a
    dec a
    asl a
    tax
    lda.l SVActor_Bases,x
    tax
    lda.l SVActor_Data+SVActor_Valid,x
    cmp #1
    beq SourceVisual_ServiceFirstNpcBeforeRepeat__scan
    jsr SVActor_ServiceOwner
    sec
    rts
SourceVisual_ServiceFirstNpcBeforeRepeat__no_near:
.a16
.i16
    clc
    rts
SourceVisual_ServiceFirstNpcBeforeRepeat__scan:
.a16
.i16
    ldy #2
SourceVisual_ServiceFirstNpcBeforeRepeat__candidate:
.a16
.i16
    tya
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    ; Only an in-viewport, supported lease selected by the compositor is
    ; eligible. Offscreen/retired/unsupported actors have no pending lease.
    lda.l SourceVisual_State+6,x
    cmp #1
    bne SourceVisual_ServiceFirstNpcBeforeRepeat__next
    lda.l SourceVisual_State+28,x
    and #$00FF
    bne SourceVisual_ServiceFirstNpcBeforeRepeat__next
    tya
    asl a
    tax
    lda.l SVActor_LoadBits,x
    and.l SourceVisual_RetireMask
    and #$00FF
    bne SourceVisual_ServiceFirstNpcBeforeRepeat__next
    lda.l SVActor_LoadDps,x
    tax
    lda.l $7E0000+CHAR_HP,x
    and #$00FF
    beq SourceVisual_ServiceFirstNpcBeforeRepeat__next
    txa
    sec
    sbc #$0A00
    tax
    lda.l SourceVisual_Sa1OwnerPolicy,x
    and #$00FF
    cmp #2
    bne SourceVisual_ServiceFirstNpcBeforeRepeat__next
    tya
    dec a
    asl a
    tax
    lda.l SVActor_Bases,x
    tax
    lda.l SVActor_Data+SVActor_Valid,x
    cmp #1
    beq SourceVisual_ServiceFirstNpcBeforeRepeat__next
    tya
    asl a
    tax
    lda.l SVActor_LoadDps,x
    tcd
    jsl SourceVisual_ServiceCurrent
    sec
    rts
SourceVisual_ServiceFirstNpcBeforeRepeat__next:
.a16
.i16
    iny
    cpy #6
    bcs SourceVisual_ServiceFirstNpcBeforeRepeat__no
    brl SourceVisual_ServiceFirstNpcBeforeRepeat__candidate
SourceVisual_ServiceFirstNpcBeforeRepeat__no:
.a16
.i16
    clc
    rts
