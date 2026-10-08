; Pinned inactive-air check_gravity, sticky base and empty platform world.
; B618 compiler contract: falling=0, no binding/platform mutation capability.
; B619 additionally admits non-gravitating hover: no DROPFRAME/WALKOFF,
; immutable current-stage fall/toss bounds cover zero. Revoke on mutations.
; Actual typed altitude/base, zero vertical velocity and no_adjust_base>0
; are checked before admission. Active airborne/landing needs another backend.
; Source phase11 subservice; no post-update Ack. Existing mark8 exits early.
SourceGravityIdle4086_Ready = $40BFE0
SourceGravityIdle4086_Status = $40BFE2
SourceGravityIdle4086_View = $40BFE4
SourceGravityIdle4086_Side = $40BFE6
SourceGravityIdle4086_Aux = $40BFE8
SourceGravityIdle4086_Mark = $40BFEA
SourceGravityIdle4086_Due = $40BFEC
SourceGravityIdle4086_Core = $40BFEE
SourceGravityIdle4086_X = $40BFF0
SourceGravityIdle4086_Z = $40BFF4
SourceGravityIdle4086_End = $40BFF8
SourceGravityIdle4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceGravityIdle4086_Ready
 cmp #$B618
 beq SourceGravityIdle4086_Guard1
 cmp #$B619
 beq SourceGravityIdle4086_Guard1
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_Guard1:
.a16
.i16
 lda.l SourceGravityIdle4086_Status
 cmp #0
 beq SourceGravityIdle4086_Guard2
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_Guard2:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceGravityIdle4086_Guard3
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_Guard3:
.a16
.i16
 lda.l SourceWorldTick4086_Ready
 cmp #$B4D5
 beq SourceGravityIdle4086_Guard4
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_Guard4:
.a16
.i16
 lda.l SourceWorldTick4086_State
 cmp #1
 beq SourceGravityIdle4086_Guard5
 cmp #2 ; actual arrange_ents POST_UPDATE owner
 beq SourceGravityIdle4086_Guard5
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_Guard5:
.a16
.i16
 lda.l SourceWorldTick4086_Phase
 cmp #11
 beq SourceGravityIdle4086_Guard6
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_Guard6:
.a16
.i16
 lda.l SourceWorldTick4086_Pending
 cmp #1
 beq SourceGravityIdle4086_Guard7
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_Guard7:
.a16
.i16
 lda.l SourceWorldTick4086_Fault
 cmp #0
 beq SourceGravityIdle4086_Guard8
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_Guard8:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourceGravityIdle4086_Guard9
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_Guard9:
.a16
.i16
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 beq SourceGravityIdle4086_Guard10
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_Guard10:
.a16
.i16
 lda.l SourceUpdateFrame4086_Ready
 cmp #$B4E3
 beq SourceGravityIdle4086_Guard11
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_Guard11:
.a16
.i16
 lda.l SourceFreeze4086_Ready
 cmp #$B5DF
 beq SourceGravityIdle4086_FreezeLease
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_FreezeLease:
.a16
.i16
 lda.l SourceLifecycle4086_Ready
 cmp #$B4FB
 beq SourceGravityIdle4086_Guard12
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_Guard12:
.a16
.i16
 lda.l SourceSelf4086_Ready
 cmp #$B4F6
 beq SourceGravityIdle4086_Guard13
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_Guard13:
.a16
.i16
 lda.l SourceSelf4086_Active
 cmp #0
 beq SourceGravityIdle4086_Guard14
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_Guard14:
.a16
.i16
 lda.l SourceSelf4086_Fault
 cmp #0
 beq SourceGravityIdle4086_Guard15
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_Guard15:
.a16
.i16
 lda.l SourceWorldTick4086_TimeLo
 cmp.l VmSourceWorld_Time
 beq SourceGravityIdle4086_Guard16
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_Guard16:
.a16
.i16
 lda.l SourceWorldTick4086_TimeLo+2
 cmp.l VmSourceWorld_Time+2
 beq SourceGravityIdle4086_Guard17
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_Guard17:
.a16
.i16
 lda.l VmSourceWorld_Count
 cmp #129
 bcc SourceGravityIdle4086_Guard18
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_Guard18:
.a16
.i16
 lda.l SourceWorldTick4086_Slot
 cmp.l VmSourceWorld_Count
 bcc SourceGravityIdle4086_Guard19
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_Guard19:
.a16
.i16
 asl a
 asl a
 sta.l SourceGravityIdle4086_Aux
 asl a
 asl a
 clc
 adc.l SourceGravityIdle4086_Aux
 sta.l SourceGravityIdle4086_Aux
 lda.l SourceWorldTick4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l SourceGravityIdle4086_Mark
 asl a
 sta.l SourceGravityIdle4086_Side
 lsr a
 lsr a
 clc
 adc.l SourceGravityIdle4086_Side
 sta.l SourceGravityIdle4086_View
 adc #$4000
 cmp.l SourceSelf4086_GlobalLow
 beq SourceGravityIdle4086_Guard20
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_Guard20:
.a16
.i16
 lda.l SourceSelf4086_GlobalHigh
 cmp #$41
 beq SourceGravityIdle4086_Guard21
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_Guard21:
.a16
.i16
 lda.l SourceGravityIdle4086_View
 tax
 lda.l SOURCE_WORLD_POOL,x
 clc
 adc #0
 cmp.l SourceSelf4086_GlobalLow
 beq SourceGravityIdle4086_Guard22
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_Guard22:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+2,x
 cmp #$41
 beq SourceGravityIdle4086_Guard23
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_Guard23:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+4,x
 ora.l SOURCE_WORLD_POOL+6,x
 bne SourceGravityIdle4086_Guard24
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_Guard24:
.a16
.i16
 lda.l SourceGravityIdle4086_Mark
 lsr a
 lsr a
 clc
 adc.l SourceGravityIdle4086_Mark
 sta.l SourceGravityIdle4086_Mark
 tax
 lda.l SOURCE_WORLD_FREEZE+36,x
 and #8
 beq SourceGravityIdle4086_First
 jmp SourceGravityIdle4086_Done
