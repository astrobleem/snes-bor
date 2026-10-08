SourcePostStationary4086_Ready = $40BFF8
SourcePostStationary4086_Status = $40BFFA
SourcePostStationary4086_Slot = $40BFFC
; Closed stationary/no-binding post-update capability.
; Caller supplies B618/B619 gravity and B617 movement leases. No callbacks/yields.
; Saves the arranger's retained self, binds explicit e, runs gravity then move,
; and restores self on both success and failure. No full POST Ack is performed.
SourcePostStationary4086_Execute:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourcePostStationary4086_Ready
 cmp #$B61A
 beq SourcePostStationary4086_LeaseReady
 jmp SourcePostStationary4086_Bad
SourcePostStationary4086_LeaseReady:
.a16
.i16
 lda.l SourcePostStationary4086_Status
 beq SourcePostStationary4086_LeaseIdle
 jmp SourcePostStationary4086_Bad
SourcePostStationary4086_LeaseIdle:
.a16
.i16
 lda.l SourcePostStationary4086_Slot
 cmp.l SourceWorldTick4086_Slot
 beq SourcePostStationary4086_LeaseSlot
 jmp SourcePostStationary4086_Bad
SourcePostStationary4086_LeaseSlot:
.a16
.i16
 lda.l SourceWorldTick4086_State
 cmp #2
 beq SourcePostStationary4086_StateGood
 jmp SourcePostStationary4086_Bad
SourcePostStationary4086_StateGood:
.a16
.i16
 lda.l SourceWorldTick4086_Phase
 cmp #11
 beq SourcePostStationary4086_PhaseGood
 jmp SourcePostStationary4086_Bad
SourcePostStationary4086_PhaseGood:
.a16
.i16
 lda.l SourceSelf4086_Ready
 cmp #$B4F6
 beq SourcePostStationary4086_SelfGood
 jmp SourcePostStationary4086_Bad
SourcePostStationary4086_SelfGood:
.a16
.i16
 lda.l SourceSelf4086_Active
 ora.l SourceSelf4086_Fault
 beq SourcePostStationary4086_IdleGood
 jmp SourcePostStationary4086_Bad
SourcePostStationary4086_IdleGood:
.a16
.i16
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 beq SourcePostStationary4086_WorldGood
 jmp SourcePostStationary4086_Bad
SourcePostStationary4086_WorldGood:
.a16
.i16
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 beq SourcePostStationary4086_PoolGood
 jmp SourcePostStationary4086_Bad
SourcePostStationary4086_PoolGood:
.a16
.i16
 lda.l VmSourceWorld_Count
 bne SourcePostStationary4086_Guard0
 jmp SourcePostStationary4086_Bad
SourcePostStationary4086_Guard0:
.a16
.i16
 cmp #129
 bcc SourcePostStationary4086_Guard1
 jmp SourcePostStationary4086_Bad
SourcePostStationary4086_Guard1:
.a16
.i16
 lda.l SourceWorldTick4086_Slot
 cmp.l VmSourceWorld_Count
 bcc SourcePostStationary4086_Guard2
 jmp SourcePostStationary4086_Bad
SourcePostStationary4086_Guard2:
.a16
.i16
 lda.l SourceSelf4086_GlobalHigh
 cmp #$41
 beq SourcePostStationary4086_Mapped
 ora.l SourceSelf4086_GlobalLow
 beq SourcePostStationary4086_Bind
 jmp SourcePostStationary4086_Bad
SourcePostStationary4086_Mapped:
.a16
.i16
 lda.l SourceSelf4086_GlobalLow
 cmp #$4000
 bcs SourcePostStationary4086_Guard3
 jmp SourcePostStationary4086_Bad
SourcePostStationary4086_Guard3:
.a16
.i16
 cmp #$6800
 bcc SourcePostStationary4086_Guard4
 jmp SourcePostStationary4086_Bad
SourcePostStationary4086_Guard4:
.a16
.i16
 sec
 sbc #$4000
 ldx #0
SourcePostStationary4086_ValidateSlot:
.a16
.i16
 cmp #80
 bcc SourcePostStationary4086_ValidateRemainder
 sec
 sbc #80
 inx
 bra SourcePostStationary4086_ValidateSlot
SourcePostStationary4086_ValidateRemainder:
.a16
.i16
 cmp #0
 beq SourcePostStationary4086_Guard5
 jmp SourcePostStationary4086_Bad
SourcePostStationary4086_Guard5:
.a16
.i16
 txa
 cmp.l VmSourceWorld_Count
 bcc SourcePostStationary4086_Guard6
 jmp SourcePostStationary4086_Bad
