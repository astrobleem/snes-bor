; One bounded foreground handoff after a real source block completion.
; The safe point is before FindEntry in a loader-only post-submit visit.
; No renderer metadata is live yet; a performed handoff retires that redundant
; nonowner visit. Incomplete source DMA retains the original fence.
SVActor_CompletionOwner = $4325B0
SVActor_CompletionUsed = $4325B2
SVActor_CompletionCandidate = $4325B4
SVActor_CompletionDp = $4325B6
SVActor_CompletionRole = $4325B8

SVActor_CompletionReset:
.a16
.i16
    jsr SVActor_Enabled
    bcc SVActor_CompletionReset__done
    lda #0
    sta.l SVActor_CompletionOwner
    sta.l SVActor_CompletionUsed
SVActor_CompletionReset__done:
.a16
.i16
    rts

; Called only AFTER ResumePendingBlock's idle fence and progress==4 actually
; publish cache state 2. Preserve the retirement routine's registers/flags.
SVActor_RecordCompletion:
.a16
.i16
    php
    rep #$30
    pha
    phx
    jsr SVActor_Enabled
    bcc SVActor_RecordCompletion__done
    lda.l SourceInput_Magic
    cmp #$1A60
    bne SVActor_RecordCompletion__done
    lda.l SVActor_LoadOwner
    cmp #1
    bcc SVActor_RecordCompletion__done
    cmp #3
    bcs SVActor_RecordCompletion__done
    cmp #2
    bne SVActor_RecordCompletion__player
    lda.l $7E0A85+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    bne SVActor_RecordCompletion__done
SVActor_RecordCompletion__player:
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
    bne SVActor_RecordCompletion__done
    lda.l SourceVisual_State,x
    cmp.l SVActor_LoadEntry
    bne SVActor_RecordCompletion__done
    lda.l SourceVisual_State+30,x
    and #$00FF
    cmp #2
    beq SVActor_RecordCompletion__record
    cmp #7
    bne SVActor_RecordCompletion__done
SVActor_RecordCompletion__record:
.a16
.i16
    lda.l SVActor_LoadOwner
    sta.l SVActor_CompletionOwner
SVActor_RecordCompletion__done:
.a16
.i16
    plx
    pla
    plp
    rts

; C=1 means this redundant nonowner service was replaced. Caller must use
; RenderCurrent__retired immediately. A is scratch; X/Y/D/DBR and widths are
; preserved. The completion token is consumed before any nested service.
SVActor_CompletionPulse:
.a16
.i16
    lda.l SVActor_CompletionOwner
    bne SVActor_CompletionPulse__token
    clc
    rts
SVActor_CompletionPulse__token:
.a16
.i16
    php
    rep #$30
    pha
    phx
    phy
    phb
    phd
    jsr SVActor_Enabled
    bcs SVActor_CompletionPulse__guard1
    brl SVActor_CompletionPulse__no
SVActor_CompletionPulse__guard1:
.a16
.i16
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SVActor_CompletionPulse__guard2
    brl SVActor_CompletionPulse__no
SVActor_CompletionPulse__guard2:
.a16
.i16
    lda.l SourceVisual_ServiceOnly
    cmp #1
    beq SVActor_CompletionPulse__guard3
    brl SVActor_CompletionPulse__no
SVActor_CompletionPulse__guard3:
.a16
.i16
    lda.l SourceVisual_CompletedEarly
    cmp #1
    beq SVActor_CompletionPulse__guard4
    brl SVActor_CompletionPulse__no
SVActor_CompletionPulse__guard4:
.a16
.i16
    lda.l SVActor_CompletionOwner
    sta.l SVActor_CompletionCandidate
    lda #0
    sta.l SVActor_CompletionOwner
    lda.l SVActor_CompletionUsed
    beq SVActor_CompletionPulse__guard5
    brl SVActor_CompletionPulse__no
SVActor_CompletionPulse__guard5:
.a16
.i16
    lda.l SVActor_CompletionCandidate
    cmp #1
    bcs SVActor_CompletionPulse__guard6
    brl SVActor_CompletionPulse__no
SVActor_CompletionPulse__guard6:
.a16
.i16
    cmp #3
    bcc SVActor_CompletionPulse__guard7
    brl SVActor_CompletionPulse__no
SVActor_CompletionPulse__guard7:
.a16
.i16
    cmp.l SVActor_LoadOwner
    beq SVActor_CompletionPulse__guard8
    brl SVActor_CompletionPulse__no
SVActor_CompletionPulse__guard8:
.a16
.i16
    dec a
    asl a
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l SourceVisual_State+6,x
    cmp #1
    beq SVActor_CompletionPulse__guard9
    brl SVActor_CompletionPulse__no
