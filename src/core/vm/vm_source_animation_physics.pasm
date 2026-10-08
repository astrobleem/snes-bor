; B61F immutable B4PH lookup. Explicit owner reserves $41FF00..$41FF4F,
; the unused former quake scratch. No actor mutation or gravity admission.
SourceAnimationPhysics4086_Ready = $41FF00
SourceAnimationPhysics4086_Status = $41FF02
SourceAnimationPhysics4086_Base = $41FF04
SourceAnimationPhysics4086_Bank = $41FF06
SourceAnimationPhysics4086_Bytes = $41FF08
SourceAnimationPhysics4086_Animations = $41FF0A
SourceAnimationPhysics4086_Handle = $41FF0C
SourceAnimationPhysics4086_Frame = $41FF0E
SourceAnimationPhysics4086_Antigrav = $41FF10
SourceAnimationPhysics4086_DropFrame = $41FF14
SourceAnimationPhysics4086_LandFrame = $41FF18
SourceAnimationPhysics4086_LandEntity = $41FF1C
SourceAnimationPhysics4086_FrameBase = $41FF20
SourceAnimationPhysics4086_FrameY = $41FF24
SourceAnimationPhysics4086_Count = $41FF28
SourceAnimationPhysics4086_Directory = $41FF2A
SourceAnimationPhysics4086_FrameStart = $41FF2C
SourceAnimationPhysics4086_TableEnd = $41FF2E
SourceAnimationPhysics4086_Scratch = $41FF30
SourceAnimationPhysics4086_ScratchCount = $41FF48
SourceAnimationPhysics4086_DirectoryEnd = $41FF4A
SourceAnimationPhysics4086_Temp = $41FF4C
SourceAnimationPhysics4086_End = $41FF50
SourceAnimationPhysics4086_Query:
.a16
.i16
 php
 rep #$38
 pha
 phx
 phy
 lda.l SourceAnimationPhysics4086_Ready
 cmp #$B61F
 beq SourceAnimationPhysics4086_Guard1
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_Guard1:
.a16
.i16
 lda.l SourceAnimationPhysics4086_Status
 beq SourceAnimationPhysics4086_Guard2
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_Guard2:
.a16
.i16
 lda.l SourceAnimationPhysics4086_Bank
 and #$FF00
 beq SourceAnimationPhysics4086_Guard3
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_Guard3:
.a16
.i16
 lda.l SourceAnimationPhysics4086_Bank
 cmp #$0040
 bcc SourceAnimationPhysics4086_RomBank
 cmp #$0080
 bcs SourceAnimationPhysics4086_Guard4
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_Guard4:
.a16
.i16
SourceAnimationPhysics4086_RomBank:
.a16
.i16
 lda.l SourceAnimationPhysics4086_Bytes
 cmp #16
 bcs SourceAnimationPhysics4086_Guard5
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_Guard5:
.a16
.i16
 cmp #32769
 bcc SourceAnimationPhysics4086_Guard6
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_Guard6:
.a16
.i16
 lda.l SourceAnimationPhysics4086_Animations
 bne SourceAnimationPhysics4086_Guard7
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_Guard7:
.a16
.i16
 cmp #129
 bcc SourceAnimationPhysics4086_Guard8
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_Guard8:
.a16
.i16
 asl a
 asl a
 asl a
 sta.l SourceAnimationPhysics4086_Temp
 asl a
 clc
 adc.l SourceAnimationPhysics4086_Temp
 clc
 adc #16
 sta.l SourceAnimationPhysics4086_DirectoryEnd
 cmp.l SourceAnimationPhysics4086_Bytes
 bcc SourceAnimationPhysics4086_Guard9
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_Guard9:
.a16
.i16
 lda.l SourceAnimationPhysics4086_Base
 cmp #$8000
 bcs SourceAnimationPhysics4086_Guard10
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_Guard10:
.a16
.i16
 cmp #$FFF1
 bcc SourceAnimationPhysics4086_Guard11
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_Guard11:
.a16
.i16
 clc
 adc.l SourceAnimationPhysics4086_Bytes
 bcc SourceAnimationPhysics4086_EndFits
 cmp #0
 beq SourceAnimationPhysics4086_Guard12
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_Guard12:
.a16
.i16
SourceAnimationPhysics4086_EndFits:
.a16
.i16
 sta.l SourceAnimationPhysics4086_TableEnd
 lda.l SourceAnimationPhysics4086_Base
 tax
 jsr SourceAnimationPhysics4086_Read
 cmp #$3442
 beq SourceAnimationPhysics4086_Guard13
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_Guard13:
.a16
.i16
 inx
 inx
 jsr SourceAnimationPhysics4086_Read
 cmp #$4850
 beq SourceAnimationPhysics4086_Guard14
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_Guard14:
.a16
.i16
 inx
 inx
 jsr SourceAnimationPhysics4086_Read
 cmp #1
 beq SourceAnimationPhysics4086_Guard15
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_Guard15:
.a16
.i16
 inx
 inx
 jsr SourceAnimationPhysics4086_Read
 cmp.l SourceAnimationPhysics4086_Animations
 beq SourceAnimationPhysics4086_Guard16
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_Guard16:
.a16
.i16
 inx
 inx
 jsr SourceAnimationPhysics4086_Read
 cmp.l SourceAnimationPhysics4086_Bytes
 beq SourceAnimationPhysics4086_Guard17
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_Guard17:
.a16
.i16
 inx
 inx
 jsr SourceAnimationPhysics4086_Read
 beq SourceAnimationPhysics4086_Guard18
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_Guard18:
.a16
.i16
 inx
 inx
 jsr SourceAnimationPhysics4086_Read
 beq SourceAnimationPhysics4086_Guard19
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_Guard19:
.a16
.i16
 inx
 inx
 jsr SourceAnimationPhysics4086_Read
 beq SourceAnimationPhysics4086_Guard20
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_Guard20:
.a16
.i16
 lda.l SourceAnimationPhysics4086_Handle
 bne SourceAnimationPhysics4086_Guard21
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_Guard21:
.a16
.i16
 cmp.l SourceAnimationPhysics4086_Animations
 beq SourceAnimationPhysics4086_HandleValid
 bcc SourceAnimationPhysics4086_Guard22
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_Guard22:
.a16
.i16
SourceAnimationPhysics4086_HandleValid:
.a16
.i16
 dec a
 asl a
 asl a
 asl a
 sta.l SourceAnimationPhysics4086_Temp
 asl a
 clc
 adc.l SourceAnimationPhysics4086_Temp
 clc
 adc #16
 clc
 adc.l SourceAnimationPhysics4086_Base
 tax
 sta.l SourceAnimationPhysics4086_Directory
 jsr SourceAnimationPhysics4086_Read
 cmp.l SourceAnimationPhysics4086_Handle
 beq SourceAnimationPhysics4086_Guard23
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_Guard23:
.a16
.i16
 inx
 inx
 jsr SourceAnimationPhysics4086_Read
 bne SourceAnimationPhysics4086_Guard24
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_Guard24:
.a16
.i16
 cmp #4096
 bcc SourceAnimationPhysics4086_Guard25
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_Guard25:
.a16
.i16
 sta.l SourceAnimationPhysics4086_ScratchCount
 inx
 inx
 jsr SourceAnimationPhysics4086_Read
 cmp #2
 bcc SourceAnimationPhysics4086_Guard26
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_Guard26:
.a16
.i16
 inx
 inx
 jsr SourceAnimationPhysics4086_Read
 beq SourceAnimationPhysics4086_AntigravHighValid
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_AntigravHighValid:
.a16
.i16
 dex
 dex
 ldy #0
