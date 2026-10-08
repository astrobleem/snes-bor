; B636 bounded self-landing common/player/arrow callbacks and retained death.
; Actual lifecycle function IDs: player1, arrow8, common10. Never aliases NULL.
; B5SC's closed animation-only admission proves damage/death scripts absent.
; Opponent score uses actual B631. B639 binds closed lethal checkdeath;
; positive diesound, item, boss, pit retirement and magic_type1 MP stay required.
; Source damage/death scripts are absent by B5SC admission.
; Continuation stages retain actor/time/model identity; no repeated child Ack.
; Source SDL control_rumble is empty; B62D leases that pinned backend policy.
SourceLandingCallback4086_Ready = $7EFF00
SourceLandingCallback4086_Status = $7EFF02
SourceLandingCallback4086_State = $7EFF04
SourceLandingCallback4086_Slot = $7EFF06
SourceLandingCallback4086_Time = $7EFF08
SourceLandingCallback4086_Model = $7EFF0C
SourceLandingCallback4086_Callback = $7EFF0E
SourceLandingCallback4086_View = $7EFF10
SourceLandingCallback4086_Side = $7EFF12
SourceLandingCallback4086_Core = $7EFF14
SourceLandingCallback4086_Effects = $7EFF16
SourceLandingCallback4086_Damage = $7EFF18
SourceLandingCallback4086_Force = $7EFF1A
SourceLandingCallback4086_Result = $7EFF1E
SourceLandingCallback4086_Max = $7EFF22
SourceLandingCallback4086_GuardBreak = $7EFF26
SourceLandingCallback4086_HealthCheat = $7EFF28
SourceLandingCallback4086_NoHurt = $7EFF2C
SourceLandingCallback4086_ReturnValue = $7EFF30
SourceLandingCallback4086_InputsReady = $7EFF32
SourceLandingCallback4086_RawForce = $7EFF34
SourceLandingCallback4086_Opponent = $7EFF38
SourceLandingCallback4086_OppView = $7EFF3C
SourceLandingCallback4086_OppCore = $7EFF3E
SourceLandingCallback4086_ScoreAmount = $7EFF40
SourceLandingCallback4086_ScorePlayer = $7EFF44
SourceLandingCallback4086_MagicType = $7EFF48
SourceLandingCallback4086_ScoreFlag = $7EFF4C
SourceLandingCallback4086_Multiplier = $7EFF4E
SourceLandingCallback4086_Negative = $7EFF50
SourceLandingCallback4086_Operand = $7EFF52
SourceLandingCallback4086_Count = $7EFF56
SourceLandingCallback4086_OppSide = $7EFF58
SourceLandingCallback4086_End = $7EFF5A
SourceLandingCallback4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceLandingCallback4086_Ready
 cmp #$B636
 beq SourceLandingCallback4086_G1
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_G1:
.a16
.i16
 lda.l SourceLandingCallback4086_InputsReady
 cmp #$B637
 beq SourceLandingCallback4086_G2
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_G2:
.a16
.i16
 lda.l SourceGravityLanding4086_State
 cmp #1
 beq SourceLandingCallback4086_G3
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_G3:
.a16
.i16
 lda.l SourceGravityLanding4086_Service
 cmp #2
 beq SourceLandingCallback4086_G4
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_G4:
.a16
.i16
 lda.l SourceLandingDamage4086_Slot
 cmp #128
 bcc SourceLandingCallback4086_G5
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_G5:
.a16
.i16
 cmp.l SourceGravityLanding4086_Slot
 beq SourceLandingCallback4086_G6
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_G6:
.a16
.i16
 cmp.l SourceWorldTick4086_Slot
 beq SourceLandingCallback4086_G7
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_G7:
.a16
.i16
 lda.l SourceLandingCallback4086_Status
 cmp #3
 bne SourceLandingCallback4086_G8
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_G8:
.a16
.i16
 lda.l SourceLandingCallback4086_State
 beq SourceLandingCallback4086_Start
 lda.l SourceLandingCallback4086_Slot
 cmp.l SourceLandingDamage4086_Slot
 beq SourceLandingCallback4086_Resume1
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_Resume1:
.a16
.i16
 lda.l SourceLandingCallback4086_Time
 cmp.l SourceGravityLanding4086_Time
 beq SourceLandingCallback4086_Resume2
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_Resume2:
.a16
.i16
 lda.l SourceLandingCallback4086_Time+2
 cmp.l SourceGravityLanding4086_Time+2
 beq SourceLandingCallback4086_Resume3
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_Resume3:
.a16
.i16
 lda.l SourceLandingCallback4086_Model
 cmp.l SourceLandingDamage4086_Model
 beq SourceLandingCallback4086_Resume4
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_Resume4:
.a16
.i16
 lda.l SourceLandingCallback4086_View
 tax
 lda.l $439008,x
 cmp.l SourceLandingCallback4086_Callback
 beq SourceLandingCallback4086_Resume5
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_Resume5:
.a16
.i16
 lda.l $43900A,x
 bne SourceLandingCallback4086_ResumeBad
 jmp SourceLandingCallback4086_Dispatch
SourceLandingCallback4086_ResumeBad:
.a16
.i16
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_Start:
.a16
.i16
 lda.l SourceLandingDamage4086_Slot
 sta.l SourceLandingCallback4086_Slot
 lda.l SourceGravityLanding4086_Time
 sta.l SourceLandingCallback4086_Time
 lda.l SourceGravityLanding4086_Time+2
 sta.l SourceLandingCallback4086_Time+2
 lda.l SourceLandingDamage4086_Model
 sta.l SourceLandingCallback4086_Model
 lda.l SourceLandingDamage4086_View
 sta.l SourceLandingCallback4086_View
 tax
 lda.l $43900A,x
 beq SourceLandingCallback4086_IdLow
 jmp SourceLandingCallback4086_Required
SourceLandingCallback4086_IdLow:
.a16
.i16
 lda.l $439008,x
 sta.l SourceLandingCallback4086_Callback
 cmp #1
 beq SourceLandingCallback4086_IdGood
 cmp #8
 beq SourceLandingCallback4086_IdGood
 cmp #10
 beq SourceLandingCallback4086_IdGood
 jmp SourceLandingCallback4086_Required
SourceLandingCallback4086_IdGood:
.a16
.i16
 lda.l SourceLandingCallback4086_Slot
 asl a
 asl a
 asl a
 sta.l SourceLandingCallback4086_Effects
 asl a
 clc
 adc.l SourceLandingCallback4086_Effects
 sta.l SourceLandingCallback4086_Effects
 lda.l SourceLandingCallback4086_Slot
 asl a
 asl a
 sta.l SourceLandingCallback4086_Damage
 asl a
 clc
 adc.l SourceLandingCallback4086_Damage
 sta.l SourceLandingCallback4086_Damage
 lda.l SourceLandingCallback4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l SourceLandingCallback4086_Core
 asl a
 sta.l SourceLandingCallback4086_Side
 clc
 adc.l SourceLandingCallback4086_Core
 sta.l SourceLandingCallback4086_Core
 jsr SourceLandingCallback4086_CheckOpponent
 bcc SourceLandingCallback4086_OpponentChecked
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_OpponentChecked:
.a16
.i16
 cmp #0
 beq SourceLandingCallback4086_NoOpponent
 jmp SourceLandingCallback4086_Required
SourceLandingCallback4086_NoOpponent:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Ready
 cmp #$B4EB
 beq SourceLandingCallback4086_CoreReady
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_CoreReady:
.a16
.i16
 lda.l SourceWeapon4086_Ready
 cmp #$B4F1
 beq SourceLandingCallback4086_WeaponReady
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_WeaponReady:
.a16
.i16
 lda.l SourceLandingCallback4086_Slot
 asl a
 asl a
 asl a
 asl a
 tax
 lda.l $43E200,x
 cmp.l SourceLandingCallback4086_Model
 beq SourceLandingCallback4086_WeaponLease
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_WeaponLease:
.a16
.i16
 jsr SourceLandingCallback4086_CheckTable
 bcc SourceLandingCallback4086_TableGood
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_TableGood:
.a16
.i16
 lda.l SourceDamageEffectsState4086_Ready
 cmp #$B62F
 beq SourceLandingCallback4086_EffectsReady
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_EffectsReady:
.a16
.i16
 lda.l SourceLandingCallback4086_Effects
 tax
 lda.l SOURCE_ENTITY_DAMAGE_EFFECTS+20,x
 cmp #$B62F
 beq SourceLandingCallback4086_EffectsLease
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_EffectsLease:
.a16
.i16
 lda.l SOURCE_ENTITY_DAMAGE_EFFECTS+22,x
 cmp.l SourceLandingCallback4086_Model
 beq SourceLandingCallback4086_EffectsModel
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_EffectsModel:
.a16
.i16
 lda.l SourceLandingCallback4086_Slot
 asl a
 asl a
 tax
 lda.l SOURCE_ENTITY_TOEXPLODE+2,x
 bne SourceLandingCallback4086_NotExploding
 lda.l SOURCE_ENTITY_TOEXPLODE,x
 cmp #2
 bne SourceLandingCallback4086_NotExploding
 ; Source early return is not a landing-force clear. Retain it.
 jmp SourceLandingCallback4086_Required
SourceLandingCallback4086_NotExploding:
.a16
.i16
 lda.l SourceBounceEffects4086_NoRumbleReady
 cmp #$B62D
 beq SourceLandingCallback4086_RumbleReady
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_RumbleReady:
.a16
.i16
 lda.l SourceLandingCallback4086_Slot
 sta.l SourceScriptClone4086_Slot
 lda.l SourceLandingCallback4086_Model
 sta.l SourceScriptClone4086_Model
 jsl SourceScriptClone4086_CheckModelProgram
 bcc SourceLandingCallback4086_ScriptsReady
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_ScriptsReady:
.a16
.i16
 lda.l SourceLandingCallback4086_Side
 tax
 lda.l $40902C,x
 cmp.l SourceScriptClone4086_Mask
 beq SourceLandingCallback4086_ScriptInstanceMatches
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_ScriptInstanceMatches:
.a16
.i16
 lda.l $40902E,x
 ora.l $409030,x
 ora.l $409032,x
 ora.l $409034,x
 ora.l $409036,x
 beq SourceLandingCallback4086_NoScriptEvents
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_NoScriptEvents:
.a16
.i16
 lda.l SourceLandingCallback4086_Slot
 asl a
 asl a
 tax
 lda.l SourceFactors4086_Ready
 cmp #$B5F1
 beq SourceLandingCallback4086_FactorsReady
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_FactorsReady:
.a16
.i16
 lda.l $43B902,x
 cmp #$B5F1
 beq SourceLandingCallback4086_FactorsLease
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_FactorsLease:
.a16
.i16
 lda.l $43B900,x
 cmp.l SourceLandingCallback4086_Model
 beq SourceLandingCallback4086_FactorsModel
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_FactorsModel:
.a16
.i16
 txa
 asl a
 asl a
 asl a
 tax
 lda.l $432800,x
 ora.l $43281C,x
 beq SourceLandingCallback4086_FactorsLow
 jmp SourceLandingCallback4086_Required
SourceLandingCallback4086_FactorsLow:
.a16
.i16
 lda.l $432802,x
 cmp #$3F80
 beq SourceLandingCallback4086_DefenseUnit
 jmp SourceLandingCallback4086_Required
SourceLandingCallback4086_DefenseUnit:
.a16
.i16
 lda.l $43281E,x
 cmp #$3F80
 beq SourceLandingCallback4086_OffenseUnit
 jmp SourceLandingCallback4086_Required
SourceLandingCallback4086_OffenseUnit:
.a16
.i16
 lda.l SourceLandingCallback4086_View
 tax
 lda.l SOURCE_WORLD_POOL+32,x
 cmp #BOR_VT_INTEGER
 beq SourceLandingCallback4086_HealthTag
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_HealthTag:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+64,x
 cmp #BOR_VT_INTEGER
 beq SourceLandingCallback4086_MaxTag
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_MaxTag:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+34,x
 ora.l SOURCE_WORLD_POOL+66,x
 beq SourceLandingCallback4086_HealthReserved
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_HealthReserved:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+38,x
 cmp #$0080
 bcc SourceLandingCallback4086_HealthBound
 jmp SourceLandingCallback4086_Required
SourceLandingCallback4086_HealthBound:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+68,x
 sta.l SourceLandingCallback4086_Max
 lda.l SOURCE_WORLD_POOL+70,x
 sta.l SourceLandingCallback4086_Max+2
 cmp #$0080
 bcc SourceLandingCallback4086_MaxBound
 jmp SourceLandingCallback4086_Required
