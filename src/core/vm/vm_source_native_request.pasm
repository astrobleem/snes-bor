; Named knife request only. No actor or allocator mutation here.
; B615 admits eight-argument named, nonrelative, type0/map0 presentation.
; Numeric coordinates use the explicit existing ACCEPTED_COMPAT_Q16_16 ABI.
; Foreground MUST execute the paired constructor before resuming this VM.
SourceNativeRequest4086_Projectile:
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
sbc #20
tcs
inc a
tcd
lda.l SourceNativeRequest4086_Ready
cmp #$B615
beq SourceNativeRequest4086_Check1
jmp SourceNativeRequest4086_Bad
SourceNativeRequest4086_Check1:
.a16
.i16
lda.l SourceNativeContinuation4086_Ready
cmp #$B612
beq SourceNativeRequest4086_Check2
jmp SourceNativeRequest4086_Bad
SourceNativeRequest4086_Check2:
.a16
.i16
lda.l SourceNativeSnapshot4086_Ready
cmp #$B614
beq SourceNativeRequest4086_Check3
jmp SourceNativeRequest4086_Bad
SourceNativeRequest4086_Check3:
.a16
.i16
lda.l SourceNamedKnife4086_Ready
cmp #$B611
beq SourceNativeRequest4086_Check4
jmp SourceNativeRequest4086_Bad
SourceNativeRequest4086_Check4:
.a16
.i16
lda.l VmNativeVariant_ContextValid
cmp #$B48F
beq SourceNativeRequest4086_Check5
jmp SourceNativeRequest4086_Bad
SourceNativeRequest4086_Check5:
.a16
.i16
lda.l SourceVMRun4086_Busy
cmp #$B4D8
beq SourceNativeRequest4086_Check6
jmp SourceNativeRequest4086_Bad
SourceNativeRequest4086_Check6:
.a16
.i16
lda.l SourceCtorState4086_Ready
cmp #$B5C2
beq SourceNativeRequest4086_Check7
jmp SourceNativeRequest4086_Bad
SourceNativeRequest4086_Check7:
.a16
.i16
lda.l SourceSpawnSlot4086_Ready
cmp #$B5A1
beq SourceNativeRequest4086_Check8
jmp SourceNativeRequest4086_Bad
SourceNativeRequest4086_Check8:
.a16
.i16
lda.l SourceUpdateFrame4086_Ready
cmp #$B4E3
beq SourceNativeRequest4086_Check9
jmp SourceNativeRequest4086_Bad
SourceNativeRequest4086_Check9:
.a16
.i16
lda.l SourceUpdateFrame4086_State
cmp #1
beq SourceNativeRequest4086_Check10
jmp SourceNativeRequest4086_Bad
SourceNativeRequest4086_Check10:
.a16
.i16
lda.l SourceUpdateFrame4086_Pending
cmp #1
beq SourceNativeRequest4086_Check11
jmp SourceNativeRequest4086_Bad
SourceNativeRequest4086_Check11:
.a16
.i16
lda.l SourceNativeContinuation4086_Request
beq SourceNativeRequest4086_Check12
jmp SourceNativeRequest4086_Bad
SourceNativeRequest4086_Check12:
.a16
.i16
lda.l VmState_Status
and #$00FF
cmp #VMSTAT_RUNNING
beq SourceNativeRequest4086_Check13
jmp SourceNativeRequest4086_Bad
SourceNativeRequest4086_Check13:
.a16
.i16
lda.l VmCall_TargetId
cmp #$020E
beq SourceNativeRequest4086_Check14
jmp SourceNativeRequest4086_Bad
SourceNativeRequest4086_Check14:
.a16
.i16
lda.l VmCall_Argc
and #$00FF
cmp #8
beq SourceNativeRequest4086_Check15
jmp SourceNativeRequest4086_Bad
SourceNativeRequest4086_Check15:
.a16
.i16
lda #0
jsl SourceNativeArgument4086_Read
jsl SourceModelName4086_Resolve
bcc SourceNativeRequest4086_Check16
jmp SourceNativeRequest4086_Bad
SourceNativeRequest4086_Check16:
.a16
.i16
sta $10
lda #1
sta $12
SourceNativeRequest4086_Coordinate:
.a16
.i16
lda $12
jsl SourceNativeArgument4086_Read
lda #BOR_VT_DECIMAL
sta.l VmSourceMutation_Tag
jsl SourceNativeNumber4086_Convert
bcc SourceNativeRequest4086_Check17
jmp SourceNativeRequest4086_Bad
SourceNativeRequest4086_Check17:
.a16
.i16
lda $12
dec a
asl a
asl a
tax
lda.l VmSourceMutation_Lo
sta $00,x
lda.l VmSourceMutation_Hi
sta $02,x
inc $12
lda $12
cmp #4
bcc SourceNativeRequest4086_Coordinate
lda #4
jsl SourceNativeArgument4086_Read
lda #BOR_VT_INTEGER
sta.l VmSourceMutation_Tag
jsl SourceNativeNumber4086_Convert
bcc SourceNativeRequest4086_Check18
jmp SourceNativeRequest4086_Bad
SourceNativeRequest4086_Check18:
.a16
.i16
lda.l VmSourceMutation_Lo
sta $0C
lda.l VmSourceMutation_Hi
sta $0E
lda #5
jsl SourceNativeArgument4086_Read
jsl SourceNativeNumber4086_Convert
bcc SourceNativeRequest4086_Check19
jmp SourceNativeRequest4086_Bad
SourceNativeRequest4086_Check19:
.a16
.i16
lda #6
jsl SourceNativeArgument4086_Read
jsl SourceNativeNumber4086_Convert
bcc SourceNativeRequest4086_Check20
jmp SourceNativeRequest4086_Bad
SourceNativeRequest4086_Check20:
.a16
.i16
lda.l VmSourceMutation_Lo
ora.l VmSourceMutation_Hi
beq SourceNativeRequest4086_Check21
jmp SourceNativeRequest4086_Bad
SourceNativeRequest4086_Check21:
.a16
.i16
lda #7
jsl SourceNativeArgument4086_Read
jsl SourceNativeNumber4086_Convert
bcc SourceNativeRequest4086_Check22
jmp SourceNativeRequest4086_Bad
SourceNativeRequest4086_Check22:
.a16
.i16
lda.l VmSourceMutation_Lo
ora.l VmSourceMutation_Hi
beq SourceNativeRequest4086_Check23
jmp SourceNativeRequest4086_Bad
SourceNativeRequest4086_Check23:
.a16
.i16
lda $10
sta.l SourceSpawnSlot4086_Model
lda $00
sta.l SourceCtorState4086_X
lda $02
sta.l SourceCtorState4086_X+2
lda $04
sta.l SourceCtorState4086_Z
lda $06
sta.l SourceCtorState4086_Z+2
lda $08
sta.l SourceCtorState4086_A
lda $0A
sta.l SourceCtorState4086_A+2
lda $0C
sta.l SourceCtorState4086_Direction
lda $0E
sta.l SourceCtorState4086_Direction+2
lda #0
sta.l VmNativeVariant_Result
sta.l VmNativeVariant_Result+2
sta.l VmNativeVariant_Result+4
sta.l VmNativeVariant_Result+6
sta.l VmState_Budget
lda #$B613
sta.l SourceNativeContinuation4086_Request
tsc
clc
adc #20
tcs
pld
ply
plx
plb
plp
clc
rtl
SourceNativeRequest4086_Bad:
.a16
.i16
tsc
clc
adc #20
tcs
pld
ply
plx
plb
lda #VMERR_BAD_NATIVE
plp
sec
rtl
