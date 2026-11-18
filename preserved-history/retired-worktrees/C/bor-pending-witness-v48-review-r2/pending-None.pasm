.snes
.bank 0
.org $8000
.a16
.i16
SourceInput_Magic = $7E46AA
SourceVisual_BlockCache = $7E4C00
SourceVisual_BlockScan = $7E4B92
SourceVisual_BlockIndex = $7E4B80
SourceVisual_BlockSlot = $7E4B82
Test_Enable = $4325F0
    jmp SVActor_PendingNone
SVActor_Enabled:
    lda.l Test_Enable
    cmp #1
    beq Test_Enabled
    clc
    rts
Test_Enabled:
.a16
.i16
    sec
    rts
SVActor_PendingSlot = $4325B0
SVActor_PendingId = $4325B2
SVActor_PendingScope:
.a16
.i16
    jsr SVActor_Enabled
    bcc SVActor_PendingScope__no
    lda.l SourceInput_Magic
    cmp #$1A60
    bne SVActor_PendingScope__no
    sec
    rts
SVActor_PendingScope__no:
.a16
.i16
    clc
    rts
; C=1/A=0: known empty; C=1/A=1/X=row: validated pending; C=0: scan.
SVActor_PendingLookup:
.a16
.i16
    jsr SVActor_PendingScope
    bcc SVActor_PendingLookup__unknown
    lda.l SVActor_PendingSlot
    cmp #$FFFF
    beq SVActor_PendingLookup__empty
    cmp #64
    bcs SVActor_PendingLookup__unknown
    sta.l SourceVisual_BlockScan
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_BlockCache+2,x
    cmp #1
    bne SVActor_PendingLookup__unknown
    lda.l SourceVisual_BlockCache,x
    cmp.l SVActor_PendingId
    bne SVActor_PendingLookup__unknown
    lda #1
    sec
    rts
SVActor_PendingLookup__empty:
.a16
.i16
    lda #0
    sec
    rts
SVActor_PendingLookup__unknown:
.a16
.i16
    clc
    rts
; X remains the existing aligned row. Publish before changing ID/state.
SVActor_PendingClaim:
.a16
.i16
    jsr SVActor_Enabled
    bcc SVActor_PendingClaim__done
    lda.l SourceInput_Magic
    cmp #$1A60
    bne SVActor_PendingClaim__unknown
    txa
    cmp #512
    bcs SVActor_PendingClaim__unknown
    and #7
    bne SVActor_PendingClaim__unknown
    txa
    lsr a
    lsr a
    lsr a
    sta.l SVActor_PendingSlot
    lda.l SourceVisual_BlockIndex
    sta.l SVActor_PendingId
    rts
SVActor_PendingClaim__unknown:
.a16
.i16
    ; A claim before input-protocol activation must invalidate known-empty.
    ; Its next scoped lookup reconstructs from the real cache, never assumes.
    lda #$FFFE
    sta.l SVActor_PendingSlot
    lda #$FFFF
    sta.l SVActor_PendingId
SVActor_PendingClaim__done:
.a16
.i16
    rts
; Called only after actual DMA retirement and progress==4 set state2.
SVActor_PendingClear:
.a16
.i16
    jsr SVActor_PendingScope
    bcc SVActor_PendingClear__done
    lda.l SVActor_PendingSlot
    cmp.l SourceVisual_BlockSlot
    bne SVActor_PendingClear__done
    lda.l SVActor_PendingId
    cmp.l SourceVisual_BlockIndex
    bne SVActor_PendingClear__done
    lda #$FFFF
    sta.l SVActor_PendingSlot
    sta.l SVActor_PendingId
SVActor_PendingClear__done:
.a16
.i16
    rts
SVActor_PendingNone:
.a16
.i16
    jsr SVActor_PendingScope
    bcc SVActor_PendingNone__done
    lda #$FFFF
    sta.l SVActor_PendingSlot
    sta.l SVActor_PendingId
SVActor_PendingNone__done:
.a16
.i16
    rts
