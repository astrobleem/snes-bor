; Build current-tick target metadata from actual source core/life/modeldata and
; the live collision frame cursor. No authored actor-name or stale snapshot.
; Only publish B4D2 after every live row succeeds. Inactive rows are neutral.
; Hostile32 projects to low16 only after all live TYPE32 values fit16, making
; (type & hostile) exact. Invincible canonicalizes the source test ==1.
SourceTargetMeta4086_Ready = $43BDB0
SourceTargetMeta4086_Status = $43BDB2 ; 1 busy,2 published,3 fault
SourceTargetMeta4086_Slot = $43BDB4
SourceTargetMeta4086_View = $43BDB6
SourceTargetMeta4086_Core = $43BDB8
SourceTargetMeta4086_Life = $43BDBA
SourceTargetMeta4086_AI = $43BDBC
SourceTargetMeta4086_Meta = $43BDBE
SourceTargetMeta4086_Value = $43BDC0
SourceTargetMeta4086_End = $43BDC2
SourceTargetMeta4086_Build:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceTargetMeta4086_Ready
 cmp #$B5F2
 beq SourceTargetMeta4086_Owned
 jmp SourceTargetMeta4086_EarlyBad
SourceTargetMeta4086_Owned:
.a16
.i16
 lda #0
 sta.l SourceTarget4086_Ready
 lda.l SourceTargetMeta4086_Status
 beq SourceTargetMeta4086_Idle
 cmp #2
 beq SourceTargetMeta4086_Idle
 jmp SourceTargetMeta4086_Bad
SourceTargetMeta4086_Idle:
.a16
.i16
 lda #1
 sta.l SourceTargetMeta4086_Status
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceTargetMeta4086_G0
 jmp SourceTargetMeta4086_Bad
SourceTargetMeta4086_G0:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourceTargetMeta4086_G1
 jmp SourceTargetMeta4086_Bad
SourceTargetMeta4086_G1:
.a16
.i16
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 beq SourceTargetMeta4086_G2
 jmp SourceTargetMeta4086_Bad
SourceTargetMeta4086_G2:
.a16
.i16
 lda.l VmSourceWorld_Count
 bne SourceTargetMeta4086_G3
 jmp SourceTargetMeta4086_Bad
SourceTargetMeta4086_G3:
.a16
.i16
 cmp #129
 bcc SourceTargetMeta4086_G4
 jmp SourceTargetMeta4086_Bad
SourceTargetMeta4086_G4:
.a16
.i16
 cmp.l SourceModelEntityCopy4086_Entities
 beq SourceTargetMeta4086_G5
 jmp SourceTargetMeta4086_Bad
SourceTargetMeta4086_G5:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Ready
 cmp #$B4EB
 beq SourceTargetMeta4086_G6
 jmp SourceTargetMeta4086_Bad
SourceTargetMeta4086_G6:
.a16
.i16
 lda.l SourceModelAttackPolicy4086_Ready
 cmp #$B5F0
 beq SourceTargetMeta4086_G7
 jmp SourceTargetMeta4086_Bad
SourceTargetMeta4086_G7:
.a16
.i16
 lda.l SourceModelAttackPolicy4086_Models
 bne SourceTargetMeta4086_G8
 jmp SourceTargetMeta4086_Bad
SourceTargetMeta4086_G8:
.a16
.i16
 cmp #17
 bcc SourceTargetMeta4086_G9
 jmp SourceTargetMeta4086_Bad
SourceTargetMeta4086_G9:
.a16
.i16
 cmp.l SourceModelEntityCopy4086_Models
 beq SourceTargetMeta4086_G10
 jmp SourceTargetMeta4086_Bad
SourceTargetMeta4086_G10:
.a16
.i16
 cmp.l SourceLifecycle4086_Models
 beq SourceTargetMeta4086_G11
 jmp SourceTargetMeta4086_Bad
