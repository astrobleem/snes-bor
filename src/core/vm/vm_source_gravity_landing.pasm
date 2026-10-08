; B627 actual landing continuation after the native velocity phase.
; State1 retains world ownership while update_frame runs actual scripts/effects.
; External bounce effects, land dust and positive landing damage remain required
; services: $8103/$8104/$8102 respectively. Never synthesize their completion.
; State2 alone commits source toss timer/update_mark and AIR completion.
; Reserved $43FDA0..$43FDC7: beyond global freeze/role state ending$43FD9C.
SourceGravityLanding4086_Ready = $43FDA0
SourceGravityLanding4086_State = $43FDA2
SourceGravityLanding4086_Slot = $43FDA4
SourceGravityLanding4086_Service = $43FDA6
SourceGravityLanding4086_Frame = $43FDA8
SourceGravityLanding4086_Model = $43FDAA
SourceGravityLanding4086_Handle = $43FDAC
SourceGravityLanding4086_Count = $43FDAE
SourceGravityLanding4086_Time = $43FDB0
SourceGravityLanding4086_View = $43FDB4
SourceGravityLanding4086_Side = $43FDB6
SourceGravityLanding4086_Aux = $43FDB8
SourceGravityLanding4086_Mark = $43FDBA
SourceGravityLanding4086_Physics = $43FDBC
SourceGravityLanding4086_OldSelf = $43FDBE
SourceGravityLanding4086_Token = $43FDC2
SourceGravityLanding4086_Temp = $43FDC6
SourceGravityLanding4086_End = $43FDC8
SourceGravityLanding4086_Begin:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceGravityLanding4086_Ready
 cmp #$B627
 beq SourceGravityLanding4086_Lease
 jmp SourceGravityLanding4086_Bad
SourceGravityLanding4086_Lease:
.a16
.i16
 lda.l SourceGravityLanding4086_State
 beq SourceGravityLanding4086_Idle
 jmp SourceGravityLanding4086_Bad
SourceGravityLanding4086_Idle:
.a16
.i16
 lda.l SourceGravityAir4086_Ready
 cmp #$B621
 beq SourceGravityLanding4086_AirLease
 jmp SourceGravityLanding4086_Bad
SourceGravityLanding4086_AirLease:
.a16
.i16
 lda.l SourceGravityAir4086_Status
 cmp #1
 beq SourceGravityLanding4086_AirPending
 jmp SourceGravityLanding4086_Bad
SourceGravityLanding4086_AirPending:
.a16
.i16
 lda.l SourceGravityAir4086_LandingNeeded
 cmp #1
 beq SourceGravityLanding4086_LandingPending
 jmp SourceGravityLanding4086_Bad
SourceGravityLanding4086_LandingPending:
.a16
.i16
 lda.l SourceLandingVelocity4086_Ready
 cmp #$B626
 beq SourceGravityLanding4086_VelocityLease
 jmp SourceGravityLanding4086_Bad
SourceGravityLanding4086_VelocityLease:
.a16
.i16
 lda.l SourceGravityLanding4086_Slot
 cmp.l SourceLandingVelocity4086_Slot
 beq SourceGravityLanding4086_SlotMatches
 jmp SourceGravityLanding4086_Bad
SourceGravityLanding4086_SlotMatches:
.a16
.i16
 jsr SourceGravityLanding4086_Context
 bcc SourceGravityLanding4086_ContextGood
 jmp SourceGravityLanding4086_Bad
SourceGravityLanding4086_ContextGood:
.a16
.i16
 lda #0
 sta.l SourceGravityLanding4086_Service
 lda.l VmSourceWorld_Time
 sta.l SourceGravityLanding4086_Time
 lda.l VmSourceWorld_Time+2
 sta.l SourceGravityLanding4086_Time+2
 lda.l SourceLandingVelocity4086_Status
 cmp #2
 beq SourceGravityLanding4086_VelocityComplete
 cmp #1
 beq SourceGravityLanding4086_BounceEffects
 jmp SourceGravityLanding4086_Bad
