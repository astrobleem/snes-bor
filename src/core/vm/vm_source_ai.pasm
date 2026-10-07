; Pinned check_ai sequencing owner. Callback bodies are explicit requests,
; never semantic-ID no-ops. Begin/Continue A=1 action,2 think,3 think script,
; 4 set_idle; A=0 complete. Continue A must match the outstanding request.
; Singleton world-service owner outside nested animation snapshots.
; noaicontrol DWORD occupies unused idle-flags +16, initialized by birth clear.
SourceAI4086_Ready = $43BCFA
SourceAI4086_State = $43BCFC
SourceAI4086_Endgame = $43BCFE
SourceAI4086_Slot = $43BD02
SourceAI4086_View = $43BD04
SourceAI4086_Side = $43BD06
SourceAI4086_Life = $43BD08
SourceAI4086_Flags = $43BD0A
SourceAI4086_Freeze = $43BD0C
SourceAI4086_Callback = $43BD0E
SourceAI4086_SpawnID = $43BD12
SourceAI4086_RespawnID = $43BD14
SourceAI4086_ModelOffset = $43BD16
SourceAI4086_RowBytes = $43BD18
SourceAI4086_Model = $43BD1A
SourceAI4086_Temp = $43BD1C
SourceAI4086_End = $43BD1E
SourceAI4086_Begin:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceAI4086_State
 bne SourceAI4086_Far1
 jmp SourceAI4086_BeginIdle
SourceAI4086_Far1:
.a16
.i16
 cmp #5
 bne SourceAI4086_Far2
 jmp SourceAI4086_BeginIdle
SourceAI4086_Far2:
.a16
.i16
 jmp SourceAI4086_Bad
SourceAI4086_BeginIdle:
.a16
.i16
 jsr SourceAI4086_Preflight
 bcs SourceAI4086_Far3
 jmp SourceAI4086_BeginChecked
SourceAI4086_Far3:
.a16
.i16
 jmp SourceAI4086_Bad
SourceAI4086_BeginChecked:
.a16
.i16
 lda.l SourceAI4086_Endgame
 ora.l SourceAI4086_Endgame+2
 bne SourceAI4086_Far4
 jmp SourceAI4086_BeginDeadline
SourceAI4086_Far4:
.a16
.i16
 jmp SourceAI4086_Done
SourceAI4086_BeginDeadline:
.a16
.i16
 jsr SourceAI4086_Deadline
 bcs SourceAI4086_Far5
 jmp SourceAI4086_BeginDue
SourceAI4086_Far5:
.a16
.i16
 jmp SourceAI4086_Done
SourceAI4086_BeginDue:
.a16
.i16
 lda.l SourceAI4086_Freeze
 tax
 lda.l $42E024,x
 ora #2
 sta.l $42E024,x
 lda.l SourceAI4086_Life
 tax
 lda.l $43900C,x
 sta.l SourceAI4086_Callback
 lda.l $43900E,x
 sta.l SourceAI4086_Callback+2
 ora.l SourceAI4086_Callback
 bne SourceAI4086_Far6
 jmp SourceAI4086_Think
SourceAI4086_Far6:
.a16
.i16
 lda #1
 jmp SourceAI4086_Request
SourceAI4086_Continue:
.a16
.i16
 php
 rep #$38
 phx
 phy
 cmp.l SourceAI4086_State
 bne SourceAI4086_Far7
 jmp SourceAI4086_ContinueMatch
SourceAI4086_Far7:
.a16
.i16
 jmp SourceAI4086_Bad
SourceAI4086_ContinueMatch:
.a16
.i16
 cmp #1
 bcs SourceAI4086_Far8
 jmp SourceAI4086_ContinueBad
SourceAI4086_Far8:
.a16
.i16
 cmp #5
 bcc SourceAI4086_Far9
 jmp SourceAI4086_ContinueBad
SourceAI4086_Far9:
.a16
.i16
 jsr SourceAI4086_Preflight
 bcs SourceAI4086_Far10
 jmp SourceAI4086_ContinueChecked