SourceLandingCallback4086_MaxBound:
.a16
.i16
 lda.l SourceLandingDamage4086_Force
 sta.l SourceLandingCallback4086_Force
 lda.l SourceLandingDamage4086_Force+2
 sta.l SourceLandingCallback4086_Force+2
 cmp #$0080
 bcc SourceLandingCallback4086_ForceBound
 jmp SourceLandingCallback4086_Required
SourceLandingCallback4086_ForceBound:
.a16
.i16
 ; Immutable B4DI header/bank/row was validated by B62F birth and installer.
 ; Revalidate through the real drop component before later scalar commit.
 lda #0
 sta.l SourceLandingCallback4086_GuardBreak
 lda.l SourceLandingCallback4086_Effects
 tax
 lda.l SOURCE_ENTITY_DAMAGE_EFFECTS+18,x
 bmi SourceLandingCallback4086_GuardCurrentZero
 ora.l SOURCE_ENTITY_DAMAGE_EFFECTS+16,x
 bne SourceLandingCallback4086_GuardChecked
SourceLandingCallback4086_GuardCurrentZero:
.a16
.i16
 lda.l SourceLandingCallback4086_Model
 asl a
 asl a
 asl a
 asl a
 clc
 adc #36
 clc
 adc.l SourceLandingDrop4086_Base
 tax
 jsr SourceLandingDrop4086_Read
 pha
 inx
 inx
 jsr SourceLandingDrop4086_Read
 bmi SourceLandingCallback4086_GuardMaxNotPositive
 bne SourceLandingCallback4086_GuardMaxPositive
 ora 1,s
 beq SourceLandingCallback4086_GuardMaxNotPositive
SourceLandingCallback4086_GuardMaxPositive:
.a16
.i16
 pla
 lda #1
 sta.l SourceLandingCallback4086_GuardBreak
 bra SourceLandingCallback4086_ZeroForce
SourceLandingCallback4086_GuardMaxNotPositive:
.a16
.i16
 pla
SourceLandingCallback4086_GuardChecked:
.a16
.i16
 lda.l SourceLandingCallback4086_Callback
 cmp #1
 bne SourceLandingCallback4086_ComputeHealth
 lda.l SourceLandingCallback4086_HealthCheat
 ora.l SourceLandingCallback4086_HealthCheat+2
 bne SourceLandingCallback4086_ZeroForce
 lda.l SourceLandingCallback4086_NoHurt
 ora.l SourceLandingCallback4086_NoHurt+2
 beq SourceLandingCallback4086_ComputeHealth
 lda.l SourceLandingCallback4086_Core
 tax
 lda.l $40C048,x
 and #2
 beq SourceLandingCallback4086_ComputeHealth
SourceLandingCallback4086_ZeroForce:
.a16
.i16
 lda #0
 sta.l SourceLandingCallback4086_Force
 sta.l SourceLandingCallback4086_Force+2
SourceLandingCallback4086_ComputeHealth:
.a16
.i16
 lda.l SourceLandingCallback4086_View
 tax
 sec
 lda.l SOURCE_WORLD_POOL+36,x
 sbc.l SourceLandingCallback4086_Force
 sta.l SourceLandingCallback4086_Result
 lda.l SOURCE_WORLD_POOL+38,x
 sbc.l SourceLandingCallback4086_Force+2
 sta.l SourceLandingCallback4086_Result+2
 bpl SourceLandingCallback4086_ResultNonnegative
 jmp SourceLandingCallback4086_LethalPolicy
SourceLandingCallback4086_ResultNonnegative:
.a16
.i16
 cmp.l SourceLandingCallback4086_Max+2
 bcc SourceLandingCallback4086_CheckNonlethal
 bne SourceLandingCallback4086_Cap
 lda.l SourceLandingCallback4086_Result
 cmp.l SourceLandingCallback4086_Max
 bcc SourceLandingCallback4086_CheckNonlethal
SourceLandingCallback4086_Cap:
.a16
.i16
 lda.l SourceLandingCallback4086_Max
 sta.l SourceLandingCallback4086_Result
 lda.l SourceLandingCallback4086_Max+2
 sta.l SourceLandingCallback4086_Result+2
