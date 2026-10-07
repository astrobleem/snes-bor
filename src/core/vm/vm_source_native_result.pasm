; A=literal completed constructor physical slot, FFFF for NULL.
; Publish the complete PTR into the restored native CALL result slot.
; Dead constructor pointers remain valid; no alive-only substitution.
; Snapshot restore supplies its immutable record/result identity.
SourceNativeResult4086_Publish:
.a16
.i16
php
rep #$38
pha
phb
phx
phy
phd
tsc
sec
sbc #8
tcs
inc a
tcd
lda 16,s
sta $04
lda.l SourceNativeRequest4086_Ready
cmp #$B615
beq SourceNativeResult4086_Check1
jmp SourceNativeResult4086_Bad
SourceNativeResult4086_Check1:
.a16
.i16
lda.l SourceNativeSnapshot4086_Ready
cmp #$B614
beq SourceNativeResult4086_Check2
jmp SourceNativeResult4086_Bad
SourceNativeResult4086_Check2:
.a16
.i16
lda.l SourceNativeSnapshot4086_State
cmp #2
beq SourceNativeResult4086_Check3
jmp SourceNativeResult4086_Bad
SourceNativeResult4086_Check3:
.a16
.i16
lda.l SourceNativeContinuation4086_Ready
cmp #$B612
beq SourceNativeResult4086_Check4
jmp SourceNativeResult4086_Bad
SourceNativeResult4086_Check4:
.a16
.i16
lda.l SourceNativeContinuation4086_State
cmp #2
beq SourceNativeResult4086_Check5
jmp SourceNativeResult4086_Bad
SourceNativeResult4086_Check5:
.a16
.i16
lda.l SourceFrameStack4086_Ready
cmp #$B4ED
beq SourceNativeResult4086_Check6
jmp SourceNativeResult4086_Bad
SourceNativeResult4086_Check6:
.a16
.i16
lda.l SourceAnimationCallback4086_Ready
cmp #$B4E6
beq SourceNativeResult4086_Check7
jmp SourceNativeResult4086_Bad
SourceNativeResult4086_Check7:
.a16
.i16
lda.l VmSourceCallback_Active
cmp #$B4A6
beq SourceNativeResult4086_Check8
jmp SourceNativeResult4086_Bad
SourceNativeResult4086_Check8:
.a16
.i16
lda.l SourceUpdateFrame4086_Pending
cmp #1
beq SourceNativeResult4086_Check9
jmp SourceNativeResult4086_Bad
SourceNativeResult4086_Check9:
.a16
.i16
lda.l VmSourceWorld_Ready
cmp #$B4A3
beq SourceNativeResult4086_Check10
jmp SourceNativeResult4086_Bad
SourceNativeResult4086_Check10:
.a16
.i16
lda.l SourceFrameStack4086_Fault
ora.l SourceNativeContinuation4086_Request
ora.l SourceVMRun4086_Busy
ora.l VmState_Budget
beq SourceNativeResult4086_Check11
jmp SourceNativeResult4086_Bad
SourceNativeResult4086_Check11:
.a16
.i16
lda.l VmState_Status
and #$00FF
cmp #VMSTAT_YIELDED
beq SourceNativeResult4086_Check12
jmp SourceNativeResult4086_Bad
SourceNativeResult4086_Check12:
.a16
.i16
lda.l SourceNativeContinuation4086_ResultSlot
cmp.l VmState_SlotCount
bcc SourceNativeResult4086_Check13
jmp SourceNativeResult4086_Bad
SourceNativeResult4086_Check13:
.a16
.i16
cmp #1024
bcc SourceNativeResult4086_Check14
jmp SourceNativeResult4086_Bad
SourceNativeResult4086_Check14:
.a16
.i16
asl a
asl a
asl a
sta $06
tax
lda.l VmSlots_Wram,x
ora.l VmSlots_Wram+2,x
beq SourceNativeResult4086_Check15
jmp SourceNativeResult4086_Bad
SourceNativeResult4086_Check15:
.a16
.i16
lda #0
sta $00
sta $02
lda $04
cmp #$FFFF
beq SourceNativeResult4086_Store
cmp.l VmSourceWorld_Count
bcc SourceNativeResult4086_Check16
jmp SourceNativeResult4086_Bad
SourceNativeResult4086_Check16:
.a16
.i16
cmp #128
bcc SourceNativeResult4086_Check17
jmp SourceNativeResult4086_Bad
SourceNativeResult4086_Check17:
.a16
.i16
asl a
asl a
asl a
asl a
sta $00
asl a
asl a
clc
adc $00
clc
adc #$4000
sta $00
lda #$0041
sta $02
ldx $00
lda.l $410000,x
cmp $00
beq SourceNativeResult4086_Check18
jmp SourceNativeResult4086_Bad
SourceNativeResult4086_Check18:
.a16
.i16
lda.l $410002,x
cmp $02
beq SourceNativeResult4086_Check19
jmp SourceNativeResult4086_Bad
SourceNativeResult4086_Check19:
.a16
.i16
SourceNativeResult4086_Store:
.a16
.i16
ldx $06
lda #BOR_VT_PTR
sta.l VmSlots_Wram,x
sta.l VmNativeVariant_Result
lda #0
sta.l VmSlots_Wram+2,x
sta.l VmNativeVariant_Result+2
lda $00
sta.l VmSlots_Wram+4,x
sta.l VmNativeVariant_Result+4
lda $02
sta.l VmSlots_Wram+6,x
sta.l VmNativeVariant_Result+6
tsc
clc
adc #8
tcs
pld
ply
plx
plb
pla
plp
clc
rtl
SourceNativeResult4086_Bad:
.a16
.i16
tsc
clc
adc #8
tcs
pld
ply
plx
plb
pla
plp
sec
rtl