SourceAI4086_Far10:
.a16
.i16
SourceAI4086_ContinueBad:
.a16
.i16
 jmp SourceAI4086_Bad
SourceAI4086_ContinueChecked:
.a16
.i16
 lda.l SourceAI4086_State
 cmp #1
 bne SourceAI4086_Far11
 jmp SourceAI4086_Think
SourceAI4086_Far11:
.a16
.i16
 cmp #2
 bne SourceAI4086_Far12
 jmp SourceAI4086_Script
SourceAI4086_Far12:
.a16
.i16
 cmp #3
 bne SourceAI4086_Far13
 jmp SourceAI4086_IdleCheck
SourceAI4086_Far13:
.a16
.i16
 jmp SourceAI4086_Done
SourceAI4086_Think:
.a16
.i16
 lda.l SourceAI4086_Life
 tax
 lda.l $439000,x
 sta.l SourceAI4086_Callback
 lda.l $439002,x
 sta.l SourceAI4086_Callback+2
 ora.l SourceAI4086_Callback
 bne SourceAI4086_Far14
 jmp SourceAI4086_Script
SourceAI4086_Far14:
.a16
.i16
 jsr SourceAI4086_Deadline
 bcc SourceAI4086_Far15
 jmp SourceAI4086_ThinkTimerDone
SourceAI4086_Far15:
.a16
.i16
 lda.l SourceAI4086_Side
 tax
 lda.l VmSourceWorld_Time
 clc
 adc #2
 sta.l $416814,x
 lda.l VmSourceWorld_Time+2
 adc #0
 sta.l $416816,x
SourceAI4086_ThinkTimerDone:
.a16
.i16
 ; noaicontrol is separate from the frame-effect reactive DWORD.
 lda.l SourceAI4086_Slot
 asl a
 asl a
 asl a
 pha
 asl a
 clc
 adc 1,s
 tax
 pla
 lda.l SOURCE_ENTITY_AI_STATE,x
 ora.l SOURCE_ENTITY_AI_STATE+2,x
 beq SourceAI4086_Far16
 jmp SourceAI4086_Script
SourceAI4086_Far16:
.a16
.i16
 lda #2
 jmp SourceAI4086_Request
SourceAI4086_Script:
.a16
.i16
 lda #0
 sta.l SourceAI4086_Callback
 sta.l SourceAI4086_Callback+2
 lda #3
 jmp SourceAI4086_Request
SourceAI4086_IdleCheck:
.a16
.i16
 lda.l SourceAI4086_Slot
 asl a
 asl a
 sta.l SourceAI4086_Temp
 asl a
 asl a
 clc
 adc.l SourceAI4086_Temp
 clc
 adc #$F500
 tax
 lda.l $410010,x
 bne SourceAI4086_Far17
 jmp SourceAI4086_IdleAnimation
SourceAI4086_Far17:
.a16
.i16
 jmp SourceAI4086_Done
SourceAI4086_IdleAnimation:
.a16
.i16
 lda.l SourceAI4086_Side
 tax
 lda.l $416804,x
 sta.l SourceAI4086_Temp
 lda.l SourceAI4086_SpawnID
 asl a
 clc
 adc.l SourceAI4086_ModelOffset
 tax
 lda.l SOURCE_MODEL_ANIMATION_CACHE,x
 cmp.l SourceAI4086_Temp
 bne SourceAI4086_Far18
 jmp SourceAI4086_IdleRequired
SourceAI4086_Far18:
.a16
.i16
 lda.l SourceAI4086_RespawnID
 asl a
 clc
 adc.l SourceAI4086_ModelOffset
 tax
 lda.l SOURCE_MODEL_ANIMATION_CACHE,x
 cmp.l SourceAI4086_Temp
 bne SourceAI4086_Far19
 jmp SourceAI4086_IdleRequired
SourceAI4086_Far19:
.a16
.i16
 jmp SourceAI4086_Done
SourceAI4086_IdleRequired:
.a16
.i16
 lda #4
 jmp SourceAI4086_Request
