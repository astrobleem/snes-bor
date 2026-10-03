; Source ordinary single-attack decision/role driver, opt-in.
; Metadata, not source identity, selects this bounded capability.
; Actor A0 attack role, A2 signed range minimum,A4 signed maximum,A6 walk role.
; A8 nonzero means additional attack/upper/jump/frame-event semantics required.
; C6 authored speed in twentieths; B0 points to signed x/z speed words.
; D8/DA retain subpixel remainders in twentieths. E6:1 enemy,11 prepare,
; 12 attack,13 runoff. RNG remains the shared source stream at world36.
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
    ; Normal campaign program word 14 reserves bit 15 for its explicit
    ; native HP-zero retirement adapter. Remaining feature bits stay
    ; fail-closed; the marker itself must not disable ordinary AI.
    lda $A8
    and #$7FFF
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
    cmp #13
    beq S6_EnemyDecision__select
    jmp S6_EnemyDecision__blocked
S6_EnemyDecision__select:
    .a16
    .i16
    jsl S6_SelectTarget
    lda $FC
    beq S6_EnemyDecision__target_ok
    jmp S6_EnemyDecision__done
S6_EnemyDecision__target_ok:
    lda $34
    bne S6_EnemyDecision__has_target
    jmp S6_EnemyDecision__no_target
S6_EnemyDecision__has_target:
    tax
    lda.l $7E0014,x
    sec
    sbc $14
    beq S6_EnemyDecision__face_fraction
    bmi S6_EnemyDecision__left
    lda #1
    bra S6_EnemyDecision__face
S6_EnemyDecision__face_fraction:
    .a16
    .i16
    lda.l $7E00D8,x
    sec
    sbc $D8
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
    cmp #13
    bne S6_EnemyDecision__not_runoff
    jmp S6_EnemyDecision__runoff
S6_EnemyDecision__not_runoff:
    cmp #11
    bne S6_EnemyDecision__grounded
    jmp S6_EnemyPrepare
S6_EnemyDecision__grounded:
    lda.l $7E0016,x
    sec
    sbc $16
    jsl S6_TargetAbs
    cmp #12
    bcs S6_EnemyDecision__chase
    jsl S6_EnemyInRange
    bcc S6_EnemyDecision__chase
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
    lda $E6
    cmp #11
    bne S6_EnemyDecision__done
    lda #1
    sta $E6
    bra S6_EnemyDecision__done
S6_EnemyDecision__chase:
    .a16
    .i16
    ; Source enemy_choose_move consumes horizontal then depth rand32 only when
    ; stalltime < source time. Horizontal approach is forced beyond 160 px.
    lda.l $7E0014,x
    sec
    sbc $14
    jsl S6_TargetAbs
    sta $AC
    lda $D2
    cmp $EE
    bcs S6_EnemyDecision__check_low_time
    jmp S6_EnemyDecision__move
S6_EnemyDecision__check_low_time:
    bne S6_EnemyDecision__choose
    lda $D0
    cmp $EC
    bne S6_EnemyDecision__check_equal_time
    jmp S6_EnemyDecision__move
S6_EnemyDecision__check_equal_time:
    bcs S6_EnemyDecision__choose
    jmp S6_EnemyDecision__move
S6_EnemyDecision__choose:
    .a16
    .i16
    ldx $B0
    bne S6_EnemyDecision__velocity_bound
    jmp S6_EnemyDecision__movement_binding
S6_EnemyDecision__velocity_bound:
    cpx #$1FF9
    bcc S6_EnemyDecision__velocity_range_ok
    jmp S6_EnemyDecision__movement_binding
S6_EnemyDecision__velocity_range_ok:
    lda #0
    sta.l $7E0000,x
    sta.l $7E0002,x
    sta.l $7E0004,x
    sta.l $7E0006,x
    stz $AE
    phd
    lda $36
    tcd
    jsl S6_Random32
    lda $04
    and #7
    pld
    sta $AA
    cmp #3
    bcc S6_EnemyDecision__toward
    lda $AC
    cmp #160
    beq S6_EnemyDecision__random_walk
    bcc S6_EnemyDecision__random_walk
    bra S6_EnemyDecision__toward
S6_EnemyDecision__random_walk:
    .a16
    .i16
    lda $AA
    cmp #5
    bcs S6_EnemyDecision__away
    bra S6_EnemyDecision__depth_choice
S6_EnemyDecision__toward:
    .a16
    .i16
    ldx $B0
    lda $C6
    ldy $1A
    bne S6_EnemyDecision__store_x_velocity
    eor #$FFFF
    inc a
    bra S6_EnemyDecision__store_x_velocity
