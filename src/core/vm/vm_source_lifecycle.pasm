; B4FB synchronous current-model scalar install. Isolated BW-RAM lease.
; 128 x 80 bytes at $439000..$43B7FF. Callback identities are not executable pointers.
; Reset=1 clears the full entity lifecycle row; Reset=0 preserves lifecycle fields.
SourceLifecycle4086_Ready = $7FFE9C
SourceLifecycle4086_Slot = $7FFE9E
SourceLifecycle4086_Model = $7FFEA0
SourceLifecycle4086_Status = $7FFEA2
SourceLifecycle4086_Base = $7FFEA4
SourceLifecycle4086_Bank = $7FFEA6
SourceLifecycle4086_Bytes = $7FFEA8
SourceLifecycle4086_Models = $7FFEAA
SourceLifecycle4086_Reset = $7FFEAC
SourceLifecycle4086_Row = $7FFEAE
SourceLifecycle4086_Entity = $7FFEB0
SourceLifecycle4086_End = $7FFEB2
SourceLifecycle4086_Index = $7FFEB4
SourceLifecycle4086_Value = $7FFEB6

SourceLifecycle4086_Preflight:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceLifecycle4086_Ready
 cmp #$B4FB
 beq SourceLifecycle4086_Guard_1
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_1:
.a16
.i16
 lda.l SourceLifecycle4086_Status
 cmp #3
 bne SourceLifecycle4086_Guard_2
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_2:
.a16
.i16
 lda.l SourceLifecycle4086_Reset
 cmp #2
 bcc SourceLifecycle4086_Guard_3
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_3:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceLifecycle4086_Guard_4
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_4:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourceLifecycle4086_Guard_5
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_5:
.a16
.i16
 lda.l VmSourceWorld_Count
 bne SourceLifecycle4086_Guard_6
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_6:
.a16
.i16
 cmp #129
 bcc SourceLifecycle4086_Guard_7
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_7:
.a16
.i16
 cmp.l SourceLifecycle4086_Slot
 bne SourceLifecycle4086_Guard_8
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_8:
.a16
.i16
 cmp.l SourceLifecycle4086_Slot
 bcs SourceLifecycle4086_Guard_9
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_9:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Ready
 cmp #$B4EB
 beq SourceLifecycle4086_Guard_10
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_10:
.a16
.i16
 lda.l VmSourceWorld_Count
 cmp.l SourceModelEntityCopy4086_Entities
 beq SourceLifecycle4086_Guard_11
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_11:
.a16
.i16
 lda.l SourceLifecycle4086_Models
 bne SourceLifecycle4086_Guard_12
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_12:
.a16
.i16
 cmp #17
 bcc SourceLifecycle4086_Guard_13
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_13:
.a16
.i16
 cmp.l SourceModelEntityCopy4086_Models
 beq SourceLifecycle4086_Guard_14
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_14:
.a16
.i16
 cmp.l SourceLifecycle4086_Model
 bne SourceLifecycle4086_Guard_15
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_15:
.a16
.i16
 cmp.l SourceLifecycle4086_Model
 bcs SourceLifecycle4086_Guard_16
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_16:
.a16
.i16
 lda.l SourceLifecycle4086_Base
 cmp #$8000
 bcs SourceLifecycle4086_Guard_17
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_17:
.a16
.i16
 clc
 adc.l SourceLifecycle4086_Bytes
 bcc SourceLifecycle4086_Guard_18
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_18:
.a16
.i16
 sta.l SourceLifecycle4086_End
 lda.l SourceLifecycle4086_Bank
 cmp #$40
 bcc SourceLifecycle4086_Guard_19
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_19:
.a16
.i16
 lda.l SourceLifecycle4086_Models
 asl a
 asl a
 asl a
 asl a
 asl a
 clc
 adc #24
 cmp.l SourceLifecycle4086_Bytes
 beq SourceLifecycle4086_Guard_20
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_20:
.a16
.i16
 lda.l SourceLifecycle4086_Base
 tax
 jsr SourceLifecycle4086_Read
 cmp #$3442
 beq SourceLifecycle4086_Guard_21
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_21:
.a16
.i16
 inx
 inx
 jsr SourceLifecycle4086_Read
 cmp #$494C
 beq SourceLifecycle4086_Guard_22
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_22:
.a16
.i16
 inx
 inx
 jsr SourceLifecycle4086_Read
 cmp #1
 beq SourceLifecycle4086_Guard_23
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_23:
.a16
.i16
 inx
 inx
 jsr SourceLifecycle4086_Read
 cmp #32
 beq SourceLifecycle4086_Guard_24
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_24:
.a16
.i16
 inx
 inx
 jsr SourceLifecycle4086_Read
 cmp.l SourceLifecycle4086_Models
 beq SourceLifecycle4086_Guard_25
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_25:
.a16
.i16
 lda.l SourceLifecycle4086_Model
 asl a
 asl a
 asl a
 asl a
 asl a
 clc
 adc #24
 clc
 adc.l SourceLifecycle4086_Base
 sta.l SourceLifecycle4086_Row
 tax
 jsr SourceLifecycle4086_Read
 cmp.l SourceLifecycle4086_Model
 beq SourceLifecycle4086_Guard_26
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_26:
.a16
.i16
 inx
 inx
 jsr SourceLifecycle4086_Read
 beq SourceLifecycle4086_Guard_27
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_27:
.a16
.i16
 inx
 inx
 jsr SourceLifecycle4086_Read
 cmp #12
 bcc SourceLifecycle4086_Guard_28
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_28:
.a16
.i16
 inx
 inx
 jsr SourceLifecycle4086_Read
 beq SourceLifecycle4086_Guard_29
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_29:
.a16
.i16
 lda.l SourceLifecycle4086_Row
 clc
 adc #12
 tax
 jsr SourceLifecycle4086_Read
 sta.l SourceLifecycle4086_Value
 inx
 inx
 jsr SourceLifecycle4086_Read
 cmp #$8000
 bne SourceLifecycle4086_MakeInvGood
 lda.l SourceLifecycle4086_Value
 bne SourceLifecycle4086_MakeInvGood
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_MakeInvGood:
.a16
.i16
 lda.l SourceLifecycle4086_Row
 clc
 adc #22
 tax
 jsr SourceLifecycle4086_Read
 and #$7F80
 cmp #$7F80
 bne SourceLifecycle4086_Guard_30
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_30:
.a16
.i16
 lda.l SourceLifecycle4086_Row
 clc
 adc #24
 tax
 ldy #4
