; Named knife_spawn post-construction only; allocation and VM API are separate.
; B611 installer admits zero modeldata.remove for all selected source models.
; Map argument must be zero. ptype/remove_on_attack are capability constants 0;
; APIs that mutate those fields remain unsupported rather than silently aliased.
; Staged EnergyCost/NoCost/NoHit/SavedMode are literal engine scalar inputs.
; Owner must be a live, distinct physical actor with current engine self token.
; Child FFFF represents a NULL constructor result, not an actor selection.
; Coordinates use explicit ACCEPTED_COMPAT_Q16_16, never color quantization.
SourceNamedKnife4086_Ready = $40BF5E
SourceNamedKnife4086_State = $40BF60
SourceNamedKnife4086_Owner = $40BF62
SourceNamedKnife4086_Child = $40BF64
SourceNamedKnife4086_Altitude = $40BF66
SourceNamedKnife4086_Map = $40BF6A
SourceNamedKnife4086_EnergyCost = $40BF6E
SourceNamedKnife4086_NoCost = $40BF72
SourceNamedKnife4086_NoHit = $40BF76
SourceNamedKnife4086_SavedMode = $40BF7A
SourceNamedKnife4086_ParentCore = $40BF7E
SourceNamedKnife4086_ChildCore = $40BF80
SourceNamedKnife4086_ParentRelation = $40BF82
SourceNamedKnife4086_ChildSide = $40BF84
SourceNamedKnife4086_ChildView = $40BF86
SourceNamedKnife4086_ChildLife = $40BF88
SourceNamedKnife4086_ChildRelation = $40BF8A
SourceNamedKnife4086_Model = $40BF8C
SourceNamedKnife4086_Cache = $40BF8E
SourceNamedKnife4086_End = $40BF90

SourceNamedKnife4086_Apply:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceNamedKnife4086_Ready
 cmp #$B611
 beq SourceNamedKnife4086_Guard_0
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_0:
.a16
.i16
 lda.l SourceNamedKnife4086_State
 beq SourceNamedKnife4086_Guard_1
 cmp #2
 beq SourceNamedKnife4086_Guard_1
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_1:
.a16
.i16
 lda.l SourceNamedKnife4086_Child
 cmp #$FFFF
 bne SourceNamedKnife4086_HasChild
 jmp SourceNamedKnife4086_Good
