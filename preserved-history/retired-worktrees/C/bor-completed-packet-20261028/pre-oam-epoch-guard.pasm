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
    lda.l SourceVisual_ActorSlot
    bne SourceVisual_ResidencyPiece__viewport
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
    bne SourceVisual_CompletedCanPublish__yes
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
    rts
SourceVisual_CompletedCapture__p1:
.a16
.i16
    jsr SourceVisual_CompletedEnabled
    bcs SourceVisual_CompletedCapture__enabled
    rts
SourceVisual_CompletedCapture__enabled:
.a16
.i16
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
    ldx #0
SourceVisual_CompletedCapture__pieces:
.a16
.i16
    lda.l SourceVisual_PieceTable,x
    sta.l SourceVisual_CompletedPieces,x
    inx
    inx
    cpx #1040
    bcc SourceVisual_CompletedCapture__pieces
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
    sta.l SourceVisual_CompletedValid
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
    bne SourceVisual_EmitCompleted__no_near
    lda.l SourceVisual_ServiceOnly
    bne SourceVisual_EmitCompleted__no_near
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
    ldx #0
SourceVisual_EmitCompleted__pieces:
.a16
.i16
    lda.l SourceVisual_CompletedPieces,x
    sta.l SourceVisual_PieceTable,x
    inx
    inx
    cpx #1040
    bcc SourceVisual_EmitCompleted__pieces
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
