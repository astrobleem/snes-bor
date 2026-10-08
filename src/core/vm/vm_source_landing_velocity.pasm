; B626 landing velocity phase, immutable no-fall-dust registry contract.
; Executes source snap/falling/bounce/toss/quake. Status1 retains ownership for
; actual bounce sound/rumble; Status2 completes velocity phase only. No POST Ack.
; Shared AIR scratch stays exclusively owned until whole gravity completes.
SourceLandingVelocity4086_Ready = $41FFEE
SourceLandingVelocity4086_Status = $41FFF0
SourceLandingVelocity4086_Autoland = $41FFF2
SourceLandingVelocity4086_Slot = $41FFF4
SourceLandingVelocity4086_Bounced = $41FFF6
SourceLandingVelocity4086_End = $41FFF8
SourceLandingVelocity4086_View = SourceGravityAir4086_View
SourceLandingVelocity4086_Side = SourceGravityAir4086_Side
SourceLandingVelocity4086_Aux = SourceGravityAir4086_Aux
SourceLandingVelocity4086_Mark = SourceGravityAir4086_Mark
SourceLandingVelocity4086_Core = SourceGravityAir4086_Core
SourceLandingVelocity4086_Due = SourceGravityAir4086_Due
SourceLandingVelocity4086_StageReady = SourceGravityAir4086_StageReady
SourceLandingVelocity4086_StageId = SourceGravityAir4086_StageId
SourceLandingVelocity4086_Gravity = SourceGravityAir4086_Gravity
SourceLandingVelocity4086_MinFall = SourceGravityAir4086_MinFall
SourceLandingVelocity4086_MaxToss = SourceGravityAir4086_MaxToss
SourceLandingVelocity4086_ZeroProfileReady = SourceGravityAir4086_ZeroProfileReady
SourceLandingVelocity4086_ZeroModels = SourceGravityAir4086_ZeroModels
SourceLandingVelocity4086_Position = SourceGravityAir4086_Position
SourceLandingVelocity4086_Velocity = SourceGravityAir4086_Velocity
SourceLandingVelocity4086_Base = SourceGravityAir4086_Base
SourceLandingVelocity4086_Delta = SourceGravityAir4086_Delta
SourceLandingVelocity4086_Temp = SourceGravityAir4086_Temp
SourceLandingVelocity4086_OriginalBase = SourceGravityAir4086_OriginalBase
SourceLandingVelocity4086_OriginalVx = SourceGravityAir4086_OriginalVx
SourceLandingVelocity4086_OriginalVz = SourceGravityAir4086_OriginalVz
SourceLandingVelocity4086_PhysicsOffset = SourceGravityAir4086_PhysicsOffset
SourceLandingVelocity4086_LandingNeeded = SourceGravityAir4086_LandingNeeded
SourceLandingVelocity4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceGravityAir4086_Ready
 cmp #$B621
 bne SourceLandingVelocity4086_EntryBad
 lda.l SourceGravityAir4086_Status
 cmp #1
 bne SourceLandingVelocity4086_EntryBad
 lda.l SourceGravityAir4086_LandingNeeded
 cmp #1
 beq SourceLandingVelocity4086_PendingAir
SourceLandingVelocity4086_EntryBad:
.a16
.i16
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_PendingAir:
.a16
.i16
 lda.l SourceLandingVelocity4086_Ready
 cmp #$B626
 beq SourceLandingVelocity4086_Guard1
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_Guard1:
.a16
.i16
 lda.l SourceLandingVelocity4086_Status
 cmp #0
 beq SourceLandingVelocity4086_Guard2
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_Guard2:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceLandingVelocity4086_Guard3
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_Guard3:
.a16
.i16
 lda.l SourceWorldTick4086_Ready
 cmp #$B4D5
 beq SourceLandingVelocity4086_Guard4
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_Guard4:
.a16
.i16
 lda.l SourceWorldTick4086_State
 cmp #2 ; actual arrange_ents POST_UPDATE owner
 beq SourceLandingVelocity4086_Guard5
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_Guard5:
.a16
.i16
 lda.l SourceWorldTick4086_Phase
 cmp #11
 beq SourceLandingVelocity4086_Guard6
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_Guard6:
.a16
.i16
 lda.l SourceWorldTick4086_Pending
 cmp #1
 beq SourceLandingVelocity4086_Guard7
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_Guard7:
.a16
.i16
 lda.l SourceWorldTick4086_Fault
 cmp #0
 beq SourceLandingVelocity4086_Guard8
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_Guard8:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourceLandingVelocity4086_Guard9
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_Guard9:
.a16
.i16
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 beq SourceLandingVelocity4086_Guard10
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_Guard10:
.a16
.i16
 lda.l SourceUpdateFrame4086_Ready
 cmp #$B4E3
 beq SourceLandingVelocity4086_Guard11
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_Guard11:
.a16
.i16
 lda.l SourceFreeze4086_Ready
 cmp #$B5DF
 beq SourceLandingVelocity4086_FreezeLease
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_FreezeLease:
.a16
.i16
 lda.l SourceLifecycle4086_Ready
 cmp #$B4FB
 beq SourceLandingVelocity4086_Guard12
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_Guard12:
.a16
.i16
 lda.l SourceSelf4086_Ready
 cmp #$B4F6
 beq SourceLandingVelocity4086_Guard13
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_Guard13:
.a16
.i16
 lda.l SourceSelf4086_Active
 cmp #0
 beq SourceLandingVelocity4086_Guard14
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_Guard14:
.a16
.i16
 lda.l SourceSelf4086_Fault
 cmp #0
 beq SourceLandingVelocity4086_Guard15
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_Guard15:
.a16
.i16
 lda.l SourceWorldTick4086_TimeLo
 cmp.l VmSourceWorld_Time
 beq SourceLandingVelocity4086_Guard16
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_Guard16:
.a16
.i16
 lda.l SourceWorldTick4086_TimeLo+2
 cmp.l VmSourceWorld_Time+2
 beq SourceLandingVelocity4086_Guard17
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_Guard17:
.a16
.i16
 lda.l VmSourceWorld_Count
 cmp #129
 bcc SourceLandingVelocity4086_Guard18
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_Guard18:
.a16
.i16
 lda.l SourceWorldTick4086_Slot
 cmp.l VmSourceWorld_Count
 bcc SourceLandingVelocity4086_Guard19
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_Guard19:
.a16
.i16
 asl a
 asl a
 sta.l SourceLandingVelocity4086_Aux
 asl a
 asl a
 clc
 adc.l SourceLandingVelocity4086_Aux
 sta.l SourceLandingVelocity4086_Aux
 lda.l SourceWorldTick4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l SourceLandingVelocity4086_Mark
 asl a
 sta.l SourceLandingVelocity4086_Side
 lsr a
 lsr a
 clc
 adc.l SourceLandingVelocity4086_Side
 sta.l SourceLandingVelocity4086_View
 adc #$4000
 cmp.l SourceSelf4086_GlobalLow
 beq SourceLandingVelocity4086_Guard20
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_Guard20:
.a16
.i16
 lda.l SourceSelf4086_GlobalHigh
 cmp #$41
 beq SourceLandingVelocity4086_Guard21
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_Guard21:
.a16
.i16
 lda.l SourceLandingVelocity4086_View
 tax
 lda.l SOURCE_WORLD_POOL,x
 clc
 adc #0
 cmp.l SourceSelf4086_GlobalLow
 beq SourceLandingVelocity4086_Guard22
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_Guard22:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+2,x
 cmp #$41
 beq SourceLandingVelocity4086_Guard23
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_Guard23:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+4,x
 ora.l SOURCE_WORLD_POOL+6,x
 bne SourceLandingVelocity4086_Guard24
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_Guard24:
.a16
.i16
 lda.l SourceLandingVelocity4086_Mark
 lsr a
 lsr a
 clc
 adc.l SourceLandingVelocity4086_Mark
 sta.l SourceLandingVelocity4086_Mark
 tax
 lda.l SOURCE_WORLD_FREEZE+36,x
 and #8
 beq SourceLandingVelocity4086_First
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_First:
.a16
.i16
 lda.l SourceLandingVelocity4086_Side
 tax
 lda.l SOURCE_WORLD_SIDES,x
 cmp.l SourceEmptyInitEnvironment4086_Models
 bcc SourceLandingVelocity4086_ModelRange
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_ModelRange:
.a16
.i16
 pha
 lda.l SourceLandingVelocity4086_View
 tax
 pla
 cmp.l $439048,x
 beq SourceLandingVelocity4086_ModelIdentity
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_ModelIdentity:
.a16
.i16
 lda.l $43904A,x
 cmp #$B4FB
 beq SourceLandingVelocity4086_ModelLease
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_ModelLease:
.a16
.i16
 lda.l SourceLandingVelocity4086_ZeroProfileReady
 cmp #$B622
 beq SourceLandingVelocity4086_ExtraGuard1
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_ExtraGuard1:
.a16
.i16
 lda.l SourceLandingVelocity4086_ZeroModels
 cmp.l SourceEmptyInitEnvironment4086_Models
 beq SourceLandingVelocity4086_ExtraGuard2
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_ExtraGuard2:
.a16
.i16
 lda.l SourcePhysicsState4086_Ready
 cmp #$B61C
 beq SourceLandingVelocity4086_ExtraGuard3
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_ExtraGuard3:
.a16
.i16
 lda.l SourceAdjustBaseEmpty4086_Ready
 cmp #$B620
 beq SourceLandingVelocity4086_ExtraGuard4
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_ExtraGuard4:
.a16
.i16
 lda.l SourceLandingVelocity4086_StageReady
 cmp #$B623
 beq SourceLandingVelocity4086_ExtraGuard5
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_ExtraGuard5:
.a16
.i16
 lda.l SourceLandingVelocity4086_StageId
 cmp.l SourceEnvironment4086_Stage
 beq SourceLandingVelocity4086_ExtraGuard6
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_ExtraGuard6:
.a16
.i16
 lda.l SourceToss4086_Ready
 cmp #$B4E2
 beq SourceLandingVelocity4086_ExtraGuard7
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_ExtraGuard7:
.a16
.i16
 lda.l SourceLandingVelocity4086_MinFall+2
 eor #$8000
 sta.l SourceLandingVelocity4086_Temp
 lda.l SourceLandingVelocity4086_MaxToss+2
 eor #$8000
 cmp.l SourceLandingVelocity4086_Temp
 bne SourceLandingVelocity4086_BoundsHigh
 lda.l SourceLandingVelocity4086_MaxToss
 cmp.l SourceLandingVelocity4086_MinFall
