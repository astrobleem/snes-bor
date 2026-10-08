; Pinned entity freeze macros and update_mark reset; bank 62.
; State row 40B at $42E000: frozen,freezetime,stalltime,releasetime,
; magictime,guardtime,mpchargetime,turntime,sealtime,update_mark (all32).
; Timers already owned by side/life/toss arrays remain in those arrays.
; B5DF grants exclusive ownership of $42E000..$42F3FF (5120B).
SourceFreeze4086_Ready = $43BC7E
SourceFreeze4086_Status = $43BC80
SourceFreeze4086_StateOffset = $43BC82
SourceFreeze4086_SideOffset = $43BC84
SourceFreeze4086_LifeOffset = $43BC86
SourceFreeze4086_TossOffset = $43BC88
SourceFreeze4086_ViewOffset = $43BC8A
SourceFreeze4086_Value = $43BC8C
SOURCE_WORLD_FREEZE = $42E000
SourceFreeze4086_ScratchEnd = $43BC90
SourceFreeze4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceFreeze4086_Ready
 cmp #$B5DF
 beq SourceFreeze4086_Guard1
 jmp SourceFreeze4086_Bad
SourceFreeze4086_Guard1:
.a16
.i16
 lda.l SourceWorldTick4086_Ready
 cmp #$B4D5
 beq SourceFreeze4086_Guard2
 jmp SourceFreeze4086_Bad
SourceFreeze4086_Guard2:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceFreeze4086_Guard3
 jmp SourceFreeze4086_Bad
SourceFreeze4086_Guard3:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourceFreeze4086_Guard4
 jmp SourceFreeze4086_Bad
SourceFreeze4086_Guard4:
.a16
.i16
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 beq SourceFreeze4086_Guard5
 jmp SourceFreeze4086_Bad
SourceFreeze4086_Guard5:
.a16
.i16
 lda.l SourceWorldTick4086_Pending
 cmp #1
 beq SourceFreeze4086_Guard6
 jmp SourceFreeze4086_Bad
SourceFreeze4086_Guard6:
.a16
.i16
 lda.l SourceWorldTick4086_State
 cmp #1
 beq SourceFreeze4086_Guard7
 jmp SourceFreeze4086_Bad
SourceFreeze4086_Guard7:
.a16
.i16
 lda.l SourceFreeze4086_Status
 beq SourceFreeze4086_Guard8
 jmp SourceFreeze4086_Bad
SourceFreeze4086_Guard8:
.a16
.i16
 lda.l VmSourceWorld_Count
 bne SourceFreeze4086_Guard9
 jmp SourceFreeze4086_Bad
SourceFreeze4086_Guard9:
.a16
.i16
 cmp #129
 bcc SourceFreeze4086_Guard10
 jmp SourceFreeze4086_Bad
SourceFreeze4086_Guard10:
.a16
.i16
 lda.l SourceWorldTick4086_Slot
 cmp.l VmSourceWorld_Count
 bcc SourceFreeze4086_Guard11
 jmp SourceFreeze4086_Bad
SourceFreeze4086_Guard11:
.a16
.i16
 lda.l VmSourceWorld_Time
 cmp.l SourceWorldTick4086_TimeLo
 beq SourceFreeze4086_Guard12
 jmp SourceFreeze4086_Bad
SourceFreeze4086_Guard12:
.a16
.i16
 lda.l VmSourceWorld_Time+2
 cmp.l SourceWorldTick4086_TimeHi
 beq SourceFreeze4086_Guard13
 jmp SourceFreeze4086_Bad
SourceFreeze4086_Guard13:
.a16
.i16
 lda.l SourceWorldTick4086_Slot
 asl a
 asl a
 sta.l SourceFreeze4086_TossOffset
 asl a
 sta.l SourceFreeze4086_StateOffset
 asl a
 asl a
 clc
 adc.l SourceFreeze4086_StateOffset
 sta.l SourceFreeze4086_StateOffset
 asl a
 sta.l SourceFreeze4086_LifeOffset
 sta.l SourceFreeze4086_ViewOffset
 lda.l SourceWorldTick4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l SourceFreeze4086_SideOffset
 lda.l SourceWorldTick4086_Phase
 cmp #1
 beq SourceFreeze4086_ResetMark
 cmp #3
 beq SourceFreeze4086_CheckFrozen
 cmp #4
 beq SourceFreeze4086_Guard14
 jmp SourceFreeze4086_Bad
