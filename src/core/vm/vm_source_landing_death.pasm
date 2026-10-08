; B639 bounded actual checkdeath: NULL item, no boss, negative diesound.
; Positive death sound/item/boss services remain required, never discarded.
; Owner is B636's retained landing callback; source exists stays untouched.
SourceLandingDeath4086_Ready = $7EFF78
SourceLandingDeath4086_State = $7EFF7A
SourceLandingDeath4086_Status = $7EFF7C
SourceLandingDeath4086_Score = $7EFF7E
SourceLandingDeath4086_Player = $7EFF82
SourceLandingDeath4086_HasScore = $7EFF86
SourceLandingDeath4086_End = $7EFF88
SourceLandingDeath4086_Preflight:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceLandingDeath4086_Ready
 bne SourceLandingDeath4086_ReadyCheck
 jmp SourceLandingDeath4086_PreRequired
SourceLandingDeath4086_ReadyCheck:
.a16
.i16
 cmp #$B639
 beq SourceLandingDeath4086_Lease
 jmp SourceLandingDeath4086_PreBad
SourceLandingDeath4086_Lease:
.a16
.i16
 lda.l SourceDeathFields4086_Ready
 cmp #$B638
 beq SourceLandingDeath4086_Fields
 jmp SourceLandingDeath4086_PreBad
SourceLandingDeath4086_Fields:
.a16
.i16
 lda.l SourceLandingCallback4086_Side
 tax
 lda.l $40903A,x
 cmp #$B638
 bne SourceLandingDeath4086_PreEarlyBad
 lda.l $409038,x
 cmp.l SourceLandingCallback4086_Model
 bne SourceLandingDeath4086_PreEarlyBad
 lda.l $40903C,x
 ora.l $40903E,x
 bne SourceLandingDeath4086_PreEarlyRequired
 ; Source body/name rows are 64 bytes, same physical stride as side/relation.
 lda.l $433838,x
 ora.l $43383A,x
 bne SourceLandingDeath4086_PreEarlyRequired
 lda.l SourceLandingCallback4086_View
 tax
 ; Match the invincibility resolver's binary32-exact coordinate domain.
 ; A required recovery caused by inexact arithmetic cannot become death.
 lda.l SOURCE_WORLD_POOL+14,x
 eor #$8000
 cmp #$7F00
 bcc SourceLandingDeath4086_WideCoordinate
 cmp #$8100
 bcc SourceLandingDeath4086_ExactCoordinate
SourceLandingDeath4086_WideCoordinate:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+12,x
 and #127
 bne SourceLandingDeath4086_PreEarlyRequired
SourceLandingDeath4086_ExactCoordinate:
.a16
.i16
 ; y <= PIT_DEPTH (-250) enters later source kill/player_die, still unbound.
 lda.l SOURCE_WORLD_POOL+14,x
 eor #$8000
 cmp #$7F06
 bcc SourceLandingDeath4086_PreEarlyRequired
 bne SourceLandingDeath4086_AbovePit
 lda.l SOURCE_WORLD_POOL+12,x
 beq SourceLandingDeath4086_PreEarlyRequired
 jmp SourceLandingDeath4086_AbovePit
SourceLandingDeath4086_PreEarlyRequired:
.a16
.i16
 jmp SourceLandingDeath4086_PreRequired
SourceLandingDeath4086_PreEarlyBad:
.a16
.i16
 jmp SourceLandingDeath4086_PreBad
SourceLandingDeath4086_AbovePit:
.a16
.i16
 lda.l SOURCE_WORLD_POOL+78,x
 bpl SourceLandingDeath4086_PreRequired
 lda.l SOURCE_WORLD_POOL+72,x
 sta.l SourceLandingDeath4086_Score
 lda.l SOURCE_WORLD_POOL+74,x
 sta.l SourceLandingDeath4086_Score+2
 lda #0
 sta.l SourceLandingDeath4086_HasScore
 lda.l SourceLandingCallback4086_Opponent
 ora.l SourceLandingCallback4086_Opponent+2
 beq SourceLandingDeath4086_PreGood
 lda.l SourceLandingCallback4086_OppCore
 tax
 lda.l $40C048,x
 and #1
 beq SourceLandingDeath4086_PreGood
 lda.l SourceLandingCallback4086_OppView
 tax
 lda.l SOURCE_WORLD_POOL+40,x
 cmp #1
 bne SourceLandingDeath4086_PreBad
 lda.l SOURCE_WORLD_POOL+42,x
 bne SourceLandingDeath4086_PreBad
 lda.l SOURCE_WORLD_POOL+44,x
 sta.l SourceLandingDeath4086_Player
 lda.l SOURCE_WORLD_POOL+46,x
 sta.l SourceLandingDeath4086_Player+2
 lda #1
 sta.l SourceLandingDeath4086_HasScore
SourceLandingDeath4086_PreGood:
.a16
.i16
 lda #0
 ply
 plx
 plp
 clc
 rtl
SourceLandingDeath4086_PreRequired:
.a16
.i16
 lda #1
 ply
 plx
 plp
 clc
 rtl
SourceLandingDeath4086_PreBad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
SourceLandingDeath4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceLandingDeath4086_Ready
 cmp #$B639
 bne SourceLandingDeath4086_EarlyBad
 lda.l SourceLandingCallback4086_State
 cmp #7
 bne SourceLandingDeath4086_EarlyBad
 lda.l SourceLandingDeath4086_State
 beq SourceLandingDeath4086_Start
 cmp #1
 beq SourceLandingDeath4086_ScoreCall
 cmp #2
 bne SourceLandingDeath4086_EarlyBad
 jmp SourceLandingDeath4086_Done
SourceLandingDeath4086_EarlyBad:
.a16
.i16
 jmp SourceLandingDeath4086_Bad
SourceLandingDeath4086_Start:
.a16
.i16
 lda.l SourceLandingCallback4086_View
 tax
 lda #1
 sta.l $439014,x
 lda #0
 sta.l $439016,x
 lda #1
 sta.l SourceLandingDeath4086_State
SourceLandingDeath4086_ScoreCall:
.a16
.i16
 lda.l SourceLandingDeath4086_HasScore
 beq SourceLandingDeath4086_Flags
 lda.l SourceLandingDeath4086_Player
 sta.l SourceScore4086_Index
 lda.l SourceLandingDeath4086_Player+2
 sta.l SourceScore4086_Index+2
 lda.l SourceLandingDeath4086_Score
 sta.l SourceScore4086_Add
 lda.l SourceLandingDeath4086_Score+2
 sta.l SourceScore4086_Add+2
 jsl SourceScore4086_Execute
 bcs SourceLandingDeath4086_Bad
 lda.l SourceScore4086_Status
 beq SourceLandingDeath4086_Flags
 lda #1
 sta.l SourceLandingDeath4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceLandingDeath4086_Flags:
.a16
.i16
 lda.l SourceLandingCallback4086_View
 tax
 lda #1
 sta.l $439010,x
 lda #0
 sta.l $439012,x
 ; flags row is slot*32, core is slot*96; use physical slot directly.
 lda.l SourceLandingCallback4086_Slot
 asl a
 asl a
 asl a
 asl a
 asl a
 tax
 lda #0
 sta.l $43EB00,x
 sta.l $43EB02,x
 lda #2
 sta.l SourceLandingDeath4086_State
SourceLandingDeath4086_Done:
.a16
.i16
 lda #0
 sta.l SourceLandingDeath4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceLandingDeath4086_Bad:
.a16
.i16
 lda #2
 sta.l SourceLandingDeath4086_Status
 ply
 plx
 plp
 sec
 rtl