SourceGravityLanding4086_BounceEffects:
.a16
.i16
 lda #3
 sta.l SourceGravityLanding4086_Service
 lda #1
 sta.l SourceGravityLanding4086_State
 jmp SourceGravityLanding4086_BouncePending
SourceGravityLanding4086_VelocityComplete:
.a16
.i16
 jsr SourceGravityLanding4086_CurrentPhysics
 bcc SourceGravityLanding4086_PhysicsGood
 jmp SourceGravityLanding4086_Bad
SourceGravityLanding4086_PhysicsGood:
.a16
.i16
 lda.l SourceAnimationPhysics4086_LandFrame+2
 beq SourceGravityLanding4086_LandFrameHighZero
 jmp SourceGravityLanding4086_Damage
SourceGravityLanding4086_LandFrameHighZero:
.a16
.i16
 lda.l SourceAnimationPhysics4086_LandFrame
 cmp.l SourceAnimationPhysics4086_Count
 beq SourceGravityLanding4086_FrameInRange
 bcc SourceGravityLanding4086_FrameInRange
 jmp SourceGravityLanding4086_Damage
SourceGravityLanding4086_FrameInRange:
.a16
.i16
 sta.l SourceGravityLanding4086_Frame
 lda.l SourceAnimationPhysics4086_Frame
 cmp.l SourceGravityLanding4086_Frame
 bcc SourceGravityLanding4086_FrameNeeded
 jmp SourceGravityLanding4086_Damage
SourceGravityLanding4086_FrameNeeded:
.a16
.i16
 lda.l SourceAnimationPhysics4086_LandEntity+2
 bmi SourceGravityLanding4086_FrameWithoutDust
 lda #4
 sta.l SourceGravityLanding4086_Service
 lda #$8104
 jmp SourceGravityLanding4086_Pending
SourceGravityLanding4086_FrameWithoutDust:
.a16
.i16
 lda.l SourceGravityLanding4086_Slot
 sta.l SourceUpdateFrame4086_Slot
 lda.l SourceGravityLanding4086_Frame
 sta.l SourceUpdateFrame4086_Request
 lda #1
 sta.l SourceGravityLanding4086_Service
 sta.l SourceGravityLanding4086_State
 jsl SourceUpdateFrame4086_Begin
 bcc SourceGravityLanding4086_FrameStarted
 jmp SourceGravityLanding4086_Bad
SourceGravityLanding4086_FrameStarted:
.a16
.i16
 lda.l SourceUpdateFrame4086_Count
 cmp.l SourceGravityLanding4086_Count
 beq SourceGravityLanding4086_FrameCountMatches
 jmp SourceGravityLanding4086_Bad
SourceGravityLanding4086_FrameCountMatches:
.a16
.i16
 jmp SourceGravityLanding4086_RunFrame
SourceGravityLanding4086_Continue:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceGravityLanding4086_Ready
 cmp #$B627
 beq SourceGravityLanding4086_ContinueLease
 jmp SourceGravityLanding4086_Bad
SourceGravityLanding4086_ContinueLease:
.a16
.i16
 lda.l SourceGravityLanding4086_State
 cmp #1
 beq SourceGravityLanding4086_ContinuePending
 jmp SourceGravityLanding4086_Bad
SourceGravityLanding4086_ContinuePending:
.a16
.i16
 jsr SourceGravityLanding4086_Context
 bcc SourceGravityLanding4086_ContinueContext
 jmp SourceGravityLanding4086_Bad
SourceGravityLanding4086_ContinueContext:
.a16
.i16
 lda.l VmSourceWorld_Time
 cmp.l SourceGravityLanding4086_Time
 beq SourceGravityLanding4086_TimeLowMatches
 jmp SourceGravityLanding4086_Bad
SourceGravityLanding4086_TimeLowMatches:
.a16
.i16
 lda.l VmSourceWorld_Time+2
 cmp.l SourceGravityLanding4086_Time+2
 beq SourceGravityLanding4086_TimeMatches
 jmp SourceGravityLanding4086_Bad