SourceNamedKnife4086_HasChild:
.a16
.i16
 lda.l SourceNamedKnife4086_Map
 ora.l SourceNamedKnife4086_Map+2
 beq SourceNamedKnife4086_Guard_2
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_2:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceNamedKnife4086_Guard_3
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_3:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourceNamedKnife4086_Guard_4
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_4:
.a16
.i16
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 beq SourceNamedKnife4086_Guard_5
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_5:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Ready
 cmp #$B4EB
 beq SourceNamedKnife4086_Guard_6
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_6:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Entities
 cmp.l VmSourceWorld_Count
 beq SourceNamedKnife4086_Guard_7
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_7:
.a16
.i16
 lda.l VmSourceWorld_Count
 bne SourceNamedKnife4086_Guard_8
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_8:
.a16
.i16
 cmp #129
 bcc SourceNamedKnife4086_Guard_9
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_9:
.a16
.i16
 lda.l SourceNamedKnife4086_Owner
 cmp.l VmSourceWorld_Count
 bcc SourceNamedKnife4086_Guard_10
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_10:
.a16
.i16
 lda.l SourceNamedKnife4086_Child
 cmp.l VmSourceWorld_Count
 bcc SourceNamedKnife4086_Guard_11
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_11:
.a16
.i16
 lda.l SourceNamedKnife4086_Child
 cmp.l SourceNamedKnife4086_Owner
 bne SourceNamedKnife4086_Guard_12
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_12:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Models
 bne SourceNamedKnife4086_Guard_13
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_13:
.a16
.i16
 cmp #17
 bcc SourceNamedKnife4086_Guard_14
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_14:
.a16
.i16
 lda.l SourceClock4086_Ready
 cmp #$B4C5
 beq SourceNamedKnife4086_Guard_15
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_15:
.a16
.i16
 lda.l SourceSelf4086_Ready
 cmp #$B4F6
 beq SourceNamedKnife4086_Guard_16
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_16:
.a16
.i16
 lda.l SourceSelf4086_Fault
 beq SourceNamedKnife4086_Guard_17
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_17:
.a16
.i16
 lda.l SourceSelf4086_GlobalHigh
 cmp #$41
 beq SourceNamedKnife4086_Guard_18
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_18:
.a16
.i16
 lda.l SourceAutokillState4086_Ready
 cmp #$B60E
 beq SourceNamedKnife4086_Guard_19
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_19:
.a16
.i16
 lda.l SourceOffscreenState4086_Ready
 cmp #$B610
 beq SourceNamedKnife4086_Guard_20
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_20:
.a16
.i16
 lda.l SourceNamedKnife4086_Child
 jsl SourceOffscreenState4086_PreflightBirth
 bcc SourceNamedKnife4086_Guard_21
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_21:
.a16
.i16
 lda.l SourceNamedKnife4086_Owner
 asl a
 asl a
 asl a
 asl a
 pha
 asl a
 asl a
 sta.l SourceNamedKnife4086_ParentRelation
 clc
 adc 1,s
 tax
 pla
 txa
 clc
 adc #$4000
 cmp.l $414000,x
 beq SourceNamedKnife4086_Guard_22
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_22:
.a16
.i16
 cmp.l SourceSelf4086_GlobalLow
 beq SourceNamedKnife4086_Guard_23
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_23:
.a16
.i16
 lda.l $414002,x
 cmp #$41
 beq SourceNamedKnife4086_Guard_24
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_24:
.a16
.i16
 lda.l $414006,x
 beq SourceNamedKnife4086_Guard_25
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_25:
.a16
.i16
 lda.l $414004,x
 cmp #1
 beq SourceNamedKnife4086_Guard_26
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_26:
.a16
.i16
 lda.l SourceNamedKnife4086_Owner
 asl a
 asl a
 asl a
 asl a
 asl a
 pha
 asl a
 clc
 adc 1,s
 tax
 pla
 txa
 sta.l SourceNamedKnife4086_ParentCore
 lda.l SourceNamedKnife4086_Child
 asl a
 asl a
 asl a
 asl a
 pha
 asl a
 asl a
 sta.l SourceNamedKnife4086_ChildSide
 sta.l SourceNamedKnife4086_ChildRelation
 clc
 adc 1,s
 tax
 pla
 txa
 sta.l SourceNamedKnife4086_ChildView
 sta.l SourceNamedKnife4086_ChildLife
 txa
 clc
 adc #$4000
 cmp.l $414000,x
 beq SourceNamedKnife4086_Guard_27
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_27:
.a16
.i16
 lda.l $414002,x
 cmp #$41
 beq SourceNamedKnife4086_Guard_28
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_28:
.a16
.i16
 lda.l $414006,x
 beq SourceNamedKnife4086_Guard_29
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_29:
.a16
.i16
 lda.l $414004,x
 cmp #2
 bcc SourceNamedKnife4086_Guard_30
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_30:
.a16
.i16
 lda.l SourceNamedKnife4086_Child
 asl a
 asl a
 asl a
 asl a
 asl a
 pha
 asl a
 clc
 adc 1,s
 tax
 pla
 txa
 sta.l SourceNamedKnife4086_ChildCore
 lda.l SourceNamedKnife4086_ChildSide
 tax
 lda.l $416800,x
 cmp.l SourceModelEntityCopy4086_Models
 bcc SourceNamedKnife4086_Guard_31
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_31:
.a16
.i16
 sta.l SourceNamedKnife4086_Model
 asl a
 asl a
 asl a
 asl a
 asl a
 pha
 asl a
 asl a
 clc
 adc 1,s
 tax
 pla
 txa
 sta.l SourceNamedKnife4086_Cache
 lda.l SourceLifecycle4086_Ready
 cmp #$B4FB
 beq SourceNamedKnife4086_LifeLease
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_LifeLease:
.a16
.i16
 lda.l SourceLifecycle4086_Models
 cmp.l SourceModelEntityCopy4086_Models
 beq SourceNamedKnife4086_LifeModels
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_LifeModels:
.a16
.i16
 lda.l SourceNamedKnife4086_ChildLife
 tax
 lda.l $43904C,x
 cmp #$B508
 beq SourceNamedKnife4086_SpeedLease
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_SpeedLease:
.a16
.i16
 lda.l SourceNamedKnife4086_ChildLife
 tax
 lda.l $43904A,x
 cmp #$B4FB
 beq SourceNamedKnife4086_Guard_32
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_32:
.a16
.i16
 lda.l $439048,x
 cmp.l SourceNamedKnife4086_Model
 beq SourceNamedKnife4086_Guard_33
 jmp SourceNamedKnife4086_Bad
