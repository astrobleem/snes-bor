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

S6_CheckPolicy:
    rep #$30
    .a16
    .i16
    lda $E0
    cmp #1
    beq S6_CheckPolicy__ok
    lda #1
    sta $FC
    sec
    rtl
S6_CheckPolicy__ok:
    .a16
    .i16
    clc
    rtl

; A=requested role, FA=reset. set_anim same role is a no-op; reset_anim
; restarts but intentionally DOES NOT reset lastanimpos (pinned BOR.C).
S6_SetRole:
    rep #$30
    .a16
    .i16
    sta $F8
    jsl S6_CheckPolicy
    bcc S6_SetRole__policy
    rtl
S6_SetRole__policy:
    .a16
    .i16
    lda $FA
    bne S6_SetRole__find
    lda $F8
    cmp $E4
    bne S6_SetRole__find
    rtl
S6_SetRole__find:
    .a16
    .i16
    ldx $CC
    beq S6_SetRole__missing
    ldy #0
S6_SetRole__search:
    .a16
    .i16
    lda [$C8],y
    cmp $F8
    beq S6_SetRole__found
    tya
    clc
    adc #16
    tay
    dex
    bne S6_SetRole__search
S6_SetRole__missing:
    .a16
    .i16
    lda #2
    sta $FC
    rtl
S6_SetRole__found:
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
    bne S6_SetRole__load
    lda #$FFFF
    sta $F4
S6_SetRole__load:
    .a16
    .i16
    jsl S6_EnterFrame
    rtl

S6_EnterFrame:
    rep #$30
    .a16
    .i16
    jsl S5_LoadFrame
    lda $2C
    beq S6_EnterFrame__valid
    lda #3
    sta $FC
    rtl
S6_EnterFrame__valid:
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
    bne S6_EnterFrame__right
    lda $14
    sec
    sbc $5C
    bra S6_EnterFrame__position
S6_EnterFrame__right:
    .a16
    .i16
    lda $14
    clc
    adc $5C
S6_EnterFrame__position:
    .a16
    .i16
    sta $14
    jsl S6_FrameChanged
    rtl

S6_ThinkPass:
    rep #$30
    .a16
    .i16
    jsl S6_CheckPolicy
    bcs S6_ThinkPass__done
    lda $F6
    beq S6_ThinkPass__done
    ; A null source think callback leaves nextthink unchanged. Driver0 is
    ; explicitly NONE, not a callback that happens to do nothing.
    lda $E6
    beq S6_ThinkPass__done
    lda $E8
    cmp $D0
    bne S6_ThinkPass__done
    lda $EA
    cmp $D2
    bne S6_ThinkPass__done
    lda $D0
    clc
    adc #2
    sta $E8
    lda $D2
    adc #0
    sta $EA
    jsl S6_Think
S6_ThinkPass__done:
    .a16
    .i16
    rtl

S6_AnimationPass:
    rep #$30
    .a16
    .i16
    jsl S6_CheckPolicy
    bcs S6_AnimationPass__done
    lda $F6
    beq S6_AnimationPass__done
    lda $D4
    cmp $D0
    bne S6_AnimationPass__done
    lda $D6
    cmp $D2
    bne S6_AnimationPass__done
    lda $06
    clc
    adc $10
    bmi S6_AnimationPass__reverse_wrap
    cmp $04
    bcc S6_AnimationPass__frame
    lda #0
    bra S6_AnimationPass__wrap
S6_AnimationPass__reverse_wrap:
    .a16
    .i16
    lda $04
    dec a
S6_AnimationPass__wrap:
    .a16
    .i16
    ldx $12
    bne S6_AnimationPass__frame
    stz $10
    lda $FE
    beq S6_AnimationPass__done
    stz $F6
    bra S6_AnimationPass__done
S6_AnimationPass__frame:
    .a16
    .i16
    ldx $10
    beq S6_AnimationPass__done
    sta $06
    jsl S6_EnterFrame
S6_AnimationPass__done:
    .a16
    .i16
    rtl
