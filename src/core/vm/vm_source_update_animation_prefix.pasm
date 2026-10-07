; Source update_animation prefix for derived non-scrolling/facing-zero models.
; Ready B60D requires validated B4UP table and stage-facing-zero capability.
; Literal expiry paths needing unfrozen/colourmap remain explicit failures.
; Timed animation advance, frame effects and kill are separate required services.
SourceUpdateAnimationPrefix4086_Ready = $43BFAA
SourceUpdateAnimationPrefix4086_Status = $43BFAC
SourceUpdateAnimationPrefix4086_Base = $43BFAE
SourceUpdateAnimationPrefix4086_Bank = $43BFB0
SourceUpdateAnimationPrefix4086_Bytes = $43BFB2
SourceUpdateAnimationPrefix4086_Models = $43BFB4
SourceUpdateAnimationPrefix4086_SleepID = $43BFB6
SourceUpdateAnimationPrefix4086_SleepWait = $43BFB8
SourceUpdateAnimationPrefix4086_Row = $43BFBC
SourceUpdateAnimationPrefix4086_Slot = $43BFBE
SourceUpdateAnimationPrefix4086_End = $43BFC0
SourceUpdateAnimationPrefix4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 phd
 tsc
 sec
 sbc #16
 tcs
 inc a
 tcd
 lda.l SourceUpdateAnimationPrefix4086_Ready
 cmp #$B60D
 beq SourceUpdateAnimationPrefix4086_Branch1
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch1:
.a16
.i16
 lda.l SourceUpdateAnimationPrefix4086_Status
 bne SourceUpdateAnimationPrefix4086_Branch2
 jmp SourceUpdateAnimationPrefix4086_Start