SourceLandingVelocity4086_BoundsHigh:
.a16
.i16
 bcs SourceLandingVelocity4086_ExtraGuard8
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_ExtraGuard8:
.a16
.i16
 lda.l SourceLandingVelocity4086_Slot
 cmp.l SourceWorldTick4086_Slot
 beq SourceLandingVelocity4086_LandingGuard1
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_LandingGuard1:
.a16
.i16
 lda.l SourceLandingVelocity4086_Side
 tax
 lda.l SOURCE_WORLD_SIDES,x
 sta.l SourceLandingPlan4086_Model
 lda.l SOURCE_WORLD_SIDES+4,x
 sta.l SourceLandingPlan4086_Handle
 sta.l SourceAnimationPhysics4086_Handle
 lda.l SOURCE_WORLD_SIDES+6,x
 sta.l SourceAnimationPhysics4086_Frame
 lda #0
 sta.l SourceLandingPlan4086_Status
 sta.l SourceAnimationPhysics4086_Status
 jsl SourceLandingPlan4086_Query

 bcc SourceLandingVelocity4086_LandingGuard2
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_LandingGuard2:
.a16
.i16
 jsl SourceAnimationPhysics4086_Query

 bcc SourceLandingVelocity4086_LandingGuard3
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_LandingGuard3:
.a16
.i16
 lda.l SourceLandingVelocity4086_Slot
 asl a
 asl a
 asl a
 asl a
 sta.l SourceLandingVelocity4086_PhysicsOffset
 tax
 lda.l SOURCE_ENTITY_PHYSICS+8,x
 ora.l SOURCE_ENTITY_PHYSICS+10,x
 beq SourceLandingVelocity4086_LandingGuard4
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_LandingGuard4:
.a16
.i16
 lda.l SourceLandingVelocity4086_View
 tax
 lda.l SOURCE_WORLD_POOL+8,x
 cmp #BOR_VT_DECIMAL
 beq SourceLandingVelocity4086_AltitudeTag
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_AltitudeTag:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+10,x
 beq SourceLandingVelocity4086_AltitudeTagHigh
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_AltitudeTagHigh:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+12,x
 cmp.l SourceLandingVelocity4086_Position
 beq SourceLandingVelocity4086_LandingGuard5
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_LandingGuard5:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+14,x
 cmp.l SourceLandingVelocity4086_Position+2
 beq SourceLandingVelocity4086_LandingGuard6
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_LandingGuard6:
.a16
.i16
 lda.l SourceLandingVelocity4086_Side
 tax
 lda.l SOURCE_WORLD_SIDES+44,x
 cmp.l SourceLandingVelocity4086_Velocity
 beq SourceLandingVelocity4086_LandingGuard7
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_LandingGuard7:
.a16
.i16
 lda.l SOURCE_WORLD_SIDES+46,x
 cmp.l SourceLandingVelocity4086_Velocity+2
 beq SourceLandingVelocity4086_LandingGuard8
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_LandingGuard8:
.a16
.i16
 lda.l SOURCE_WORLD_SIDES+48,x
 cmp.l SourceLandingVelocity4086_Base
 beq SourceLandingVelocity4086_LandingGuard9
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_LandingGuard9:
.a16
.i16
 lda.l SOURCE_WORLD_SIDES+50,x
 cmp.l SourceLandingVelocity4086_Base+2
 beq SourceLandingVelocity4086_LandingGuard10
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_LandingGuard10:
.a16
.i16
 lda.l SourceLandingVelocity4086_Velocity+2
 bmi SourceLandingVelocity4086_Descending
 ora.l SourceLandingVelocity4086_Velocity
 beq SourceLandingVelocity4086_LandingGuard11
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_LandingGuard11:
.a16
.i16
SourceLandingVelocity4086_Descending:
.a16
.i16
 lda.l SOURCE_WORLD_SIDES+36,x
 sta.l SourceLandingVelocity4086_OriginalVx
 lda.l SOURCE_WORLD_SIDES+38,x
 sta.l SourceLandingVelocity4086_OriginalVx+2
 lda.l SOURCE_WORLD_SIDES+40,x
 sta.l SourceLandingVelocity4086_OriginalVz
 lda.l SOURCE_WORLD_SIDES+42,x
 sta.l SourceLandingVelocity4086_OriginalVz+2
 lda #0
 sta.l SourceLandingVelocity4086_Bounced
 lda.l SourceLandingPlan4086_Bounce+2
 and #$7FFF
 ora.l SourceLandingPlan4086_Bounce
 bne SourceLandingVelocity4086_FactorNonzero
 jmp SourceLandingVelocity4086_NoBounce
