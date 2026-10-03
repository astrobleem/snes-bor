; S5 ABI v1. Also included by actor_behavior.pasm; RAM ownership belongs to
; each caller. Isolated fixtures use separately reserved contexts.
; Native 65816, D = caller-owned 256-byte bank-0 WRAM context, DBR=0,
; decimal clear. Public calls JSL/RTL, clobber A/X/Y/P, return A16/I16.
; Host serializes calls; scratch/context must not be shared with interrupts.
; All pointers are 24-bit. Frame tables must fit in one 64KB bank.
; No model names, role numbers, production entity offsets or profile guessing.
;
; DP: 00 table ptr(3), 04 count, 06 frame, 08 flags(bit0 attacking,
; bit1 projectile), 0A active, 0C valid, 0E remaining ticks, 10 animating,
; 12 loop, 14 attacker x, 16 z, 18 altitude, 1A direction(0 left),
; 1C target x, 1E z, 20 altitude, 22 direction, 24 same-entity,
; 26 target frame ptr(3), 2A hit, 2C error, 30 current frame ptr(3).
; 40 loaded source frame, 60 loaded target frame, 80/88 world rectangles,
; 90..9F scratch. Geometry inputs/results must fit signed16 without overflow.
; Packed 32-byte frame (words): delay in 200Hz ticks, vulnerable,
; body L/T/R/B, force, drop, attack type, attack L/T/R/B, 3 reserved words.
; Collision reports overlap only: no target type filter, attack-ID dedupe,
; damage callback, HP, hit spark, counterattack or gameplay lifecycle binding.
;
; Drift uses signed32 units of 1/2560 pixel (source tenths exact).
; A0 x, A4 velocity, A8 advancex, AC source speed; B0 authored x (s16),
; B2 source type (0 none), B4 has walk, B6 alive, B8 driver (1 drift),
; BA direction, BC damage-callback binding (zero), BE random03 (u16).
; Host S5_HostRandom03 writes BE in [0,7680), preserves D/DBR, A16/I16.
; It is called once when binding a new eligible actor, never on drift ticks.
; This numeric ABI is NOT a claim of bit-identical BOR IEEE-float/RNG output.
; C0..C7 drift scratch. Caller initializes whole context before first use.
; D0/D2 logical absolute time (u32), D4/D6 nextanim (u32). Begin schedules
; nextanim=now+delay; Tick increments now once and advances only on equality.
; E0 policy: 1 SOURCE_EXACT, 2 explicit ACCEPTED_COMPAT fixture descriptors.
; E2 collision: 0 source boxes, 1 accepted fixed extents (requires policy 2).
; Clock ownership is external: source ticks=200Hz; accepted ticks=host clock.
; This comparison control does not replace the immutable accepted engine.

S5_LoadFrame:
    rep #$30
    .a16
    .i16
    stz $0A
    stz $0C
    stz $2C
    lda $E0
    cmp #1
    beq S5_LoadFrame__policy
    cmp #2
    bne S5_LoadFrame__bad
S5_LoadFrame__policy:
    .a16
    .i16
    lda $06
    cmp $04
    bcs S5_LoadFrame__bad
    ; Maximum count 2048 keeps index*32 in a word. Generator also checks
    ; table extent, so addition cannot cross a bank or wrap into MMIO.
    lda $04
    cmp #2049
    bcs S5_LoadFrame__bad
    lda $06
    asl a
    asl a
    asl a
    asl a
    asl a
    clc
    adc $00
    bcs S5_LoadFrame__bad
    sta $30
    lda $02
    sta $32
    ldy #0
    ldx #0
S5_LoadFrame__copy:
    .a16
    .i16
    lda [$30],y
    sta $40,x
    iny
    iny
    inx
    inx
    cpx #32
    bne S5_LoadFrame__copy
    lda #1
    sta $0C
    rtl
S5_LoadFrame__bad:
    .a16
    .i16
    lda #1
    sta $2C
    ldx #30
S5_LoadFrame__clear:
    .a16
    .i16
    stz $40,x
    dex
    dex
    bpl S5_LoadFrame__clear
    rtl

S5_ActivateAttack:
    rep #$30
    .a16
    .i16
    stz $0A
    lda $0C
    beq S5_ActivateAttack__done
    lda $08
    and #3
    beq S5_ActivateAttack__done
    lda $4C
    beq S5_ActivateAttack__done
    lda #1
    sta $0A
