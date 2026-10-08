; B62A: synchronous source landing kill under the existing no-event contract.
; The completed lease admits exactly the held victim's following POST move.
; No arbitrary inactive entity is admitted by the movement backend.
SourceLandingKill4086_Ready = $43FDF0
SourceLandingKill4086_Status = $43FDF2
SourceLandingKill4086_Slot = $43FDF4
SourceLandingKill4086_Time = $43FDF6
SourceLandingKill4086_Token = $43FDFA
SourceLandingKill4086_End = $43FDFE
SourceLandingKill4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceLandingKill4086_Ready
 cmp #$B62A
 beq SourceLandingKill4086_ReadyGood
 jmp SourceLandingKill4086_Bad
SourceLandingKill4086_ReadyGood:
.a16
.i16
 lda.l SourceLandingKill4086_Status
 beq SourceLandingKill4086_Fresh
 jmp SourceLandingKill4086_Bad
SourceLandingKill4086_Fresh:
.a16
.i16
 lda.l SourcePostAir4086_Ready
 cmp #$B628
 beq SourceLandingKill4086_PostReady
 jmp SourceLandingKill4086_Bad
SourceLandingKill4086_PostReady:
.a16
.i16
 lda.l SourcePostAir4086_State
 cmp #1
 beq SourceLandingKill4086_PostOwned
 jmp SourceLandingKill4086_Bad
SourceLandingKill4086_PostOwned:
.a16
.i16
 lda.l SourcePostAir4086_Slot
 cmp.l SourceLandingDamage4086_Slot
 beq SourceLandingKill4086_SameSlot
 jmp SourceLandingKill4086_Bad
SourceLandingKill4086_SameSlot:
.a16
.i16
 sta.l SourceLandingKill4086_Slot
 sta.l SourceRetirement4086_Slot
 lda.l SourceSelf4086_GlobalLow
 sta.l SourceLandingKill4086_Token
 lda.l SourceSelf4086_GlobalHigh
 sta.l SourceLandingKill4086_Token+2
 lda.l VmSourceWorld_Time
 sta.l SourceLandingKill4086_Time
 lda.l VmSourceWorld_Time+2
 sta.l SourceLandingKill4086_Time+2
 ; Preflight precedes source health publication and every retirement mutation.
 jsl SourceRetirement4086_PreflightNoEvents
 bcc SourceLandingKill4086_RetirementChecked
 jmp SourceLandingKill4086_Bad
SourceLandingKill4086_RetirementChecked:
.a16
.i16
 cmp #1
 beq SourceLandingKill4086_LiveVictim
 jmp SourceLandingKill4086_Bad
SourceLandingKill4086_LiveVictim:
.a16
.i16
 jsl SourceRetirement4086_ApplyNoEvents
 bcc SourceLandingKill4086_Retired
 jmp SourceLandingKill4086_Bad
SourceLandingKill4086_Retired:
.a16
.i16
 lda.l SourceRetirement4086_Status
 cmp #2
 beq SourceLandingKill4086_Done
 jmp SourceLandingKill4086_Bad
SourceLandingKill4086_Done:
.a16
.i16
 lda #2
 sta.l SourceLandingKill4086_Status
 lda #0
 ply
 plx
 plp
 clc
 rtl
SourceLandingKill4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceLandingKill4086_Status
 ply
 plx
 plp
 sec
 rtl

; Called only from check_move's otherwise-rejected inactive-row branch.
SourceLandingKill4086_CheckMoveRetired:
.a16
.i16
 php
 rep #$38
 pha
 lda.l SourceLandingKill4086_Ready
 cmp #$B62A
 beq SourceLandingKill4086_MoveGuard1
 jmp SourceLandingKill4086_MoveBad
SourceLandingKill4086_MoveGuard1:
.a16
.i16
 lda.l SourceLandingKill4086_Status
 cmp #2
 beq SourceLandingKill4086_MoveGuard2
 jmp SourceLandingKill4086_MoveBad
SourceLandingKill4086_MoveGuard2:
.a16
.i16
 lda.l SourcePostAir4086_Ready
 cmp #$B628
 beq SourceLandingKill4086_MoveGuard3
 jmp SourceLandingKill4086_MoveBad
SourceLandingKill4086_MoveGuard3:
.a16
.i16
 lda.l SourcePostAir4086_State
 cmp #1
 beq SourceLandingKill4086_MoveGuard4
 jmp SourceLandingKill4086_MoveBad
SourceLandingKill4086_MoveGuard4:
.a16
.i16
 lda.l SourceGravityAir4086_Status
 cmp #2
 beq SourceLandingKill4086_MoveGuard5
 jmp SourceLandingKill4086_MoveBad
SourceLandingKill4086_MoveGuard5:
.a16
.i16
 lda.l SourceGravityLanding4086_State
 cmp #2
 beq SourceLandingKill4086_MoveGuard6
 jmp SourceLandingKill4086_MoveBad
SourceLandingKill4086_MoveGuard6:
.a16
.i16
 lda.l SourceLandingDamage4086_Status
 cmp #2
 beq SourceLandingKill4086_MoveGuard7
 jmp SourceLandingKill4086_MoveBad
SourceLandingKill4086_MoveGuard7:
.a16
.i16
 lda.l SourceLandingKill4086_Slot
 cmp.l SourceWorldTick4086_Slot
 beq SourceLandingKill4086_MoveGuard8
 jmp SourceLandingKill4086_MoveBad
SourceLandingKill4086_MoveGuard8:
.a16
.i16
 cmp.l SourcePostAir4086_Slot
 beq SourceLandingKill4086_MoveGuard9
 jmp SourceLandingKill4086_MoveBad
SourceLandingKill4086_MoveGuard9:
.a16
.i16
 cmp.l SourceRetirement4086_Slot
 beq SourceLandingKill4086_MoveGuard10
 jmp SourceLandingKill4086_MoveBad
SourceLandingKill4086_MoveGuard10:
.a16
.i16
 lda.l SourceRetirement4086_Status
 cmp #2
 beq SourceLandingKill4086_MoveGuard11
 jmp SourceLandingKill4086_MoveBad
SourceLandingKill4086_MoveGuard11:
.a16
.i16
 lda.l SourceLandingKill4086_Time
 cmp.l VmSourceWorld_Time
 beq SourceLandingKill4086_MoveGuard12
 jmp SourceLandingKill4086_MoveBad
SourceLandingKill4086_MoveGuard12:
.a16
.i16
 lda.l SourceLandingKill4086_Time+2
 cmp.l VmSourceWorld_Time+2
 beq SourceLandingKill4086_MoveGuard13
 jmp SourceLandingKill4086_MoveBad
SourceLandingKill4086_MoveGuard13:
.a16
.i16
 lda.l SourceLandingKill4086_Token
 cmp.l SourceSelf4086_GlobalLow
 beq SourceLandingKill4086_MoveGuard14
 jmp SourceLandingKill4086_MoveBad
SourceLandingKill4086_MoveGuard14:
.a16
.i16
 cmp.l SourceRetirement4086_Victim
 beq SourceLandingKill4086_MoveGuard15
 jmp SourceLandingKill4086_MoveBad
SourceLandingKill4086_MoveGuard15:
.a16
.i16
 lda.l SourceLandingKill4086_Token+2
 cmp #$41
 beq SourceLandingKill4086_MoveGuard16
 jmp SourceLandingKill4086_MoveBad
SourceLandingKill4086_MoveGuard16:
.a16
.i16
 pla
 plp
 clc
 rtl
SourceLandingKill4086_MoveBad:
.a16
.i16
 pla
 plp
 sec
 rtl
