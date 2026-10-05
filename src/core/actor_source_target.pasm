; Source enemy_find_target discrete core, opt-in only.
; D=source actor page, DBR0,A16/I16,decimal clear. Actor36=world DP.
; World44/46 are player[0]/player[1] context pointers (not first two actors).
; Output actor34=target, A=target. Scratch actor60..6C. FC=10 numeric domain,
; FC=9 bad binding. Missing player pointers retain source ordering semantics.
; Admission: source coordinates MUST already be proven integral, not rounded
; from arbitrary floats. Each operand must be -16384..16383. Differences are
; bounded to 32767 (signed16); Manhattan sums through 65534 use unsigned16 and
; exactly representable at precision24+.
; This routine does not certify fractional AI or ordinary enemy execution.
S6_SelectTarget:
    rep #$30
    .a16
    .i16
    jsl S6_CheckPolicy
    lda $FC
    beq S6_SelectTarget__world
    rtl
S6_SelectTarget__world:
    .a16
    .i16
    stz $34
    lda $36
    jsl S6_TargetPointer
    bcc S6_SelectTarget__world_valid
    jmp S6_SelectTarget__bad
S6_SelectTarget__world_valid:
    .a16
    .i16
    tax
    lda.l $7E0044,x
    sta $60
    lda.l $7E0046,x
    sta $62
    lda $60
    bne S6_SelectTarget__both
    jmp S6_SelectTarget__one
S6_SelectTarget__both:
    .a16
    .i16
    jsl S6_TargetPointer
    bcc S6_SelectTarget__p0_valid
    jmp S6_SelectTarget__bad
S6_SelectTarget__p0_valid:
    .a16
    .i16
    lda $62
    bne S6_SelectTarget__p1_present
    jmp S6_SelectTarget__first
S6_SelectTarget__p1_present:
    .a16
    .i16
    jsl S6_TargetPointer
    bcc S6_SelectTarget__p1_valid
    jmp S6_SelectTarget__bad
S6_SelectTarget__p1_valid:
    .a16
    .i16
    lda $14
    jsl S6_TargetCoordinate
    bcc S6_SelectTarget__x_valid
    jmp S6_SelectTarget__numeric
S6_SelectTarget__x_valid:
    .a16
    .i16
    lda $16
    jsl S6_TargetCoordinate
    bcc S6_SelectTarget__z_valid
    jmp S6_SelectTarget__numeric
S6_SelectTarget__z_valid:
    .a16
    .i16
    ldx $60
    jsl S6_TargetDelta
    lda $FC
    bne S6_SelectTarget__return
    lda $64
    sta $68
    lda $66
    sta $6A
    ldx $62
    jsl S6_TargetDelta
    lda $FC
    bne S6_SelectTarget__return
    ; Strict straddling, equal X is NOT on the other side.
    lda $68
    beq S6_SelectTarget__distance
    lda $64
    beq S6_SelectTarget__distance
    eor $68
    bpl S6_SelectTarget__distance
    lda $1A
    beq S6_SelectTarget__left
    lda $68
    bmi S6_SelectTarget__first
    bra S6_SelectTarget__second
S6_SelectTarget__left:
    .a16
    .i16
    lda $68
    bpl S6_SelectTarget__first
    bra S6_SelectTarget__second
S6_SelectTarget__distance:
    .a16
    .i16
    lda $68
    jsl S6_TargetAbs
    sta $6C
    lda $6A
    jsl S6_TargetAbs
    clc
    adc $6C
    sta $6C
    lda $64
    jsl S6_TargetAbs
    sta $68
    lda $66
    jsl S6_TargetAbs
    clc
    adc $68
    cmp $6C
    ; source strict d1<d2, ties select player[1].
    beq S6_SelectTarget__second
    bcc S6_SelectTarget__second
S6_SelectTarget__first:
    .a16
    .i16
    lda $60
    sta $34
    rtl
S6_SelectTarget__one:
    .a16
    .i16
    lda $62
    beq S6_SelectTarget__second
    jsl S6_TargetPointer
    bcs S6_SelectTarget__bad
S6_SelectTarget__second:
    .a16
    .i16
    lda $62
    sta $34
S6_SelectTarget__return:
    .a16
    .i16
    rtl
S6_SelectTarget__bad:
    .a16
    .i16
    lda #9
    sta $FC
    rtl
S6_SelectTarget__numeric:
    .a16
    .i16
    lda #10
    sta $FC
    rtl

S6_TargetPointer:
    .a16
    .i16
    pha
    and #$00FF
    bne S6_TargetPointer__bad
    pla
    beq S6_TargetPointer__zero
    cmp #$1F00
    rtl
S6_TargetPointer__bad:
    .a16
    .i16
    pla
S6_TargetPointer__zero:
    .a16
    .i16
    sec
    rtl

S6_TargetCoordinate:
    .a16
    .i16
    pha
    clc
    adc #16384
    cmp #32768
    pla
    rtl

S6_TargetDelta:
    .a16
    .i16
    lda.l $7E0014,x
    jsl S6_TargetCoordinate
    bcs S6_TargetDelta__numeric
    sta $64
    lda.l $7E0016,x
    jsl S6_TargetCoordinate
    bcs S6_TargetDelta__numeric
    sta $66
    lda $14
    sec
    sbc $64
    sta $64
    lda $16
    sec
    sbc $66
    sta $66
    rtl
S6_TargetDelta__numeric:
    .a16
    .i16
    lda #10
    sta $FC
    rtl
S6_TargetAbs:
    .a16
    .i16
    cmp #0
    bpl S6_TargetAbs__done
    eor #$FFFF
    inc a
S6_TargetAbs__done:
    .a16
    .i16
    rtl
