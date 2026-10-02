; SOURCE_EXACT grounded ordinary-opponent damage slice, not whole damage ABI.
; Same D/DBR/width/policy contract as actor_source_scheduler.pasm.
; Target: F2 type=2 enemy, F0 signed16 HP,14 x,1A direction,08 attack flags.
; Inputs: A signed16 force, X source drop, Y source attack type;
; B8 attacker x, C2 explicit inair, C4 linked. 3A pain role ID supplied by linker.
; Outputs: B4/B6 pain deadline32, E6 driver=2 (pain), HP/direction/role/flags.
; BA/BC/BE request scratch, C0 proposed HP. FC diagnostics:
; 4 unbound lifecycle (drop/blast/air/link),5 damage numeric range/type.
; Normal's explicit compatibility program marker permits grounded lethal
; hits to publish HP=0 and retire at the existing campaign slot seam.
; Unsupported cases FAIL BEFORE target mutation. They do not use compat damage.
; The source full callback also owns score/opponent/SFX/world dependencies;
; caller must bind these before certifying a complete actor or damage event.
; Generic callback dispatch. Inputs match the existing enemy routine;
; player callback additionally receives attacker source type at76.
S6_GroundDamage:
    rep #$30
    .a16
    .i16
    pha
    lda $F2
    cmp #1
    beq S6_GroundDamage__player
    pla
    jml S6_EnemyGroundDamage
S6_GroundDamage__player:
    .a16
    .i16
    pla
    jml S6_PlayerGroundDamage

; Pinned player_takedamage, nonlethal/unlinked/grounded 16-bit-xdir slice.
; 74 explicit jumping flag (independent of altitude),76 attacker type.
; E6=7 means player_pain, not enemy recovery. Caller owns opponent/effects.
; The supported source adapter stores xdir as a signed 16-bit speed with a
; zero upper word. player_takedamage negates it; unsupported upper-word and
; minimum-integer values fail before any gameplay mutation.
S6_PlayerGroundDamage:
    rep #$30
    .a16
    .i16
    sta $BA
    stx $BC
    sty $BE
    jsl S6_CheckPolicy
    bcc S6_PlayerGroundDamage__policy
    rtl
S6_PlayerGroundDamage__policy:
    .a16
    .i16
    lda $18
    eor #$8000
    cmp #$7F06              ; signed a >= PIT_DEPTH(-250)
    bcs S6_PlayerGroundDamage__above_pit
    jmp S6_PlayerGroundDamage__lifecycle
S6_PlayerGroundDamage__above_pit:
    .a16
    .i16
    lda $BA
    bpl S6_PlayerGroundDamage__nonnegative_force
    jmp S6_PlayerGroundDamage__range
S6_PlayerGroundDamage__nonnegative_force:
    .a16
    .i16
    lda $76
    cmp #2
    beq S6_PlayerGroundDamage__force
    cmp #1
    beq S6_PlayerGroundDamage__player_type_ok
    jmp S6_PlayerGroundDamage__range
S6_PlayerGroundDamage__player_type_ok:
    lsr $BA
S6_PlayerGroundDamage__force:
    .a16
    .i16
    lda $F0
    sec
    sbc $BA
    bvc S6_PlayerGroundDamage__no_overflow
    jmp S6_PlayerGroundDamage__range
S6_PlayerGroundDamage__no_overflow:
    sta $C0
    bpl S6_PlayerGroundDamage__hp_nonnegative
    jmp S6_PlayerGroundDamage__lifecycle
S6_PlayerGroundDamage__hp_nonnegative:
    bne S6_PlayerGroundDamage__nonlethal
    jmp S6_PlayerGroundDamage__lethal
S6_PlayerGroundDamage__nonlethal:
    lda $BC
    ora $C2
    ora $C4
    beq S6_PlayerGroundDamage__not_lifecycle
    jmp S6_PlayerGroundDamage__lifecycle
S6_PlayerGroundDamage__not_lifecycle:
    lda $BE
    cmp #1
    bne S6_PlayerGroundDamage__not_damage_type
    jmp S6_PlayerGroundDamage__lifecycle
S6_PlayerGroundDamage__not_damage_type:
    ldx $B0
    bne S6_PlayerGroundDamage__velocity_pointer
    jmp S6_PlayerGroundDamage__range
S6_PlayerGroundDamage__velocity_pointer:
    cpx #$1FF9
    bcc S6_PlayerGroundDamage__velocity_window
    jmp S6_PlayerGroundDamage__range
S6_PlayerGroundDamage__velocity_window:
    lda.l $7E0002,x
    beq S6_PlayerGroundDamage__velocity_upper_zero
    jmp S6_PlayerGroundDamage__range
