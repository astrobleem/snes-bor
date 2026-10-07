; Pure admission of an offline native-constructor continuation (B4NC).
; B612 installer validates complete table/instruction/metadata CRC/SHA pairing.
; B613 Request is posted by an admitted native API before cooperative yield.
; This entry does not capture slots, retain strings, or execute a constructor.
; It rejects stale caller/frame/callsite identity before any actor mutation.
SourceNativeContinuation4086_Ready = $40BF90
SourceNativeContinuation4086_State = $40BF92
SourceNativeContinuation4086_Base = $40BF94
SourceNativeContinuation4086_Bank = $40BF96
SourceNativeContinuation4086_Bytes = $40BF98
SourceNativeContinuation4086_Count = $40BF9A
SourceNativeContinuation4086_Record = $40BF9C
SourceNativeContinuation4086_Row = $40BF9E
SourceNativeContinuation4086_Frames = $40BFA0
SourceNativeContinuation4086_Slots = $40BFA2
SourceNativeContinuation4086_Payload = $40BFA4
SourceNativeContinuation4086_SlotList = $40BFA6
SourceNativeContinuation4086_Cursor = $40BFA8
SourceNativeContinuation4086_RowEnd = $40BFAA
SourceNativeContinuation4086_ResultSlot = $40BFAC
SourceNativeContinuation4086_Request = $40BFAE
SourceNativeContinuation4086_End = $40BFB0
SourceNativeRequest4086_Ready = $40BFBE ; B615 named constructor request adapter
SourceNativeRequest4086_End = $40BFC0
SOURCE_NATIVE_CONTEXT_BYTES = 237
SOURCE_NATIVE_SNAPSHOT_BYTES = 512

SourceNativeContinuation4086_Match:
.a16
.i16
 php
 rep #$38
 phx
 phy
 phd
 tsc
 sec
 sbc #10
 tcs
 inc a
 tcd
 lda.l SourceNativeContinuation4086_Ready
 cmp #$B612
 beq SourceNativeContinuation4086_Check0
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check0:
.a16
.i16
 lda.l SourceNativeContinuation4086_State
 beq SourceNativeContinuation4086_Start
 cmp #2
 beq SourceNativeContinuation4086_Start
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Start:
.a16
.i16
 lda.l SourceNativeContinuation4086_Request
 cmp #$B613
 beq SourceNativeContinuation4086_Check1
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check1:
.a16
.i16
 lda.l SourceVMRun4086_Ready
 cmp #$B4D7
 beq SourceNativeContinuation4086_Check2
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check2:
.a16
.i16
 lda.l SourceVMRun4086_Busy
 beq SourceNativeContinuation4086_Check3
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check3:
.a16
.i16
 lda.l VmState_Status
 and #$00FF
 cmp #VMSTAT_YIELDED
 beq SourceNativeContinuation4086_Check4
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check4:
.a16
.i16
 lda.l VmState_Budget
 beq SourceNativeContinuation4086_Check5
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check5:
.a16
.i16
 lda.l SourceAnimationCallback4086_Ready
 cmp #$B4E6
 beq SourceNativeContinuation4086_Check6
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check6:
.a16
.i16
 lda.l SourceAnimationCallback4086_State
 cmp #1
 beq SourceNativeContinuation4086_CallbackState
 cmp #2
 beq SourceNativeContinuation4086_CallbackState
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_CallbackState:
.a16
.i16
 lda.l VmSourceCallback_Ready
 cmp #$B4A5
 beq SourceNativeContinuation4086_Check7
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check7:
.a16
.i16
 lda.l VmSourceCallback_Active
 cmp #$B4A6
 beq SourceNativeContinuation4086_Check8
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check8:
.a16
.i16
 lda.l SourceUpdateFrame4086_Ready
 cmp #$B4E3
 beq SourceNativeContinuation4086_Check9
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check9:
.a16
.i16
 lda.l SourceUpdateFrame4086_State
 cmp #1
 beq SourceNativeContinuation4086_Check10
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check10:
.a16
.i16
 lda.l SourceUpdateFrame4086_Pending
 cmp #1
 beq SourceNativeContinuation4086_Check11
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check11:
.a16
.i16
 lda.l SourceFrameStack4086_Ready
 cmp #$B4ED
 beq SourceNativeContinuation4086_Check12
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check12:
.a16
.i16
 lda.l SourceFrameStack4086_Fault
 beq SourceNativeContinuation4086_Check13
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check13:
.a16
.i16
 lda.l SourceFrameStack4086_Depth
 cmp #7
 bcc SourceNativeContinuation4086_Check14
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check14:
.a16
.i16
 lda.l VmState_SlotCount
 bne SourceNativeContinuation4086_Check15
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check15:
.a16
.i16
 cmp #1025
 bcc SourceNativeContinuation4086_Check16
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check16:
.a16
.i16
 lda.l SourceNativeContinuation4086_Count
 bne SourceNativeContinuation4086_Check17
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check17:
.a16
.i16
 cmp #1025
 bcc SourceNativeContinuation4086_Check18
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check18:
.a16
.i16
 lda.l SourceNativeContinuation4086_Bank
 bne SourceNativeContinuation4086_Check19
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check19:
.a16
.i16
 cmp #64
 bcc SourceNativeContinuation4086_Check20
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check20:
.a16
.i16
 sta $02
 lda.l SourceNativeContinuation4086_Base
 cmp #$8000
 bcs SourceNativeContinuation4086_Check21
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check21:
.a16
.i16
 sta $00
 lda.l SourceNativeContinuation4086_Bytes
 cmp #52
 bcs SourceNativeContinuation4086_Check22
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check22:
.a16
.i16
 cmp #$8001
 bcc SourceNativeContinuation4086_Check23
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check23:
.a16
.i16
 clc
 adc $00
 bcc SourceNativeContinuation4086_Bounds
 beq SourceNativeContinuation4086_Bounds
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Bounds:
.a16
.i16
 ldy #0
 lda [$00],y
 cmp #$3442
 beq SourceNativeContinuation4086_Check24
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check24:
.a16
.i16
 ldy #2
 lda [$00],y
 cmp #$434E
 beq SourceNativeContinuation4086_Check25
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check25:
.a16
.i16
 ldy #4
 lda [$00],y
 cmp #1
 beq SourceNativeContinuation4086_Check26
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check26:
.a16
.i16
 ldy #8
 lda [$00],y
 cmp #4
 beq SourceNativeContinuation4086_Check27
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check27:
.a16
.i16
 ldy #10
 lda [$00],y
 cmp #0
 beq SourceNativeContinuation4086_Check28
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check28:
.a16
.i16
 ldy #14
 lda [$00],y
 cmp #0
 beq SourceNativeContinuation4086_Check29
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check29:
.a16
.i16
 ldy #28
 lda [$00],y
 cmp #0
 beq SourceNativeContinuation4086_Check30
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check30:
.a16
.i16
 ldy #30
 lda [$00],y
 cmp #0
 beq SourceNativeContinuation4086_Check31
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check31:
.a16
.i16
 ldy #6
 lda [$00],y
 cmp.l SourceNativeContinuation4086_Count
 beq SourceNativeContinuation4086_Check32
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check32:
.a16
.i16
 lda.l SourceNativeContinuation4086_Bytes
 sec
 sbc #32
 ldy #12
 cmp [$00],y
 beq SourceNativeContinuation4086_Check33
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check33:
.a16
.i16
 lda.l SourceNativeContinuation4086_Count
 asl a
 asl a
 clc
 adc #32
 sta $04
 cmp.l SourceNativeContinuation4086_Bytes
 bcc SourceNativeContinuation4086_Check34
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check34:
.a16
.i16
 lda #0
 sta.l SourceNativeContinuation4086_Record
