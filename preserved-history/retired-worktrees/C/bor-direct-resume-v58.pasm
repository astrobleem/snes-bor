
; Resume an already-admitted immutable player lease. The caller has established
; exact owner/entry, pending state, urgent role, lifetime and idle DMA scope.
; Cache/stage, roster, source role, viewport and ordinary loader checks remain.
; C=1 means serviced (including normal pending); C=0 uses the full old path.
SVActor_ResumeCompletedLease:
.a16
.i16
    tdc
    tax
    lda.l $7E0000+CHAR_ROSTER_INDEX,x
    and #$00FF
    sta.l SVActor_CompletionRoster
    lda.l SVActor_CompletionCandidate
    dec a
    sta.l SourceVisual_ActorSlot
    asl a
    asl a
    asl a
    sta.l SourceVisual_DebugRecord
    asl a
    asl a
    sta.l SourceVisual_Record
    tax
    lda.l SourceVisual_State+29,x
    and #$00FF
    cmp.l SVActor_CompletionRoster
    bne SVActor_ResumeCompletedLease__no
    lda.l SVActor_CompletionRole
    cmp #2
    bne SVActor_ResumeCompletedLease__entry
    tdc
    tax
    lda.l $7E0000+CHAR_SELECTED,x
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
    beq SVActor_ResumeCompletedLease__no
SVActor_ResumeCompletedLease__entry:
.a16
.i16
    lda.l SVActor_LoadEntry
    sta.l SourceVisual_EntryIndexSaved
    jsr SVActor_MetaEntry
    bcc SVActor_ResumeCompletedLease__no
    lda.l SourceVisual_EntryScratch
    and #$00FF
    cmp.l SVActor_CompletionRoster
    bne SVActor_ResumeCompletedLease__no
    lda.l SourceVisual_EntryScratch+1
    and #$00FF
    cmp.l SVActor_CompletionRole
    bne SVActor_ResumeCompletedLease__no
    jsr SourceVisual_FrameInViewport
    bcc SVActor_ResumeCompletedLease__no
    lda.l SourceVisual_EntryScratch
    sta.l SourceVisual_Key
    lda.l SourceVisual_EntryScratch+2
    sta.l SourceVisual_Key+2
    lda #1
    sta.l SourceVisual_ServiceOnly
    jsr SourceVisual_LoadResources
    sec
    rts
SVActor_ResumeCompletedLease__no:
.a16
.i16
    clc
    rts
