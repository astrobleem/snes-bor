; Explicit physical-controller bridge for an exclusively owned foreign input
; snapshot. Far entry: A=1 or 2 ports, X/Y=low/high source time. Preserves all
; registers/widths/DBR. Carry=1 rejects unsupported port counts without writes.
; Call once per outer inputrefresh, not once per catch-up source tick. The
; snapshot stays immutable across callbacks and catch-up ticks. No auto-enable.
SourceInputController_Count = $7FF8E2
SourceInputController_TimeLo = $7FF8E4
SourceInputController_TimeHi = $7FF8E6
SourceInputController_OldReady = $7FF8E8
SourceInputController_OldCount = $7FF8EA
SourceInputController_Raw = $7FF8EC
SourceInputController_Mapped = $7FF8EE
SourceInputController_Old = $7FF8F0
SourceInputController_Raw1 = $7FF8F4 ; exact words consumed, observer only
SourceInputController_Raw2 = $7FF8F6

SourceInputController_Refresh:
.a16
.i16
    php
    rep #$31
    pha
    phx
    phy
    phb
    cmp #1
    beq SourceInputController_Refresh__valid
    cmp #2
    beq SourceInputController_Refresh__valid
    plb
    ply
    plx
    pla
    plp
    sec
    rtl
SourceInputController_Refresh__valid:
.a16
.i16
    sta.l SourceInputController_Count
    txa
    sta.l SourceInputController_TimeLo
    tya
    sta.l SourceInputController_TimeHi
    sep #$20
.a8
    lda #0
    pha
    plb
    rep #$31
.a16
.i16
SourceInputController_Refresh__wait:
.a16
.i16
    lda.w $4212
    and #1
    bne SourceInputController_Refresh__wait
    lda.l VmSourceInput_Ready
    sta.l SourceInputController_OldReady
    lda.l VmSourceInput_Count
    sta.l SourceInputController_OldCount
    lda #0
    sta.l VmSourceInput_Ready
    ldx #0
SourceInputController_Refresh__port:
.a16
.i16
    lda #0
    sta.l SourceInputController_Old
    lda.l SourceInputController_OldReady
    cmp #$B4C2
    bne SourceInputController_Refresh__read
    lda.l SourceInputController_OldCount
    cmp.l SourceInputController_Count
    bne SourceInputController_Refresh__read
    lda.l VmSourceInput_Data,x
    sta.l SourceInputController_Old
SourceInputController_Refresh__read:
.a16
.i16
    cpx #0
    bne SourceInputController_Refresh__second
    lda.w $4218
    sta.l SourceInputController_Raw1
    bra SourceInputController_Refresh__signature
SourceInputController_Refresh__second:
.a16
.i16
    lda.w $421A
    sta.l SourceInputController_Raw2
SourceInputController_Refresh__signature:
.a16
.i16
    pha
    and #$000F
    beq SourceInputController_Refresh__pad
    pla
    lda #0
    bra SourceInputController_Refresh__mapped
SourceInputController_Refresh__pad:
.a16
.i16
    pla
    jsr SourceInputController_Map
SourceInputController_Refresh__mapped:
.a16
.i16
    sta.l VmSourceInput_Data,x
    eor #$FFFF
    and.l SourceInputController_Old
    sta.l VmSourceInput_Data+8,x
    lda.l SourceInputController_Old
    eor #$FFFF
    and.l VmSourceInput_Data,x
    sta.l VmSourceInput_Data+4,x
    lda #0
    sta.l VmSourceInput_Data+2,x
    sta.l VmSourceInput_Data+6,x
    sta.l VmSourceInput_Data+10,x
    cpx #12
    beq SourceInputController_Refresh__commit
    lda.l SourceInputController_Count
    cmp #1
    beq SourceInputController_Refresh__commit
    ldx #12
    jmp SourceInputController_Refresh__port
SourceInputController_Refresh__commit:
.a16
.i16
    lda.l SourceInputController_Count
    sta.l VmSourceInput_Count
    lda.l SourceInputController_TimeLo
    sta.l VmSourceInput_Tick
    lda.l SourceInputController_TimeHi
    sta.l VmSourceInput_Tick+2
    lda #$B4C2
    sta.l VmSourceInput_Ready
SourceInputController_Refresh__done:
.a16
.i16
    plb
    ply
    plx
    pla
    plp
    clc
    rtl
