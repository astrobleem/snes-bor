; Private prepared-walk handoff through the existing scene and PPU publisher.
; These wrappers are unhooked until their physical marker and foreground
; lifetime collector have been proved together.
SourceNextControl_NmiTail:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    phd
    lda.l SourcePacket_CopyBusy
    bne SourceNextControl_TailRefresh
    lda.l SourceNextCommit_State
    bne SourceNextControl_TailRefresh
    lda.l SourceNextFrame_Base
    cmp #$4E46
    bne SourceNextControl_TryP2
    lda.l SourceNextFrame_Base+750
    bne SourceNextControl_TryP2
    lda #0
    jsl SourceNextCommit_Apply
    bcs SourceNextControl_TailRefresh
SourceNextControl_TryP2:
.a16
.i16
    lda.l SourceNextFrame_Base+1024
    cmp #$4E46
    bne SourceNextControl_TailRefresh
    lda.l SourceNextFrame_Base+1024+750
    bne SourceNextControl_TailRefresh
    lda #1
    jsl SourceNextCommit_Apply
SourceNextControl_TailRefresh:
.a16
.i16
    lda.l SourcePacket_CopyBusy
    bne SourceNextControl_TailOriginal
    lda.l SourceNextCommit_Dirty
    beq SourceNextControl_TailOriginal
    lda #0
    sta.l SourcePacket_RefreshAccepted
SourceNextControl_TailOriginal:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    jsl SourcePacket_NmiPrepare
    php
    rep #$30
    pha
    lda.l SourceNextCommit_Dirty
    beq SourceNextControl_TailDone
    lda.l SourcePacket_RefreshAccepted
    cmp #1
    bne SourceNextControl_TailDone
    lda #1
    sta.l SourcePacket_NmiPending
SourceNextControl_TailDone:
.a16
.i16
    pla
    plp
    rtl

; Both normal and busy NMI gates must use this wrapper. The original
; publisher still owns queue, blanking, beam and DMA checks.
SourceNextControl_NmiPublish:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    phd
    lda.l SourceNextCommit_State
    cmp #1
    bne SourceNextControl_PublishOriginal
    lda.l SourcePacket_CopyBusy
    bne SourceNextControl_PublishSkip
    lda.l SourceNextCommit_Slot
    cmp #2
    bcs SourceNextControl_PublishSkip
    tax
    xba
    asl a
    asl a
    tax
    lda.l SourceNextFrame_Base+750,x
    cmp #2
    beq SourceNextControl_PublishAbort
    lda.l SourceNextScene_Magic
    cmp #$5343
    bne SourceNextControl_PublishAbort
    lda.l SourceNextScene_Low
    cmp.l SourceNextCommit_Low
    bne SourceNextControl_PublishAbort
    lda.l SourceNextScene_High
    cmp.l SourceNextCommit_High
    bne SourceNextControl_PublishAbort
    lda.l SourceNextCommit_Slot
    jsl SourceNextLive_Check
    bcc SourceNextControl_PublishAbort
SourceNextControl_PublishOriginal:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    jsl SourcePacket_NmiPublish
    rtl
SourceNextControl_PublishAbort:
.a16
.i16
    lda.l SourceNextCommit_Slot
    jsl SourceNextCommit_Abort
SourceNextControl_PublishSkip:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    rtl

; The foreground owns resource release. CopyBusy is acquired before examining
; either frame so NMI cannot commit a frame while its pins are being removed.
SourceNextControl_Foreground:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    phd
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    bne SourceNextControl_ForegroundDone
    lda.l $7E46DE
    bne SourceNextControl_ForegroundDone
    lda.l SourcePacket_CopyBusy
    bne SourceNextControl_ForegroundDone
    lda #1
    sta.l SourcePacket_CopyBusy
    lda #0
    jsl SourceNextControl_CollectSlot
    lda #1
    jsl SourceNextControl_CollectSlot
    lda #0
    sta.l SourcePacket_CopyBusy
