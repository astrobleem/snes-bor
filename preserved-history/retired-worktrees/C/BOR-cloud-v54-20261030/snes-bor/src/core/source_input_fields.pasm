; Original BOR production input journal, 64 physical fields * two pads.
; NMI exclusively owns Producer and ring writes. Main exclusively owns
; Consumer, private edge histories, worker mailboxes and native edge latches.
; Publish Producer LAST. No MSU, world/AI, OAM, or game-facing input mutation
; occurs in NMI. The original unconditional physical clock hook is retained.
;
; DebugEmitOam is $7E4660..469F; journal controls occupy the following 32-byte
; gap, and the ring $4700..47FF ends exactly before EntryScratch at $4800.
SourceInput_Producer = $7E46A0
SourceInput_Consumer = $7E46A2
SourceInput_Overflows = $7E46A4
SourceInput_Next = $7E46A6
SourceInput_ReadIndex = $7E46A8
SourceInput_Magic = $7E46AA
SourceInput_Samples = $7E46AC
SourceInput_DrainEnd = $7E46AE
SourceInput_BaseReady = $7E4BF4 ; epoch flag, independent of diagnostic sample wrap
SourceInput_BaseField = $7E46B0
SourceInput_ReplayField = $7E46B2
SourceInput_ReplayHeld1 = $7E46B4
SourceInput_ReplayHeld2 = $7E46B6
SourceInput_Selected1 = $7E46B8
SourceInput_Selected2 = $7E46BA
SourceInput_HistoryMisses = $7E46BC
SourceInput_ReplayTemp = $7E46BE
SourceInput_Ring = $7E4700

SourceInput_NmiGate:
    jsl SourceClock4086_NmiGate
    php
    rep #$30
.a16
.i16
    pha
    phx
    phb
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SourceInput_NmiGate__magic
    brl SourceInput_NmiGate__done
SourceInput_NmiGate__magic:
.a16
.i16
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq SourceInput_NmiGate__campaign
    brl SourceInput_NmiGate__done
SourceInput_NmiGate__campaign:
.a16
.i16
    lda.l $7E1760
    cmp #1
    beq SourceInput_NmiGate__active
    brl SourceInput_NmiGate__done
SourceInput_NmiGate__active:
.a16
.i16
    lda.l SourceInput_BaseReady
    bne SourceInput_NmiGate__based
    lda.l StageTimer_FieldCounter
    dec a
    sta.l SourceInput_BaseField
    lda #1
    sta.l SourceInput_BaseReady
SourceInput_NmiGate__based:
.a16
.i16
    lda.l SourceInput_Producer
    inc a
    and #63
    sta.l SourceInput_Next
    cmp.l SourceInput_Consumer
    bne SourceInput_NmiGate__space
    lda.l SourceInput_Overflows
    inc a
    sta.l SourceInput_Overflows
    brl SourceInput_NmiGate__done
SourceInput_NmiGate__space:
.a16
.i16
    lda.l SourceInput_Producer
    asl a
    asl a
    tax
    sep #$20
.a8
    lda #0
    pha
    plb
    rep #$30
.a16
.i16
    ; Auto-joy completes in a bounded hardware interval after vblank starts.
    ; Polling here also covers NMIs that skip visual commits while main stalls.
SourceInput_NmiGate__joy_busy:
.a16
.i16
    lda $4212
    and #1
    bne SourceInput_NmiGate__joy_busy
    lda $4218
    bit #$000F
    beq SourceInput_NmiGate__p1
    lda #0
SourceInput_NmiGate__p1:
.a16
.i16
    sta.l SourceInput_Ring,x
    lda $421A
    bit #$000F
    beq SourceInput_NmiGate__p2
    lda #0
SourceInput_NmiGate__p2:
.a16
.i16
    sta.l SourceInput_Ring+2,x
    lda.l SourceInput_Next
    sta.l SourceInput_Producer
    lda.l SourceInput_Samples
    inc a
    sta.l SourceInput_Samples
SourceInput_NmiGate__done:
    rep #$30
.a16
.i16
    plb
    plx
    pla
    plp
    rtl

; Cooperative main-thread consumer, called by relay waits, allocator scans
; and before the main poll. NMI can append a row at any instruction boundary;
; it never writes these edge histories/mailboxes and cannot lose an OR edge.
SourceVisual_SampleInput:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    lda.l SourceInput_Magic
    cmp #$1A60
    beq SourceVisual_SampleInput__magic
    brl SourceVisual_SampleInput__done
SourceVisual_SampleInput__magic:
.a16
.i16
    lda.l Game_CampaignId
    and #$00FF
    cmp #3
    beq SourceVisual_SampleInput__campaign
    brl SourceVisual_SampleInput__done
