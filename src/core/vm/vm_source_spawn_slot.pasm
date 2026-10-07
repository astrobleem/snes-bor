; Source first-slot choice for the exclusive bounded pool. Returns a choice,
; not a constructed entity. Caller must run real Kill when NeedKill=1, then
; cleanup/factors/body/default-init before returning the source entity token.
; A full fixed lease is explicit RESOURCE_LIMIT (status4,C1), never a silent
; dropped spawn. Dynamic C heap growth is not supplied by this capability.
SourceSpawnSlot4086_Ready = $43B880
SourceSpawnSlot4086_Model = $43B882
SourceSpawnSlot4086_Status = $43B884
SourceSpawnSlot4086_Slot = $43B886
SourceSpawnSlot4086_NeedKill = $43B888
SourceSpawnSlot4086_OverrideLo = $43B88A
SourceSpawnSlot4086_OverrideHi = $43B88C
SourceSpawnSlot4086_Count = $43B88E
SourceSpawnSlot4086_Index = $43B890
SourceSpawnSlot4086_View = $43B892
SourceSpawnSlot4086_Life = $43B894
SourceSpawnSlot4086_PriorityLo = $43B896
SourceSpawnSlot4086_PriorityHi = $43B898
SourceSpawnSlot4086_OverrideActive = $43B89A
SourceSpawnSlot4086_OrderMode = $43B89C
SourceSpawnSlot4086_PhysicalSlot = $43B89E
SourceSpawnSlot4086_Seen = $43B8A0 ; 16-byte complete-permutation bitmap
SourceSpawnSlot4086_Mask = $43B8B0
SourceSpawnSlot4086_End = $43B8B2
SourceSpawnSlot4086_Select:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceSpawnSlot4086_Ready
 cmp #$B5A1
 beq SourceSpawnSlot4086_Guard_1
 jmp SourceSpawnSlot4086_Bad
SourceSpawnSlot4086_Guard_1:
.a16
.i16
 lda.l SourceSpawnSlot4086_Status
 cmp #3
 bne SourceSpawnSlot4086_Guard_2
 jmp SourceSpawnSlot4086_Bad
SourceSpawnSlot4086_Guard_2:
.a16
.i16
 cmp #4
 bne SourceSpawnSlot4086_Guard_3
 jmp SourceSpawnSlot4086_Bad
SourceSpawnSlot4086_Guard_3:
.a16
.i16
 lda #$FFFF
 sta.l SourceSpawnSlot4086_Slot
 lda #0
 sta.l SourceSpawnSlot4086_NeedKill
 lda.l SourceSpawnSlot4086_Model
 cmp #$FFFF
 bne SourceSpawnSlot4086_Guard_4
 jmp SourceSpawnSlot4086_Good
SourceSpawnSlot4086_Guard_4:
.a16
.i16
 sta.l SourceLifecycle4086_Model
 lda #0
 sta.l SourceLifecycle4086_Slot
 lda #1
 sta.l SourceLifecycle4086_Reset
 jsl SourceLifecycle4086_Preflight
 bcc SourceSpawnSlot4086_Guard_5
 jmp SourceSpawnSlot4086_Bad
SourceSpawnSlot4086_Guard_5:
.a16
.i16
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 beq SourceSpawnSlot4086_Guard_6
 jmp SourceSpawnSlot4086_Bad
SourceSpawnSlot4086_Guard_6:
.a16
.i16
 lda.l SourceLifecycle4086_Models
 cmp.l VmSourceWorld_TemplateCount
 beq SourceSpawnSlot4086_Guard_7
 jmp SourceSpawnSlot4086_Bad
SourceSpawnSlot4086_Guard_7:
.a16
.i16
 jsr SourceSpawnSlot4086_ValidateOrder
 bcc SourceSpawnSlot4086_OrderValid
 jmp SourceSpawnSlot4086_Bad
SourceSpawnSlot4086_OrderValid:
.a16
.i16
 lda.l SourceLifecycle4086_Row
 clc
 adc #16
 tax
 ; Same immutable current-model priority lease used by constructor scalars.
 phb
 sep #$20
.a8
 lda.l SourceLifecycle4086_Bank
 pha
 plb
 rep #$20
.a16
 lda.w $0000,x
 sta.l SourceSpawnSlot4086_PriorityLo
 lda.w $0002,x
 sta.l SourceSpawnSlot4086_PriorityHi
 plb
 lda #0
 sta.l SourceSpawnSlot4086_Count
 sta.l SourceSpawnSlot4086_Index
 sta.l SourceSpawnSlot4086_View
 sta.l SourceSpawnSlot4086_Life
SourceSpawnSlot4086_CountLoop:
.a16
.i16
 lda.l SourceSpawnSlot4086_View
 tax
 txa
 clc
 adc #$4000
 cmp.l $414000,x
 beq SourceSpawnSlot4086_Guard_8
 jmp SourceSpawnSlot4086_Bad
SourceSpawnSlot4086_Guard_8:
.a16
.i16
 lda.l $414002,x
 cmp #$41
 beq SourceSpawnSlot4086_Guard_9
 jmp SourceSpawnSlot4086_Bad
SourceSpawnSlot4086_Guard_9:
.a16
.i16
 lda.l $414006,x
 beq SourceSpawnSlot4086_Guard_10
 jmp SourceSpawnSlot4086_Bad
SourceSpawnSlot4086_Guard_10:
.a16
.i16
 lda.l $414004,x
 cmp #2
 bcc SourceSpawnSlot4086_Guard_11
 jmp SourceSpawnSlot4086_Bad
SourceSpawnSlot4086_Guard_11:
.a16
.i16
 clc
 adc.l SourceSpawnSlot4086_Count
 sta.l SourceSpawnSlot4086_Count
 jsr SourceSpawnSlot4086_Next
 lda.l SourceSpawnSlot4086_Index
 cmp.l VmSourceWorld_Count
 bcs SourceSpawnSlot4086_Guard_12
 jmp SourceSpawnSlot4086_CountLoop
SourceSpawnSlot4086_Guard_12:
.a16
.i16
 lda.l $43FD82
 beq SourceSpawnSlot4086_Guard_13
 jmp SourceSpawnSlot4086_Bad
SourceSpawnSlot4086_Guard_13:
.a16
.i16
 lda.l SourceSpawnSlot4086_Count
 cmp.l $43FD80
 beq SourceSpawnSlot4086_Guard_14
 jmp SourceSpawnSlot4086_Bad
SourceSpawnSlot4086_Guard_14:
.a16
.i16
 cmp.l VmSourceWorld_Count
 bne SourceSpawnSlot4086_Guard_15
 jmp SourceSpawnSlot4086_Limit
SourceSpawnSlot4086_Guard_15:
.a16
.i16
 ; int32 count>=spawnoverride, including negative override values.
 lda #0
 sta.l SourceSpawnSlot4086_OverrideActive
 lda.l SourceSpawnSlot4086_OverrideHi
 bpl SourceSpawnSlot4086_Guard_16
 jmp SourceSpawnSlot4086_EnableOverride
SourceSpawnSlot4086_Guard_16:
.a16
.i16
 beq SourceSpawnSlot4086_Guard_17
 jmp SourceSpawnSlot4086_ScanStart
SourceSpawnSlot4086_Guard_17:
.a16
.i16
 lda.l SourceSpawnSlot4086_Count
 cmp.l SourceSpawnSlot4086_OverrideLo
 bcs SourceSpawnSlot4086_Guard_18
 jmp SourceSpawnSlot4086_ScanStart
SourceSpawnSlot4086_Guard_18:
.a16
.i16
SourceSpawnSlot4086_EnableOverride:
.a16
.i16
 lda #1
 sta.l SourceSpawnSlot4086_OverrideActive
SourceSpawnSlot4086_ScanStart:
.a16
.i16
 lda #0
 sta.l SourceSpawnSlot4086_Index
 sta.l SourceSpawnSlot4086_View
 sta.l SourceSpawnSlot4086_Life
SourceSpawnSlot4086_Scan:
.a16
.i16
 jsr SourceSpawnSlot4086_ReadOrderedSlot
 lda.l SourceSpawnSlot4086_View
 tax
 lda.l $414004,x
 bne SourceSpawnSlot4086_Guard_19
 jmp SourceSpawnSlot4086_Free
SourceSpawnSlot4086_Guard_19:
.a16
.i16
 lda.l SourceSpawnSlot4086_OverrideActive
 bne SourceSpawnSlot4086_Guard_20
 jmp SourceSpawnSlot4086_ScanNext
SourceSpawnSlot4086_Guard_20:
.a16
.i16
 lda.l SourceSpawnSlot4086_Life
 tax
 lda.l $43904A,x
 cmp #$B4FB
 beq SourceSpawnSlot4086_Guard_21
 jmp SourceSpawnSlot4086_Bad
SourceSpawnSlot4086_Guard_21:
.a16
.i16
 lda.l $439048,x
 cmp.l SourceLifecycle4086_Models
 bcc SourceSpawnSlot4086_Guard_22
 jmp SourceSpawnSlot4086_Bad
SourceSpawnSlot4086_Guard_22:
.a16
.i16
 lda.l $43903E,x
 bmi SourceSpawnSlot4086_Guard_23
 jmp SourceSpawnSlot4086_ScanNext
SourceSpawnSlot4086_Guard_23:
.a16
.i16
 ; Existing priority is negative. Positive current-model priority is always
 ; >= it. When both are negative compare high words, then unsigned low words.
 lda.l SourceSpawnSlot4086_PriorityHi
 bmi SourceSpawnSlot4086_Guard_24
 jmp SourceSpawnSlot4086_Override
SourceSpawnSlot4086_Guard_24:
.a16
.i16
 lda.l $43903E,x
 cmp.l SourceSpawnSlot4086_PriorityHi
 bcs SourceSpawnSlot4086_Guard_25
 jmp SourceSpawnSlot4086_Override
SourceSpawnSlot4086_Guard_25:
.a16
.i16
 beq SourceSpawnSlot4086_Guard_26
 jmp SourceSpawnSlot4086_ScanNext
SourceSpawnSlot4086_Guard_26:
.a16
.i16
 lda.l $43903C,x
 cmp.l SourceSpawnSlot4086_PriorityLo
 bcs SourceSpawnSlot4086_Guard_27
 jmp SourceSpawnSlot4086_Override
SourceSpawnSlot4086_Guard_27:
.a16
.i16
 beq SourceSpawnSlot4086_Guard_28
 jmp SourceSpawnSlot4086_ScanNext
SourceSpawnSlot4086_Guard_28:
.a16
.i16
SourceSpawnSlot4086_Override:
.a16
.i16
 lda #1
 sta.l SourceSpawnSlot4086_NeedKill
SourceSpawnSlot4086_Free:
.a16
.i16
 lda.l SourceSpawnSlot4086_PhysicalSlot
 sta.l SourceSpawnSlot4086_Slot
 jmp SourceSpawnSlot4086_Good
SourceSpawnSlot4086_ScanNext:
.a16
.i16
 jsr SourceSpawnSlot4086_Next
 lda.l SourceSpawnSlot4086_Index
 cmp.l VmSourceWorld_Count
 bcs SourceSpawnSlot4086_Guard_29
 jmp SourceSpawnSlot4086_Scan
SourceSpawnSlot4086_Guard_29:
.a16
.i16
 jmp SourceSpawnSlot4086_Bad
SourceSpawnSlot4086_Limit:
.a16
.i16
 lda #4
 sta.l SourceSpawnSlot4086_Status
 ply
 plx
 plp
 sec
 rtl
SourceSpawnSlot4086_Good:
.a16
.i16
 lda #2
 sta.l SourceSpawnSlot4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceSpawnSlot4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceSpawnSlot4086_Status
 ply
 plx
 plp
 sec
 rtl
SourceSpawnSlot4086_Next:
.a16
.i16
 lda.l SourceSpawnSlot4086_Index
 inc a
 sta.l SourceSpawnSlot4086_Index
 lda.l SourceSpawnSlot4086_View
 clc
 adc #80
 sta.l SourceSpawnSlot4086_View
 lda.l SourceSpawnSlot4086_Life
 clc
 adc #80
 sta.l SourceSpawnSlot4086_Life
 rts