SourceGravityLanding4086_TimeMatches:
.a16
.i16
 lda.l SourceGravityLanding4086_Service
 cmp #1
 beq SourceGravityLanding4086_RunFrame
 ; Required external services have no native completion backend here.
 cmp #2
 beq SourceGravityLanding4086_DamagePending
 cmp #3
 beq SourceGravityLanding4086_BouncePending
 cmp #4
 beq SourceGravityLanding4086_DustPending
 jmp SourceGravityLanding4086_Bad
SourceGravityLanding4086_DamagePending:
.a16
.i16
 jmp SourceGravityLanding4086_LiveDamage
SourceGravityLanding4086_BouncePending:
.a16
.i16
 lda.l SourceBounceEffects4086_Ready
 beq SourceGravityLanding4086_BounceUnbound
 cmp #$B62C
 beq SourceGravityLanding4086_BounceBound
 jmp SourceGravityLanding4086_Bad
SourceGravityLanding4086_BounceBound:
.a16
.i16
 jsl SourceBounceEffects4086_Execute
 bcc SourceGravityLanding4086_BounceProgress
 jmp SourceGravityLanding4086_Bad
SourceGravityLanding4086_BounceProgress:
.a16
.i16
 cmp #0
 beq SourceGravityLanding4086_BounceDone
 jmp SourceGravityLanding4086_Return
SourceGravityLanding4086_BounceDone:
.a16
.i16
 lda #0
 sta.l SourceGravityLanding4086_Service
 jmp SourceGravityLanding4086_VelocityComplete
SourceGravityLanding4086_BounceUnbound:
.a16
.i16
 lda #$8103
 jmp SourceGravityLanding4086_Return
SourceGravityLanding4086_DustPending:
.a16
.i16
 lda #$8104
 jmp SourceGravityLanding4086_Return
SourceGravityLanding4086_RunFrame:
.a16
.i16
 lda.l SourceUpdateFrame4086_Slot
 cmp.l SourceGravityLanding4086_Slot
 beq SourceGravityLanding4086_FrameSlotMatches
 jmp SourceGravityLanding4086_Bad
SourceGravityLanding4086_FrameSlotMatches:
.a16
.i16
 lda.l SourceUpdateFrame4086_Request
 cmp.l SourceGravityLanding4086_Frame
 beq SourceGravityLanding4086_FrameRequestMatches
 jmp SourceGravityLanding4086_Bad
SourceGravityLanding4086_FrameRequestMatches:
.a16
.i16
 jsl SourceFrameOwner4086_Run
 bcc SourceGravityLanding4086_FrameProgress
 jmp SourceGravityLanding4086_Bad
SourceGravityLanding4086_FrameProgress:
.a16
.i16
 cmp #0
 beq SourceGravityLanding4086_FrameDone
 jmp SourceGravityLanding4086_Return
SourceGravityLanding4086_FrameDone:
.a16
.i16
 lda #0
 sta.l SourceGravityLanding4086_Service
SourceGravityLanding4086_Damage:
.a16
.i16
 lda.l SourceGravityLanding4086_Physics
 tax
 lda.l SOURCE_ENTITY_PHYSICS+14,x
 bmi SourceGravityLanding4086_Commit
 bne SourceGravityLanding4086_RequireDamage
 lda.l SOURCE_ENTITY_PHYSICS+12,x
 beq SourceGravityLanding4086_Commit
SourceGravityLanding4086_RequireDamage:
.a16
.i16
 ; Source tests the current entity's canonical dead DWORD after update_frame.
 ; A dead entity keeps damage_on_landing unchanged and skips its handler.
 lda.l SourceGravityLanding4086_View
 tax
 lda.l $439014,x
 ora.l $439016,x
 beq SourceGravityLanding4086_LiveDamage
 lda.l SourceGravityLanding4086_Physics
 tax
 jmp SourceGravityLanding4086_Commit
SourceGravityLanding4086_LiveDamage:
.a16
.i16
 ; Positive landing damage cannot be dropped or treated as a completed callback.
 lda #2
 sta.l SourceGravityLanding4086_Service
 lda #1
 sta.l SourceGravityLanding4086_State
 lda.l SourceLandingDamage4086_Ready
 beq SourceGravityLanding4086_DamageUnbound
 cmp #$B629
 beq SourceGravityLanding4086_DamageBound
 jmp SourceGravityLanding4086_Bad
