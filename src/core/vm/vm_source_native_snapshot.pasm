; Native VM snapshot ownership. Uses the next free frame-stack row plus
; its 16-byte tail. B614 installer owns this extension; no new data arena.
; Capture preserves caller VM/frame/slot state and retains dynamic strings.
; Complete refcount/liveness preflight precedes any arena or refcount write.
; The frame owner and the VM snapshot together consume two existing rows.
; Pair push, constructor execution and restore are separate continuation steps.
SourceNativeSnapshot4086_Ready = $40BFB0
SourceNativeSnapshot4086_State = $40BFB2
SourceNativeSnapshot4086_Row = $40BFB4
SourceNativeSnapshot4086_Tail = $40BFB6
SourceNativeSnapshot4086_Cursor = $40BFB8
SourceNativeSnapshot4086_Handle = $40BFBA
SourceNativeSnapshot4086_Counter = $40BFBC
SourceNativeSnapshot4086_End = $40BFBE

SourceNativeSnapshot4086_Capture:
.a16
.i16
 php
 rep #$38
 phb
 phx
 phy
 phd
 tsc
 sec
 sbc #12
 tcs
 inc a
 tcd
 lda.l SourceNativeSnapshot4086_Ready
 cmp #$B614
 beq SourceNativeSnapshot4086_Check0
 jmp SourceNativeSnapshot4086_Bad
SourceNativeSnapshot4086_Check0:
.a16
.i16
 jsl SourceNativeContinuation4086_Match
 bcc SourceNativeSnapshot4086_Check1
 jmp SourceNativeSnapshot4086_Bad
SourceNativeSnapshot4086_Check1:
.a16
.i16
 lda.l SourceNativeContinuation4086_Bank
 sta $02
 lda.l SourceNativeContinuation4086_Base
 sta $00
 lda.l SourceFrameStack4086_Depth
 inc a
 pha
 xba
 asl a
 clc
 adc #$F000
 sta.l SourceNativeSnapshot4086_Row
 pla
 asl a
 asl a
 asl a
 asl a
 clc
 adc #$FD00
 sta.l SourceNativeSnapshot4086_Tail
 tax
 lda.l $430000,x
 cmp #$B614
 bne SourceNativeSnapshot4086_Check2
 jmp SourceNativeSnapshot4086_Bad
SourceNativeSnapshot4086_Check2:
.a16
.i16
 lda #0
 sta $04
SourceNativeSnapshot4086_PreflightSlots:
.a16
.i16
 lda $04
 cmp.l SourceNativeContinuation4086_Slots
 bcc SourceNativeSnapshot4086_PreflightBody
 jmp SourceNativeSnapshot4086_Save
SourceNativeSnapshot4086_PreflightBody:
.a16
.i16
 asl a
 clc
 adc.l SourceNativeContinuation4086_SlotList
 tay
 lda [$00],y
 jsr SourceNativeSnapshot4086_StringHandle
 bcc SourceNativeSnapshot4086_Check3
 jmp SourceNativeSnapshot4086_Bad
SourceNativeSnapshot4086_Check3:
.a16
.i16
 cmp #$FFFF
 bne SourceNativeSnapshot4086_Dynamic
 jmp SourceNativeSnapshot4086_NextPreflight
SourceNativeSnapshot4086_Dynamic:
.a16
.i16
 sta.l SourceNativeSnapshot4086_Handle
 lda #0
 sta $06
 sta.l SourceNativeSnapshot4086_Counter
SourceNativeSnapshot4086_CountAliases:
.a16
.i16
 lda $06
 cmp.l SourceNativeContinuation4086_Slots
 bcc SourceNativeSnapshot4086_AliasBody
 jmp SourceNativeSnapshot4086_CheckRefcount
SourceNativeSnapshot4086_AliasBody:
.a16
.i16
 asl a
 clc
 adc.l SourceNativeContinuation4086_SlotList
 tay
 lda [$00],y
 jsr SourceNativeSnapshot4086_StringHandle
 bcc SourceNativeSnapshot4086_Check4
 jmp SourceNativeSnapshot4086_Bad
SourceNativeSnapshot4086_Check4:
.a16
.i16
 cmp.l SourceNativeSnapshot4086_Handle
 bne SourceNativeSnapshot4086_NextAlias
 lda.l SourceNativeSnapshot4086_Counter
 inc a
 sta.l SourceNativeSnapshot4086_Counter
SourceNativeSnapshot4086_NextAlias:
.a16
.i16
 inc $06
 jmp SourceNativeSnapshot4086_CountAliases
SourceNativeSnapshot4086_CheckRefcount:
.a16
.i16
 lda.l SourceNativeSnapshot4086_Handle
 asl a
 asl a
 asl a
 asl a
 asl a
 asl a
 tax
 lda.l VmStrPool_Wram,x
 and #$00FF
 bne SourceNativeSnapshot4086_Check5
 jmp SourceNativeSnapshot4086_Bad
SourceNativeSnapshot4086_Check5:
.a16
.i16
 clc
 adc.l SourceNativeSnapshot4086_Counter
 cmp #256
 bcc SourceNativeSnapshot4086_Check6
 jmp SourceNativeSnapshot4086_Bad
SourceNativeSnapshot4086_Check6:
.a16
.i16
SourceNativeSnapshot4086_NextPreflight:
.a16
.i16
 inc $04
 jmp SourceNativeSnapshot4086_PreflightSlots
SourceNativeSnapshot4086_Save:
.a16
.i16
 lda #1
 sta.l SourceNativeSnapshot4086_State
 ldx #$E090
 lda.l SourceNativeSnapshot4086_Row
 clc
 adc #0
 tay
 lda #11
 mvn $40,$7F
 ldx #$E09D
 lda.l SourceNativeSnapshot4086_Row
 clc
 adc #12
 tay
 lda #14
 mvn $40,$7F
 ldx #$F600
 lda.l SourceNativeSnapshot4086_Row
 clc
 adc #27
 tay
 lda #71
 mvn $40,$7F
 ldx #$F660
 lda.l SourceNativeSnapshot4086_Row
 clc
 adc #99
 tay
 lda #29
 mvn $40,$7F
 ldx #$F780
 lda.l SourceNativeSnapshot4086_Row
 clc
 adc #129
 tay
 lda #25
 mvn $40,$7F
 ldx #$F7A0
 lda.l SourceNativeSnapshot4086_Row
 clc
 adc #155
 tay
 lda #63
 mvn $40,$7F
 ldx #$FB30
 lda.l SourceNativeSnapshot4086_Row
 clc
 adc #219
 tay
 lda #7
 mvn $40,$7F
 ldx #$F400
 lda.l SourceNativeSnapshot4086_Row
 clc
 adc #227
 tay
 lda #9
 mvn $40,$7F
 lda.l VmState_FrameTop
 beq SourceNativeSnapshot4086_FramesDone
 asl a
 asl a
 sta $06
 asl a
 clc
 adc $06
 sta $06
 dec a
 pha
 lda.l SourceNativeSnapshot4086_Row
 clc
 adc #237
 tay
 ldx #$E100
 pla
 mvn $40,$7F
SourceNativeSnapshot4086_FramesDone:
.a16
.i16
 lda.l SourceNativeContinuation4086_Frames
 asl a
 asl a
 sta $06
 asl a
 clc
 adc $06
 clc
 adc #237
 sta.l SourceNativeSnapshot4086_Cursor
 lda #0
 sta $04
SourceNativeSnapshot4086_CopySlots:
.a16
.i16
 lda $04
 cmp.l SourceNativeContinuation4086_Slots
 bcc SourceNativeSnapshot4086_CopySlotBody
 jmp SourceNativeSnapshot4086_Publish
SourceNativeSnapshot4086_CopySlotBody:
.a16
.i16
 asl a
 clc
 adc.l SourceNativeContinuation4086_SlotList
 tay
 lda [$00],y
 sta $08
 jsr SourceNativeSnapshot4086_StringHandle
 cmp #$FFFF
 beq SourceNativeSnapshot4086_SlotRetained
 asl a
 asl a
 asl a
 asl a
 asl a
 asl a
 tax
 sep #$20
.a8
 lda.l VmStrPool_Wram,x
 inc a
 sta.l VmStrPool_Wram,x
 rep #$38
.a16
.i16
SourceNativeSnapshot4086_SlotRetained:
.a16
.i16
 lda $08
 asl a
 asl a
 asl a
 clc
 adc #$C000
 tax
 lda.l SourceNativeSnapshot4086_Row
 clc
 adc.l SourceNativeSnapshot4086_Cursor
 tay
 lda #7
 mvn $40,$7F
 lda.l SourceNativeSnapshot4086_Cursor
 clc
 adc #8
 sta.l SourceNativeSnapshot4086_Cursor
 inc $04
 jmp SourceNativeSnapshot4086_CopySlots
SourceNativeSnapshot4086_Publish:
.a16
.i16
 lda.l SourceNativeSnapshot4086_Tail
 tax
 lda.l SourceNativeContinuation4086_Record
 sta.l $430002,x
 lda.l SourceNativeContinuation4086_Payload
 sta.l $430004,x
 lda.l SourceNativeContinuation4086_Frames
 sta.l $430006,x
 lda.l SourceNativeContinuation4086_Slots
 sta.l $430008,x
 ldy #16
 lda [$00],y
 sta.l $43000A,x
 iny
 iny
 lda [$00],y
 sta.l $43000C,x
 lda #0
 sta.l $43000E,x
 lda #$B614
 sta.l $430000,x
SourceNativeSnapshot4086_Good:
.a16
.i16
 lda #2
 sta.l SourceNativeSnapshot4086_State
 tsc
 clc
 adc #12
 tcs
 pld
 ply
 plx
 plb
 plp
 clc
 rtl
SourceNativeSnapshot4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceNativeSnapshot4086_State
 tsc
 clc
 adc #12
 tcs
 pld
 ply
 plx
 plb
 plp
 sec
 rtl
; A=slot ID, A=FFFF for non-dynamic cells, else object0..63, C invalid.
SourceNativeSnapshot4086_StringHandle:
.a16
.i16
 asl a
 asl a
 asl a
 tax
 lda.l VmSlots_Wram,x
 and #$00FF
 cmp #BOR_VT_STR
 bne SourceNativeSnapshot4086_NotDynamic
 lda.l VmSlots_Wram+6,x
 bpl SourceNativeSnapshot4086_NotDynamic
 cmp #$8000
 bne SourceNativeSnapshot4086_HandleBad
 lda.l VmSlots_Wram+4,x
 cmp #VMSTRPOOL_OBJ_COUNT
 bcs SourceNativeSnapshot4086_HandleBad
 clc
 rts
SourceNativeSnapshot4086_NotDynamic:
.a16
.i16
 lda #$FFFF
 clc
 rts
SourceNativeSnapshot4086_HandleBad:
.a16
.i16
 sec
 rts