SourceFreeze4086_Guard14:
.a16
.i16
 jmp SourceFreeze4086_Expand
SourceFreeze4086_ResetMark:
.a16
.i16
 lda.l SourceFreeze4086_StateOffset
 tax
 lda #0
 sta.l SOURCE_WORLD_FREEZE+36,x
 sta.l SOURCE_WORLD_FREEZE+38,x
 jmp SourceFreeze4086_Done
SourceFreeze4086_CheckFrozen:
.a16
.i16
 jsr SourceFreeze4086_Predicate
 sta.l SourceWorldTick4086_Frozen
 jmp SourceFreeze4086_Done
SourceFreeze4086_Expand:
.a16
.i16
 lda.l SourceLifecycle4086_Ready
 cmp #$B4FB
 beq SourceFreeze4086_Guard15
 jmp SourceFreeze4086_Bad
SourceFreeze4086_Guard15:
.a16
.i16
 lda.l SourceToss4086_Ready
 cmp #$B4E2
 beq SourceFreeze4086_Guard16
 jmp SourceFreeze4086_Bad
SourceFreeze4086_Guard16:
.a16
.i16
 lda.l SourceFreeze4086_StateOffset
 tax
 lda.l SOURCE_WORLD_FREEZE+8,x
 ora.l SOURCE_WORLD_FREEZE+10,x
 beq SourceFreeze4086_TimerDone0
 clc
 lda.l SOURCE_WORLD_FREEZE+8,x
 adc #1
 sta.l SOURCE_WORLD_FREEZE+8,x
 lda.l SOURCE_WORLD_FREEZE+10,x
 adc #0
 sta.l SOURCE_WORLD_FREEZE+10,x
SourceFreeze4086_TimerDone0:
.a16
.i16
 lda.l SourceFreeze4086_StateOffset
 tax
 lda.l SOURCE_WORLD_FREEZE+12,x
 ora.l SOURCE_WORLD_FREEZE+14,x
 beq SourceFreeze4086_TimerDone1
 clc
 lda.l SOURCE_WORLD_FREEZE+12,x
 adc #1
 sta.l SOURCE_WORLD_FREEZE+12,x
 lda.l SOURCE_WORLD_FREEZE+14,x
 adc #0
 sta.l SOURCE_WORLD_FREEZE+14,x
SourceFreeze4086_TimerDone1:
.a16
.i16
 lda.l SourceFreeze4086_SideOffset
 tax
 lda.l SOURCE_WORLD_SIDES+8,x
 ora.l SOURCE_WORLD_SIDES+10,x
 beq SourceFreeze4086_TimerDone2
 clc
 lda.l SOURCE_WORLD_SIDES+8,x
 adc #1
 sta.l SOURCE_WORLD_SIDES+8,x
 lda.l SOURCE_WORLD_SIDES+10,x
 adc #0
 sta.l SOURCE_WORLD_SIDES+10,x
SourceFreeze4086_TimerDone2:
.a16
.i16
 lda.l SourceFreeze4086_SideOffset
 tax
 lda.l SOURCE_WORLD_SIDES+20,x
 ora.l SOURCE_WORLD_SIDES+22,x
 beq SourceFreeze4086_TimerDone3
 clc
 lda.l SOURCE_WORLD_SIDES+20,x
 adc #1
 sta.l SOURCE_WORLD_SIDES+20,x
 lda.l SOURCE_WORLD_SIDES+22,x
 adc #0
 sta.l SOURCE_WORLD_SIDES+22,x
SourceFreeze4086_TimerDone3:
.a16
.i16
 lda.l SourceFreeze4086_SideOffset
 tax
 lda.l SOURCE_WORLD_SIDES+24,x
 ora.l SOURCE_WORLD_SIDES+26,x
 beq SourceFreeze4086_TimerDone4
 clc
 lda.l SOURCE_WORLD_SIDES+24,x
 adc #1
 sta.l SOURCE_WORLD_SIDES+24,x
 lda.l SOURCE_WORLD_SIDES+26,x
 adc #0
 sta.l SOURCE_WORLD_SIDES+26,x
