; B638 optional copied death modeldata. A=physical slot, X=current model.
; View tail +72 score int32/+76 diesound int32. Relation +56 model/+58 B638
; owns that extension; +60 source item pointer (calloc NULL at fresh birth).
; Copy preserves item on model changes. No item/death/boss service is hidden.
; B4DF score rows; diesound is copied from current mutable cached model +76.
SourceDeathFields4086_Ready = $7EFF5A
SourceDeathFields4086_Base = $7EFF5C
SourceDeathFields4086_Bank = $7EFF5E
SourceDeathFields4086_Bytes = $7EFF60
SourceDeathFields4086_Models = $7EFF62
SourceDeathFields4086_Slot = $7EFF64
SourceDeathFields4086_Model = $7EFF66
SourceDeathFields4086_View = $7EFF68
SourceDeathFields4086_Relation = $7EFF6A
SourceDeathFields4086_Cache = $7EFF6C
SourceDeathFields4086_Row = $7EFF6E
SourceDeathFields4086_Score = $7EFF70
SourceDeathFields4086_Sound = $7EFF74
SourceDeathFields4086_End = $7EFF78
SourceDeathFields4086_Preflight:
.a16
.i16
 php
 rep #$38
 phx
 phy
 pha
 lda.l SourceDeathFields4086_Ready
 beq SourceDeathFields4086_Disabled
 cmp #$B638
 beq SourceDeathFields4086_Capture
 jmp SourceDeathFields4086_PreBadStack
SourceDeathFields4086_Disabled:
.a16
.i16
 pla
 ply
 plx
 plp
 clc
 rtl
SourceDeathFields4086_Capture:
.a16
.i16
 pla
 sta.l SourceDeathFields4086_Slot
 cmp #128
 bcc SourceDeathFields4086_SlotGood
 jmp SourceDeathFields4086_PreBad
SourceDeathFields4086_SlotGood:
.a16
.i16
 txa
 sta.l SourceDeathFields4086_Model
 lda.l SourceModelEntityCopy4086_Ready
 cmp #$B4EB
 beq SourceDeathFields4086_CoreGood
 jmp SourceDeathFields4086_PreBad
SourceDeathFields4086_CoreGood:
.a16
.i16
 lda.l SourceModelEntityCopy4086_Entities
 beq SourceDeathFields4086_PreBad
 cmp #129
 bcs SourceDeathFields4086_PreBad
 cmp.l SourceDeathFields4086_Slot
 beq SourceDeathFields4086_PreBad
 bcc SourceDeathFields4086_PreBad
 lda.l SourceDeathFields4086_Models
 beq SourceDeathFields4086_PreBad
 cmp #17
 bcs SourceDeathFields4086_PreBad
 cmp.l SourceModelEntityCopy4086_Models
 bne SourceDeathFields4086_PreBad
 cmp.l SourceDeathFields4086_Model
 beq SourceDeathFields4086_PreBad
 bcc SourceDeathFields4086_PreBad
 asl a
 asl a
 asl a
 clc
 adc #24
 cmp.l SourceDeathFields4086_Bytes
 bne SourceDeathFields4086_PreBad
 lda.l SourceDeathFields4086_Base
 cmp #$8000
 bcc SourceDeathFields4086_PreBad
 clc
 adc.l SourceDeathFields4086_Bytes
 bcs SourceDeathFields4086_PreBad
 lda.l SourceDeathFields4086_Bank
 cmp #$100
 bcs SourceDeathFields4086_PreBad
 cmp #$40
 bcc SourceDeathFields4086_RomGood
 cmp #$C0
 bcs SourceDeathFields4086_RomGood
 bra SourceDeathFields4086_PreBad
SourceDeathFields4086_PreBadStack:
.a16
.i16
 pla
SourceDeathFields4086_PreBad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
SourceDeathFields4086_RomGood:
.a16
.i16
 lda.l SourceDeathFields4086_Base
 tax
 jsr SourceDeathFields4086_Read
 cmp #$3442
 bne SourceDeathFields4086_PreBad
 inx
 inx
 jsr SourceDeathFields4086_Read
 cmp #$4644
 bne SourceDeathFields4086_PreBad
 inx
 inx
 jsr SourceDeathFields4086_Read
 cmp #1
 bne SourceDeathFields4086_PreBad
 inx
 inx
 jsr SourceDeathFields4086_Read
 cmp #8
 bne SourceDeathFields4086_PreBad
 inx
 inx
 jsr SourceDeathFields4086_Read
 cmp.l SourceDeathFields4086_Models
 bne SourceDeathFields4086_PreBad
 ldy #7
SourceDeathFields4086_HeaderReserved:
.a16
.i16
 inx
 inx
 jsr SourceDeathFields4086_Read
 bne SourceDeathFields4086_PreBad
 dey
 bne SourceDeathFields4086_HeaderReserved
 lda.l SourceDeathFields4086_Model
 asl a
 asl a
 asl a
 clc
 adc #24
 clc
 adc.l SourceDeathFields4086_Base
 sta.l SourceDeathFields4086_Row
 tax
 jsr SourceDeathFields4086_Read
 cmp.l SourceDeathFields4086_Model
 beq SourceDeathFields4086_RowGood
 jmp SourceDeathFields4086_PreBad
SourceDeathFields4086_RowGood:
.a16
.i16
 inx
 inx
 jsr SourceDeathFields4086_Read
 beq SourceDeathFields4086_ReservedGood
 jmp SourceDeathFields4086_PreBad
SourceDeathFields4086_ReservedGood:
.a16
.i16
 inx
 inx
 jsr SourceDeathFields4086_Read
 sta.l SourceDeathFields4086_Score
 inx
 inx
 jsr SourceDeathFields4086_Read
 sta.l SourceDeathFields4086_Score+2
 lda.l SourceDeathFields4086_Model
 asl a
 asl a
 asl a
 asl a
 asl a
 pha
 asl a
 asl a
 clc
 adc 1,s
 sta.l SourceDeathFields4086_Cache
 pla
 lda.l SourceDeathFields4086_Cache
 tax
 lda.l $40B04C,x
 sta.l SourceDeathFields4086_Sound
 lda.l $40B04E,x
 sta.l SourceDeathFields4086_Sound+2
 lda.l SourceDeathFields4086_Slot
 asl a
 asl a
 asl a
 asl a
 pha
 asl a
 asl a
 sta.l SourceDeathFields4086_Relation
 clc
 adc 1,s
 sta.l SourceDeathFields4086_View
 pla
 ply
 plx
 plp
 clc
 rtl
SourceDeathFields4086_Copy:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jsl SourceDeathFields4086_Preflight
 bcs SourceDeathFields4086_CopyBad
 lda.l SourceDeathFields4086_Ready
 beq SourceDeathFields4086_CopyGood
 lda.l SourceDeathFields4086_View
 tax
 lda.l SourceDeathFields4086_Score
 sta.l SOURCE_WORLD_POOL+72,x
 lda.l SourceDeathFields4086_Score+2
 sta.l SOURCE_WORLD_POOL+74,x
 lda.l SourceDeathFields4086_Sound
 sta.l SOURCE_WORLD_POOL+76,x
 lda.l SourceDeathFields4086_Sound+2
 sta.l SOURCE_WORLD_POOL+78,x
 lda.l SourceDeathFields4086_Relation
 tax
 lda.l SourceDeathFields4086_Model
 sta.l $409038,x
 lda #$B638
 sta.l $40903A,x
SourceDeathFields4086_CopyGood:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
SourceDeathFields4086_CopyBad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
SourceDeathFields4086_Birth:
.a16
.i16
 php
 rep #$38
 phx
 jsl SourceDeathFields4086_Copy
 bcs SourceDeathFields4086_BirthBad
 lda.l SourceDeathFields4086_Ready
 beq SourceDeathFields4086_BirthGood
 lda.l SourceDeathFields4086_Relation
 tax
 lda #0
 sta.l $40903C,x
 sta.l $40903E,x
SourceDeathFields4086_BirthGood:
.a16
.i16
 plx
 plp
 clc
 rtl
SourceDeathFields4086_BirthBad:
.a16
.i16
 plx
 plp
 sec
 rtl
SourceDeathFields4086_Read:
.a16
.i16
 phb
 sep #$20
.a8
 lda.l SourceDeathFields4086_Bank
 pha
 plb
 rep #$20
.a16
 lda.w $0000,x
 plb
 ora #0
 rts