SourceNamedKnife4086_Guard_33:
.a16
.i16
 lda #1
 sta.l SourceNamedKnife4086_State
 lda.l SourceNamedKnife4086_ChildView
 tax
 lda #BOR_VT_DECIMAL
 sta.l $414008,x
 lda #0
 sta.l $41400A,x
 lda.l SourceNamedKnife4086_Altitude
 sta.l $41400C,x
 lda.l SourceNamedKnife4086_Altitude+2
 sta.l $41400E,x
 lda.l SourceNamedKnife4086_ParentCore
 tax
 lda.l $40C048,x
 and #1
 beq SourceNamedKnife4086_NotPlayer
 lda #32
 ldy #0
 bra SourceNamedKnife4086_SetType
SourceNamedKnife4086_NotPlayer:
.a16
.i16
 lda.l $40C04A,x
 tay
 lda.l $40C048,x
SourceNamedKnife4086_SetType:
.a16
.i16
 pha
 lda.l SourceNamedKnife4086_ChildCore
 tax
 pla
 sta.l $40C048,x
 tya
 sta.l $40C04A,x
 lda.l SourceNamedKnife4086_EnergyCost+2
 bmi SourceNamedKnife4086_CostDone
 ora.l SourceNamedKnife4086_EnergyCost
 beq SourceNamedKnife4086_CostDone
 lda.l SourceNamedKnife4086_NoCost
 ora.l SourceNamedKnife4086_NoCost+2
 beq SourceNamedKnife4086_CostDone
 lda.l SourceNamedKnife4086_ParentRelation
 tax
 lda #1
 sta.l $409020,x
 lda #0
 sta.l $409022,x
SourceNamedKnife4086_CostDone:
.a16
.i16
 lda.l SourceNamedKnife4086_ChildLife
 tax
 lda.l $439034,x
 ora.l $439036,x
 beq SourceNamedKnife4086_CachedSpeed
 lda #0
 ldy #0
 bra SourceNamedKnife4086_SetSpeed
SourceNamedKnife4086_CachedSpeed:
.a16
.i16
 lda.l SourceNamedKnife4086_Cache
 tax
 lda.l $40B002,x
 and #$7FFF
 ora.l $40B000,x
 bne SourceNamedKnife4086_SpeedDone
 lda #2
 ldy #1
SourceNamedKnife4086_SetSpeed:
.a16
.i16
 pha
 lda.l SourceNamedKnife4086_ChildSide
 tax
 lda #0
 sta.l $41683C,x
 pla
 sta.l $41683E,x
 lda.l SourceNamedKnife4086_ChildLife
 tax
 tya
 sta.l $439044,x
 lda #0
 sta.l $439046,x
 lda #$B508
 sta.l $43904C,x
SourceNamedKnife4086_SpeedDone:
.a16
.i16
 lda.l SourceNamedKnife4086_ChildRelation
 tax
 lda.l SourceSelf4086_GlobalLow
 sta.l $409008,x
 lda #$41
 sta.l $40900A,x
 lda.l SourceNamedKnife4086_ChildCore
 tax
 lda #1
 sta.l $40C058,x
 lda #0
 sta.l $40C05A,x
 lda #256
 sta.l $40C034,x
 lda #0
 sta.l $40C036,x
 lda #4
 sta.l $40C038,x
 lda #0
 sta.l $40C03A,x
 lda.l SourceNamedKnife4086_ChildLife
 tax
 lda #6
 sta.l $439000,x
 lda #0
 sta.l $439002,x
 sta.l $439004,x
 sta.l $439006,x
 sta.l $43900A,x
 sta.l $43900C,x
 sta.l $43900E,x
 sta.l $439012,x
 lda #8
 sta.l $439008,x
 lda #1
 sta.l $439010,x
 lda.l SourceNamedKnife4086_ChildSide
 tax
 lda.l SourceClock4086_TimeLo
 clc
 adc #1
 sta.l $416814,x
 lda.l SourceClock4086_TimeHi
 adc #0
 sta.l $416816,x
 lda #0
 sta.l $416820,x
 lda #2
 sta.l $416822,x
 lda.l SourceNamedKnife4086_Altitude
 sta.l $416830,x
 lda.l SourceNamedKnife4086_Altitude+2
 sta.l $416832,x
 lda.l SourceNamedKnife4086_Child
 asl a
 asl a
 tax
 lda.l SOURCE_ENTITY_OFFSCREEN,x
 ora.l SOURCE_ENTITY_OFFSCREEN+2,x
 bne SourceNamedKnife4086_OffscreenDone
 lda #200
 sta.l SOURCE_ENTITY_OFFSCREEN,x
 lda #0
 sta.l SOURCE_ENTITY_OFFSCREEN+2,x