SourceFreeze4086_TimerDone4:
.a16
.i16
 lda.l SourceFreeze4086_StateOffset
 tax
 lda.l SOURCE_WORLD_FREEZE+16,x
 ora.l SOURCE_WORLD_FREEZE+18,x
 beq SourceFreeze4086_TimerDone5
 clc
 lda.l SOURCE_WORLD_FREEZE+16,x
 adc #1
 sta.l SOURCE_WORLD_FREEZE+16,x
 lda.l SOURCE_WORLD_FREEZE+18,x
 adc #0
 sta.l SOURCE_WORLD_FREEZE+18,x
SourceFreeze4086_TimerDone5:
.a16
.i16
 lda.l SourceFreeze4086_StateOffset
 tax
 lda.l SOURCE_WORLD_FREEZE+20,x
 ora.l SOURCE_WORLD_FREEZE+22,x
 beq SourceFreeze4086_TimerDone6
 clc
 lda.l SOURCE_WORLD_FREEZE+20,x
 adc #1
 sta.l SOURCE_WORLD_FREEZE+20,x
 lda.l SOURCE_WORLD_FREEZE+22,x
 adc #0
 sta.l SOURCE_WORLD_FREEZE+22,x
SourceFreeze4086_TimerDone6:
.a16
.i16
 lda.l SourceFreeze4086_TossOffset
 tax
 lda.l SOURCE_WORLD_TOSS_TIMES+0,x
 ora.l SOURCE_WORLD_TOSS_TIMES+2,x
 beq SourceFreeze4086_TimerDone7
 clc
 lda.l SOURCE_WORLD_TOSS_TIMES+0,x
 adc #1
 sta.l SOURCE_WORLD_TOSS_TIMES+0,x
 lda.l SOURCE_WORLD_TOSS_TIMES+2,x
 adc #0
 sta.l SOURCE_WORLD_TOSS_TIMES+2,x
SourceFreeze4086_TimerDone7:
.a16
.i16
 lda.l $43FD98
 ora.l $43FD9A
 ora.l $43FD94
 ora.l $43FD96
 beq SourceFreeze4086_TimerDone8
 lda.l SourceFreeze4086_StateOffset
 tax
 lda.l SOURCE_WORLD_FREEZE+4,x
 ora.l SOURCE_WORLD_FREEZE+6,x
 beq SourceFreeze4086_TimerDone8
 clc
 lda.l SOURCE_WORLD_FREEZE+4,x
 adc #1
 sta.l SOURCE_WORLD_FREEZE+4,x
 lda.l SOURCE_WORLD_FREEZE+6,x
 adc #0
 sta.l SOURCE_WORLD_FREEZE+6,x
SourceFreeze4086_TimerDone8:
.a16
.i16
 lda.l SourceFreeze4086_StateOffset
 tax
 lda.l SOURCE_WORLD_FREEZE+24,x
 ora.l SOURCE_WORLD_FREEZE+26,x
 beq SourceFreeze4086_TimerDone9
 clc
 lda.l SOURCE_WORLD_FREEZE+24,x
 adc #1
 sta.l SOURCE_WORLD_FREEZE+24,x
 lda.l SOURCE_WORLD_FREEZE+26,x
 adc #0
 sta.l SOURCE_WORLD_FREEZE+26,x
SourceFreeze4086_TimerDone9:
.a16
.i16
 lda.l SourceFreeze4086_LifeOffset
 tax
 lda.l $439000+32,x
 ora.l $439000+34,x
 beq SourceFreeze4086_TimerDone10
 clc
 lda.l $439000+32,x
 adc #1
 sta.l $439000+32,x
 lda.l $439000+34,x
 adc #0
 sta.l $439000+34,x
SourceFreeze4086_TimerDone10:
.a16
.i16
 lda.l SourceFreeze4086_StateOffset
 tax
 lda.l SOURCE_WORLD_FREEZE+28,x
 ora.l SOURCE_WORLD_FREEZE+30,x
 beq SourceFreeze4086_TimerDone11
 clc
 lda.l SOURCE_WORLD_FREEZE+28,x
 adc #1
 sta.l SOURCE_WORLD_FREEZE+28,x
 lda.l SOURCE_WORLD_FREEZE+30,x
 adc #0
 sta.l SOURCE_WORLD_FREEZE+30,x
SourceFreeze4086_TimerDone11:
.a16
.i16
 lda.l SourceFreeze4086_StateOffset
 tax
 lda.l SOURCE_WORLD_FREEZE+32,x
 ora.l SOURCE_WORLD_FREEZE+34,x
 beq SourceFreeze4086_TimerDone12
 clc
 lda.l SOURCE_WORLD_FREEZE+32,x
 adc #1
 sta.l SOURCE_WORLD_FREEZE+32,x
 lda.l SOURCE_WORLD_FREEZE+34,x
 adc #0
 sta.l SOURCE_WORLD_FREEZE+34,x
