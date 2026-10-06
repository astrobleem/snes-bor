; B505 exact integer player spawn heights in Q16, paired current stage.
; Synchronous query, including a valid dead entity pointer as source C permits.
SourcePlayerSpawnHeight4086_Ready = $7FFEE0
SourcePlayerSpawnHeight4086_Stage = $7FFEE2
SourcePlayerSpawnHeight4086_Heights = $7FFEE4
SourcePlayerSpawnHeight4086_ValueLo = $7FFEF4
SourcePlayerSpawnHeight4086_ValueHi = $7FFEF6
SourcePlayerSpawnHeight4086_Slot = $7FFEF8
SourcePlayerSpawnHeight4086_View = $7FFEFA
SourcePlayerSpawnHeight4086_Index = $7FFEFC
SourcePlayerSpawnHeight4086_Status = $7FFEFE

SourcePlayerSpawnHeight4086_Query:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourcePlayerSpawnHeight4086_Ready
 cmp #$B505
 beq SourcePlayerSpawnHeight4086_Guard_1
 jmp SourcePlayerSpawnHeight4086_Bad
SourcePlayerSpawnHeight4086_Guard_1:
.a16
.i16
 lda.l SourcePlayerSpawnHeight4086_Status
 cmp #3
 bne SourcePlayerSpawnHeight4086_Guard_2
 jmp SourcePlayerSpawnHeight4086_Bad
SourcePlayerSpawnHeight4086_Guard_2:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourcePlayerSpawnHeight4086_Guard_3
 jmp SourcePlayerSpawnHeight4086_Bad
SourcePlayerSpawnHeight4086_Guard_3:
.a16
.i16
 lda.l VmSourceWorld_Level
 bne SourcePlayerSpawnHeight4086_Guard_4
 jmp SourcePlayerSpawnHeight4086_Bad
SourcePlayerSpawnHeight4086_Guard_4:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourcePlayerSpawnHeight4086_Guard_5
 jmp SourcePlayerSpawnHeight4086_Bad
SourcePlayerSpawnHeight4086_Guard_5:
.a16
.i16
 lda.l VmSourceWorld_Count
 bne SourcePlayerSpawnHeight4086_Guard_6
 jmp SourcePlayerSpawnHeight4086_Bad
SourcePlayerSpawnHeight4086_Guard_6:
.a16
.i16
 cmp #129
 bcc SourcePlayerSpawnHeight4086_Guard_7
 jmp SourcePlayerSpawnHeight4086_Bad
SourcePlayerSpawnHeight4086_Guard_7:
.a16
.i16
 lda.l SourcePlayerSpawnHeight4086_Slot
 cmp.l VmSourceWorld_Count
 bcc SourcePlayerSpawnHeight4086_Guard_8
 jmp SourcePlayerSpawnHeight4086_Bad
SourcePlayerSpawnHeight4086_Guard_8:
.a16
.i16
 lda.l SourceEnvironment4086_Ready
 cmp #$B4D1
 beq SourcePlayerSpawnHeight4086_Guard_9
 jmp SourcePlayerSpawnHeight4086_Bad
SourcePlayerSpawnHeight4086_Guard_9:
.a16
.i16
 lda.l SourcePlayerSpawnHeight4086_Stage
 bne SourcePlayerSpawnHeight4086_Guard_10
 jmp SourcePlayerSpawnHeight4086_Bad
SourcePlayerSpawnHeight4086_Guard_10:
.a16
.i16
 cmp.l SourceEnvironment4086_Stage
 beq SourcePlayerSpawnHeight4086_Guard_11
 jmp SourcePlayerSpawnHeight4086_Bad
SourcePlayerSpawnHeight4086_Guard_11:
.a16
.i16
 lda.l SourcePlayerSpawnHeight4086_Slot
 asl a
 asl a
 asl a
 asl a
 sta.l SourcePlayerSpawnHeight4086_Index
 asl a
 asl a
 clc
 adc.l SourcePlayerSpawnHeight4086_Index
 clc
 adc #$4000
 sta.l SourcePlayerSpawnHeight4086_View
 tax
 cmp.l $410000,x
 beq SourcePlayerSpawnHeight4086_Guard_12
 jmp SourcePlayerSpawnHeight4086_Bad
SourcePlayerSpawnHeight4086_Guard_12:
.a16
.i16
 lda.l $410002,x
 cmp #$0041
 beq SourcePlayerSpawnHeight4086_Guard_13
 jmp SourcePlayerSpawnHeight4086_Bad
SourcePlayerSpawnHeight4086_Guard_13:
.a16
.i16
 lda.l $410028,x
 cmp #BOR_VT_INTEGER
 beq SourcePlayerSpawnHeight4086_Guard_14
 jmp SourcePlayerSpawnHeight4086_Bad
SourcePlayerSpawnHeight4086_Guard_14:
.a16
.i16
 lda.l $41002A,x
 beq SourcePlayerSpawnHeight4086_Guard_15
 jmp SourcePlayerSpawnHeight4086_Bad
SourcePlayerSpawnHeight4086_Guard_15:
.a16
.i16
 lda.l $41002E,x
 beq SourcePlayerSpawnHeight4086_Guard_16
 jmp SourcePlayerSpawnHeight4086_Bad
SourcePlayerSpawnHeight4086_Guard_16:
.a16
.i16
 lda.l $41002C,x
 cmp #4
 bcc SourcePlayerSpawnHeight4086_Guard_17
 jmp SourcePlayerSpawnHeight4086_Bad
SourcePlayerSpawnHeight4086_Guard_17:
.a16
.i16
 asl a
 asl a
 sta.l SourcePlayerSpawnHeight4086_Index
 tax
 lda.l SourcePlayerSpawnHeight4086_Heights,x
 beq SourcePlayerSpawnHeight4086_Guard_18
 jmp SourcePlayerSpawnHeight4086_Bad
SourcePlayerSpawnHeight4086_Guard_18:
.a16
.i16
 lda.l SourcePlayerSpawnHeight4086_Heights+2,x
 cmp #$8000
 bcc SourcePlayerSpawnHeight4086_Guard_19
 jmp SourcePlayerSpawnHeight4086_Bad
SourcePlayerSpawnHeight4086_Guard_19:
.a16
.i16
 sta.l SourcePlayerSpawnHeight4086_ValueHi
 lda #0
 sta.l SourcePlayerSpawnHeight4086_ValueLo
 lda #2
 sta.l SourcePlayerSpawnHeight4086_Status
 ply
 plx
 plp
 clc
 rtl
SourcePlayerSpawnHeight4086_Bad:
.a16
.i16
 lda #3
 sta.l SourcePlayerSpawnHeight4086_Status
 ply
 plx
 plp
 sec
 rtl

SourcePlayerSpawnHeight4086_CheckIdle:
.a16
.i16
 php
 rep #$38
 pha
 lda.l SourcePlayerSpawnHeight4086_Ready
 beq SourcePlayerSpawnHeight4086_IdleGood
 cmp #$B505
 bne SourcePlayerSpawnHeight4086_IdleBad
 lda.l SourcePlayerSpawnHeight4086_Status
 beq SourcePlayerSpawnHeight4086_IdleGood
 cmp #2
 bne SourcePlayerSpawnHeight4086_IdleBad
SourcePlayerSpawnHeight4086_IdleGood:
.a16
.i16
 pla
 plp
 clc
 rtl
SourcePlayerSpawnHeight4086_IdleBad:
.a16
.i16
 pla
 plp
 sec
 rtl