SourceNamedKnife4086_OffscreenDone:
.a16
.i16
 phx
 lda.l SourceNamedKnife4086_ChildLife
 tax
 lda.l $439034,x
 tay
 lda.l $439036,x
 plx
 sta.l SOURCE_ENTITY_AUTOKILL+2,x
 tya
 sta.l SOURCE_ENTITY_AUTOKILL,x
 lda.l SourceNamedKnife4086_Child
 asl a
 asl a
 asl a
 asl a
 asl a
 asl a
 tax
 lda #0
 sta.l $433830,x ; actual colourmap index (map0 clears any old map)
 lda.l SourceNamedKnife4086_ChildCore
 tax
 lda.l $40C02A,x
 bpl SourceNamedKnife4086_InheritDone40
 lda.l SourceNamedKnife4086_ParentCore
 tax
 lda.l $40C028,x
 pha
 lda.l $40C02A,x
 tay
 lda.l SourceNamedKnife4086_ChildCore
 tax
 pla
 sta.l $40C028,x
 tya
 sta.l $40C02A,x
SourceNamedKnife4086_InheritDone40:
.a16
.i16
 lda.l SourceNamedKnife4086_ChildCore
 tax
 lda.l $40C02E,x
 bpl SourceNamedKnife4086_InheritDone44
 lda.l SourceNamedKnife4086_ParentCore
 tax
 lda.l $40C02C,x
 pha
 lda.l $40C02E,x
 tay
 lda.l SourceNamedKnife4086_ChildCore
 tax
 pla
 sta.l $40C02C,x
 tya
 sta.l $40C02E,x
SourceNamedKnife4086_InheritDone44:
.a16
.i16
 lda.l SourceNamedKnife4086_ParentCore
 tax
 lda.l $40C048,x
 and #1
 beq SourceNamedKnife4086_MaskDone
 lda.l SourceNamedKnife4086_NoHit
 ora.l SourceNamedKnife4086_NoHit+2
 ora.l SourceNamedKnife4086_SavedMode
 ora.l SourceNamedKnife4086_SavedMode+2
 beq SourceNamedKnife4086_MaskDone
 lda.l SourceNamedKnife4086_ChildCore
 tax
 lda.l $40C028,x
 and #$FFFE
 sta.l $40C028,x
 lda.l $40C02C,x
 and #$FFFE
 sta.l $40C02C,x
SourceNamedKnife4086_MaskDone:
.a16
.i16
 lda.l SourceNamedKnife4086_ChildCore
 tax
 lda #1
 sta.l $40C004,x
 lda #0
 sta.l $40C006,x
 lda #1
 sta.l $40C008,x
 lda #0
 sta.l $40C00A,x
 lda #1
 sta.l $40C010,x
 lda #0
 sta.l $40C012,x
 lda #1
 sta.l $40C014,x
 lda #0
 sta.l $40C016,x
 lda #1
 sta.l $40C024,x
 lda #0
 sta.l $40C026,x
SourceNamedKnife4086_Good:
.a16
.i16
 lda #2
 sta.l SourceNamedKnife4086_State
 ply
 plx
 plp
 clc
 rtl
SourceNamedKnife4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceNamedKnife4086_State
 ply
 plx
 plp
 sec
 rtl
