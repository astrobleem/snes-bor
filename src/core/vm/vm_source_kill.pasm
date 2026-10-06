; Typed openbor_killentity boundary. NULL returns INTEGER 0 without calling
; kill; every admitted non-NULL physical pointer returns 1, including a dead
; row. Native retirement has explicit no-event/no-minion capability guards.
; Non-NULL DECIMAL/STR pointer reinterpretation is unbound; no numeric alias.
Vm_SourceKill:
.a16
.i16
    php
    rep #$38
    phx
    phy
    lda.l VmCall_Argc
    and #$00FF
    beq Vm_SourceKill_Bad
    lda #0
    jsr Vm_SourceEntityArgSlot
    lda.l VmSlots_Wram+4,x
    sta.l SourceRetirement4086_ArgLo
    lda.l VmSlots_Wram+6,x
    sta.l SourceRetirement4086_ArgHi
    ora.l SourceRetirement4086_ArgLo
    beq Vm_SourceKill_CheckNull
    lda.l VmSlots_Wram,x
    and #$00FF
    cmp #5
    beq Vm_SourceKill_Pointer
    cmp #1
    bne Vm_SourceKill_Bad
Vm_SourceKill_Pointer:
.a16
.i16
    jsl SourceRetirement4086_ResolvePointer
    bcs Vm_SourceKill_Bad
    cmp #$FFFF
    beq Vm_SourceKill_Bad
    sta.l SourceRetirement4086_Slot
    jsl SourceRetirement4086_ApplyNoEvents
    bcs Vm_SourceKill_Bad
    lda #1
    bra Vm_SourceKill_Integer
Vm_SourceKill_CheckNull:
.a16
.i16
    lda.l VmSlots_Wram,x
    and #$00FF
    beq Vm_SourceKill_Null
    cmp #1
    beq Vm_SourceKill_Null
    cmp #5
    bne Vm_SourceKill_Bad
Vm_SourceKill_Null:
.a16
.i16
    lda #0
Vm_SourceKill_Integer:
.a16
.i16
    sta.l VmNativeVariant_Result+4
    lda #1
    sta.l VmNativeVariant_Result
    lda #0
    sta.l VmNativeVariant_Result+2
    sta.l VmNativeVariant_Result+6
    ply
    plx
    plp
    clc
    rtl
Vm_SourceKill_Bad:
.a16
.i16
    lda.l SourceRetirement4086_Ready
    cmp #$B4F8
    bne Vm_SourceKill_BadReturn
    lda #3
    sta.l SourceRetirement4086_Status
Vm_SourceKill_BadReturn:
.a16
.i16
    lda #VMERR_BAD_NATIVE
    ply
    plx
    plp
    sec
    rtl
