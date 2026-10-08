; B621 bounded active air integration with B622 immutable zero-height/zero-
; model-antigravity/no DROPFRAME/WALKOFF/onmovea profile, B623 stage physics,
; and actual B620 base service. Status1 requires real landing service, never Ack.
; Q16 numeric compatibility; compiler/world installer is not admitted here.
SourceGravityAir4086_Ready = $41FF68
SourceGravityAir4086_Status = $41FF6A
SourceGravityAir4086_View = $41FF6C
SourceGravityAir4086_Side = $41FF6E
SourceGravityAir4086_Aux = $41FF70
SourceGravityAir4086_Mark = $41FF72
SourceGravityAir4086_Core = $41FF74
SourceGravityAir4086_Due = $41FF76
SourceGravityAir4086_StageReady = $41FF78
SourceGravityAir4086_StageId = $41FF7A
SourceGravityAir4086_Gravity = $41FF7C
SourceGravityAir4086_MinFall = $41FF80
SourceGravityAir4086_MaxToss = $41FF84
SourceGravityAir4086_ZeroProfileReady = $41FF88
SourceGravityAir4086_ZeroModels = $41FF8A
SourceGravityAir4086_Position = $41FF8C
SourceGravityAir4086_Velocity = $41FF90
SourceGravityAir4086_Base = $41FF94
SourceGravityAir4086_Delta = $41FF98
SourceGravityAir4086_Temp = $41FF9C
SourceGravityAir4086_OriginalBase = $41FFA0
SourceGravityAir4086_OriginalVx = $41FFA4
SourceGravityAir4086_OriginalVz = $41FFA8
SourceGravityAir4086_PhysicsOffset = $41FFAC
SourceGravityAir4086_LandingNeeded = $41FFAE
SourceGravityAir4086_End = $41FFB0
SourceGravityAir4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceGravityAir4086_Ready
 cmp #$B621
 beq SourceGravityAir4086_Guard1
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_Guard1:
.a16
.i16
 lda #0
 sta.l SourceGravityAir4086_LandingNeeded
 lda.l SourceGravityAir4086_Status
 cmp #0
 beq SourceGravityAir4086_Guard2
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_Guard2:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceGravityAir4086_Guard3
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_Guard3:
.a16
.i16
 lda.l SourceWorldTick4086_Ready
 cmp #$B4D5
 beq SourceGravityAir4086_Guard4
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_Guard4:
.a16
.i16
 lda.l SourceWorldTick4086_State
 cmp #1
 beq SourceGravityAir4086_Guard5
 cmp #2 ; actual arrange_ents POST_UPDATE owner
 beq SourceGravityAir4086_Guard5
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_Guard5:
.a16
.i16
 lda.l SourceWorldTick4086_Phase
 cmp #11
 beq SourceGravityAir4086_Guard6
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_Guard6:
.a16
.i16
 lda.l SourceWorldTick4086_Pending
 cmp #1
 beq SourceGravityAir4086_Guard7
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_Guard7:
.a16
.i16
 lda.l SourceWorldTick4086_Fault
 cmp #0
 beq SourceGravityAir4086_Guard8
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_Guard8:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourceGravityAir4086_Guard9
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_Guard9:
.a16
.i16
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 beq SourceGravityAir4086_Guard10
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_Guard10:
.a16
.i16
 lda.l SourceUpdateFrame4086_Ready
 cmp #$B4E3
 beq SourceGravityAir4086_Guard11
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_Guard11:
.a16
.i16
 lda.l SourceFreeze4086_Ready
 cmp #$B5DF
 beq SourceGravityAir4086_FreezeLease
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_FreezeLease:
.a16
.i16
 lda.l SourceLifecycle4086_Ready
 cmp #$B4FB
 beq SourceGravityAir4086_Guard12
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_Guard12:
.a16
.i16
 lda.l SourceSelf4086_Ready
 cmp #$B4F6
 beq SourceGravityAir4086_Guard13
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_Guard13:
.a16
.i16
 lda.l SourceSelf4086_Active
 cmp #0
 beq SourceGravityAir4086_Guard14
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_Guard14:
.a16
.i16
 lda.l SourceSelf4086_Fault
 cmp #0
 beq SourceGravityAir4086_Guard15
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_Guard15:
.a16
.i16
 lda.l SourceWorldTick4086_TimeLo
 cmp.l VmSourceWorld_Time
 beq SourceGravityAir4086_Guard16
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_Guard16:
.a16
.i16
 lda.l SourceWorldTick4086_TimeLo+2
 cmp.l VmSourceWorld_Time+2
 beq SourceGravityAir4086_Guard17
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_Guard17:
.a16
.i16
 lda.l VmSourceWorld_Count
 cmp #129
 bcc SourceGravityAir4086_Guard18
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_Guard18:
.a16
.i16
 lda.l SourceWorldTick4086_Slot
 cmp.l VmSourceWorld_Count
 bcc SourceGravityAir4086_Guard19
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_Guard19:
.a16
.i16
 asl a
 asl a
 sta.l SourceGravityAir4086_Aux
 asl a
 asl a
 clc
 adc.l SourceGravityAir4086_Aux
 sta.l SourceGravityAir4086_Aux
 lda.l SourceWorldTick4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l SourceGravityAir4086_Mark
 asl a
 sta.l SourceGravityAir4086_Side
 lsr a
 lsr a
 clc
 adc.l SourceGravityAir4086_Side
 sta.l SourceGravityAir4086_View
 adc #$4000
 cmp.l SourceSelf4086_GlobalLow
 beq SourceGravityAir4086_Guard20
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_Guard20:
.a16
.i16
 lda.l SourceSelf4086_GlobalHigh
 cmp #$41
 beq SourceGravityAir4086_Guard21
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_Guard21:
.a16
.i16
 lda.l SourceGravityAir4086_View
 tax
 lda.l SOURCE_WORLD_POOL,x
 clc
 adc #0
 cmp.l SourceSelf4086_GlobalLow
 beq SourceGravityAir4086_Guard22
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_Guard22:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+2,x
 cmp #$41
 beq SourceGravityAir4086_Guard23
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_Guard23:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+4,x
 ora.l SOURCE_WORLD_POOL+6,x
 bne SourceGravityAir4086_Guard24
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_Guard24:
.a16
.i16
 lda.l SourceGravityAir4086_Mark
 lsr a
 lsr a
 clc
 adc.l SourceGravityAir4086_Mark
 sta.l SourceGravityAir4086_Mark
 tax
 lda.l SOURCE_WORLD_FREEZE+36,x
 and #8
 beq SourceGravityAir4086_First
 jmp SourceGravityAir4086_Done