SourcePostStationary4086_Guard6:
.a16
.i16
SourcePostStationary4086_Bind:
.a16
.i16
 lda.l SourceGravityIdle4086_Status
 cmp #0
 beq SourcePostStationary4086_SourceGravityIdle4086Ready
 cmp #2
 beq SourcePostStationary4086_SourceGravityIdle4086Ready
 jmp SourcePostStationary4086_Bad
SourcePostStationary4086_SourceGravityIdle4086Ready:
.a16
.i16
 lda.l SourceCheckMove4086_Status
 cmp #0
 beq SourcePostStationary4086_SourceCheckMove4086Ready
 cmp #2
 beq SourcePostStationary4086_SourceCheckMove4086Ready
 jmp SourcePostStationary4086_Bad
SourcePostStationary4086_SourceCheckMove4086Ready:
.a16
.i16
 lda #0
 sta.l SourceGravityIdle4086_Status
 sta.l SourceCheckMove4086_Status
 lda.l SourceSelf4086_GlobalHigh
 pha
 lda.l SourceSelf4086_GlobalLow
 pha
 lda.l SourceWorldTick4086_Slot
 asl a
 asl a
 asl a
 asl a
 tax
 asl a
 asl a
 sta.l SourceSelf4086_GlobalLow
 txa
 clc
 adc.l SourceSelf4086_GlobalLow
 clc
 adc #$4000
 sta.l SourceSelf4086_GlobalLow
 lda #$41
 sta.l SourceSelf4086_GlobalHigh
 jsl SourceAdjustBaseEmpty4086_RunPost
 bcs SourcePostStationary4086_RestoreBad
 jsl SourceGravityIdle4086_Execute
 bcs SourcePostStationary4086_RestoreBad
 jsl SourceCheckMove4086_Execute
 bcs SourcePostStationary4086_RestoreBad
 pla
 sta.l SourceSelf4086_GlobalLow
 pla
 sta.l SourceSelf4086_GlobalHigh
 lda #2
 sta.l SourcePostStationary4086_Status
 ply
 plx
 plp
 clc
 rtl
SourcePostStationary4086_RestoreBad:
.a16
.i16
 pla
 sta.l SourceSelf4086_GlobalLow
 pla
 sta.l SourceSelf4086_GlobalHigh
SourcePostStationary4086_Bad:
.a16
.i16
 lda #3
 sta.l SourcePostStationary4086_Status
 ply
 plx
 plp
 sec
 rtl

; A=service to issue, preserved. Disabled capability leaves static paths alone.
SourcePostStationary4086_Issue:
.a16
.i16
 php
 rep #$38
 pha
 cmp #11
 bne SourcePostStationary4086_ControlGood
 lda.l SourcePostStationary4086_Ready
 beq SourcePostStationary4086_ControlGood
 cmp #$B61A
 bne SourcePostStationary4086_ControlBad
 lda.l SourcePostStationary4086_Status
 cmp #0
 beq SourcePostStationary4086_IssueValid
 cmp #2
 bne SourcePostStationary4086_ControlBad
SourcePostStationary4086_IssueValid:
.a16
.i16
 lda.l SourceWorldTick4086_Slot
 sta.l SourcePostStationary4086_Slot
 lda #0
 sta.l SourcePostStationary4086_Status
 bra SourcePostStationary4086_ControlGood
SourcePostStationary4086_CheckAck:
.a16
.i16
 php
 rep #$38
 pha
 lda.l SourceWorldTick4086_Phase
 cmp #11
 bne SourcePostStationary4086_ControlGood
 lda.l SourcePostStationary4086_Ready
 beq SourcePostStationary4086_ControlGood
 cmp #$B61A
 bne SourcePostStationary4086_ControlBad
 lda.l SourcePostStationary4086_Status
 cmp #2
 bne SourcePostStationary4086_ControlBad
 lda.l SourcePostStationary4086_Slot
 cmp.l SourceWorldTick4086_Slot
 bne SourcePostStationary4086_ControlBad
 lda.l SourceGravityIdle4086_Status
 cmp #2
 bne SourcePostStationary4086_ControlBad
 lda.l SourceCheckMove4086_Status
 cmp #2
 bne SourcePostStationary4086_ControlBad
SourcePostStationary4086_ControlGood:
.a16
.i16
 pla
 plp
 clc
 rtl
SourcePostStationary4086_ControlBad:
.a16
.i16
 pla
 plp
 sec
 rtl
