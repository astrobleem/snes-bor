; One-argument findtarget: pinned normal_find_target(anim=-1,detect=0).
; Exclusive canonical pool plus current-tick target metadata lease required.
; Metadata BW $41E800..$41F1FF is disjoint from views, sidecars and variables.
; No AI, range animation query or model-name policy. Foreground/non-reentrant.
SourceTarget4086_Ready = $7FFA88
SourceTarget4086_Count = $7FFA8A
SourceTarget4086_TimeLo = $7FFA8C
SourceTarget4086_TimeHi = $7FFA8E
SourceTarget4086_SelfXLo = $7FFA90
SourceTarget4086_SelfXHi = $7FFA92
SourceTarget4086_SelfZLo = $7FFA94
SourceTarget4086_SelfZHi = $7FFA96
SourceTarget4086_Hostile = $7FFA98
SourceTarget4086_Direction = $7FFA9A
SourceTarget4086_DetectLo = $7FFA9C
SourceTarget4086_DetectHi = $7FFA9E
SourceTarget4086_Index = $7FFAA0
SourceTarget4086_Record = $7FFAA2
SourceTarget4086_Meta = $7FFAA4
SourceTarget4086_Selected = $7FFAA6
SourceTarget4086_SelectedRecord = $7FFAA8
SourceTarget4086_SelectedMeta = $7FFAAA
SourceTarget4086_DistanceLo = $7FFAAC
SourceTarget4086_DistanceHi = $7FFAAE
SourceTarget4086_BestLo = $7FFAB0
SourceTarget4086_BestHi = $7FFAB2
SourceTarget4086_LeftLo = $7FFAB4
SourceTarget4086_LeftHi = $7FFAB6
SourceTarget4086_DiffLo = $7FFAB8
SourceTarget4086_DiffHi = $7FFABA
SourceTarget4086_Front = $7FFABC
SourceTarget4086_Scratch = $7FFABE
SourceTarget4086_RightLo = $7FFAC0
SourceTarget4086_RightHi = $7FFAC2
SourceTarget4086_Order = $7FFAC4
SourceTarget4086_SelfIndex = $7FFAC6
SourceTarget4086_OrderReady = $7FFAC8
SourceTarget4086_CurrentSlot = $7FFACA
SourceTarget4086_ScanCount = $7FFACC
SourceTarget4086_Seen = $7FFAD0 ; sixteen-byte permutation bitmap
SOURCE_TARGET_META = $41E800
SOURCE_TARGET_ORDER = $41F200

Vm_SourceFindTarget:
.a16
.i16
    lda.l VmNativeVariant_ContextValid
    cmp #$B48F
    bne Vm_SourceFindTarget_Bad
    lda.l VmCall_Argc
    and #$00FF
    cmp #1
    bne Vm_SourceFindTarget_Bad
    jsr Vm_SourceEntityLocate
    bcs Vm_SourceFindTarget_Bad
    cmp #0
    bne Vm_SourceFindTarget_Lease
    jmp Vm_NativeVariantDispatch__null_ok
Vm_SourceFindTarget_Lease:
.a16
.i16
    lda.l VmSourceWorld_Ready
    cmp #$B4A3
    bne Vm_SourceFindTarget_Bad
    lda.l SourceTarget4086_Ready
    cmp #$B4D2
    bne Vm_SourceFindTarget_Bad
    lda.l SourceTarget4086_Count
    beq Vm_SourceFindTarget_Bad
    cmp #129
    bcs Vm_SourceFindTarget_Bad
    cmp.l VmSourceWorld_Count
    bne Vm_SourceFindTarget_Bad
    cmp.l VmSourceEntity_Count
    bne Vm_SourceFindTarget_Bad
    lda.l VmSourceEntity_Base
    cmp #$4000
    bne Vm_SourceFindTarget_Bad
    lda.l VmSourceEntity_Bank
    and #$00FF
    cmp #$41
    bne Vm_SourceFindTarget_Bad
    lda.l SourceTarget4086_TimeLo
    cmp.l VmSourceWorld_Time
    bne Vm_SourceFindTarget_Bad
    lda.l SourceTarget4086_TimeHi
    cmp.l VmSourceWorld_Time+2
    bne Vm_SourceFindTarget_Bad
    bra Vm_SourceFindTarget_Self
Vm_SourceFindTarget_Bad:
.a16
.i16
    lda #VMERR_BAD_NATIVE
    sec
    rtl
Vm_SourceFindTarget_Self:
.a16
.i16
    lda.l VmSourceWorld_PoolBase
    cmp #$4000
    bne Vm_SourceFindTarget_Bad
    lda.l SourceClock4086_Ready
    cmp #$B4C5
    bne Vm_SourceFindTarget_Current
    lda.l SourceClock4086_TimeLo
    cmp.l VmSourceWorld_Time
    bne Vm_SourceFindTarget_Bad
    lda.l SourceClock4086_TimeHi
    cmp.l VmSourceWorld_Time+2
    bne Vm_SourceFindTarget_Bad
Vm_SourceFindTarget_Current:
.a16
.i16
    lda.l SourceTarget4086_OrderReady
    cmp #$B4D3
    beq Vm_SourceFindTarget_OrderGranted
    jmp Vm_SourceFindTarget_Bad
Vm_SourceFindTarget_OrderGranted:
.a16
.i16
    lda.l SourceTarget4086_ScanCount
    cmp.l SourceTarget4086_Count
    bcc Vm_SourceFindTarget_OrderValidate
    beq Vm_SourceFindTarget_OrderValidate
    jmp Vm_SourceFindTarget_Bad
Vm_SourceFindTarget_OrderValidate:
.a16
.i16
    jsr Vm_SourceTargetOrderValidate
    bcc Vm_SourceFindTarget_OrderValid
    jmp Vm_SourceFindTarget_Bad
Vm_SourceFindTarget_OrderValid:
.a16
.i16
    lda.l VmSourceEntity_Index
    sta.l SourceTarget4086_SelfIndex
    asl a
    asl a
    sta.l SourceTarget4086_Scratch
    asl a
    asl a
    clc
    adc.l SourceTarget4086_Scratch
    tax
    lda.l SOURCE_TARGET_META+10,x
    beq Vm_SourceFindTarget_CurrentMeta
    jmp Vm_SourceFindTarget_Bad
Vm_SourceFindTarget_CurrentMeta:
.a16
.i16
    lda.l SOURCE_TARGET_META+2,x
    sta.l SourceTarget4086_Hostile
    lda.l SOURCE_TARGET_META+12,x
    sta.l SourceTarget4086_DetectLo
    lda.l SOURCE_TARGET_META+14,x
    sta.l SourceTarget4086_DetectHi
    ldy #52
    jsr Vm_SourceEntityRead16
    sta.l SourceTarget4086_SelfXLo
    ldy #54
    jsr Vm_SourceEntityRead16
    sta.l SourceTarget4086_SelfXHi
    ldy #60
    jsr Vm_SourceEntityRead16
    sta.l SourceTarget4086_SelfZLo
    ldy #62
    jsr Vm_SourceEntityRead16
    sta.l SourceTarget4086_SelfZHi
    lda #0
    sta.l SourceTarget4086_Direction
    ldy #30
    jsr Vm_SourceEntityRead16
    bne Vm_SourceFindTarget_Begin
    ldy #28
    jsr Vm_SourceEntityRead16
    cmp #1
    bne Vm_SourceFindTarget_Begin
    sta.l SourceTarget4086_Direction
Vm_SourceFindTarget_Begin:
.a16
.i16
    lda #0
    sta.l SourceTarget4086_Index
    sta.l SourceTarget4086_Record
    sta.l SourceTarget4086_Meta
    lda #$FFFF
    sta.l SourceTarget4086_Selected
Vm_SourceFindTarget_Scan:
.a16
.i16
    lda.l SourceTarget4086_Index
    cmp.l SourceTarget4086_ScanCount
    bcc Vm_SourceFindTarget_OrderSlot
    jmp Vm_SourceFindTarget_Finish
