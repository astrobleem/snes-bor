; Retain only the exact first authored attack-0 picture after normal
; emission. The existing next-pose held bits64/128 are otherwise unhooked;
; they are distinct from the OAM completed/retiring owner bits. No byte of
; OAM, DMA readiness, world state or published packet is changed here.
SourceAttackStandby_Reserve:
.a16
.i16
    php
    rep #$30
    pha
    lda.l SourceVisual_Key
    cmp #$0216
    bne SourceAttackStandby_ReserveDone
    lda.l SourceVisual_Key+2
    bne SourceAttackStandby_ReserveDone
    lda.l SourceVisual_PieceCount
    cmp #10
    bne SourceAttackStandby_ReserveDone
    jsl SourceNextPins_Acquire
SourceAttackStandby_ReserveDone:
    pla
    plp
    rtl

; The allocator calls this only after its normal victim search fails. Drop
; both optional standby leases, then retry the unchanged physical allocator.
; Current/hardware OAM has independent completed/retiring pins. A standby
; image is never published by this experiment, so its held bits are optional.
SourceAttackStandby_ReleasePressure:
.a16
.i16
    php
    rep #$30
    pha
    phx
    ldx #0
SourceAttackStandby_PressureScan:
    lda.l SVActor_HeldBlocks,x
    and #$00C0
    bne SourceAttackStandby_PressureDrop
    txa
    clc
    adc #8
    tax
    cpx #512
    bcc SourceAttackStandby_PressureScan
    plx
    pla
    plp
    clc
    rtl
SourceAttackStandby_PressureDrop:
    lda #0
    jsl SourceNextPins_ReleaseUnpublished
    lda #1
    jsl SourceNextPins_ReleaseUnpublished
    plx
    pla
    plp
    sec
    rtl