SourceLandingVelocity4086_FactorNonzero:
.a16
.i16
 lda.l SourceLandingPlan4086_ModelBounce
 ora.l SourceLandingPlan4086_ModelBounce+2
 bne SourceLandingVelocity4086_ModelBounces
 jmp SourceLandingVelocity4086_NoBounce
SourceLandingVelocity4086_ModelBounces:
.a16
.i16
 lda.l SourceLandingVelocity4086_PhysicsOffset
 tax
 lda.l SOURCE_ENTITY_PHYSICS+14,x
 cmp #$FFFF
 bne SourceLandingVelocity4086_DamageAllowsBounce
 lda.l SOURCE_ENTITY_PHYSICS+12,x
 cmp #$FFFE
 bne SourceLandingVelocity4086_CheckAutoland
 jmp SourceLandingVelocity4086_NoBounce
SourceLandingVelocity4086_CheckAutoland:
.a16
.i16
 cmp #$FFFF
 bne SourceLandingVelocity4086_DamageAllowsBounce
 lda.l SourceLandingVelocity4086_Autoland
 cmp #1
 bne SourceLandingVelocity4086_DamageAllowsBounce
 jmp SourceLandingVelocity4086_NoBounce
SourceLandingVelocity4086_DamageAllowsBounce:
.a16
.i16
 lda.l SourceLandingVelocity4086_Velocity+2
 bne SourceLandingVelocity4086_NegativeVelocity
 jmp SourceLandingVelocity4086_NoBounce