SourceAI4086_Done:
.a16
.i16
 lda #5
 sta.l SourceAI4086_State
 lda #0
 jmp SourceAI4086_Good
SourceAI4086_Request:
.a16
.i16
 sta.l SourceAI4086_State
SourceAI4086_Good:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
SourceAI4086_Bad:
.a16
.i16
 lda #6
 sta.l SourceAI4086_State
 ply
 plx
 plp
 sec
 rtl
; C=0 iff unsigned nextthink<=time.
SourceAI4086_Deadline:
.a16
.i16
 lda.l SourceAI4086_Side
 tax
 lda.l $416816,x
 cmp.l VmSourceWorld_Time+2
 bcs SourceAI4086_Far20
 jmp SourceAI4086_DeadlineDue
SourceAI4086_Far20:
.a16
.i16
 beq SourceAI4086_Far21
 jmp SourceAI4086_DeadlineFuture
SourceAI4086_Far21:
.a16
.i16
 lda.l $416814,x
 cmp.l VmSourceWorld_Time
 bcs SourceAI4086_Far22
 jmp SourceAI4086_DeadlineDue
SourceAI4086_Far22:
.a16
.i16
 bne SourceAI4086_Far23
 jmp SourceAI4086_DeadlineDue
SourceAI4086_Far23:
.a16
.i16
SourceAI4086_DeadlineFuture:
.a16
.i16
 sec
 rts
SourceAI4086_DeadlineDue:
.a16
.i16
 clc
 rts
SourceAI4086_Preflight:
.a16
.i16
 lda.l SourceAI4086_Ready
 cmp #$B5E2
 bne SourceAI4086_Far24
 jmp SourceAI4086_Check0
SourceAI4086_Far24:
.a16
.i16
 jmp SourceAI4086_PreflightBad
SourceAI4086_Check0:
.a16
.i16
 lda.l SourceWorldTick4086_Ready
 cmp #$B4D5
 bne SourceAI4086_Far25
 jmp SourceAI4086_Check1
SourceAI4086_Far25:
.a16
.i16
 jmp SourceAI4086_PreflightBad
SourceAI4086_Check1:
.a16
.i16
 lda.l SourceWorldTick4086_State
 cmp #1
 bne SourceAI4086_Far26
 jmp SourceAI4086_Check2
SourceAI4086_Far26:
.a16
.i16
 jmp SourceAI4086_PreflightBad
SourceAI4086_Check2:
.a16
.i16
 lda.l SourceWorldTick4086_Pending
 cmp #1
 bne SourceAI4086_Far27
 jmp SourceAI4086_Check3
SourceAI4086_Far27:
.a16
.i16
 jmp SourceAI4086_PreflightBad
SourceAI4086_Check3:
.a16
.i16
 lda.l SourceWorldTick4086_Phase
 cmp #6
 bne SourceAI4086_Far28
 jmp SourceAI4086_Check4
SourceAI4086_Far28:
.a16
.i16
 jmp SourceAI4086_PreflightBad
SourceAI4086_Check4:
.a16
.i16
 lda.l SourceWorldTick4086_TimeLo
 cmp.l VmSourceWorld_Time
 bne SourceAI4086_Far29
 jmp SourceAI4086_Check5
SourceAI4086_Far29:
.a16
.i16
 jmp SourceAI4086_PreflightBad
SourceAI4086_Check5:
.a16
.i16
 lda.l SourceWorldTick4086_TimeHi
 cmp.l VmSourceWorld_Time+2
 bne SourceAI4086_Far30
 jmp SourceAI4086_Check6
SourceAI4086_Far30:
.a16
.i16
 jmp SourceAI4086_PreflightBad
SourceAI4086_Check6:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 bne SourceAI4086_Far31
 jmp SourceAI4086_Check7
SourceAI4086_Far31:
.a16
.i16
 jmp SourceAI4086_PreflightBad
SourceAI4086_Check7:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 bne SourceAI4086_Far32
 jmp SourceAI4086_Check8
