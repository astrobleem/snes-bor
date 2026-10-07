; Equal-bound normal attack chance, using compiler-proven literal C cutoff.
; Caller selects the exact immutable model/on-screen cutoff. This numeric
; kernel alone does not grant a model lease or execute normal_prepare.
; Even a certain outcome consumes randf(1)'s ONE real RNG call unless ALWAYS.
SourceNormalChance4086_Ready = $43BEEC
SourceNormalChance4086_Status = $43BEEE
SourceNormalChance4086_Cutoff = $43BEF0
SourceNormalChance4086_AI = $43BEF2
SourceNormalChance4086_Result = $43BEF6
SourceNormalChance4086_Residue = $43BEFA
SourceNormalChance4086_End = $43BEFC
SourceNormalChance4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceNormalChance4086_Ready
 cmp #$B600
 beq SourceNormalChance4086_Lease
 jmp SourceNormalChance4086_Bad
SourceNormalChance4086_Lease:
.a16
.i16
 lda.l SourceNormalChance4086_Status
 beq SourceNormalChance4086_Start
 cmp #2
 beq SourceNormalChance4086_Start
 jmp SourceNormalChance4086_Bad
SourceNormalChance4086_Start:
.a16
.i16
 lda #1
 sta.l SourceNormalChance4086_Status
 lda.l SourceNormalChance4086_AI
 and #8
 beq SourceNormalChance4086_CutoffCheck
 jmp SourceNormalChance4086_True
SourceNormalChance4086_CutoffCheck:
.a16
.i16
 lda.l SourceNormalChance4086_Cutoff
 cmp #$FFFF
 beq SourceNormalChance4086_Draw
 cmp #10000
 bcc SourceNormalChance4086_Draw
 jmp SourceNormalChance4086_Bad
SourceNormalChance4086_Draw:
.a16
.i16
 lda.l VmNativeVariant_Result
 pha
 lda.l VmNativeVariant_Result+2
 pha
 lda.l VmNativeVariant_Result+4
 pha
 lda.l VmNativeVariant_Result+6
 pha
 lda.l SourceModelEntityCopy4086_Lo
 pha
 lda.l SourceModelEntityCopy4086_Hi
 pha
 jsl SourceRandom4086_Next
 bcc SourceNormalChance4086_Modulo
 jmp SourceNormalChance4086_RestoreBad
SourceNormalChance4086_Modulo:
.a16
.i16
 lda.l VmNativeVariant_Result+4
 sta.l SourceModelEntityCopy4086_Lo
 lda.l VmNativeVariant_Result+6
 sta.l SourceModelEntityCopy4086_Hi
 jsl SourceRandomFloat4086_Modulo10000
 sta.l SourceNormalChance4086_Residue
 jsr SourceNormalChance4086_Restore
 lda.l SourceNormalChance4086_Cutoff
 cmp #$FFFF
 beq SourceNormalChance4086_False
 cmp.l SourceNormalChance4086_Residue
 bcc SourceNormalChance4086_False
SourceNormalChance4086_True:
.a16
.i16
 lda #1
 bra SourceNormalChance4086_Done
SourceNormalChance4086_False:
.a16
.i16
 lda #0
SourceNormalChance4086_Done:
.a16
.i16
 sta.l SourceNormalChance4086_Result
 lda #0
 sta.l SourceNormalChance4086_Result+2
 lda #2
 sta.l SourceNormalChance4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceNormalChance4086_RestoreBad:
.a16
.i16
 jsr SourceNormalChance4086_Restore
SourceNormalChance4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceNormalChance4086_Status
 ply
 plx
 plp
 sec
 rtl
SourceNormalChance4086_Restore:
.a16
.i16
 ; JSR's return address occupies the top stack word. Restore through
 ; indexed stack reads, then remove six saved words below that address.
 lda 3,s
 sta.l SourceModelEntityCopy4086_Hi
 lda 5,s
 sta.l SourceModelEntityCopy4086_Lo
 lda 7,s
 sta.l VmNativeVariant_Result+6
 lda 9,s
 sta.l VmNativeVariant_Result+4
 lda 11,s
 sta.l VmNativeVariant_Result+2
 lda 13,s
 sta.l VmNativeVariant_Result
 pla
 sta 11,s
 tsc
 clc
 adc #10
 tcs
 rts
