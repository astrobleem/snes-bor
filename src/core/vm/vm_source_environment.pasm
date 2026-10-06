; Native script checkwall(x,z) for compiler-proven immutable empty wall lists.
; This is height (DECIMAL zero), not the engine checkwall wall-index API.
; The owner grants B4D1 only for the current checked zero-wall stage, and must
; retire the lease before level changes. Nonempty geometry faults explicitly.
SourceEnvironment4086_Ready = $7FFA82
SourceEnvironment4086_WallCount = $7FFA84
SourceEnvironment4086_Stage = $7FFA86

Vm_SourceCheckWall:
.a16
.i16
    lda.l VmNativeVariant_ContextValid
    cmp #$B48F
    bne Vm_SourceCheckWall_Bad
    lda.l VmCall_Argc
    and #$00FF
    cmp #2
    bne Vm_SourceCheckWall_Bad
    lda.l SourceEnvironment4086_Ready
    cmp #$B4D1
    bne Vm_SourceCheckWall_Bad
    lda.l SourceEnvironment4086_WallCount
    bne Vm_SourceCheckWall_Bad
    lda.l SourceEnvironment4086_Stage
    beq Vm_SourceCheckWall_Bad
    ; With no wall candidates, every numeric input returns zero. Failed
    ; numeric conversions also return zero in the pinned script API.
    lda #BOR_VT_DECIMAL
    sta.l VmNativeVariant_Result
    lda #0
    sta.l VmNativeVariant_Result+2
    sta.l VmNativeVariant_Result+4
    sta.l VmNativeVariant_Result+6
    clc
    rtl
Vm_SourceCheckWall_Bad:
.a16
.i16
    lda #VMERR_BAD_NATIVE
    sec
    rtl
