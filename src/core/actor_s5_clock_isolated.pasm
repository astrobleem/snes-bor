; S5 rational 200Hz clock, isolated host ABI. D is a separate zeroed clock
; context, DBR=0, native, decimal clear. Public JSL/RTL, A/X/Y/P clobbered.
; 00/02 elapsed master clocks * 200 (u32), 04/06 remainder (u32),
; 08/0A master clock rate (u32), 0C/0E emitted source tick count (u32).
; 16 status: 0 success, 1 invalid rate/remainder, 2 elapsed overflow;
; 1A/1C scratch. Invalid calls leave remainder/count unchanged.
; Input rate >0, remainder < rate, elapsed*200 + remainder must fit u32.
; Host supplies measured/platform-defined elapsed time, never nominal 60Hz.
; Callback S5_HostSourceTick must preserve D/DBR and return A16/I16.
; Callback sees incremented source count and runs one 200Hz update. Dispatch
; drift every second source tick. Scheduling can batch updates at vblank;
; this does not mean physical CPU callbacks are spaced exactly 5ms apart.
S5_ClockAdvance:
    rep #$30
    .a16
    .i16
    stz $16
    lda $08
    ora $0A
    beq S5_ClockAdvance__invalid
    lda $06
    cmp $0A
    bcc S5_ClockAdvance__add
    bne S5_ClockAdvance__invalid
    lda $04
    cmp $08
    bcs S5_ClockAdvance__invalid
S5_ClockAdvance__add:
    .a16
    .i16
    lda $04
    clc
    adc $00
    sta $1A
    lda $06
    adc $02
    bcs S5_ClockAdvance__overflow
    sta $06
    lda $1A
    sta $04
S5_ClockAdvance__next:
    .a16
    .i16
    lda $06
    cmp $0A
    bcc S5_ClockAdvance__done
    bne S5_ClockAdvance__emit
    lda $04
    cmp $08
    bcc S5_ClockAdvance__done
S5_ClockAdvance__emit:
    .a16
    .i16
    lda $04
    sec
    sbc $08
    sta $04
    lda $06
    sbc $0A
    sta $06
    inc $0C
    bne S5_ClockAdvance__callback
    inc $0E
S5_ClockAdvance__callback:
    .a16
    .i16
    jsl S5_HostSourceTick
    bra S5_ClockAdvance__next
S5_ClockAdvance__done:
    .a16
    .i16
    rtl
S5_ClockAdvance__invalid:
    .a16
    .i16
    lda #1
    sta $16
    rtl
S5_ClockAdvance__overflow:
    .a16
    .i16
    lda #2
    sta $16
    rtl