SourceNativeContinuation4086_NextRecord:
.a16
.i16
 lda.l SourceNativeContinuation4086_Record
 cmp.l SourceNativeContinuation4086_Count
 bcc SourceNativeContinuation4086_Directory
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Directory:
.a16
.i16
 asl a
 asl a
 clc
 adc #32
 tay
 lda [$00],y
 cmp $04
 bcs SourceNativeContinuation4086_Check35
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check35:
.a16
.i16
 sta.l SourceNativeContinuation4086_Row
 iny
 iny
 lda [$00],y
 cmp #16
 bcs SourceNativeContinuation4086_Check36
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check36:
.a16
.i16
 clc
 adc.l SourceNativeContinuation4086_Row
 bcc SourceNativeContinuation4086_Check37
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check37:
.a16
.i16
 sta.l SourceNativeContinuation4086_RowEnd
 cmp.l SourceNativeContinuation4086_Bytes
 bcc SourceNativeContinuation4086_RowBounds
 beq SourceNativeContinuation4086_RowBounds
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_RowBounds:
.a16
.i16
 lda.l SourceNativeContinuation4086_Row
 tay
 lda.l SourceNativeContinuation4086_Row
 clc
 adc #0
 tay
 lda [$00],y
 cmp.l SourceAnimationCallback4086_Program
 beq SourceNativeContinuation4086_Key0
 jmp SourceNativeContinuation4086_Advance
SourceNativeContinuation4086_Key0:
.a16
.i16
 lda.l SourceNativeContinuation4086_Row
 clc
 adc #2
 tay
 lda [$00],y
 cmp.l VmState_Ip
 beq SourceNativeContinuation4086_Key2
 jmp SourceNativeContinuation4086_Advance
SourceNativeContinuation4086_Key2:
.a16
.i16
 lda.l SourceNativeContinuation4086_Row
 clc
 adc #4
 tay
 lda [$00],y
 cmp.l VmCall_TargetId
 beq SourceNativeContinuation4086_Key4
 jmp SourceNativeContinuation4086_Advance
SourceNativeContinuation4086_Key4:
.a16
.i16
 lda.l SourceNativeContinuation4086_Row
 clc
 adc #6
 tay
 lda [$00],y
 cmp.l VmPriv_C
 beq SourceNativeContinuation4086_Key6
 jmp SourceNativeContinuation4086_Advance
SourceNativeContinuation4086_Key6:
.a16
.i16
 lda.l SourceNativeContinuation4086_Row
 clc
 adc #8
 tay
 lda [$00],y
 sta.l SourceNativeContinuation4086_ResultSlot
 cmp.l VmState_SlotCount
 bcc SourceNativeContinuation4086_Check38
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check38:
.a16
.i16
 iny
 iny
 lda [$00],y
 sta.l SourceNativeContinuation4086_Frames
 cmp.l VmState_FrameTop
 beq SourceNativeContinuation4086_Check39
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check39:
.a16
.i16
 cmp #65
 bcc SourceNativeContinuation4086_Check40
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check40:
.a16
.i16
 iny
 iny
 lda [$00],y
 sta.l SourceNativeContinuation4086_Slots
 bne SourceNativeContinuation4086_Check41
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check41:
.a16
.i16
 cmp #1025
 bcc SourceNativeContinuation4086_Check42
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check42:
.a16
.i16
 iny
 iny
 lda [$00],y
 sta.l SourceNativeContinuation4086_Payload
 cmp #SOURCE_NATIVE_SNAPSHOT_BYTES+1
 bcc SourceNativeContinuation4086_Check43
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check43:
.a16
.i16
 lda.l SourceNativeContinuation4086_Frames
 clc
 adc.l SourceNativeContinuation4086_Slots
 asl a
 clc
 adc #16
 clc
 adc.l SourceNativeContinuation4086_Row
 cmp.l SourceNativeContinuation4086_RowEnd
 beq SourceNativeContinuation4086_Check44
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check44:
.a16
.i16
 lda.l SourceNativeContinuation4086_Frames
 asl a
 asl a
 sta $06
 asl a
 clc
 adc $06
 sta $06
 lda.l SourceNativeContinuation4086_Slots
 asl a
 asl a
 asl a
 clc
 adc $06
 clc
 adc #SOURCE_NATIVE_CONTEXT_BYTES
 cmp.l SourceNativeContinuation4086_Payload
 beq SourceNativeContinuation4086_Check45
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check45:
.a16
.i16
 lda.l SourceNativeContinuation4086_Row
 clc
 adc #16
 sta.l SourceNativeContinuation4086_Cursor
 lda #0
 sta $06
 ldx #0