SourceNextControl_ForegroundDone:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    jsl SourcePacket_ForegroundPrepare
    rtl

SourceNextControl_CollectSlot:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    cmp #2
    bcc SourceNextControl_CollectValid
    brl SourceNextControl_CollectDone
SourceNextControl_CollectValid:
.a16
.i16
    pha
    xba
    asl a
    asl a
    tax
    lda.l SourceNextFrame_Base,x
    cmp #$4E46
    beq SourceNextControl_CollectPrepared
    cmp #$4E47
    beq SourceNextControl_CollectPending
    cmp #$4E48
    beq SourceNextControl_CollectPublished
    brl SourceNextControl_CollectPop
SourceNextControl_CollectPrepared:
.a16
.i16
    lda.l SourceNextFrame_Base+750,x
    bne SourceNextControl_CollectCancel
    lda.l SourceNextScene_Magic
    cmp #$5343
    bne SourceNextControl_CollectCancel
    lda.l SourceNextScene_Low
    cmp.l SourceNextFrame_Base+742,x
    bne SourceNextControl_CollectCancel
    lda.l SourceNextScene_High
    cmp.l SourceNextFrame_Base+744,x
    bne SourceNextControl_CollectCancel
    brl SourceNextControl_CollectPop
SourceNextControl_CollectCancel:
.a16
.i16
    lda 1,s
    jsl SourceNextFrame_CancelUnpublished
    brl SourceNextControl_CollectPop
SourceNextControl_CollectPending:
.a16
.i16
    lda.l SourceNextScene_Magic
    cmp #$5343
    bne SourceNextControl_CollectRequestAbort
    lda.l SourceNextScene_Low
    cmp.l SourceNextCommit_Low
    bne SourceNextControl_CollectRequestAbort
    lda.l SourceNextScene_High
    cmp.l SourceNextCommit_High
    beq SourceNextControl_CollectPop
SourceNextControl_CollectRequestAbort:
.a16
.i16
    lda #2
    sta.l SourceNextFrame_Base+750,x
    brl SourceNextControl_CollectPop
SourceNextControl_CollectPublished:
.a16
.i16
    lda.l SourceVisual_CompletedAcks
    cmp.l SourceNextFrame_Base+746,x
    beq SourceNextControl_CollectPop
    lda.l SourcePacket_ActiveValid
    beq SourceNextControl_CollectRelease
    lda.l SourceNextScene_Magic
    cmp #$5343
    bne SourceNextControl_CollectRelease
    lda.l SourceNextScene_Low
    cmp.l SourceNextFrame_Base+742,x
    bne SourceNextControl_CollectRelease
    lda.l SourceNextScene_High
    cmp.l SourceNextFrame_Base+744,x
    beq SourceNextControl_CollectPop
SourceNextControl_CollectRelease:
.a16
.i16
    lda #$4E46
    sta.l SourceNextFrame_Base,x
    lda #1
    sta.l SourceNextFrame_Base+750,x
    lda 1,s
    jsl SourceNextFrame_CancelUnpublished
SourceNextControl_CollectPop:
.a16
.i16
    pla
SourceNextControl_CollectDone:
.a16
.i16
    ply
    plx
    pla
    plp
    rtl

; Preserve the original palette-queued store. Only walking role1 attempts
; private preparation; attack, jump and all other loader roles stay original.
SourceNextControl_PaletteQueued:
.a16
.i16
    lda #1
    sta.l SourceVisual_State+4,x
    php
    rep #$30
    pha
    phx
    phy
    phb
    phd
    lda.l SourceVisual_EntryScratch+1
    and #255
    cmp #1
    bne SourceNextControl_PaletteDone
    lda.l SourceVisual_ActorSlot
    cmp #2
    bcs SourceNextControl_PaletteDone
    jsl SourceNextFrame_Prepare
SourceNextControl_PaletteDone:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    rtl
SourceNextControl_End:
