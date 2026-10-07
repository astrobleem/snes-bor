; Immutable B4FC collision descriptor query. Compiler validates complete table.
; Query validates the selected handle/frame and ROM extent before outputs.
; Outputs are current frame indexes, not a grant of target/world authority.
SourceCollisionFrame4086_Ready = $43BD7E
SourceCollisionFrame4086_Bank = $43BD80 ; LoROM bank 0..63, table at $8000
SourceCollisionFrame4086_Bytes = $43BD82
SourceCollisionFrame4086_Handle = $43BD84
SourceCollisionFrame4086_Frame = $43BD86
SourceCollisionFrame4086_Status = $43BD88 ; 0 idle,2 complete,3 fault
SourceCollisionFrame4086_Box = $43BD8A
SourceCollisionFrame4086_Attack = $43BD8C
SourceCollisionFrame4086_Vulnerable = $43BD8E
SourceCollisionFrame4086_Offset = $43BD90
SourceCollisionFrame4086_EntitySlot = $43BD92
SourceCollisionFrame4086_EntityView = $43BD94
SourceCollisionFrame4086_EntitySide = $43BD96
SourceCollisionFrame4086_End = $43BD98
; A=physical entity slot. Resolve the current live animation cursor; do not
; use the birth model/cache slot, which can differ after a source model switch.
SourceCollisionFrame4086_QueryEntity:
.a16
.i16
 php
 rep #$38
 phx
 phy
 cmp #128
 bcc SourceCollisionFrame4086_EntitySlotOK
 jmp SourceCollisionFrame4086_EntityBad
SourceCollisionFrame4086_EntitySlotOK:
.a16
.i16
 sta.l SourceCollisionFrame4086_EntitySlot
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceCollisionFrame4086_EntityWorld
 jmp SourceCollisionFrame4086_EntityBad
SourceCollisionFrame4086_EntityWorld:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourceCollisionFrame4086_EntityPool
 jmp SourceCollisionFrame4086_EntityBad
SourceCollisionFrame4086_EntityPool:
.a16
.i16
 lda.l VmSourceWorld_SideBase
 cmp #$6800
 beq SourceCollisionFrame4086_EntitySideBase
 jmp SourceCollisionFrame4086_EntityBad
SourceCollisionFrame4086_EntitySideBase:
.a16
.i16
 lda.l VmSourceWorld_Count
 cmp #129
 bcc SourceCollisionFrame4086_EntityCount
 jmp SourceCollisionFrame4086_EntityBad
SourceCollisionFrame4086_EntityCount:
.a16
.i16
 cmp.l SourceCollisionFrame4086_EntitySlot
 bne SourceCollisionFrame4086_EntityNotEqual
 jmp SourceCollisionFrame4086_EntityBad
SourceCollisionFrame4086_EntityNotEqual:
.a16
.i16
 bcs SourceCollisionFrame4086_EntityExtent
 jmp SourceCollisionFrame4086_EntityBad
SourceCollisionFrame4086_EntityExtent:
.a16
.i16
 lda.l SourceCollisionFrame4086_EntitySlot
 asl a
 asl a
 asl a
 asl a
 sta.l SourceCollisionFrame4086_EntityView
 asl a
 asl a
 sta.l SourceCollisionFrame4086_EntitySide
 clc
 adc.l SourceCollisionFrame4086_EntityView
 adc #$4000
 sta.l SourceCollisionFrame4086_EntityView
 tax
 cmp.l $410000,x
 beq SourceCollisionFrame4086_EntityTokenLow
 jmp SourceCollisionFrame4086_EntityBad
SourceCollisionFrame4086_EntityTokenLow:
.a16
.i16
 lda.l $410002,x
 cmp #$0041
 beq SourceCollisionFrame4086_EntityTokenHigh
 jmp SourceCollisionFrame4086_EntityBad
SourceCollisionFrame4086_EntityTokenHigh:
.a16
.i16
 lda.l $410004,x
 ora.l $410006,x
 bne SourceCollisionFrame4086_EntityLive
 jmp SourceCollisionFrame4086_EntityBad