Vm_SourceFindTarget_OrderSlot:
.a16
.i16
    asl a
    tax
    lda.l SOURCE_TARGET_ORDER,x
    sta.l SourceTarget4086_CurrentSlot
    cmp.l SourceTarget4086_SelfIndex
    bne Vm_SourceFindTarget_Candidate
    jmp Vm_SourceFindTarget_Next
Vm_SourceFindTarget_Candidate:
.a16
.i16
    lda.l SourceTarget4086_CurrentSlot
    asl a
    asl a
    sta.l SourceTarget4086_Scratch
    asl a
    asl a
    clc
    adc.l SourceTarget4086_Scratch
    sta.l SourceTarget4086_Meta
    lda.l SourceTarget4086_CurrentSlot
    asl a
    asl a
    asl a
    asl a
    sta.l SourceTarget4086_Scratch
    asl a
    asl a
    clc
    adc.l SourceTarget4086_Scratch
    sta.l SourceTarget4086_Record
    lda.l SourceTarget4086_Record
    tax
    lda.l VmSourceEntity_Ready
    cmp #$B5EF
    beq Vm_SourceFindTarget_SourceAlive
    lda.l SOURCE_WORLD_POOL+4,x
    cmp #1
    beq Vm_SourceFindTarget_Alive
    jmp Vm_SourceFindTarget_Next
Vm_SourceFindTarget_SourceAlive:
.a16
.i16
    lda.l SOURCE_WORLD_POOL+4,x
    ora.l SOURCE_WORLD_POOL+6,x
    bne Vm_SourceFindTarget_Alive
    jmp Vm_SourceFindTarget_Next
Vm_SourceFindTarget_Alive:
.a16
.i16
    lda.l SOURCE_WORLD_POOL+48,x
    cmp #BOR_VT_DECIMAL
    bne Vm_SourceFindTarget_Corrupt
    lda.l SOURCE_WORLD_POOL+50,x
    bne Vm_SourceFindTarget_Corrupt
    lda.l SOURCE_WORLD_POOL+56,x
    cmp #BOR_VT_DECIMAL
    bne Vm_SourceFindTarget_Corrupt
    lda.l SOURCE_WORLD_POOL+58,x
    bne Vm_SourceFindTarget_Corrupt
    lda.l SourceTarget4086_Meta
    tax
    lda.l SOURCE_TARGET_META+10,x
    bne Vm_SourceFindTarget_Corrupt
    lda.l SOURCE_TARGET_META+4,x
    beq Vm_SourceFindTarget_Hostile
    jmp Vm_SourceFindTarget_Next
Vm_SourceFindTarget_Corrupt:
.a16
.i16
    jmp Vm_SourceFindTarget_Bad
Vm_SourceFindTarget_Hostile:
.a16
.i16
    lda.l SOURCE_TARGET_META,x
    and.l SourceTarget4086_Hostile
    bne Vm_SourceFindTarget_Stealth
    jmp Vm_SourceFindTarget_Next
Vm_SourceFindTarget_Stealth:
.a16
.i16
    lda.l SourceTarget4086_DetectHi
    eor #$8000
    sta.l SourceTarget4086_Scratch
    lda.l SOURCE_TARGET_META+18,x
    eor #$8000
    cmp.l SourceTarget4086_Scratch
    bcc Vm_SourceFindTarget_Distance
    beq Vm_SourceFindTarget_StealthLow
    jmp Vm_SourceFindTarget_Next
Vm_SourceFindTarget_StealthLow:
.a16
.i16
    lda.l SOURCE_TARGET_META+16,x
    cmp.l SourceTarget4086_DetectLo
    bcc Vm_SourceFindTarget_Distance
    beq Vm_SourceFindTarget_Distance
    jmp Vm_SourceFindTarget_Next
