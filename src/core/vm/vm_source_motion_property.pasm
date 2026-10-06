; Generic velocity/model speed mutation over the canonical owned BW pool.
; Pinned changeentityproperty velocity is x,z,y; speed changes modeldata.speed,
; not speedmul. All values use explicit ACCEPTED_COMPAT_Q16_16.
; Sidecar +36,+40,+44 are velocity x,z,y; +60 is modeldata.speed.
; The original read-view lease cannot grant this capability.
SourceMotionProperty_Side = $7FFA80

Vm_SourceMotionProperty:
.a16
.i16
    lda.l VmSourceWorld_Ready
    cmp #$B4A3
    bne Vm_SourceMotionProperty_Bad
    lda.l VmSourceWorld_PoolBase
    cmp #$4000
    bne Vm_SourceMotionProperty_Bad
    lda.l VmSourceWorld_SideBase
    cmp #$6800
    bne Vm_SourceMotionProperty_Bad
    lda.l VmSourceEntity_Base
    cmp #$4000
    bne Vm_SourceMotionProperty_Bad
    lda.l VmSourceEntity_Bank
    and #$00FF
    cmp #$41
    bne Vm_SourceMotionProperty_Bad
    lda.l VmSourceWorld_Count
    beq Vm_SourceMotionProperty_Bad
    cmp #129
    bcs Vm_SourceMotionProperty_Bad
    cmp.l VmSourceEntity_Count
    bne Vm_SourceMotionProperty_Bad
    lda.l VmSourceEntity_Index
    cmp.l VmSourceWorld_Count
    bcs Vm_SourceMotionProperty_Bad
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.l SourceMotionProperty_Side
    lda #2
    sta.l VmSourceMutation_Tag
    sta.l VmSourceMutation_Arg
    lda.l VmSourceMutation_Name
    cmp #112
    beq Vm_SourceMotionProperty_Velocity
    lda #60
    bra Vm_SourceMotionProperty_Offset
Vm_SourceMotionProperty_Velocity:
.a16
.i16
    lda #36
Vm_SourceMotionProperty_Offset:
.a16
.i16
    sta.l VmSourceMutation_Offset
    bra Vm_SourceMotionProperty_Component
Vm_SourceMotionProperty_Bad:
.a16
.i16
    jmp Vm_SourceEntityChange__bad
Vm_SourceMotionProperty_Component:
.a16
.i16
    lda.l VmSourceMutation_Arg
    jsr Vm_SourceEntityArgSlot
    jsr Vm_SourceMutationNumber
    bcc Vm_SourceMotionProperty_Write
    cmp #$FFFF
    beq Vm_SourceMotionProperty_Bad
    bra Vm_SourceMotionProperty_Next
Vm_SourceMotionProperty_Write:
.a16
.i16
    lda.l VmSourceMutation_Name
    cmp #112
    beq Vm_SourceMotionProperty_PhysicalWrite
    jsl SourceSpeedIdentity4086_PreflightProperty
    bcs Vm_SourceMotionProperty_Bad
    jsl SourceSpeedIdentity4086_ApplyProperty
Vm_SourceMotionProperty_PhysicalWrite:
.a16
.i16
    lda.l SourceMotionProperty_Side
    clc
    adc.l VmSourceMutation_Offset
    tax
    lda.l VmSourceMutation_Lo
    sta.l SOURCE_WORLD_SIDES,x
    lda.l VmSourceMutation_Hi
    sta.l SOURCE_WORLD_SIDES+2,x
Vm_SourceMotionProperty_Next:
.a16
.i16
    lda.l VmSourceMutation_Name
    cmp #112
    bne Vm_SourceMotionProperty_Done
    lda.l VmSourceMutation_Arg
    inc a
    sta.l VmSourceMutation_Arg
    lda.l VmCall_Argc
    and #$00FF
    cmp.l VmSourceMutation_Arg
    beq Vm_SourceMotionProperty_Done
    lda.l VmSourceMutation_Offset
    clc
    adc #4
    sta.l VmSourceMutation_Offset
    bra Vm_SourceMotionProperty_Component
Vm_SourceMotionProperty_Done:
.a16
.i16
    jmp Vm_NativeVariantDispatch__null_ok
