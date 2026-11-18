; Equivalent block release with one immutable arena eligibility check.
; Entered AFTER original SVActor_ReleasePinLease. Original fallback is intact.
; Campaign and initialized arena magics are foreground-owned; NMI never
; resets them. Held/Old owner bytes are intentionally read afresh per row.
SourceRelease_Protected:
.a16
.i16
    lda.l SourceVisual_CompletedMagic
    cmp #$C04D
    bne SourceRelease_Fallback
    lda.l Game_CampaignId
    and #255
    cmp #3
    bne SourceRelease_Fallback
    lda.l SVActor_Magic
    cmp #$AC19
    beq SourceRelease_Fast
SourceRelease_Fallback:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    tax
    lda #1
    jml SourceVisual_ReleaseActorBlocks__mask
SourceRelease_Fast:
.a16
.i16
    lda.l SourceVisual_ActorSlot
    tax
    lda #1
SourceRelease_Fast__mask:
.i16
    cpx #0
    beq SourceRelease_Fast__mask_ready
    asl a
    dex
    bra SourceRelease_Fast__mask
SourceRelease_Fast__mask_ready:
    sep #$20
.a8
    sta.l SourceVisual_BlockActorMask
    eor #$FF
    sta.l SourceVisual_BlockOther2
    rep #$31
.a16
.i16
    lda #0
    sta.l SourceVisual_BlockScan
SourceRelease_Fast__scan:
.a16
    lda.l SourceVisual_BlockScan
    cmp #SOURCE_VISUAL_TILE_BLOCKS
    bcc SourceRelease_Fast__body
    brl SourceRelease_Fast__done
SourceRelease_Fast__body:
.a16
.i16
    asl a
    asl a
    asl a
    tax
    sep #$20
.a8
    lda.l SourceVisual_BlockCache+4,x
    and.l SourceVisual_BlockOther2
    sta.l SourceVisual_BlockCache+4,x
    bne SourceRelease_Fast__next
    ; Scope is stable for this foreground release; pins remain live per row.
    rep #$20
.a16
.i16
    lda.l SVActor_HeldBlocks,x
    ora.l SVActor_OldBlocks,x
    and #$00FF
    bne SourceRelease_Fast__next
    sep #$20
.a8
.i16
    lda.l SourceVisual_BlockCache+7,x
    cmp #$A6
    beq SourceRelease_Fast__private_tag
    cmp #$A7
    bne SourceRelease_Fast__clear_unowned
SourceRelease_Fast__private_tag:
.a8
.i16
    jsl SourcePrefetch_KeepPending
    bcs SourceRelease_Fast__next
    jsl SourcePrefetch_KeepReady
    bcs SourceRelease_Fast__next
SourceRelease_Fast__clear_unowned:
.a8
.i16
    lda.l SourceVisual_BlockCache+2,x
    cmp #2
    bne SourceRelease_Fast__clear_cache
    jsl SourceIdle_KeepBlock
    bcs SourceRelease_Fast__next
SourceRelease_Fast__clear_cache:
.a8
.i16
    rep #$31
.a16
.i16
    ; Invalidate the full-cache certificate immediately before an actual
    ; clear; retaining evictable Ready content cannot create an empty row.
    lda.l SourceVisual_BucketMagic
    cmp #$B17B
    bne SourceRelease_Fast__occupancy_unknown
    lda #$B17A
    sta.l SourceVisual_BucketMagic
SourceRelease_Fast__occupancy_unknown:
.a16
.i16
    lda #0
    sta.l SourceVisual_BlockCache+2,x
    sta.l SourceVisual_BlockCache+6,x
SourceRelease_Fast__next:
    rep #$31
.a16
.i16
    lda.l SourceVisual_BlockScan
    inc a
    sta.l SourceVisual_BlockScan
    brl SourceRelease_Fast__scan
SourceRelease_Fast__done:
    jml SourceVisual_ReleaseActorBlocks__done
SourceRelease_End:
