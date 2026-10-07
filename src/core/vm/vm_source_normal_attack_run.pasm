; Execute the ordered normal_attack owner with real selector bodies.
; Unsupported target/mutation branches propagate faults, never fake responses.
SourceNormalAttackRun4086_Ready = $43BDD0
SourceNormalAttackRun4086_Status = $43BDD2 ; 0 idle,1 busy,2 done,3 fault
SourceNormalAttackRun4086_End = $43BDD4
SourceNormalAttackRun4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceNormalAttackRun4086_Ready
 cmp #$B5F5
 beq SourceNormalAttackRun4086_Lease
 jmp SourceNormalAttackRun4086_Bad
SourceNormalAttackRun4086_Lease:
.a16
.i16
 lda.l SourceNormalAttackRun4086_Status
 beq SourceNormalAttackRun4086_Idle
 cmp #2
 beq SourceNormalAttackRun4086_Idle
 jmp SourceNormalAttackRun4086_Bad
SourceNormalAttackRun4086_Idle:
.a16
.i16
 lda #1
 sta.l SourceNormalAttackRun4086_Status
 jsl SourceNormalAttack4086_Begin
 bcc SourceNormalAttackRun4086_Loop
 jmp SourceNormalAttackRun4086_Bad
SourceNormalAttackRun4086_Loop:
.a16
.i16
 lda.l SourceNormalAttack4086_State
 cmp #7
 beq SourceNormalAttackRun4086_Done
 cmp #1
 beq SourceNormalAttackRun4086_Grab
 cmp #2
 beq SourceNormalAttackRun4086_Entry
 cmp #3
 beq SourceNormalAttackRun4086_Block
 cmp #4
 beq SourceNormalAttackRun4086_Entry
 cmp #5
 beq SourceNormalAttackRun4086_Normal
 cmp #6
 beq SourceNormalAttackRun4086_Entry
 jmp SourceNormalAttackRun4086_Bad
SourceNormalAttackRun4086_Grab:
.a16
.i16
 lda.l SourceTryGrab4086_Status
 jsr SourceNormalAttackRun4086_Reusable
 bcs SourceNormalAttackRun4086_Bad
 sta.l SourceTryGrab4086_Status
 jsl SourceTryGrab4086_Execute
 jmp SourceNormalAttackRun4086_Resume
SourceNormalAttackRun4086_Entry:
.a16
.i16
 lda.l SourceAttackEntry4086_Status
 jsr SourceNormalAttackRun4086_Reusable
 bcs SourceNormalAttackRun4086_Bad
 sta.l SourceAttackEntry4086_Status
 jsl SourceAttackEntry4086_Execute
 jmp SourceNormalAttackRun4086_Resume
SourceNormalAttackRun4086_Block:
.a16
.i16
 lda.l SourceTryBlock4086_Status
 jsr SourceNormalAttackRun4086_Reusable
 bcs SourceNormalAttackRun4086_Bad
 sta.l SourceTryBlock4086_Status
 jsl SourceTryBlock4086_Execute
 jmp SourceNormalAttackRun4086_Resume
SourceNormalAttackRun4086_Normal:
.a16
.i16
 lda.l SourceTryNormalAttack4086_Status
 jsr SourceNormalAttackRun4086_Reusable
 bcs SourceNormalAttackRun4086_Bad
 sta.l SourceTryNormalAttack4086_Status
 jsl SourceTryNormalAttack4086_Execute
SourceNormalAttackRun4086_Resume:
.a16
.i16
 bcs SourceNormalAttackRun4086_Bad
 lda.l SourceNormalAttack4086_State
 jsl SourceNormalAttack4086_Continue
 bcs SourceNormalAttackRun4086_Bad
 jmp SourceNormalAttackRun4086_Loop
SourceNormalAttackRun4086_Done:
.a16
.i16
 lda #2
 sta.l SourceNormalAttackRun4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceNormalAttackRun4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceNormalAttackRun4086_Status
 ply
 plx
 plp
 sec
 rtl
SourceNormalAttackRun4086_Reusable:
.a16
.i16
 cmp #0
 beq SourceNormalAttackRun4086_ReusableGood
 cmp #2
 bne SourceNormalAttackRun4086_ReusableBad
SourceNormalAttackRun4086_ReusableGood:
.a16
.i16
 lda #0
 clc
 rts
SourceNormalAttackRun4086_ReusableBad:
.a16
.i16
 sec
 rts
