; Exact count_ents predicate over the admitted fixed source pool.
; A=type mask (low sixteen bits), returns A=count, C=fault.
; No entity writes or global scratch. Pointer permutation does not affect count.
SourceCountEntities4086_Count:
.a16
.i16
 php
 rep #$38
 phx
 phy
 pha
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 bne SourceCountEntities4086_Bad
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 bne SourceCountEntities4086_Bad
 lda.l VmSourceWorld_Count
 beq SourceCountEntities4086_Bad
 cmp #129
 bcs SourceCountEntities4086_Bad
 pha ; remaining, above input mask
 lda #0
 pha ; counter
 ldx #0
 ldy #0
SourceCountEntities4086_Loop:
.a16
.i16
 lda.l $414004,x
 ora.l $414006,x
 beq SourceCountEntities4086_Next
 phx
 tyx
 lda.l $40C048,x
 plx
 and 5,s
 beq SourceCountEntities4086_Next
 lda 1,s
 inc a
 sta 1,s
SourceCountEntities4086_Next:
.a16
.i16
 txa
 clc
 adc #80
 tax
 tya
 clc
 adc #96
 tay
 lda 3,s
 dec a
 sta 3,s
 bne SourceCountEntities4086_Loop
 lda 1,s
 sta 5,s
 pla
 pla
 pla
 ply
 plx
 plp
 clc
 rtl
SourceCountEntities4086_Bad:
.a16
.i16
 pla
 ply
 plx
 plp
 sec
 rtl