SourceTargetMeta4086_G11:
.a16
.i16
 lda.l SourceLifecycle4086_Ready
 cmp #$B4FB
 beq SourceTargetMeta4086_G12
 jmp SourceTargetMeta4086_Bad
SourceTargetMeta4086_G12:
.a16
.i16
 lda.l SourceCollisionFrame4086_Ready
 cmp #$B5EE
 beq SourceTargetMeta4086_G13
 jmp SourceTargetMeta4086_Bad
SourceTargetMeta4086_G13:
.a16
.i16
 lda.l SourceTarget4086_OrderReady
 cmp #$B4D3
 beq SourceTargetMeta4086_G14
 jmp SourceTargetMeta4086_Bad
SourceTargetMeta4086_G14:
.a16
.i16
 lda.l VmSourceWorld_Count
 sta.l SourceTarget4086_Count
 sta.l SourceTarget4086_ScanCount
 jsl SourceTarget4086_CheckOrder
 bcc SourceTargetMeta4086_OrderValid
 jmp SourceTargetMeta4086_Bad
SourceTargetMeta4086_OrderValid:
.a16
.i16
 lda.l VmSourceWorld_Time
 sta.l SourceTarget4086_TimeLo
 lda.l VmSourceWorld_Time+2
 sta.l SourceTarget4086_TimeHi
 lda #0
 sta.l SourceTargetMeta4086_Slot
SourceTargetMeta4086_Loop:
.a16
.i16
 ; Stable physical rows are separate from mutable ent_list order.
 lda.l SourceTargetMeta4086_Slot
 asl a
 asl a
 asl a
 asl a
 sta.l SourceTargetMeta4086_Value
 asl a
 asl a
 clc
 adc.l SourceTargetMeta4086_Value
 sta.l SourceTargetMeta4086_Life
 clc
 adc #$4000
 sta.l SourceTargetMeta4086_View
 lda.l SourceTargetMeta4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l SourceTargetMeta4086_Value
 asl a
 clc
 adc.l SourceTargetMeta4086_Value
 sta.l SourceTargetMeta4086_Core
 lda.l SourceTargetMeta4086_Slot
 asl a
 asl a
 asl a
 sta.l SourceTargetMeta4086_Value
 asl a
 clc
 adc.l SourceTargetMeta4086_Value
 sta.l SourceTargetMeta4086_AI
 lda.l SourceTargetMeta4086_Slot
 asl a
 asl a
 sta.l SourceTargetMeta4086_Value
 asl a
 asl a
 clc
 adc.l SourceTargetMeta4086_Value
 sta.l SourceTargetMeta4086_Meta
 lda.l SourceTargetMeta4086_View
 tax
 lda.l $410004,x
 ora.l $410006,x
 bne SourceTargetMeta4086_Alive
 ; No animation dereference for inactive slots, including retired cursors.
 lda.l SourceTargetMeta4086_Meta
 tax
 ldy #10
 lda #0
SourceTargetMeta4086_Neutral:
.a16
.i16
 sta.l SOURCE_TARGET_META,x
 inx
 inx
 dey
 bne SourceTargetMeta4086_Neutral
 jmp SourceTargetMeta4086_Next
SourceTargetMeta4086_Alive:
.a16
.i16
 lda.l SourceTargetMeta4086_View
 cmp.l $410000,x

 beq SourceTargetMeta4086_G15
 jmp SourceTargetMeta4086_Bad
SourceTargetMeta4086_G15:
.a16
.i16
 lda.l $410002,x
 cmp #$0041
 beq SourceTargetMeta4086_G16
 jmp SourceTargetMeta4086_Bad
SourceTargetMeta4086_G16:
.a16
.i16
 lda.l $410000+48,x
 cmp #BOR_VT_DECIMAL
 beq SourceTargetMeta4086_G17
 jmp SourceTargetMeta4086_Bad
SourceTargetMeta4086_G17:
.a16
.i16
 lda.l $410000+50,x
 cmp #0
 beq SourceTargetMeta4086_G18
 jmp SourceTargetMeta4086_Bad