SourceNativeContinuation4086_FrameLoop:
.a16
.i16
 lda $06
 cmp.l SourceNativeContinuation4086_Frames
 bcc SourceNativeContinuation4086_FrameBody
 jmp SourceNativeContinuation4086_SlotStart
SourceNativeContinuation4086_FrameBody:
.a16
.i16
 lda.l SourceNativeContinuation4086_Cursor
 tay
 lda [$00],y
 cmp.l VmFrames_Wram+4,x
 beq SourceNativeContinuation4086_Check46
 jmp SourceNativeContinuation4086_Advance
SourceNativeContinuation4086_Check46:
.a16
.i16
 lda.l SourceNativeContinuation4086_Cursor
 clc
 adc #2
 sta.l SourceNativeContinuation4086_Cursor
 txa
 clc
 adc #12
 tax
 inc $06
 jmp SourceNativeContinuation4086_FrameLoop
SourceNativeContinuation4086_SlotStart:
.a16
.i16
 lda.l SourceNativeContinuation4086_Cursor
 sta.l SourceNativeContinuation4086_SlotList
 lda #0
 sta $06
 sta $08
SourceNativeContinuation4086_SlotLoop:
.a16
.i16
 lda $06
 cmp.l SourceNativeContinuation4086_Slots
 bcc SourceNativeContinuation4086_SlotBody
 lda $08
 bne SourceNativeContinuation4086_Good
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_SlotBody:
.a16
.i16
 lda.l SourceNativeContinuation4086_Cursor
 tay
 lda [$00],y
 cmp.l VmState_SlotCount
 bcc SourceNativeContinuation4086_Check47
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check47:
.a16
.i16
 ldx $06
 beq SourceNativeContinuation4086_FirstSlot
 cmp $04
 bne SourceNativeContinuation4086_Check48
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check48:
.a16
.i16
 bcs SourceNativeContinuation4086_Check49
 jmp SourceNativeContinuation4086_Bad
SourceNativeContinuation4086_Check49:
.a16
.i16
SourceNativeContinuation4086_FirstSlot:
.a16
.i16
 sta $04
 cmp.l SourceNativeContinuation4086_ResultSlot
 bne SourceNativeContinuation4086_NotResult
 lda #1
 sta $08
SourceNativeContinuation4086_NotResult:
.a16
.i16
 lda.l SourceNativeContinuation4086_Cursor
 clc
 adc #2
 sta.l SourceNativeContinuation4086_Cursor
 inc $06
 jmp SourceNativeContinuation4086_SlotLoop
SourceNativeContinuation4086_Advance:
.a16
.i16
 lda.l SourceNativeContinuation4086_Record
 inc a
 sta.l SourceNativeContinuation4086_Record
 jmp SourceNativeContinuation4086_NextRecord
SourceNativeContinuation4086_Good:
.a16
.i16
 lda #2
 sta.l SourceNativeContinuation4086_State
 tsc
 clc
 adc #10
 tcs
 pld
 ply
 plx
 plp
 clc
 rtl
SourceNativeContinuation4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceNativeContinuation4086_State
 tsc
 clc
 adc #10
 tcs
 pld
 ply
 plx
 plp
 sec
 rtl
