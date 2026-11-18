.snes
CHAR_ZP_LEN = $85
Screen_PosX = $412420
Spawn_HoleCount = $412422
WBridge_TargetHandle = $412146
WBridge_Policy = $412140
WBridge_Temp78 = $412D20
WBridge_Temp7C = $412D22
WBridge_Temp80 = $412D24
WBridge_Temp82 = $412D26
WBridge_Temp84 = $412D28
WBridge_Temp86 = $412D2A
WBridge_Temp88 = $412D2C
WBridge_Temp8A = $412D2E
WHost_Action = $41214A
WHost_Frame = $412154
WHost_Role = $412156
WHost_InputP1Press = $412020
WHost_InputP1Trigger = $412022
WHost_InputP2Press = $412024
WHost_InputP2Trigger = $412026
WHost_Mode = $411760
WHost_Error = $411764
WHost_PlayerWorldMaxX = $412D06
S7Resident_Owner = $41175E
WHost_FrameEvents = $41176C
WHost_HitEvents = $41176E
CHAR_SELECTED = $B
CHAR_SELECTED_JUMP = $5
Relay_HostScreen_PosX = $7E1601
Relay_HostSpawn_HoleCount = $7E58F0
.bank 37
.org $8000
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
; Host W5_HostRandom03 writes BE in [0,7680), preserves D/DBR, A16/I16.
; It is called once when binding a new eligible actor, never on drift ticks.
; This numeric ABI is NOT a claim of bit-identical BOR IEEE-float/RNG output.
; C0..C7 drift scratch. Caller initializes whole context before first use.
; D0/D2 logical absolute time (u32), D4/D6 nextanim (u32). Begin schedules
; nextanim=now+delay; Tick increments now once and advances only on equality.
; E0 policy: 1 SOURCE_EXACT, 2 explicit ACCEPTED_COMPAT fixture descriptors.
; E2 collision: 0 source boxes, 1 accepted fixed extents (requires policy 2).
; Clock ownership is external: source ticks=200Hz; accepted ticks=host clock.
; This comparison control does not replace the immutable accepted engine.

W5_LoadFrame:
    rep #$30
    .a16
    .i16
    stz $0A
    stz $0C
    stz $2C
    lda $E0
    cmp #1
    beq W5_LoadFrame__policy
    cmp #2
    bne W5_LoadFrame__bad
W5_LoadFrame__policy:
    .a16
    .i16
    lda $06
    cmp $04
    bcs W5_LoadFrame__bad
    ; Maximum count 2048 keeps index*32 in a word. Generator also checks
    ; table extent, so addition cannot cross a bank or wrap into MMIO.
    lda $04
    cmp #2049
    bcs W5_LoadFrame__bad
    lda $06
    asl a
    asl a
    asl a
    asl a
    asl a
    clc
    adc $00
    bcs W5_LoadFrame__bad
    sta $30
    lda $02
    sta $32
    ldy #0
    ldx #0
W5_LoadFrame__copy:
    .a16
    .i16
    lda [$30],y
    sta $40,x
    iny
    iny
    inx
    inx
    cpx #32
    bne W5_LoadFrame__copy
    lda #1
    sta $0C
    rtl
W5_LoadFrame__bad:
    .a16
    .i16
    lda #1
    sta $2C
    ldx #30
W5_LoadFrame__clear:
    .a16
    .i16
    stz $40,x
    dex
    dex
    bpl W5_LoadFrame__clear
    rtl

W5_ActivateAttack:
    rep #$30
    .a16
    .i16
    stz $0A
    lda $0C
    beq W5_ActivateAttack__done
    lda $08
    and #3
    beq W5_ActivateAttack__done
    lda $4C
    beq W5_ActivateAttack__done
    lda #1
    sta $0A
W5_ActivateAttack__done:
    .a16
    .i16
    rtl

; Begin after setting table/count/frame/loop. Advance exactly once for each
; logical 200Hz source tick. Begin occurs after this tick's animation phase;
; same-tick behavior/animation dispatch ordering needs a host binding.
; Zero delay retains nextanim==entry time, never underflows a byte to 255.
W5_AnimationBegin:
    rep #$30
    .a16
    .i16
    jsl W5_LoadFrame
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
    jsl W5_ActivateAttack
    rtl
W5_AnimationTick:
    rep #$30
    .a16
    .i16
    inc $D0
    bne W5_AnimationTick__time
    inc $D2
W5_AnimationTick__time:
    .a16
    .i16
    lda $10
    beq W5_AnimationTick__done
    lda $0E
    beq W5_AnimationTick__deadline
    dec $0E
W5_AnimationTick__deadline:
    .a16
    .i16
    lda $D2
    cmp $D6
    bne W5_AnimationTick__done
    lda $D0
    cmp $D4
    bne W5_AnimationTick__done
    lda $06
    inc a
    cmp $04
    bcc W5_AnimationTick__frame
    lda $12
    bne W5_AnimationTick__loop
    stz $10
    bra W5_AnimationTick__done
W5_AnimationTick__loop:
    .a16
    .i16
    lda #0
W5_AnimationTick__frame:
    .a16
    .i16
    sta $06
    jsl W5_AnimationBegin
W5_AnimationTick__done:
    .a16
    .i16
    rtl

W5_CheckCollision:
    rep #$30
    .a16
    .i16
    stz $2A
    lda $0A
    beq W5_CheckCollision__reject
    lda $24
    bne W5_CheckCollision__reject
    lda $E2
    beq W5_CheckCollision__source
    cmp #1
    bne W5_CheckCollision__reject
    lda $E0
    cmp #2
    bne W5_CheckCollision__reject
    jsl W5_CompatCollision
    rtl
W5_CheckCollision__source:
    .a16
    .i16
    lda $16
    sec
    sbc $1E
    bpl W5_CheckCollision__depth
    eor #$FFFF
    inc a
W5_CheckCollision__depth:
    .a16
    .i16
    cmp #13
    bcs W5_CheckCollision__reject
    ldy #0
    ldx #0
W5_CheckCollision__copy:
    .a16
    .i16
    lda [$26],y
    sta $60,x
    iny
    iny
    inx
    inx
    cpx #32
    bne W5_CheckCollision__copy
    lda $62
    beq W5_CheckCollision__reject
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
    jsr W5_TransformBox
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
    jsr W5_TransformBox
    bra W5_CheckCollision__overlap
W5_CheckCollision__reject:
    .a16
    .i16
    rtl
W5_CheckCollision__overlap:
    .a16
    .i16
    ; Signed inclusive comparisons via sign-bit bias. A > B rejects.
    lda $8C
    eor #$8000
    sta $96
    lda $80
    eor #$8000
    cmp $96
    beq W5_CheckCollision__x2
    bcs W5_CheckCollision__reject
W5_CheckCollision__x2:
    .a16
    .i16
    lda $84
    eor #$8000
    sta $96
    lda $88
    eor #$8000
    cmp $96
    beq W5_CheckCollision__y1
    bcs W5_CheckCollision__reject
W5_CheckCollision__y1:
    .a16
    .i16
    lda $8E
    eor #$8000
    sta $96
    lda $82
    eor #$8000
    cmp $96
    beq W5_CheckCollision__y2
    bcs W5_CheckCollision__reject
W5_CheckCollision__y2:
    .a16
    .i16
    lda $86
    eor #$8000
    sta $96
    lda $8A
    eor #$8000
    cmp $96
    beq W5_CheckCollision__hit
    bcs W5_CheckCollision__reject
W5_CheckCollision__hit:
    .a16
    .i16
    lda #1
    sta $2A
    rtl

; Explicit accepted-control geometry only; callers supply projected y=z-a.
W5_CompatCollision:
    rep #$30
    .a16
    .i16
    lda $14
    sec
    sbc $1C
    bpl W5_CompatCollision__x
    eor #$FFFF
    inc a
W5_CompatCollision__x:
    .a16
    .i16
    cmp #32
    bcs W5_CompatCollision__done
    lda $1E
    sec
    sbc $20
    sta $96
    lda $16
    sec
    sbc $18
    sec
    sbc $96
    bpl W5_CompatCollision__y
    eor #$FFFF
    inc a
W5_CompatCollision__y:
    .a16
    .i16
    cmp #64
    bcs W5_CompatCollision__done
    lda #1
    sta $2A
W5_CompatCollision__done:
    .a16
    .i16
    rtl

; DP indexed source. Destination indirect through $98 because 65816 has
; no direct-page,Y STA. Host DBR=0 and D is a low-WRAM context.
W5_TransformBox:
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
    beq W5_TransformBox__left
    lda $00,x
    clc
    adc $90
    sta ($98),y
    ldy #4
    lda $04,x
    clc
    adc $90
    sta ($98),y
    bra W5_TransformBox__vertical
W5_TransformBox__left:
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
W5_TransformBox__vertical:
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

W5_DriftBind:
    rep #$30
    .a16
    .i16
    lda $E0
    cmp #1
    bne W5_DriftBind__reject
    lda $B8
    bne W5_DriftBind__done
    lda $B2
    bne W5_DriftBind__reject
    lda $B4
    beq W5_DriftBind__reject
    jsl W5_HostRandom03
    lda $BE
    cmp #7680
    bcs W5_DriftBind__reject
    clc
    adc $AC
    sta $A4
    lda $AE
    adc #0
    sta $A6
    lda #1
    sta $BA
    lda $B0
    bmi W5_DriftBind__activate
    cmp #160
    bcc W5_DriftBind__activate
    stz $BA
    lda #0
    sec
    sbc $A4
    sta $A4
    lda #0
    sbc $A6
    sta $A6
W5_DriftBind__activate:
    .a16
    .i16
    lda #1
    sta $B6
    sta $B8
    stz $08
    stz $0A
    stz $BC
W5_DriftBind__done:
    .a16
    .i16
    rtl
W5_DriftBind__reject:
    .a16
    .i16
    lda #2
    sta $2C
    rtl

; One call per THINK_SPEED=2 source ticks (100Hz logical). Removal is a
; returned alive bit, not a production kill/unlink/slot-release callback.
W5_DriftTick:
    rep #$30
    .a16
    .i16
    lda $B8
    cmp #1
    bne W5_DriftTick__done
    lda $B6
    beq W5_DriftTick__done
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
    bcc W5_DriftTick__kill
    bne W5_DriftTick__upper
    lda $A0
    cmp $C0
    bcc W5_DriftTick__kill
W5_DriftTick__upper:
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
    bcc W5_DriftTick__move
    bne W5_DriftTick__kill
    lda $A0
    cmp $C0
    bcc W5_DriftTick__move
    beq W5_DriftTick__move
W5_DriftTick__kill:
    .a16
    .i16
    stz $B6
    bra W5_DriftTick__done
W5_DriftTick__move:
    .a16
    .i16
    lda $A0
    clc
    adc $A4
    sta $A0
    lda $A2
    adc $A6
    sta $A2
W5_DriftTick__done:
    .a16
    .i16
    rtl

; SOURCE_EXACT execution ABI v1, opt-in isolated linker only.
; Reuses S5 frame/box context and 32-byte descriptors, no second source IR.
; D=caller actor context, DBR=0, native A16/I16, decimal clear. JSL/RTL.
; $00 frame pointer24,04 count,06 frame,08 behavior attack flags,10 signed
; animation step(-1/0/+1),12 loop,14/16/18 source integer x/depth/altitude,
; 1A direction. $40 loaded source frame, $90..9F scratch (S5-owned too).
; C8 role table pointer24, CC role count, D0 current world time32 (call input),
; D4 nextanim32, E0 policy (MUST1), E4 current role, E6 behavior-state ID,
; E8 nextthink32, EC stalltime32, F0 health, F2 type, F4 lastanimpos,
; F6 exists, F8 requested role, FA force reset, FC error, FE autokill.
; Role record16: role u16,count u16,frameptr24,loop u8,reserved8.
; Frame record S5 + reserved word28 authored move,30 raster identity index.
; FrameChanged is a required event/render consumer. Think is a separately
; linked source behavior driver. Missing hooks are link errors, not fallback.
; Global host orders gravity -> all thinkers -> all animations -> collisions;
; do not call a per-actor whole update that changes that source pass ordering.

W6_CheckPolicy:
    rep #$30
    .a16
    .i16
    lda $E0
    cmp #1
    beq W6_CheckPolicy__ok
    lda #1
    sta $FC
    sec
    rtl
W6_CheckPolicy__ok:
    .a16
    .i16
    clc
    rtl

; A=requested role, FA=reset. set_anim same role is a no-op; reset_anim
; restarts but intentionally DOES NOT reset lastanimpos (pinned BOR.C).
W6_SetRole:
    rep #$30
    .a16
    .i16
    sta $F8
    jsl W6_CheckPolicy
    bcc W6_SetRole__policy
    rtl
W6_SetRole__policy:
    .a16
    .i16
    lda $FA
    bne W6_SetRole__find
    lda $F8
    cmp $E4
    bne W6_SetRole__find
    rtl
W6_SetRole__find:
    .a16
    .i16
    ldx $CC
    beq W6_SetRole__missing
    ldy #0
W6_SetRole__search:
    .a16
    .i16
    lda [$C8],y
    cmp $F8
    beq W6_SetRole__found
    tya
    clc
    adc #16
    tay
    dex
    bne W6_SetRole__search
W6_SetRole__missing:
    .a16
    .i16
    lda #2
    sta $FC
    rtl
W6_SetRole__found:
    .a16
    .i16
    sta $E4
    iny
    iny
    lda [$C8],y
    sta $04
    iny
    iny
    lda [$C8],y
    sta $00
    iny
    iny
    lda [$C8],y
    and #$00FF
    sta $02
    iny
    lda [$C8],y
    and #$00FF
    sta $12
    stz $06
    lda #1
    sta $10
    lda $FA
    bne W6_SetRole__load
    lda #$FFFF
    sta $F4
W6_SetRole__load:
    .a16
    .i16
    jsl W6_EnterFrame
    rtl

W6_EnterFrame:
    rep #$30
    .a16
    .i16
    jsl W5_LoadFrame
    lda $2C
    beq W6_EnterFrame__valid
    lda #3
    sta $FC
    rtl
W6_EnterFrame__valid:
    .a16
    .i16
    lda $D0
    clc
    adc $40
    sta $D4
    lda $D2
    adc #0
    sta $D6
    lda $1A
    bne W6_EnterFrame__right
    lda $14
    sec
    sbc $5C
    bra W6_EnterFrame__position
W6_EnterFrame__right:
    .a16
    .i16
    lda $14
    clc
    adc $5C
W6_EnterFrame__position:
    .a16
    .i16
    sta $14
    jsl W6_FrameChanged
    rtl

W6_ThinkPass:
    rep #$30
    .a16
    .i16
    jsl W6_CheckPolicy
    bcs W6_ThinkPass__done
    lda $F6
    beq W6_ThinkPass__done
    ; A null source think callback leaves nextthink unchanged. Driver0 is
    ; explicitly NONE, not a callback that happens to do nothing.
    lda $E6
    beq W6_ThinkPass__done
    lda $E8
    cmp $D0
    bne W6_ThinkPass__done
    lda $EA
    cmp $D2
    bne W6_ThinkPass__done
    lda $D0
    clc
    adc #2
    sta $E8
    lda $D2
    adc #0
    sta $EA
    jsl W6_Think
W6_ThinkPass__done:
    .a16
    .i16
    rtl

W6_AnimationPass:
    rep #$30
    .a16
    .i16
    jsl W6_CheckPolicy
    bcs W6_AnimationPass__done
    lda $F6
    beq W6_AnimationPass__done
    lda $D4
    cmp $D0
    bne W6_AnimationPass__done
    lda $D6
    cmp $D2
    bne W6_AnimationPass__done
    lda $06
    clc
    adc $10
    bmi W6_AnimationPass__reverse_wrap
    cmp $04
    bcc W6_AnimationPass__frame
    lda #0
    bra W6_AnimationPass__wrap
W6_AnimationPass__reverse_wrap:
    .a16
    .i16
    lda $04
    dec a
W6_AnimationPass__wrap:
    .a16
    .i16
    ldx $12
    bne W6_AnimationPass__frame
    stz $10
    lda $FE
    beq W6_AnimationPass__done
    stz $F6
    bra W6_AnimationPass__done
W6_AnimationPass__frame:
    .a16
    .i16
    ldx $10
    beq W6_AnimationPass__done
    sta $06
    jsl W6_EnterFrame
W6_AnimationPass__done:
    .a16
    .i16
    rtl

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
W6_GroundDamage:
    rep #$30
    .a16
    .i16
    pha
    lda $F2
    cmp #1
    beq W6_GroundDamage__player
    pla
    jml W6_EnemyGroundDamage
W6_GroundDamage__player:
    .a16
    .i16
    pla
    jml W6_PlayerGroundDamage

; Pinned player_takedamage, nonlethal/unlinked/grounded 16-bit-xdir slice.
; 74 explicit jumping flag (independent of altitude),76 attacker type.
; E6=7 means player_pain, not enemy recovery. Caller owns opponent/effects.
; The supported source adapter stores xdir as a signed 16-bit speed with a
; zero upper word. player_takedamage negates it; unsupported upper-word and
; minimum-integer values fail before any gameplay mutation.
W6_PlayerGroundDamage:
    rep #$30
    .a16
    .i16
    sta $BA
    stx $BC
    sty $BE
    jsl W6_CheckPolicy
    bcc W6_PlayerGroundDamage__policy
    rtl
W6_PlayerGroundDamage__policy:
    .a16
    .i16
    lda $18
    eor #$8000
    cmp #$7F06              ; signed a >= PIT_DEPTH(-250)
    bcs W6_PlayerGroundDamage__above_pit
    jmp W6_PlayerGroundDamage__lifecycle
W6_PlayerGroundDamage__above_pit:
    .a16
    .i16
    lda $BA
    bpl W6_PlayerGroundDamage__nonnegative_force
    jmp W6_PlayerGroundDamage__range
W6_PlayerGroundDamage__nonnegative_force:
    .a16
    .i16
    lda $76
    cmp #2
    beq W6_PlayerGroundDamage__force
    cmp #1
    beq W6_PlayerGroundDamage__player_type_ok
    jmp W6_PlayerGroundDamage__range
W6_PlayerGroundDamage__player_type_ok:
    lsr $BA
W6_PlayerGroundDamage__force:
    .a16
    .i16
    lda $F0
    sec
    sbc $BA
    bvc W6_PlayerGroundDamage__no_overflow
    jmp W6_PlayerGroundDamage__range
W6_PlayerGroundDamage__no_overflow:
    sta $C0
    bpl W6_PlayerGroundDamage__hp_nonnegative
    jmp W6_PlayerGroundDamage__lifecycle
W6_PlayerGroundDamage__hp_nonnegative:
    bne W6_PlayerGroundDamage__nonlethal
    jmp W6_PlayerGroundDamage__lethal
W6_PlayerGroundDamage__nonlethal:
    lda $BC
    ora $C2
    ora $C4
    beq W6_PlayerGroundDamage__not_lifecycle
    jmp W6_PlayerGroundDamage__lifecycle
W6_PlayerGroundDamage__not_lifecycle:
    lda $BE
    cmp #1
    bne W6_PlayerGroundDamage__not_damage_type
    jmp W6_PlayerGroundDamage__lifecycle
W6_PlayerGroundDamage__not_damage_type:
    ldx $B0
    bne W6_PlayerGroundDamage__velocity_pointer
    jmp W6_PlayerGroundDamage__range
W6_PlayerGroundDamage__velocity_pointer:
    cpx #$7FF9
    bcc W6_PlayerGroundDamage__velocity_window
    jmp W6_PlayerGroundDamage__range
W6_PlayerGroundDamage__velocity_window:
    lda.l $40A002,x
    beq W6_PlayerGroundDamage__velocity_upper_zero
    jmp W6_PlayerGroundDamage__range
W6_PlayerGroundDamage__velocity_upper_zero:
    lda.l $40A000,x
    cmp #$8000
    bne W6_PlayerGroundDamage__velocity_negatable
    jmp W6_PlayerGroundDamage__range
W6_PlayerGroundDamage__velocity_negatable:
    ; All admission checks precede changes to gameplay state.
    ldx $B0
    lda.l $40A000,x
    eor #$FFFF
    inc a
    sta.l $40A000,x
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
    bvc W6_PlayerGroundDamage__sign
    eor #$8000
W6_PlayerGroundDamage__sign:
    .a16
    .i16
    bmi W6_PlayerGroundDamage__right
    lda #0
    bra W6_PlayerGroundDamage__face
W6_PlayerGroundDamage__right:
    .a16
    .i16
    lda #1
W6_PlayerGroundDamage__face:
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
    jsl W6_SetRole
    stz $FA
    rtl
W6_PlayerGroundDamage__lethal:
    .a16
    .i16
    lda $A8
    and #$8000
    beq W6_PlayerGroundDamage__lifecycle
    lda $BC
    ora $C2
    ora $C4
    bne W6_PlayerGroundDamage__lifecycle
    lda $BE
    cmp #1
    beq W6_PlayerGroundDamage__lifecycle
    lda #0
    sta $F0
    sta $F6
    stz $74
    lda $08
    and #$FFFE
    sta $08
    rtl
W6_PlayerGroundDamage__range:
    .a16
    .i16
    lda #5
    sta $FC
    rtl
W6_PlayerGroundDamage__lifecycle:
    .a16
    .i16
    lda #4
    sta $FC
    rtl

W6_EnemyGroundDamage:
    rep #$30
    .a16
    .i16
    sta $BA
    stx $BC
    sty $BE
    jsl W6_CheckPolicy
    bcc W6_EnemyGroundDamage__policy
    rtl
W6_EnemyGroundDamage__policy:
    .a16
    .i16
    lda $F2
    cmp #2
    beq W6_EnemyGroundDamage__enemy_type
    jmp W6_EnemyGroundDamage__range
W6_EnemyGroundDamage__enemy_type:
    lda $F0
    sec
    sbc $BA
    bvc W6_EnemyGroundDamage__no_overflow
    jmp W6_EnemyGroundDamage__range
W6_EnemyGroundDamage__no_overflow:
    sta $C0
    bmi W6_EnemyGroundDamage__lethal
    beq W6_EnemyGroundDamage__lethal
    lda $BC
    ora $C2
    ora $C4
    beq W6_EnemyGroundDamage__not_lifecycle
    jmp W6_EnemyGroundDamage__lifecycle
W6_EnemyGroundDamage__not_lifecycle:
    lda $BE
    cmp #1
    beq W6_EnemyGroundDamage__lifecycle
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
    beq W6_EnemyGroundDamage__direction
    ; Signed coordinate comparison, preserving overflow correctly.
    sec
    sbc $B8
    bvc W6_EnemyGroundDamage__sign
    eor #$8000
W6_EnemyGroundDamage__sign:
    .a16
    .i16
    bpl W6_EnemyGroundDamage__left
    lda #1
    bra W6_EnemyGroundDamage__store_direction
W6_EnemyGroundDamage__left:
    .a16
    .i16
    lda #0
W6_EnemyGroundDamage__store_direction:
    .a16
    .i16
    sta $1A
W6_EnemyGroundDamage__direction:
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
    jsl W6_SetRole
    stz $FA
    rtl
W6_EnemyGroundDamage__lethal:
    .a16
    .i16
    lda $A8
    and #$8000
    beq W6_EnemyGroundDamage__lifecycle
    lda $BC
    ora $C2
    ora $C4
    bne W6_EnemyGroundDamage__lifecycle
    lda $BE
    cmp #1
    beq W6_EnemyGroundDamage__lifecycle
    ; The source ordinary-enemy death callback consumes one random lift value
    ; on the lethal path. Keep that stream position even though Normal's
    ; production entity contract uses BOR's HP-zero soft-kill renderer and
    ; retires the resident row at the next acknowledged snapshot boundary.
    phd
    lda $36
    tcd
    jsl W6_Random32
    jsl W6_RandomModulo1000
    pld
    lda #0
    sta $F0
    sta $F6
    stz $08
    rtl
W6_EnemyGroundDamage__range:
    .a16
    .i16
    lda #5
    sta $FC
    rtl
W6_EnemyGroundDamage__lifecycle:
    .a16
    .i16
    lda #4
    sta $FC
    rtl

; Grounded pain/rise completion. 38 idle role ID, E6 driver2 pain/3 rise;
; C4 explicit linked state. Numeric velocity storage is independently owned:
; B0 points to eight bytes (xdir32,zdir32); zero is exact in supported formats.
; Driver1 ordinary enemy is returned to caller; this routine never invents AI.
W6_RecoveryThink:
    rep #$30
    .a16
    .i16
    jsl W6_CheckPolicy
    bcs W6_RecoveryThink__done
    lda $10
    bne W6_RecoveryThink__done
    lda $C4
    bne W6_RecoveryThink__blocked
    lda $E6
    cmp #2
    beq W6_RecoveryThink__idle
    cmp #3
    bne W6_RecoveryThink__blocked
    jsl W6_StopMovement
    lda $FC
    bne W6_RecoveryThink__done
W6_RecoveryThink__idle:
    .a16
    .i16
    lda #1
    sta $E6
    stz $FA
    lda $38
    jsl W6_SetRole
W6_RecoveryThink__done:
    .a16
    .i16
    rtl
W6_RecoveryThink__blocked:
    .a16
    .i16
    lda #4
    sta $FC
    rtl

W6_StopMovement:
    rep #$30
    .a16
    .i16
    ldx $B0
    beq W6_StopMovement__unbound
    cpx #$7FF9
    bcs W6_StopMovement__unbound
    lda #0
    sta.l $40A000,x
    sta.l $40A002,x
    sta.l $40A004,x
    sta.l $40A006,x
    rtl
W6_StopMovement__unbound:
    .a16
    .i16
    lda #7
    sta $FC
    rtl

; Source enemy_drop/enemy_lie/suicide scheduling. Physics/landing decides
; when to enter LIE and sets EC stall deadline; this does not infer a role
; from altitude. E6:1 enemy,2 pain,3 rise,4 lie,5 suicide,6 initial drop.
; B2 blink,3C source rise-role ID, C2 explicit source inair predicate.
W6_GroundLifecycle:
    rep #$30
    .a16
    .i16
    jsl W6_CheckPolicy
    bcs W6_GroundLifecycle__done
    lda $E6
    cmp #5
    beq W6_GroundLifecycle__remove
    cmp #6
    beq W6_GroundLifecycle__drop
    cmp #4
    beq W6_GroundLifecycle__lie
    lda #8
    sta $FC
W6_GroundLifecycle__done:
    .a16
    .i16
    rtl
W6_GroundLifecycle__remove:
    .a16
    .i16
    stz $F6
    rtl
W6_GroundLifecycle__drop:
    .a16
    .i16
    lda $C2
    bne W6_GroundLifecycle__done
    lda #1
    sta $E6
    lda $F0
    beq W6_GroundLifecycle__remove
    bmi W6_GroundLifecycle__remove
    rtl
W6_GroundLifecycle__lie:
    .a16
    .i16
    lda $F0
    beq W6_GroundLifecycle__dead
    bmi W6_GroundLifecycle__dead
    lda $D2
    cmp $EE
    bcc W6_GroundLifecycle__done
    bne W6_GroundLifecycle__rise
    lda $D0
    cmp $EC
    bcc W6_GroundLifecycle__done
W6_GroundLifecycle__rise:
    .a16
    .i16
    jsl W6_StopMovement
    lda $FC
    bne W6_GroundLifecycle__done
    stz $FA
    lda $3C
    jsl W6_SetRole
    lda #3
    sta $E6
    rtl
W6_GroundLifecycle__dead:
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

; SOURCE_EXACT pairwise hit resolver, opt-in CPU fixture ABI.
; Attacker D: S5 geometry context plus 34 target DP(u16),36 world RNG/attack
; context DP(u16), DC/DE current attack ID32. Target: D8/DA hit-by ID32,
; B4/B6 pain deadline32, F0 HP,F2 source type, current frame pointer30.
; World context offset20/22: shared new-attack ID32, initialized1.
; All contexts must be separate, aligned bank0 WRAM mirrors below $2000.
; Host calls on source collision-pass parity and binds every world target.
; Grounded enemy and bounded nonlethal player damage callbacks are linked.
; Other callbacks/lifecycle and upper-counter pass remain explicit blockers.
; Required W6_HitEffects hook owns hit flash, score/opponent and audio effects;
; a fixture event sink is not a production effects certificate.
W6_TryHitOne:
    rep #$30
    .a16
    .i16
    jsl W6_CheckPolicy
    bcc W6_TryHitOne__policy
    rtl
W6_TryHitOne__policy:
    .a16
    .i16
    jsl W5_ActivateAttack
    lda $0A
    bne W6_TryHitOne__active
    stz $DC
    stz $DE
    rtl
W6_TryHitOne__active:
    .a16
    .i16
    lda $34
    ora $36
    and #$E0FF
    cmp #$6000
    beq W6_TryHitOne__addresses
    lda #6
    sta $FC
    rtl
W6_TryHitOne__addresses:
    .a16
    .i16
    ; Callback scope is explicit, rather than defaulting an enemy hit to
    ; accepted fixed damage or another source model's behavior.
    ldx $34
    lda.l $40A0F2,x
    cmp #1
    beq W6_TryHitOne__player_target
    cmp #2
    beq W6_TryHitOne__target_type
    lda #5
    sta $FC
    rtl
W6_TryHitOne__player_target:
    .a16
    .i16
    lda $08
    and #2
    bne W6_TryHitOne__identity
    lda $F2
    cmp #1
    beq W6_TryHitOne__identity
    cmp #2
    beq W6_TryHitOne__identity
    rtl
W6_TryHitOne__target_type:
    .a16
    .i16
    lda $08
    and #2
    bne W6_TryHitOne__identity
    lda $F2
    cmp #1
    beq W6_TryHitOne__identity
    rtl
W6_TryHitOne__identity:
    .a16
    .i16
    lda $DC
    ora $DE
    bne W6_TryHitOne__have_id
    ldx $36
    lda.l $40A020,x
    inc a
    sta.l $40A020,x
    bne W6_TryHitOne__read_id
    lda.l $40A022,x
    inc a
    sta.l $40A022,x
    bne W6_TryHitOne__read_id
    lda #1
    sta.l $40A020,x
W6_TryHitOne__read_id:
    .a16
    .i16
    lda.l $40A020,x
    sta $DC
    lda.l $40A022,x
    sta $DE
W6_TryHitOne__have_id:
    .a16
    .i16
    ldx $34
    lda.l $40A0F6,x
    beq W6_TryHitOne__done
    lda.l $40A0D8,x
    cmp $DC
    bne W6_TryHitOne__pain
    lda.l $40A0DA,x
    cmp $DE
    beq W6_TryHitOne__done
W6_TryHitOne__pain:
    .a16
    .i16
    lda.l $40A0B6,x
    cmp $D2
    bcc W6_TryHitOne__geometry
    bne W6_TryHitOne__done
    lda.l $40A0B4,x
    cmp $D0
    bcs W6_TryHitOne__done
W6_TryHitOne__geometry:
    .a16
    .i16
    tdc
    cmp $34
    beq W6_TryHitOne__done
    stz $24
    lda.l $40A014,x
    sta $1C
    lda.l $40A016,x
    sta $1E
    lda.l $40A018,x
    sta $20
    lda.l $40A01A,x
    sta $22
    lda.l $40A030,x
    sta $26
    lda.l $40A032,x
    sta $28
    jsl W6_SourceCollision
    lda $2A
    beq W6_TryHitOne__done
    jmp W6_TryHitOne__damage
W6_TryHitOne__done:
    .a16
    .i16
    rtl
W6_TryHitOne__damage:
    .a16
    .i16
    ldx $34
    lda $D0
    sta.l $40A0D0,x
    lda $D2
    sta.l $40A0D2,x
    lda $14
    sta.l $40A0B8,x
    lda $F2
    sta.l $40A076,x
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
    jsl W6_GroundDamage
    pld
    pla
    pla
    pla
    ldx $34
    lda.l $40A0FC,x
    sta $FC
    bne W6_TryHitOne__done
    lda $DC
    sta.l $40A0D8,x
    lda $DE
    sta.l $40A0DA,x
    jsl W6_HitEffects
    rtl

; S5 owns60..7F as transient target-frame staging. The scheduler also keeps
; persistent host/lifecycle fields70..7F between calls. Preserve that complete
; overlap explicitly at the interface; never let a target's attack geometry
; become the attacker's slot handle, displayed HP or lifecycle state.
; Source collision only consumes the target's header/body60..6B internally.
W6_SourceCollision:
    rep #$30
    .a16
    .i16
    ldx #14
W6_SourceCollision__save:
    .a16
    .i16
    lda $70,x
    pha
    dex
    dex
    bpl W6_SourceCollision__save
    jsl W5_CheckCollision
    ldx #0
W6_SourceCollision__restore:
    .a16
    .i16
    pla
    sta $70,x
    inx
    inx
    cpx #16
    bne W6_SourceCollision__restore
    rtl

; Pinned GAMELIB3/RAND32.ASM integer recurrence, independent project/world state.
; Separate caller-owned D context (not an actor DP): 00 seed32,04 result32,
; 08 product48,0E shifted multiplier48,14 source seed32,18 remainder16.
; A16/I16 DBR0 decimal clear; JSL/RTL. Shared world stream, NOT per-actor RNG.
; Scheduling/call-order ownership remains with the source world scheduler.
W6_Random32:
    rep #$30
    .a16
    .i16
    lda $00
    sta $14
    lda $02
    sta $16
    stz $08
    stz $0A
    stz $0C
    lda #$4E6D
    sta $0E
    lda #$41C6
    sta $10
    stz $12
    ldx #32
W6_Random32__bit:
    .a16
    .i16
    lsr $16
    ror $14
    bcc W6_Random32__shift
    lda $08
    clc
    adc $0E
    sta $08
    lda $0A
    adc $10
    sta $0A
    lda $0C
    adc $12
    sta $0C
W6_Random32__shift:
    .a16
    .i16
    asl $0E
    rol $10
    rol $12
    dex
    bne W6_Random32__bit
    lda $08
    clc
    adc #12345
    sta $00
    lda $0A
    adc #0
    sta $02
    sta $04
    lda $0C
    adc #0
    sta $06
    rtl

; Unsigned full returned-word modulo1000, no replacement byte distribution.
W6_RandomModulo1000:
    rep #$30
    .a16
    .i16
    lda $04
    sta $14
    lda $06
    sta $16
    stz $18
    ldx #32
W6_RandomModulo1000__bit:
    .a16
    .i16
    asl $14
    rol $16
    rol $18
    lda $18
    cmp #1000
    bcc W6_RandomModulo1000__next
    sbc #1000
    sta $18
W6_RandomModulo1000__next:
    .a16
    .i16
    dex
    bne W6_RandomModulo1000__bit
    rtl

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
W6_SelectTarget:
    rep #$30
    .a16
    .i16
    jsl W6_CheckPolicy
    lda $FC
    beq W6_SelectTarget__world
    rtl
W6_SelectTarget__world:
    .a16
    .i16
    stz $34
    lda $36
    jsl W6_TargetPointer
    bcc W6_SelectTarget__world_valid
    jmp W6_SelectTarget__bad
W6_SelectTarget__world_valid:
    .a16
    .i16
    tax
    lda.l $40A044,x
    sta $60
    lda.l $40A046,x
    sta $62
    lda $60
    bne W6_SelectTarget__both
    jmp W6_SelectTarget__one
W6_SelectTarget__both:
    .a16
    .i16
    jsl W6_TargetPointer
    bcc W6_SelectTarget__p0_valid
    jmp W6_SelectTarget__bad
W6_SelectTarget__p0_valid:
    .a16
    .i16
    lda $62
    bne W6_SelectTarget__p1_present
    jmp W6_SelectTarget__first
W6_SelectTarget__p1_present:
    .a16
    .i16
    jsl W6_TargetPointer
    bcc W6_SelectTarget__p1_valid
    jmp W6_SelectTarget__bad
W6_SelectTarget__p1_valid:
    .a16
    .i16
    lda $14
    jsl W6_TargetCoordinate
    bcc W6_SelectTarget__x_valid
    jmp W6_SelectTarget__numeric
W6_SelectTarget__x_valid:
    .a16
    .i16
    lda $16
    jsl W6_TargetCoordinate
    bcc W6_SelectTarget__z_valid
    jmp W6_SelectTarget__numeric
W6_SelectTarget__z_valid:
    .a16
    .i16
    ldx $60
    jsl W6_TargetDelta
    lda $FC
    bne W6_SelectTarget__return
    lda $64
    sta $68
    lda $66
    sta $6A
    ldx $62
    jsl W6_TargetDelta
    lda $FC
    bne W6_SelectTarget__return
    ; Strict straddling, equal X is NOT on the other side.
    lda $68
    beq W6_SelectTarget__distance
    lda $64
    beq W6_SelectTarget__distance
    eor $68
    bpl W6_SelectTarget__distance
    lda $1A
    beq W6_SelectTarget__left
    lda $68
    bmi W6_SelectTarget__first
    bra W6_SelectTarget__second
W6_SelectTarget__left:
    .a16
    .i16
    lda $68
    bpl W6_SelectTarget__first
    bra W6_SelectTarget__second
W6_SelectTarget__distance:
    .a16
    .i16
    lda $68
    jsl W6_TargetAbs
    sta $6C
    lda $6A
    jsl W6_TargetAbs
    clc
    adc $6C
    sta $6C
    lda $64
    jsl W6_TargetAbs
    sta $68
    lda $66
    jsl W6_TargetAbs
    clc
    adc $68
    cmp $6C
    ; source strict d1<d2, ties select player[1].
    beq W6_SelectTarget__second
    bcc W6_SelectTarget__second
W6_SelectTarget__first:
    .a16
    .i16
    lda $60
    sta $34
    rtl
W6_SelectTarget__one:
    .a16
    .i16
    lda $62
    beq W6_SelectTarget__second
    jsl W6_TargetPointer
    bcs W6_SelectTarget__bad
W6_SelectTarget__second:
    .a16
    .i16
    lda $62
    sta $34
W6_SelectTarget__return:
    .a16
    .i16
    rtl
W6_SelectTarget__bad:
    .a16
    .i16
    lda #9
    sta $FC
    rtl
W6_SelectTarget__numeric:
    .a16
    .i16
    lda #10
    sta $FC
    rtl

W6_TargetPointer:
    .a16
    .i16
    pha
    and #$00FF
    bne W6_TargetPointer__bad
    pla
    beq W6_TargetPointer__zero
    cmp #$7F00
    rtl
W6_TargetPointer__bad:
    .a16
    .i16
    pla
W6_TargetPointer__zero:
    .a16
    .i16
    sec
    rtl

W6_TargetCoordinate:
    .a16
    .i16
    pha
    clc
    adc #16384
    cmp #32768
    pla
    rtl

W6_TargetDelta:
    .a16
    .i16
    lda.l $40A014,x
    jsl W6_TargetCoordinate
    bcs W6_TargetDelta__numeric
    sta $64
    lda.l $40A016,x
    jsl W6_TargetCoordinate
    bcs W6_TargetDelta__numeric
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
W6_TargetDelta__numeric:
    .a16
    .i16
    lda #10
    sta $FC
    rtl
W6_TargetAbs:
    .a16
    .i16
    cmp #0
    bpl W6_TargetAbs__done
    eor #$FFFF
    inc a
W6_TargetAbs__done:
    .a16
    .i16
    rtl

; Opt-in discrete source world consumers. Not production dispatch.
; D=world for count, D=actor for kill/display. DBR0,A16/I16,decimal clear.
; World44/46 player entities;4E/50 player opponent references.
; World48/4A/4C count scratch. Actor70=source oldhealth.
; Slot table and contexts must satisfy link_world_contexts admission.
; Unlinked kill is complete for these declared references. Linked kill fails
; closed until source ent_unlink ownership is represented (C4 is only a flag).
W6_CountEntities:
    rep #$30
    .a16
    .i16
    sta $48
    stz $4A
    stz $4C
    stz $3A
    lda $34
    cmp #151
    bcs W6_CountEntities__bad
W6_CountEntities__loop:
    .a16
    .i16
    lda $4A
    cmp $34
    bcs W6_CountEntities__done
    asl a
    tay
    lda [$30],y
    beq W6_CountEntities__next
    jsl W6_TargetPointer
    bcs W6_CountEntities__bad
    tax
    lda.l $40A0E0,x
    cmp #1
    bne W6_CountEntities__bad
    lda.l $40A0F6,x
    beq W6_CountEntities__next
    lda.l $40A0F2,x
    and $48
    beq W6_CountEntities__next
    inc $4C
W6_CountEntities__next:
    .a16
    .i16
    inc $4A
    bra W6_CountEntities__loop
W6_CountEntities__bad:
    .a16
    .i16
    lda #9
    sta $3A
    stz $4C
W6_CountEntities__done:
    .a16
    .i16
    lda $4C
    rtl

W6_KillUnlinked:
    rep #$30
    .a16
    .i16
    jsl W6_CheckPolicy
    bcs W6_KillUnlinked__policy_done
    lda $C4
    bne W6_KillUnlinked__linked
    lda $36
    jsl W6_TargetPointer
    bcs W6_KillUnlinked__bad
    tax
    stz $F0
    stz $F6
    tdc
    cmp.l $40A044,x
    bne W6_KillUnlinked__player1
    lda #0
    sta.l $40A044,x
    tdc
W6_KillUnlinked__player1:
    .a16
    .i16
    cmp.l $40A046,x
    bne W6_KillUnlinked__opponent0
    lda #0
    sta.l $40A046,x
    tdc
W6_KillUnlinked__opponent0:
    .a16
    .i16
    cmp.l $40A04E,x
    bne W6_KillUnlinked__opponent1
    lda #0
    sta.l $40A04E,x
    tdc
W6_KillUnlinked__opponent1:
    .a16
    .i16
    cmp.l $40A050,x
    bne W6_KillUnlinked__done
    lda #0
    sta.l $40A050,x
W6_KillUnlinked__policy_done:
    .a16
    .i16
    rtl
W6_KillUnlinked__done:
    lda #0
    sta.l $41243E
    lda #3
    ldx $7A
    ldy #0
    jsl S6_EventPush
    .a16
    .i16
    rtl
W6_KillUnlinked__linked:
    .a16
    .i16
    lda #4
    sta $FC
    rtl
W6_KillUnlinked__bad:
    .a16
    .i16
    lda #9
    sta $FC
    rtl

W6_DisplayHealth:
    rep #$30
    .a16
    .i16
    jsl W6_CheckPolicy
    bcs W6_DisplayHealth__done
    lda $70
    cmp $F0
    beq W6_DisplayHealth__done
    sec
    sbc $F0
    bvc W6_DisplayHealth__sign
    eor #$8000
W6_DisplayHealth__sign:
    .a16
    .i16
    bmi W6_DisplayHealth__increase
    dec $70
    rtl
W6_DisplayHealth__increase:
    .a16
    .i16
    inc $70
W6_DisplayHealth__done:
    .a16
    .i16
    rtl

; Opt-in source world pass coordinator; not linked into shipped production.
; D = aligned world context in bank0 WRAM mirror, DBR0, A16/I16, decimal clear.
; 30 slot pointer-table24 (u16 actor DP per source slot; zero = empty slot).
; 34 source slot count <=150,36 current slot,38 pass,3A error,
; 3C/3E absolute source tick32,40 level-present,42 saved world DP.
; RNG/attack counter occupy00..22 independently. Actor36 receives world DP.
; Slot ordinal, NOT dense active index, owns collision parity.
; Actor context is256 bytes, page aligned $0100..$1E00, distinct from world.
; Linker must prove table immutability, unique actor contexts and no overlap
; with stack/other allocations. This bank0 ABI is NOT a150-live-actor claim.
; All bound actor policies are checked before any execution pass.
; Errors:1 policy,9 slot/layout, other actor error propagated. No fallback.
;
; Required host hooks (D=actor, world pointer36, preserve D/width/DBR):
; W6_WorldLost, W6_WorldGravity, W6_WorldAttack, W6_WorldHealth.
; These must implement source world/numeric/effect semantics or set actorFC.
; Missing hooks are link errors. No no-op production defaults are supplied.
; Gravity includes hole/pit processing; world attack owns whole target scan.
; W6_ThinkPass / AnimationPass consume their existing required hooks.
; Callback death is observed by every following pass and later slot visit.
; Time D0/D2 and world36 are immutable tick inputs, installed on the first
; enabled pass. An in-pass birth must install those inputs at bind time.
; Host supplies source time, does not advance it here, and owns pause/cap100.

; Bound entry is available only after a successful checked pass and while the
; host holds the immutable slot-table/count/policy/context-layout lease. It does
; NOT cache existence, health, target, callback errors, time or parity. Release,
; bind/respawn, table/count/policy mutation invalidate that lease. D/DBR and
; M/X entry contract is identical; both entries return with identical stack.
W6_UpdateWorldBound:
    rep #$30
    .a16
    .i16
    stz $3A
    jmp W6_UpdateWorld__start

W6_UpdateWorld:
    rep #$30
    .a16
    .i16
    tdc
    sta $42
    and #$00FF
    bne W6_UpdateWorld__bad
    tdc
    beq W6_UpdateWorld__bad
    cmp #$7F00
    bcs W6_UpdateWorld__bad
    lda $34
    cmp #151
    bcs W6_UpdateWorld__bad
    stz $3A
    stz $36
W6_UpdateWorld__preflight:
    .a16
    .i16
    lda $36
    cmp $34
    bcs W6_UpdateWorld__start
    asl a
    tay
    lda [$30],y
    beq W6_UpdateWorld__next_check
    tax
    and #$00FF
    bne W6_UpdateWorld__bad
    txa
    cmp #$7F00
    bcs W6_UpdateWorld__bad
    cmp $42
    beq W6_UpdateWorld__bad
    lda.l $40A0E0,x
    cmp #1
    bne W6_UpdateWorld__policy
W6_UpdateWorld__next_check:
    .a16
    .i16
    inc $36
    bra W6_UpdateWorld__preflight
W6_UpdateWorld__bad:
    .a16
    .i16
    lda #9
    sta $3A
    rtl
W6_UpdateWorld__policy:
    .a16
    .i16
    lda #1
    sta $3A
    rtl
W6_UpdateWorld__start:
; Generated by tools/bor_compile/world_pass_codegen.py; no actor data.
W6_UpdateWorld_P0:
    .a16
    .i16
    lda #0
    sta $38
    stz $36
    lda $40
    bne W6_UpdateWorld_P0__slot
    jmp W6_UpdateWorld_P1
W6_UpdateWorld_P0__slot:
    .a16
    .i16
    lda $36
    cmp $34
    bcc W6_UpdateWorld_P0__visit
    jmp W6_UpdateWorld_P1
W6_UpdateWorld_P0__visit:
    .a16
    .i16
    lda $36
    asl a
    tay
    lda [$30],y
    beq W6_UpdateWorld_P0__next
    tax
    lda.l $40A0F6,x
    beq W6_UpdateWorld_P0__next
    lda.l $40A0FC,x
    beq W6_UpdateWorld_P0__call
    sta $3A
    rtl
W6_UpdateWorld_P0__call:
    .a16
    .i16
    lda $3C
    sta.l $40A0D0,x
    lda $3E
    sta.l $40A0D2,x
    lda $42
    sta.l $40A036,x
    phd
    txa
    tcd
    jsl W6_WorldLost
    lda $FC
    pld
    cmp #0
    beq W6_UpdateWorld_P0__next
    sta $3A
    rtl
W6_UpdateWorld_P0__next:
    .a16
    .i16
    inc $36
    jmp W6_UpdateWorld_P0__slot
W6_UpdateWorld_P1:
    .a16
    .i16
    lda #1
    sta $38
    stz $36
    lda $40
    bne W6_UpdateWorld_P1__slot
    jmp W6_UpdateWorld_P2
W6_UpdateWorld_P1__slot:
    .a16
    .i16
    lda $36
    cmp $34
    bcc W6_UpdateWorld_P1__visit
    jmp W6_UpdateWorld_P2
W6_UpdateWorld_P1__visit:
    .a16
    .i16
    lda $36
    asl a
    tay
    lda [$30],y
    beq W6_UpdateWorld_P1__next
    tax
    lda.l $40A0F6,x
    beq W6_UpdateWorld_P1__next
    lda.l $40A0FC,x
    beq W6_UpdateWorld_P1__call
    sta $3A
    rtl
W6_UpdateWorld_P1__call:
    .a16
    .i16
    phd
    txa
    tcd
    jsl W6_WorldGravity
    lda $FC
    pld
    cmp #0
    beq W6_UpdateWorld_P1__next
    sta $3A
    rtl
W6_UpdateWorld_P1__next:
    .a16
    .i16
    inc $36
    jmp W6_UpdateWorld_P1__slot
W6_UpdateWorld_P2:
    .a16
    .i16
    lda #2
    sta $38
    stz $36
W6_UpdateWorld_P2__slot:
    .a16
    .i16
    lda $36
    cmp $34
    bcc W6_UpdateWorld_P2__visit
    jmp W6_UpdateWorld_P3
W6_UpdateWorld_P2__visit:
    .a16
    .i16
    lda $36
    asl a
    tay
    lda [$30],y
    beq W6_UpdateWorld_P2__next
    tax
    lda.l $40A0F6,x
    beq W6_UpdateWorld_P2__next
    lda.l $40A0FC,x
    beq W6_UpdateWorld_P2__call
    sta $3A
    rtl
W6_UpdateWorld_P2__call:
    .a16
    .i16
    lda $40
    bne W6_UpdateWorld_P2__time_ready
    lda $3C
    sta.l $40A0D0,x
    lda $3E
    sta.l $40A0D2,x
    lda $42
    sta.l $40A036,x
W6_UpdateWorld_P2__time_ready:
    .a16
    .i16
    phd
    txa
    tcd
    jsl W6_ThinkPass
    lda $FC
    pld
    cmp #0
    beq W6_UpdateWorld_P2__next
    sta $3A
    rtl
W6_UpdateWorld_P2__next:
    .a16
    .i16
    inc $36
    jmp W6_UpdateWorld_P2__slot
W6_UpdateWorld_P3:
    .a16
    .i16
    lda #3
    sta $38
    stz $36
W6_UpdateWorld_P3__slot:
    .a16
    .i16
    lda $36
    cmp $34
    bcc W6_UpdateWorld_P3__visit
    jmp W6_UpdateWorld_P4
W6_UpdateWorld_P3__visit:
    .a16
    .i16
    lda $36
    asl a
    tay
    lda [$30],y
    beq W6_UpdateWorld_P3__next
    tax
    lda.l $40A0F6,x
    beq W6_UpdateWorld_P3__next
    lda.l $40A0FC,x
    beq W6_UpdateWorld_P3__call
    sta $3A
    rtl
W6_UpdateWorld_P3__call:
    .a16
    .i16
    phd
    txa
    tcd
    jsl W6_AnimationPass
    lda $FC
    pld
    cmp #0
    beq W6_UpdateWorld_P3__next
    sta $3A
    rtl
W6_UpdateWorld_P3__next:
    .a16
    .i16
    inc $36
    jmp W6_UpdateWorld_P3__slot
W6_UpdateWorld_P4:
    .a16
    .i16
    lda #4
    sta $38
    stz $36
W6_UpdateWorld_P4__slot:
    .a16
    .i16
    lda $36
    cmp $34
    bcc W6_UpdateWorld_P4__visit
    jmp W6_UpdateWorld_P5
W6_UpdateWorld_P4__visit:
    .a16
    .i16
    lda $36
    eor $3C
    and #1
    bne W6_UpdateWorld_P4__next
    lda $36
    asl a
    tay
    lda [$30],y
    beq W6_UpdateWorld_P4__next
    tax
    lda.l $40A0F6,x
    beq W6_UpdateWorld_P4__next
    lda.l $40A0FC,x
    beq W6_UpdateWorld_P4__call
    sta $3A
    rtl
W6_UpdateWorld_P4__call:
    .a16
    .i16
    phd
    txa
    tcd
    jsl W6_WorldAttack
    lda $FC
    pld
    cmp #0
    beq W6_UpdateWorld_P4__next
    sta $3A
    rtl
W6_UpdateWorld_P4__next:
    .a16
    .i16
    inc $36
    jmp W6_UpdateWorld_P4__slot
W6_UpdateWorld_P5:
    .a16
    .i16
    lda #5
    sta $38
    stz $36
W6_UpdateWorld_P5__slot:
    .a16
    .i16
    lda $36
    cmp $34
    bcc W6_UpdateWorld_P5__visit
    jmp W6_UpdateWorld__done
W6_UpdateWorld_P5__visit:
    .a16
    .i16
    lda $36
    asl a
    tay
    lda [$30],y
    beq W6_UpdateWorld_P5__next
    tax
    lda.l $40A0F6,x
    beq W6_UpdateWorld_P5__next
    lda.l $40A0FC,x
    beq W6_UpdateWorld_P5__call
    sta $3A
    rtl
W6_UpdateWorld_P5__call:
    .a16
    .i16
    phd
    txa
    tcd
    jsl W6_WorldHealth
    lda $FC
    pld
    cmp #0
    beq W6_UpdateWorld_P5__next
    sta $3A
    rtl
W6_UpdateWorld_P5__next:
    .a16
    .i16
    inc $36
    jmp W6_UpdateWorld_P5__slot
    ; Final public iterator state matches the reference traversal.
W6_UpdateWorld__done:
    .a16
    .i16
    lda #6
    sta $38
    rtl

W6_UpdateWorldDispatch:
    rep #$30
    .a16
    .i16
    cpy #0
    bne W6_UpdateWorldDispatch__gravity
    jsl W6_WorldLost
    rtl
W6_UpdateWorldDispatch__gravity:
    .a16
    .i16
    cpy #1
    bne W6_UpdateWorldDispatch__think
    jsl W6_WorldGravity
    rtl
W6_UpdateWorldDispatch__think:
    .a16
    .i16
    cpy #2
    bne W6_UpdateWorldDispatch__animation
    jsl W6_ThinkPass
    rtl
W6_UpdateWorldDispatch__animation:
    .a16
    .i16
    cpy #3
    bne W6_UpdateWorldDispatch__attack
    jsl W6_AnimationPass
    rtl
W6_UpdateWorldDispatch__attack:
    .a16
    .i16
    cpy #4
    bne W6_UpdateWorldDispatch__health
    jsl W6_WorldAttack
    rtl
W6_UpdateWorldDispatch__health:
    .a16
    .i16
    jsl W6_WorldHealth
    rtl

; Source ordinary single-attack decision/role driver, opt-in.
; Metadata, not source identity, selects this bounded capability.
; Actor A0 attack role, A2 signed range minimum,A4 signed maximum,A6 walk role.
; A8 nonzero means additional attack/upper/jump/frame-event semantics required.
; C6 authored speed in twentieths; B0 points to signed x/z speed words.
; D8/DA retain subpixel remainders in twentieths. E6:1 enemy,11 prepare,
; 12 attack,13 runoff. RNG remains the shared source stream at world36.
W6_EnemyDecision:
    rep #$30
    .a16
    .i16
    jsl W6_CheckPolicy
    bcc W6_EnemyDecision__policy
    rtl
W6_EnemyDecision__policy:
    .a16
    .i16
    ; Normal campaign program word 14 reserves bit 15 for its explicit
    ; native HP-zero retirement adapter. Remaining feature bits stay
    ; fail-closed; the marker itself must not disable ordinary AI.
    lda $A8
    and #$7FFF
    beq W6_EnemyDecision__features
    jmp W6_EnemyDecision__blocked
W6_EnemyDecision__features:
    .a16
    .i16
    lda $E6
    cmp #12
    bne W6_EnemyDecision__driver
    jml W6_EnemyAttack
W6_EnemyDecision__driver:
    .a16
    .i16
    cmp #1
    beq W6_EnemyDecision__select
    cmp #11
    beq W6_EnemyDecision__select
    cmp #13
    beq W6_EnemyDecision__select
    jmp W6_EnemyDecision__blocked
W6_EnemyDecision__select:
    .a16
    .i16
    jsl W6_SelectTarget
    lda $FC
    beq W6_EnemyDecision__target_ok
    jmp W6_EnemyDecision__done
W6_EnemyDecision__target_ok:
    lda $34
    bne W6_EnemyDecision__has_target
    jmp W6_EnemyDecision__no_target
W6_EnemyDecision__has_target:
    tax
    lda.l $40A014,x
    sec
    sbc $14
    beq W6_EnemyDecision__face_fraction
    bmi W6_EnemyDecision__left
    lda #1
    bra W6_EnemyDecision__face
W6_EnemyDecision__face_fraction:
    .a16
    .i16
    lda.l $40A0D8,x
    sec
    sbc $D8
    beq W6_EnemyDecision__left
    bmi W6_EnemyDecision__left
    lda #1
    bra W6_EnemyDecision__face
W6_EnemyDecision__left:
    .a16
    .i16
    lda #0
W6_EnemyDecision__face:
    .a16
    .i16
    sta $1A
    lda $E6
    cmp #13
    bne W6_EnemyDecision__not_runoff
    jmp W6_EnemyDecision__runoff
W6_EnemyDecision__not_runoff:
    cmp #11
    bne W6_EnemyDecision__grounded
    jmp W6_EnemyPrepare
W6_EnemyDecision__grounded:
    lda.l $40A016,x
    sec
    sbc $16
    jsl W6_TargetAbs
    cmp #12
    bcs W6_EnemyDecision__chase
    jsl W6_EnemyInRange
    bcc W6_EnemyDecision__chase
    stz $FA
    lda $38
    jsl W6_SetRole
    lda $FC
    bne W6_EnemyDecision__done
    lda #11
    sta $E6
    ; rand32()%20 == (rand32()%1000)%20 for every unsigned32 result.
    phd
    lda $36
    tcd
    jsl W6_Random32
    jsl W6_RandomModulo1000
    lda $18
W6_EnemyDecision__mod20:
    .a16
    .i16
    cmp #20
    bcc W6_EnemyDecision__delay
    sbc #20
    bra W6_EnemyDecision__mod20
W6_EnemyDecision__delay:
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
W6_EnemyDecision__done:
    .a16
    .i16
    rtl
W6_EnemyDecision__no_target:
    .a16
    .i16
    lda $E6
    cmp #11
    bne W6_EnemyDecision__done
    lda #1
    sta $E6
    bra W6_EnemyDecision__done
W6_EnemyDecision__chase:
    .a16
    .i16
    ; Source enemy_choose_move consumes horizontal then depth rand32 only when
    ; stalltime < source time. Horizontal approach is forced beyond 160 px.
    lda.l $40A014,x
    sec
    sbc $14
    jsl W6_TargetAbs
    sta $AC
    lda $D2
    cmp $EE
    bcs W6_EnemyDecision__check_low_time
    jmp W6_EnemyDecision__move
W6_EnemyDecision__check_low_time:
    bne W6_EnemyDecision__choose
    lda $D0
    cmp $EC
    bne W6_EnemyDecision__check_equal_time
    jmp W6_EnemyDecision__move
W6_EnemyDecision__check_equal_time:
    bcs W6_EnemyDecision__choose
    jmp W6_EnemyDecision__move
W6_EnemyDecision__choose:
    .a16
    .i16
    ldx $B0
    bne W6_EnemyDecision__velocity_bound
    jmp W6_EnemyDecision__movement_binding
W6_EnemyDecision__velocity_bound:
    cpx #$7FF9
    bcc W6_EnemyDecision__velocity_range_ok
    jmp W6_EnemyDecision__movement_binding
W6_EnemyDecision__velocity_range_ok:
    lda #0
    sta.l $40A000,x
    sta.l $40A002,x
    sta.l $40A004,x
    sta.l $40A006,x
    stz $AE
    phd
    lda $36
    tcd
    jsl W6_Random32
    lda $04
    and #7
    pld
    sta $AA
    cmp #3
    bcc W6_EnemyDecision__toward
    lda $AC
    cmp #160
    beq W6_EnemyDecision__random_walk
    bcc W6_EnemyDecision__random_walk
    bra W6_EnemyDecision__toward
W6_EnemyDecision__random_walk:
    .a16
    .i16
    lda $AA
    cmp #5
    bcs W6_EnemyDecision__away
    bra W6_EnemyDecision__depth_choice
W6_EnemyDecision__toward:
    .a16
    .i16
    ldx $B0
    lda $C6
    ldy $1A
    bne W6_EnemyDecision__store_x_velocity
    eor #$FFFF
    inc a
    bra W6_EnemyDecision__store_x_velocity
W6_EnemyDecision__away:
    .a16
    .i16
    ldx $B0
    lda $C6
    lsr a
    ldy $1A
    beq W6_EnemyDecision__store_x_velocity
    eor #$FFFF
    inc a
W6_EnemyDecision__store_x_velocity:
    .a16
    .i16
    sta.l $40A000,x
    lda #0
    sta.l $40A002,x
    lda #1
    sta $AE
W6_EnemyDecision__depth_choice:
    .a16
    .i16
    phd
    lda $36
    tcd
    jsl W6_Random32
    lda $04
    and #7
    pld
    cmp #2
    bcc W6_EnemyDecision__depth_negative
    cmp #6
    bcs W6_EnemyDecision__depth_positive
    bra W6_EnemyDecision__choose_role
W6_EnemyDecision__depth_negative:
    .a16
    .i16
    ldx $B0
    lda $C6
    lsr a
    eor #$FFFF
    inc a
    sta.l $40A004,x
    lda #0
    sta.l $40A006,x
    lda #1
    sta $AE
    bra W6_EnemyDecision__choose_role
W6_EnemyDecision__depth_positive:
    .a16
    .i16
    ldx $B0
    lda $C6
    lsr a
    sta.l $40A004,x
    lda #0
    sta.l $40A006,x
    lda #1
    sta $AE
W6_EnemyDecision__choose_role:
    .a16
    .i16
    lda $AE
    beq W6_EnemyDecision__select_idle
    lda $A6
    bra W6_EnemyDecision__set_role
W6_EnemyDecision__select_idle:
    .a16
    .i16
    lda $38
W6_EnemyDecision__set_role:
    .a16
    .i16
    stz $FA
    jsl W6_SetRole
    lda $FC
    beq W6_EnemyDecision__role_ok
    jmp W6_EnemyDecision__done
W6_EnemyDecision__role_ok:
    lda $E4
    cmp $A6
    bne W6_EnemyDecision__set_deadline
    ldx $B0
    lda.l $40A000,x
    beq W6_EnemyDecision__set_deadline
    bmi W6_EnemyDecision__velocity_left
    lda $1A
    bne W6_EnemyDecision__frame_forward
    bra W6_EnemyDecision__frame_reverse
W6_EnemyDecision__velocity_left:
    .a16
    .i16
    lda $1A
    beq W6_EnemyDecision__frame_forward
W6_EnemyDecision__frame_reverse:
    .a16
    .i16
    lda #$FFFF
    sta $10
    bra W6_EnemyDecision__set_deadline
W6_EnemyDecision__frame_forward:
    .a16
    .i16
    lda #1
    sta $10
W6_EnemyDecision__set_deadline:
    .a16
    .i16
    lda $D0
    clc
    adc #200
    sta $EC
    lda $D2
    adc #0
    sta $EE
W6_EnemyDecision__move:
    .a16
    .i16
    jsl W6_EnemyApplyMovement
    jmp W6_EnemyDecision__done
W6_EnemyDecision__movement_binding:
    .a16
    .i16
    lda #7
    sta $FC
    jmp W6_EnemyDecision__done
W6_EnemyDecision__runoff:
    .a16
    .i16
    ldx $B0
    bne W6_EnemyDecision__runoff_bound
    jmp W6_EnemyDecision__movement_binding
W6_EnemyDecision__runoff_bound:
    cpx #$7FF9
    bcc W6_EnemyDecision__runoff_range_ok
    jmp W6_EnemyDecision__movement_binding
W6_EnemyDecision__runoff_range_ok:
    lda $C6
    lsr a
    ldy $1A
    beq W6_EnemyDecision__runoff_store
    eor #$FFFF
    inc a
W6_EnemyDecision__runoff_store:
    .a16
    .i16
    sta.l $40A000,x
    lda #0
    sta.l $40A002,x
    sta.l $40A004,x
    sta.l $40A006,x
    jsl W6_EnemyApplyMovement
    lda $D2
    cmp $EE
    bcs W6_EnemyDecision__runoff_low_time
    jmp W6_EnemyDecision__done
W6_EnemyDecision__runoff_low_time:
    bne W6_EnemyDecision__runoff_expired
    lda $D0
    cmp $EC
    bne W6_EnemyDecision__runoff_equal_time
    jmp W6_EnemyDecision__done
W6_EnemyDecision__runoff_equal_time:
    bcs W6_EnemyDecision__runoff_expired
    jmp W6_EnemyDecision__done
W6_EnemyDecision__runoff_expired:
    .a16
    .i16
    lda #1
    sta $E6
    jmp W6_EnemyDecision__done
W6_EnemyDecision__attack:
    .a16
    .i16
    jml W6_EnemyAttack
W6_EnemyDecision__blocked:
    .a16
    .i16
    lda #13
    sta $FC
    rtl

W6_EnemyPrepare:
    .a16
    .i16
    lda $D2
    cmp $EE
    bcc W6_EnemyPrepare__done
    bne W6_EnemyPrepare__ready
    lda $D0
    cmp $EC
    bcc W6_EnemyPrepare__done
W6_EnemyPrepare__ready:
    .a16
    .i16
    jsl W6_EnemyInRange
    bcc W6_EnemyPrepare__retry
    stz $FA
    lda $A0
    jsl W6_SetRole
    lda #12
    sta $E6
W6_EnemyPrepare__done:
    .a16
    .i16
    rtl
W6_EnemyPrepare__retry:
    .a16
    .i16
    lda #1
    sta $E6
    rtl

; Direction was just selected toward target. Distance is nonnegative and
; bounded8190. Source strict minimum/maximum comparisons preserve equality.
W6_EnemyInRange:
    .a16
    .i16
    ldx $34
    lda.l $40A014,x
    sec
    sbc $14
    jsl W6_TargetAbs
    sta $AA
    lda $A2
    bmi W6_EnemyInRange__maximum
    cmp $AA
    bcs W6_EnemyInRange__miss
W6_EnemyInRange__maximum:
    .a16
    .i16
    lda $A4
    bmi W6_EnemyInRange__miss
    beq W6_EnemyInRange__miss
    cmp $AA
    beq W6_EnemyInRange__miss
    bcc W6_EnemyInRange__miss
    sec
    rtl
W6_EnemyInRange__miss:
    .a16
    .i16
    clc
    rtl

W6_EnemyAttack:
    .a16
    .i16
    lda $08
    ora #1
    sta $08
    lda $06
    sta $F4
    lda $10
    bne W6_EnemyAttack__done
    lda $08
    and #$FFFE
    sta $08
    jsl W6_StopMovement
    lda $FC
    bne W6_EnemyAttack__done
    jsl W6_SelectTarget
    lda $FC
    bne W6_EnemyAttack__done
    lda $34
    beq W6_EnemyAttack__idle
    tax
    lda.l $40A014,x
    sec
    sbc $14
    jsl W6_TargetAbs
    cmp #80
    bcs W6_EnemyAttack__idle
    phd
    lda $36
    tcd
    jsl W6_Random32
    lda $04
    pld
    and #3
    beq W6_EnemyAttack__idle
    stz $FA
    lda $A6
    jsl W6_SetRole
    lda #13
    sta $E6
    bra W6_EnemyAttack__deadline
W6_EnemyAttack__idle:
    .a16
    .i16
    stz $FA
    lda $38
    jsl W6_SetRole
    lda #1
    sta $E6
W6_EnemyAttack__deadline:
    .a16
    .i16
    lda $D0
    clc
    adc #200
    sta $EC
    lda $D2
    adc #0
    sta $EE
W6_EnemyAttack__done:
    .a16
    .i16
    rtl

; Apply the retained source x/z velocity once per enemy-think callback. The
; model linker stores speed in twentieths; integer actor coordinates retain a
; signed twentieth-pixel remainder, preserving exact authored decimal speeds.
W6_EnemyApplyMovement:
    rep #$30
    .a16
    .i16
    lda $B0
    beq W6_EnemyApplyMovement__binding
    cmp #$7FF9
    bcs W6_EnemyApplyMovement__binding
    ldx $B0
    lda.l $40A004,x
    beq W6_EnemyApplyMovement__x
    lda $16
    cmp #160
    bcs W6_EnemyApplyMovement__z_high
    lda $C6
    lsr a
    sta.l $40A004,x
    lda #0
    sta.l $40A006,x
    bra W6_EnemyApplyMovement__x
W6_EnemyApplyMovement__z_high:
    .a16
    .i16
    cmp #233
    bcc W6_EnemyApplyMovement__x
    lda $C6
    lsr a
    eor #$FFFF
    inc a
    sta.l $40A004,x
    lda #0
    sta.l $40A006,x
W6_EnemyApplyMovement__x:
    .a16
    .i16
    stz $90
    stz $92
    stz $94
    jsl W6_EnemyApplyAxis
    lda #2
    sta $90
    sta $92
    lda #4
    sta $94
    jsl W6_EnemyApplyAxis
    rtl
W6_EnemyApplyMovement__binding:
    .a16
    .i16
    lda #7
    sta $FC
    rtl

; Generic axis accumulator. $90=remainder offset, $92=position offset,
; $94=velocity offset in the eight-byte B0 block. Divide toward zero, then
; keep the canonical integer position truncated toward zero (as BOR does for
; collision/raster coordinates).
W6_EnemyApplyAxis:
    .a16
    .i16
    lda $B0
    clc
    adc $94
    tax
    lda.l $40A000,x
    sta $96
    bne W6_EnemyApplyAxis__velocity
    jmp W6_EnemyApplyAxis__done
W6_EnemyApplyAxis__velocity:
    ldx $90
    lda $D8,x
    clc
    adc $96
    sta $AA
    bmi W6_EnemyApplyAxis__negative
    stz $AE
W6_EnemyApplyAxis__positive_loop:
    .a16
    .i16
    cmp #20
    bcc W6_EnemyApplyAxis__positive_remainder
    sec
    sbc #20
    inc $AE
    bra W6_EnemyApplyAxis__positive_loop
W6_EnemyApplyAxis__positive_remainder:
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
    bra W6_EnemyApplyAxis__normalize
W6_EnemyApplyAxis__negative:
    .a16
    .i16
    eor #$FFFF
    inc a
    stz $AE
W6_EnemyApplyAxis__negative_loop:
    .a16
    .i16
    cmp #20
    bcc W6_EnemyApplyAxis__negative_remainder
    sec
    sbc #20
    inc $AE
    bra W6_EnemyApplyAxis__negative_loop
W6_EnemyApplyAxis__negative_remainder:
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
W6_EnemyApplyAxis__normalize:
    .a16
    .i16
    ldx $92
    lda $14,x
    bmi W6_EnemyApplyAxis__negative_position
    beq W6_EnemyApplyAxis__store_remainder
    lda $98
    bpl W6_EnemyApplyAxis__store_remainder
    lda $14,x
    dec a
    sta $14,x
    lda $98
    clc
    adc #20
    sta $98
    bra W6_EnemyApplyAxis__store_remainder
W6_EnemyApplyAxis__negative_position:
    .a16
    .i16
    lda $98
    bmi W6_EnemyApplyAxis__store_remainder
    ldx $92
    lda $14,x
    inc a
    sta $14,x
    lda $98
    sec
    sbc #20
    sta $98
W6_EnemyApplyAxis__store_remainder:
    .a16
    .i16
    ldx $90
    lda $98
    sta $D8,x
W6_EnemyApplyAxis__done:
    .a16
    .i16
    rtl

W6_Think:
    rep #$30
    .a16
    .i16
    lda $E6
    cmp #2
    beq WHost_Recovery
    cmp #3
    beq WHost_Recovery
    cmp #4
    beq WHost_Lifecycle
    cmp #5
    beq WHost_Lifecycle
    cmp #6
    beq WHost_Lifecycle
    cmp #7
    bne W6_Think__not_pain
    jml WHost_PlayerPain
W6_Think__not_pain:
    .a16
    .i16
    cmp #8
    beq WHost_PlayerAction
    cmp #9
    bne W6_Think__enemy
    jml WHost_PlayerAttack
W6_Think__enemy:
    .a16
    .i16
    jsl W6_EnemyDecision
    jsl WHost_PublishTarget
    rtl
WHost_Recovery:
    .a16
    .i16
    jml W6_RecoveryThink
WHost_Lifecycle:
    .a16
    .i16
    jml W6_GroundLifecycle

; Target publication is a real production-slot handle, not a context address.
; Selection itself remains the already-proven W6_SelectTarget implementation.
WHost_PublishTarget:
    .a16
    .i16
    lda $34
    beq WHost_PublishTarget__none
    tax
    lda.l $40A0F6,x
    beq WHost_PublishTarget__none
    lda.l $40A07A,x
    clc
    adc #$0A00
    bra WHost_PublishTarget__store
WHost_PublishTarget__none:
    .a16
    .i16
    lda #0
WHost_PublishTarget__store:
    .a16
    .i16
    ldx $7A
    sta.l WBridge_TargetHandle,x
    rtl

WHost_ClearRemovedReferences:
    .a16
    .i16
    lda $7A
    clc
    adc #$0A00
    sta $AA
    ldx #0
WHost_ClearRemovedReferences__slot:
    .a16
    .i16
    lda.l WBridge_TargetHandle,x
    cmp $AA
    bne WHost_ClearRemovedReferences__next
    lda #0
    sta.l WBridge_TargetHandle,x
WHost_ClearRemovedReferences__next:
    .a16
    .i16
    txa
    clc
    adc #CHAR_ZP_LEN
    tax
    cpx #CHAR_ZP_LEN*6
    bcc WHost_ClearRemovedReferences__slot
    rtl

; Normal's persistent player controller consumes only the current worker-tick
; input words. Held directions advance the canonical source position at the
; model's authored speed20, using the same twentieth-pixel accumulator as the
; source enemy driver. Attack remains an edge from that same tick record.
WHost_PlayerAction:
    sep #$20
    .a8
    lda CHAR_SELECTED
    cmp #CHAR_SELECTED_JUMP
    bne WHost_PlayerAction__grounded
    ; BOR's Jump_PlayerTick remains the sole owner of the existing 60-Hz
    ; airborne X/Z transition. Do not apply the persistent 200-Hz grounded
    ; controller while that native substate is active.
    jml WHost_PlayerAction__done
WHost_PlayerAction__grounded:
    rep #$30
    .a16
    .i16
    jsl WHost_PlayerMove
    jsl WHost_PlayerInputTrigger
    and #$4000
    bne WHost_PlayerAction__attack
WHost_PlayerAction__ordinary:
    .a16
    .i16
    ldx $7A
    lda.l WHost_Action,x
    cmp #$FFFF
    beq WHost_PlayerAction__locomotion
    cmp $A0
    beq WHost_PlayerAction__attack
    jml WHost_PlayerAction__unsupported
WHost_PlayerAction__attack:
    ldx $7A
    lda #$FFFF
    sta.l WHost_Action,x
    stz $FA
    lda $A0
    jsl W6_SetRole
    lda $08
    ora #1
    sta $08
    lda #9
    sta $E6
    rtl
WHost_PlayerAction__locomotion:
    jsl WHost_PlayerInputHeld
    and #$0F00
    beq WHost_PlayerAction__idle
    lda $A6
    bra WHost_PlayerAction__set_locomotion
WHost_PlayerAction__idle:
    lda $38
WHost_PlayerAction__set_locomotion:
    stz $FA
    jsl W6_SetRole
    lda #8
    sta $E6
WHost_PlayerAction__done:
    .a16
    .i16
    rtl
WHost_PlayerAction__unsupported:
    .a16
    .i16
    lda #15
    sta $FC
    rtl
WHost_PlayerAttack:
    .a16
    .i16
    jsl WHost_PlayerMove
    lda $10
    bne WHost_PlayerAction__done
    lda $08
    and #$FFFE
    sta $08
    bra WHost_PlayerIdle
WHost_PlayerPain:
    .a16
    .i16
    ; No special-input/grab fallback. Controlled fixture supplies no input.
    lda $C4
    bne WHost_PlayerAction__unsupported
    lda $10
    bne WHost_PlayerAction__done
WHost_PlayerIdle:
    .a16
    .i16
    stz $FA
    lda $38
    jsl W6_SetRole
    lda #8
    sta $E6
    rtl

; Return the per-tick held or edge word for the currently bound player.
; Production P1/P2 occupy physical context rows 0 and CHAR_ZP_LEN.
WHost_PlayerInputHeld:
    .a16
    .i16
    lda $7A
    cmp #CHAR_ZP_LEN
    beq WHost_PlayerInputHeld__p2
    lda.l WHost_InputP1Press
    rtl
WHost_PlayerInputHeld__p2:
    lda.l WHost_InputP2Press
    rtl

WHost_PlayerInputTrigger:
    .a16
    .i16
    lda $7A
    cmp #CHAR_ZP_LEN
    beq WHost_PlayerInputTrigger__p2
    lda.l WHost_InputP1Trigger
    rtl
WHost_PlayerInputTrigger__p2:
    lda.l WHost_InputP2Trigger
    rtl

; Move the player in SOURCE_EXACT coordinates. The PAK-derived model speed is
; stored in twentieths; W6_EnemyApplyAxis retains signed twentieth-pixel
; remainders in this actor context, so 0.9/1.2 authored speeds do not drift.
; Left wins over right and up wins over down, matching Character_PlayFrame.
; B doubles speed. Direction/role and coordinates all belong to this one SA-1
; pass; the S-CPU consumes only the next coherent snapshot.
WHost_PlayerMove:
    .a16
    .i16
    jsl WHost_PlayerInputHeld
    sta $B4
    and #$0300
    beq WHost_PlayerMove__x_stop
    and #$0200
    beq WHost_PlayerMove__x_right
    lda $C6
    eor #$FFFF
    inc a
    bra WHost_PlayerMove__x_speed
WHost_PlayerMove__x_right:
    lda $C6
WHost_PlayerMove__x_speed:
    sta $B6
    lda $B4
    and #$8000
    beq WHost_PlayerMove__x_load
    lda $B6
    asl a
    sta $B6
WHost_PlayerMove__x_load:
    lda $B6
    bra WHost_PlayerMove__x_store
WHost_PlayerMove__x_stop:
    lda #0
    sta $B6
WHost_PlayerMove__x_store:
    ldx $B0
    sta.l $40A000,x
    stz $90
    stz $92
    stz $94
    jsl W6_EnemyApplyAxis
    ; The S-CPU's Character_PlayFrame clamps player X to WorldMaxX after a
    ; horizontal step. Persistent ownership must preserve that stage-local
    ; rule too; otherwise an actor carried from a wider previous stage can
    ; walk past the new stage and eventually exceed the snapshot bridge's
    ; admitted source-coordinate domain. Left wins over right, and only the
    ; selected direction's native clamp is applied.
    lda.l WHost_Mode
    cmp #1
    bne WHost_PlayerMove__x_bound_done
    lda.l S7Resident_Owner
    cmp #2
    bne WHost_PlayerMove__x_bound_done
    lda $B4
    and #$0300
    beq WHost_PlayerMove__x_bound_done
    and #$0200
    beq WHost_PlayerMove__x_bound_right
    lda $14
    bpl WHost_PlayerMove__x_bound_done
    stz $14
    bra WHost_PlayerMove__x_bound_done
WHost_PlayerMove__x_bound_right:
    lda $14
    cmp.l WHost_PlayerWorldMaxX
    bcc WHost_PlayerMove__x_bound_done
    beq WHost_PlayerMove__x_bound_done
    lda.l WHost_PlayerWorldMaxX
    sta $14
WHost_PlayerMove__x_bound_done:

    lda $B4
    and #$0C00
    beq WHost_PlayerMove__y_stop
    and #$0800
    beq WHost_PlayerMove__y_down
    lda $C6
    eor #$FFFF
    inc a
    bra WHost_PlayerMove__y_speed
WHost_PlayerMove__y_down:
    lda $C6
WHost_PlayerMove__y_speed:
    sta $B6
    lda $B4
    and #$8000
    beq WHost_PlayerMove__y_load
    lda $B6
    asl a
    sta $B6
WHost_PlayerMove__y_load:
    lda $B6
    bra WHost_PlayerMove__y_store
WHost_PlayerMove__y_stop:
    lda #0
    sta $B6
WHost_PlayerMove__y_store:
    sta $B6
    ldx $B0
    txa
    clc
    adc #4
    tax
    lda $B6
    sta.l $40A000,x
    lda #2
    sta $90
    sta $92
    lda #4
    sta $94
    jsl W6_EnemyApplyAxis

    lda $B4
    and #$0300
    beq WHost_PlayerMove__done
    and #$0200
    bne WHost_PlayerMove__left
    lda #1
    sta $1A
    rtl
WHost_PlayerMove__left:
    lda #0
    sta $1A
WHost_PlayerMove__done:
    rtl

W6_FrameChanged:
    rep #$30
    .a16
    .i16
    ldx $7A
    lda $06
    sta.l WHost_Frame,x
    lda $E4
    cmp $38
    beq W6_FrameChanged__idle
    cmp $A6
    beq W6_FrameChanged__walk
    cmp $A0
    beq W6_FrameChanged__attack
    cmp $3A
    beq W6_FrameChanged__pain
    cmp $3C
    beq W6_FrameChanged__rise
    lda $A8
    and #$00FF
    cmp $E4
    beq W6_FrameChanged__jump
    lda #$00FF
    bra W6_FrameChanged__store_role
W6_FrameChanged__idle:
    lda #0
    bra W6_FrameChanged__store_role
W6_FrameChanged__walk:
    lda #1
    bra W6_FrameChanged__store_role
W6_FrameChanged__attack:
    lda #2
    bra W6_FrameChanged__store_role
W6_FrameChanged__rise:
    lda #5
    bra W6_FrameChanged__store_role
W6_FrameChanged__jump:
    lda #7
    bra W6_FrameChanged__store_role
W6_FrameChanged__pain:
    lda #8
W6_FrameChanged__store_role:
    sta.l WHost_Role,x
    lda.l WHost_FrameEvents
    inc a
    sta.l WHost_FrameEvents
    lda $E4
    sta.l $41243E
    lda #1
    ldx $7A
    ldy $06
    jsl S6_EventPush
    rtl

W6_WorldHealth:
    rep #$30
    .a16
    .i16
    jml W6_DisplayHealth

W6_WorldLost:
    rep #$30
    .a16
    .i16
    lda.l Screen_PosX
    ; The display camera need not land on the exact 4-pixel source lattice.
    ; Use each bound actor's compiler-selected inverse policy, just like
    ; bridge import; Normal's 5/4 projection is intentionally rounded.
    jsl WBridge_UnprojectPolicy
    bcs WHost_EnvironmentBlocked
    sec
    sbc #1000
    sta $AA
    lda $14
    sec
    sbc $AA
    bmi WHost_LostRemove
    lda $18
    eor #$8000
    cmp #$7E0C                ; source a < PIT_DEPTH*2 (-500)
    bcc WHost_LostRemove
    rtl
WHost_LostRemove:
    .a16
    .i16
    jml W6_KillUnlinked
WHost_EnvironmentBlocked:
    ; Projection failure from W6_WorldLost is still fail-closed. Gravity no
    ; longer branches here because its former $C2 test read actor scratch.
    .a16
    .i16
    lda #10
    sta $FC
    rtl

W6_WorldGravity:
    rep #$30
    .a16
    .i16
    ; This pass has no source actor-local gravity state to apply. $C2 is
    ; scratch beyond CharacterEntity's 133-byte contract (e.g. DriftTick's
    ; signed-bound temporary), not a gravity/hole certificate; treating a
    ; stale nonzero value as fatal faulted ordinary Normal actors. Authored
    ; stage hazards are serviced by StageBoundsHost_Physics/Enter on the
    ; gameplay path before the resident-world tick.
    rtl

W6_WorldAttack:
    rep #$30
    .a16
    .i16
    ; BOR.C gates the entire target scan on this source frame's attack.
    ; An inactive frame resets attack_id once, even with no live targets.
    ; Do not repeatedly decode the identical inactive frame for each target.
    jsl W6_CheckPolicy
    bcs W6_WorldAttack__done
    jsl W5_ActivateAttack
    lda $0A
    bne W6_WorldAttack__active
    stz $DC
    stz $DE
    rtl
W6_WorldAttack__active:
    .a16
    .i16
    ; Scan stable source slot order, not just the selected AI target.
    stz $AC
W6_WorldAttack__slot:
    .a16
    .i16
    lda $AC
    asl a
    tax
    lda.l WHost_SlotTable,x
    sta $34
    tax
    lda.l $40A0F6,x
    bne W6_WorldAttack__bound_target
    ; Typed props and the special Biker remain S-CPU-owned. Publish only a
    ; compact, ordered query for a live marked physical slot; the normal relay
    ; then runs BOR's exact native AABB/invulnerability/damage/reward/reveal
    ; path on its canonical CharacterEntity state. Worker enemies and scenery
    ; never become duplicate simulated contexts.
    lda $F2
    cmp #1
    bne W6_WorldAttack__next
    lda $AC
    beq W6_WorldAttack__next
    tax
    lda.l $412D00,x
    beq W6_WorldAttack__next
    lda $16
    and #$00FF
    sta.l $41243A
    lda $AC
    xba
    and #$FF00
    ora.l $41243A
    tay
    ldx $14
    ; Event D is consumed by the S-CPU relay and names the paired host-side
    ; CharacterEntity window. SA-1 source contexts live at $1900-$1EFF while
    ; their host owner windows are $7900-$7EFF; translate only the source
    ; range so an already host-qualified D value remains unchanged.
    phd
    php
    tdc
    cmp #$1900
    bcc W6_WorldAttack__native_owner_ready
    cmp #$1F00
    bcs W6_WorldAttack__native_owner_ready
    clc
    adc #$6000
    tcd
W6_WorldAttack__native_owner_ready:
    plp
    lda #4
    jsl S6_EventPush
    pld
    bra W6_WorldAttack__next
W6_WorldAttack__bound_target:
    jsl W6_TryHitOne
    lda $FC
    bne W6_WorldAttack__done
W6_WorldAttack__next:
    .a16
    .i16
    inc $AC
    lda $AC
    cmp #6
    bcc W6_WorldAttack__slot
W6_WorldAttack__done:
    .a16
    .i16
    rtl

W6_HitEffects:
    rep #$30
    .a16
    .i16
    ; This publication is NOT a complete flash/audio/combo/effects binding.
    ; Keep the full effect category un-certified until its consumers exist.
    lda.l WHost_HitEvents
    inc a
    sta.l WHost_HitEvents
    ldx $34
    lda.l $40A0F0,x
    tay
    lda.l $40A0BA,x
    sta.l $41243E
    ldx $34
    lda #2
    jsl S6_EventPush
    rtl

WBridge_UnprojectPolicy:
    .a16
    .i16
    phx
    pha
    ldx $7A
    lda.l WBridge_Policy,x
    and #$00FF
    cmp #2
    beq WBridge_UnprojectPolicy__rounded
    pla
    plx
    jml WBridge_Unproject
WBridge_UnprojectPolicy__rounded:
    pla
    plx
    jml WBridge_UnprojectRounded

WBridge_UnprojectRounded:
    .a16
    .i16
    sta.l WBridge_Temp80
    clc
    adc #13106
    cmp #26213
    bcs WBridge_Unproject__bad
    lda #0
    sta.l WBridge_Temp86
    lda.l WBridge_Temp80
    bpl WBridge_UnprojectRounded__magnitude
    pha
    lda.l WBridge_Temp86
    inc a
    sta.l WBridge_Temp86
    pla
    eor #$FFFF
    inc a
WBridge_UnprojectRounded__magnitude:
    sta.l WBridge_Temp80
    asl a
    asl a
    clc
    adc.l WBridge_Temp80
    clc
    adc #2
    lsr a
    lsr a
    pha
    lda.l WBridge_Temp86
    tay
    pla
    cpy #0
    beq WBridge_UnprojectRounded__done
    eor #$FFFF
    inc a
WBridge_UnprojectRounded__done:
    clc
    rtl

; Signed target integer -> source integer; carry set rejects non-lattice
; values on policy 1 or values beyond the target selection proof's bound.
WBridge_Unproject:
    .a16
    .i16
    sta.l WBridge_Temp80
    and #3
    bne WBridge_Unproject__bad
    lda.l WBridge_Temp80
    clc
    adc #13106
    cmp #26213
    bcs WBridge_Unproject__bad
    lda.l WBridge_Temp80
    cmp #$8000
    ror a
    cmp #$8000
    ror a
    sta.l WBridge_Temp82
    asl a
    asl a
    clc
    adc.l WBridge_Temp82
    clc
    rtl
WBridge_Unproject__bad:
    .a16
    .i16
    sec
    rtl

; Signed source integer -> production integer on the admitted5-pixel lattice.
; Exact bounded integer conversion, not floating evaluation or approximation.
; abs(n)=256*h+l, 256=51*5+1, hence n/5=51*h+(h+l)/5.
; h<=63 and h+l<=318. Tables reject every nonzero remainder. No hardware
; divider ownership/NMI dependency. X preserved; Y/scratch clobbered as before.
WBridge_Project:
    .a16
    .i16
    phx
    sta.l WBridge_Temp80
    clc
    adc #16383
    cmp #32767
    bcs WBridge_Project__bad
    lda #0
    sta.l WBridge_Temp86
    lda.l WBridge_Temp80
    bpl WBridge_Project__positive
    pha
    lda.l WBridge_Temp86
    inc a
    sta.l WBridge_Temp86
    pla
    eor #$FFFF
    inc a
WBridge_Project__positive:
    .a16
    .i16
    sta.l WBridge_Temp80
    xba
    and #$003F
    sta.l WBridge_Temp82
    asl a
    tax
    lda.l WBridge_ProjectHigh,x
    sta.l WBridge_Temp84
    lda.l WBridge_Temp80
    and #$00FF
    clc
    adc.l WBridge_Temp82
    asl a
    tax
    lda.l WBridge_ProjectLow,x
    bmi WBridge_Project__bad
    clc
    adc.l WBridge_Temp84
    pha
    lda.l WBridge_Temp86
    tay
    pla
    cpy #0
    beq WBridge_Project__done
    eor #$FFFF
    inc a
WBridge_Project__done:
    .a16
    .i16
    plx
    clc
    rtl
WBridge_Project__bad:
    .a16
    .i16
    plx
    sec
    rtl

; Normal policy 2: nearest 4/5 projection. abs(n)=256*h+l and
; 4*n/5=204*h+4*(h+l)/5. The compact second table avoids a divider in the
; per-tick export path. Policy 1 continues to use the exact-only table below.
WBridge_ProjectRounded:
    .a16
    .i16
    phx
    sta.l WBridge_Temp80
    clc
    adc #16383
    cmp #32767
    bcs WBridge_ProjectRounded__bad
    lda #0
    sta.l WBridge_Temp86
    lda.l WBridge_Temp80
    bpl WBridge_ProjectRounded__positive
    pha
    lda.l WBridge_Temp86
    inc a
    sta.l WBridge_Temp86
    pla
    eor #$FFFF
    inc a
WBridge_ProjectRounded__positive:
    sta.l WBridge_Temp80
    xba
    and #$003F
    sta.l WBridge_Temp82
    asl a
    tax
    lda.l WBridge_ProjectHigh,x
    sta.l WBridge_Temp84
    lda.l WBridge_Temp80
    and #$00FF
    clc
    adc.l WBridge_Temp82
    asl a
    tax
    lda.l WBridge_ProjectRoundedLow,x
    clc
    adc.l WBridge_Temp84
    pha
    lda.l WBridge_Temp86
    tay
    pla
    cpy #0
    beq WBridge_ProjectRounded__done
    eor #$FFFF
    inc a
WBridge_ProjectRounded__done:
    plx
    clc
    rtl
WBridge_ProjectRounded__bad:
    plx
    sec
    rtl

WBridge_ProjectHigh:
    .dw $0000,$00CC,$0198,$0264,$0330,$03FC,$04C8,$0594,$0660,$072C,$07F8,$08C4
    .dw $0990,$0A5C,$0B28,$0BF4,$0CC0,$0D8C,$0E58,$0F24,$0FF0,$10BC,$1188,$1254
    .dw $1320,$13EC,$14B8,$1584,$1650,$171C,$17E8,$18B4,$1980,$1A4C,$1B18,$1BE4
    .dw $1CB0,$1D7C,$1E48,$1F14,$1FE0,$20AC,$2178,$2244,$2310,$23DC,$24A8,$2574
    .dw $2640,$270C,$27D8,$28A4,$2970,$2A3C,$2B08,$2BD4,$2CA0,$2D6C,$2E38,$2F04
    .dw $2FD0,$309C,$3168,$3234
WBridge_ProjectRoundedLow:
    .dw $0000,$0001,$0002,$0002,$0003,$0004,$0005,$0006,$0006,$0007,$0008,$0009,$000A,$000A,$000B,$000C
    .dw $000D,$000E,$000E,$000F,$0010,$0011,$0012,$0012,$0013,$0014,$0015,$0016,$0016,$0017,$0018,$0019
    .dw $001A,$001A,$001B,$001C,$001D,$001E,$001E,$001F,$0020,$0021,$0022,$0022,$0023,$0024,$0025,$0026
    .dw $0026,$0027,$0028,$0029,$002A,$002A,$002B,$002C,$002D,$002E,$002E,$002F,$0030,$0031,$0032,$0032
    .dw $0033,$0034,$0035,$0036,$0036,$0037,$0038,$0039,$003A,$003A,$003B,$003C,$003D,$003E,$003E,$003F
    .dw $0040,$0041,$0042,$0042,$0043,$0044,$0045,$0046,$0046,$0047,$0048,$0049,$004A,$004A,$004B,$004C
    .dw $004D,$004E,$004E,$004F,$0050,$0051,$0052,$0052,$0053,$0054,$0055,$0056,$0056,$0057,$0058,$0059
    .dw $005A,$005A,$005B,$005C,$005D,$005E,$005E,$005F,$0060,$0061,$0062,$0062,$0063,$0064,$0065,$0066
    .dw $0066,$0067,$0068,$0069,$006A,$006A,$006B,$006C,$006D,$006E,$006E,$006F,$0070,$0071,$0072,$0072
    .dw $0073,$0074,$0075,$0076,$0076,$0077,$0078,$0079,$007A,$007A,$007B,$007C,$007D,$007E,$007E,$007F
    .dw $0080,$0081,$0082,$0082,$0083,$0084,$0085,$0086,$0086,$0087,$0088,$0089,$008A,$008A,$008B,$008C
    .dw $008D,$008E,$008E,$008F,$0090,$0091,$0092,$0092,$0093,$0094,$0095,$0096,$0096,$0097,$0098,$0099
    .dw $009A,$009A,$009B,$009C,$009D,$009E,$009E,$009F,$00A0,$00A1,$00A2,$00A2,$00A3,$00A4,$00A5,$00A6
    .dw $00A6,$00A7,$00A8,$00A9,$00AA,$00AA,$00AB,$00AC,$00AD,$00AE,$00AE,$00AF,$00B0,$00B1,$00B2,$00B2
    .dw $00B3,$00B4,$00B5,$00B6,$00B6,$00B7,$00B8,$00B9,$00BA,$00BA,$00BB,$00BC,$00BD,$00BE,$00BE,$00BF
    .dw $00C0,$00C1,$00C2,$00C2,$00C3,$00C4,$00C5,$00C6,$00C6,$00C7,$00C8,$00C9,$00CA,$00CA,$00CB,$00CC
    .dw $00CD,$00CE,$00CE,$00CF,$00D0,$00D1,$00D2,$00D2,$00D3,$00D4,$00D5,$00D6,$00D6,$00D7,$00D8,$00D9
    .dw $00DA,$00DA,$00DB,$00DC,$00DD,$00DE,$00DE,$00DF,$00E0,$00E1,$00E2,$00E2,$00E3,$00E4,$00E5,$00E6
    .dw $00E6,$00E7,$00E8,$00E9,$00EA,$00EA,$00EB,$00EC,$00ED,$00EE,$00EE,$00EF,$00F0,$00F1,$00F2,$00F2
    .dw $00F3,$00F4,$00F5,$00F6,$00F6,$00F7,$00F8,$00F9,$00FA,$00FA,$00FB,$00FC,$00FD,$00FE,$00FE
WBridge_ProjectLow:
    .dw $0000,$8000,$8000,$8000,$8000,$0004,$8000,$8000,$8000,$8000,$0008,$8000
    .dw $8000,$8000,$8000,$000C,$8000,$8000,$8000,$8000,$0010,$8000,$8000,$8000
    .dw $8000,$0014,$8000,$8000,$8000,$8000,$0018,$8000,$8000,$8000,$8000,$001C
    .dw $8000,$8000,$8000,$8000,$0020,$8000,$8000,$8000,$8000,$0024,$8000,$8000
    .dw $8000,$8000,$0028,$8000,$8000,$8000,$8000,$002C,$8000,$8000,$8000,$8000
    .dw $0030,$8000,$8000,$8000,$8000,$0034,$8000,$8000,$8000,$8000,$0038,$8000
    .dw $8000,$8000,$8000,$003C,$8000,$8000,$8000,$8000,$0040,$8000,$8000,$8000
    .dw $8000,$0044,$8000,$8000,$8000,$8000,$0048,$8000,$8000,$8000,$8000,$004C
    .dw $8000,$8000,$8000,$8000,$0050,$8000,$8000,$8000,$8000,$0054,$8000,$8000
    .dw $8000,$8000,$0058,$8000,$8000,$8000,$8000,$005C,$8000,$8000,$8000,$8000
    .dw $0060,$8000,$8000,$8000,$8000,$0064,$8000,$8000,$8000,$8000,$0068,$8000
    .dw $8000,$8000,$8000,$006C,$8000,$8000,$8000,$8000,$0070,$8000,$8000,$8000
    .dw $8000,$0074,$8000,$8000,$8000,$8000,$0078,$8000,$8000,$8000,$8000,$007C
    .dw $8000,$8000,$8000,$8000,$0080,$8000,$8000,$8000,$8000,$0084,$8000,$8000
    .dw $8000,$8000,$0088,$8000,$8000,$8000,$8000,$008C,$8000,$8000,$8000,$8000
    .dw $0090,$8000,$8000,$8000,$8000,$0094,$8000,$8000,$8000,$8000,$0098,$8000
    .dw $8000,$8000,$8000,$009C,$8000,$8000,$8000,$8000,$00A0,$8000,$8000,$8000
    .dw $8000,$00A4,$8000,$8000,$8000,$8000,$00A8,$8000,$8000,$8000,$8000,$00AC
    .dw $8000,$8000,$8000,$8000,$00B0,$8000,$8000,$8000,$8000,$00B4,$8000,$8000
    .dw $8000,$8000,$00B8,$8000,$8000,$8000,$8000,$00BC,$8000,$8000,$8000,$8000
    .dw $00C0,$8000,$8000,$8000,$8000,$00C4,$8000,$8000,$8000,$8000,$00C8,$8000
    .dw $8000,$8000,$8000,$00CC,$8000,$8000,$8000,$8000,$00D0,$8000,$8000,$8000
    .dw $8000,$00D4,$8000,$8000,$8000,$8000,$00D8,$8000,$8000,$8000,$8000,$00DC
    .dw $8000,$8000,$8000,$8000,$00E0,$8000,$8000,$8000,$8000,$00E4,$8000,$8000
    .dw $8000,$8000,$00E8,$8000,$8000,$8000,$8000,$00EC,$8000,$8000,$8000,$8000
    .dw $00F0,$8000,$8000,$8000,$8000,$00F4,$8000,$8000,$8000,$8000,$00F8,$8000
    .dw $8000,$8000,$8000,$00FC,$8000,$8000,$8000

WHost_SlotTable:
    .dw $7900,$7A00,$7B00,$7C00,$7D00,$7E00

W5_HostRandom03:
    .a16
    .i16
    lda #$FFFF
    sta $BE
    lda #10
    sta $FC
    rtl

S6_EventPush:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    sta.l $412436
    txa
    sta.l $412438
    tya
    sta.l $41243A
    tdc
    sta.l $41243C
    lda.l $412430
    sec
    sbc.l $412432
    cmp #128
    bcs S6_EventPush__overflow
    lda.l $412430
    and #$007F
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l $412430
    sta.l $412450,x
    lda.l $412436
    sta.l $412452,x
    lda.l $41173C
    sta.l $412454,x
    lda.l $41173E
    sta.l $412456,x
    lda.l $41243C
    sta.l $412458,x
    lda.l $412438
    sta.l $41245A,x
    lda.l $41243A
    sta.l $41245C,x
    lda.l $41243E
    sta.l $41245E,x
S6_EventPush__record_written:
    lda.l $412430
    inc a
    sta.l $412430
    bra S6_EventPush__return
S6_EventPush__overflow:
    lda #1
    sta.l $412434
S6_EventPush__return:
    ply
    plx
    pla
    plp
    rtl
Worker_Gate:
    .a8
    .i16
    lda $3025
    cmp #$55
    beq Worker_Enter
    cmp #$AA
    beq Worker_LegacyAck
    jml Worker_Gate
Worker_LegacyAck:
    .a8
    .i16
    jml $00807E
Worker_Enter:
    php
    phb
    phd
    sep #$20
    .a8
    .i16
    lda #0
    pha
    plb
    lda #8
    sta $2225
    lda #3
    sta $3027
    rep #$30
    .a16
    .i16
    lda #$7700
    tcd
    ; BW-RAM is battery-backed and may contain arbitrary power-on bytes.
    ; Establish a clean worker protocol epoch before the first poll so random
    ; fault/snapshot/remove/event sequence values cannot become live commands.
    lda #0
    sta.l $412002
    sta.l $412004
    sta.l $412008
    sta.l $412430
    sta.l $412432
    sta.l $412434
    sta.l $412436
    sta.l $412438
    sta.l $41243A
    sta.l $41243C
    sta.l $41243E
    sta.l $412440
    sta.l $412442
    sta.l $412444
    sta.l $412446
    sta.l $41200C
    sta.l $7E1778
    sep #$20
    .a8
    lda #0
    sta.l $412006
    sta.l $412007
    sta.l $41200A
    lda #0
    sta.l $412014
    sta.l $412016
    sta.l $412018
    sta.l $41201A
    sta.l $412020
    sta.l $412022
    sta.l $412024
    sta.l $412026
    rep #$30
    .a16
    .i16
Worker_Poll:
    .a16
    .i16
    sep #$20
    .a8
    lda.l $41200A
    beq Worker_NoFault
    jml Worker_FaultWait
Worker_NoFault:
    ; A production birth/retire publication requests a park at this point.
    ; Worker_Poll is reached only after the previous world pass is complete.
    lda.l $41200C
    beq Worker_NoMutationFence
    lda #2
    sta.l $41200C
Worker_MutationFenceWait:
    lda.l $41200C
    bne Worker_MutationFenceWait
    rep #$30
    .a16
    .i16
    jml Worker_Poll
Worker_NoMutationFence:
    rep #$30
    .a16
    .i16
    lda.l $412434
    beq Worker_NoEventOverflow
    jml Worker_EventFault
Worker_NoEventOverflow:
    lda.l $412002
    cmp.l $412004
    beq Worker_NoTick
    jml Worker_Tick
Worker_NoTick:
    lda.l $412440
    cmp.l $412442
    beq Worker_NoRemoveCommand
    lda.l $41173C
    jsl Worker_ApplyRemove
Worker_NoRemoveCommand:
    sep #$20
    .a8
    lda.l $412006
    cmp.l $412007
    bne Worker_HasSnapshot
    jml Worker_Poll
Worker_HasSnapshot:
    and #1
    rep #$30
    .a16
    .i16
    beq Worker_Snapshot_A
    jml Worker_Snapshot_B
Worker_Snapshot_A:
    .a16
    .i16
    lda.l $411700
    sta.l $414000
    lda.l $411702
    sta.l $414002
    lda.l $411704
    sta.l $414004
    lda.l $411706
    sta.l $414006
    lda.l $411708
    sta.l $414008
    lda.l $41170A
    sta.l $41400A
    lda.l $41170C
    sta.l $41400C
    lda.l $41170E
    sta.l $41400E
    lda.l $411710
    sta.l $414010
    lda.l $411712
    sta.l $414012
    lda.l $411714
    sta.l $414014
    lda.l $411716
    sta.l $414016
    lda.l $411718
    sta.l $414018
    lda.l $41171A
    sta.l $41401A
    lda.l $41171C
    sta.l $41401C
    lda.l $41171E
    sta.l $41401E
    lda.l $411720
    sta.l $414020
    lda.l $411722
    sta.l $414022
    lda.l $41173C
    sta.l $414024
    lda.l $41173E
    sta.l $414026
    lda.l $41176C
    sta.l $414028
    lda.l $41176E
    sta.l $41402A
    lda.l $412004
    sta.l $41402E
    lda.l $412002
    sta.l $414030
    lda.l $41200A
    sta.l $414032
    lda.l $411914
    sta.l $414034
    lda.l $411916
    sta.l $414036
    lda.l $411918
    sta.l $414038
    lda.l $41191A
    sta.l $41403A
    lda.l $4119E4
    sta.l $41403C
    lda.l $411906
    sta.l $41403E
    lda.l $4119F6
    sta.l $414040
    lda.l $4119FC
    sta.l $414042
    lda.l $4119F0
    sta.l $414044
    lda.l $411970
    sta.l $414046
    lda.l $411934
    sta.l $414052
    lda.l $4119E6
    sta.l $414054
    lda.l $412146
    sta.l $414048
    lda.l $412140
    sta.l $41404A
    lda.l $41214A
    sta.l $41404C
    lda.l $412154
    sta.l $41404E
    lda.l $412156
    sta.l $414050
    lda.l $412141
    sta.l $414056
    lda.l $411A14
    sta.l $414058
    lda.l $411A16
    sta.l $41405A
    lda.l $411A18
    sta.l $41405C
    lda.l $411A1A
    sta.l $41405E
    lda.l $411AE4
    sta.l $414060
    lda.l $411A06
    sta.l $414062
    lda.l $411AF6
    sta.l $414064
    lda.l $411AFC
    sta.l $414066
    lda.l $411AF0
    sta.l $414068
    lda.l $411A70
    sta.l $41406A
    lda.l $411A34
    sta.l $414076
    lda.l $411AE6
    sta.l $414078
    lda.l $4121CB
    sta.l $41406C
    lda.l $4121C5
    sta.l $41406E
    lda.l $4121CF
    sta.l $414070
    lda.l $4121D9
    sta.l $414072
    lda.l $4121DB
    sta.l $414074
    lda.l $4121C6
    sta.l $41407A
    lda.l $411B14
    sta.l $41407C
    lda.l $411B16
    sta.l $41407E
    lda.l $411B18
    sta.l $414080
    lda.l $411B1A
    sta.l $414082
    lda.l $411BE4
    sta.l $414084
    lda.l $411B06
    sta.l $414086
    lda.l $411BF6
    sta.l $414088
    lda.l $411BFC
    sta.l $41408A
    lda.l $411BF0
    sta.l $41408C
    lda.l $411B70
    sta.l $41408E
    lda.l $411B34
    sta.l $41409A
    lda.l $411BE6
    sta.l $41409C
    lda.l $412250
    sta.l $414090
    lda.l $41224A
    sta.l $414092
    lda.l $412254
    sta.l $414094
    lda.l $41225E
    sta.l $414096
    lda.l $412260
    sta.l $414098
    lda.l $41224B
    sta.l $41409E
    lda.l $411C14
    sta.l $4140A0
    lda.l $411C16
    sta.l $4140A2
    lda.l $411C18
    sta.l $4140A4
    lda.l $411C1A
    sta.l $4140A6
    lda.l $411CE4
    sta.l $4140A8
    lda.l $411C06
    sta.l $4140AA
    lda.l $411CF6
    sta.l $4140AC
    lda.l $411CFC
    sta.l $4140AE
    lda.l $411CF0
    sta.l $4140B0
    lda.l $411C70
    sta.l $4140B2
    lda.l $411C34
    sta.l $4140BE
    lda.l $411CE6
    sta.l $4140C0
    lda.l $4122D5
    sta.l $4140B4
    lda.l $4122CF
    sta.l $4140B6
    lda.l $4122D9
    sta.l $4140B8
    lda.l $4122E3
    sta.l $4140BA
    lda.l $4122E5
    sta.l $4140BC
    lda.l $4122D0
    sta.l $4140C2
    lda.l $411D14
    sta.l $4140C4
    lda.l $411D16
    sta.l $4140C6
    lda.l $411D18
    sta.l $4140C8
    lda.l $411D1A
    sta.l $4140CA
    lda.l $411DE4
    sta.l $4140CC
    lda.l $411D06
    sta.l $4140CE
    lda.l $411DF6
    sta.l $4140D0
    lda.l $411DFC
    sta.l $4140D2
    lda.l $411DF0
    sta.l $4140D4
    lda.l $411D70
    sta.l $4140D6
    lda.l $411D34
    sta.l $4140E2
    lda.l $411DE6
    sta.l $4140E4
    lda.l $41235A
    sta.l $4140D8
    lda.l $412354
    sta.l $4140DA
    lda.l $41235E
    sta.l $4140DC
    lda.l $412368
    sta.l $4140DE
    lda.l $41236A
    sta.l $4140E0
    lda.l $412355
    sta.l $4140E6
    lda.l $411E14
    sta.l $4140E8
    lda.l $411E16
    sta.l $4140EA
    lda.l $411E18
    sta.l $4140EC
    lda.l $411E1A
    sta.l $4140EE
    lda.l $411EE4
    sta.l $4140F0
    lda.l $411E06
    sta.l $4140F2
    lda.l $411EF6
    sta.l $4140F4
    lda.l $411EFC
    sta.l $4140F6
    lda.l $411EF0
    sta.l $4140F8
    lda.l $411E70
    sta.l $4140FA
    lda.l $411E34
    sta.l $414106
    lda.l $411EE6
    sta.l $414108
    lda.l $4123DF
    sta.l $4140FC
    lda.l $4123D9
    sta.l $4140FE
    lda.l $4123E3
    sta.l $414100
    lda.l $4123ED
    sta.l $414102
    lda.l $4123EF
    sta.l $414104
    lda.l $4123DA
    sta.l $41410A
    jml Worker_Snapshot_Ack
Worker_Snapshot_B:
    .a16
    .i16
    lda.l $411700
    sta.l $414110
    lda.l $411702
    sta.l $414112
    lda.l $411704
    sta.l $414114
    lda.l $411706
    sta.l $414116
    lda.l $411708
    sta.l $414118
    lda.l $41170A
    sta.l $41411A
    lda.l $41170C
    sta.l $41411C
    lda.l $41170E
    sta.l $41411E
    lda.l $411710
    sta.l $414120
    lda.l $411712
    sta.l $414122
    lda.l $411714
    sta.l $414124
    lda.l $411716
    sta.l $414126
    lda.l $411718
    sta.l $414128
    lda.l $41171A
    sta.l $41412A
    lda.l $41171C
    sta.l $41412C
    lda.l $41171E
    sta.l $41412E
    lda.l $411720
    sta.l $414130
    lda.l $411722
    sta.l $414132
    lda.l $41173C
    sta.l $414134
    lda.l $41173E
    sta.l $414136
    lda.l $41176C
    sta.l $414138
    lda.l $41176E
    sta.l $41413A
    lda.l $412004
    sta.l $41413E
    lda.l $412002
    sta.l $414140
    lda.l $41200A
    sta.l $414142
    lda.l $411914
    sta.l $414144
    lda.l $411916
    sta.l $414146
    lda.l $411918
    sta.l $414148
    lda.l $41191A
    sta.l $41414A
    lda.l $4119E4
    sta.l $41414C
    lda.l $411906
    sta.l $41414E
    lda.l $4119F6
    sta.l $414150
    lda.l $4119FC
    sta.l $414152
    lda.l $4119F0
    sta.l $414154
    lda.l $411970
    sta.l $414156
    lda.l $411934
    sta.l $414162
    lda.l $4119E6
    sta.l $414164
    lda.l $412146
    sta.l $414158
    lda.l $412140
    sta.l $41415A
    lda.l $41214A
    sta.l $41415C
    lda.l $412154
    sta.l $41415E
    lda.l $412156
    sta.l $414160
    lda.l $412141
    sta.l $414166
    lda.l $411A14
    sta.l $414168
    lda.l $411A16
    sta.l $41416A
    lda.l $411A18
    sta.l $41416C
    lda.l $411A1A
    sta.l $41416E
    lda.l $411AE4
    sta.l $414170
    lda.l $411A06
    sta.l $414172
    lda.l $411AF6
    sta.l $414174
    lda.l $411AFC
    sta.l $414176
    lda.l $411AF0
    sta.l $414178
    lda.l $411A70
    sta.l $41417A
    lda.l $411A34
    sta.l $414186
    lda.l $411AE6
    sta.l $414188
    lda.l $4121CB
    sta.l $41417C
    lda.l $4121C5
    sta.l $41417E
    lda.l $4121CF
    sta.l $414180
    lda.l $4121D9
    sta.l $414182
    lda.l $4121DB
    sta.l $414184
    lda.l $4121C6
    sta.l $41418A
    lda.l $411B14
    sta.l $41418C
    lda.l $411B16
    sta.l $41418E
    lda.l $411B18
    sta.l $414190
    lda.l $411B1A
    sta.l $414192
    lda.l $411BE4
    sta.l $414194
    lda.l $411B06
    sta.l $414196
    lda.l $411BF6
    sta.l $414198
    lda.l $411BFC
    sta.l $41419A
    lda.l $411BF0
    sta.l $41419C
    lda.l $411B70
    sta.l $41419E
    lda.l $411B34
    sta.l $4141AA
    lda.l $411BE6
    sta.l $4141AC
    lda.l $412250
    sta.l $4141A0
    lda.l $41224A
    sta.l $4141A2
    lda.l $412254
    sta.l $4141A4
    lda.l $41225E
    sta.l $4141A6
    lda.l $412260
    sta.l $4141A8
    lda.l $41224B
    sta.l $4141AE
    lda.l $411C14
    sta.l $4141B0
    lda.l $411C16
    sta.l $4141B2
    lda.l $411C18
    sta.l $4141B4
    lda.l $411C1A
    sta.l $4141B6
    lda.l $411CE4
    sta.l $4141B8
    lda.l $411C06
    sta.l $4141BA
    lda.l $411CF6
    sta.l $4141BC
    lda.l $411CFC
    sta.l $4141BE
    lda.l $411CF0
    sta.l $4141C0
    lda.l $411C70
    sta.l $4141C2
    lda.l $411C34
    sta.l $4141CE
    lda.l $411CE6
    sta.l $4141D0
    lda.l $4122D5
    sta.l $4141C4
    lda.l $4122CF
    sta.l $4141C6
    lda.l $4122D9
    sta.l $4141C8
    lda.l $4122E3
    sta.l $4141CA
    lda.l $4122E5
    sta.l $4141CC
    lda.l $4122D0
    sta.l $4141D2
    lda.l $411D14
    sta.l $4141D4
    lda.l $411D16
    sta.l $4141D6
    lda.l $411D18
    sta.l $4141D8
    lda.l $411D1A
    sta.l $4141DA
    lda.l $411DE4
    sta.l $4141DC
    lda.l $411D06
    sta.l $4141DE
    lda.l $411DF6
    sta.l $4141E0
    lda.l $411DFC
    sta.l $4141E2
    lda.l $411DF0
    sta.l $4141E4
    lda.l $411D70
    sta.l $4141E6
    lda.l $411D34
    sta.l $4141F2
    lda.l $411DE6
    sta.l $4141F4
    lda.l $41235A
    sta.l $4141E8
    lda.l $412354
    sta.l $4141EA
    lda.l $41235E
    sta.l $4141EC
    lda.l $412368
    sta.l $4141EE
    lda.l $41236A
    sta.l $4141F0
    lda.l $412355
    sta.l $4141F6
    lda.l $411E14
    sta.l $4141F8
    lda.l $411E16
    sta.l $4141FA
    lda.l $411E18
    sta.l $4141FC
    lda.l $411E1A
    sta.l $4141FE
    lda.l $411EE4
    sta.l $414200
    lda.l $411E06
    sta.l $414202
    lda.l $411EF6
    sta.l $414204
    lda.l $411EFC
    sta.l $414206
    lda.l $411EF0
    sta.l $414208
    lda.l $411E70
    sta.l $41420A
    lda.l $411E34
    sta.l $414216
    lda.l $411EE6
    sta.l $414218
    lda.l $4123DF
    sta.l $41420C
    lda.l $4123D9
    sta.l $41420E
    lda.l $4123E3
    sta.l $414210
    lda.l $4123ED
    sta.l $414212
    lda.l $4123EF
    sta.l $414214
    lda.l $4123DA
    sta.l $41421A
    jml Worker_Snapshot_Ack
Worker_Snapshot_Ack:
    .a16
    .i16
    sep #$20
    .a8
    lda.l $412006
    sta.l $412007
    rep #$30
    .a16
    .i16
    jml Worker_Poll
Worker_Tick:
    .a16
    .i16
    lda.l $412004
    and #$01FF
    asl a
    asl a
    asl a
    tax
    lda.l $413000,x
    sta $3C
    lda.l $413002,x
    sta $3E
    lda.l $413004,x
    sta.l $412420
    lda.l $413006,x
    sta.l $412422
    lda $3C
    jsl Worker_ApplyRemove
    lda.l $412004
    asl a
    asl a
    asl a
    tax
    lda.l $415000,x
    sta.l $412020
    lda.l $415002,x
    sta.l $412022
    lda.l $415004,x
    sta.l $412024
    lda.l $415006,x
    sta.l $412026
    lda.l $415002,x
    and #$4000
    beq Worker_Input_P1_Done
    lda #0
    sta.l $41214A
Worker_Input_P1_Done:
    lda.l $415006,x
    and #$4000
    beq Worker_InputApplied
    lda #0
    sta.l $4121CF
Worker_InputApplied:
Worker_Execute:
    .a16
    .i16
    jsl W6_UpdateWorld
    lda.l $412434
    beq Worker_EventsOkay
    jml Worker_EventFault
Worker_EventsOkay:
    lda $3A
    bne Worker_WorldFault
Worker_Complete:
    .a16
    .i16
    lda.l $412004
    inc a
    and #$01FF
    sta.l $412004
Worker_Complete__Poll:
    jml Worker_Poll
Worker_EventFault:
    .a16
    .i16
    lda #23
    bra Worker_Fault
Worker_RingFault:
    .a16
    .i16
    lda #22
    bra Worker_Fault
Worker_WorldFault:
    .a16
    .i16
    ; First world callback fault: preserve pass/actor cursors, actor DP,
    ; driver, unsupported-feature byte and actor-local error for the campaign.
    lda $3A
    sta.l $412C50
    lda $38
    sta.l $412C52
    lda $36
    sta.l $412C54
    txa
    sta.l $412C56
    phd
    txa
    tcd
    lda $E6
    sta.l $412C58
    lda $A8
    sta.l $412C5A
    lda $FC
    sta.l $412C5C
    lda $E4
    sta.l $412C5E
    lda $C2
    sta.l $412C60
    lda.l Spawn_HoleCount
    sta.l $412C62
    lda $14
    sta.l $412C64
    lda $16
    sta.l $412C66
    lda.l $41200C
    sta.l $412C68
    lda $E0
    sta.l $412C6A
    pld
    lda $3A
Worker_Fault:
    .a16
    .i16
    sta.l $412008
    sep #$20
    .a8
    lda #1
    sta.l $41200A
    rep #$30
    .a16
    .i16
Worker_FaultWait:
    .a16
    .i16
    jml Worker_FaultWait
Worker_ApplyRemove:
    .a16
    .i16
    sta.l $41243E
    lda.l $412440
    cmp.l $412442
    beq Worker_ApplyRemove__done
    lda.l $41243E
    sec
    sbc.l $412446
    beq Worker_ApplyRemove__tick_match
    ; The worker clock is 16-bit while the production source clock is
    ; extended. Compare the short (current minus requested) delta as signed
    ; so a removal queued for tick $0000 waits correctly while the resident
    ; world is at $FFFE/$FFFF instead of faulting as stale.
    bmi Worker_ApplyRemove__done
    bra Worker_ApplyRemove__bad
Worker_ApplyRemove__tick_match:
    lda.l $412444
    sec
    sbc #$0A00
    ldx #0
Worker_ApplyRemove__slot:
    cmp #0
    beq Worker_ApplyRemove__found
    sec
    sbc #CHAR_ZP_LEN
    bcc Worker_ApplyRemove__bad
    inx
    cpx #6
    bcc Worker_ApplyRemove__slot
    bra Worker_ApplyRemove__bad
Worker_ApplyRemove__found:
    txa
    asl a
    tax
    lda.l WHost_SlotTable,x
    tcd
    stz $FC
    jsl W6_KillUnlinked
    lda $FC
    bne Worker_ApplyRemove__bad
    lda.l $412440
    sta.l $412442
    lda #$7700
    tcd
Worker_ApplyRemove__done:
    rtl
Worker_ApplyRemove__bad:
    ; Temporary campaign-fixture forensic record in the unallocated BW-RAM
    ; gap after the sequenced event ring. Preserve why the one-slot removal
    ; contract rejected this command before entering the fail-closed wait.
    lda.l $41243E
    sta.l $412C50
    lda.l $412440
    sta.l $412C52
    lda.l $412442
    sta.l $412C54
    lda.l $412444
    sta.l $412C56
    lda.l $412446
    sta.l $412C58
    lda $3C
    sta.l $412C5A
    tdc
    sta.l $412C5C
    txa
    sta.l $412C5E
    lda $FC
    sta.l $412C60
    lda #24
    jml Worker_Fault

.bank 36
.org $8000

Relay_Poll_P2:
    php
    rep #$30
    .a16
    .i16
    jsl $0781E3
    pha
    lda.l $7E175C
    bne Relay_Poll_P2__owned
    pla
    plp
    rtl
Relay_Poll_P2__owned:
    lda.l $7E0410
    sta.l $412014
    lda.l $7E0412
    ora.l $412016
    sta.l $412016
    lda.l $7E0416
    sta.l $412018
    lda.l $7E0418
    ora.l $41201A
    sta.l $41201A
    pla
    plp
    rtl

Relay_QueueRemove:
    php
    rep #$30
    .a16
    .i16
    phx
    phy
    pha
    lda.l $7E175E
    cmp #2
    beq Relay_QueueRemove__owned
    pla
    jsl $1E9FCF
    bra Relay_QueueRemove__return
Relay_QueueRemove__owned:
    lda.l $412440
    cmp.l $412442
    bne Relay_QueueRemove__busy
    pla
    sta.l $412444
    lda.l $7E1760
    cmp #4
    beq Relay_QueueRemove__current_tick
    lda.l $7E1774
    inc a
    bra Relay_QueueRemove__store_tick
Relay_QueueRemove__current_tick:
    lda.l $7E1774
Relay_QueueRemove__store_tick:
    sta.l $412446
    lda.l $412440
    inc a
    sta.l $412440
    bra Relay_QueueRemove__return
Relay_QueueRemove__busy:
    pla
    lda #24
    sta.l $7E1764
Relay_QueueRemove__return:
    rep #$30
    .a16
    .i16
    ply
    plx
    plp
    rtl

Relay_Run:
    php
    rep #$30
    .a16
    .i16
    phx
    phy
    phb
    phd
    sep #$20
    .a8
    lda #0
    pha
    plb
    rep #$30
    .a16
    .i16
    lda.l $7E175C
    beq Relay_Acquire_First
    ; Nonblocking gameplay-event pump: consume only published ring rows;
    ; never wait for an SA-1 tick or copy the source-world contexts.
    jsl Relay_DrainEvents
    bra Relay_Queue
Relay_Acquire_First:
    jsl Relay_Acquire
Relay_Queue:
    .a16
    .i16
    sep #$20
    .a8
    lda.l $41200A
    beq Relay_Queue__healthy
    jml Relay_Flagged
Relay_Queue__healthy:
    rep #$20
    .a16
    lda.l $412002
    inc a
    and #$01FF
    cmp.l $412004
    bne Relay_Queue__head_open
    jml Relay_Failed
Relay_Queue__head_open:
    lda.l $412002
    and #$01FF
    asl a
    asl a
    asl a
    tax
    lda.l $7E1774
    sta.l $413000,x
    lda.l $7E1776
    sta.l $413002,x
    lda.l $7E1774
    inc a
    sta.l $7E1774
    bne Relay_Queue__clock_advanced
    lda.l $7E1776
    inc a
    sta.l $7E1776
Relay_Queue__clock_advanced:
    .a16
    .i16
    lda.l $412014
    sta.l $415000,x
    lda.l $412016
    sta.l $415002,x
    lda.l $412018
    sta.l $415004,x
    lda.l $41201A
    sta.l $415006,x
    lda #0
    sta.l $412016
    sta.l $41201A
    .a16
    .i16
    lda.l Relay_HostScreen_PosX
    sta.l $413004,x
    lda.l Relay_HostSpawn_HoleCount
    sta.l $413006,x
    lda.l $412002
    inc a
    and #$01FF
    sta.l $412002
    sta.l $7E175A
Relay_Queued:
    .a16
    .i16
    pld
    plb
    ply
    plx
    plp
    rtl
Relay_Failed:
    .a16
    .i16
    lda #21
    sta.l $7E1764
    bra Relay_Queued
Relay_Flagged:
    .a8
    rep #$20
    .a16
    lda #21
    sta.l $7E1764
    bra Relay_Queued

Relay_Acquire:
    .a16
    .i16
    lda #0
    sta.l $412002
    sta.l $412004
    sta.l $412008
    sta.l $412430
    sta.l $412432
    sta.l $412434
    sta.l $412436
    sta.l $412438
    sta.l $41243A
    sta.l $41243C
    sta.l $41243E
    sta.l $412440
    sta.l $412442
    sta.l $412444
    sta.l $412446
    sta.l $7E1778
    lda #0
    sta.l $412014
    sta.l $412016
    sta.l $412018
    sta.l $41201A
    sta.l $412020
    sta.l $412022
    sta.l $412024
    sta.l $412026

    sep #$20
    .a8
    lda #0
    sta.l $412006
    sta.l $412007
    sta.l $41200A
    lda #$89
    sta $2231
    stz $3026
    stz $3027
    rep #$30
    .a16
    .i16
    ldx #0
Relay_InWorld:
    .a16
    .i16
    lda.l $7E1700,x
    sta.l $411700,x
    inx
    inx
    cpx #256
    bcc Relay_InWorld
    ldx #0
Relay_InActors:
    .a16
    .i16
    lda.l $7E1900,x
    sta.l $411900,x
    inx
    inx
    cpx #1536
    bcc Relay_InActors
    ldx #0
Relay_InFields:
    .a16
    .i16
    lda.l $7E550F,x
    sta.l $412100,x
    inx
    inx
    cpx #798
    bcc Relay_InFields
    lda.l $7E1601
    sta.l $412420
    lda.l $7E58F0
    sta.l $412422
    lda.l $411934
    beq Relay_ToWorker_0_52
    clc
    adc #$6000
    sta.l $411934
Relay_ToWorker_0_52:
    .a16
    .i16
    lda.l $411936
    beq Relay_ToWorker_0_54
    clc
    adc #$6000
    sta.l $411936
Relay_ToWorker_0_54:
    .a16
    .i16
    lda.l $4119B0
    beq Relay_ToWorker_0_176
    clc
    adc #$6000
    sta.l $4119B0
Relay_ToWorker_0_176:
    .a16
    .i16
    lda.l $411A34
    beq Relay_ToWorker_1_52
    clc
    adc #$6000
    sta.l $411A34
Relay_ToWorker_1_52:
    .a16
    .i16
    lda.l $411A36
    beq Relay_ToWorker_1_54
    clc
    adc #$6000
    sta.l $411A36
Relay_ToWorker_1_54:
    .a16
    .i16
    lda.l $411AB0
    beq Relay_ToWorker_1_176
    clc
    adc #$6000
    sta.l $411AB0
Relay_ToWorker_1_176:
    .a16
    .i16
    lda.l $411B34
    beq Relay_ToWorker_2_52
    clc
    adc #$6000
    sta.l $411B34
Relay_ToWorker_2_52:
    .a16
    .i16
    lda.l $411B36
    beq Relay_ToWorker_2_54
    clc
    adc #$6000
    sta.l $411B36
Relay_ToWorker_2_54:
    .a16
    .i16
    lda.l $411BB0
    beq Relay_ToWorker_2_176
    clc
    adc #$6000
    sta.l $411BB0
Relay_ToWorker_2_176:
    .a16
    .i16
    lda.l $411C34
    beq Relay_ToWorker_3_52
    clc
    adc #$6000
    sta.l $411C34
Relay_ToWorker_3_52:
    .a16
    .i16
    lda.l $411C36
    beq Relay_ToWorker_3_54
    clc
    adc #$6000
    sta.l $411C36
Relay_ToWorker_3_54:
    .a16
    .i16
    lda.l $411CB0
    beq Relay_ToWorker_3_176
    clc
    adc #$6000
    sta.l $411CB0
Relay_ToWorker_3_176:
    .a16
    .i16
    lda.l $411D34
    beq Relay_ToWorker_4_52
    clc
    adc #$6000
    sta.l $411D34
Relay_ToWorker_4_52:
    .a16
    .i16
    lda.l $411D36
    beq Relay_ToWorker_4_54
    clc
    adc #$6000
    sta.l $411D36
Relay_ToWorker_4_54:
    .a16
    .i16
    lda.l $411DB0
    beq Relay_ToWorker_4_176
    clc
    adc #$6000
    sta.l $411DB0
Relay_ToWorker_4_176:
    .a16
    .i16
    lda.l $411E34
    beq Relay_ToWorker_5_52
    clc
    adc #$6000
    sta.l $411E34
Relay_ToWorker_5_52:
    .a16
    .i16
    lda.l $411E36
    beq Relay_ToWorker_5_54
    clc
    adc #$6000
    sta.l $411E36
Relay_ToWorker_5_54:
    .a16
    .i16
    lda.l $411EB0
    beq Relay_ToWorker_5_176
    clc
    adc #$6000
    sta.l $411EB0
Relay_ToWorker_5_176:
    .a16
    .i16
    lda.l $411744
    beq Relay_ToWorker_world_68
    clc
    adc #$6000
    sta.l $411744
Relay_ToWorker_world_68:
    .a16
    .i16
    lda.l $411746
    beq Relay_ToWorker_world_70
    clc
    adc #$6000
    sta.l $411746
Relay_ToWorker_world_70:
    .a16
    .i16
    lda.l $41174E
    beq Relay_ToWorker_world_78
    clc
    adc #$6000
    sta.l $41174E
Relay_ToWorker_world_78:
    .a16
    .i16
    lda.l $411750
    beq Relay_ToWorker_world_80
    clc
    adc #$6000
    sta.l $411750
Relay_ToWorker_world_80:
    .a16
    .i16
    lda #WHost_SlotTable & $FFFF
    sta.l $411730
    lda #$0025
    sta.l $411732
    sep #$20
    .a8
    lda #$55
    sta $3025
    ldy #$FFFF
Relay_Acquired:
    .a8
    .i16
    lda $3027
    cmp #3
    beq Relay_AcquireDone
    dey
    bne Relay_Acquired
    jml Relay_Timeout
Relay_AcquireDone:
    .a8
    .i16
    rep #$30
    .a16
    .i16
    lda #1
    sta.l $7E175C
    lda #2
    sta.l $7E175E
    rtl

Relay_Flush:
    .a16
    .i16
    php
    rep #$30
    phx
    phy
    phb
    phd
    sep #$20
    .a8
    lda #0
    pha
    plb
    lda.l $7E175C
    bne Relay_Flush_Owned
    jml Relay_Flush_Return
Relay_Flush_Owned:
    ldy #$FFFF
Relay_Wait_Ticks:
    .a8
    lda.l $41200A
    beq Relay_Flush_Ticks_NoFault
    jml Relay_Flush_Timeout
Relay_Flush_Ticks_NoFault:
    rep #$20
    .a16
    lda.l $412002
    cmp.l $412004
    beq Relay_Request_Snapshot
    sep #$20
    .a8
    dey
    bne Relay_Wait_Ticks
    jml Relay_Flush_Timeout
Relay_Request_Snapshot:
    .a16
    .i16
    sep #$20
    .a8
    lda.l $412006
    inc a
    sta.l $412006
    ldy #$FFFF
Relay_Wait_Snapshot:
    .a8
    lda.l $41200A
    beq Relay_Flush_Snapshot_NoFault
    jml Relay_Flush_Timeout
Relay_Flush_Snapshot_NoFault:
    lda.l $412007
    cmp.l $412006
    beq Relay_Snapshot_Ready
    dey
    bne Relay_Wait_Snapshot
    jml Relay_Flush_Timeout
Relay_Snapshot_Ready:
    .a8
    lda.l $412006
    and #1
    beq Relay_Commit_A
    jml Relay_Commit_B
Relay_Commit_A:
    rep #$30
    .a16
    .i16
    lda.l $414000
    sta.l $7E1700
    lda.l $414002
    sta.l $7E1702
    lda.l $414004
    sta.l $7E1704
    lda.l $414006
    sta.l $7E1706
    lda.l $414008
    sta.l $7E1708
    lda.l $41400A
    sta.l $7E170A
    lda.l $41400C
    sta.l $7E170C
    lda.l $41400E
    sta.l $7E170E
    lda.l $414010
    sta.l $7E1710
    lda.l $414012
    sta.l $7E1712
    lda.l $414014
    sta.l $7E1714
    lda.l $414016
    sta.l $7E1716
    lda.l $414018
    sta.l $7E1718
    lda.l $41401A
    sta.l $7E171A
    lda.l $41401C
    sta.l $7E171C
    lda.l $41401E
    sta.l $7E171E
    lda.l $414020
    sta.l $7E1720
    lda.l $414022
    sta.l $7E1722
    lda.l $414028
    sta.l $7E176C
    lda.l $41402A
    sta.l $7E176E
    lda.l $41404A
    and #$00FF
    beq Relay_SnapshotZeroPolicy_A_0
    cmp #3
    bcc Relay_SnapshotBound_A_0
    jmp Relay_SnapshotPolicyFault_A_0
Relay_SnapshotZeroPolicy_A_0:
    jmp Relay_SnapshotUnbound_A_0
Relay_SnapshotBound_A_0:
    lda.l $414034
    sta.l $7E1914
    lda.l $414036
    sta.l $7E1916
    lda.l $414038
    sta.l $7E1918
    lda.l $41403A
    sta.l $7E191A
    lda.l $41403C
    sta.l $7E19E4
    lda.l $41403E
    sta.l $7E1906
    lda.l $414040
    sta.l $7E19F6
    lda.l $414042
    sta.l $7E19FC
    lda.l $414044
    sta.l $7E19F0
    lda.l $414046
    sta.l $7E1970
    lda.l $414052
    sta.l $7E1934
    lda.l $414054
    sta.l $7E19E6
    lda.l $414048
    sta.l $7E5555
    sep #$20
    .a8
    lda.l $41404A
    sta.l $7E554F
    rep #$30
    .a16
    .i16
    lda.l $414046
    sta.l $7E5551
    lda.l $41404C
    sta.l $7E5559
    lda.l $41404E
    sta.l $7E5563
    lda.l $414050
    sta.l $7E5565
    lda #$1900
    tcd
    lda #0
    sta $7A
    lda.l $414034
    jsl $1E93DB
    bcs Relay_ProjectFault_A_0
    sta.l $7E0A04
    lda.l $414036
    jsl $1E93DB
    bcs Relay_ProjectFault_A_0
    sta.l $7E0A06
    sep #$20
    .a8
    lda.l $414044
    sta.l $7E0A23
    lda.l $41403A
    sta.l $7E0A08
    bra Relay_ProjectNext_A_0
Relay_SnapshotUnbound_A_0:
    .a16
    .i16
    jmp Relay_ProjectNext_A_0
Relay_ProjectFault_A_0:
    .a16
    .i16
    lda #10
    sta.l $7E1764
    stp
Relay_SnapshotPolicyFault_A_0:
    .a16
    .i16
    lda #1
    sta.l $7E1764
    stp
Relay_ProjectNext_A_0:
    rep #$30
    .a16
    .i16
    lda.l $41406E
    and #$00FF
    beq Relay_SnapshotZeroPolicy_A_1
    cmp #3
    bcc Relay_SnapshotBound_A_1
    jmp Relay_SnapshotPolicyFault_A_1
Relay_SnapshotZeroPolicy_A_1:
    jmp Relay_SnapshotUnbound_A_1
Relay_SnapshotBound_A_1:
    lda.l $414058
    sta.l $7E1A14
    lda.l $41405A
    sta.l $7E1A16
    lda.l $41405C
    sta.l $7E1A18
    lda.l $41405E
    sta.l $7E1A1A
    lda.l $414060
    sta.l $7E1AE4
    lda.l $414062
    sta.l $7E1A06
    lda.l $414064
    sta.l $7E1AF6
    lda.l $414066
    sta.l $7E1AFC
    lda.l $414068
    sta.l $7E1AF0
    lda.l $41406A
    sta.l $7E1A70
    lda.l $414076
    sta.l $7E1A34
    lda.l $414078
    sta.l $7E1AE6
    lda.l $41406C
    sta.l $7E55DA
    sep #$20
    .a8
    lda.l $41406E
    sta.l $7E55D4
    rep #$30
    .a16
    .i16
    lda.l $41406A
    sta.l $7E55D6
    lda.l $414070
    sta.l $7E55DE
    lda.l $414072
    sta.l $7E55E8
    lda.l $414074
    sta.l $7E55EA
    lda #$1A00
    tcd
    lda #133
    sta $7A
    lda.l $414058
    jsl $1E93DB
    bcs Relay_ProjectFault_A_1
    sta.l $7E0A89
    lda.l $41405A
    jsl $1E93DB
    bcs Relay_ProjectFault_A_1
    sta.l $7E0A8B
    sep #$20
    .a8
    lda.l $414068
    sta.l $7E0AA8
    lda.l $41405E
    sta.l $7E0A8D
    bra Relay_ProjectNext_A_1
Relay_SnapshotUnbound_A_1:
    .a16
    .i16
    jmp Relay_ProjectNext_A_1
Relay_ProjectFault_A_1:
    .a16
    .i16
    lda #10
    sta.l $7E1764
    stp
Relay_SnapshotPolicyFault_A_1:
    .a16
    .i16
    lda #1
    sta.l $7E1764
    stp
Relay_ProjectNext_A_1:
    rep #$30
    .a16
    .i16
    lda.l $414092
    and #$00FF
    beq Relay_SnapshotZeroPolicy_A_2
    cmp #3
    bcc Relay_SnapshotBound_A_2
    jmp Relay_SnapshotPolicyFault_A_2
Relay_SnapshotZeroPolicy_A_2:
    jmp Relay_SnapshotUnbound_A_2
Relay_SnapshotBound_A_2:
    lda.l $41407C
    sta.l $7E1B14
    lda.l $41407E
    sta.l $7E1B16
    lda.l $414080
    sta.l $7E1B18
    lda.l $414082
    sta.l $7E1B1A
    lda.l $414084
    sta.l $7E1BE4
    lda.l $414086
    sta.l $7E1B06
    lda.l $414088
    sta.l $7E1BF6
    lda.l $41408A
    sta.l $7E1BFC
    lda.l $41408C
    sta.l $7E1BF0
    lda.l $41408E
    sta.l $7E1B70
    lda.l $41409A
    sta.l $7E1B34
    lda.l $41409C
    sta.l $7E1BE6
    lda.l $414090
    sta.l $7E565F
    sep #$20
    .a8
    lda.l $414092
    sta.l $7E5659
    rep #$30
    .a16
    .i16
    lda.l $41408E
    sta.l $7E565B
    lda.l $414094
    sta.l $7E5663
    lda.l $414096
    sta.l $7E566D
    lda.l $414098
    sta.l $7E566F
    lda.l $41409E
    sta.l $7E565A
    lda #$1B00
    tcd
    lda #266
    sta $7A
    lda.l $41407C
    jsl $1E93DB
    bcs Relay_ProjectFault_A_2
    sta.l $7E0B0E
    lda.l $41407E
    jsl $1E93DB
    bcs Relay_ProjectFault_A_2
    sta.l $7E0B10
    sep #$20
    .a8
    lda.l $41408C
    sta.l $7E0B2D
    lda.l $414082
    sta.l $7E0B12
    bra Relay_ProjectNext_A_2
Relay_SnapshotUnbound_A_2:
    .a16
    .i16
    jmp Relay_ProjectNext_A_2
Relay_ProjectFault_A_2:
    .a16
    .i16
    lda #10
    sta.l $7E1764
    stp
Relay_SnapshotPolicyFault_A_2:
    .a16
    .i16
    lda #1
    sta.l $7E1764
    stp
Relay_ProjectNext_A_2:
    rep #$30
    .a16
    .i16
    lda.l $4140B6
    and #$00FF
    beq Relay_SnapshotZeroPolicy_A_3
    cmp #3
    bcc Relay_SnapshotBound_A_3
    jmp Relay_SnapshotPolicyFault_A_3
Relay_SnapshotZeroPolicy_A_3:
    jmp Relay_SnapshotUnbound_A_3
Relay_SnapshotBound_A_3:
    lda.l $4140A0
    sta.l $7E1C14
    lda.l $4140A2
    sta.l $7E1C16
    lda.l $4140A4
    sta.l $7E1C18
    lda.l $4140A6
    sta.l $7E1C1A
    lda.l $4140A8
    sta.l $7E1CE4
    lda.l $4140AA
    sta.l $7E1C06
    lda.l $4140AC
    sta.l $7E1CF6
    lda.l $4140AE
    sta.l $7E1CFC
    lda.l $4140B0
    sta.l $7E1CF0
    lda.l $4140B2
    sta.l $7E1C70
    lda.l $4140BE
    sta.l $7E1C34
    lda.l $4140C0
    sta.l $7E1CE6
    lda.l $4140B4
    sta.l $7E56E4
    sep #$20
    .a8
    lda.l $4140B6
    sta.l $7E56DE
    rep #$30
    .a16
    .i16
    lda.l $4140B2
    sta.l $7E56E0
    lda.l $4140B8
    sta.l $7E56E8
    lda.l $4140BA
    sta.l $7E56F2
    lda.l $4140BC
    sta.l $7E56F4
    lda.l $4140C2
    sta.l $7E56DF
    lda #$1C00
    tcd
    lda #399
    sta $7A
    lda.l $4140A0
    jsl $1E93DB
    bcs Relay_ProjectFault_A_3
    sta.l $7E0B93
    lda.l $4140A2
    jsl $1E93DB
    bcs Relay_ProjectFault_A_3
    sta.l $7E0B95
    sep #$20
    .a8
    lda.l $4140B0
    sta.l $7E0BB2
    lda.l $4140A6
    sta.l $7E0B97
    bra Relay_ProjectNext_A_3
Relay_SnapshotUnbound_A_3:
    .a16
    .i16
    jmp Relay_ProjectNext_A_3
Relay_ProjectFault_A_3:
    .a16
    .i16
    lda #10
    sta.l $7E1764
    stp
Relay_SnapshotPolicyFault_A_3:
    .a16
    .i16
    lda #1
    sta.l $7E1764
    stp
Relay_ProjectNext_A_3:
    rep #$30
    .a16
    .i16
    lda.l $4140DA
    and #$00FF
    beq Relay_SnapshotZeroPolicy_A_4
    cmp #3
    bcc Relay_SnapshotBound_A_4
    jmp Relay_SnapshotPolicyFault_A_4
Relay_SnapshotZeroPolicy_A_4:
    jmp Relay_SnapshotUnbound_A_4
Relay_SnapshotBound_A_4:
    lda.l $4140C4
    sta.l $7E1D14
    lda.l $4140C6
    sta.l $7E1D16
    lda.l $4140C8
    sta.l $7E1D18
    lda.l $4140CA
    sta.l $7E1D1A
    lda.l $4140CC
    sta.l $7E1DE4
    lda.l $4140CE
    sta.l $7E1D06
    lda.l $4140D0
    sta.l $7E1DF6
    lda.l $4140D2
    sta.l $7E1DFC
    lda.l $4140D4
    sta.l $7E1DF0
    lda.l $4140D6
    sta.l $7E1D70
    lda.l $4140E2
    sta.l $7E1D34
    lda.l $4140E4
    sta.l $7E1DE6
    lda.l $4140D8
    sta.l $7E5769
    sep #$20
    .a8
    lda.l $4140DA
    sta.l $7E5763
    rep #$30
    .a16
    .i16
    lda.l $4140D6
    sta.l $7E5765
    lda.l $4140DC
    sta.l $7E576D
    lda.l $4140DE
    sta.l $7E5777
    lda.l $4140E0
    sta.l $7E5779
    lda.l $4140E6
    sta.l $7E5764
    lda #$1D00
    tcd
    lda #532
    sta $7A
    lda.l $4140C4
    jsl $1E93DB
    bcs Relay_ProjectFault_A_4
    sta.l $7E0C18
    lda.l $4140C6
    jsl $1E93DB
    bcs Relay_ProjectFault_A_4
    sta.l $7E0C1A
    sep #$20
    .a8
    lda.l $4140D4
    sta.l $7E0C37
    lda.l $4140CA
    sta.l $7E0C1C
    bra Relay_ProjectNext_A_4
Relay_SnapshotUnbound_A_4:
    .a16
    .i16
    jmp Relay_ProjectNext_A_4
Relay_ProjectFault_A_4:
    .a16
    .i16
    lda #10
    sta.l $7E1764
    stp
Relay_SnapshotPolicyFault_A_4:
    .a16
    .i16
    lda #1
    sta.l $7E1764
    stp
Relay_ProjectNext_A_4:
    rep #$30
    .a16
    .i16
    lda.l $4140FE
    and #$00FF
    beq Relay_SnapshotZeroPolicy_A_5
    cmp #3
    bcc Relay_SnapshotBound_A_5
    jmp Relay_SnapshotPolicyFault_A_5
Relay_SnapshotZeroPolicy_A_5:
    jmp Relay_SnapshotUnbound_A_5
Relay_SnapshotBound_A_5:
    lda.l $4140E8
    sta.l $7E1E14
    lda.l $4140EA
    sta.l $7E1E16
    lda.l $4140EC
    sta.l $7E1E18
    lda.l $4140EE
    sta.l $7E1E1A
    lda.l $4140F0
    sta.l $7E1EE4
    lda.l $4140F2
    sta.l $7E1E06
    lda.l $4140F4
    sta.l $7E1EF6
    lda.l $4140F6
    sta.l $7E1EFC
    lda.l $4140F8
    sta.l $7E1EF0
    lda.l $4140FA
    sta.l $7E1E70
    lda.l $414106
    sta.l $7E1E34
    lda.l $414108
    sta.l $7E1EE6
    lda.l $4140FC
    sta.l $7E57EE
    sep #$20
    .a8
    lda.l $4140FE
    sta.l $7E57E8
    rep #$30
    .a16
    .i16
    lda.l $4140FA
    sta.l $7E57EA
    lda.l $414100
    sta.l $7E57F2
    lda.l $414102
    sta.l $7E57FC
    lda.l $414104
    sta.l $7E57FE
    lda.l $41410A
    sta.l $7E57E9
    lda #$1E00
    tcd
    lda #665
    sta $7A
    lda.l $4140E8
    jsl $1E93DB
    bcs Relay_ProjectFault_A_5
    sta.l $7E0C9D
    lda.l $4140EA
    jsl $1E93DB
    bcs Relay_ProjectFault_A_5
    sta.l $7E0C9F
    sep #$20
    .a8
    lda.l $4140F8
    sta.l $7E0CBC
    lda.l $4140EE
    sta.l $7E0CA1
    bra Relay_ProjectNext_A_5
Relay_SnapshotUnbound_A_5:
    .a16
    .i16
    jmp Relay_ProjectNext_A_5
Relay_ProjectFault_A_5:
    .a16
    .i16
    lda #10
    sta.l $7E1764
    stp
Relay_SnapshotPolicyFault_A_5:
    .a16
    .i16
    lda #1
    sta.l $7E1764
    stp
Relay_ProjectNext_A_5:
    rep #$30
    .a16
    .i16
    jml Relay_Flush_Return
Relay_Commit_B:
    .a8
    rep #$30
    .a16
    .i16
    lda.l $414110
    sta.l $7E1700
    lda.l $414112
    sta.l $7E1702
    lda.l $414114
    sta.l $7E1704
    lda.l $414116
    sta.l $7E1706
    lda.l $414118
    sta.l $7E1708
    lda.l $41411A
    sta.l $7E170A
    lda.l $41411C
    sta.l $7E170C
    lda.l $41411E
    sta.l $7E170E
    lda.l $414120
    sta.l $7E1710
    lda.l $414122
    sta.l $7E1712
    lda.l $414124
    sta.l $7E1714
    lda.l $414126
    sta.l $7E1716
    lda.l $414128
    sta.l $7E1718
    lda.l $41412A
    sta.l $7E171A
    lda.l $41412C
    sta.l $7E171C
    lda.l $41412E
    sta.l $7E171E
    lda.l $414130
    sta.l $7E1720
    lda.l $414132
    sta.l $7E1722
    lda.l $414138
    sta.l $7E176C
    lda.l $41413A
    sta.l $7E176E
    lda.l $41415A
    and #$00FF
    beq Relay_SnapshotZeroPolicy_B_0
    cmp #3
    bcc Relay_SnapshotBound_B_0
    jmp Relay_SnapshotPolicyFault_B_0
Relay_SnapshotZeroPolicy_B_0:
    jmp Relay_SnapshotUnbound_B_0
Relay_SnapshotBound_B_0:
    lda.l $414144
    sta.l $7E1914
    lda.l $414146
    sta.l $7E1916
    lda.l $414148
    sta.l $7E1918
    lda.l $41414A
    sta.l $7E191A
    lda.l $41414C
    sta.l $7E19E4
    lda.l $41414E
    sta.l $7E1906
    lda.l $414150
    sta.l $7E19F6
    lda.l $414152
    sta.l $7E19FC
    lda.l $414154
    sta.l $7E19F0
    lda.l $414156
    sta.l $7E1970
    lda.l $414162
    sta.l $7E1934
    lda.l $414164
    sta.l $7E19E6
    lda.l $414158
    sta.l $7E5555
    sep #$20
    .a8
    lda.l $41415A
    sta.l $7E554F
    rep #$30
    .a16
    .i16
    lda.l $414156
    sta.l $7E5551
    lda.l $41415C
    sta.l $7E5559
    lda.l $41415E
    sta.l $7E5563
    lda.l $414160
    sta.l $7E5565
    lda #$1900
    tcd
    lda #0
    sta $7A
    lda.l $414144
    jsl $1E93DB
    bcs Relay_ProjectFault_B_0
    sta.l $7E0A04
    lda.l $414146
    jsl $1E93DB
    bcs Relay_ProjectFault_B_0
    sta.l $7E0A06
    sep #$20
    .a8
    lda.l $414154
    sta.l $7E0A23
    lda.l $41414A
    sta.l $7E0A08
    bra Relay_ProjectNext_B_0
Relay_SnapshotUnbound_B_0:
    .a16
    .i16
    jmp Relay_ProjectNext_B_0
Relay_ProjectFault_B_0:
    .a16
    .i16
    lda #10
    sta.l $7E1764
    stp
Relay_SnapshotPolicyFault_B_0:
    .a16
    .i16
    lda #1
    sta.l $7E1764
    stp
Relay_ProjectNext_B_0:
    rep #$30
    .a16
    .i16
    lda.l $41417E
    and #$00FF
    beq Relay_SnapshotZeroPolicy_B_1
    cmp #3
    bcc Relay_SnapshotBound_B_1
    jmp Relay_SnapshotPolicyFault_B_1
Relay_SnapshotZeroPolicy_B_1:
    jmp Relay_SnapshotUnbound_B_1
Relay_SnapshotBound_B_1:
    lda.l $414168
    sta.l $7E1A14
    lda.l $41416A
    sta.l $7E1A16
    lda.l $41416C
    sta.l $7E1A18
    lda.l $41416E
    sta.l $7E1A1A
    lda.l $414170
    sta.l $7E1AE4
    lda.l $414172
    sta.l $7E1A06
    lda.l $414174
    sta.l $7E1AF6
    lda.l $414176
    sta.l $7E1AFC
    lda.l $414178
    sta.l $7E1AF0
    lda.l $41417A
    sta.l $7E1A70
    lda.l $414186
    sta.l $7E1A34
    lda.l $414188
    sta.l $7E1AE6
    lda.l $41417C
    sta.l $7E55DA
    sep #$20
    .a8
    lda.l $41417E
    sta.l $7E55D4
    rep #$30
    .a16
    .i16
    lda.l $41417A
    sta.l $7E55D6
    lda.l $414180
    sta.l $7E55DE
    lda.l $414182
    sta.l $7E55E8
    lda.l $414184
    sta.l $7E55EA
    lda #$1A00
    tcd
    lda #133
    sta $7A
    lda.l $414168
    jsl $1E93DB
    bcs Relay_ProjectFault_B_1
    sta.l $7E0A89
    lda.l $41416A
    jsl $1E93DB
    bcs Relay_ProjectFault_B_1
    sta.l $7E0A8B
    sep #$20
    .a8
    lda.l $414178
    sta.l $7E0AA8
    lda.l $41416E
    sta.l $7E0A8D
    bra Relay_ProjectNext_B_1
Relay_SnapshotUnbound_B_1:
    .a16
    .i16
    jmp Relay_ProjectNext_B_1
Relay_ProjectFault_B_1:
    .a16
    .i16
    lda #10
    sta.l $7E1764
    stp
Relay_SnapshotPolicyFault_B_1:
    .a16
    .i16
    lda #1
    sta.l $7E1764
    stp
Relay_ProjectNext_B_1:
    rep #$30
    .a16
    .i16
    lda.l $4141A2
    and #$00FF
    beq Relay_SnapshotZeroPolicy_B_2
    cmp #3
    bcc Relay_SnapshotBound_B_2
    jmp Relay_SnapshotPolicyFault_B_2
Relay_SnapshotZeroPolicy_B_2:
    jmp Relay_SnapshotUnbound_B_2
Relay_SnapshotBound_B_2:
    lda.l $41418C
    sta.l $7E1B14
    lda.l $41418E
    sta.l $7E1B16
    lda.l $414190
    sta.l $7E1B18
    lda.l $414192
    sta.l $7E1B1A
    lda.l $414194
    sta.l $7E1BE4
    lda.l $414196
    sta.l $7E1B06
    lda.l $414198
    sta.l $7E1BF6
    lda.l $41419A
    sta.l $7E1BFC
    lda.l $41419C
    sta.l $7E1BF0
    lda.l $41419E
    sta.l $7E1B70
    lda.l $4141AA
    sta.l $7E1B34
    lda.l $4141AC
    sta.l $7E1BE6
    lda.l $4141A0
    sta.l $7E565F
    sep #$20
    .a8
    lda.l $4141A2
    sta.l $7E5659
    rep #$30
    .a16
    .i16
    lda.l $41419E
    sta.l $7E565B
    lda.l $4141A4
    sta.l $7E5663
    lda.l $4141A6
    sta.l $7E566D
    lda.l $4141A8
    sta.l $7E566F
    lda.l $4141AE
    sta.l $7E565A
    lda #$1B00
    tcd
    lda #266
    sta $7A
    lda.l $41418C
    jsl $1E93DB
    bcs Relay_ProjectFault_B_2
    sta.l $7E0B0E
    lda.l $41418E
    jsl $1E93DB
    bcs Relay_ProjectFault_B_2
    sta.l $7E0B10
    sep #$20
    .a8
    lda.l $41419C
    sta.l $7E0B2D
    lda.l $414192
    sta.l $7E0B12
    bra Relay_ProjectNext_B_2