SourceCollisionFrame4086_EntityLive:
.a16
.i16
 lda.l SourceCollisionFrame4086_EntitySide
 tax
 lda.l $416804,x
 sta.l SourceCollisionFrame4086_Handle
 lda.l $416806,x
 sta.l SourceCollisionFrame4086_Frame
 jsl SourceCollisionFrame4086_Query
 bcc SourceCollisionFrame4086_EntityGood
 jmp SourceCollisionFrame4086_EntityBad
SourceCollisionFrame4086_EntityGood:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
SourceCollisionFrame4086_EntityBad:
.a16
.i16
 lda #3
 sta.l SourceCollisionFrame4086_Status
 ply
 plx
 plp
 sec
 rtl
SourceCollisionFrame4086_Query:
.a16
.i16
 php
 rep #$38
 phx
 phy
 phd
 tsc
 sec
 sbc #12
 tcs
 inc a
 tcd
 lda.l SourceCollisionFrame4086_Ready
 cmp #$B5EE
 beq SourceCollisionFrame4086_Lease
 jmp SourceCollisionFrame4086_Bad
SourceCollisionFrame4086_Lease:
.a16
.i16
 lda.l SourceCollisionFrame4086_Status
 beq SourceCollisionFrame4086_Idle
 jmp SourceCollisionFrame4086_Bad
SourceCollisionFrame4086_Idle:
.a16
.i16
 lda.l SourceCollisionFrame4086_Bank
 cmp #64
 bcc SourceCollisionFrame4086_BankOK
 jmp SourceCollisionFrame4086_Bad
SourceCollisionFrame4086_BankOK:
.a16
.i16
 sta $02
 lda #$8000
 sta $00
 lda.l SourceCollisionFrame4086_Bytes
 cmp #24
 bcs SourceCollisionFrame4086_SizeMin
 jmp SourceCollisionFrame4086_Bad
SourceCollisionFrame4086_SizeMin:
.a16
.i16
 cmp #$8001
 bcc SourceCollisionFrame4086_SizeOK
 jmp SourceCollisionFrame4086_Bad
SourceCollisionFrame4086_SizeOK:
.a16
.i16
 ldy #0
 lda [$00],y
 cmp #$3442 ; B4
 beq SourceCollisionFrame4086_Magic1
 jmp SourceCollisionFrame4086_Bad
SourceCollisionFrame4086_Magic1:
.a16
.i16
 ldy #2
 lda [$00],y
 cmp #$4346 ; FC
 beq SourceCollisionFrame4086_Magic2
 jmp SourceCollisionFrame4086_Bad
SourceCollisionFrame4086_Magic2:
.a16
.i16
 ldy #4
 lda [$00],y
 cmp #1
 beq SourceCollisionFrame4086_Version
 jmp SourceCollisionFrame4086_Bad
SourceCollisionFrame4086_Version:
.a16
.i16
 ldy #14
 lda [$00],y
 beq SourceCollisionFrame4086_Header
 jmp SourceCollisionFrame4086_Bad
SourceCollisionFrame4086_Header:
.a16
.i16
 ldy #6
 lda [$00],y
 bne SourceCollisionFrame4086_Count
 jmp SourceCollisionFrame4086_Bad
SourceCollisionFrame4086_Count:
.a16
.i16
 cmp #4095 ; directory extent must fit a LoROM bank
 bcc SourceCollisionFrame4086_CountBound
 jmp SourceCollisionFrame4086_Bad
SourceCollisionFrame4086_CountBound:
.a16
.i16
 sta $04
 asl a
 asl a
 asl a
 clc
 adc #16
 sta $06 ; end of directory
 cmp.l SourceCollisionFrame4086_Bytes
 bcc SourceCollisionFrame4086_Directory
 jmp SourceCollisionFrame4086_Bad
SourceCollisionFrame4086_Directory:
.a16
.i16
 lda.l SourceCollisionFrame4086_Handle
 bne SourceCollisionFrame4086_HandleMin
 jmp SourceCollisionFrame4086_Bad
SourceCollisionFrame4086_HandleMin:
.a16
.i16
 cmp $04
 bcc SourceCollisionFrame4086_HandleOK
 beq SourceCollisionFrame4086_HandleOK
 jmp SourceCollisionFrame4086_Bad
