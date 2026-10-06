; B504 closed no-platform animation registry + B4D1 current empty-wall stage.
; Caller/compiler must revoke on registry, platform mutation or stage change.
; Native world publication of that closed capability is separate.
SourceEmptyInitEnvironment4086_Ready = $7FFED0
SourceEmptyInitEnvironment4086_Models = $7FFED2
SourceEmptyInitEnvironment4086_Stage = $7FFED4
SourceEmptyInitEnvironment4086_Status = $7FFED6
SourceEmptyInitEnvironment4086_PlatformLo = $7FFED8
SourceEmptyInitEnvironment4086_PlatformHi = $7FFEDA
SourceEmptyInitEnvironment4086_WallIndex = $7FFEDC

SourceEmptyInitEnvironment4086_Query:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceEmptyInitEnvironment4086_Ready
 cmp #$B504
 beq SourceEmptyInitEnvironment4086_Guard_1
 jmp SourceEmptyInitEnvironment4086_Bad
SourceEmptyInitEnvironment4086_Guard_1:
.a16
.i16
 lda.l SourceEmptyInitEnvironment4086_Status
 cmp #3
 bne SourceEmptyInitEnvironment4086_Guard_2
 jmp SourceEmptyInitEnvironment4086_Bad
SourceEmptyInitEnvironment4086_Guard_2:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceEmptyInitEnvironment4086_Guard_3
 jmp SourceEmptyInitEnvironment4086_Bad
SourceEmptyInitEnvironment4086_Guard_3:
.a16
.i16
 lda.l VmSourceWorld_Level
 bne SourceEmptyInitEnvironment4086_Guard_4
 jmp SourceEmptyInitEnvironment4086_Bad
SourceEmptyInitEnvironment4086_Guard_4:
.a16
.i16
 lda.l VmSourceWorld_Count
 bne SourceEmptyInitEnvironment4086_Guard_5
 jmp SourceEmptyInitEnvironment4086_Bad
SourceEmptyInitEnvironment4086_Guard_5:
.a16
.i16
 cmp #129
 bcc SourceEmptyInitEnvironment4086_Guard_6
 jmp SourceEmptyInitEnvironment4086_Bad
SourceEmptyInitEnvironment4086_Guard_6:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourceEmptyInitEnvironment4086_Guard_7
 jmp SourceEmptyInitEnvironment4086_Bad
SourceEmptyInitEnvironment4086_Guard_7:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Ready
 cmp #$B4EB
 beq SourceEmptyInitEnvironment4086_Guard_8
 jmp SourceEmptyInitEnvironment4086_Bad
SourceEmptyInitEnvironment4086_Guard_8:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Entities
 cmp.l VmSourceWorld_Count
 beq SourceEmptyInitEnvironment4086_Guard_9
 jmp SourceEmptyInitEnvironment4086_Bad
SourceEmptyInitEnvironment4086_Guard_9:
.a16
.i16
 lda.l SourceEmptyInitEnvironment4086_Models
 bne SourceEmptyInitEnvironment4086_Guard_10
 jmp SourceEmptyInitEnvironment4086_Bad
SourceEmptyInitEnvironment4086_Guard_10:
.a16
.i16
 cmp #17
 bcc SourceEmptyInitEnvironment4086_Guard_11
 jmp SourceEmptyInitEnvironment4086_Bad
SourceEmptyInitEnvironment4086_Guard_11:
.a16
.i16
 cmp.l SourceModelEntityCopy4086_Models
 beq SourceEmptyInitEnvironment4086_Guard_12
 jmp SourceEmptyInitEnvironment4086_Bad
SourceEmptyInitEnvironment4086_Guard_12:
.a16
.i16
 cmp.l VmSourceWorld_TemplateCount
 beq SourceEmptyInitEnvironment4086_Guard_13
 jmp SourceEmptyInitEnvironment4086_Bad
SourceEmptyInitEnvironment4086_Guard_13:
.a16
.i16
 lda.l SourceEnvironment4086_Ready
 cmp #$B4D1
 beq SourceEmptyInitEnvironment4086_Guard_14
 jmp SourceEmptyInitEnvironment4086_Bad
SourceEmptyInitEnvironment4086_Guard_14:
.a16
.i16
 lda.l SourceEnvironment4086_WallCount
 beq SourceEmptyInitEnvironment4086_Guard_15
 jmp SourceEmptyInitEnvironment4086_Bad
SourceEmptyInitEnvironment4086_Guard_15:
.a16
.i16
 lda.l SourceEmptyInitEnvironment4086_Stage
 bne SourceEmptyInitEnvironment4086_Guard_16
 jmp SourceEmptyInitEnvironment4086_Bad
SourceEmptyInitEnvironment4086_Guard_16:
.a16
.i16
 cmp.l SourceEnvironment4086_Stage
 beq SourceEmptyInitEnvironment4086_Guard_17
 jmp SourceEmptyInitEnvironment4086_Bad
SourceEmptyInitEnvironment4086_Guard_17:
.a16
.i16
 lda #0
 sta.l SourceEmptyInitEnvironment4086_PlatformLo
 sta.l SourceEmptyInitEnvironment4086_PlatformHi
 lda #$FFFF
 sta.l SourceEmptyInitEnvironment4086_WallIndex
 lda #2
 sta.l SourceEmptyInitEnvironment4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceEmptyInitEnvironment4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceEmptyInitEnvironment4086_Status
 ply
 plx
 plp
 sec
 rtl

SourceEmptyInitEnvironment4086_CheckIdle:
.a16
.i16
 php
 rep #$38
 pha
 lda.l SourceEmptyInitEnvironment4086_Ready
 beq SourceEmptyInitEnvironment4086_IdleGood
 cmp #$B504
 bne SourceEmptyInitEnvironment4086_IdleBad
 lda.l SourceEmptyInitEnvironment4086_Status
 beq SourceEmptyInitEnvironment4086_IdleGood
 cmp #2
 bne SourceEmptyInitEnvironment4086_IdleBad
SourceEmptyInitEnvironment4086_IdleGood:
.a16
.i16
 pla
 plp
 clc
 rtl
SourceEmptyInitEnvironment4086_IdleBad:
.a16
.i16
 pla
 plp
 sec
 rtl