SourceUpdateAnimationPrefix4086_Branch2:
.a16
.i16
 cmp #2
 beq SourceUpdateAnimationPrefix4086_Branch3
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch3:
.a16
.i16
SourceUpdateAnimationPrefix4086_Start:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceUpdateAnimationPrefix4086_Branch4
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch4:
.a16
.i16
 lda.l SourceWorldTick4086_Ready
 cmp #$B4D5
 beq SourceUpdateAnimationPrefix4086_Branch5
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch5:
.a16
.i16
 lda.l SourceFreeze4086_Ready
 cmp #$B5DF
 beq SourceUpdateAnimationPrefix4086_Branch6
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch6:
.a16
.i16
 lda.l SourceIdle4086_Ready
 cmp #$B4F3
 beq SourceUpdateAnimationPrefix4086_Branch7
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch7:
.a16
.i16
 lda.l SourceLifecycle4086_Ready
 cmp #$B4FB
 beq SourceUpdateAnimationPrefix4086_Branch8
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch8:
.a16
.i16
 lda.l SourceSelf4086_Ready
 cmp #$B4F6
 beq SourceUpdateAnimationPrefix4086_Branch9
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch9:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Ready
 cmp #$B4EB
 beq SourceUpdateAnimationPrefix4086_Branch10
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch10:
.a16
.i16
 lda.l SourceWorldTick4086_State
 cmp #$0001
 beq SourceUpdateAnimationPrefix4086_Branch11
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch11:
.a16
.i16
 lda.l SourceWorldTick4086_Pending
 cmp #$0001
 beq SourceUpdateAnimationPrefix4086_Branch12
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch12:
.a16
.i16
 lda.l SourceWorldTick4086_Phase
 cmp #$0007
 beq SourceUpdateAnimationPrefix4086_Branch13
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch13:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourceUpdateAnimationPrefix4086_Branch14
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch14:
.a16
.i16
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 beq SourceUpdateAnimationPrefix4086_Branch15
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch15:
.a16
.i16
 lda.l SourceSelf4086_Active
 beq SourceUpdateAnimationPrefix4086_Branch16
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch16:
.a16
.i16
 lda.l SourceSelf4086_Fault
 beq SourceUpdateAnimationPrefix4086_Branch17
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch17:
.a16
.i16
 lda.l SourceWorldTick4086_TimeLo
 cmp.l VmSourceWorld_Time
 beq SourceUpdateAnimationPrefix4086_Branch18
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch18:
.a16
.i16
 lda.l SourceWorldTick4086_TimeHi
 cmp.l VmSourceWorld_Time+2
 beq SourceUpdateAnimationPrefix4086_Branch19
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch19:
.a16
.i16
 lda.l SourceUpdateFrame4086_Ready
 cmp #$B4E3
 beq SourceUpdateAnimationPrefix4086_FrameLeaseValid
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_FrameLeaseValid:
.a16
.i16
 jsl SourceUpdateFrame4086_CheckIdle
 bcc SourceUpdateAnimationPrefix4086_Branch20
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch20:
.a16
.i16
 lda.l VmSourceWorld_Count
 bne SourceUpdateAnimationPrefix4086_Branch21
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch21:
.a16
.i16
 cmp #129
 bcc SourceUpdateAnimationPrefix4086_Branch22
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch22:
.a16
.i16
 lda.l SourceWorldTick4086_Slot
 cmp.l VmSourceWorld_Count
 bcc SourceUpdateAnimationPrefix4086_Branch23
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch23:
.a16
.i16
 sta.l SourceUpdateAnimationPrefix4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 sta $06
 asl a
 sta $0E
 clc
 adc $06
 sta $0A
 lda $06
 lsr a
 lsr a
 sta $08
 asl a
 asl a
 clc
 adc $08
 sta $08
 lda $0E
 clc
 adc #$6800
 cmp.l SourceWorldTick4086_Side
 beq SourceUpdateAnimationPrefix4086_Branch24
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch24:
.a16
.i16
 lda $0E
 clc
 adc $06
 lsr a
 clc
 adc $06
 sta $04
 clc
 adc #$4000
 sta $0C
 cmp.l SourceWorldTick4086_View
 beq SourceUpdateAnimationPrefix4086_Branch25
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch25:
.a16
.i16
 cmp.l SourceSelf4086_GlobalLow
 beq SourceUpdateAnimationPrefix4086_Branch26
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch26:
.a16
.i16
 lda.l SourceSelf4086_GlobalHigh
 cmp #$0041
 beq SourceUpdateAnimationPrefix4086_Branch27
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch27:
.a16
.i16
 ldx $0C
 lda.l $410000,x
 cmp $0C
 beq SourceUpdateAnimationPrefix4086_Branch28
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch28:
.a16
.i16
 lda.l $410002,x
 cmp #$0041
 beq SourceUpdateAnimationPrefix4086_Branch29
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch29:
.a16
.i16
 lda.l $410004,x
 ora.l $410006,x
 bne SourceUpdateAnimationPrefix4086_Branch30
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch30:
.a16
.i16
 ldx $0E
 lda.l $416800,x
 cmp.l SourceUpdateAnimationPrefix4086_Models
 bcc SourceUpdateAnimationPrefix4086_Branch31
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch31:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Entities
 cmp.l VmSourceWorld_Count
 bcs SourceUpdateAnimationPrefix4086_CoreRowsValid
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_CoreRowsValid:
.a16
.i16
 ldx $04
 lda.l $43904A,x
 cmp #$B4FB
 beq SourceUpdateAnimationPrefix4086_ModelMarkerValid
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_ModelMarkerValid:
.a16
.i16
 lda.l $439048,x
 sta $0E
 lda.l SourceWorldTick4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 asl a
 tax
 lda.l $416800,x
 cmp $0E
 beq SourceUpdateAnimationPrefix4086_ModelIdentityValid
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_ModelIdentityValid:
.a16
.i16
 lda.l SourceUpdateAnimationPrefix4086_Models
 cmp.l SourceLifecycle4086_Models
 beq SourceUpdateAnimationPrefix4086_LifeModelsValid
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_LifeModelsValid:
.a16
.i16
 lda.l SourceUpdateAnimationPrefix4086_Models
 cmp.l SourceModelEntityCopy4086_Models
 beq SourceUpdateAnimationPrefix4086_Branch32
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch32:
.a16
.i16
 lda.l SourceUpdateAnimationPrefix4086_Models
 bne SourceUpdateAnimationPrefix4086_Branch33
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch33:
.a16
.i16
 cmp #17
 bcc SourceUpdateAnimationPrefix4086_Branch34
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch34:
.a16
.i16
 lda.l $416800,x
 asl a
 asl a
 asl a
 asl a
 clc
 adc #24
 sta.l SourceUpdateAnimationPrefix4086_Row
 adc #16
 cmp.l SourceUpdateAnimationPrefix4086_Bytes
 bne SourceUpdateAnimationPrefix4086_Branch35
 jmp SourceUpdateAnimationPrefix4086_TableBound
