
; v777 SHADOW ONLY: kind/root-held remain zero. These records cannot
; authorize Adopt/Retire, publish an image or change a cache lease.
; 434EA0..4ECF future body, 4ED0..4EF7 descriptor, footer4EF8..4EFF.
; Init is the only reset writer; NMI owns ticket/source, SA1 owns source
; cancellation count, SCPU foreground owns native count. Cancel is an
; idempotent byte store shared by both CPUs, never a read-modify-write.
.bank 39
.org $A000
SourceIdleShadow_Init:
.a16
.i16
    php
    rep #$30
    pha
    phx
    lda #0
    ldx #0
SourceIdleShadow_Clear:
    sta.l $434EA0,x
    inx
    inx
    cpx #96
    bcc SourceIdleShadow_Clear
    lda #$1DAD
    sta.l $434ED0
    lda #$D1E0
    sta.l $434EA0
    sep #$20
.a8
    lda #1
    sta.l $434EF9
    rep #$20
.a16
    plx
    pla
    plp
    lda #$4F
    sta.l SourceAttackOwned_SourceHi
    rtl
; Called ONLY at the existing success tail, after both physical OAM DMAs.
; This shadow sequence is transport telemetry, NOT an idle-owner ticket.
SourceIdleShadow_NmiCommit:
.a16
.i16
    sta.l SourcePacket_NmiPending
    php
    rep #$30
    pha
    lda.l $434EA0
    cmp #$D1E0
    bne SourceIdleShadow_NmiDone
    lda.l $434ED0
    cmp #$1DAD
    bne SourceIdleShadow_NmiDone
    lda.l $434ED2
    bne SourceIdleShadow_NmiDone
    lda.l $434EF9
    and #255
    cmp #1
    bne SourceIdleShadow_NmiDone
    lda.l $434EFA
    inc a
    sta.l $434EFA
    bne SourceIdleShadow_NoCarry
    lda.l $434EFC
    inc a
    sta.l $434EFC
SourceIdleShadow_NoCarry:
    lda.l $434EFA
    sta.l $434EE0
    lda.l $434EFC
    sta.l $434EE2
    jsl SourceAttackOwned_SourceSelect
    and #255
    sta.l $434EF2
    lda #1
    sta.l $434EEE
SourceIdleShadow_NmiDone:
    pla
    plp
    rtl
SourceIdleShadow_CancelNative:
.a16
.i16
    php
    rep #$30
    pha
    tdc
    cmp #$0A00
    beq SourceIdleShadow_NativeScope
    cmp #$0A85
    bne SourceIdleShadow_NativeDone
SourceIdleShadow_NativeScope:
    lda.l $434EA0
    cmp #$D1E0
    bne SourceIdleShadow_NativeDone
    lda.l $434EF9
    and #255
    cmp #1
    bne SourceIdleShadow_NativeDone
    lda.l $434EF4
    inc a
    sta.l $434EF4
    sep #$20
.a8
    lda #1
    sta.l $434EF8
SourceIdleShadow_NativeDone:
    rep #$20
.a16
    pla
    plp
    rtl
SourceIdleShadow_Jump:
.a8
.i16
    jsl SourceIdleShadow_CancelNative
    lda #AUDIO_SEMANTIC_JUMP
    sta.l AudioSemantic_CurrentId
    rtl
; SA1-safe: only caller DP and linear BW-RAM, no SCPU WRAM/PPU accesses.
SourceIdleShadow_CancelSource:
.a16
.i16
    php
    rep #$30
    pha
    lda $7A
    beq SourceIdleShadow_SourceScope
    cmp #133
    bne SourceIdleShadow_SourceDone
SourceIdleShadow_SourceScope:
    lda.l $434EA0
    cmp #$D1E0
    bne SourceIdleShadow_SourceDone
    lda.l $434EF9
    and #255
    cmp #1
    bne SourceIdleShadow_SourceDone
    lda.l $434EF6
    inc a
    sta.l $434EF6
    sep #$20
.a8
    lda #1
    sta.l $434EF8
SourceIdleShadow_SourceDone:
    rep #$20
.a16
    pla
    plp
    rtl
SourceIdleShadow_Role:
.a16
.i16
    jsl SourceIdleShadow_CancelSource
    sta $E4
    iny
    iny
    rtl
SourceIdleShadow_Axis:
.a16
.i16
    jsl SourceIdleShadow_CancelSource
    ldx $90
    lda $9A,x
    rtl
SourceIdleShadow_DamageVelocity:
.a16
.i16
    jsl SourceIdleShadow_CancelSource
    ldx $B0
    lda.l $40A000,x
    rtl
SourceIdleShadow_DamageLethal:
.a16
.i16
    jsl SourceIdleShadow_CancelSource
    lda #0
    sta $F0
    sta $F6
    rtl
SourceIdleShadow_End:
.assert * <= $27B000, "idle shadow hooks exceed blank ROM"