SourceLandingVelocity4086_NegativeVelocity:
.a16
.i16
 cmp #$FFFE ; -1.5 Q16.16 is $FFFE8000, not $FFFF8000
 bcc SourceLandingVelocity4086_BounceRequired
 beq SourceLandingVelocity4086_CheckThresholdLow
 jmp SourceLandingVelocity4086_NoBounce
SourceLandingVelocity4086_CheckThresholdLow:
.a16
.i16
 lda.l SourceLandingVelocity4086_Velocity
 cmp #$8000
 bcc SourceLandingVelocity4086_BounceRequired
 jmp SourceLandingVelocity4086_NoBounce
SourceLandingVelocity4086_BounceRequired:
.a16
.i16
 lda.l SourceLandingPlan4086_Bounce
 beq SourceLandingVelocity4086_LandingGuard12
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_LandingGuard12:
.a16
.i16
 lda.l SourceLandingPlan4086_Bounce+2
 cmp #$4080
 beq SourceLandingVelocity4086_LandingGuard13
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_LandingGuard13:
.a16
.i16
 lda.l SourceEntityToss4086_Ready
 cmp #$B624
 beq SourceLandingVelocity4086_LandingGuard14
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_LandingGuard14:
.a16
.i16
 lda.l SourceEntityToss4086_Status
 beq SourceLandingVelocity4086_TossIdle
 cmp #2

 beq SourceLandingVelocity4086_LandingGuard15
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_LandingGuard15:
.a16
.i16
SourceLandingVelocity4086_TossIdle:
.a16
.i16
 lda.l SourceLandingVelocity4086_OriginalVx+2
 cmp #$8000
 ror a
 sta.l SourceLandingVelocity4086_OriginalVx+2
 lda.l SourceLandingVelocity4086_OriginalVx
 ror a
 sta.l SourceLandingVelocity4086_OriginalVx
 lda.l SourceLandingVelocity4086_OriginalVx+2
 cmp #$8000
 ror a
 sta.l SourceLandingVelocity4086_OriginalVx+2
 lda.l SourceLandingVelocity4086_OriginalVx
 ror a
 sta.l SourceLandingVelocity4086_OriginalVx
 lda.l SourceLandingVelocity4086_OriginalVz+2
 cmp #$8000
 ror a
 sta.l SourceLandingVelocity4086_OriginalVz+2
 lda.l SourceLandingVelocity4086_OriginalVz
 ror a
 sta.l SourceLandingVelocity4086_OriginalVz
 lda.l SourceLandingVelocity4086_OriginalVz+2
 cmp #$8000
 ror a
 sta.l SourceLandingVelocity4086_OriginalVz+2
 lda.l SourceLandingVelocity4086_OriginalVz
 ror a
 sta.l SourceLandingVelocity4086_OriginalVz
 lda.l SourceLandingVelocity4086_Velocity+2
 cmp #$8000
 ror a
 sta.l SourceLandingVelocity4086_Velocity+2
 lda.l SourceLandingVelocity4086_Velocity
 ror a
 sta.l SourceLandingVelocity4086_Velocity
 lda.l SourceLandingVelocity4086_Velocity+2
 cmp #$8000
 ror a
 sta.l SourceLandingVelocity4086_Velocity+2
 lda.l SourceLandingVelocity4086_Velocity
 ror a
 sta.l SourceLandingVelocity4086_Velocity
 lda #0
 sec
 sbc.l SourceLandingVelocity4086_Velocity
 sta.l SourceLandingVelocity4086_Velocity
 lda #0
 sbc.l SourceLandingVelocity4086_Velocity+2
 sta.l SourceLandingVelocity4086_Velocity+2
 lda.l SourceLandingVelocity4086_Base
 clc
 adc #$8000
 sta.l SourceLandingVelocity4086_Temp
 lda.l SourceLandingVelocity4086_Base+2
 adc #0

 bvc SourceLandingVelocity4086_LandingGuard16
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_LandingGuard16:
.a16
.i16
 lda #1
 sta.l SourceLandingVelocity4086_Bounced
 jmp SourceLandingVelocity4086_Publish