SourceLifecycle4086_Reserved:
.a16
.i16
 jsr SourceLifecycle4086_Read
 beq SourceLifecycle4086_Guard_31
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_31:
.a16
.i16
 inx
 inx
 dey
 bne SourceLifecycle4086_Reserved
 lda.l SourceLifecycle4086_Slot
 asl a
 asl a
 asl a
 asl a
 pha
 asl a
 asl a
 clc
 adc 1,s
 ply
 sta.l SourceLifecycle4086_Entity
 clc
 adc #$4000
 tax
 cmp.l $410000,x
 beq SourceLifecycle4086_Guard_32
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_32:
.a16
.i16
 lda.l $410002,x
 cmp #$0041
 beq SourceLifecycle4086_Guard_33
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_33:
.a16
.i16
 lda.l SourceLifecycle4086_Reset
 bne SourceLifecycle4086_Validated
 lda.l SourceLifecycle4086_Entity
 tax
 lda.l $43904A,x
 cmp #$B4FB
 beq SourceLifecycle4086_Guard_34
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_Guard_34:
.a16
.i16
SourceLifecycle4086_Validated:
.a16
.i16
 lda #2
 sta.l SourceLifecycle4086_Status
 ply
 plx
 plp
 clc
 rtl

SourceLifecycle4086_Apply:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jsl SourceLifecycle4086_Preflight
 bcc SourceLifecycle4086_ApplyGood
 jmp SourceLifecycle4086_Bad
SourceLifecycle4086_ApplyGood:
.a16
.i16
 lda.l SourceLifecycle4086_Reset
 beq SourceLifecycle4086_Copy
 lda.l SourceLifecycle4086_Entity
 tax
 ldy #40
 lda #0
SourceLifecycle4086_Clear:
.a16
.i16
 sta.l $439000,x
 inx
 inx
 dey
 bne SourceLifecycle4086_Clear
SourceLifecycle4086_Copy:
.a16
.i16
 lda #0
 sta.l SourceLifecycle4086_Index
SourceLifecycle4086_CopyLoop:
.a16
.i16
 lda.l SourceLifecycle4086_Row
 clc
 adc #4
 clc
 adc.l SourceLifecycle4086_Index
 tax
 jsr SourceLifecycle4086_Read
 sta.l SourceLifecycle4086_Value
 lda.l SourceLifecycle4086_Entity
 clc
 adc.l SourceLifecycle4086_Index
 tax
 lda.l SourceLifecycle4086_Value
 sta.l $439030,x
 lda.l SourceLifecycle4086_Index
 inc a
 inc a
 sta.l SourceLifecycle4086_Index
 cmp #20
 bcc SourceLifecycle4086_CopyLoop
 lda.l SourceLifecycle4086_Entity
 tax
 lda.l SourceLifecycle4086_Model
 sta.l $439048,x
 lda #$B4FB
 sta.l $43904A,x
 lda #2
 sta.l SourceLifecycle4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceLifecycle4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceLifecycle4086_Status
 ply
 plx
 plp
 sec
 rtl
SourceLifecycle4086_Read:
.a16
.i16
 phb
 lda.l SourceLifecycle4086_Bank
 sep #$20
.a8
 pha
 plb
 rep #$20
.a16
 lda.w $0000,x
 plb
 ora #0
 rts

SourceLifecycle4086_CheckIdle:
.a16
.i16
 php
 rep #$38
 pha
 lda.l SourceLifecycle4086_Ready
 beq SourceLifecycle4086_IdleGood
 cmp #$B4FB
 bne SourceLifecycle4086_IdleBad
 lda.l SourceLifecycle4086_Status
 beq SourceLifecycle4086_IdleGood
 cmp #2
 bne SourceLifecycle4086_IdleBad
SourceLifecycle4086_IdleGood:
.a16
.i16
 pla
 plp
 clc
 rtl
SourceLifecycle4086_IdleBad:
.a16
.i16
 pla
 plp
 sec
 rtl
