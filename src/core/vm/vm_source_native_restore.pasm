; Restore transfers retained snapshot strings into live slots exactly once.
; Preflight validates immutable table ownership and both saved/current refs.
; No actor, VM, arena or pool mutation occurs before preflight completes.
SourceNativeSnapshot4086_CheckPair:
.a16
.i16
php
rep #$38
phb
phx
phy
phd
tsc
sec
sbc #34
tcs
inc a
tcd
lda #0
sta $20
jmp SourceNativeSnapshot4086_RBegin
SourceNativeSnapshot4086_Restore:
.a16
.i16
php
rep #$38
phb
phx
phy
phd
tsc
sec
sbc #34
tcs
inc a
tcd
lda #1
sta $20
SourceNativeSnapshot4086_RBegin:
.a16
.i16
lda.l SourceNativeSnapshot4086_Ready
cmp #$B614
beq SourceNativeSnapshot4086_RCheck1
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck1:
.a16
.i16
lda.l SourceNativeContinuation4086_Ready
cmp #$B612
beq SourceNativeSnapshot4086_RCheck2
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck2:
.a16
.i16
lda.l SourceFrameStack4086_Ready
cmp #$B4ED
beq SourceNativeSnapshot4086_RCheck3
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck3:
.a16
.i16
lda.l SourceFrameStack4086_Fault
beq SourceNativeSnapshot4086_RCheck4
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck4:
.a16
.i16
lda $20
beq SourceNativeSnapshot4086_RPairDepth
lda.l SourceFrameStack4086_Depth
cmp #7
bcc SourceNativeSnapshot4086_RDepthValid
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RDepthValid:
.a16
.i16
inc a
bra SourceNativeSnapshot4086_RDepthReady
SourceNativeSnapshot4086_RPairDepth:
.a16
.i16
lda.l SourceFrameStack4086_Depth
cmp #2
bcc SourceNativeSnapshot4086_RDepthBad
cmp #9
bcc SourceNativeSnapshot4086_RPairDepthValid
SourceNativeSnapshot4086_RDepthBad:
.a16
.i16
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RPairDepthValid:
.a16
.i16
dec a
SourceNativeSnapshot4086_RDepthReady:
.a16
.i16
pha
xba
asl a
clc
adc #$F000
sta $04
lda #$0040
sta $06
pla
asl a
asl a
asl a
asl a
clc
adc #$FD00
sta $12
tax
lda.l $430000,x
cmp #$B614
beq SourceNativeSnapshot4086_RCheck6
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck6:
.a16
.i16
lda.l $43000E,x
beq SourceNativeSnapshot4086_RCheck7
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck7:
.a16
.i16
lda.l $430002,x
sta $1E
cmp.l SourceNativeContinuation4086_Count
bcc SourceNativeSnapshot4086_RCheck8
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck8:
.a16
.i16
lda.l $430004,x
sta $1C
cmp #513
bcc SourceNativeSnapshot4086_RCheck9
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck9:
.a16
.i16
lda.l $430006,x
sta $1A
cmp #65
bcc SourceNativeSnapshot4086_RCheck10
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck10:
.a16
.i16
lda.l $430008,x
sta $0C
cmp #1025
bcc SourceNativeSnapshot4086_RCheck11
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck11:
.a16
.i16
lda.l SourceNativeContinuation4086_Bank
bne SourceNativeSnapshot4086_RCheck12
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck12:
.a16
.i16
cmp #64
bcc SourceNativeSnapshot4086_RCheck13
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck13:
.a16
.i16
sta $02
lda.l SourceNativeContinuation4086_Base
cmp #$8000
bcs SourceNativeSnapshot4086_RCheck14
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck14:
.a16
.i16
sta $00
lda.l SourceNativeContinuation4086_Bytes
cmp #52
bcs SourceNativeSnapshot4086_RCheck15
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck15:
.a16
.i16
cmp #$8001
bcc SourceNativeSnapshot4086_RCheck16
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck16:
.a16
.i16
clc
adc $00
bcc SourceNativeSnapshot4086_RTableBounds
beq SourceNativeSnapshot4086_RTableBounds
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RTableBounds:
.a16
.i16
ldy #0
lda [$00],y
cmp #$3442
beq SourceNativeSnapshot4086_RCheck17
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck17:
.a16
.i16
ldy #2
lda [$00],y
cmp #$434E
beq SourceNativeSnapshot4086_RCheck18
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck18:
.a16
.i16
ldy #4
lda [$00],y
cmp #1
beq SourceNativeSnapshot4086_RCheck19
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck19:
.a16
.i16
ldy #8
lda [$00],y
cmp #4
beq SourceNativeSnapshot4086_RCheck20
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck20:
.a16
.i16
ldy #10
lda [$00],y
cmp #0
beq SourceNativeSnapshot4086_RCheck21
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck21:
.a16
.i16
ldy #6
lda [$00],y
cmp.l SourceNativeContinuation4086_Count
beq SourceNativeSnapshot4086_RCheck22
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck22:
.a16
.i16
ldx $12
ldy #16
lda [$00],y
cmp.l $430000+10,x
beq SourceNativeSnapshot4086_RCheck23
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck23:
.a16
.i16
ldx $12
ldy #18
lda [$00],y
cmp.l $430000+12,x
beq SourceNativeSnapshot4086_RCheck24
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck24:
.a16
.i16
lda $1E
asl a
asl a
clc
adc #32
tay
lda [$00],y
sta $10
iny
iny
lda [$00],y
sta $18
clc
adc $10
bcc SourceNativeSnapshot4086_RCheck25
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck25:
.a16
.i16
cmp.l SourceNativeContinuation4086_Bytes
bcc SourceNativeSnapshot4086_RRowBounds
beq SourceNativeSnapshot4086_RRowBounds
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RRowBounds:
.a16
.i16
lda $10
cmp #32
bcs SourceNativeSnapshot4086_RCheck26
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck26:
.a16
.i16
lda $10
clc
adc #10
tay
lda [$00],y
cmp $1A
beq SourceNativeSnapshot4086_RCheck27
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck27:
.a16
.i16
lda $10
clc
adc #12
tay
lda [$00],y
cmp $0C
beq SourceNativeSnapshot4086_RCheck28
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck28:
.a16
.i16
lda $10
clc
adc #14
tay
lda [$00],y
cmp $1C
beq SourceNativeSnapshot4086_RCheck29
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck29:
.a16
.i16
lda $1A
asl a
asl a
sta $0E
asl a
clc
adc $0E
sta $0E
clc
adc #237
sta $0A
lda $0C
asl a
asl a
asl a
clc
adc $0A
cmp $1C
beq SourceNativeSnapshot4086_RCheck30
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck30:
.a16
.i16
lda $1A
clc
adc $0C
asl a
clc
adc #16
cmp $18
beq SourceNativeSnapshot4086_RCheck31
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck31:
.a16
.i16
lda $10
clc
adc #0
tay
lda [$00],y
sta $18
ldy #111
lda [$04],y
cmp $18
beq SourceNativeSnapshot4086_RCheck101
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck101:
.a16
.i16
lda $10
clc
adc #2
tay
lda [$00],y
sta $18
ldy #3
lda [$04],y
cmp $18
beq SourceNativeSnapshot4086_RCheck102
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck102:
.a16
.i16
lda $10
clc
adc #4
tay
lda [$00],y
sta $18
ldy #233
lda [$04],y
cmp $18
beq SourceNativeSnapshot4086_RCheck103
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck103:
.a16
.i16
ldy #10
lda [$04],y
cmp $1A
beq SourceNativeSnapshot4086_RCheck104
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck104:
.a16
.i16
lda #0
sta $08
SourceNativeSnapshot4086_RFrameIdentity:
.a16
.i16
lda $08
cmp $1A
bcs SourceNativeSnapshot4086_RFrameIdentityDone
asl a
clc
adc $10
clc
adc #16
tay
lda [$00],y
sta $18
lda $08
asl a
asl a
sta $14
asl a
clc
adc $14
clc
adc #241
tay
lda [$04],y
cmp $18
beq SourceNativeSnapshot4086_RCheck105
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck105:
.a16
.i16
inc $08
jmp SourceNativeSnapshot4086_RFrameIdentity
SourceNativeSnapshot4086_RFrameIdentityDone:
.a16
.i16
lda $1A
asl a
clc
adc $10
clc
adc #16
sta $10
lda #0
sta $08
SourceNativeSnapshot4086_RPreflight:
.a16
.i16
lda $08
cmp $0C
bcc SourceNativeSnapshot4086_RSlot
jmp SourceNativeSnapshot4086_RCopy
SourceNativeSnapshot4086_RSlot:
.a16
.i16
jsr SourceNativeSnapshot4086_RSlotID
bcc SourceNativeSnapshot4086_RCheck32
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck32:
.a16
.i16
sta $14
jsr SourceNativeSnapshot4086_StringHandle
bcc SourceNativeSnapshot4086_RCheck33
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck33:
.a16
.i16
sta $16
jsr SourceNativeSnapshot4086_RRefs
bcc SourceNativeSnapshot4086_RCheck34
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck34:
.a16
.i16
jsr SourceNativeSnapshot4086_RSavedHandle
bcc SourceNativeSnapshot4086_RCheck35
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck35:
.a16
.i16
sta $16
jsr SourceNativeSnapshot4086_RRefs
bcc SourceNativeSnapshot4086_RCheck36
jmp SourceNativeSnapshot4086_RBad
SourceNativeSnapshot4086_RCheck36:
.a16
.i16
inc $08
jmp SourceNativeSnapshot4086_RPreflight
SourceNativeSnapshot4086_RCopy:
.a16
.i16
lda $20
bne SourceNativeSnapshot4086_RCopyRequired
jmp SourceNativeSnapshot4086_RGood
SourceNativeSnapshot4086_RCopyRequired:
.a16
.i16
lda #1
sta.l SourceNativeSnapshot4086_State
lda #0
sta $08
SourceNativeSnapshot4086_RRelease:
.a16
.i16
lda $08
cmp $0C
bcs SourceNativeSnapshot4086_RContext
jsr SourceNativeSnapshot4086_RSlotID
jsr SourceNativeSnapshot4086_StringHandle
cmp #$FFFF
beq SourceNativeSnapshot4086_RReleaseNext
asl a
asl a
asl a
asl a
asl a
asl a
tax
sep #$20
.a8
lda.l VmStrPool_Wram,x
dec a
sta.l VmStrPool_Wram,x
rep #$38
SourceNativeSnapshot4086_RReleaseNext:
.a16
.i16
inc $08
jmp SourceNativeSnapshot4086_RRelease
SourceNativeSnapshot4086_RContext:
.a16
.i16
lda $04
clc
adc #0
tax
ldy #$E090
lda #11
mvn $7F,$40
lda $04
clc
adc #12
tax
ldy #$E09D
lda #14
mvn $7F,$40
lda $04
clc
adc #27
tax
ldy #$F600
lda #71
mvn $7F,$40
lda $04
clc
adc #99
tax
ldy #$F660
lda #29
mvn $7F,$40
lda $04
clc
adc #129
tax
ldy #$F780
lda #25
mvn $7F,$40
lda $04
clc
adc #155
tax
ldy #$F7A0
lda #63
mvn $7F,$40
lda $04
clc
adc #219
tax
ldy #$FB30
lda #7
mvn $7F,$40
lda $04
clc
adc #227
tax
ldy #$F400
lda #9
mvn $7F,$40
lda $0E
beq SourceNativeSnapshot4086_RFramesDone
dec a
pha
lda $04
clc
adc #237
tax
ldy #$E100
pla
mvn $7F,$40
SourceNativeSnapshot4086_RFramesDone:
.a16
.i16
lda #0
sta $08
SourceNativeSnapshot4086_RTransfer:
.a16
.i16
lda $08
cmp $0C
bcs SourceNativeSnapshot4086_RCommit
jsr SourceNativeSnapshot4086_RSlotID
asl a
asl a
asl a
clc
adc #$C000
tay
lda $08
asl a
asl a
asl a
clc
adc $0A
clc
adc $04
tax
lda #7
mvn $7F,$40
inc $08
jmp SourceNativeSnapshot4086_RTransfer
SourceNativeSnapshot4086_RCommit:
.a16
.i16
lda $1E
sta.l SourceNativeContinuation4086_Record
lda $10
sec
sbc #16
sta.l SourceNativeContinuation4086_Row
lda $1A
asl a
sta $18
lda.l SourceNativeContinuation4086_Row
sec
sbc $18
sta.l SourceNativeContinuation4086_Row
clc
adc #8
tay
lda [$00],y
sta.l SourceNativeContinuation4086_ResultSlot
lda #2
sta.l SourceNativeContinuation4086_State
ldx $12
lda #0
sta.l $430000,x
lda #2
sta.l SourceNativeSnapshot4086_State
jmp SourceNativeSnapshot4086_RGood
SourceNativeSnapshot4086_RBad:
.a16
.i16
lda #3
sta.l SourceNativeSnapshot4086_State
tsc
clc
adc #34
tcs
pld
ply
plx
plb
plp
sec
rtl
SourceNativeSnapshot4086_RGood:
.a16
.i16
tsc
clc
adc #34
tcs
pld
ply
plx
plb
plp
clc
rtl
SourceNativeSnapshot4086_RSlotID:
.a16
.i16
lda $08
asl a
clc
adc $10
tay
lda [$00],y
cmp #1024
bcs SourceNativeSnapshot4086_RHelperBad
sta $14
ldy #14
lda [$04],y
cmp #1025
bcs SourceNativeSnapshot4086_RHelperBad
cmp $14
bcc SourceNativeSnapshot4086_RHelperBad
beq SourceNativeSnapshot4086_RHelperBad
lda $08
asl a
clc
adc $10
tay
lda $14
pha
lda $08
beq SourceNativeSnapshot4086_RIDGood
dey
dey
lda [$00],y
sta $18
pla
cmp $18
bcc SourceNativeSnapshot4086_RHelperBad
beq SourceNativeSnapshot4086_RHelperBad
clc
rts
SourceNativeSnapshot4086_RIDGood:
.a16
.i16
pla
clc
rts
SourceNativeSnapshot4086_RSavedHandle:
.a16
.i16
lda $08
asl a
asl a
asl a
clc
adc $0A
tay
lda [$04],y
and #$00FF
cmp #BOR_VT_STR
bne SourceNativeSnapshot4086_RNotDynamic
iny
iny
iny
iny
iny
iny
lda [$04],y
bpl SourceNativeSnapshot4086_RNotDynamic
cmp #$8000
bne SourceNativeSnapshot4086_RHelperBad
dey
dey
lda [$04],y
cmp #64
bcs SourceNativeSnapshot4086_RHelperBad
clc
rts
SourceNativeSnapshot4086_RNotDynamic:
.a16
.i16
lda #$FFFF
clc
rts
SourceNativeSnapshot4086_RHelperBad:
.a16
.i16
sec
rts
SourceNativeSnapshot4086_RRefs:
.a16
.i16
lda $16
cmp #$FFFF
beq SourceNativeSnapshot4086_RRefsGood
lda $08
pha
lda #0
sta $08
sta $18
SourceNativeSnapshot4086_RRefsLoop:
.a16
.i16
lda $08
cmp $0C
bcs SourceNativeSnapshot4086_RRefsCounted
lda $08
asl a
clc
adc $10
tay
lda [$00],y
cmp #1024
bcs SourceNativeSnapshot4086_RRefsFail
jsr SourceNativeSnapshot4086_StringHandle
bcs SourceNativeSnapshot4086_RRefsFail
cmp $16
bne SourceNativeSnapshot4086_RRefsSaved
inc $18
SourceNativeSnapshot4086_RRefsSaved:
.a16
.i16
jsr SourceNativeSnapshot4086_RSavedHandle
bcs SourceNativeSnapshot4086_RRefsFail
cmp $16
bne SourceNativeSnapshot4086_RRefsNext
inc $18
SourceNativeSnapshot4086_RRefsNext:
.a16
.i16
inc $08
jmp SourceNativeSnapshot4086_RRefsLoop
SourceNativeSnapshot4086_RRefsCounted:
.a16
.i16
lda $16
asl a
asl a
asl a
asl a
asl a
asl a
tax
lda.l VmStrPool_Wram,x
and #$00FF
cmp $18
bcc SourceNativeSnapshot4086_RRefsFail
pla
sta $08
SourceNativeSnapshot4086_RRefsGood:
.a16
.i16
clc
rts
SourceNativeSnapshot4086_RRefsFail:
.a16
.i16
pla
sta $08
sec
rts