SourceLandingCallback4086_CheckNonlethal:
.a16
.i16
 lda.l SourceLandingCallback4086_Result
 ora.l SourceLandingCallback4086_Result+2
 bne SourceLandingCallback4086_BeginServices
SourceLandingCallback4086_LethalPolicy:
.a16
.i16
 jsr SourceLandingCallback4086_ResolveInvincible
 bcc SourceLandingCallback4086_InvincibleResult
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_InvincibleResult:
.a16
.i16
 cmp #0
 beq SourceLandingCallback4086_BeginServices
 jsl SourceLandingDeath4086_Preflight
 bcc SourceLandingCallback4086_DeathAdmission
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_DeathAdmission:
.a16
.i16
 cmp #0
 beq SourceLandingCallback4086_BeginServices
 jmp SourceLandingCallback4086_Required
SourceLandingCallback4086_BeginServices:
.a16
.i16
 jsr SourceLandingCallback4086_PrepareScore
 bcc SourceLandingCallback4086_ScorePrepared
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_ScorePrepared:
.a16
.i16
 cmp #0
 beq SourceLandingCallback4086_ScoreAdmitted
 jmp SourceLandingCallback4086_Required
SourceLandingCallback4086_ScoreAdmitted:
.a16
.i16
 lda #0
 sta.l SourceLandingDeath4086_State
 lda #1
 sta.l SourceLandingCallback4086_State
SourceLandingCallback4086_Dispatch:
.a16
.i16
 lda.l SourceLandingCallback4086_State
 cmp #1
 beq SourceLandingCallback4086_Drop
 cmp #2
 bne SourceLandingCallback4086_Dispatch3
 jmp SourceLandingCallback4086_Weapon
SourceLandingCallback4086_Dispatch3:
.a16
.i16
 cmp #3
 bne SourceLandingCallback4086_Dispatch4
 jmp SourceLandingCallback4086_EffectsCall
SourceLandingCallback4086_Dispatch4:
.a16
.i16
 cmp #4
 bne SourceLandingCallback4086_Dispatch5
 jmp SourceLandingCallback4086_Score
SourceLandingCallback4086_Dispatch5:
.a16
.i16
 cmp #5
 bne SourceLandingCallback4086_DispatchBad
 jmp SourceLandingCallback4086_Commit
SourceLandingCallback4086_DispatchBad:
.a16
.i16
 cmp #7
 bne SourceLandingCallback4086_Dispatch6
 jmp SourceLandingCallback4086_DeathCall
SourceLandingCallback4086_Dispatch6:
.a16
.i16
 cmp #6
 bne SourceLandingCallback4086_DispatchInvalid
 jmp SourceLandingCallback4086_Complete
SourceLandingCallback4086_DispatchInvalid:
.a16
.i16
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_Drop:
.a16
.i16
 ; Actual arrow callback mutates these modeldata flags before common body.
 lda.l SourceLandingCallback4086_Callback
 cmp #8
 bne SourceLandingCallback4086_DropCall
 lda.l SourceLandingCallback4086_Core
 tax
 lda #1
 sta.l $40C004,x
 sta.l $40C008,x
 sta.l $40C010,x
 sta.l $40C014,x
 lda #0
 sta.l $40C006,x
 sta.l $40C00A,x
 sta.l $40C012,x
 sta.l $40C016,x
 sta.l $40C024,x
 sta.l $40C026,x
SourceLandingCallback4086_DropCall:
.a16
.i16
 lda.l SourceLandingCallback4086_Damage
 tax
 lda #16
 sta.l SOURCE_ENTITY_DAMAGE_STATE+8,x
 lda #0
 sta.l SOURCE_ENTITY_DAMAGE_STATE+10,x
 lda.l SourceLandingCallback4086_Slot
 sta.l SourceLandingDrop4086_Slot
 jsl SourceLandingDrop4086_Execute
 bcc SourceLandingCallback4086_DropDone
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_DropDone:
.a16
.i16
 lda #2
 sta.l SourceLandingCallback4086_State