S5_ActivateAttack__done:
    .a16
    .i16
    rtl

; Begin after setting table/count/frame/loop. Advance exactly once for each
; logical 200Hz source tick. Begin occurs after this tick's animation phase;
; same-tick behavior/animation dispatch ordering needs a host binding.
; Zero delay retains nextanim==entry time, never underflows a byte to 255.
S5_AnimationBegin:
    rep #$30
    .a16
    .i16
    jsl S5_LoadFrame
    lda $0C
    sta $10
    lda $40
    sta $0E
    clc
    adc $D0
    sta $D4
    lda $D2
    adc #0
    sta $D6
    jsl S5_ActivateAttack
    rtl
S5_AnimationTick:
    rep #$30
    .a16
    .i16
    inc $D0
    bne S5_AnimationTick__time
    inc $D2
S5_AnimationTick__time:
    .a16
    .i16
    lda $10
    beq S5_AnimationTick__done
    lda $0E
    beq S5_AnimationTick__deadline
    dec $0E
S5_AnimationTick__deadline:
    .a16
    .i16
    lda $D2
    cmp $D6
    bne S5_AnimationTick__done
    lda $D0
    cmp $D4
    bne S5_AnimationTick__done
    lda $06
    inc a
    cmp $04
    bcc S5_AnimationTick__frame
    lda $12
    bne S5_AnimationTick__loop
    stz $10
    bra S5_AnimationTick__done
S5_AnimationTick__loop:
    .a16
    .i16
    lda #0
S5_AnimationTick__frame:
    .a16
    .i16
    sta $06
    jsl S5_AnimationBegin
S5_AnimationTick__done:
    .a16
    .i16
    rtl

S5_CheckCollision:
    rep #$30
    .a16
    .i16
    stz $2A
    lda $0A
    beq S5_CheckCollision__reject
    lda $24
    bne S5_CheckCollision__reject
    lda $E2
    beq S5_CheckCollision__source
    cmp #1
    bne S5_CheckCollision__reject
    lda $E0
    cmp #2
    bne S5_CheckCollision__reject
    jsl S5_CompatCollision
    rtl
S5_CheckCollision__source:
    .a16
    .i16
    lda $16
    sec
    sbc $1E
    bpl S5_CheckCollision__depth
    eor #$FFFF
    inc a
S5_CheckCollision__depth:
    .a16
    .i16
    cmp #13
    bcs S5_CheckCollision__reject
    ldy #0
    ldx #0
S5_CheckCollision__copy:
    .a16
    .i16
    lda [$26],y
    sta $60,x
    iny
    iny
    inx
    inx
    cpx #32
    bne S5_CheckCollision__copy
    lda $62
    beq S5_CheckCollision__reject
    ; Transform either box through one helper (X source, Y destination).
    lda $14
    sta $90
    lda $16
    sec
    sbc $18
    sta $92
    lda $1A
    sta $94
    ldx #$52
    ldy #$80
    jsr S5_TransformBox
    lda $1C
    sta $90
    lda $1E
    sec
    sbc $20
    sta $92
    lda $22
    sta $94
    ldx #$64
    ldy #$88
    jsr S5_TransformBox
    bra S5_CheckCollision__overlap
S5_CheckCollision__reject:
    .a16
    .i16
    rtl
S5_CheckCollision__overlap:
    .a16
    .i16
    ; Signed inclusive comparisons via sign-bit bias. A > B rejects.
    lda $8C
    eor #$8000
    sta $96
    lda $80
    eor #$8000
    cmp $96
    beq S5_CheckCollision__x2
    bcs S5_CheckCollision__reject
S5_CheckCollision__x2:
    .a16
    .i16
    lda $84
    eor #$8000
    sta $96
    lda $88
    eor #$8000
    cmp $96
    beq S5_CheckCollision__y1
    bcs S5_CheckCollision__reject
S5_CheckCollision__y1:
    .a16
    .i16
    lda $8E
    eor #$8000
    sta $96
    lda $82
    eor #$8000
    cmp $96
    beq S5_CheckCollision__y2
    bcs S5_CheckCollision__reject
S5_CheckCollision__y2:
    .a16
    .i16
    lda $86
    eor #$8000
    sta $96
    lda $8A
    eor #$8000
    cmp $96
    beq S5_CheckCollision__hit
    bcs S5_CheckCollision__reject
S5_CheckCollision__hit:
    .a16
    .i16
    lda #1
    sta $2A
    rtl