SourceGravityIdle4086_First:
.a16
.i16
 lda.l SourceGravityIdle4086_Side
 tax
 lda.l SOURCE_WORLD_SIDES,x
 cmp.l SourceEmptyInitEnvironment4086_Models
 bcc SourceGravityIdle4086_ModelRange
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_ModelRange:
.a16
.i16
 pha
 lda.l SourceGravityIdle4086_View
 tax
 pla
 cmp.l $439048,x
 beq SourceGravityIdle4086_ModelIdentity
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_ModelIdentity:
.a16
.i16
 lda.l $43904A,x
 cmp #$B4FB
 beq SourceGravityIdle4086_ModelLease
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_ModelLease:
.a16
.i16
 jsl SourceEmptyInitEnvironment4086_Query
 bcc SourceGravityIdle4086_Guard25
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_Guard25:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Ready
 cmp #$B4EB
 beq SourceGravityIdle4086_CoreReady
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_CoreReady:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Entities
 cmp.l VmSourceWorld_Count
 beq SourceGravityIdle4086_CoreCount
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_CoreCount:
.a16
.i16
 lda.l SourceWorldTick4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l SourceGravityIdle4086_Core
 asl a
 clc
 adc.l SourceGravityIdle4086_Core
 sta.l SourceGravityIdle4086_Core
 tax
 lda.l $40C026,x
 bmi SourceGravityIdle4086_RejectCore
 ora.l $40C024,x
 bne SourceGravityIdle4086_StickyBase
SourceGravityIdle4086_RejectCore:
.a16
.i16
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_StickyBase:
.a16
.i16
 lda.l SourcePhysicsState4086_Ready
 beq SourceGravityIdle4086_PhysicsGuardDone
 cmp #$B61C
 beq SourceGravityIdle4086_PhysicsLease
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_PhysicsLease:
.a16
.i16
 lda.l SourceWorldTick4086_Slot
 asl a
 asl a
 asl a
 asl a
 tax
 ; Closed stationary/no-platform capability requires actual zero falling and
 ; NULL collision relations whenever the canonical physics row is installed.
 lda.l SOURCE_ENTITY_PHYSICS,x
 ora.l SOURCE_ENTITY_PHYSICS+2,x
 ora.l SOURCE_ENTITY_PHYSICS+4,x
 ora.l SOURCE_ENTITY_PHYSICS+6,x
 ora.l SOURCE_ENTITY_PHYSICS+8,x
 ora.l SOURCE_ENTITY_PHYSICS+10,x
 beq SourceGravityIdle4086_PhysicsGuardDone
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_PhysicsGuardDone:
.a16
.i16
 lda.l SourceGravityIdle4086_Side
 tax
 lda.l SOURCE_WORLD_SIDES+44,x
 ora.l SOURCE_WORLD_SIDES+46,x
 beq SourceGravityIdle4086_ZeroVertical
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_ZeroVertical:
.a16
.i16
 lda.l SOURCE_WORLD_SIDES+48,x
 sta.l SourceGravityIdle4086_X
 lda.l SOURCE_WORLD_SIDES+50,x
 sta.l SourceGravityIdle4086_X+2
 lda.l SourceGravityIdle4086_View
 tax
 lda.l SOURCE_WORLD_POOL+8,x
 cmp #BOR_VT_DECIMAL
 beq SourceGravityIdle4086_AltitudeTyped
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_AltitudeTyped:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+10,x
 beq SourceGravityIdle4086_AltitudeReserved
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_AltitudeReserved:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+12,x
 cmp.l SourceGravityIdle4086_X
 beq SourceGravityIdle4086_AltitudeLow
 jmp SourceGravityIdle4086_Hover