S6_PlayerGroundDamage__velocity_upper_zero:
    lda.l $7E0000,x
    cmp #$8000
    bne S6_PlayerGroundDamage__velocity_negatable
    jmp S6_PlayerGroundDamage__range
S6_PlayerGroundDamage__velocity_negatable:
    ; All admission checks precede changes to gameplay state.
    ldx $B0
    lda.l $7E0000,x
    eor #$FFFF
    inc a
    sta.l $7E0000,x
    lda $D0
    clc
    adc #40
    sta $B4
    lda $D2
    adc #0
    sta $B6
    lda $14
    sec
    sbc $B8
    bvc S6_PlayerGroundDamage__sign
    eor #$8000
S6_PlayerGroundDamage__sign:
    .a16
    .i16
    bmi S6_PlayerGroundDamage__right
    lda #0
    bra S6_PlayerGroundDamage__face
S6_PlayerGroundDamage__right:
    .a16
    .i16
    lda #1
S6_PlayerGroundDamage__face:
    .a16
    .i16
    sta $1A
    lda $08
    and #$FFFE
    sta $08
    stz $74
    lda $C0
    sta $F0
    lda #7
    sta $E6
    lda #1
    sta $FA
    lda $3A
    jsl S6_SetRole
    stz $FA
    rtl
S6_PlayerGroundDamage__lethal:
    .a16
    .i16
    lda $A8
    and #$8000
    beq S6_PlayerGroundDamage__lifecycle
    lda $BC
    ora $C2
    ora $C4
    bne S6_PlayerGroundDamage__lifecycle
    lda $BE
    cmp #1
    beq S6_PlayerGroundDamage__lifecycle
    lda #0
    sta $F0
    sta $F6
    stz $74
    lda $08
    and #$FFFE
    sta $08
    rtl
S6_PlayerGroundDamage__range:
    .a16
    .i16
    lda #5
    sta $FC
    rtl
S6_PlayerGroundDamage__lifecycle:
    .a16
    .i16
    lda #4
    sta $FC
    rtl

S6_EnemyGroundDamage:
    rep #$30
    .a16
    .i16
    sta $BA
    stx $BC
    sty $BE
    jsl S6_CheckPolicy
    bcc S6_EnemyGroundDamage__policy
    rtl
S6_EnemyGroundDamage__policy:
    .a16
    .i16
    lda $F2
    cmp #2
    beq S6_EnemyGroundDamage__enemy_type
    jmp S6_EnemyGroundDamage__range
S6_EnemyGroundDamage__enemy_type:
    lda $F0
    sec
    sbc $BA
    bvc S6_EnemyGroundDamage__no_overflow
    jmp S6_EnemyGroundDamage__range
S6_EnemyGroundDamage__no_overflow:
    sta $C0
    bmi S6_EnemyGroundDamage__lethal
    beq S6_EnemyGroundDamage__lethal
    lda $BC
    ora $C2
    ora $C4
    beq S6_EnemyGroundDamage__not_lifecycle
    jmp S6_EnemyGroundDamage__lifecycle
S6_EnemyGroundDamage__not_lifecycle:
    lda $BE
    cmp #1
    beq S6_EnemyGroundDamage__lifecycle
    ; Pinned enemy callback treats other attack kinds alike in this branch.
    lda $D0
    clc
    adc #40
    sta $B4
    lda $D2
    adc #0
    sta $B6
    lda $14
    cmp $B8
    beq S6_EnemyGroundDamage__direction
    ; Signed coordinate comparison, preserving overflow correctly.
    sec
    sbc $B8
    bvc S6_EnemyGroundDamage__sign
    eor #$8000
S6_EnemyGroundDamage__sign:
    .a16
    .i16
    bpl S6_EnemyGroundDamage__left
    lda #1
    bra S6_EnemyGroundDamage__store_direction
S6_EnemyGroundDamage__left:
    .a16
    .i16
    lda #0
S6_EnemyGroundDamage__store_direction:
    .a16
    .i16
    sta $1A
S6_EnemyGroundDamage__direction:
    .a16
    .i16
    lda $08
    and #$FFFE
    sta $08
    lda $C0
    sta $F0
    lda #2
    sta $E6
    lda #1
    sta $FA
    lda $3A
    jsl S6_SetRole
    stz $FA
    rtl