; Explicit accepted-control geometry only; callers supply projected y=z-a.
S5_CompatCollision:
    rep #$30
    .a16
    .i16
    lda $14
    sec
    sbc $1C
    bpl S5_CompatCollision__x
    eor #$FFFF
    inc a
S5_CompatCollision__x:
    .a16
    .i16
    cmp #32
    bcs S5_CompatCollision__done
    lda $1E
    sec
    sbc $20
    sta $96
    lda $16
    sec
    sbc $18
    sec
    sbc $96
    bpl S5_CompatCollision__y
    eor #$FFFF
    inc a
S5_CompatCollision__y:
    .a16
    .i16
    cmp #64
    bcs S5_CompatCollision__done
    lda #1
    sta $2A
S5_CompatCollision__done:
    .a16
    .i16
    rtl

; DP indexed source. Destination indirect through $98 because 65816 has
; no direct-page,Y STA. Host DBR=0 and D is a low-WRAM context.
S5_TransformBox:
    .a16
    .i16
    tya
    sta $98
    tdc
    clc
    adc $98
    sta $98
    ldy #0
    lda $94
    beq S5_TransformBox__left
    lda $00,x
    clc
    adc $90
    sta ($98),y
    ldy #4
    lda $04,x
    clc
    adc $90
    sta ($98),y
    bra S5_TransformBox__vertical
S5_TransformBox__left:
    .a16
    .i16
    lda $90
    sec
    sbc $04,x
    sta ($98),y
    ldy #4
    lda $90
    sec
    sbc $00,x
    sta ($98),y
S5_TransformBox__vertical:
    .a16
    .i16
    ldy #2
    lda $02,x
    clc
    adc $92
    sta ($98),y
    ldy #6
    lda $06,x
    clc
    adc $92
    sta ($98),y
    rts

S5_DriftBind:
    rep #$30
    .a16
    .i16
    lda $E0
    cmp #1
    bne S5_DriftBind__reject
    lda $B8
    bne S5_DriftBind__done
    lda $B2
    bne S5_DriftBind__reject
    lda $B4
    beq S5_DriftBind__reject
    jsl S5_HostRandom03
    lda $BE
    cmp #7680
    bcs S5_DriftBind__reject
    clc
    adc $AC
    sta $A4
    lda $AE
    adc #0
    sta $A6
    lda #1
    sta $BA
    lda $B0
    bmi S5_DriftBind__activate
    cmp #160
    bcc S5_DriftBind__activate
    stz $BA
    lda #0
    sec
    sbc $A4
    sta $A4
    lda #0
    sbc $A6
    sta $A6
S5_DriftBind__activate:
    .a16
    .i16
    lda #1
    sta $B6
    sta $B8
    stz $08
    stz $0A
    stz $BC
S5_DriftBind__done:
    .a16
    .i16
    rtl
S5_DriftBind__reject:
    .a16
    .i16
    lda #2
    sta $2C
    rtl

; One call per THINK_SPEED=2 source ticks (100Hz logical). Removal is a
; returned alive bit, not a production kill/unlink/slot-release callback.
S5_DriftTick:
    rep #$30
    .a16
    .i16
    lda $B8
    cmp #1
    bne S5_DriftTick__done
    lda $B6
    beq S5_DriftTick__done
    ; lower bound = advancex - 80, upper = advancex + 400.
    lda $A8
    sec
    sbc #$2000
    sta $C0
    lda $AA
    sbc #3
    eor #$8000
    sta $C2
    lda $A2
    eor #$8000
    cmp $C2
    bcc S5_DriftTick__kill
    bne S5_DriftTick__upper
    lda $A0
    cmp $C0
    bcc S5_DriftTick__kill
S5_DriftTick__upper:
    .a16
    .i16
    lda $A8
    clc
    adc #$A000
    sta $C0
    lda $AA
    adc #15
    eor #$8000
    sta $C2
    lda $A2
    eor #$8000
    cmp $C2
    bcc S5_DriftTick__move
    bne S5_DriftTick__kill
    lda $A0
    cmp $C0
    bcc S5_DriftTick__move
    beq S5_DriftTick__move
S5_DriftTick__kill:
    .a16
    .i16
    stz $B6
    bra S5_DriftTick__done
S5_DriftTick__move:
    .a16
    .i16
    lda $A0
    clc
    adc $A4
    sta $A0
    lda $A2
    adc $A6
    sta $A2
S5_DriftTick__done:
    .a16
    .i16
    rtl
