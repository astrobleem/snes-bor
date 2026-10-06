; B5F1 closed uniform immutable factors. Exact independent 32-byte entity
; snapshots at $432800..$4337FF, per-slot model/lease at $43B900..$43BAFF.
; Compiler validates B5UF CRC and paired source identity before granting Ready.
; Mutation APIs and nonuniform attack factors are not admitted by this lease.
; Slot/Model input uses the checked constructor ScriptClone controls.
SourceFactors4086_Ready = $43B832
SourceFactors4086_Status = $43B834
SourceFactors4086_Base = $43B836
SourceFactors4086_Bank = $43B838
SourceFactors4086_Bytes = $43B83A
SourceFactors4086_Models = $43B83C
SourceFactors4086_Attacks = $43B83E
SourceFactors4086_Row = $43B840
SourceFactors4086_Entity = $43B842
SourceFactors4086_Index = $43B844
SourceFactors4086_Value = $43B846
SourceFactors4086_End = $43B848
SourceFactors4086_Apply:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jsr SourceScriptClone4086_Preflight
 bcc SourceFactors4086_Guard_1
 jmp SourceFactors4086_Bad
SourceFactors4086_Guard_1:
.a16
.i16
 lda.l SourceFactors4086_Ready
 cmp #$B5F1
 beq SourceFactors4086_Guard_2
 jmp SourceFactors4086_Bad
SourceFactors4086_Guard_2:
.a16
.i16
 lda.l SourceFactors4086_Status
 cmp #3
 bne SourceFactors4086_Guard_3
 jmp SourceFactors4086_Bad
SourceFactors4086_Guard_3:
.a16
.i16
 lda.l SourceFactors4086_Models
 cmp.l SourceScriptClone4086_Models
 beq SourceFactors4086_Guard_4
 jmp SourceFactors4086_Bad
SourceFactors4086_Guard_4:
.a16
.i16
 lda.l SourceFactors4086_Attacks
 cmp #20
 bcs SourceFactors4086_Guard_5
 jmp SourceFactors4086_Bad
SourceFactors4086_Guard_5:
.a16
.i16
 cmp #256
 bcc SourceFactors4086_Guard_6
 jmp SourceFactors4086_Bad
SourceFactors4086_Guard_6:
.a16
.i16
 lda.l SourceFactors4086_Base
 cmp #$8000
 bcs SourceFactors4086_Guard_7
 jmp SourceFactors4086_Bad
SourceFactors4086_Guard_7:
.a16
.i16
 lda.l SourceFactors4086_Bank
 bne SourceFactors4086_Guard_8
 jmp SourceFactors4086_Bad
SourceFactors4086_Guard_8:
.a16
.i16
 cmp #64
 bcc SourceFactors4086_Guard_9
 jmp SourceFactors4086_Bad
SourceFactors4086_Guard_9:
.a16
.i16
 lda.l SourceFactors4086_Models
 asl a
 asl a
 sta.l SourceFactors4086_Value
 asl a
 asl a
 asl a
 clc
 adc.l SourceFactors4086_Value
 clc
 adc #24
 cmp.l SourceFactors4086_Bytes
 beq SourceFactors4086_Guard_10
 jmp SourceFactors4086_Bad
SourceFactors4086_Guard_10:
.a16
.i16
 dec a
 clc
 adc.l SourceFactors4086_Base
 bcc SourceFactors4086_Guard_11
 jmp SourceFactors4086_Bad
SourceFactors4086_Guard_11:
.a16
.i16
 ldx #0
 jsr SourceFactors4086_Read
 cmp #$3542
 beq SourceFactors4086_Guard_12
 jmp SourceFactors4086_Bad
SourceFactors4086_Guard_12:
.a16
.i16
 ldx #2
 jsr SourceFactors4086_Read
 cmp #$4655
 beq SourceFactors4086_Guard_13
 jmp SourceFactors4086_Bad
SourceFactors4086_Guard_13:
.a16
.i16
 ldx #4
 jsr SourceFactors4086_Read
 cmp #1
 beq SourceFactors4086_Guard_14
 jmp SourceFactors4086_Bad