S6_EnemyGroundDamage__lethal:
    .a16
    .i16
    lda $A8
    and #$8000
    beq S6_EnemyGroundDamage__lifecycle
    lda $BC
    ora $C2
    ora $C4
    bne S6_EnemyGroundDamage__lifecycle
    lda $BE
    cmp #1
    beq S6_EnemyGroundDamage__lifecycle
    ; The source ordinary-enemy death callback consumes one random lift value
    ; on the lethal path. Keep that stream position even though Normal's
    ; production entity contract uses BOR's HP-zero soft-kill renderer and
    ; retires the resident row at the next acknowledged snapshot boundary.
    phd
    lda $36
    tcd
    jsl S6_Random32
    jsl S6_RandomModulo1000
    pld
    lda #0
    sta $F0
    sta $F6
    stz $08
    rtl
S6_EnemyGroundDamage__range:
    .a16
    .i16
    lda #5
    sta $FC
    rtl
S6_EnemyGroundDamage__lifecycle:
    .a16
    .i16
    lda #4
    sta $FC
    rtl

; Grounded pain/rise completion. 38 idle role ID, E6 driver2 pain/3 rise;
; C4 explicit linked state. Numeric velocity storage is independently owned:
; B0 points to eight bytes (xdir32,zdir32); zero is exact in supported formats.
; Driver1 ordinary enemy is returned to caller; this routine never invents AI.
S6_RecoveryThink:
    rep #$30
    .a16
    .i16
    jsl S6_CheckPolicy
    bcs S6_RecoveryThink__done
    lda $10
    bne S6_RecoveryThink__done
    lda $C4
    bne S6_RecoveryThink__blocked
    lda $E6
    cmp #2
    beq S6_RecoveryThink__idle
    cmp #3
    bne S6_RecoveryThink__blocked
    jsl S6_StopMovement
    lda $FC
    bne S6_RecoveryThink__done
S6_RecoveryThink__idle:
    .a16
    .i16
    lda #1
    sta $E6
    stz $FA
    lda $38
    jsl S6_SetRole
S6_RecoveryThink__done:
    .a16
    .i16
    rtl
S6_RecoveryThink__blocked:
    .a16
    .i16
    lda #4
    sta $FC
    rtl

S6_StopMovement:
    rep #$30
    .a16
    .i16
    ldx $B0
    beq S6_StopMovement__unbound
    cpx #$1FF9
    bcs S6_StopMovement__unbound
    lda #0
    sta.l $7E0000,x
    sta.l $7E0002,x
    sta.l $7E0004,x
    sta.l $7E0006,x
    rtl
S6_StopMovement__unbound:
    .a16
    .i16
    lda #7
    sta $FC
    rtl

; Source enemy_drop/enemy_lie/suicide scheduling. Physics/landing decides
; when to enter LIE and sets EC stall deadline; this does not infer a role
; from altitude. E6:1 enemy,2 pain,3 rise,4 lie,5 suicide,6 initial drop.
; B2 blink,3C source rise-role ID, C2 explicit source inair predicate.
S6_GroundLifecycle:
    rep #$30
    .a16
    .i16
    jsl S6_CheckPolicy
    bcs S6_GroundLifecycle__done
    lda $E6
    cmp #5
    beq S6_GroundLifecycle__remove
    cmp #6
    beq S6_GroundLifecycle__drop
    cmp #4
    beq S6_GroundLifecycle__lie
    lda #8
    sta $FC
S6_GroundLifecycle__done:
    .a16
    .i16
    rtl
S6_GroundLifecycle__remove:
    .a16
    .i16
    stz $F6
    rtl
S6_GroundLifecycle__drop:
    .a16
    .i16
    lda $C2
    bne S6_GroundLifecycle__done
    lda #1
    sta $E6
    lda $F0
    beq S6_GroundLifecycle__remove
    bmi S6_GroundLifecycle__remove
    rtl
S6_GroundLifecycle__lie:
    .a16
    .i16
    lda $F0
    beq S6_GroundLifecycle__dead
    bmi S6_GroundLifecycle__dead
    lda $D2
    cmp $EE
    bcc S6_GroundLifecycle__done
    bne S6_GroundLifecycle__rise
    lda $D0
    cmp $EC
    bcc S6_GroundLifecycle__done
S6_GroundLifecycle__rise:
    .a16
    .i16
    jsl S6_StopMovement
    lda $FC
    bne S6_GroundLifecycle__done
    stz $FA
    lda $3C
    jsl S6_SetRole
    lda #3
    sta $E6
    rtl
S6_GroundLifecycle__dead:
    .a16
    .i16
    lda #5
    sta $E6
    lda #1
    sta $B2
    lda $D0
    clc
    adc #400
    sta $E8
    lda $D2
    adc #0
    sta $EA
    rtl
