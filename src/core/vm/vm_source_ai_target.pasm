; Direct common_think normal_find_target(-1,0), using actual owner/self state.
; Does not insert a self.exists test: source selector tails can query after
; retiring self. Candidate exists remains full32. No fabricated VM arguments.
; Reuse the checked target scan while preserving its typed VM result scratch.
SourceAITarget4086_Ready = $43BDC2
SourceAITarget4086_Status = $43BDC4 ; 0 idle,1 busy,2 complete,3 fault
SourceAITarget4086_Result = $43BDC6 ; entity token32, zero if none
SourceAITarget4086_Selected = $43BDCA ; physical slot or FFFF
SourceAITarget4086_End = $43BDCC
; Same source query from an actual check_ai ACTION callback. This entry does
; not borrow or manufacture a common_think phase. Its caller owns action ID.
SourceAITarget4086_ActionUnbounded:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceAITarget4086_Ready
 cmp #$B5F3
 beq SourceAITarget4086_ActionLease
 jmp SourceAITarget4086_Bad
SourceAITarget4086_ActionLease:
.a16
.i16
 lda.l SourceAITarget4086_Status
 beq SourceAITarget4086_ActionStart
 cmp #2
 beq SourceAITarget4086_ActionStart
 jmp SourceAITarget4086_Bad
SourceAITarget4086_ActionStart:
.a16
.i16
 lda #1
 sta.l SourceAITarget4086_Status
 lda.l SourceAI4086_State
 cmp #1
 beq SourceAITarget4086_ActionOwner
 jmp SourceAITarget4086_Bad
SourceAITarget4086_ActionOwner:
.a16
.i16
 jsl SourceAI4086_CheckOwner
 bcc SourceAITarget4086_ActionChecked
 jmp SourceAITarget4086_Bad
SourceAITarget4086_ActionChecked:
.a16
.i16
 jmp SourceAITarget4086_Owner
SourceAITarget4086_Unbounded:
.a16
.i16
 php
 rep #$38
 phx
 phy
 lda.l SourceAITarget4086_Ready
 cmp #$B5F3
 beq SourceAITarget4086_Lease
 jmp SourceAITarget4086_Bad
SourceAITarget4086_Lease:
.a16
.i16
 lda.l SourceAITarget4086_Status
 beq SourceAITarget4086_Idle
 cmp #2
 beq SourceAITarget4086_Idle
 jmp SourceAITarget4086_Bad
SourceAITarget4086_Idle:
.a16
.i16
 lda #1
 sta.l SourceAITarget4086_Status
 jsl SourceCommonThink4086_CheckOwner
 bcc SourceAITarget4086_Owner
 jmp SourceAITarget4086_Bad
SourceAITarget4086_Owner:
.a16
.i16
 lda.l VmSourceEntity_Ready
 cmp #$B5EF
 beq SourceAITarget4086_ViewReady
 jmp SourceAITarget4086_Bad
SourceAITarget4086_ViewReady:
.a16
.i16
 lda.l VmSourceEntity_Base
 cmp #$4000
 beq SourceAITarget4086_ViewBase
 jmp SourceAITarget4086_Bad
SourceAITarget4086_ViewBase:
.a16
.i16
 lda.l VmSourceEntity_Bank
 and #$00FF
 cmp #$41
 beq SourceAITarget4086_ViewBank
 jmp SourceAITarget4086_Bad
SourceAITarget4086_ViewBank:
.a16
.i16
 lda.l VmSourceEntity_Count
 cmp.l VmSourceWorld_Count
 beq SourceAITarget4086_ViewCount
 jmp SourceAITarget4086_Bad
SourceAITarget4086_ViewCount:
.a16
.i16
 ; The builder deliberately skips inactive rows. Validate self coordinates
 ; independently, then load self's actual core/modeldata even if retired.
 lda.l SourceAI4086_View
 tax
 lda.l $410030,x
 cmp #BOR_VT_DECIMAL
 beq SourceAITarget4086_XTag
 jmp SourceAITarget4086_Bad