SourceLandingCallback4086_Weapon:
.a16
.i16
 lda.l SourceLandingCallback4086_Slot
 asl a
 asl a
 asl a
 asl a
 tax
 lda.l $43E204,x
 ora.l $43E206,x
 bne SourceLandingCallback4086_WeaponDone
 lda.l SourceLandingCallback4086_Slot
 sta.l SourceDropWeapon4086_Slot
 jsl SourceDropWeapon4086_Execute
 bcc SourceLandingCallback4086_WeaponResult
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_WeaponResult:
.a16
.i16
 lda.l SourceDropWeapon4086_Status
 beq SourceLandingCallback4086_WeaponDone
 jmp SourceLandingCallback4086_Required
SourceLandingCallback4086_WeaponDone:
.a16
.i16
 lda #3
 sta.l SourceLandingCallback4086_State
SourceLandingCallback4086_EffectsCall:
.a16
.i16
 lda.l SourceLandingCallback4086_GuardBreak
 bne SourceLandingCallback4086_EffectsDone
 lda.l SourceLandingCallback4086_Slot
 sta.l SourceLandingEffects4086_Slot
 jsl SourceLandingEffects4086_Execute
 bcc SourceLandingCallback4086_EffectsResult
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_EffectsResult:
.a16
.i16
 lda.l SourceLandingEffects4086_Status
 cmp #4
 beq SourceLandingCallback4086_EffectsDone
 jmp SourceLandingCallback4086_Required
SourceLandingCallback4086_EffectsDone:
.a16
.i16
 lda #4
 sta.l SourceLandingCallback4086_State
SourceLandingCallback4086_Score:
.a16
.i16
 lda.l SourceLandingCallback4086_ScoreFlag
 beq SourceLandingCallback4086_ScoreDone
 lda.l SourceLandingCallback4086_ScorePlayer
 sta.l SourceScore4086_Index
 lda.l SourceLandingCallback4086_ScorePlayer+2
 sta.l SourceScore4086_Index+2
 lda.l SourceLandingCallback4086_ScoreAmount
 sta.l SourceScore4086_Add
 lda.l SourceLandingCallback4086_ScoreAmount+2
 sta.l SourceScore4086_Add+2
 jsl SourceScore4086_Execute
 bcc SourceLandingCallback4086_ScoreResult
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_ScoreResult:
.a16
.i16
 lda.l SourceScore4086_Status
 beq SourceLandingCallback4086_ScoreDone
 jmp SourceLandingCallback4086_Required
SourceLandingCallback4086_ScoreDone:
.a16
.i16
 lda #5
 sta.l SourceLandingCallback4086_State
SourceLandingCallback4086_Commit:
.a16
.i16
 ; MP admissibility was checked before source actor writes. The score stage
 ; executes actual B631 once, retaining pending service requirements.
 ; The paired animation-only script lease means actual dispatchers return.
 ; Commit checkdamage's health before checkdeath and its retained score child.
 lda.l SourceLandingCallback4086_View
 tax
 lda.l SourceLandingCallback4086_Result
 sta.l SOURCE_WORLD_POOL+36,x
 lda.l SourceLandingCallback4086_Result+2
 sta.l SOURCE_WORLD_POOL+38,x
 bmi SourceLandingCallback4086_StartDeath
 lda.l SourceLandingCallback4086_Result
 ora.l SourceLandingCallback4086_Result+2
 bne SourceLandingCallback4086_FinishForce
SourceLandingCallback4086_StartDeath:
.a16
.i16
 lda #7
 sta.l SourceLandingCallback4086_State
SourceLandingCallback4086_DeathCall:
.a16
.i16
 jsl SourceLandingDeath4086_Execute
 bcc SourceLandingCallback4086_DeathResult
 jmp SourceLandingCallback4086_Bad
SourceLandingCallback4086_DeathResult:
.a16
.i16
 lda.l SourceLandingDeath4086_Status
 beq SourceLandingCallback4086_FinishForce
 jmp SourceLandingCallback4086_Required
SourceLandingCallback4086_FinishForce:
.a16
.i16
 lda.l SourceLandingDamage4086_Physics
 tax
 lda #0
 sta.l SOURCE_ENTITY_PHYSICS+12,x
 sta.l SOURCE_ENTITY_PHYSICS+14,x
 lda #1
 sta.l SourceLandingCallback4086_ReturnValue
 lda.l SourceLandingCallback4086_Callback
 cmp #8
 bne SourceLandingCallback4086_ReturnSet
 lda #0
 sta.l SourceLandingCallback4086_ReturnValue
 lda.l SourceLandingCallback4086_View
 tax
 lda.l $439014,x
 ora.l $439016,x
 beq SourceLandingCallback4086_ReturnSet
 lda #1
 sta.l SourceLandingCallback4086_ReturnValue