Relay_SnapshotUnbound_B_2:
    .a16
    .i16
    jmp Relay_ProjectNext_B_2
Relay_ProjectFault_B_2:
    .a16
    .i16
    lda #10
    sta.l $7E1764
    stp
Relay_SnapshotPolicyFault_B_2:
    .a16
    .i16
    lda #1
    sta.l $7E1764
    stp
Relay_ProjectNext_B_2:
    rep #$30
    .a16
    .i16
    lda.l $4141C6
    and #$00FF
    beq Relay_SnapshotZeroPolicy_B_3
    cmp #3
    bcc Relay_SnapshotBound_B_3
    jmp Relay_SnapshotPolicyFault_B_3
Relay_SnapshotZeroPolicy_B_3:
    jmp Relay_SnapshotUnbound_B_3
Relay_SnapshotBound_B_3:
    lda.l $4141B0
    sta.l $7E1C14
    lda.l $4141B2
    sta.l $7E1C16
    lda.l $4141B4
    sta.l $7E1C18
    lda.l $4141B6
    sta.l $7E1C1A
    lda.l $4141B8
    sta.l $7E1CE4
    lda.l $4141BA
    sta.l $7E1C06
    lda.l $4141BC
    sta.l $7E1CF6
    lda.l $4141BE
    sta.l $7E1CFC
    lda.l $4141C0
    sta.l $7E1CF0
    lda.l $4141C2
    sta.l $7E1C70
    lda.l $4141CE
    sta.l $7E1C34
    lda.l $4141D0
    sta.l $7E1CE6
    lda.l $4141C4
    sta.l $7E56E4
    sep #$20
    .a8
    lda.l $4141C6
    sta.l $7E56DE
    rep #$30
    .a16
    .i16
    lda.l $4141C2
    sta.l $7E56E0
    lda.l $4141C8
    sta.l $7E56E8
    lda.l $4141CA
    sta.l $7E56F2
    lda.l $4141CC
    sta.l $7E56F4
    lda.l $4141D2
    sta.l $7E56DF
    lda #$1C00
    tcd
    lda #399
    sta $7A
    lda.l $4141B0
    jsl $1E93DB
    bcs Relay_ProjectFault_B_3
    sta.l $7E0B93
    lda.l $4141B2
    jsl $1E93DB
    bcs Relay_ProjectFault_B_3
    sta.l $7E0B95
    sep #$20
    .a8
    lda.l $4141C0
    sta.l $7E0BB2
    lda.l $4141B6
    sta.l $7E0B97
    bra Relay_ProjectNext_B_3
Relay_SnapshotUnbound_B_3:
    .a16
    .i16
    jmp Relay_ProjectNext_B_3
Relay_ProjectFault_B_3:
    .a16
    .i16
    lda #10
    sta.l $7E1764
    stp
Relay_SnapshotPolicyFault_B_3:
    .a16
    .i16
    lda #1
    sta.l $7E1764
    stp
Relay_ProjectNext_B_3:
    rep #$30
    .a16
    .i16
    lda.l $4141EA
    and #$00FF
    beq Relay_SnapshotZeroPolicy_B_4
    cmp #3
    bcc Relay_SnapshotBound_B_4
    jmp Relay_SnapshotPolicyFault_B_4
Relay_SnapshotZeroPolicy_B_4:
    jmp Relay_SnapshotUnbound_B_4
Relay_SnapshotBound_B_4:
    lda.l $4141D4
    sta.l $7E1D14
    lda.l $4141D6
    sta.l $7E1D16
    lda.l $4141D8
    sta.l $7E1D18
    lda.l $4141DA
    sta.l $7E1D1A
    lda.l $4141DC
    sta.l $7E1DE4
    lda.l $4141DE
    sta.l $7E1D06
    lda.l $4141E0
    sta.l $7E1DF6
    lda.l $4141E2
    sta.l $7E1DFC
    lda.l $4141E4
    sta.l $7E1DF0
    lda.l $4141E6
    sta.l $7E1D70
    lda.l $4141F2
    sta.l $7E1D34
    lda.l $4141F4
    sta.l $7E1DE6
    lda.l $4141E8
    sta.l $7E5769
    sep #$20
    .a8
    lda.l $4141EA
    sta.l $7E5763
    rep #$30
    .a16
    .i16
    lda.l $4141E6
    sta.l $7E5765
    lda.l $4141EC
    sta.l $7E576D
    lda.l $4141EE
    sta.l $7E5777
    lda.l $4141F0
    sta.l $7E5779
    lda.l $4141F6
    sta.l $7E5764
    lda #$1D00
    tcd
    lda #532
    sta $7A
    lda.l $4141D4
    jsl $1E93DB
    bcs Relay_ProjectFault_B_4
    sta.l $7E0C18
    lda.l $4141D6
    jsl $1E93DB
    bcs Relay_ProjectFault_B_4
    sta.l $7E0C1A
    sep #$20
    .a8
    lda.l $4141E4
    sta.l $7E0C37
    lda.l $4141DA
    sta.l $7E0C1C
    bra Relay_ProjectNext_B_4
Relay_SnapshotUnbound_B_4:
    .a16
    .i16
    jmp Relay_ProjectNext_B_4
Relay_ProjectFault_B_4:
    .a16
    .i16
    lda #10
    sta.l $7E1764
    stp
Relay_SnapshotPolicyFault_B_4:
    .a16
    .i16
    lda #1
    sta.l $7E1764
    stp
Relay_ProjectNext_B_4:
    rep #$30
    .a16
    .i16
    lda.l $41420E
    and #$00FF
    beq Relay_SnapshotZeroPolicy_B_5
    cmp #3
    bcc Relay_SnapshotBound_B_5
    jmp Relay_SnapshotPolicyFault_B_5
Relay_SnapshotZeroPolicy_B_5:
    jmp Relay_SnapshotUnbound_B_5
Relay_SnapshotBound_B_5:
    lda.l $4141F8
    sta.l $7E1E14
    lda.l $4141FA
    sta.l $7E1E16
    lda.l $4141FC
    sta.l $7E1E18
    lda.l $4141FE
    sta.l $7E1E1A
    lda.l $414200
    sta.l $7E1EE4
    lda.l $414202
    sta.l $7E1E06
    lda.l $414204
    sta.l $7E1EF6
    lda.l $414206
    sta.l $7E1EFC
    lda.l $414208
    sta.l $7E1EF0
    lda.l $41420A
    sta.l $7E1E70
    lda.l $414216
    sta.l $7E1E34
    lda.l $414218
    sta.l $7E1EE6
    lda.l $41420C
    sta.l $7E57EE
    sep #$20
    .a8
    lda.l $41420E
    sta.l $7E57E8
    rep #$30
    .a16
    .i16
    lda.l $41420A
    sta.l $7E57EA
    lda.l $414210
    sta.l $7E57F2
    lda.l $414212
    sta.l $7E57FC
    lda.l $414214
    sta.l $7E57FE
    lda.l $41421A
    sta.l $7E57E9
    lda #$1E00
    tcd
    lda #665
    sta $7A
    lda.l $4141F8
    jsl $1E93DB
    bcs Relay_ProjectFault_B_5
    sta.l $7E0C9D
    lda.l $4141FA
    jsl $1E93DB
    bcs Relay_ProjectFault_B_5
    sta.l $7E0C9F
    sep #$20
    .a8
    lda.l $414208
    sta.l $7E0CBC
    lda.l $4141FE
    sta.l $7E0CA1
    bra Relay_ProjectNext_B_5
Relay_SnapshotUnbound_B_5:
    .a16
    .i16
    jmp Relay_ProjectNext_B_5
Relay_ProjectFault_B_5:
    .a16
    .i16
    lda #10
    sta.l $7E1764
    stp
Relay_SnapshotPolicyFault_B_5:
    .a16
    .i16
    lda #1
    sta.l $7E1764
    stp
Relay_ProjectNext_B_5:
    rep #$30
    .a16
    .i16
Relay_Flush_Return:
    .a16
    .i16
    jsl Relay_DrainEvents
    .a16
    .i16
    rep #$30
    pld
    plb
    ply
    plx
    plp
    rtl
Relay_Flush_Timeout:
    .a8
    .i16
    rep #$30
    .a16
    .i16
    lda #21
    sta.l $7E1764
    lda #1
    sta.l $7E175C
    lda #2
    sta.l $7E175E
    pld
    plb
    ply
    plx
    plp
    rtl
Relay_Timeout:
    .a8
    .i16
    rep #$30
    .a16
    lda #21
    sta.l $7E1764
    stp
Relay_DrainEvents:
    .a16
    .i16
    php
    rep #$30
    phx
    phy
    phd
    phb
    sep #$20
    .a8
    lda #0
    pha
    plb
    rep #$30
    .a16
    .i16
    lda.l $7E175C
    bne Relay_DrainEvents__owned
    jml Relay_DrainEvents__done
Relay_DrainEvents__owned:
Relay_DrainEvents__loop:
    rep #$30
    .a16
    .i16
    lda.l $412434
    beq Relay_DrainEvents__no_overflow
    jml Relay_DrainEvents__fault
Relay_DrainEvents__no_overflow:
    ; Both CPUs access this ring asynchronously in the production path. Take
    ; a stable producer-head sample before deciding empty/nonempty; a row is
    ; consumed only after its published sequence matches the current tail.
    lda.l $412430
    sta.l $7E1766
    lda.l $412430
    cmp.l $7E1766
    bne Relay_DrainEvents__loop
    lda.l $412432
    cmp.l $7E1766
    bne Relay_DrainEvents__has_event
    jml Relay_DrainEvents__done
Relay_DrainEvents__has_event:
    and #$007F
    asl a
    asl a
    asl a
    asl a
    tax
    lda.l $412450,x
    cmp.l $412432
    beq Relay_DrainEvents__sequence_ok
    lda.l $412430
    cmp.l $7E1766
    bne Relay_DrainEvents__sequence_retry
    jml Relay_DrainEvents__fault
Relay_DrainEvents__sequence_retry:
    jml Relay_DrainEvents__loop
Relay_DrainEvents__sequence_ok:
Relay_DrainEvents__record:
    lda.l $412452,x
    cmp #1
    beq Relay_DrainEvents__visual
    cmp #2
    beq Relay_DrainEvents__hit
    cmp #3
    bne Relay_DrainEvents__check_native_prop
    jml Relay_DrainEvents__unlink
Relay_DrainEvents__check_native_prop:
    cmp #4
    bne Relay_DrainEvents__unknown_kind
    jml Relay_DrainEvents__native_prop
Relay_DrainEvents__unknown_kind:
    jml Relay_DrainEvents__fault
Relay_DrainEvents__visual:
    lda.l $7E176C
    inc a
    sta.l $7E176C
    jml Relay_DrainEvents__ack
Relay_DrainEvents__hit:
    ; HP/role are already coherent in the acknowledged snapshot. This record
    ; carries the ordered external hit notification; do not replay damage or
    ; increment the canonical source hit counter mirrored by that snapshot.
    ; Dispatch the existing S-CPU landed-hit sound service exactly once; the
    ; separate delivery sequence below remains independent of world counters.
    ; Source-owned combat bypasses native Character_HitApply callbacks.
    ; Route the ordered landed hit to BOR opponent HUD without replaying HP.
    phx
    jsl $00B160
    plx
    lda.l $412458,x
    sec
    sbc #$7900
    bcs Relay_DrainEvents__hit_attacker_base_ok
    jml Relay_DrainEvents__fault
Relay_DrainEvents__hit_attacker_base_ok:
    cmp #$0600
    bcc Relay_DrainEvents__hit_attacker_range_ok
    jml Relay_DrainEvents__fault
Relay_DrainEvents__hit_attacker_range_ok:
    sta.l $7E1768
    and #$00FF
    beq Relay_DrainEvents__hit_attacker_aligned
    jml Relay_DrainEvents__fault
Relay_DrainEvents__hit_attacker_aligned:
    lda.l $7E1768
    xba
    and #$00FF
    cmp #6
    bcc Relay_DrainEvents__hit_attacker_slot_ok
    jml Relay_DrainEvents__fault
Relay_DrainEvents__hit_attacker_slot_ok:
    sta.l $7E1768
    lda.l $41245A,x
    sec
    sbc #$7900
    bcs Relay_DrainEvents__hit_victim_base_ok
    jml Relay_DrainEvents__fault
Relay_DrainEvents__hit_victim_base_ok:
    cmp #$0600
    bcc Relay_DrainEvents__hit_victim_range_ok
    jml Relay_DrainEvents__fault
Relay_DrainEvents__hit_victim_range_ok:
    sta.l $7E176A
    and #$00FF
    beq Relay_DrainEvents__hit_victim_aligned
    jml Relay_DrainEvents__fault
Relay_DrainEvents__hit_victim_aligned:
    lda.l $7E176A
    xba
    and #$00FF
    cmp #6
    bcc Relay_DrainEvents__hit_victim_slot_ok
    jml Relay_DrainEvents__fault
Relay_DrainEvents__hit_victim_slot_ok:
    sta.l $7E176A
    ; Publish only player/opponent pairs; reverse enemy-to-player hits.
    lda.l $7E1768
    cmp #2
    bcs Relay_DrainEvents__hit_attacker_npc
    lda.l $7E176A
    cmp #2
    bcs Relay_DrainEvents__hit_player_attacker
    jml Relay_DrainEvents__ack
Relay_DrainEvents__hit_player_attacker:
    bra Relay_DrainEvents__hit_publish
Relay_DrainEvents__hit_attacker_npc:
    lda.l $7E176A
    cmp #2
    bcc Relay_DrainEvents__hit_player_victim
    jml Relay_DrainEvents__ack
Relay_DrainEvents__hit_player_victim:
    lda.l $7E1768
    pha
    lda.l $7E176A
    sta.l $7E1768
    pla
    sta.l $7E176A
Relay_DrainEvents__hit_publish:
    lda.l $7E1768
    asl a
    tax
    lda.l $05872C,x
    pha
    lda.l $7E176A
    asl a
    tax
    lda.l $05872C,x
    tay
    pla
    tax
    jsl $058148
    jml Relay_DrainEvents__ack
    jsl $00B160
    jml Relay_DrainEvents__ack
Relay_DrainEvents__native_prop:
    ; Bounded diagnostic counters in the otherwise unused Normal-prop
    ; protocol tail; campaign verification reads these without pausing the
    ; worker or changing the event/ownership contract.
    lda.l $412D10
    inc a
    sta.l $412D10
    ; Retain the event tuple before using X as a physical-entity table index.
    txa
    sta.l $7E1766
    lda.l $41245A,x
    sta.l $7E1768
    lda.l $41245C,x
    sta.l $7E176A
    and #$FF00
    xba
    and #$00FF
    cmp #1
    bcs Relay_DrainEvents__native_prop_slot_low_ok
    jml Relay_DrainEvents__fault
Relay_DrainEvents__native_prop_slot_low_ok:
    cmp #6
    bcc Relay_DrainEvents__native_prop_slot_high_ok
    jml Relay_DrainEvents__fault
Relay_DrainEvents__native_prop_slot_high_ok:
    rep #$30
    .a16
    .i16
    ; The generic hit routine reads this ABI as a 16-bit table index even
    ; though its storage declaration is a byte. Clear/write both bytes here
    ; so a prior host hit cannot leave a stale high byte in the invulnerability
    ; lookup index.
    sta.l $7FF50C
    asl a
    tax
    lda.l $0980EB,x
    tcd
    sep #$20
    .a8
    lda $000F
    cmp #$03
    beq Relay_DrainEvents__native_prop_kind_ok
    cmp #$04
    beq Relay_DrainEvents__native_prop_kind_ok
    jml Relay_DrainEvents__native_prop_ack
Relay_DrainEvents__native_prop_kind_ok:
    rep #$30
    .a16
    .i16
    lda.l $412D12
    inc a
    sta.l $412D12
    sep #$20
    .a8
    lda $0023
    bne Relay_DrainEvents__native_prop_alive
    jml Relay_DrainEvents__native_prop_ack
Relay_DrainEvents__native_prop_alive:
    rep #$30
    .a16
    .i16
    lda.l $0980F7,x
    sta.l $7FF500
    ; Event D is the current SA-1 actor-context page ($7900 + slot*$100,
    ; matching WHost_SlotTable). Map that
    ; owner back to its one native player D window without copying its actor
    ; context or changing who owns simulation.
    lda.l $7E1766
    tax
    lda.l $412458,x
    sec
    sbc #$7900
    and #$FF00
    xba
    asl a
    tax
    cpx #12
    bcc Relay_DrainEvents__native_prop_attacker_slot_ok
    jml Relay_DrainEvents__fault
Relay_DrainEvents__native_prop_attacker_slot_ok:
    lda.l $0980EB,x
    tcd
    sep #$20
    .a8
    lda $000F
    cmp #1
    beq Relay_DrainEvents__native_prop_attacker_ok
    jml Relay_DrainEvents__native_prop_ack
Relay_DrainEvents__native_prop_attacker_ok:
    rep #$30
    .a16
    .i16
    ; Native S-CPU-owned targets use CharacterEntity coordinates in the same
    ; policy-projected space as render snapshots. Convert the source-exact
    ; event position through the attacker's bridge policy before BOR's native
    ; AABB test; raw SA-1 coordinates against projected host coordinates
    ; silently miss the target.
    tdc
    sec
    sbc #$0A00
    sta $7A
    lda.l $7E1768
    jsl $1E93DB
    bcc Relay_DrainEvents__native_prop_project_x_ok
    jml Relay_DrainEvents__native_prop_ack
Relay_DrainEvents__native_prop_project_x_ok:
    sta.l $7E1768
    lda.l $7E176A
    and #$00FF
    jsl $1E93DB
    bcc Relay_DrainEvents__native_prop_project_y_ok
    jml Relay_DrainEvents__native_prop_ack
Relay_DrainEvents__native_prop_project_y_ok:
    sta.l $7E176A
    .a16
    .i16
    ; Run the native collision/damage tail at the attack's source-tick
    ; coordinates after converting into the target's S-CPU-native space, then
    ; restore the coherent latest render position.
    lda $0004
    pha
    sep #$20
    .a8
    lda $0006
    pha
    rep #$30
    .a16
    .i16
    lda.l $7E1768
    sta $0004
    lda.l $7E176A
    and #$00FF
    sep #$20
    .a8
    sta $0006
    rep #$30
    .a16
    .i16
    lda.l $7FF500
    tax
    jsl $0C99A9
    bcs Relay_DrainEvents__native_prop_landed
    rep #$30
    .a16
    .i16
    lda.l $412D16
    inc a
    sta.l $412D16
    jml Relay_DrainEvents__native_prop_restore
Relay_DrainEvents__native_prop_landed:
    rep #$30
    .a16
    .i16
    lda.l $412D14
    inc a
    sta.l $412D14
    jsl $00E4F9
    rep #$30
    .a16
    .i16
    lda.l $7FF500
    clc
    adc #$0023
    tax
    sep #$20
    .a8
    lda.l $7E0A00,x
    bne Relay_DrainEvents__native_prop_restore
    rep #$30
    .a16
    .i16
    lda.l $7FF500
    tax
    jsl $088A16
Relay_DrainEvents__native_prop_restore:
    sep #$20
    .a8
    pla
    sta $0006
    rep #$30
    .a16
    .i16
    pla
    sta $0004
Relay_DrainEvents__native_prop_ack:
    jml Relay_DrainEvents__ack
Relay_DrainEvents__unlink:
    lda.l $412458,x
    sec
    sbc #$6000
    ; Producer scratch $412436-$41243E is SA-1-owned. The relay runs
    ; concurrently: using its source-D cell here can corrupt the next
    ; published record between S6_EventPush's TDC and row copy.
    sta.l $7E176A
    ; Unlink events name one of the six fixed resident source pages. Reject
    ; malformed pages before searching the S-CPU bridge table.
    cmp #$1900
    bcc Relay_DrainEvents__fault
    cmp #$1F00
    bcs Relay_DrainEvents__fault
    and #$00FF
    bne Relay_DrainEvents__fault
    ldx #0
Relay_DrainEvents__find:
    lda.l $7E5553,x
    cmp.l $7E176A
    bne Relay_DrainEvents__next_context
    jml Relay_DrainEvents__found
Relay_DrainEvents__next_context:
    txa
    clc
    adc #133
    tax
    cpx #798
    bcc Relay_DrainEvents__find
    ; A source-side lifecycle/rebind boundary may already have retired this
    ; bridge row after the worker unlinked it. The event is still ordered, but
    ; there is no current native owner to remove; acknowledge it instead of
    ; faulting or applying the stale unlink to a later occupant.
    jml Relay_DrainEvents__stale_unlink
Relay_DrainEvents__stale_unlink:
    jml Relay_DrainEvents__ack
Relay_DrainEvents__found:
    txa
    clc
    adc #$0A00
    jsl $1E9FCF
    lda.l $7E1764
    beq Relay_DrainEvents__unlink_ok
    cmp #24
    bne Relay_DrainEvents__unlink_fault
    ; The sequenced native-removal mailbox is single-entry. If an earlier
    ; unlink is still awaiting acknowledgement, retain this event at the ring
    ; tail and retry on the next main-loop service; treating ordinary mailbox
    ; backpressure as an event fault would halt the S-CPU and strand the world.
    lda #0
    sta.l $7E1764
    jml Relay_DrainEvents__done
Relay_DrainEvents__unlink_fault:
    jml Relay_DrainEvents__fault
Relay_DrainEvents__unlink_ok:
Relay_DrainEvents__ack:
    ; Event-specific handlers may return in M=8. Restore the ring ABI before
    ; touching 16-bit sequence counters or forming the next record address.
    rep #$30
    .a16
    .i16
    lda.l $412432
    inc a
    sta.l $412432
    lda.l $7E1778
    inc a
    sta.l $7E1778
    jml Relay_DrainEvents__loop
Relay_DrainEvents__fault:
    .a16
    .i16
    lda #23
    sta.l $7E1764
    stp
Relay_DrainEvents__done:
    rep #$30
    plb
    pld
    ply
    plx
    plp
    rtl
