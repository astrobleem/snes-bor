; SOURCE_EXACT pairwise hit resolver, opt-in CPU fixture ABI.
; Attacker D: S5 geometry context plus 34 target DP(u16),36 world RNG/attack
; context DP(u16), DC/DE current attack ID32. Target: D8/DA hit-by ID32,
; B4/B6 pain deadline32, F0 HP,F2 source type, current frame pointer30.
; World context offset20/22: shared new-attack ID32, initialized1.
; All contexts must be separate, aligned bank0 WRAM mirrors below $2000.
; Host calls on source collision-pass parity and binds every world target.
; Grounded enemy and bounded nonlethal player damage callbacks are linked.
; Other callbacks/lifecycle and upper-counter pass remain explicit blockers.
; Required S6_HitEffects hook owns hit flash, score/opponent and audio effects;
; a fixture event sink is not a production effects certificate.
S6_TryHitOne:
    rep #$30
    .a16
    .i16
    jsl S6_CheckPolicy
    bcc S6_TryHitOne__policy
    rtl
S6_TryHitOne__policy:
    .a16
    .i16
    jsl S5_ActivateAttack
    lda $0A
    bne S6_TryHitOne__active
    stz $DC
    stz $DE
    rtl
S6_TryHitOne__active:
    .a16
    .i16
    lda $34
    ora $36
    and #$E0FF
    beq S6_TryHitOne__addresses
    lda #6
    sta $FC
    rtl
S6_TryHitOne__addresses:
    .a16
    .i16
    ; Callback scope is explicit, rather than defaulting an enemy hit to
    ; accepted fixed damage or another source model's behavior.
    ldx $34
    lda.l $7E00F2,x
    cmp #1
    beq S6_TryHitOne__player_target
    cmp #2
    beq S6_TryHitOne__target_type
    lda #5
    sta $FC
    rtl
S6_TryHitOne__player_target:
    .a16
    .i16
    lda $08
    and #2
    bne S6_TryHitOne__identity
    lda $F2
    cmp #1
    beq S6_TryHitOne__identity
    cmp #2
    beq S6_TryHitOne__identity
    rtl
S6_TryHitOne__target_type:
    .a16
    .i16
    lda $08
    and #2
    bne S6_TryHitOne__identity
    lda $F2
    cmp #1
    beq S6_TryHitOne__identity
    rtl
S6_TryHitOne__identity:
    .a16
    .i16
    lda $DC
    ora $DE
    bne S6_TryHitOne__have_id
    ldx $36
    lda.l $7E0020,x
    inc a
    sta.l $7E0020,x
    bne S6_TryHitOne__read_id
    lda.l $7E0022,x
    inc a
    sta.l $7E0022,x
    bne S6_TryHitOne__read_id
    lda #1
    sta.l $7E0020,x
S6_TryHitOne__read_id:
    .a16
    .i16
    lda.l $7E0020,x
    sta $DC
    lda.l $7E0022,x
    sta $DE
S6_TryHitOne__have_id:
    .a16
    .i16
    ldx $34
    lda.l $7E00F6,x
    beq S6_TryHitOne__done
    lda.l $7E00D8,x
    cmp $DC
    bne S6_TryHitOne__pain
    lda.l $7E00DA,x
    cmp $DE
    beq S6_TryHitOne__done
S6_TryHitOne__pain:
    .a16
    .i16
    lda.l $7E00B6,x
    cmp $D2
    bcc S6_TryHitOne__geometry
    bne S6_TryHitOne__done
    lda.l $7E00B4,x
    cmp $D0
    bcs S6_TryHitOne__done
S6_TryHitOne__geometry:
    .a16
    .i16
    tdc
    cmp $34
    beq S6_TryHitOne__done
    stz $24
    lda.l $7E0014,x
    sta $1C
    lda.l $7E0016,x
    sta $1E
    lda.l $7E0018,x
    sta $20
    lda.l $7E001A,x
    sta $22
    lda.l $7E0030,x
    sta $26
    lda.l $7E0032,x
    sta $28
    jsl S6_SourceCollision
    lda $2A
    beq S6_TryHitOne__done
    jmp S6_TryHitOne__damage
S6_TryHitOne__done:
    .a16
    .i16
    rtl
S6_TryHitOne__damage:
    .a16
    .i16
    ldx $34
    lda $D0
    sta.l $7E00D0,x
    lda $D2
    sta.l $7E00D2,x
    lda $14
    sta.l $7E00B8,x
    lda $F2
    sta.l $7E0076,x
    lda $4C
    pha
    lda $4E
    pha
    lda $50
    pha
    lda $34
    phd
    tcd
    ; Saved D must remain on top for PLD, so retrieve arguments via stack.
    lda $05,s
    tax
    lda $03,s
    tay
    lda $07,s
    jsl S6_GroundDamage
    pld
    pla
    pla
    pla
    ldx $34
    lda.l $7E00FC,x
    sta $FC
    bne S6_TryHitOne__done
    lda $DC
    sta.l $7E00D8,x
    lda $DE
    sta.l $7E00DA,x
    jsl S6_HitEffects
    rtl

; S5 owns60..7F as transient target-frame staging. The scheduler also keeps
; persistent host/lifecycle fields70..7F between calls. Preserve that complete
; overlap explicitly at the interface; never let a target's attack geometry
; become the attacker's slot handle, displayed HP or lifecycle state.
; Source collision only consumes the target's header/body60..6B internally.
S6_SourceCollision:
    rep #$30
    .a16
    .i16
    ldx #14
S6_SourceCollision__save:
    .a16
    .i16
    lda $70,x
    pha
    dex
    dex
    bpl S6_SourceCollision__save
    jsl S5_CheckCollision
    ldx #0
S6_SourceCollision__restore:
    .a16
    .i16
    pla
    sta $70,x
    inx
    inx
    cpx #16
    bne S6_SourceCollision__restore
    rtl
