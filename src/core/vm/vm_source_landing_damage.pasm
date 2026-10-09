; B629 source NULL-takedamage, unit-defense, nonlethal landing damage.
; Exact source binary32 domain: positive health and force below 2^23.
; Pending statuses1 callback,4 kill,5 other arithmetic backend. No fake Ack.
; Canonical current life fields: takedamage DWORD+4, dead DWORD+20.
; Requires the immutable uniform factor snapshot and its current model lease.
SourceLandingDamage4086_Ready = $43FDDC
SourceLandingDamage4086_Status = $43FDDE
SourceLandingDamage4086_Slot = $43FDE0
SourceLandingDamage4086_View = $43FDE2
SourceLandingDamage4086_Physics = $43FDE4
SourceLandingDamage4086_Model = $43FDE6
SourceLandingDamage4086_Force = $43FDE8
SourceLandingDamage4086_Result = $43FDEC
SourceLandingDamage4086_End = $43FDF0
SourceLandingDamage4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceLandingDamage4086_Ready
 cmp #$B629
 beq SourceLandingDamage4086_Lease
 jmp SourceLandingDamage4086_Bad
SourceLandingDamage4086_Lease:
.a16
.i16
 lda.l SourceGravityLanding4086_State
 cmp #1
 beq SourceLandingDamage4086_GravityOwned
 jmp SourceLandingDamage4086_Bad
SourceLandingDamage4086_GravityOwned:
.a16
.i16
 lda.l SourceGravityLanding4086_Service
 cmp #2
 beq SourceLandingDamage4086_ServiceOwned
 jmp SourceLandingDamage4086_Bad
SourceLandingDamage4086_ServiceOwned:
.a16
.i16
 lda.l SourceLandingDamage4086_Slot
 cmp.l SourceGravityLanding4086_Slot
 beq SourceLandingDamage4086_SlotMatches
 jmp SourceLandingDamage4086_Bad
SourceLandingDamage4086_SlotMatches:
.a16
.i16
 cmp.l SourceWorldTick4086_Slot
 beq SourceLandingDamage4086_WorldSlot
 jmp SourceLandingDamage4086_Bad
SourceLandingDamage4086_WorldSlot:
.a16
.i16
 lda.l SourceLandingDamage4086_Status
 cmp #3
 bne SourceLandingDamage4086_NotFaulted
 jmp SourceLandingDamage4086_Bad
SourceLandingDamage4086_NotFaulted:
.a16
.i16
 ; Revalidate physical actor/time and pending gravity at every service call.
 jsr SourceGravityLanding4086_Context
 bcc SourceLandingDamage4086_ContextGood
 jmp SourceLandingDamage4086_Bad
SourceLandingDamage4086_ContextGood:
.a16
.i16
 lda.l SourceSelf4086_Ready
 cmp #$B4F6
 beq SourceLandingDamage4086_SelfReady
 jmp SourceLandingDamage4086_Bad
SourceLandingDamage4086_SelfReady:
.a16
.i16
 jsl SourceSelf4086_CheckIdle
 bcc SourceLandingDamage4086_SelfIdle
 jmp SourceLandingDamage4086_Bad
SourceLandingDamage4086_SelfIdle:
.a16
.i16
 lda.l SourceGravityLanding4086_View
 sta.l SourceLandingDamage4086_View
 clc
 adc #$4000
 cmp.l SourceSelf4086_GlobalLow
 beq SourceLandingDamage4086_SelfLow
 jmp SourceLandingDamage4086_Bad
SourceLandingDamage4086_SelfLow:
.a16
.i16
 lda.l SourceSelf4086_GlobalHigh
 cmp #$41
 beq SourceLandingDamage4086_SelfHigh
 jmp SourceLandingDamage4086_Bad
SourceLandingDamage4086_SelfHigh:
.a16
.i16
 lda.l SourceLifecycle4086_Ready
 cmp #$B4FB
 beq SourceLandingDamage4086_LifeReady
 jmp SourceLandingDamage4086_Bad
