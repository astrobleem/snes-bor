; Closed B5SQ spawn-row preparation, not a complete stage queue dispatcher.
; Caller checks immutable table CRC/model/stage pairing before granting B5D2.
; Preserve original binary32 positions in ROM; consume paired offline Q16.
; Stage scrolling advance is added before the actual source constructor.
; Only input/control fields are written. No entity is allocated or published.
SourceStageQueue4086_Ready = $43BB00
SourceStageQueue4086_Status = $43BB02
SourceStageQueue4086_Base = $43BB04
SourceStageQueue4086_Bank = $43BB06
SourceStageQueue4086_Bytes = $43BB08
SourceStageQueue4086_Records = $43BB0A
SourceStageQueue4086_Stages = $43BB0C
SourceStageQueue4086_Index = $43BB0E
SourceStageQueue4086_Stage = $43BB10
SourceStageQueue4086_Row = $43BB12
SourceStageQueue4086_Read = $43BB14
SourceStageQueue4086_Model = $43BB16
SourceStageQueue4086_X = $43BB18
SourceStageQueue4086_Z = $43BB1C
SourceStageQueue4086_A = $43BB20
SourceStageQueue4086_Direction = $43BB24
SourceStageQueue4086_Time = $43BB28
SourceStageQueue4086_End = $43BB2C

SourceStageQueue4086_PrepareSpawn:
.a16
.i16
 php
 rep #$38
 phb
 phx
 phy
 jsr SourceStageQueue4086_CheckRow
 bcc SourceStageQueue4086_SpawnRowValid
 jmp SourceStageQueue4086_Bad
SourceStageQueue4086_SpawnRowValid:
.a16
.i16
 lda #2
 jsr SourceStageQueue4086_ReadRow
 cmp #1 ; actual spawn, never WAIT/GROUP/empty alias
 beq SourceStageQueue4086_Spawn
 jmp SourceStageQueue4086_Bad
SourceStageQueue4086_Spawn:
.a16
.i16
 lda #4
 jsr SourceStageQueue4086_ReadRow
 cmp.l VmSourceWorld_TemplateCount
 bcc SourceStageQueue4086_ModelValid
 jmp SourceStageQueue4086_Bad
SourceStageQueue4086_ModelValid:
.a16
.i16
 sta.l SourceStageQueue4086_Model
 lda #112
 jsr SourceStageQueue4086_ReadRow
 sta.l SourceStageQueue4086_X
 lda #114
 jsr SourceStageQueue4086_ReadRow
 sta.l SourceStageQueue4086_X+2
 lda #116
 jsr SourceStageQueue4086_ReadRow
 sta.l SourceStageQueue4086_Z
 lda #118
 jsr SourceStageQueue4086_ReadRow
 sta.l SourceStageQueue4086_Z+2
 lda #120
 jsr SourceStageQueue4086_ReadRow
 sta.l SourceStageQueue4086_A
 lda #122
 jsr SourceStageQueue4086_ReadRow
 sta.l SourceStageQueue4086_A+2
 lda #24
 jsr SourceStageQueue4086_ReadRow
 sta.l SourceStageQueue4086_Direction
 lda #26
 jsr SourceStageQueue4086_ReadRow
 sta.l SourceStageQueue4086_Direction+2
 lda.l VmSourceWorld_ScrollAxis
 beq SourceStageQueue4086_Horizontal
 cmp #1
 beq SourceStageQueue4086_Vertical
 jmp SourceStageQueue4086_Bad
SourceStageQueue4086_Horizontal:
.a16
.i16
 lda.l SourceStageQueue4086_X
 clc
 adc.l VmSourceWorld_AdvanceX
 sta.l SourceStageQueue4086_X
 lda.l SourceStageQueue4086_X+2
 adc.l VmSourceWorld_AdvanceX+2
 bvc SourceStageQueue4086_XSumValid
 jmp SourceStageQueue4086_Bad