SourceGravityAir4086_First:
.a16
.i16
 lda.l SourceGravityAir4086_Side
 tax
 lda.l SOURCE_WORLD_SIDES,x
 cmp.l SourceEmptyInitEnvironment4086_Models
 bcc SourceGravityAir4086_ModelRange
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_ModelRange:
.a16
.i16
 pha
 lda.l SourceGravityAir4086_View
 tax
 pla
 cmp.l $439048,x
 beq SourceGravityAir4086_ModelIdentity
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_ModelIdentity:
.a16
.i16
 lda.l $43904A,x
 cmp #$B4FB
 beq SourceGravityAir4086_ModelLease
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_ModelLease:
.a16
.i16
 lda.l SourceGravityAir4086_ZeroProfileReady
 cmp #$B622
 beq SourceGravityAir4086_ExtraGuard1
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_ExtraGuard1:
.a16
.i16
 lda.l SourceGravityAir4086_ZeroModels
 cmp.l SourceEmptyInitEnvironment4086_Models
 beq SourceGravityAir4086_ExtraGuard2
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_ExtraGuard2:
.a16
.i16
 lda.l SourcePhysicsState4086_Ready
 cmp #$B61C
 beq SourceGravityAir4086_ExtraGuard3
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_ExtraGuard3:
.a16
.i16
 lda.l SourceAdjustBaseEmpty4086_Ready
 cmp #$B620
 beq SourceGravityAir4086_ExtraGuard4
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_ExtraGuard4:
.a16
.i16
 lda.l SourceGravityAir4086_StageReady
 cmp #$B623
 beq SourceGravityAir4086_ExtraGuard5
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_ExtraGuard5:
.a16
.i16
 lda.l SourceGravityAir4086_StageId
 cmp.l SourceEnvironment4086_Stage
 beq SourceGravityAir4086_ExtraGuard6
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_ExtraGuard6:
.a16
.i16
 lda.l SourceToss4086_Ready
 cmp #$B4E2
 beq SourceGravityAir4086_ExtraGuard7
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_ExtraGuard7:
.a16
.i16
 lda.l SourceGravityAir4086_MinFall+2
 eor #$8000
 sta.l SourceGravityAir4086_Temp
 lda.l SourceGravityAir4086_MaxToss+2
 eor #$8000
 cmp.l SourceGravityAir4086_Temp
 bne SourceGravityAir4086_BoundsHigh
 lda.l SourceGravityAir4086_MaxToss
 cmp.l SourceGravityAir4086_MinFall