; Disabled pointer-order lease is a separate isolated identity-order fixture
; capability. A live world tick requires the real shared B4D3 permutation.
SourceSpawnSlot4086_ValidateOrder:
.a16
.i16
 lda #0
 sta.l SourceSpawnSlot4086_OrderMode
 lda.l SourceTarget4086_OrderReady
 bne SourceSpawnSlot4086_OrderPresent
 lda.l SourceWorldTick4086_Ready
 beq SourceSpawnSlot4086_OrderGood
 jmp SourceSpawnSlot4086_OrderBad
SourceSpawnSlot4086_OrderPresent:
.a16
.i16
 cmp #$B4D3
 beq SourceSpawnSlot4086_OrderGranted
 jmp SourceSpawnSlot4086_OrderBad
SourceSpawnSlot4086_OrderGranted:
.a16
.i16
 lda #1
 sta.l SourceSpawnSlot4086_OrderMode
 ldx #0
 lda #0
SourceSpawnSlot4086_ClearSeen:
.a16
.i16
 sta.l SourceSpawnSlot4086_Seen,x
 inx
 inx
 cpx #16
 bcc SourceSpawnSlot4086_ClearSeen
 sta.l SourceSpawnSlot4086_Index
SourceSpawnSlot4086_OrderLoop:
.a16
.i16
 lda.l SourceSpawnSlot4086_Index
 asl a
 tax
 lda.l SOURCE_TARGET_ORDER,x
 cmp.l VmSourceWorld_Count
 bcc SourceSpawnSlot4086_OrderRange
 jmp SourceSpawnSlot4086_OrderBad
SourceSpawnSlot4086_OrderRange:
.a16
.i16
 sta.l SourceSpawnSlot4086_PhysicalSlot
 and #15
 asl a
 tax
 lda.l SourceSpawnSlot4086_BitMask,x
 sta.l SourceSpawnSlot4086_Mask
 lda.l SourceSpawnSlot4086_PhysicalSlot
 lsr a
 lsr a
 lsr a
 lsr a
 asl a
 tax
 lda.l SourceSpawnSlot4086_Seen,x
 and.l SourceSpawnSlot4086_Mask
 beq SourceSpawnSlot4086_OrderUnique
 jmp SourceSpawnSlot4086_OrderBad
SourceSpawnSlot4086_OrderUnique:
.a16
.i16
 lda.l SourceSpawnSlot4086_Seen,x
 ora.l SourceSpawnSlot4086_Mask
 sta.l SourceSpawnSlot4086_Seen,x
 lda.l SourceSpawnSlot4086_Index
 inc a
 sta.l SourceSpawnSlot4086_Index
 cmp.l VmSourceWorld_Count
 bcc SourceSpawnSlot4086_OrderLoop
SourceSpawnSlot4086_OrderGood:
.a16
.i16
 clc
 rts
SourceSpawnSlot4086_OrderBad:
.a16
.i16
 sec
 rts

; Index is a pointer-order index, while outputs/offsets name physical slots.
SourceSpawnSlot4086_ReadOrderedSlot:
.a16
.i16
 ; X is caller scratch and restored by Select.
 lda.l SourceSpawnSlot4086_OrderMode
 beq SourceSpawnSlot4086_IdentitySlot
 lda.l SourceSpawnSlot4086_Index
 asl a
 tax
 lda.l SOURCE_TARGET_ORDER,x
 bra SourceSpawnSlot4086_Physical
SourceSpawnSlot4086_IdentitySlot:
.a16
.i16
 lda.l SourceSpawnSlot4086_Index
SourceSpawnSlot4086_Physical:
.a16
.i16
 sta.l SourceSpawnSlot4086_PhysicalSlot
 asl a
 asl a
 asl a
 asl a
 sta.l SourceSpawnSlot4086_View
 asl a
 asl a
 clc
 adc.l SourceSpawnSlot4086_View
 sta.l SourceSpawnSlot4086_View
 sta.l SourceSpawnSlot4086_Life
 rts
SourceSpawnSlot4086_BitMask:
 .dw $0001,$0002,$0004,$0008,$0010,$0020,$0040,$0080
 .dw $0100,$0200,$0400,$0800,$1000,$2000,$4000,$8000