SourceFactors4086_Guard_14:
.a16
.i16
 ldx #6
 jsr SourceFactors4086_Read
 cmp #36
 beq SourceFactors4086_Guard_15
 jmp SourceFactors4086_Bad
SourceFactors4086_Guard_15:
.a16
.i16
 ldx #8
 jsr SourceFactors4086_Read
 cmp.l SourceFactors4086_Models
 beq SourceFactors4086_Guard_16
 jmp SourceFactors4086_Bad
SourceFactors4086_Guard_16:
.a16
.i16
 ldx #10
 jsr SourceFactors4086_Read
 cmp.l SourceFactors4086_Attacks
 beq SourceFactors4086_Guard_17
 jmp SourceFactors4086_Bad
SourceFactors4086_Guard_17:
.a16
.i16
 ldx #12
 jsr SourceFactors4086_Read
 clc
 adc #24
 cmp.l SourceFactors4086_Bytes
 beq SourceFactors4086_Guard_18
 jmp SourceFactors4086_Bad
SourceFactors4086_Guard_18:
.a16
.i16
 ldx #14
 jsr SourceFactors4086_Read
 beq SourceFactors4086_Guard_19
 jmp SourceFactors4086_Bad
SourceFactors4086_Guard_19:
.a16
.i16
 ldx #20
 jsr SourceFactors4086_Read
 beq SourceFactors4086_Guard_20
 jmp SourceFactors4086_Bad
SourceFactors4086_Guard_20:
.a16
.i16
 ldx #22
 jsr SourceFactors4086_Read
 beq SourceFactors4086_Guard_21
 jmp SourceFactors4086_Bad
SourceFactors4086_Guard_21:
.a16
.i16
 lda.l SourceScriptClone4086_Model
 asl a
 asl a
 sta.l SourceFactors4086_Value
 asl a
 asl a
 asl a
 clc
 adc.l SourceFactors4086_Value
 clc
 adc #24
 sta.l SourceFactors4086_Row
 tax
 jsr SourceFactors4086_Read
 cmp.l SourceScriptClone4086_Model
 beq SourceFactors4086_Guard_22
 jmp SourceFactors4086_Bad
SourceFactors4086_Guard_22:
.a16
.i16
 inx
 inx
 jsr SourceFactors4086_Read
 beq SourceFactors4086_Guard_23
 jmp SourceFactors4086_Bad
SourceFactors4086_Guard_23:
.a16
.i16
 lda.l SourceFactors4086_Row
 clc
 adc #4
 sta.l SourceFactors4086_Row
 lda.l SourceScriptClone4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l SourceFactors4086_Entity
 lda #0
 sta.l SourceFactors4086_Index
SourceFactors4086_Copy:
.a16
.i16
 lda.l SourceFactors4086_Row
 clc
 adc.l SourceFactors4086_Index
 tax
 jsr SourceFactors4086_Read
 sta.l SourceFactors4086_Value
 lda.l SourceFactors4086_Entity
 clc
 adc.l SourceFactors4086_Index
 tax
 lda.l SourceFactors4086_Value
 sta.l $432800,x
 lda.l SourceFactors4086_Index
 inc a
 inc a
 sta.l SourceFactors4086_Index
 cmp #32
 bcs SourceFactors4086_Guard_24
 jmp SourceFactors4086_Copy
SourceFactors4086_Guard_24:
.a16
.i16
 lda.l SourceScriptClone4086_Slot
 asl a
 asl a
 tax
 lda.l SourceScriptClone4086_Model
 sta.l $43B900,x
 lda #$B5F1
 sta.l $43B902,x
 lda #2
 sta.l SourceFactors4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceFactors4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceFactors4086_Status
 ply
 plx
 plp
 sec
 rtl
SourceFactors4086_Read:
.a16
.i16
 phb
 phx
 txa
 clc
 adc.l SourceFactors4086_Base
 tax
 sep #$20
.a8
 lda.l SourceFactors4086_Bank
 pha
 plb
 rep #$20
.a16
 lda.w $0000,x
 plx
 plb
 ora #0
 rts