S6_EnemyDecision__away:
    .a16
    .i16
    ldx $B0
    lda $C6
    lsr a
    ldy $1A
    beq S6_EnemyDecision__store_x_velocity
    eor #$FFFF
    inc a
S6_EnemyDecision__store_x_velocity:
    .a16
    .i16
    sta.l $7E0000,x
    lda #0
    sta.l $7E0002,x
    lda #1
    sta $AE
S6_EnemyDecision__depth_choice:
    .a16
    .i16
    phd
    lda $36
    tcd
    jsl S6_Random32
    lda $04
    and #7
    pld
    cmp #2
    bcc S6_EnemyDecision__depth_negative
    cmp #6
    bcs S6_EnemyDecision__depth_positive
    bra S6_EnemyDecision__choose_role
S6_EnemyDecision__depth_negative:
    .a16
    .i16
    ldx $B0
    lda $C6
    lsr a
    eor #$FFFF
    inc a
    sta.l $7E0004,x
    lda #0
    sta.l $7E0006,x
    lda #1
    sta $AE
    bra S6_EnemyDecision__choose_role
S6_EnemyDecision__depth_positive:
    .a16
    .i16
    ldx $B0
    lda $C6
    lsr a
    sta.l $7E0004,x
    lda #0
    sta.l $7E0006,x
    lda #1
    sta $AE
S6_EnemyDecision__choose_role:
    .a16
    .i16
    lda $AE
    beq S6_EnemyDecision__select_idle
    lda $A6
    bra S6_EnemyDecision__set_role
S6_EnemyDecision__select_idle:
    .a16
    .i16
    lda $38
S6_EnemyDecision__set_role:
    .a16
    .i16
    stz $FA
    jsl S6_SetRole
    lda $FC
    beq S6_EnemyDecision__role_ok
    jmp S6_EnemyDecision__done
S6_EnemyDecision__role_ok:
    lda $E4
    cmp $A6
    bne S6_EnemyDecision__set_deadline
    ldx $B0
    lda.l $7E0000,x
    beq S6_EnemyDecision__set_deadline
    bmi S6_EnemyDecision__velocity_left
    lda $1A
    bne S6_EnemyDecision__frame_forward
    bra S6_EnemyDecision__frame_reverse
S6_EnemyDecision__velocity_left:
    .a16
    .i16
    lda $1A
    beq S6_EnemyDecision__frame_forward
S6_EnemyDecision__frame_reverse:
    .a16
    .i16
    lda #$FFFF
    sta $10
    bra S6_EnemyDecision__set_deadline
S6_EnemyDecision__frame_forward:
    .a16
    .i16
    lda #1
    sta $10
S6_EnemyDecision__set_deadline:
    .a16
    .i16
    lda $D0
    clc
    adc #200
    sta $EC
    lda $D2
    adc #0
    sta $EE
S6_EnemyDecision__move:
    .a16
    .i16
    jsl S6_EnemyApplyMovement
    jmp S6_EnemyDecision__done
S6_EnemyDecision__movement_binding:
    .a16
    .i16
    lda #7
    sta $FC
    jmp S6_EnemyDecision__done
S6_EnemyDecision__runoff:
    .a16
    .i16
    ldx $B0
    bne S6_EnemyDecision__runoff_bound
    jmp S6_EnemyDecision__movement_binding
S6_EnemyDecision__runoff_bound:
    cpx #$1FF9
    bcc S6_EnemyDecision__runoff_range_ok
    jmp S6_EnemyDecision__movement_binding
S6_EnemyDecision__runoff_range_ok:
    lda $C6
    lsr a
    ldy $1A
    beq S6_EnemyDecision__runoff_store
    eor #$FFFF
    inc a
S6_EnemyDecision__runoff_store:
    .a16
    .i16
    sta.l $7E0000,x
    lda #0
    sta.l $7E0002,x
    sta.l $7E0004,x
    sta.l $7E0006,x
    jsl S6_EnemyApplyMovement
    lda $D2
    cmp $EE
    bcs S6_EnemyDecision__runoff_low_time
    jmp S6_EnemyDecision__done
S6_EnemyDecision__runoff_low_time:
    bne S6_EnemyDecision__runoff_expired
    lda $D0
    cmp $EC
    bne S6_EnemyDecision__runoff_equal_time
    jmp S6_EnemyDecision__done
S6_EnemyDecision__runoff_equal_time:
    bcs S6_EnemyDecision__runoff_expired
    jmp S6_EnemyDecision__done