SourceAnimationPhysics4086_MetaLoop:
.a16
.i16
 jsr SourceAnimationPhysics4086_Read
 sta.l SourceAnimationPhysics4086_Temp
 phx
 tyx
 lda.l SourceAnimationPhysics4086_Temp
 sta.l SourceAnimationPhysics4086_Scratch,x
 plx
 inx
 inx
 iny
 iny
 cpy #16
 bne SourceAnimationPhysics4086_MetaLoop
 jsr SourceAnimationPhysics4086_Read
 sta.l SourceAnimationPhysics4086_FrameStart
 cmp.l SourceAnimationPhysics4086_DirectoryEnd
 bcs SourceAnimationPhysics4086_Guard27
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_Guard27:
.a16
.i16
 inx
 inx
 jsr SourceAnimationPhysics4086_Read
 beq SourceAnimationPhysics4086_Guard28
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_Guard28:
.a16
.i16
 lda.l SourceAnimationPhysics4086_ScratchCount
 asl a
 asl a
 asl a
 clc
 adc.l SourceAnimationPhysics4086_FrameStart
 bcc SourceAnimationPhysics4086_Guard29
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_Guard29:
.a16
.i16
 cmp.l SourceAnimationPhysics4086_Bytes
 beq SourceAnimationPhysics4086_FrameSpanValid
 bcc SourceAnimationPhysics4086_Guard30
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_Guard30:
.a16
.i16
SourceAnimationPhysics4086_FrameSpanValid:
.a16
.i16
 lda.l SourceAnimationPhysics4086_Frame
 cmp.l SourceAnimationPhysics4086_ScratchCount
 bcc SourceAnimationPhysics4086_Guard31
 jmp SourceAnimationPhysics4086_Bad
SourceAnimationPhysics4086_Guard31:
.a16
.i16
 asl a
 asl a
 asl a
 clc
 adc.l SourceAnimationPhysics4086_FrameStart
 clc
 adc.l SourceAnimationPhysics4086_Base
 tax
 ldy #16
SourceAnimationPhysics4086_FrameLoop:
.a16
.i16
 jsr SourceAnimationPhysics4086_Read
 sta.l SourceAnimationPhysics4086_Temp
 phx
 tyx
 lda.l SourceAnimationPhysics4086_Temp
 sta.l SourceAnimationPhysics4086_Scratch,x
 plx
 inx
 inx
 iny
 iny
 cpy #24
 bne SourceAnimationPhysics4086_FrameLoop
 ldx #0
SourceAnimationPhysics4086_Publish:
.a16
.i16
 lda.l SourceAnimationPhysics4086_Scratch,x
 sta.l SourceAnimationPhysics4086_Antigrav,x
 inx
 inx
 cpx #24
 bne SourceAnimationPhysics4086_Publish
 lda.l SourceAnimationPhysics4086_ScratchCount
 sta.l SourceAnimationPhysics4086_Count
 lda #2
 sta.l SourceAnimationPhysics4086_Status
 ply
 plx
 pla
 plp
 clc
 rtl
SourceAnimationPhysics4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceAnimationPhysics4086_Status
 ply
 plx
 pla
 plp
 sec
 rtl
SourceAnimationPhysics4086_Read:
.a16
.i16
 phb
 sep #$20
.a8
 lda.l SourceAnimationPhysics4086_Bank
 pha
 plb
 rep #$20
.a16
 lda.w $0000,x
 plb
 ora #0
 rts