SourceLandingDamage4086_LifeReady:
.a16
.i16
 lda.l SourceLandingDamage4086_View
 tax
 lda.l $43904A,x
 cmp #$B4FB
 beq SourceLandingDamage4086_LifeOwned
 jmp SourceLandingDamage4086_Bad
SourceLandingDamage4086_LifeOwned:
.a16
.i16
 lda.l $439048,x
 sta.l SourceLandingDamage4086_Model
 lda.l $439014,x
 ora.l $439016,x
 beq SourceLandingDamage4086_Live
 jmp SourceLandingDamage4086_Complete
SourceLandingDamage4086_Live:
.a16
.i16
 lda.l SourceGravityLanding4086_Side
 tax
 lda.l SOURCE_WORLD_SIDES,x
 cmp.l SourceLandingDamage4086_Model
 beq SourceLandingDamage4086_ModelMatches
 jmp SourceLandingDamage4086_Bad
SourceLandingDamage4086_ModelMatches:
.a16
.i16
 lda.l SourceGravityLanding4086_Physics
 sta.l SourceLandingDamage4086_Physics
 tax
 lda.l SOURCE_ENTITY_PHYSICS+12,x
 sta.l SourceLandingDamage4086_Force
 lda.l SOURCE_ENTITY_PHYSICS+14,x
 sta.l SourceLandingDamage4086_Force+2
 bmi SourceLandingDamage4086_NoPositiveForce
 bne SourceLandingDamage4086_HasForce
 lda.l SourceLandingDamage4086_Force
 bne SourceLandingDamage4086_HasForce
SourceLandingDamage4086_NoPositiveForce:
.a16
.i16
 jmp SourceLandingDamage4086_Complete
SourceLandingDamage4086_HasForce:
.a16
.i16
 lda.l SourceLandingDamage4086_View
 tax
 lda.l $439000+SOURCE_LIFECYCLE_TAKEDAMAGE,x
 ora.l $439002+SOURCE_LIFECYCLE_TAKEDAMAGE,x
 beq SourceLandingDamage4086_NullCallback
 lda.l SourceLandingCallback4086_Ready
 beq SourceLandingDamage4086_CallbackUnbound
 cmp #$B636
 beq SourceLandingDamage4086_CallbackBound
 jmp SourceLandingDamage4086_Bad
SourceLandingDamage4086_CallbackBound:
.a16
.i16
 jsl SourceLandingCallback4086_Execute
 bcc SourceLandingDamage4086_CallbackProgress
 jmp SourceLandingDamage4086_Bad
SourceLandingDamage4086_CallbackProgress:
.a16
.i16
 lda.l SourceLandingCallback4086_Status
 cmp #2
 bne SourceLandingDamage4086_CallbackUnbound
 jmp SourceLandingDamage4086_Complete
SourceLandingDamage4086_CallbackUnbound:
.a16
.i16
 lda #1
 jmp SourceLandingDamage4086_Pending
SourceLandingDamage4086_NullCallback:
.a16
.i16
 lda.l SourceFactors4086_Ready
 cmp #$B5F1
 beq SourceLandingDamage4086_FactorsReady
 jmp SourceLandingDamage4086_Bad
SourceLandingDamage4086_FactorsReady:
.a16
.i16
 lda.l SourceLandingDamage4086_Slot
 asl a
 asl a
 tax
 lda.l $43B902,x
 cmp #$B5F1
 beq SourceLandingDamage4086_FactorLease
 jmp SourceLandingDamage4086_Bad
SourceLandingDamage4086_FactorLease:
.a16
.i16
 lda.l $43B900,x
 cmp.l SourceLandingDamage4086_Model
 beq SourceLandingDamage4086_FactorModel
 jmp SourceLandingDamage4086_Bad
SourceLandingDamage4086_FactorModel:
.a16
.i16
 txa
 asl a
 asl a
 asl a
 tax
 lda.l $432800,x
 beq SourceLandingDamage4086_FactorLowZero
 jmp SourceLandingDamage4086_ArithmeticPending
SourceLandingDamage4086_FactorLowZero:
.a16
.i16
 lda.l $432802,x
 cmp #$3F80
 beq SourceLandingDamage4086_UnitFactor
 jmp SourceLandingDamage4086_ArithmeticPending