SourceGravityAir4086_BoundsHigh:
.a16
.i16
 bcs SourceGravityAir4086_ExtraGuard8
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_ExtraGuard8:
.a16
.i16
 lda.l SourceGravityAir4086_Side
 tax
 lda.l SOURCE_WORLD_SIDES+48,x
 sta.l SourceGravityAir4086_OriginalBase
 lda.l SOURCE_WORLD_SIDES+50,x
 sta.l SourceGravityAir4086_OriginalBase+2
 lda.l SOURCE_WORLD_SIDES+36,x
 sta.l SourceGravityAir4086_OriginalVx
 lda.l SOURCE_WORLD_SIDES+38,x
 sta.l SourceGravityAir4086_OriginalVx+2
 lda.l SOURCE_WORLD_SIDES+40,x
 sta.l SourceGravityAir4086_OriginalVz
 lda.l SOURCE_WORLD_SIDES+42,x
 sta.l SourceGravityAir4086_OriginalVz+2
 jsl SourceAdjustBaseEmpty4086_RunPost
 bcc SourceGravityAir4086_ExtraGuard9
 jmp SourceGravityAir4086_Bad
SourceGravityAir4086_ExtraGuard9:
.a16
.i16
 jsl SourceFreeze4086_Query
 bcc SourceGravityAir4086_ExtraGuard10
 jmp SourceGravityAir4086_RollbackBad
SourceGravityAir4086_ExtraGuard10:
.a16
.i16
 cmp #0
 beq SourceGravityAir4086_Unfrozen
 jmp SourceGravityAir4086_MarkDone
SourceGravityAir4086_Unfrozen:
.a16
.i16
 lda #0
 sta.l SourceGravityAir4086_Due
 lda.l SourceWorldTick4086_Slot
 asl a
 asl a
 tax
 lda.l SOURCE_WORLD_TOSS_TIMES+2,x
 cmp.l VmSourceWorld_Time+2
 bcc SourceGravityAir4086_IsDue
 bne SourceGravityAir4086_NotDue
 lda.l SOURCE_WORLD_TOSS_TIMES,x
 cmp.l VmSourceWorld_Time
 bcc SourceGravityAir4086_IsDue
 beq SourceGravityAir4086_IsDue
SourceGravityAir4086_NotDue:
.a16
.i16
 jmp SourceGravityAir4086_MarkDone
SourceGravityAir4086_IsDue:
.a16
.i16
 lda #1
 sta.l SourceGravityAir4086_Due
 lda.l SourceWorldTick4086_Slot
 asl a
 asl a
 asl a
 asl a
 sta.l SourceGravityAir4086_PhysicsOffset
 tax
 lda.l SOURCE_ENTITY_PHYSICS,x
 ora.l SOURCE_ENTITY_PHYSICS+2,x
 sta.l SourceGravityAir4086_Temp
 lda.l SourceGravityAir4086_Side
 tax
 lda.l SOURCE_WORLD_SIDES+44,x
 sta.l SourceGravityAir4086_Velocity
 ora.l SourceGravityAir4086_Temp
 sta.l SourceGravityAir4086_Temp
 lda.l SOURCE_WORLD_SIDES+46,x
 sta.l SourceGravityAir4086_Velocity+2
 ora.l SourceGravityAir4086_Temp
 sta.l SourceGravityAir4086_Temp
 lda.l SOURCE_WORLD_SIDES+48,x
 sta.l SourceGravityAir4086_Base
 lda.l SOURCE_WORLD_SIDES+50,x
 sta.l SourceGravityAir4086_Base+2
 lda.l SourceGravityAir4086_View
 tax
 lda.l SOURCE_WORLD_POOL+12,x
 sta.l SourceGravityAir4086_Position
 cmp.l SourceGravityAir4086_Base
 bne SourceGravityAir4086_Airborne
 lda.l SOURCE_WORLD_POOL+14,x
 sta.l SourceGravityAir4086_Position+2
 cmp.l SourceGravityAir4086_Base+2
 bne SourceGravityAir4086_Airborne
 lda.l SourceGravityAir4086_Temp
 bne SourceGravityAir4086_Airborne
 jmp SourceGravityAir4086_TimerDone