SourceFreeze4086_TimerDone12:
.a16
.i16
SourceFreeze4086_Done:
.a16
.i16
 lda #2
 sta.l SourceFreeze4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceFreeze4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceFreeze4086_Status
 ply
 plx
 plp
 sec
 rtl

; Constructor preflight occurs before any live state reset. Cold-disabled lease
; ignores child arrays; enabled freeze state also owns canonical toss timestamps.
SourceFreeze4086_PreflightBirth:
.a16
.i16
 php
 rep #$38
 lda.l SourceFreeze4086_Ready
 beq SourceFreeze4086_BirthLeaseOk
 cmp #$B5DF
 bne SourceFreeze4086_BirthLeaseBad
 lda.l SourceToss4086_Ready
 cmp #$B4E2
 bne SourceFreeze4086_BirthLeaseBad
 lda.l VmSourceWorld_Count
 beq SourceFreeze4086_BirthLeaseBad
 cmp #129
 bcs SourceFreeze4086_BirthLeaseBad
 lda.l SourceScriptClone4086_Slot
 cmp.l VmSourceWorld_Count
 bcs SourceFreeze4086_BirthLeaseBad
SourceFreeze4086_BirthLeaseOk:
.a16
.i16
 plp
 clc
 rtl
SourceFreeze4086_BirthLeaseBad:
.a16
.i16
 plp
 sec
 rtl

SourceFreeze4086_InitializeBirth:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jsl SourceFreeze4086_PreflightBirth
 bcs SourceFreeze4086_BirthBad
 lda.l SourceFreeze4086_Ready
 beq SourceFreeze4086_BirthDone
 lda.l SourceScriptClone4086_Slot
 asl a
 asl a
 tax
 lda #0
 sta.l SOURCE_WORLD_TOSS_TIMES,x
 sta.l SOURCE_WORLD_TOSS_TIMES+2,x
 txa
 asl a
 sta.l SourceFreeze4086_Value
 asl a
 asl a
 clc
 adc.l SourceFreeze4086_Value
 tax
 ldy #20
 lda #0
SourceFreeze4086_BirthClear:
.a16
.i16
 sta.l SOURCE_WORLD_FREEZE,x
 inx
 inx
 dey
 bne SourceFreeze4086_BirthClear
SourceFreeze4086_BirthDone:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
SourceFreeze4086_BirthBad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl

; Private predicate over validated current tick slot; no live state writes.
SourceFreeze4086_Predicate:
.a16
.i16
 lda.l SourceWorldTick4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l SourceFreeze4086_Value
 asl a
 clc
 adc.l SourceFreeze4086_Value
 tax
 lda.l $40C04A,x
 bne SourceFreeze4086_Predicate_NotTextbox
 lda.l $40C048,x
 cmp #128
 beq SourceFreeze4086_Predicate_Personal
SourceFreeze4086_Predicate_NotTextbox:
.a16
.i16
 lda.l $43FD98
 ora.l $43FD9A
 bne SourceFreeze4086_Predicate_Frozen
 lda.l $43FD94
 ora.l $43FD96
 beq SourceFreeze4086_Predicate_Personal
 lda.l SourceFreeze4086_ViewOffset
 tax
 lda.l SOURCE_WORLD_POOL,x
 cmp.l $43FD94
 bne SourceFreeze4086_Predicate_Frozen
 lda.l SOURCE_WORLD_POOL+2,x
 cmp.l $43FD96
 bne SourceFreeze4086_Predicate_Frozen
SourceFreeze4086_Predicate_Personal:
.a16
.i16
 lda.l SourceFreeze4086_StateOffset
 tax
 lda.l SOURCE_WORLD_FREEZE,x
 ora.l SOURCE_WORLD_FREEZE+2,x
 beq SourceFreeze4086_Predicate_NotFrozen
 lda.l SOURCE_WORLD_FREEZE+6,x
 cmp.l VmSourceWorld_Time+2
 bcc SourceFreeze4086_Predicate_NotFrozen
 bne SourceFreeze4086_Predicate_Frozen
 lda.l SOURCE_WORLD_FREEZE+4,x
 cmp.l VmSourceWorld_Time
 bcc SourceFreeze4086_Predicate_NotFrozen
 beq SourceFreeze4086_Predicate_NotFrozen