SourceUpdateAnimationPrefix4086_Branch35:
.a16
.i16
 bcc SourceUpdateAnimationPrefix4086_Branch36
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch36:
.a16
.i16
SourceUpdateAnimationPrefix4086_TableBound:
.a16
.i16
 lda.l SourceUpdateAnimationPrefix4086_Base
 cmp #$8000
 bcs SourceUpdateAnimationPrefix4086_Branch37
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch37:
.a16
.i16
 clc
 adc.l SourceUpdateAnimationPrefix4086_Bytes
 bcs SourceUpdateAnimationPrefix4086_Branch38
 jmp SourceUpdateAnimationPrefix4086_BankBound
SourceUpdateAnimationPrefix4086_Branch38:
.a16
.i16
 cmp #0
 beq SourceUpdateAnimationPrefix4086_Branch39
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch39:
.a16
.i16
SourceUpdateAnimationPrefix4086_BankBound:
.a16
.i16
 lda.l SourceUpdateAnimationPrefix4086_Bank
 sta $02
 cmp #$0040
 bcc SourceUpdateAnimationPrefix4086_Branch40
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch40:
.a16
.i16
 lda.l SourceUpdateAnimationPrefix4086_Row
 clc
 adc.l SourceUpdateAnimationPrefix4086_Base
 sta $00
 ldy #8
 lda [$00],y
 sta.l SourceUpdateAnimationPrefix4086_SleepWait
 iny
 iny
 lda [$00],y
 sta.l SourceUpdateAnimationPrefix4086_SleepWait+2
 lda.l VmSourceWorld_Level
 cmp #2
 bcc SourceUpdateAnimationPrefix4086_Branch41
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch41:
.a16
.i16
 lda.l VmSourceWorld_Level
 bne SourceUpdateAnimationPrefix4086_Branch42
 jmp SourceUpdateAnimationPrefix4086_NoLevel
SourceUpdateAnimationPrefix4086_Branch42:
.a16
.i16
 ldy #0
 lda [$00],y
 iny
 iny
 ora [$00],y

 beq SourceUpdateAnimationPrefix4086_Branch43
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch43:
.a16
.i16
 iny
 iny
 lda [$00],y
 sta $0E
 iny
 iny
 lda [$00],y
 and #$7FFF
 ora $0E

 beq SourceUpdateAnimationPrefix4086_Branch44
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch44:
.a16
.i16
 ldx $0A
 lda.l $40C048,x
 and #$0400

 beq SourceUpdateAnimationPrefix4086_Branch45
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch45:
.a16
.i16
SourceUpdateAnimationPrefix4086_NoLevel:
.a16
.i16
 ldy #12
 lda [$00],y
 iny
 iny
 ora [$00],y
 bne SourceUpdateAnimationPrefix4086_Branch46
 jmp SourceUpdateAnimationPrefix4086_EscapeDone
SourceUpdateAnimationPrefix4086_Branch46:
.a16
.i16
 ldx $06
 lda.l $43EB04,x
 ora.l $43EB06,x

 bne SourceUpdateAnimationPrefix4086_Branch47
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch47:
.a16
.i16
SourceUpdateAnimationPrefix4086_EscapeDone:
.a16
.i16
 ldx $08
 lda.l $42E004,x
 ora.l $42E006,x
 bne SourceUpdateAnimationPrefix4086_Branch48
 jmp SourceUpdateAnimationPrefix4086_ThawDone
SourceUpdateAnimationPrefix4086_Branch48:
.a16
.i16
 lda.l VmSourceWorld_Time+2
 cmp.l $42E006,x
 bcs SourceUpdateAnimationPrefix4086_Branch49
 jmp SourceUpdateAnimationPrefix4086_ThawDone
SourceUpdateAnimationPrefix4086_Branch49:
.a16
.i16
 beq SourceUpdateAnimationPrefix4086_Branch50
 jmp SourceUpdateAnimationPrefix4086_ThawDone_Expired
SourceUpdateAnimationPrefix4086_Branch50:
.a16
.i16
 lda.l VmSourceWorld_Time
 cmp.l $42E004,x
 bcs SourceUpdateAnimationPrefix4086_Branch51
 jmp SourceUpdateAnimationPrefix4086_ThawDone