SourceVisual_SampleInput__campaign:
.a16
.i16
    lda.l $7E1760
    cmp #1
    beq SourceVisual_SampleInput__active
    brl SourceVisual_SampleInput__done
SourceVisual_SampleInput__active:
.a16
.i16
    lda.l SourceInput_Producer
    sta.l SourceInput_DrainEnd
SourceVisual_SampleInput__row:
.a16
.i16
    lda.l SourceInput_Consumer
    cmp.l SourceInput_DrainEnd
    bne SourceVisual_SampleInput__next
    brl SourceVisual_SampleInput__done
SourceVisual_SampleInput__next:
.a16
.i16
    sta.l SourceInput_ReadIndex
    asl a
    asl a
    tax
    lda.l SourceInput_Ring,x
    sta.l SourceVisual_FieldRaw1
    lda.l SourceVisual_FieldPress1
    eor #$FFFF
    and.l SourceVisual_FieldRaw1
    sta.l SourceVisual_FieldEdge1
    ora.l $412016
    sta.l $412016
    lda.l SourceVisual_FieldEdge1
    ora.l SourceVisual_LatchedInput
    sta.l SourceVisual_LatchedInput
    lda.l SourceVisual_FieldRaw1
    sta.l SourceVisual_FieldPress1
    sta.l $412014
    lda.l SourceInput_Ring+2,x
    sta.l SourceVisual_FieldRaw2
    lda.l SourceVisual_FieldPress2
    eor #$FFFF
    and.l SourceVisual_FieldRaw2
    sta.l SourceVisual_FieldEdge2
    ora.l $41201A
    sta.l $41201A
    lda.l SourceVisual_FieldEdge2
    ora.l SourceVisual_LatchedInput2
    sta.l SourceVisual_LatchedInput2
    lda.l SourceVisual_FieldRaw2
    sta.l SourceVisual_FieldPress2
    sta.l $412018
    lda.l SourceInput_ReadIndex
    inc a
    and #63
    sta.l SourceInput_Consumer
    brl SourceVisual_SampleInput__row
SourceVisual_SampleInput__done:
    rep #$30
.a16
.i16
    ply
    plx
    pla
    plp
    rtl

; A16 is the physical field being replayed by the bounded source catch-up
; batch. Preserve caller state and queue-row X. Drain sampling remains separate:
; each source tick receives that field's held pads, not the latest pad repeated
; over the entire backlog. Multiple 200-Hz ticks within one field get one edge.
SourceInput_SelectField:
    php
    rep #$30
.a16
.i16
    pha
    phx
    phy
    sta.l SourceInput_ReplayTemp
    lda.l SourceInput_Samples
    bne SourceInput_SelectField__sampled
    brl SourceInput_SelectField__miss
SourceInput_SelectField__sampled:
.a16
.i16
    lda.l StageTimer_FieldCounter
    sec
    sbc.l SourceInput_ReplayTemp
    cmp #63
    bcc SourceInput_SelectField__recent
    brl SourceInput_SelectField__miss
SourceInput_SelectField__recent:
.a16
.i16
    lda.l SourceInput_ReplayTemp
    sec
    sbc.l SourceInput_BaseField
    dec a
    cmp #$8000
    bcc SourceInput_SelectField__in_epoch
    brl SourceInput_SelectField__miss
SourceInput_SelectField__in_epoch:
.a16
.i16
    and #63
    asl a
    asl a
    tax
    lda.l SourceInput_Ring,x
    sta.l SourceInput_Selected1
    lda.l SourceInput_Ring+2,x
    sta.l SourceInput_Selected2
    lda.l SourceInput_ReplayTemp
    cmp.l SourceInput_ReplayField
    beq SourceInput_SelectField__same
    sta.l SourceInput_ReplayField
    lda.l SourceInput_ReplayHeld1
    eor #$FFFF
    and.l SourceInput_Selected1
    sta.l $412016
    lda.l SourceInput_ReplayHeld2
    eor #$FFFF
    and.l SourceInput_Selected2
    sta.l $41201A
    bra SourceInput_SelectField__held
SourceInput_SelectField__same:
.a16
.i16
    lda #0
    sta.l $412016
    sta.l $41201A
SourceInput_SelectField__held:
.a16
.i16
    lda.l SourceInput_Selected1
    sta.l SourceInput_ReplayHeld1
    sta.l $412014
    lda.l SourceInput_Selected2
    sta.l SourceInput_ReplayHeld2
    sta.l $412018
    bra SourceInput_SelectField__done
SourceInput_SelectField__miss:
.a16
.i16
    ; Startup before the first sample or an older-than-ring backlog retains
    ; the existing sampled fallback, with an explicit diagnostic count.
    lda.l SourceInput_HistoryMisses
    inc a
    sta.l SourceInput_HistoryMisses
SourceInput_SelectField__done:
.a16
.i16
    ply
    plx
    pla
    plp
    rtl