SourceGravityAir4086_Airborne:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+14,x
 sta.l SourceGravityAir4086_Position+2
 lda.l SourceGravityAir4086_Velocity+2
 cmp #$8000
 ror a
 sta.l SourceGravityAir4086_Delta+2
 lda.l SourceGravityAir4086_Velocity
 ror a
 sta.l SourceGravityAir4086_Delta
 clc
 adc.l SourceGravityAir4086_Position
 sta.l SourceGravityAir4086_Position
 lda.l SourceGravityAir4086_Position+2
 adc.l SourceGravityAir4086_Delta+2
 bvc SourceGravityAir4086_ExtraGuard11
 jmp SourceGravityAir4086_RollbackBad
SourceGravityAir4086_ExtraGuard11:
.a16
.i16
 sta.l SourceGravityAir4086_Position+2
 lda.l SourceWorldTick4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l SourceGravityAir4086_Core
 asl a
 clc
 adc.l SourceGravityAir4086_Core
 tax
 lda.l $40C016,x
 bmi SourceGravityAir4086_Clamp
 ora.l $40C014,x
 beq SourceGravityAir4086_Clamp
 lda.l SourceAnimationPhysics4086_Antigrav
 bne SourceGravityAir4086_Clamp
 lda.l SourceGravityAir4086_Gravity+2
 cmp #$8000
 ror a
 sta.l SourceGravityAir4086_Delta+2
 lda.l SourceGravityAir4086_Gravity
 ror a
 sta.l SourceGravityAir4086_Delta
 clc
 adc.l SourceGravityAir4086_Velocity
 sta.l SourceGravityAir4086_Velocity
 lda.l SourceGravityAir4086_Velocity+2
 adc.l SourceGravityAir4086_Delta+2
 bvc SourceGravityAir4086_ExtraGuard12
 jmp SourceGravityAir4086_RollbackBad
SourceGravityAir4086_ExtraGuard12:
.a16
.i16
 sta.l SourceGravityAir4086_Velocity+2
SourceGravityAir4086_Clamp:
.a16
.i16
 lda.l SourceGravityAir4086_MinFall+2
 eor #$8000
 sta.l SourceGravityAir4086_Temp
 lda.l SourceGravityAir4086_Velocity+2
 eor #$8000
 cmp.l SourceGravityAir4086_Temp
 bcc SourceGravityAir4086_ClampMin
 bne SourceGravityAir4086_MinOK
 lda.l SourceGravityAir4086_Velocity
 cmp.l SourceGravityAir4086_MinFall
 bcs SourceGravityAir4086_MinOK
SourceGravityAir4086_ClampMin:
.a16
.i16
 lda.l SourceGravityAir4086_MinFall
 sta.l SourceGravityAir4086_Velocity
 lda.l SourceGravityAir4086_MinFall+2
 sta.l SourceGravityAir4086_Velocity+2
SourceGravityAir4086_MinOK:
.a16
.i16
 lda.l SourceGravityAir4086_MaxToss+2
 eor #$8000
 sta.l SourceGravityAir4086_Temp
 lda.l SourceGravityAir4086_Velocity+2
 eor #$8000
 cmp.l SourceGravityAir4086_Temp
 bcc SourceGravityAir4086_MaxOK
 bne SourceGravityAir4086_ClampMax
 lda.l SourceGravityAir4086_Velocity
 cmp.l SourceGravityAir4086_MaxToss
 bcc SourceGravityAir4086_MaxOK
 beq SourceGravityAir4086_MaxOK
SourceGravityAir4086_ClampMax:
.a16
.i16
 lda.l SourceGravityAir4086_MaxToss
 sta.l SourceGravityAir4086_Velocity
 lda.l SourceGravityAir4086_MaxToss+2
 sta.l SourceGravityAir4086_Velocity+2