SourceUpdateAnimationPrefix4086_Branch51:
.a16
.i16
SourceUpdateAnimationPrefix4086_ThawDone_Expired:
.a16
.i16
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_ThawDone:
.a16
.i16
 ldx $04
 lda.l $439028,x
 ora.l $43902A,x
 bne SourceUpdateAnimationPrefix4086_Branch52
 jmp SourceUpdateAnimationPrefix4086_MapDone
SourceUpdateAnimationPrefix4086_Branch52:
.a16
.i16
 lda.l VmSourceWorld_Time+2
 cmp.l $43902A,x
 bcs SourceUpdateAnimationPrefix4086_Branch53
 jmp SourceUpdateAnimationPrefix4086_MapDone
SourceUpdateAnimationPrefix4086_Branch53:
.a16
.i16
 beq SourceUpdateAnimationPrefix4086_Branch54
 jmp SourceUpdateAnimationPrefix4086_MapDone_Expired
SourceUpdateAnimationPrefix4086_Branch54:
.a16
.i16
 lda.l VmSourceWorld_Time
 cmp.l $439028,x
 bcs SourceUpdateAnimationPrefix4086_Branch55
 jmp SourceUpdateAnimationPrefix4086_MapDone
SourceUpdateAnimationPrefix4086_Branch55:
.a16
.i16
SourceUpdateAnimationPrefix4086_MapDone_Expired:
.a16
.i16
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_MapDone:
.a16
.i16
 ldx $08
 lda.l $42E020,x
 ora.l $42E022,x
 bne SourceUpdateAnimationPrefix4086_Branch56
 jmp SourceUpdateAnimationPrefix4086_SealChecked
SourceUpdateAnimationPrefix4086_Branch56:
.a16
.i16
 lda.l VmSourceWorld_Time+2
 cmp.l $42E022,x
 bcs SourceUpdateAnimationPrefix4086_Branch57
 jmp SourceUpdateAnimationPrefix4086_SealChecked
SourceUpdateAnimationPrefix4086_Branch57:
.a16
.i16
 beq SourceUpdateAnimationPrefix4086_Branch58
 jmp SourceUpdateAnimationPrefix4086_SealChecked_Expired
SourceUpdateAnimationPrefix4086_Branch58:
.a16
.i16
 lda.l VmSourceWorld_Time
 cmp.l $42E020,x
 bcs SourceUpdateAnimationPrefix4086_Branch59
 jmp SourceUpdateAnimationPrefix4086_SealChecked
SourceUpdateAnimationPrefix4086_Branch59:
.a16
.i16
SourceUpdateAnimationPrefix4086_SealChecked_Expired:
.a16
.i16
 lda $08
 lsr a
 tax
 lda.l $437E10,x
 cmp #$B5FB
 beq SourceUpdateAnimationPrefix4086_Branch60
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch60:
.a16
.i16
 lda.l $437E12,x
 beq SourceUpdateAnimationPrefix4086_Branch61
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch61:
.a16
.i16
SourceUpdateAnimationPrefix4086_SealChecked:
.a16
.i16
 ldx $06
 lda.l $43EB00,x
 and #2
 bne SourceUpdateAnimationPrefix4086_Branch62
 jmp SourceUpdateAnimationPrefix4086_Sleep
SourceUpdateAnimationPrefix4086_Branch62:
.a16
.i16
 ldx $0C
 lda.l $410010,x
 cmp #BOR_VT_INTEGER
 beq SourceUpdateAnimationPrefix4086_Branch63
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch63:
.a16
.i16
 lda.l $410012,x
 beq SourceUpdateAnimationPrefix4086_Branch64
 jmp SourceUpdateAnimationPrefix4086_Bad
SourceUpdateAnimationPrefix4086_Branch64:
.a16
.i16
 lda.l $410016,x
 beq SourceUpdateAnimationPrefix4086_Branch65
 jmp SourceUpdateAnimationPrefix4086_SleepDone
SourceUpdateAnimationPrefix4086_Branch65:
.a16
.i16
 lda.l $410014,x
 cmp.l SourceUpdateAnimationPrefix4086_SleepID
 beq SourceUpdateAnimationPrefix4086_Branch66
 jmp SourceUpdateAnimationPrefix4086_SleepDone