SourceAI4086_Far32:
.a16
.i16
 jmp SourceAI4086_PreflightBad
SourceAI4086_Check8:
.a16
.i16
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 bne SourceAI4086_Far33
 jmp SourceAI4086_Check9
SourceAI4086_Far33:
.a16
.i16
 jmp SourceAI4086_PreflightBad
SourceAI4086_Check9:
.a16
.i16
 lda.l SourceLifecycle4086_Ready
 cmp #$B4FB
 bne SourceAI4086_Far34
 jmp SourceAI4086_Check10
SourceAI4086_Far34:
.a16
.i16
 jmp SourceAI4086_PreflightBad
SourceAI4086_Check10:
.a16
.i16
 lda.l SourceFreeze4086_Ready
 cmp #$B5DF
 bne SourceAI4086_Far35
 jmp SourceAI4086_Check11
SourceAI4086_Far35:
.a16
.i16
 jmp SourceAI4086_PreflightBad
SourceAI4086_Check11:
.a16
.i16
 lda.l SourceSelf4086_Ready
 cmp #$B4F6
 bne SourceAI4086_Far36
 jmp SourceAI4086_Check12
SourceAI4086_Far36:
.a16
.i16
 jmp SourceAI4086_PreflightBad
SourceAI4086_Check12:
.a16
.i16
 lda.l SourceModelAnimationCopy4086_Ready
 cmp #$B4E9
 bne SourceAI4086_Far37
 jmp SourceAI4086_Check13
SourceAI4086_Far37:
.a16
.i16
 jmp SourceAI4086_PreflightBad
SourceAI4086_Check13:
.a16
.i16
 jsl SourceUpdateFrame4086_CheckIdle
 bcc SourceAI4086_Far38
 jmp SourceAI4086_PreflightBad
SourceAI4086_Far38:
.a16
.i16
 jsl SourceSelf4086_CheckIdle
 bcc SourceAI4086_Far39
 jmp SourceAI4086_PreflightBad
SourceAI4086_Far39:
.a16
.i16
 lda.l VmSourceWorld_Count
 bne SourceAI4086_Far40
 jmp SourceAI4086_PreflightBad
SourceAI4086_Far40:
.a16
.i16
 cmp #129
 bcc SourceAI4086_Far41
 jmp SourceAI4086_PreflightBad
SourceAI4086_Far41:
.a16
.i16
 lda.l SourceWorldTick4086_Slot
 cmp.l VmSourceWorld_Count
 bcc SourceAI4086_Far42
 jmp SourceAI4086_PreflightBad
SourceAI4086_Far42:
.a16
.i16
 lda.l SourceAI4086_State
 bne SourceAI4086_Far43
 jmp SourceAI4086_FirstSlot
SourceAI4086_Far43:
.a16
.i16
 cmp #5
 bne SourceAI4086_Far44
 jmp SourceAI4086_FirstSlot
SourceAI4086_Far44:
.a16
.i16
 lda.l SourceWorldTick4086_Slot
 cmp.l SourceAI4086_Slot
 beq SourceAI4086_Far45
 jmp SourceAI4086_PreflightBad
SourceAI4086_Far45:
.a16
.i16
SourceAI4086_FirstSlot:
.a16
.i16
 lda.l SourceWorldTick4086_Slot
 sta.l SourceAI4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l SourceAI4086_Flags
 asl a
 sta.l SourceAI4086_Side
 lsr a
 lsr a
 clc
 adc.l SourceAI4086_Side
 sta.l SourceAI4086_Life
 adc #$4000
 sta.l SourceAI4086_View
 cmp.l SourceSelf4086_GlobalLow
 beq SourceAI4086_Far46
 jmp SourceAI4086_PreflightBad
SourceAI4086_Far46:
.a16
.i16
 lda.l SourceSelf4086_GlobalHigh
 cmp #$0041
 beq SourceAI4086_Far47
 jmp SourceAI4086_PreflightBad