SourceCollisionFrame4086_HandleOK:
.a16
.i16
 dec a
 asl a
 asl a
 asl a
 clc
 adc #16
 tay
 lda [$00],y
 cmp.l SourceCollisionFrame4086_Handle
 beq SourceCollisionFrame4086_Row
 jmp SourceCollisionFrame4086_Bad
SourceCollisionFrame4086_Row:
.a16
.i16
 iny
 iny
 lda [$00],y
 cmp.l SourceCollisionFrame4086_Frame
 bne SourceCollisionFrame4086_FrameNotEqual
 jmp SourceCollisionFrame4086_Bad
SourceCollisionFrame4086_FrameNotEqual:
.a16
.i16
 bcs SourceCollisionFrame4086_FrameOK
 jmp SourceCollisionFrame4086_Bad
SourceCollisionFrame4086_FrameOK:
.a16
.i16
 iny
 iny
 lda [$00],y
 cmp $06
 bcs SourceCollisionFrame4086_DataMin
 jmp SourceCollisionFrame4086_Bad
SourceCollisionFrame4086_DataMin:
.a16
.i16
 sta $04
 iny
 iny
 lda [$00],y
 beq SourceCollisionFrame4086_Data
 jmp SourceCollisionFrame4086_Bad
SourceCollisionFrame4086_Data:
.a16
.i16
 lda.l SourceCollisionFrame4086_Frame
 cmp #2730
 bcc SourceCollisionFrame4086_Multiply
 jmp SourceCollisionFrame4086_Bad
SourceCollisionFrame4086_Multiply:
.a16
.i16
 asl a
 asl a
 sta $06
 asl a
 clc
 adc $06
 clc
 adc $04
 bcc SourceCollisionFrame4086_FrameOffset
 jmp SourceCollisionFrame4086_Bad
SourceCollisionFrame4086_FrameOffset:
.a16
.i16
 sta $06
 clc
 adc #12
 bcc SourceCollisionFrame4086_FrameEnd
 jmp SourceCollisionFrame4086_Bad
SourceCollisionFrame4086_FrameEnd:
.a16
.i16
 cmp.l SourceCollisionFrame4086_Bytes
 bcc SourceCollisionFrame4086_ReadFrame
 beq SourceCollisionFrame4086_ReadFrame
 jmp SourceCollisionFrame4086_Bad
SourceCollisionFrame4086_ReadFrame:
.a16
.i16
 lda $06
 clc
 adc #6
 tay
 lda [$00],y
 beq SourceCollisionFrame4086_FrameReserved
 jmp SourceCollisionFrame4086_Bad
SourceCollisionFrame4086_FrameReserved:
.a16
.i16
 iny
 iny
 lda [$00],y
 sta $08
 iny
 iny
 lda [$00],y
 sta $0A
 ldy #10
 lda [$00],y
 cmp $08
 bcs SourceCollisionFrame4086_BoxOK
 jmp SourceCollisionFrame4086_Bad
SourceCollisionFrame4086_BoxOK:
.a16
.i16
 ldy #12
 lda [$00],y
 cmp $0A
 bcs SourceCollisionFrame4086_Publish
 jmp SourceCollisionFrame4086_Bad
SourceCollisionFrame4086_Publish:
.a16
.i16
 lda $06
 sta.l SourceCollisionFrame4086_Offset
 lda $0A
 sta.l SourceCollisionFrame4086_Attack
 lda $08
 sta.l SourceCollisionFrame4086_Box
 beq SourceCollisionFrame4086_Vulnerability
 lda #1
SourceCollisionFrame4086_Vulnerability:
.a16
.i16
 sta.l SourceCollisionFrame4086_Vulnerable
 lda #2
 sta.l SourceCollisionFrame4086_Status
 tsc
 clc
 adc #12
 tcs
 pld
 ply
 plx
 plp
 clc
 rtl
SourceCollisionFrame4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceCollisionFrame4086_Status
 tsc
 clc
 adc #12
 tcs
 pld
 ply
 plx
 plp
 sec
 rtl
