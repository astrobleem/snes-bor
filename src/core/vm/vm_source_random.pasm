; af23dc9 engine/source/randlib/rand32.c, Win32 unsigned long = 32 bits.
; One source-world stream, never a per-entity seed. The world owner installs
; the seed before publishing B4D4 and owns all AI/script call ordering.
; Cold boot retires the lease. This primitive does not install a world owner.
SourceRandom4086_Ready = $7FFAE0
SourceRandom4086_SeedLo = $7FFAE2
SourceRandom4086_SeedHi = $7FFAE4
SourceRandom4086_CallsLo = $7FFAE6
SourceRandom4086_CallsHi = $7FFAE8
SourceRandom4086_Busy = $7FFAEA
SourceRandom4086_ScratchEnd = $7FFAEC

Vm_SourceRand:
.a16
.i16
    lda.l VmNativeVariant_ContextValid
    cmp #$B48F
    bne Vm_SourceRand_Bad
    lda.l VmCall_Argc
    and #$00FF
    bne Vm_SourceRand_Bad
    jml SourceRandom4086_Next
Vm_SourceRand_Bad:
.a16
.i16
    lda #VMERR_BAD_NATIVE
    sec
    rtl

SourceRandom4086_Next:
.a16
.i16
    lda.l SourceRandom4086_Ready
    cmp #$B4D4
    bne Vm_SourceRand_Bad
    lda.l SourceRandom4086_Busy
    bne Vm_SourceRand_Bad
    php
    rep #$38
    phx
    phy
    phb
    phd
    lda #1
    sta.l SourceRandom4086_Busy
    ; All multiply scratch is stack local. Interrupted VM direct-page state
    ; is preserved, and no actor DP or global arithmetic scratch is borrowed.
    tsc
    sec
    sbc #26
    tcs
    inc a
    tcd
    sep #$20
.a8
    lda #0
    pha
    plb
    rep #$20
.a16
    lda.l SourceRandom4086_SeedLo
    sta $00
    lda.l SourceRandom4086_SeedHi
    sta $02
    jsl S6_Random32
    lda $00
    sta.l SourceRandom4086_SeedLo
    lda $02
    sta.l SourceRandom4086_SeedHi
    lda #BOR_VT_INTEGER
    sta.l VmNativeVariant_Result
    lda #0
    sta.l VmNativeVariant_Result+2
    lda $04
    sta.l VmNativeVariant_Result+4
    lda $06
    sta.l VmNativeVariant_Result+6
    lda.l SourceRandom4086_CallsLo
    clc
    adc #1
    sta.l SourceRandom4086_CallsLo
    lda.l SourceRandom4086_CallsHi
    adc #0
    sta.l SourceRandom4086_CallsHi
    lda #0
    sta.l SourceRandom4086_Busy
    tsc
    clc
    adc #26
    tcs
    pld
    plb
    ply
    plx
    plp
    clc
    rtl
SourceRandom4086_Bad:
.a16
.i16
    lda #VMERR_BAD_NATIVE
    sec
    rtl

; The existing independently checked 48-bit multiply retains product bits
; 16..47 for the returned word and bits 0..31 for the next seed. Its discrete
; recurrence matches the pinned 4086 C authority; the old S6 name is internal.
.include "../actor_source_rng.pasm"