SourceTargetMeta4086_G18:
.a16
.i16
 lda.l $410000+56,x
 cmp #BOR_VT_DECIMAL
 beq SourceTargetMeta4086_G19
 jmp SourceTargetMeta4086_Bad
SourceTargetMeta4086_G19:
.a16
.i16
 lda.l $410000+58,x
 cmp #0
 beq SourceTargetMeta4086_G20
 jmp SourceTargetMeta4086_Bad
SourceTargetMeta4086_G20:
.a16
.i16
 lda.l $410000+24,x
 cmp #BOR_VT_INTEGER
 beq SourceTargetMeta4086_G21
 jmp SourceTargetMeta4086_Bad
SourceTargetMeta4086_G21:
.a16
.i16
 lda.l $410000+26,x
 cmp #0
 beq SourceTargetMeta4086_G22
 jmp SourceTargetMeta4086_Bad
SourceTargetMeta4086_G22:
.a16
.i16
 lda.l SourceTargetMeta4086_Core
 tax
 lda.l $40C04A,x
 beq SourceTargetMeta4086_G23
 jmp SourceTargetMeta4086_Bad
SourceTargetMeta4086_G23:
.a16
.i16
 lda.l SourceTargetMeta4086_Life
 tax
 lda.l $43904A,x
 cmp #$B4FB
 beq SourceTargetMeta4086_G24
 jmp SourceTargetMeta4086_Bad
SourceTargetMeta4086_G24:
.a16
.i16
 lda.l $439048,x
 cmp.l SourceModelAttackPolicy4086_Models

 bcc SourceTargetMeta4086_G25
 jmp SourceTargetMeta4086_Bad
SourceTargetMeta4086_G25:
.a16
.i16
 sta.l SourceTargetMeta4086_Value
 lda.l SourceTargetMeta4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 asl a
 tax
 lda.l $416800,x
 cmp.l SourceTargetMeta4086_Value

 beq SourceTargetMeta4086_G26
 jmp SourceTargetMeta4086_Bad
SourceTargetMeta4086_G26:
.a16
.i16
 lda #0
 sta.l SourceCollisionFrame4086_Status
 lda.l SourceTargetMeta4086_Slot
 jsl SourceCollisionFrame4086_QueryEntity

 bcc SourceTargetMeta4086_G27
 jmp SourceTargetMeta4086_Bad
SourceTargetMeta4086_G27:
.a16
.i16
 lda.l SourceTargetMeta4086_Core
 tax
 lda.l $40C048,x
 ldy #0
 jsr SourceTargetMeta4086_Store
 lda.l SourceTargetMeta4086_Core
 tax
 lda.l $40C028,x
 ldy #2
 jsr SourceTargetMeta4086_Store
 lda.l SourceTargetMeta4086_Life
 tax
 lda.l $439014,x
 ora.l $439016,x
 beq SourceTargetMeta4086_DeadValue
 lda #1
SourceTargetMeta4086_DeadValue:
.a16
.i16
 ldy #4
 jsr SourceTargetMeta4086_Store
 lda.l SourceTargetMeta4086_Life
 tax
 lda.l $439018,x
 cmp #1
 bne SourceTargetMeta4086_NotInvincibleOne
 lda.l $43901A,x
 bne SourceTargetMeta4086_NotInvincibleOne
 lda #1
 bra SourceTargetMeta4086_InvincibleValue
SourceTargetMeta4086_NotInvincibleOne:
.a16
.i16
 lda #0