SourceStageQueue4086_XSumValid:
.a16
.i16
 sta.l SourceStageQueue4086_X+2
 bra SourceStageQueue4086_Publish
SourceStageQueue4086_Vertical:
.a16
.i16
 lda.l SourceStageQueue4086_Z
 clc
 adc.l VmSourceWorld_AdvanceY
 sta.l SourceStageQueue4086_Z
 lda.l SourceStageQueue4086_Z+2
 adc.l VmSourceWorld_AdvanceY+2
 bvc SourceStageQueue4086_ZSumValid
 jmp SourceStageQueue4086_Bad
SourceStageQueue4086_ZSumValid:
.a16
.i16
 sta.l SourceStageQueue4086_Z+2
SourceStageQueue4086_Publish:
.a16
.i16
 lda.l SourceStageQueue4086_Model
 sta.l SourceSpawnSlot4086_Model
 lda.l SourceStageQueue4086_X
 sta.l SourceCtorState4086_X
 lda.l SourceStageQueue4086_X+2
 sta.l SourceCtorState4086_X+2
 lda.l SourceStageQueue4086_Z
 sta.l SourceCtorState4086_Z
 lda.l SourceStageQueue4086_Z+2
 sta.l SourceCtorState4086_Z+2
 lda.l SourceStageQueue4086_A
 sta.l SourceCtorState4086_A
 lda.l SourceStageQueue4086_A+2
 sta.l SourceCtorState4086_A+2
 lda.l SourceStageQueue4086_Direction
 sta.l SourceCtorState4086_Direction
 lda.l SourceStageQueue4086_Direction+2
 sta.l SourceCtorState4086_Direction+2
 lda.l VmSourceWorld_Time
 sta.l SourceStageQueue4086_Time
 sta.l SourceCtorState4086_Time
 sta.l SourceDefaultChoice4086_TimeLo
 sta.l SourceDefaultPlayer4086_TimeLo
 lda.l VmSourceWorld_Time+2
 sta.l SourceStageQueue4086_Time+2
 sta.l SourceCtorState4086_Time+2
 sta.l SourceDefaultChoice4086_TimeHi
 sta.l SourceDefaultPlayer4086_TimeHi
 lda #0
 sta.l SourceDefaultChoice4086_Select
 lda #2
 sta.l SourceStageQueue4086_Status
 ply
 plx
 plb
 plp
 clc
 rtl
SourceStageQueue4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceStageQueue4086_Status
 ply
 plx
 plb
 plp
 sec
 rtl

SourceStageQueue4086_ReadRow:
.a16
.i16
 clc
 adc.l SourceStageQueue4086_Row
SourceStageQueue4086_ReadAt:
.a16
.i16
 clc
 adc.l SourceStageQueue4086_Base
 tax
 phb
 sep #$20
.a8
 lda.l SourceStageQueue4086_Bank
 pha
 plb
 rep #$20
.a16
 lda.w $0000,x
 plb
 ora #0
 rts

; Shared readonly row validation for the queue dispatcher, including WAIT,
; GROUP and empty source records. The immutable table lease still requires
; caller-verified CRC/model/stage pairing. Does not prepare spawn coordinates.
SourceStageQueue4086_ValidateCurrentRow:
.a16
.i16
 php
 rep #$38
 phb
 phx
 phy
 jsr SourceStageQueue4086_CheckRow
 bcc SourceStageQueue4086_RowChecked
 jmp SourceStageQueue4086_Bad
SourceStageQueue4086_RowChecked:
.a16
.i16
 lda #2
 sta.l SourceStageQueue4086_Status
 ply
 plx
 plb
 plp
 clc
 rtl
SourceStageQueue4086_CheckRow:
.a16
.i16
 lda.l SourceStageQueue4086_Ready
 cmp #$B5D2
 beq SourceStageQueue4086_Granted
 jmp SourceStageQueue4086_CheckRowBad