SourceAI4086_Far47:
.a16
.i16
 lda.l SourceAI4086_View
 tax
 cmp.l $410000,x
 beq SourceAI4086_Far48
 jmp SourceAI4086_PreflightBad
SourceAI4086_Far48:
.a16
.i16
 lda.l $410002,x
 cmp #$0041
 beq SourceAI4086_Far49
 jmp SourceAI4086_PreflightBad
SourceAI4086_Far49:
.a16
.i16
 lda.l SourceAI4086_Life
 lsr a
 sta.l SourceAI4086_Freeze
 lda.l SourceModelAnimationCopy4086_Maximum
 bne SourceAI4086_Far50
 jmp SourceAI4086_PreflightBad
SourceAI4086_Far50:
.a16
.i16
 cmp #1025
 bcc SourceAI4086_Far51
 jmp SourceAI4086_PreflightBad
SourceAI4086_Far51:
.a16
.i16
 cmp.l SourceAI4086_SpawnID
 bcs SourceAI4086_Far52
 jmp SourceAI4086_PreflightBad
SourceAI4086_Far52:
.a16
.i16
 bne SourceAI4086_Far53
 jmp SourceAI4086_PreflightBad
SourceAI4086_Far53:
.a16
.i16
 cmp.l SourceAI4086_RespawnID
 bcs SourceAI4086_Far54
 jmp SourceAI4086_PreflightBad
SourceAI4086_Far54:
.a16
.i16
 bne SourceAI4086_Far55
 jmp SourceAI4086_PreflightBad
SourceAI4086_Far55:
.a16
.i16
 asl a
 sta.l SourceAI4086_RowBytes
 lda.l SourceModelAnimationCopy4086_Models
 bne SourceAI4086_Far56
 jmp SourceAI4086_PreflightBad
SourceAI4086_Far56:
.a16
.i16
 cmp #129
 bcc SourceAI4086_Far57
 jmp SourceAI4086_PreflightBad
SourceAI4086_Far57:
.a16
.i16
 tax
 lda #0
SourceAI4086_CacheSize:
.a16
.i16
 clc
 adc.l SourceAI4086_RowBytes
 bcc SourceAI4086_Far58
 jmp SourceAI4086_PreflightBad
SourceAI4086_Far58:
.a16
.i16
 dex
 beq SourceAI4086_Far59
 jmp SourceAI4086_CacheSize
SourceAI4086_Far59:
.a16
.i16
 cmp #8193
 bcc SourceAI4086_Far60
 jmp SourceAI4086_PreflightBad
SourceAI4086_Far60:
.a16
.i16
 cmp.l SourceModelAnimationCopy4086_Bytes
 beq SourceAI4086_Far61
 jmp SourceAI4086_PreflightBad
SourceAI4086_Far61:
.a16
.i16
 lda.l SourceAI4086_Side
 tax
 lda.l $416800,x
 cmp.l SourceModelAnimationCopy4086_Models
 bcc SourceAI4086_Far62
 jmp SourceAI4086_PreflightBad
SourceAI4086_Far62:
.a16
.i16
 sta.l SourceAI4086_Model
 tax
 lda #0
 cpx #0
 bne SourceAI4086_Far63
 jmp SourceAI4086_ModelDone
SourceAI4086_Far63:
.a16
.i16
SourceAI4086_ModelLoop:
.a16
.i16
 clc
 adc.l SourceAI4086_RowBytes
 dex
 beq SourceAI4086_Far64
 jmp SourceAI4086_ModelLoop
SourceAI4086_Far64:
.a16
.i16
SourceAI4086_ModelDone:
.a16
.i16
 sta.l SourceAI4086_ModelOffset
 clc
 rts
SourceAI4086_PreflightBad:
.a16
.i16
 sec
 rts

; Public read-only ownership check for actual callback backends.
SourceAI4086_CheckOwner:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jsr SourceAI4086_Preflight
 bcc SourceAI4086_CheckOwnerGood
 ply
 plx
 plp
 sec
 rtl
SourceAI4086_CheckOwnerGood:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