SourceGravityLanding4086_DamageBound:
.a16
.i16
 jsl SourceLandingDamage4086_Execute
 bcc SourceGravityLanding4086_DamageProgress
 jmp SourceGravityLanding4086_Bad
SourceGravityLanding4086_DamageProgress:
.a16
.i16
 cmp #0
 beq SourceGravityLanding4086_DamageDone
 jmp SourceGravityLanding4086_Return
SourceGravityLanding4086_DamageDone:
.a16
.i16
 lda #0
 sta.l SourceGravityLanding4086_Service
 lda.l SourceGravityLanding4086_Physics
 tax
 jmp SourceGravityLanding4086_Commit
SourceGravityLanding4086_DamageUnbound:
.a16
.i16
 lda #$8102
 jmp SourceGravityLanding4086_Pending
SourceGravityLanding4086_Commit:
.a16
.i16
 lda #0
 sta.l SOURCE_ENTITY_PHYSICS+4,x
 sta.l SOURCE_ENTITY_PHYSICS+6,x
 lda.l SourceGravityLanding4086_Slot
 asl a
 asl a
 tax
 lda.l SOURCE_WORLD_TOSS_TIMES+2,x
 cmp.l VmSourceWorld_Time+2
 bcc SourceGravityLanding4086_TimerDue
 bne SourceGravityLanding4086_TimerDone
 lda.l SOURCE_WORLD_TOSS_TIMES,x
 cmp.l VmSourceWorld_Time
 bcc SourceGravityLanding4086_TimerDue
 bne SourceGravityLanding4086_TimerDone
SourceGravityLanding4086_TimerDue:
.a16
.i16
 lda.l VmSourceWorld_Time
 clc
 adc #1
 sta.l SOURCE_WORLD_TOSS_TIMES,x
 lda.l VmSourceWorld_Time+2
 adc #0
 sta.l SOURCE_WORLD_TOSS_TIMES+2,x
SourceGravityLanding4086_TimerDone:
.a16
.i16
 lda.l SourceGravityLanding4086_Mark
 tax
 lda.l SOURCE_WORLD_FREEZE+36,x
 ora #8
 sta.l SOURCE_WORLD_FREEZE+36,x
 lda #2
 sta.l SourceGravityLanding4086_State
 sta.l SourceGravityAir4086_Status
 lda #0
 sta.l SourceGravityAir4086_LandingNeeded
 jmp SourceGravityLanding4086_Return
SourceGravityLanding4086_Pending:
.a16
.i16
 pha
 lda #1
 sta.l SourceGravityLanding4086_State
 pla
SourceGravityLanding4086_Return:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
SourceGravityLanding4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceGravityLanding4086_State
 ply
 plx
 plp
 sec
 rtl

; Scalar current actor metadata; no mutation of actor, frame owner or self.
SourceGravityLanding4086_CurrentPhysics:
.a16
.i16
 lda.l SourceGravityLanding4086_Side
 tax
 lda.l SOURCE_WORLD_SIDES,x
 sta.l SourceGravityLanding4086_Model
 sta.l SourceLandingPlan4086_Model
 lda.l SOURCE_WORLD_SIDES+4,x
 sta.l SourceGravityLanding4086_Handle
 sta.l SourceLandingPlan4086_Handle
 sta.l SourceAnimationPhysics4086_Handle
 lda.l SOURCE_WORLD_SIDES+6,x
 sta.l SourceAnimationPhysics4086_Frame
 lda #0
 sta.l SourceLandingPlan4086_Status
 sta.l SourceAnimationPhysics4086_Status
 jsl SourceLandingPlan4086_Query
 bcs SourceGravityLanding4086_QueryReturn
 jsl SourceAnimationPhysics4086_Query
 bcs SourceGravityLanding4086_QueryReturn
 lda.l SourceAnimationPhysics4086_Count
 sta.l SourceGravityLanding4086_Count
 clc
SourceGravityLanding4086_QueryReturn:
.a16
.i16
 rts