SourceStageQueue4086_Granted:
.a16
.i16
 lda.l SourceStageQueue4086_Status
 beq SourceStageQueue4086_NotFault
 cmp #2
 beq SourceStageQueue4086_NotFault
 jmp SourceStageQueue4086_CheckRowBad
SourceStageQueue4086_NotFault:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourceStageQueue4086_World
 jmp SourceStageQueue4086_CheckRowBad
SourceStageQueue4086_World:
.a16
.i16
 lda.l VmSourceWorld_Level
 cmp #1
 beq SourceStageQueue4086_Level
 jmp SourceStageQueue4086_CheckRowBad
SourceStageQueue4086_Level:
.a16
.i16
 lda.l SourceStageQueue4086_Base
 cmp #$8000
 bcs SourceStageQueue4086_BaseValid
 jmp SourceStageQueue4086_CheckRowBad
SourceStageQueue4086_BaseValid:
.a16
.i16
 lda.l SourceStageQueue4086_Bank
 bne SourceStageQueue4086_Far_1
 jmp SourceStageQueue4086_CheckRowBad
SourceStageQueue4086_Far_1:
.a16
.i16
 cmp #64
 bcc SourceStageQueue4086_BankValid
 jmp SourceStageQueue4086_CheckRowBad
SourceStageQueue4086_BankValid:
.a16
.i16
 lda.l SourceStageQueue4086_Bytes
 cmp #24
 bcs SourceStageQueue4086_LengthValid
 jmp SourceStageQueue4086_CheckRowBad
SourceStageQueue4086_LengthValid:
.a16
.i16
 clc
 adc.l SourceStageQueue4086_Base
 bcc SourceStageQueue4086_SpanValid
 jmp SourceStageQueue4086_CheckRowBad
SourceStageQueue4086_SpanValid:
.a16
.i16
 lda #0
 jsr SourceStageQueue4086_ReadAt
 cmp #$3542 ; B5
 beq SourceStageQueue4086_Magic1
 jmp SourceStageQueue4086_CheckRowBad
SourceStageQueue4086_Magic1:
.a16
.i16
 lda #2
 jsr SourceStageQueue4086_ReadAt
 cmp #$5153 ; SQ
 beq SourceStageQueue4086_Magic2
 jmp SourceStageQueue4086_CheckRowBad
SourceStageQueue4086_Magic2:
.a16
.i16
 lda #4
 jsr SourceStageQueue4086_ReadAt
 cmp #1
 beq SourceStageQueue4086_Version
 jmp SourceStageQueue4086_CheckRowBad
SourceStageQueue4086_Version:
.a16
.i16
 lda #6
 jsr SourceStageQueue4086_ReadAt
 cmp #128
 beq SourceStageQueue4086_Stride
 jmp SourceStageQueue4086_CheckRowBad
SourceStageQueue4086_Stride:
.a16
.i16
 lda.l SourceStageQueue4086_Records
 bne SourceStageQueue4086_Far_2
 jmp SourceStageQueue4086_CheckRowBad
SourceStageQueue4086_Far_2:
.a16
.i16
 cmp #256
 bcc SourceStageQueue4086_RecordCount
 jmp SourceStageQueue4086_CheckRowBad
SourceStageQueue4086_RecordCount:
.a16
.i16
 lda #8
 jsr SourceStageQueue4086_ReadAt
 cmp.l SourceStageQueue4086_Records
 beq SourceStageQueue4086_RecordsPaired
 jmp SourceStageQueue4086_CheckRowBad
SourceStageQueue4086_RecordsPaired:
.a16
.i16
 asl a
 asl a
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l SourceStageQueue4086_Read
 clc
 adc #24
 cmp.l SourceStageQueue4086_Bytes
 beq SourceStageQueue4086_BodySize
 jmp SourceStageQueue4086_CheckRowBad