SVActor_CompletionPulse__guard9:
.a16
.i16
    lda.l SourceVisual_State,x
    cmp.l SVActor_LoadEntry
    beq SVActor_CompletionPulse__guard10
    brl SVActor_CompletionPulse__no
SVActor_CompletionPulse__guard10:
.a16
.i16
    lda.l SourceVisual_State+30,x
    and #$00FF
    sta.l SVActor_CompletionRole
    cmp #2
    beq SVActor_CompletionPulse__attack
    cmp #7
    beq SVActor_CompletionPulse__jump
    brl SVActor_CompletionPulse__no
SVActor_CompletionPulse__attack:
.a16
.i16
    jsr SVActor_FirstAttack
    cmp.l SVActor_CompletionCandidate
    beq SVActor_CompletionPulse__guard11
    brl SVActor_CompletionPulse__no
SVActor_CompletionPulse__guard11:
.a16
.i16
    brl SVActor_CompletionPulse__snapshot
SVActor_CompletionPulse__jump:
.a16
.i16
    lda.l SVActor_CompletionCandidate
    dec a
    asl a
    tax
    lda.l SVActor_LoadDps,x
    tax
    lda.l $7E0000+CHAR_SELECTED,x
    and #$00FF
    cmp #CHAR_SELECTED_JUMP
    beq SVActor_CompletionPulse__guard12
    brl SVActor_CompletionPulse__no
SVActor_CompletionPulse__guard12:
.a16
.i16
SVActor_CompletionPulse__snapshot:
.a16
.i16
    lda.l SVActor_CompletionCandidate
    cmp #1
    beq SVActor_CompletionPulse__p1
    lda.l $7E0A85+CHAR_INPUT_DRIVEN
    and #$00FF
    cmp #1
    beq SVActor_CompletionPulse__guard13
    brl SVActor_CompletionPulse__no
SVActor_CompletionPulse__guard13:
.a16
.i16
    lda.l SVActor_Data+SVActor_Valid
    cmp #1
    beq SVActor_CompletionPulse__guard14
    brl SVActor_CompletionPulse__no
SVActor_CompletionPulse__guard14:
.a16
.i16
    lda.l SVActor_Data+1
    brl SVActor_CompletionPulse__picture
SVActor_CompletionPulse__p1:
.a16
.i16
    lda.l SourceVisual_CompletedValid
    cmp #1
    beq SVActor_CompletionPulse__guard15
    brl SVActor_CompletionPulse__no
SVActor_CompletionPulse__guard15:
.a16
.i16
    lda.l SourceVisual_CompletedEntry+1
SVActor_CompletionPulse__picture:
.a16
.i16
    and #$00FF
    cmp.l SVActor_CompletionRole
    bne SVActor_CompletionPulse__guard16
    brl SVActor_CompletionPulse__no
SVActor_CompletionPulse__guard16:
.a16
.i16
    lda.l SVActor_CompletionCandidate
    dec a
    asl a
    tax
    lda.l SVActor_LoadDps,x
    sta.l SVActor_CompletionDp
    tdc
    cmp.l SVActor_CompletionDp
    bne SVActor_CompletionPulse__guard17
    brl SVActor_CompletionPulse__no
SVActor_CompletionPulse__guard17:
.a16
.i16
    lda.l SVActor_CompletionDp
    tax
    lda.l $7E0000+CHAR_HP,x
    and #$00FF
    bne SVActor_CompletionPulse__guard18
    brl SVActor_CompletionPulse__no
SVActor_CompletionPulse__guard18:
.a16
.i16
    lda.l Nmi_FrameBusy
    and #$00FF
    beq SVActor_CompletionPulse__environment1
    brl SVActor_CompletionPulse__no
SVActor_CompletionPulse__environment1:
.a16
.i16
    lda.l Nmi_Busy
    and #$00FF
    beq SVActor_CompletionPulse__environment2
    brl SVActor_CompletionPulse__no
SVActor_CompletionPulse__environment2:
.a16
.i16
    lda.l Msu1_StreamBusy
    and #$00FF
    beq SVActor_CompletionPulse__environment3
    brl SVActor_CompletionPulse__no
SVActor_CompletionPulse__environment3:
.a16
.i16
    jsr SourceVisual_HasOwnedDma
    bcc SVActor_CompletionPulse__guard19
    brl SVActor_CompletionPulse__no
SVActor_CompletionPulse__guard19:
.a16
.i16
    lda #1
    sta.l SVActor_CompletionUsed
    lda.l SVActor_CompletionDp
    tcd
SVActor_CompletionPulse__service:
.a16
.i16
    jsl SourceVisual_ServiceCurrent
    pld
    plb
    ply
    plx
    pla
    plp
    sec
    rts
SVActor_CompletionPulse__no:
.a16
.i16
    pld
    plb
    ply
    plx
    pla
    plp
    clc
    rts