SourceGravityIdle4086_AltitudeLow:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+14,x
 cmp.l SourceGravityIdle4086_X+2
 beq SourceGravityIdle4086_Inactive
 jmp SourceGravityIdle4086_Hover
SourceGravityIdle4086_Hover:
.a16
.i16
 lda.l SourceGravityIdle4086_Ready
 cmp #$B619
 beq SourceGravityIdle4086_HoverLease
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_HoverLease:
.a16
.i16
 lda.l SourceGravityIdle4086_Core
 tax
 lda.l $40C016,x
 bmi SourceGravityIdle4086_HoverNoGravity
 ora.l $40C014,x
 beq SourceGravityIdle4086_HoverNoGravity
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_HoverNoGravity:
.a16
.i16
 lda.l SourceGravityIdle4086_View
 tax
 lda.l SOURCE_WORLD_POOL+12,x
 sec
 sbc.l SourceGravityIdle4086_X
 sta.l SourceGravityIdle4086_Z
 lda.l SOURCE_WORLD_POOL+14,x
 sbc.l SourceGravityIdle4086_X+2
 bvs SourceGravityIdle4086_HoverReject
 bmi SourceGravityIdle4086_HoverReject
 bne SourceGravityIdle4086_Inactive
 lda.l SourceGravityIdle4086_Z
 cmp #6554
 bcs SourceGravityIdle4086_Inactive
SourceGravityIdle4086_HoverReject:
.a16
.i16
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_Inactive:
.a16
.i16
 jsl SourceFreeze4086_Query
 bcc SourceGravityIdle4086_FreezeValid
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_FreezeValid:
.a16
.i16
 cmp #0
 beq SourceGravityIdle4086_TimeLease
 jmp SourceGravityIdle4086_MarkChecked
SourceGravityIdle4086_TimeLease:
.a16
.i16
 lda.l SourceToss4086_Ready
 cmp #$B4E2
 beq SourceGravityIdle4086_TimerOffset
 jmp SourceGravityIdle4086_Bad
SourceGravityIdle4086_TimerOffset:
.a16
.i16
 lda.l SourceWorldTick4086_Slot
 asl a
 asl a
 tax
 lda.l SOURCE_WORLD_TOSS_TIMES+2,x
 cmp.l VmSourceWorld_Time+2
 bcc SourceGravityIdle4086_TimerDue
 beq SourceGravityIdle4086_TimerLow
 bra SourceGravityIdle4086_MarkChecked
SourceGravityIdle4086_TimerLow:
.a16
.i16
 lda.l SOURCE_WORLD_TOSS_TIMES,x
 cmp.l VmSourceWorld_Time
 bcc SourceGravityIdle4086_TimerDue
 beq SourceGravityIdle4086_TimerDue
 bra SourceGravityIdle4086_MarkChecked
SourceGravityIdle4086_TimerDue:
.a16
.i16
 lda.l VmSourceWorld_Time
 clc
 adc #1
 sta.l SOURCE_WORLD_TOSS_TIMES,x
 lda.l VmSourceWorld_Time+2
 adc #0
 sta.l SOURCE_WORLD_TOSS_TIMES+2,x
SourceGravityIdle4086_MarkChecked:
.a16
.i16
 lda.l SourceGravityIdle4086_Mark
 tax
 lda.l SOURCE_WORLD_FREEZE+36,x
 ora #8
 sta.l SOURCE_WORLD_FREEZE+36,x
SourceGravityIdle4086_Done:
.a16
.i16
 lda #2
 sta.l SourceGravityIdle4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceGravityIdle4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceGravityIdle4086_Status
 ply
 plx
 plp
 sec
 rtl