SourceUpdateAnimationPrefix4086_Branch66:
.a16
.i16
 lda $08
 lsr a
 tax
 lda.l $41F510,x
 beq SourceUpdateAnimationPrefix4086_Branch67
 jmp SourceUpdateAnimationPrefix4086_SleepDone
SourceUpdateAnimationPrefix4086_Branch67:
.a16
.i16
SourceUpdateAnimationPrefix4086_Sleep:
.a16
.i16
 ldx $06
 lda.l VmSourceWorld_Time
 clc
 adc.l SourceUpdateAnimationPrefix4086_SleepWait
 sta.l $43EB18,x
 lda.l VmSourceWorld_Time+2
 adc.l SourceUpdateAnimationPrefix4086_SleepWait+2
 sta.l $43EB1A,x
SourceUpdateAnimationPrefix4086_SleepDone:
.a16
.i16
 ldx $04
 lda.l $439018,x
 ora.l $43901A,x
 bne SourceUpdateAnimationPrefix4086_Branch68
 jmp SourceUpdateAnimationPrefix4086_InvinDone
SourceUpdateAnimationPrefix4086_Branch68:
.a16
.i16
 lda.l VmSourceWorld_Time+2
 cmp.l $439022,x
 bcs SourceUpdateAnimationPrefix4086_Branch69
 jmp SourceUpdateAnimationPrefix4086_InvinDone
SourceUpdateAnimationPrefix4086_Branch69:
.a16
.i16
 beq SourceUpdateAnimationPrefix4086_Branch70
 jmp SourceUpdateAnimationPrefix4086_InvinExpired
SourceUpdateAnimationPrefix4086_Branch70:
.a16
.i16
 lda.l VmSourceWorld_Time
 cmp.l $439020,x
 bcs SourceUpdateAnimationPrefix4086_Branch71
 jmp SourceUpdateAnimationPrefix4086_InvinDone
SourceUpdateAnimationPrefix4086_Branch71:
.a16
.i16
SourceUpdateAnimationPrefix4086_InvinExpired:
.a16
.i16
 lda #0
 ldy #16
SourceUpdateAnimationPrefix4086_ClearInvin:
.a16
.i16
 sta.l $439018,x
 inx
 inx
 dey
 dey
 beq SourceUpdateAnimationPrefix4086_Branch72
 jmp SourceUpdateAnimationPrefix4086_ClearInvin
SourceUpdateAnimationPrefix4086_Branch72:
.a16
.i16
SourceUpdateAnimationPrefix4086_InvinDone:
.a16
.i16
 ldx $08
 lda.l $42E020,x
 ora.l $42E022,x
 bne SourceUpdateAnimationPrefix4086_Branch73
 jmp SourceUpdateAnimationPrefix4086_SealDone
SourceUpdateAnimationPrefix4086_Branch73:
.a16
.i16
 lda.l VmSourceWorld_Time+2
 cmp.l $42E022,x
 bcs SourceUpdateAnimationPrefix4086_Branch74
 jmp SourceUpdateAnimationPrefix4086_SealDone
SourceUpdateAnimationPrefix4086_Branch74:
.a16
.i16
 beq SourceUpdateAnimationPrefix4086_Branch75
 jmp SourceUpdateAnimationPrefix4086_SealDone_Expired
SourceUpdateAnimationPrefix4086_Branch75:
.a16
.i16
 lda.l VmSourceWorld_Time
 cmp.l $42E020,x
 bcs SourceUpdateAnimationPrefix4086_Branch76
 jmp SourceUpdateAnimationPrefix4086_SealDone
SourceUpdateAnimationPrefix4086_Branch76:
.a16
.i16
SourceUpdateAnimationPrefix4086_SealDone_Expired:
.a16
.i16
 lda $08
 lsr a
 tax
 lda #0
 sta.l $437E04,x
 sta.l $437E06,x
SourceUpdateAnimationPrefix4086_SealDone:
.a16
.i16
 lda #2
 sta.l SourceUpdateAnimationPrefix4086_Status
 tsc
 clc
 adc #16
 tcs
 pld
 ply
 plx
 lda #0
 plp
 clc
 rtl
SourceUpdateAnimationPrefix4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceUpdateAnimationPrefix4086_Status
 tsc
 clc
 adc #16
 tcs
 pld
 ply
 plx
 lda #0
 plp
 sec
 rtl