Vm_SourceFindTarget_Distance:
.a16
.i16
    lda.l SourceTarget4086_SelfXLo
    sta.l SourceTarget4086_LeftLo
    lda.l SourceTarget4086_SelfXHi
    sta.l SourceTarget4086_LeftHi
    lda.l SourceTarget4086_Record
    tax
    lda.l SOURCE_WORLD_POOL+52,x
    sta.l SourceTarget4086_RightLo
    lda.l SOURCE_WORLD_POOL+54,x
    sta.l SourceTarget4086_RightHi
    jsr Vm_SourceTargetDifference
    lda.l SourceTarget4086_Order
    sta.l SourceTarget4086_Front
    lda.l SourceTarget4086_DiffLo
    sta.l SourceTarget4086_DistanceLo
    lda.l SourceTarget4086_DiffHi
    sta.l SourceTarget4086_DistanceHi
    lda.l SourceTarget4086_SelfZLo
    sta.l SourceTarget4086_LeftLo
    lda.l SourceTarget4086_SelfZHi
    sta.l SourceTarget4086_LeftHi
    lda.l SourceTarget4086_Record
    tax
    lda.l SOURCE_WORLD_POOL+60,x
    sta.l SourceTarget4086_RightLo
    lda.l SOURCE_WORLD_POOL+62,x
    sta.l SourceTarget4086_RightHi
    jsr Vm_SourceTargetDifference
    lda.l SourceTarget4086_DiffLo
    clc
    adc.l SourceTarget4086_DistanceLo
    sta.l SourceTarget4086_DistanceLo
    lda.l SourceTarget4086_DiffHi
    adc.l SourceTarget4086_DistanceHi
    sta.l SourceTarget4086_DistanceHi
    bcc Vm_SourceFindTarget_Range
    jmp Vm_SourceFindTarget_Next
Vm_SourceFindTarget_Range:
.a16
.i16
    cmp #9999
    bcc Vm_SourceFindTarget_Preference
    beq Vm_SourceFindTarget_RangeLow
    jmp Vm_SourceFindTarget_Next
Vm_SourceFindTarget_RangeLow:
.a16
.i16
    lda.l SourceTarget4086_DistanceLo
    beq Vm_SourceFindTarget_Preference
    jmp Vm_SourceFindTarget_Next
Vm_SourceFindTarget_Preference:
.a16
.i16
    lda.l SourceTarget4086_Selected
    cmp #$FFFF
    beq Vm_SourceFindTarget_Take
    lda.l SourceTarget4086_SelectedMeta
    tax
    lda.l SOURCE_TARGET_META+8,x
    beq Vm_SourceFindTarget_Take
    lda.l SOURCE_TARGET_META+6,x
    cmp #1
    beq Vm_SourceFindTarget_Take
    lda.l SourceTarget4086_Front
    cmp.l SourceTarget4086_Direction
    bne Vm_SourceFindTarget_Next
    lda.l SourceTarget4086_DistanceHi
    cmp.l SourceTarget4086_BestHi
    bcc Vm_SourceFindTarget_Take
    bne Vm_SourceFindTarget_Next
    lda.l SourceTarget4086_DistanceLo
    cmp.l SourceTarget4086_BestLo
    bcs Vm_SourceFindTarget_Next
Vm_SourceFindTarget_Take:
.a16
.i16
    lda.l SourceTarget4086_CurrentSlot
    sta.l SourceTarget4086_Selected
    lda.l SourceTarget4086_Record
    sta.l SourceTarget4086_SelectedRecord
    lda.l SourceTarget4086_Meta
    sta.l SourceTarget4086_SelectedMeta
    lda.l SourceTarget4086_DistanceLo
    sta.l SourceTarget4086_BestLo
    lda.l SourceTarget4086_DistanceHi
    sta.l SourceTarget4086_BestHi
Vm_SourceFindTarget_Next:
.a16
.i16
    lda.l SourceTarget4086_Index
    inc a
    sta.l SourceTarget4086_Index
    cmp.l SourceTarget4086_ScanCount
    bcs Vm_SourceFindTarget_Finish
    jmp Vm_SourceFindTarget_Scan
Vm_SourceFindTarget_Finish:
.a16
.i16
    lda.l SourceTarget4086_Selected
    cmp #$FFFF
    bne Vm_SourceFindTarget_Result
    jmp Vm_NativeVariantDispatch__null_ok