; Preserve retained parent self while a real frame owns SourceSelf's snapshot.
; During frame callback yield global self is legitimately owned by that frame.
SourceGravityLanding4086_Context:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceGravityLanding4086_ContextWorld
 jmp SourceGravityLanding4086_ContextBad
SourceGravityLanding4086_ContextWorld:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourceGravityLanding4086_ContextPool
 jmp SourceGravityLanding4086_ContextBad
SourceGravityLanding4086_ContextPool:
.a16
.i16
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 beq SourceGravityLanding4086_ContextSide
 jmp SourceGravityLanding4086_ContextBad
SourceGravityLanding4086_ContextSide:
.a16
.i16
 lda.l SourceGravityAir4086_Ready
 cmp #$B621
 beq SourceGravityLanding4086_ContextAir
 jmp SourceGravityLanding4086_ContextBad
SourceGravityLanding4086_ContextAir:
.a16
.i16
 lda.l SourceGravityAir4086_Status
 cmp #1
 beq SourceGravityLanding4086_ContextAirPending
 jmp SourceGravityLanding4086_ContextBad
SourceGravityLanding4086_ContextAirPending:
.a16
.i16
 lda.l SourceGravityAir4086_LandingNeeded
 cmp #1
 beq SourceGravityLanding4086_ContextLanding
 jmp SourceGravityLanding4086_ContextBad
SourceGravityLanding4086_ContextLanding:
.a16
.i16
 lda.l SourceWorldTick4086_TimeLo
 cmp.l VmSourceWorld_Time
 beq SourceGravityLanding4086_ContextTimeLow
 jmp SourceGravityLanding4086_ContextBad
SourceGravityLanding4086_ContextTimeLow:
.a16
.i16
 lda.l SourceWorldTick4086_TimeHi
 cmp.l VmSourceWorld_Time+2
 beq SourceGravityLanding4086_ContextTime
 jmp SourceGravityLanding4086_ContextBad
SourceGravityLanding4086_ContextTime:
.a16
.i16
 lda.l VmSourceWorld_Count
 cmp #129
 bcc SourceGravityLanding4086_ContextCount
 jmp SourceGravityLanding4086_ContextBad
SourceGravityLanding4086_ContextCount:
.a16
.i16
 lda.l SourceGravityLanding4086_Slot
 cmp.l VmSourceWorld_Count
 bcs SourceGravityLanding4086_ContextBad
 cmp.l SourceWorldTick4086_Slot
 bne SourceGravityLanding4086_ContextBad
 lda.l SourceWorldTick4086_Ready
 cmp #$B4D5
 bne SourceGravityLanding4086_ContextBad
 lda.l SourceWorldTick4086_State
 cmp #2
 bne SourceGravityLanding4086_ContextBad
 lda.l SourceWorldTick4086_Phase
 cmp #11
 bne SourceGravityLanding4086_ContextBad
 lda.l SourceWorldTick4086_Pending
 cmp #1
 bne SourceGravityLanding4086_ContextBad
 lda.l SourceWorldTick4086_Fault
 bne SourceGravityLanding4086_ContextBad
 lda.l SourcePhysicsState4086_Ready
 cmp #$B61C
 bne SourceGravityLanding4086_ContextBad
 lda.l SourceGravityLanding4086_Slot
 asl a
 asl a
 asl a
 asl a
 sta.l SourceGravityLanding4086_Physics
 sta.l SourceGravityLanding4086_View
 asl a
 asl a
 sta.l SourceGravityLanding4086_Side
 clc
 adc.l SourceGravityLanding4086_View
 sta.l SourceGravityLanding4086_View
 lda.l SourceGravityLanding4086_Physics
 lsr a
 lsr a
 clc
 adc.l SourceGravityLanding4086_Physics
 sta.l SourceGravityLanding4086_Aux
 lda.l SourceGravityLanding4086_Physics
 asl a
 sta.l SourceGravityLanding4086_Mark
 lsr a
 lsr a
 clc
 adc.l SourceGravityLanding4086_Mark
 sta.l SourceGravityLanding4086_Mark
 clc
 rts
SourceGravityLanding4086_ContextBad:
.a16
.i16
 sec
 rts