SourceFreeze4086_Predicate_Frozen:
.a16
.i16
 lda #1
 bra SourceFreeze4086_Predicate_PublishFrozen
SourceFreeze4086_Predicate_NotFrozen:
.a16
.i16
 lda #0
SourceFreeze4086_Predicate_PublishFrozen:
.a16
.i16
 rts

; Readonly query for check_lost, frozen service, and check_move phase11.
SourceFreeze4086_Query:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceFreeze4086_Ready
 cmp #$B5DF
 beq SourceFreeze4086_QueryGuard1
 jmp SourceFreeze4086_QueryBad
SourceFreeze4086_QueryGuard1:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceFreeze4086_QueryGuard2
 jmp SourceFreeze4086_QueryBad
SourceFreeze4086_QueryGuard2:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourceFreeze4086_QueryGuard3
 jmp SourceFreeze4086_QueryBad
SourceFreeze4086_QueryGuard3:
.a16
.i16
 lda.l SourceWorldTick4086_Ready
 cmp #$B4D5
 beq SourceFreeze4086_QueryGuard4
 jmp SourceFreeze4086_QueryBad
SourceFreeze4086_QueryGuard4:
.a16
.i16
 lda.l SourceWorldTick4086_Pending
 cmp #1
 beq SourceFreeze4086_QueryGuard5
 jmp SourceFreeze4086_QueryBad
SourceFreeze4086_QueryGuard5:
.a16
.i16
 lda.l SourceWorldTick4086_State
 cmp #1
 beq SourceFreeze4086_QueryGuard6
 cmp #2
 bne SourceFreeze4086_QueryStateBad
 lda.l SourceWorldTick4086_Phase
 cmp #11 ; arranger may query freeze only for post-update
 beq SourceFreeze4086_QueryGuard6
SourceFreeze4086_QueryStateBad:
.a16
.i16
 jmp SourceFreeze4086_QueryBad
SourceFreeze4086_QueryGuard6:
.a16
.i16
 lda.l VmSourceWorld_Count
 bne SourceFreeze4086_QueryGuard7
 jmp SourceFreeze4086_QueryBad
SourceFreeze4086_QueryGuard7:
.a16
.i16
 cmp #129
 bcc SourceFreeze4086_QueryGuard8
 jmp SourceFreeze4086_QueryBad
SourceFreeze4086_QueryGuard8:
.a16
.i16
 lda.l SourceWorldTick4086_Slot
 cmp.l VmSourceWorld_Count
 bcc SourceFreeze4086_QueryGuard9
 jmp SourceFreeze4086_QueryBad
SourceFreeze4086_QueryGuard9:
.a16
.i16
 lda.l VmSourceWorld_Time
 cmp.l SourceWorldTick4086_TimeLo
 beq SourceFreeze4086_QueryGuard10
 jmp SourceFreeze4086_QueryBad
SourceFreeze4086_QueryGuard10:
.a16
.i16
 lda.l VmSourceWorld_Time+2
 cmp.l SourceWorldTick4086_TimeHi
 beq SourceFreeze4086_QueryGuard11
 jmp SourceFreeze4086_QueryBad
SourceFreeze4086_QueryGuard11:
.a16
.i16
 lda.l SourceWorldTick4086_Phase
 cmp #2
 beq SourceFreeze4086_QueryPhase
 cmp #3
 beq SourceFreeze4086_QueryGuard12
 cmp #11
 beq SourceFreeze4086_QueryGuard12
 jmp SourceFreeze4086_QueryBad
SourceFreeze4086_QueryGuard12:
.a16
.i16
SourceFreeze4086_QueryPhase:
.a16
.i16
 lda.l SourceWorldTick4086_Slot
 asl a
 asl a
 asl a
 sta.l SourceFreeze4086_Value
 asl a
 asl a
 clc
 adc.l SourceFreeze4086_Value
 sta.l SourceFreeze4086_StateOffset
 asl a
 sta.l SourceFreeze4086_ViewOffset
 jsr SourceFreeze4086_Predicate
 ply
 plx
 plp
 clc
 rtl
SourceFreeze4086_QueryBad:
.a16
.i16
 lda #$FFFF
 ply
 plx
 plp
 sec
 rtl