Vm_SourceFindTarget_Result:
.a16
.i16
    lda.l SourceTarget4086_SelectedRecord
    tax
    lda.l SOURCE_WORLD_POOL,x
    sta.l VmNativeVariant_Result+4
    lda.l SOURCE_WORLD_POOL+2,x
    sta.l VmNativeVariant_Result+6
    lda #BOR_VT_PTR
    sta.l VmNativeVariant_Result
    lda #0
    sta.l VmNativeVariant_Result+2
    clc
    rtl

; Exact unsigned magnitude of two signed Q16.16 operands, including opposite
; signed extremes. Do not abs() a wrapped signed subtraction. Order=left<right.
Vm_SourceTargetDifference:
.a16
.i16
    lda.l SourceTarget4086_RightHi
    eor #$8000
    sta.l SourceTarget4086_Scratch
    lda.l SourceTarget4086_LeftHi
    eor #$8000
    cmp.l SourceTarget4086_Scratch
    bcc Vm_SourceTargetDifference_Right
    bne Vm_SourceTargetDifference_Left
    lda.l SourceTarget4086_LeftLo
    cmp.l SourceTarget4086_RightLo
    bcc Vm_SourceTargetDifference_Right
Vm_SourceTargetDifference_Left:
.a16
.i16
    lda #0
    sta.l SourceTarget4086_Order
    lda.l SourceTarget4086_LeftLo
    sec
    sbc.l SourceTarget4086_RightLo
    sta.l SourceTarget4086_DiffLo
    lda.l SourceTarget4086_LeftHi
    sbc.l SourceTarget4086_RightHi
    sta.l SourceTarget4086_DiffHi
    rts
Vm_SourceTargetDifference_Right:
.a16
.i16
    lda #1
    sta.l SourceTarget4086_Order
    lda.l SourceTarget4086_RightLo
    sec
    sbc.l SourceTarget4086_LeftLo
    sta.l SourceTarget4086_DiffLo
    lda.l SourceTarget4086_RightHi
    sbc.l SourceTarget4086_LeftHi
    sta.l SourceTarget4086_DiffHi
    rts

; Validate the complete pointer-order permutation before querying its active
; prefix. A repeated slot is an admission fault, not a duplicate entity visit.
Vm_SourceTargetOrderValidate:
.a16
.i16
    ldx #0
    lda #0
Vm_SourceTargetOrderValidate_Clear:
.a16
.i16
    sta.l SourceTarget4086_Seen,x
    inx
    inx
    cpx #16
    bcc Vm_SourceTargetOrderValidate_Clear
    lda #0
    sta.l SourceTarget4086_Index
Vm_SourceTargetOrderValidate_Loop:
.a16
.i16
    lda.l SourceTarget4086_Index
    asl a
    tax
    lda.l SOURCE_TARGET_ORDER,x
    cmp.l SourceTarget4086_Count
    bcs Vm_SourceTargetOrderValidate_Bad
    sta.l SourceTarget4086_CurrentSlot
    and #15
    asl a
    tax
    lda.l Vm_SourceTargetBitMask,x
    sta.l SourceTarget4086_Scratch
    lda.l SourceTarget4086_CurrentSlot
    lsr a
    lsr a
    lsr a
    lsr a
    asl a
    tax
    lda.l SourceTarget4086_Seen,x
    and.l SourceTarget4086_Scratch
    bne Vm_SourceTargetOrderValidate_Bad
    lda.l SourceTarget4086_Seen,x
    ora.l SourceTarget4086_Scratch
    sta.l SourceTarget4086_Seen,x
    lda.l SourceTarget4086_Index
    inc a
    sta.l SourceTarget4086_Index
    cmp.l SourceTarget4086_Count
    bcc Vm_SourceTargetOrderValidate_Loop
    clc
    rts
Vm_SourceTargetOrderValidate_Bad:
.a16
.i16
    sec
    rts
Vm_SourceTargetBitMask:
    .dw $0001,$0002,$0004,$0008,$0010,$0020,$0040,$0080
    .dw $0100,$0200,$0400,$0800,$1000,$2000,$4000,$8000