S6_EnemyDecision__runoff_expired:
    .a16
    .i16
    lda #1
    sta $E6
    jmp S6_EnemyDecision__done
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

; Apply the retained source x/z velocity once per enemy-think callback. The
; model linker stores speed in twentieths; integer actor coordinates retain a
; signed twentieth-pixel remainder, preserving exact authored decimal speeds.
S6_EnemyApplyMovement:
    rep #$30
    .a16
    .i16
    lda $B0
    beq S6_EnemyApplyMovement__binding
    cmp #$1FF9
    bcs S6_EnemyApplyMovement__binding
    ldx $B0
    lda.l $7E0004,x
    beq S6_EnemyApplyMovement__x
    lda $16
    cmp #160
    bcs S6_EnemyApplyMovement__z_high
    lda $C6
    lsr a
    sta.l $7E0004,x
    lda #0
    sta.l $7E0006,x
    bra S6_EnemyApplyMovement__x
S6_EnemyApplyMovement__z_high:
    .a16
    .i16
    cmp #233
    bcc S6_EnemyApplyMovement__x
    lda $C6
    lsr a
    eor #$FFFF
    inc a
    sta.l $7E0004,x
    lda #0
    sta.l $7E0006,x
S6_EnemyApplyMovement__x:
    .a16
    .i16
    stz $90
    stz $92
    stz $94
    jsl S6_EnemyApplyAxis
    lda #2
    sta $90
    sta $92
    lda #4
    sta $94
    jsl S6_EnemyApplyAxis
    rtl
S6_EnemyApplyMovement__binding:
    .a16
    .i16
    lda #7
    sta $FC
    rtl

; Generic axis accumulator. $90=remainder offset, $92=position offset,
; $94=velocity offset in the eight-byte B0 block. Divide toward zero, then
; keep the canonical integer position truncated toward zero (as BOR does for
; collision/raster coordinates).
S6_EnemyApplyAxis:
    .a16
    .i16
    lda $B0
    clc
    adc $94
    tax
    lda.l $7E0000,x
    sta $96
    bne S6_EnemyApplyAxis__velocity
    jmp S6_EnemyApplyAxis__done
S6_EnemyApplyAxis__velocity:
    ldx $90
    lda $D8,x
    clc
    adc $96
    sta $AA
    bmi S6_EnemyApplyAxis__negative
    stz $AE
S6_EnemyApplyAxis__positive_loop:
    .a16
    .i16
    cmp #20
    bcc S6_EnemyApplyAxis__positive_remainder
    sec
    sbc #20
    inc $AE
    bra S6_EnemyApplyAxis__positive_loop
S6_EnemyApplyAxis__positive_remainder:
    .a16
    .i16
    sta $AC
    ; A has direct-page,X but not direct-page,Y. Use the selected 0/2 field
    ; offset in X so position math remains relative to the active actor D.
    ldx $92
    lda $AE
    clc
    adc $14,x
    sta $14,x
    lda $AC
    sta $98
    bra S6_EnemyApplyAxis__normalize
S6_EnemyApplyAxis__negative:
    .a16
    .i16
    eor #$FFFF
    inc a
    stz $AE
S6_EnemyApplyAxis__negative_loop:
    .a16
    .i16
    cmp #20
    bcc S6_EnemyApplyAxis__negative_remainder
    sec
    sbc #20
    inc $AE
    bra S6_EnemyApplyAxis__negative_loop
S6_EnemyApplyAxis__negative_remainder:
    .a16
    .i16
    sta $AC
    ldx $92
    lda $AE
    eor #$FFFF
    inc a
    clc
    adc $14,x
    sta $14,x
    lda $AC
    eor #$FFFF
    inc a
    sta $98
S6_EnemyApplyAxis__normalize:
    .a16
    .i16
    ldx $92
    lda $14,x
    bmi S6_EnemyApplyAxis__negative_position
    beq S6_EnemyApplyAxis__store_remainder
    lda $98
    bpl S6_EnemyApplyAxis__store_remainder
    lda $14,x
    dec a
    sta $14,x
    lda $98
    clc
    adc #20
    sta $98
    bra S6_EnemyApplyAxis__store_remainder
S6_EnemyApplyAxis__negative_position:
    .a16
    .i16
    lda $98
    bmi S6_EnemyApplyAxis__store_remainder
    ldx $92
    lda $14,x
    inc a
    sta $14,x
    lda $98
    sec
    sbc #20
    sta $98
S6_EnemyApplyAxis__store_remainder:
    .a16
    .i16
    ldx $90
    lda $98
    sta $D8,x
S6_EnemyApplyAxis__done:
    .a16
    .i16
    rtl