SourceLandingDamage4086_UnitFactor:
.a16
.i16
 lda.l SourceLandingDamage4086_View
 tax
 lda.l SOURCE_WORLD_POOL+32,x
 cmp #BOR_VT_INTEGER
 beq SourceLandingDamage4086_HealthTag
 jmp SourceLandingDamage4086_Bad
SourceLandingDamage4086_HealthTag:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+34,x
 beq SourceLandingDamage4086_HealthReserved
 jmp SourceLandingDamage4086_Bad
SourceLandingDamage4086_HealthReserved:
.a16
.i16
 lda.l SourceLandingDamage4086_Force+2
 cmp #$0080
 bcc SourceLandingDamage4086_Far1_0
 jmp SourceLandingDamage4086_ArithmeticPending
SourceLandingDamage4086_Far1_0:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+38,x
 bpl SourceLandingDamage4086_Far0_0
 cmp #$FF80
 bcs SourceLandingDamage4086_NegativeHealthBounded
 jmp SourceLandingDamage4086_ArithmeticPending
SourceLandingDamage4086_NegativeHealthBounded:
.a16
.i16
 jmp SourceLandingDamage4086_KillPending
SourceLandingDamage4086_Far0_0:
.a16
.i16
 cmp #$0080
 bcc SourceLandingDamage4086_Far1_1
 jmp SourceLandingDamage4086_ArithmeticPending
SourceLandingDamage4086_Far1_1:
.a16
.i16
 sec
 lda.l SOURCE_WORLD_POOL+36,x
 sbc.l SourceLandingDamage4086_Force
 sta.l SourceLandingDamage4086_Result
 lda.l SOURCE_WORLD_POOL+38,x
 sbc.l SourceLandingDamage4086_Force+2
 sta.l SourceLandingDamage4086_Result+2
 bpl SourceLandingDamage4086_Far0_1
 jmp SourceLandingDamage4086_KillPending
SourceLandingDamage4086_Far0_1:
.a16
.i16
 ora.l SourceLandingDamage4086_Result
 beq SourceLandingDamage4086_KillPending
 lda.l SourceLandingDamage4086_Result
 sta.l SOURCE_WORLD_POOL+36,x
 lda.l SourceLandingDamage4086_Result+2
 sta.l SOURCE_WORLD_POOL+38,x
 lda.l SourceLandingDamage4086_Physics
 tax
 lda #0
 sta.l SOURCE_ENTITY_PHYSICS+12,x
 sta.l SOURCE_ENTITY_PHYSICS+14,x
SourceLandingDamage4086_Complete:
.a16
.i16
 lda #2
 sta.l SourceLandingDamage4086_Status
 lda #0
 jmp SourceLandingDamage4086_Return
SourceLandingDamage4086_KillPending:
.a16
.i16
 lda.l SourceLandingKill4086_Ready
 beq SourceLandingDamage4086_KillUnbound
 cmp #$B62A
 beq SourceLandingDamage4086_KillBound
 jmp SourceLandingDamage4086_Bad
SourceLandingDamage4086_KillBound:
.a16
.i16
 jsl SourceLandingKill4086_Execute
 bcc SourceLandingDamage4086_KillDone
 jmp SourceLandingDamage4086_Bad
SourceLandingDamage4086_KillDone:
.a16
.i16
 lda.l SourceLandingDamage4086_Physics
 tax
 lda #0
 sta.l SOURCE_ENTITY_PHYSICS+12,x
 sta.l SOURCE_ENTITY_PHYSICS+14,x
 jmp SourceLandingDamage4086_Complete
SourceLandingDamage4086_KillUnbound:
.a16
.i16
 lda #4
 bra SourceLandingDamage4086_Pending
SourceLandingDamage4086_ArithmeticPending:
.a16
.i16
 lda #5
SourceLandingDamage4086_Pending:
.a16
.i16
 sta.l SourceLandingDamage4086_Status
 lda #$8102
SourceLandingDamage4086_Return:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
SourceLandingDamage4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceLandingDamage4086_Status
 ply
 plx
 plp
 sec
 rtl