SourceLandingVelocity4086_NoBounce:
.a16
.i16
 lda #0
 sta.l SourceLandingVelocity4086_Velocity
 sta.l SourceLandingVelocity4086_Velocity+2
 lda.l SourceAnimationPhysics4086_FrameBase+2
 bmi SourceLandingVelocity4086_BaseNonpositive
 bne SourceLandingVelocity4086_Publish
 lda.l SourceAnimationPhysics4086_FrameBase
 bne SourceLandingVelocity4086_Publish
SourceLandingVelocity4086_BaseNonpositive:
.a16
.i16
 lda.l SourceAnimationPhysics4086_FrameY+2
 bmi SourceLandingVelocity4086_YNonpositive
 bne SourceLandingVelocity4086_Publish
 lda.l SourceAnimationPhysics4086_FrameY
 bne SourceLandingVelocity4086_Publish
SourceLandingVelocity4086_YNonpositive:
.a16
.i16
 lda #0
 sta.l SourceLandingVelocity4086_OriginalVx
 sta.l SourceLandingVelocity4086_OriginalVx+2
 sta.l SourceLandingVelocity4086_OriginalVz
 sta.l SourceLandingVelocity4086_OriginalVz+2
SourceLandingVelocity4086_Publish:
.a16
.i16
 lda.l SourceLandingVelocity4086_View
 tax
 lda.l SourceLandingVelocity4086_Base
 sta.l SOURCE_WORLD_POOL+12,x
 lda.l SourceLandingVelocity4086_Base+2
 sta.l SOURCE_WORLD_POOL+14,x
 lda.l SourceLandingVelocity4086_PhysicsOffset
 tax
 lda #0
 sta.l SOURCE_ENTITY_PHYSICS,x
 sta.l SOURCE_ENTITY_PHYSICS+2,x
 lda.l SourceLandingVelocity4086_Side
 tax
 lda.l SourceLandingVelocity4086_OriginalVx
 sta.l SOURCE_WORLD_SIDES+36,x
 lda.l SourceLandingVelocity4086_OriginalVx+2
 sta.l SOURCE_WORLD_SIDES+38,x
 lda.l SourceLandingVelocity4086_OriginalVz
 sta.l SOURCE_WORLD_SIDES+40,x
 lda.l SourceLandingVelocity4086_OriginalVz+2
 sta.l SOURCE_WORLD_SIDES+42,x
 lda.l SourceLandingVelocity4086_Bounced
 bne SourceLandingVelocity4086_ExecuteToss
 lda.l SourceLandingVelocity4086_Velocity
 sta.l SOURCE_WORLD_SIDES+44,x
 lda.l SourceLandingVelocity4086_Velocity+2
 sta.l SOURCE_WORLD_SIDES+46,x
 lda #2
 sta.l SourceLandingVelocity4086_Status
 jmp SourceLandingVelocity4086_ReturnGood
SourceLandingVelocity4086_ExecuteToss:
.a16
.i16
 lda.l SourceLandingVelocity4086_Slot
 sta.l SourceEntityToss4086_Slot
 lda.l SourceLandingVelocity4086_Velocity
 sta.l SourceEntityToss4086_Lift
 lda.l SourceLandingVelocity4086_Velocity+2
 sta.l SourceEntityToss4086_Lift+2
 lda #0
 sta.l SourceEntityToss4086_Status
 jsl SourceEntityToss4086_Execute

 bcc SourceLandingVelocity4086_LandingGuard17
 jmp SourceLandingVelocity4086_Bad
SourceLandingVelocity4086_LandingGuard17:
.a16
.i16
 lda.l SourceLandingPlan4086_Noquake
 and #1
 bne SourceLandingVelocity4086_QuakeDone
 lda #4
 sta.l SourceFrameEffectLeaf4086_LevelQuakeLo
 lda #0
 sta.l SourceFrameEffectLeaf4086_LevelQuakeHi
SourceLandingVelocity4086_QuakeDone:
.a16
.i16
 lda #1
 sta.l SourceLandingVelocity4086_Status
SourceLandingVelocity4086_ReturnGood:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
SourceLandingVelocity4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceLandingVelocity4086_Status
 ply
 plx
 plp
 sec
 rtl