SourceTargetMeta4086_InvincibleValue:
.a16
.i16
 ldy #6
 jsr SourceTargetMeta4086_Store
 lda.l SourceCollisionFrame4086_Vulnerable
 ldy #8
 jsr SourceTargetMeta4086_Store
 lda #0
 ldy #10
 jsr SourceTargetMeta4086_Store
 lda.l SourceTargetMeta4086_AI
 tax
 lda.l SOURCE_ENTITY_AI_STATE+16,x
 ldy #12
 jsr SourceTargetMeta4086_Store
 lda.l SourceTargetMeta4086_AI
 tax
 lda.l SOURCE_ENTITY_AI_STATE+18,x
 ldy #14
 jsr SourceTargetMeta4086_Store
 lda.l SourceTargetMeta4086_AI
 tax
 lda.l SOURCE_ENTITY_AI_STATE+20,x
 ldy #16
 jsr SourceTargetMeta4086_Store
 lda.l SourceTargetMeta4086_AI
 tax
 lda.l SOURCE_ENTITY_AI_STATE+22,x
 ldy #18
 jsr SourceTargetMeta4086_Store
SourceTargetMeta4086_Next:
.a16
.i16
 lda.l SourceTargetMeta4086_Slot
 inc a
 sta.l SourceTargetMeta4086_Slot
 cmp.l VmSourceWorld_Count
 bcs SourceTargetMeta4086_Publish
 jmp SourceTargetMeta4086_Loop
SourceTargetMeta4086_Publish:
.a16
.i16
 lda #$B4D2
 sta.l SourceTarget4086_Ready
 lda #2
 sta.l SourceTargetMeta4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceTargetMeta4086_Bad:
.a16
.i16
 lda #0
 sta.l SourceTarget4086_Ready
SourceTargetMeta4086_EarlyBad:
.a16
.i16
 lda #3
 sta.l SourceTargetMeta4086_Status
 ply
 plx
 plp
 sec
 rtl
SourceTargetMeta4086_Store:
.a16
.i16
 pha
 tya
 clc
 adc.l SourceTargetMeta4086_Meta
 tax
 pla
 sta.l SOURCE_TARGET_META,x
 rts
; Bank 28's legacy target core is near full. Keep only the four-byte RTS/RTL
; bridge there; this checked public wrapper and new producer live in bank63.
SourceTarget4086_CheckOrder:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceTarget4086_Count
 beq SourceTarget4086_CheckOrderBad
 cmp #129
 bcs SourceTarget4086_CheckOrderBad
 lda.l SourceTarget4086_OrderReady
 cmp #$B4D3
 bne SourceTarget4086_CheckOrderBad
 jsl SourceTarget4086_OrderBridge
 bcs SourceTarget4086_CheckOrderBad
 ply
 plx
 plp
 clc
 rtl
SourceTarget4086_CheckOrderBad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
; Optional admitted source-world adapter. Legacy metadata consumers keep
; their path when B5F2 is absent. Validate typed arguments/null/stale handles
; before rebuilding metadata; no manufactured service response is involved.
SourceTargetMeta4086_FindTargetAdapter:
.a16
.i16
 lda.l SourceTargetMeta4086_Ready
 beq SourceTargetMeta4086_FindLegacy
 cmp #$B5F2
 bne SourceTargetMeta4086_FindBad
 lda.l VmNativeVariant_ContextValid
 cmp #$B48F
 bne SourceTargetMeta4086_FindBad
 lda.l VmCall_Argc
 and #$00FF
 cmp #1
 bne SourceTargetMeta4086_FindBad
 jsl Vm_SourceEntityLocateBridge
 bcs SourceTargetMeta4086_FindBad
 cmp #0
 beq SourceTargetMeta4086_FindNull
 lda.l VmSourceEntity_Ready
 cmp #$B5EF
 bne SourceTargetMeta4086_FindBad
 jsl SourceTargetMeta4086_Build
 bcs SourceTargetMeta4086_FindBad
 jml Vm_SourceFindTarget_Lease
SourceTargetMeta4086_FindNull:
.a16
.i16
 jml Vm_NativeVariantDispatch__null_ok
SourceTargetMeta4086_FindLegacy:
.a16
.i16
 jml Vm_SourceFindTarget_LegacyEntry
SourceTargetMeta4086_FindBad:
.a16
.i16
 lda #VMERR_BAD_NATIVE
 sec
 rtl
