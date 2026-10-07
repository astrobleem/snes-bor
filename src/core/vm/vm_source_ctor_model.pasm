; Fresh constructor modeldata copy, distinct from model-switch fallback.
; Caller has cleared script values and reset the destination instance.
; Uses current mutable B4EB cached model; immutable lifecycle capability is paired.
; Does not publish exists/count, coordinates, factors, roles or palette leases.
SourceCtorModel4086_Core = $43B820
SourceCtorModel4086_Cache = $43B822
SourceCtorModel4086_Side = $43B824
SourceCtorModel4086_View = $43B826
SourceCtorModel4086_SpeedLo = $43B828
SourceCtorModel4086_SpeedHi = $43B82A
SourceCtorModel4086_Truth = $43B82C
SourceCtorModel4086_Status = $43B82E
SourceCtorModel4086_Index = $43B830
SourceCtorModel4086_End = $43B832

SourceCtorModel4086_Preflight:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jsr SourceScriptClone4086_Preflight
 bcc SourceCtorModel4086_Guard_1
 jmp SourceCtorModel4086_Bad
SourceCtorModel4086_Guard_1:
.a16
.i16
 lda.l SourceScriptClone4086_Status
 cmp #2
 beq SourceCtorModel4086_Guard_2
 jmp SourceCtorModel4086_Bad
SourceCtorModel4086_Guard_2:
.a16
.i16
 lda.l SourceScriptClone4086_Models
 cmp.l SourceModelEntityCopy4086_Models
 beq SourceCtorModel4086_Guard_3
 jmp SourceCtorModel4086_Bad
SourceCtorModel4086_Guard_3:
.a16
.i16
 lda.l SourceScriptClone4086_Relation
 tax
 lda.l $40902C,x
 ora.l $40902E,x
 ora.l $409030,x
 ora.l $409032,x
 ora.l $409034,x
 ora.l $409036,x
 beq SourceCtorModel4086_Guard_4
 jmp SourceCtorModel4086_Bad
SourceCtorModel4086_Guard_4:
.a16
.i16
 lda.l SourceScriptClone4086_Slot
 sta.l SourceLifecycle4086_Slot
 lda.l SourceScriptClone4086_Model
 sta.l SourceLifecycle4086_Model
 lda #1
 sta.l SourceLifecycle4086_Reset
 jsl SourceLifecycle4086_Preflight
 bcc SourceCtorModel4086_Guard_5
 jmp SourceCtorModel4086_Bad
SourceCtorModel4086_Guard_5:
.a16
.i16
 lda.l SourceScriptClone4086_Relation
 sta.l SourceCtorModel4086_Side
 lsr a
 clc
 adc.l SourceScriptClone4086_Relation
 sta.l SourceCtorModel4086_Core
 lda.l SourceScriptClone4086_Token
 sec
 sbc #$4000
 sta.l SourceCtorModel4086_View
 lda.l SourceScriptClone4086_Model
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l SourceCtorModel4086_Cache
 asl a
 asl a
 clc
 adc.l SourceCtorModel4086_Cache
 sta.l SourceCtorModel4086_Cache
 tax
 lda.l $40B000,x
 sta.l SourceModelEntityCopy4086_Lo
 lda.l $40B002,x
 sta.l SourceModelEntityCopy4086_Hi
 and #$7FFF
 ora.l SourceModelEntityCopy4086_Lo
 bne SourceCtorModel4086_Guard_6
 jmp SourceCtorModel4086_Zero
SourceCtorModel4086_Guard_6:
.a16
.i16
 lda #1
SourceCtorModel4086_Zero:
.a16
.i16
 sta.l SourceCtorModel4086_Truth
 jsl SourceModelSpeed4086_ProjectQ16
 bcc SourceCtorModel4086_Guard_7
 jmp SourceCtorModel4086_Bad
SourceCtorModel4086_Guard_7:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Lo
 sta.l SourceCtorModel4086_SpeedLo
 lda.l SourceModelEntityCopy4086_Hi
 sta.l SourceCtorModel4086_SpeedHi

 lda #2
 sta.l SourceCtorModel4086_Status
 ply
 plx
 plp
 clc
 rtl

SourceCtorModel4086_Apply:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jsl SourceCtorModel4086_Preflight
 bcc SourceCtorModel4086_ApplyGood
 jmp SourceCtorModel4086_Bad
SourceCtorModel4086_ApplyGood:
.a16
.i16
 ; All rejectable domains checked before any entity write.
 lda #0
 sta.l SourceCtorModel4086_Index
SourceCtorModel4086_Copy:
.a16
.i16
 lda.l SourceCtorModel4086_Index
 clc
 adc.l SourceCtorModel4086_Cache
 tax
 lda.l $40B050,x
 pha
 lda.l SourceCtorModel4086_Index
 clc
 adc.l SourceCtorModel4086_Core
 tax
 pla
 sta.l $40C000,x
 lda.l SourceCtorModel4086_Index
 inc a
 inc a
 sta.l SourceCtorModel4086_Index
 cmp #72
 bcs SourceCtorModel4086_Guard_8
 jmp SourceCtorModel4086_Copy
SourceCtorModel4086_Guard_8:
.a16
.i16
 lda.l SourceCtorModel4086_Cache
 tax
 lda.l $40B09C,x
 pha
 lda.l $40B09E,x
 pha
 lda.l $40B090,x
 pha
 lda.l $40B092,x
 pha
 lda.l SourceCtorModel4086_Core
 tax
 pla
 sta.l $40C04E,x
 pla
 sta.l $40C04C,x
 pla
 sta.l $40C04A,x
 pla
 sta.l $40C048,x
 lda #0
 sta.l $40C050,x
 sta.l $40C052,x
 sta.l $40C054,x
 sta.l $40C056,x
 sta.l $40C058,x
 sta.l $40C05A,x
 sta.l $40C05C,x
 sta.l $40C05E,x
 lda.l SourceCtorModel4086_View
 tax
 lda #1
 sta.l $414020,x
 sta.l $414040,x
 lda #0
 sta.l $414022,x
 sta.l $414042,x
 lda.l SourceCtorModel4086_Cache
 tax
 lda.l $40B08C,x
 pha
 lda.l $40B08E,x
 pha
 lda.l SourceCtorModel4086_View
 tax
 pla
 sta.l $414026,x
 sta.l $414046,x
 pla
 sta.l $414024,x
 sta.l $414044,x
 lda.l SourceCtorModel4086_Side
 tax
 lda.l SourceScriptClone4086_Model
 sta.l $416800,x
 sta.l $416802,x
 lda.l SourceCtorModel4086_SpeedLo
 sta.l $41683C,x
 lda.l SourceCtorModel4086_SpeedHi
 sta.l $41683E,x
 jsl SourceLifecycle4086_Apply
 bcc SourceCtorModel4086_Guard_9
 jmp SourceCtorModel4086_Bad
SourceCtorModel4086_Guard_9:
.a16
.i16
 lda.l SourceLifecycle4086_Entity
 tax
 lda.l SourceCtorModel4086_Truth
 sta.l $439044,x
 lda #0
 sta.l $439046,x
 lda #$B508
 sta.l $43904C,x
 lda #2
 sta.l SourceCtorModel4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceCtorModel4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceCtorModel4086_Status
 ply
 plx
 plp
 sec
 rtl