SourceLandingCallback4086_ReturnSet:
.a16
.i16
 lda #6
 sta.l SourceLandingCallback4086_State
SourceLandingCallback4086_Complete:
.a16
.i16
 lda #2
 sta.l SourceLandingCallback4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceLandingCallback4086_Required:
.a16
.i16
 lda #1
 sta.l SourceLandingCallback4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceLandingCallback4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceLandingCallback4086_Status
 ply
 plx
 plp
 sec
 rtl
; Readonly B4DI validation before any source actor mutation or guard lookup.
SourceLandingCallback4086_CheckTable:
.a16
.i16
 lda.l SourceLandingDrop4086_Ready
 cmp #$B62E
 beq SourceLandingCallback4086_Table1
 jmp SourceLandingCallback4086_TableBad
SourceLandingCallback4086_Table1:
.a16
.i16
 lda.l SourceLandingDrop4086_Bank
 cmp #$100
 bcc SourceLandingCallback4086_Table2
 jmp SourceLandingCallback4086_TableBad
SourceLandingCallback4086_Table2:
.a16
.i16
 cmp #$40
 bcc SourceLandingCallback4086_TableBank
 cmp #$C0
 bcs SourceLandingCallback4086_TableBank
 jmp SourceLandingCallback4086_TableBad
SourceLandingCallback4086_TableBank:
.a16
.i16
 lda.l SourceLandingDrop4086_Base
 cmp #$8000
 bcs SourceLandingCallback4086_Table3
 jmp SourceLandingCallback4086_TableBad
SourceLandingCallback4086_Table3:
.a16
.i16
 lda.l SourceLandingDrop4086_Models
 beq SourceLandingCallback4086_TableBad
 cmp #17
 bcs SourceLandingCallback4086_TableBad
 cmp.l SourceLandingCallback4086_Model
 beq SourceLandingCallback4086_TableBad
 bcc SourceLandingCallback4086_TableBad
 asl a
 asl a
 asl a
 asl a
 clc
 adc #24
 cmp.l SourceLandingDrop4086_Bytes
 bne SourceLandingCallback4086_TableBad
 clc
 adc.l SourceLandingDrop4086_Base
 bcs SourceLandingCallback4086_TableBad
 jsr SourceLandingCallback4086_CheckHeader
 bcs SourceLandingCallback4086_TableBad
 lda.l SourceLandingCallback4086_Model
 asl a
 asl a
 asl a
 asl a
 clc
 adc #24
 clc
 adc.l SourceLandingDrop4086_Base
 tax
 jsr SourceLandingDrop4086_Read
 cmp.l SourceLandingCallback4086_Model
 bne SourceLandingCallback4086_TableBad
 inx
 inx
 jsr SourceLandingDrop4086_Read
 bne SourceLandingCallback4086_TableBad
 clc
 rts
SourceLandingCallback4086_TableBad:
.a16
.i16
 sec
 rts
SourceLandingCallback4086_CheckHeader:
.a16
.i16
 lda.l SourceLandingDrop4086_Base
 tax
 jsr SourceLandingDrop4086_Read
 cmp #$3442
 bne SourceLandingCallback4086_HeaderBad
 inx
 inx
 jsr SourceLandingDrop4086_Read
 cmp #$4944
 bne SourceLandingCallback4086_HeaderBad
 inx
 inx
 jsr SourceLandingDrop4086_Read
 cmp #1
 bne SourceLandingCallback4086_HeaderBad
 inx
 inx
 jsr SourceLandingDrop4086_Read
 cmp #16
 bne SourceLandingCallback4086_HeaderBad
 inx
 inx
 jsr SourceLandingDrop4086_Read
 cmp.l SourceLandingDrop4086_Models
 bne SourceLandingCallback4086_HeaderBad
 inx
 inx
 jsr SourceLandingDrop4086_Read
 bne SourceLandingCallback4086_HeaderBad
 clc
 rts
SourceLandingCallback4086_HeaderBad:
.a16
.i16
 sec
 rts