SourceAITarget4086_XTag:
.a16
.i16
 lda.l $410032,x
 beq SourceAITarget4086_XReserved
 jmp SourceAITarget4086_Bad
SourceAITarget4086_XReserved:
.a16
.i16
 lda.l $410038,x
 cmp #BOR_VT_DECIMAL
 beq SourceAITarget4086_ZTag
 jmp SourceAITarget4086_Bad
SourceAITarget4086_ZTag:
.a16
.i16
 lda.l $41003A,x
 beq SourceAITarget4086_ZReserved
 jmp SourceAITarget4086_Bad
SourceAITarget4086_ZReserved:
.a16
.i16
 lda.l $410018,x
 cmp #BOR_VT_INTEGER
 beq SourceAITarget4086_DTag
 jmp SourceAITarget4086_Bad
SourceAITarget4086_DTag:
.a16
.i16
 lda.l $41001A,x
 beq SourceAITarget4086_Build
 jmp SourceAITarget4086_Bad
SourceAITarget4086_Build:
.a16
.i16
 jsl SourceTargetMeta4086_Build
 bcc SourceAITarget4086_Self
 jmp SourceAITarget4086_Bad
SourceAITarget4086_Self:
.a16
.i16
 lda.l SourceAI4086_Slot
 sta.l SourceTarget4086_SelfIndex
 asl a
 asl a
 asl a
 asl a
 asl a
 pha
 asl a
 clc
 adc 1,s
 tax
 pla
 lda.l $40C028,x
 sta.l SourceTarget4086_Hostile
 lda.l SourceAI4086_Slot
 asl a
 asl a
 asl a
 pha
 asl a
 clc
 adc 1,s
 tax
 pla
 lda.l SOURCE_ENTITY_AI_STATE+16,x
 sta.l SourceTarget4086_DetectLo
 lda.l SOURCE_ENTITY_AI_STATE+18,x
 sta.l SourceTarget4086_DetectHi
 lda.l SourceAI4086_View
 tax
 lda.l $410034,x
 sta.l SourceTarget4086_SelfXLo
 lda.l $410036,x
 sta.l SourceTarget4086_SelfXHi
 lda.l $41003C,x
 sta.l SourceTarget4086_SelfZLo
 lda.l $41003E,x
 sta.l SourceTarget4086_SelfZHi
 lda #0
 sta.l SourceTarget4086_Direction
 lda.l $41001E,x
 bne SourceAITarget4086_Scan
 lda.l $41001C,x
 cmp #1
 bne SourceAITarget4086_Scan
 sta.l SourceTarget4086_Direction
SourceAITarget4086_Scan:
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
 jsl Vm_SourceFindTarget_Begin
 bcs SourceAITarget4086_RestoreBad
 lda.l VmNativeVariant_Result+4
 sta.l SourceAITarget4086_Result
 lda.l VmNativeVariant_Result+6
 sta.l SourceAITarget4086_Result+2
 lda.l SourceTarget4086_Selected
 sta.l SourceAITarget4086_Selected
 pla
 sta.l VmNativeVariant_Result+6
 pla
 sta.l VmNativeVariant_Result+4
 pla
 sta.l VmNativeVariant_Result+2
 pla
 sta.l VmNativeVariant_Result
 lda #2
 sta.l SourceAITarget4086_Status
 ply
 plx
 plp
 clc
 rtl
SourceAITarget4086_RestoreBad:
.a16
.i16
 pla
 sta.l VmNativeVariant_Result+6
 pla
 sta.l VmNativeVariant_Result+4
 pla
 sta.l VmNativeVariant_Result+2
 pla
 sta.l VmNativeVariant_Result
SourceAITarget4086_Bad:
.a16
.i16
 lda #3
 sta.l SourceAITarget4086_Status
 ply
 plx
 plp
 sec
 rtl