SourceGravityAir4086_MaxOK:
.a16
.i16
 lda.l SourceGravityAir4086_Position
 sec
 sbc.l SourceGravityAir4086_Base
 sta.l SourceGravityAir4086_Delta
 lda.l SourceGravityAir4086_Position+2
 sbc.l SourceGravityAir4086_Base+2
 bvc SourceGravityAir4086_ExtraGuard13
 jmp SourceGravityAir4086_RollbackBad
SourceGravityAir4086_ExtraGuard13:
.a16
.i16
 sta.l SourceGravityAir4086_Delta+2
 lda #0
 sta.l SourceGravityAir4086_LandingNeeded
 lda.l SourceGravityAir4086_Velocity+2
 bmi SourceGravityAir4086_Descending
 ora.l SourceGravityAir4086_Velocity
 bne SourceGravityAir4086_PublishAir
SourceGravityAir4086_Descending:
.a16
.i16
 lda.l SourceGravityAir4086_Delta+2
 bmi SourceGravityAir4086_NeedsLanding
 bne SourceGravityAir4086_PublishAir
 lda.l SourceGravityAir4086_Delta
 cmp #6554
 bcs SourceGravityAir4086_PublishAir
SourceGravityAir4086_NeedsLanding:
.a16
.i16
 lda #1
 sta.l SourceGravityAir4086_LandingNeeded
SourceGravityAir4086_PublishAir:
.a16
.i16
 lda.l SourceGravityAir4086_View
 tax
 lda.l SourceGravityAir4086_Position
 sta.l SOURCE_WORLD_POOL+12,x
 lda.l SourceGravityAir4086_Position+2
 sta.l SOURCE_WORLD_POOL+14,x
 lda.l SourceGravityAir4086_Side
 tax
 lda.l SourceGravityAir4086_Velocity
 sta.l SOURCE_WORLD_SIDES+44,x
 lda.l SourceGravityAir4086_Velocity+2
 sta.l SOURCE_WORLD_SIDES+46,x
 lda.l SourceGravityAir4086_PhysicsOffset
 tax
 lda #0
 sta.l SOURCE_ENTITY_PHYSICS+4,x
 sta.l SOURCE_ENTITY_PHYSICS+6,x
 lda.l SourceGravityAir4086_LandingNeeded
 beq SourceGravityAir4086_TimerDone
 lda #1
 sta.l SourceGravityAir4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceGravityAir4086_TimerDone:
.a16
.i16
 lda.l SourceWorldTick4086_Slot
 asl a
 asl a
 tax
 lda.l VmSourceWorld_Time
 clc
 adc #1
 sta.l SOURCE_WORLD_TOSS_TIMES,x
 lda.l VmSourceWorld_Time+2
 adc #0
 sta.l SOURCE_WORLD_TOSS_TIMES+2,x
SourceGravityAir4086_MarkDone:
.a16
.i16
 lda.l SourceGravityAir4086_Mark
 tax
 lda.l SOURCE_WORLD_FREEZE+36,x
 ora #8
 sta.l SOURCE_WORLD_FREEZE+36,x
SourceGravityAir4086_Done:
.a16
.i16
 lda #2
 sta.l SourceGravityAir4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceGravityAir4086_RollbackBad:
.a16
.i16
 lda.l SourceGravityAir4086_Side
 tax
 lda.l SourceGravityAir4086_OriginalBase
 sta.l SOURCE_WORLD_SIDES+48,x
 lda.l SourceGravityAir4086_OriginalBase+2
 sta.l SOURCE_WORLD_SIDES+50,x
 lda.l SourceGravityAir4086_OriginalVx
 sta.l SOURCE_WORLD_SIDES+36,x
 lda.l SourceGravityAir4086_OriginalVx+2
 sta.l SOURCE_WORLD_SIDES+38,x
 lda.l SourceGravityAir4086_OriginalVz
 sta.l SOURCE_WORLD_SIDES+40,x
 lda.l SourceGravityAir4086_OriginalVz+2
 sta.l SOURCE_WORLD_SIDES+42,x
SourceGravityAir4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceGravityAir4086_Status
 ply
 plx
 plp
 sec
 rtl