SourceStageQueue4086_BodySize:
.a16
.i16
 lda #12
 jsr SourceStageQueue4086_ReadAt
 cmp.l SourceStageQueue4086_Read
 beq SourceStageQueue4086_BodySizePaired
 jmp SourceStageQueue4086_CheckRowBad
SourceStageQueue4086_BodySizePaired:
.a16
.i16
 lda #14
 jsr SourceStageQueue4086_ReadAt
 beq SourceStageQueue4086_BodyHigh
 jmp SourceStageQueue4086_CheckRowBad
SourceStageQueue4086_BodyHigh:
.a16
.i16
 lda #20
 jsr SourceStageQueue4086_ReadAt
 beq SourceStageQueue4086_ReservedLow
 jmp SourceStageQueue4086_CheckRowBad
SourceStageQueue4086_ReservedLow:
.a16
.i16
 lda #22
 jsr SourceStageQueue4086_ReadAt
 beq SourceStageQueue4086_ReservedHigh
 jmp SourceStageQueue4086_CheckRowBad
SourceStageQueue4086_ReservedHigh:
.a16
.i16
 lda #10
 jsr SourceStageQueue4086_ReadAt
 cmp.l SourceStageQueue4086_Stages
 beq SourceStageQueue4086_StagesPaired
 jmp SourceStageQueue4086_CheckRowBad
SourceStageQueue4086_StagesPaired:
.a16
.i16
 lda.l SourceStageQueue4086_Stage
 bne SourceStageQueue4086_Far_3
 jmp SourceStageQueue4086_CheckRowBad
SourceStageQueue4086_Far_3:
.a16
.i16
 cmp.l SourceStageQueue4086_Stages
 bcc SourceStageQueue4086_StageValid
 beq SourceStageQueue4086_StageValid
 jmp SourceStageQueue4086_CheckRowBad
SourceStageQueue4086_StageValid:
.a16
.i16
 pha
 lda.l SourceEnvironment4086_Ready
 cmp #$B4D1
 beq SourceStageQueue4086_EnvironmentValid
 pla
 jmp SourceStageQueue4086_CheckRowBad
SourceStageQueue4086_EnvironmentValid:
.a16
.i16
 pla
 cmp.l SourceEnvironment4086_Stage
 beq SourceStageQueue4086_CurrentStage
 jmp SourceStageQueue4086_CheckRowBad
SourceStageQueue4086_CurrentStage:
.a16
.i16
 lda.l SourceStageQueue4086_Index
 cmp.l SourceStageQueue4086_Records
 bcc SourceStageQueue4086_IndexValid
 jmp SourceStageQueue4086_CheckRowBad
SourceStageQueue4086_IndexValid:
.a16
.i16
 asl a
 asl a
 asl a
 asl a
 asl a
 asl a
 asl a
 clc
 adc #24
 sta.l SourceStageQueue4086_Row
 lda #0
 jsr SourceStageQueue4086_ReadRow
 cmp.l SourceStageQueue4086_Stage
 beq SourceStageQueue4086_RowPaired
 jmp SourceStageQueue4086_CheckRowBad
SourceStageQueue4086_RowPaired:
.a16
.i16
 lda #2
 jsr SourceStageQueue4086_ReadRow
 cmp #4
 bcc SourceStageQueue4086_RowKindValid
 jmp SourceStageQueue4086_CheckRowBad
SourceStageQueue4086_RowKindValid:
.a16
.i16
 cmp #1
 bne SourceStageQueue4086_RowModelChecked
 lda #4
 jsr SourceStageQueue4086_ReadRow
 cmp.l VmSourceWorld_TemplateCount
 bcc SourceStageQueue4086_RowModelChecked
 jmp SourceStageQueue4086_CheckRowBad
SourceStageQueue4086_RowModelChecked:
.a16
.i16
 clc
 rts
SourceStageQueue4086_CheckRowBad:
.a16
.i16
 sec
 rts
