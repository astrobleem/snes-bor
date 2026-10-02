; Source ordinary single-attack decision/role driver, opt-in.
; Metadata, not source identity, selects this bounded capability.
; Actor A0 attack role, A2 signed range minimum,A4 signed maximum,A6 walk role.
; A8 nonzero means additional attack/upper/jump/frame-event semantics required.
; AA scratch. 38 idle role; E6:1 enemy,11 prepare,12 attack,13 runoff.
; Required host grounds/positions/source integer domain and supplies one
; shared source RNG at36. No movement fallback exists outside this slice.
; FC13 identifies approach/runoff/additional-role capability not bound here.
S6_EnemyDecision:
    rep #$30
    .a16
    .i16
    jsl S6_CheckPolicy
    bcc S6_EnemyDecision__policy
    rtl
S6_EnemyDecision__policy:
    .a16
    .i16
    lda $A8
    beq S6_EnemyDecision__features
    jmp S6_EnemyDecision__blocked
S6_EnemyDecision__features:
    .a16
    .i16
    lda $E6
    cmp #12
    bne S6_EnemyDecision__driver
    jml S6_EnemyAttack
S6_EnemyDecision__driver:
    .a16
    .i16
    cmp #1
    beq S6_EnemyDecision__select
    cmp #11
    beq S6_EnemyDecision__select
    jmp S6_EnemyDecision__blocked
S6_EnemyDecision__select:
    .a16
    .i16
    jsl S6_SelectTarget
    lda $FC
    bne S6_EnemyDecision__done
    lda $34
    beq S6_EnemyDecision__no_target
    tax
    lda.l $7E0014,x
    sec
    sbc $14
    beq S6_EnemyDecision__left
    bmi S6_EnemyDecision__left
    lda #1
    bra S6_EnemyDecision__face
S6_EnemyDecision__left:
    .a16
    .i16
    lda #0
S6_EnemyDecision__face:
    .a16
    .i16
    sta $1A
    lda $E6
    cmp #11
    beq S6_EnemyPrepare
    lda.l $7E0016,x
    sec
    sbc $16
    jsl S6_TargetAbs
    cmp #12
    bcs S6_EnemyDecision__blocked
    jsl S6_EnemyInRange
    bcc S6_EnemyDecision__blocked
    stz $FA
    lda $38
    jsl S6_SetRole
    lda $FC
    bne S6_EnemyDecision__done
    lda #11
    sta $E6
    ; rand32()%20 == (rand32()%1000)%20 for every unsigned32 result.
    phd
    lda $36
    tcd
    jsl S6_Random32
    jsl S6_RandomModulo1000
    lda $18
S6_EnemyDecision__mod20:
    .a16
    .i16
    cmp #20
    bcc S6_EnemyDecision__delay
    sbc #20
    bra S6_EnemyDecision__mod20
S6_EnemyDecision__delay:
    .a16
    .i16
    pld
    clc
    adc #50
    clc
    adc $D0
    sta $EC
    lda $D2
    adc #0
    sta $EE
S6_EnemyDecision__done:
    .a16
    .i16
    rtl
S6_EnemyDecision__no_target:
    .a16
    .i16
    lda #1
    sta $E6
    rtl
S6_EnemyDecision__attack:
    .a16
    .i16
    jml S6_EnemyAttack
S6_EnemyDecision__blocked:
    .a16
    .i16
    lda #13
    sta $FC
    rtl

S6_EnemyPrepare:
    .a16
    .i16
    lda $D2
    cmp $EE
    bcc S6_EnemyPrepare__done
    bne S6_EnemyPrepare__ready
    lda $D0
    cmp $EC
    bcc S6_EnemyPrepare__done
S6_EnemyPrepare__ready:
    .a16
    .i16
    jsl S6_EnemyInRange
    bcc S6_EnemyPrepare__retry
    stz $FA
    lda $A0
    jsl S6_SetRole
    lda #12
    sta $E6
S6_EnemyPrepare__done:
    .a16
    .i16
    rtl
S6_EnemyPrepare__retry:
    .a16
    .i16
    lda #1
    sta $E6
    rtl

; Direction was just selected toward target. Distance is nonnegative and
; bounded8190. Source strict minimum/maximum comparisons preserve equality.
S6_EnemyInRange:
    .a16
    .i16
    ldx $34
    lda.l $7E0014,x
    sec
    sbc $14
    jsl S6_TargetAbs
    sta $AA
    lda $A2
    bmi S6_EnemyInRange__maximum
    cmp $AA
    bcs S6_EnemyInRange__miss
S6_EnemyInRange__maximum:
    .a16
    .i16
    lda $A4
    bmi S6_EnemyInRange__miss
    beq S6_EnemyInRange__miss
    cmp $AA
    beq S6_EnemyInRange__miss
    bcc S6_EnemyInRange__miss
    sec
    rtl
S6_EnemyInRange__miss:
    .a16
    .i16
    clc
    rtl

S6_EnemyAttack:
    .a16
    .i16
    lda $08
    ora #1
    sta $08
    lda $06
    sta $F4
    lda $10
    bne S6_EnemyAttack__done
    lda $08
    and #$FFFE
    sta $08
    jsl S6_StopMovement
    lda $FC
    bne S6_EnemyAttack__done
    jsl S6_SelectTarget
    lda $FC
    bne S6_EnemyAttack__done
    lda $34
    beq S6_EnemyAttack__idle
    tax
    lda.l $7E0014,x
    sec
    sbc $14
    jsl S6_TargetAbs
    cmp #80
    bcs S6_EnemyAttack__idle
    phd
    lda $36
    tcd
    jsl S6_Random32
    lda $04
    pld
    and #3
    beq S6_EnemyAttack__idle
    stz $FA
    lda $A6
    jsl S6_SetRole
    lda #13
    sta $E6
    bra S6_EnemyAttack__deadline
S6_EnemyAttack__idle:
    .a16
    .i16
    stz $FA
    lda $38
    jsl S6_SetRole
    lda #1
    sta $E6
S6_EnemyAttack__deadline:
    .a16
    .i16
    lda $D0
    clc
    adc #200
    sta $EC
    lda $D2
    adc #0
    sta $EE
S6_EnemyAttack__done:
    .a16
    .i16
    rtl
