"""Native check_costmove over the real source entity stores.

An exclusive caller lease supplies controls and the missing combostep[1..4]
array. No production allocation is implied. Begin executes the actual native
animation initializer; pending frame-zero work is returned, never auto-acked.
"""
import re


def emit(work,combo_tail,symbols):
    if not 0<=work<=0xffffff-64 or not 0<=combo_tail<=0xffffff-2048:
        raise ValueError('COSTMOVE_NATIVE_EXTENT')
    if work<combo_tail+2048 and combo_tail<work+64:raise ValueError('COSTMOVE_NATIVE_OVERLAP')
    code='''
SourceCostMove_Begin:
.a16
.i16
 php
 rep #$39
 pha
 phx
 phy
 lda.l W
 cmp #$B670
 beq SourceCostMove_Lease
 jmp SourceCostMove_Fault
SourceCostMove_Lease:
.a16
.i16
 lda.l W+2
 beq SourceCostMove_Start
 cmp #2
 beq SourceCostMove_Start
 cmp #4
 beq SourceCostMove_Start
 jmp SourceCostMove_Fault
SourceCostMove_Start:
.a16
.i16
 lda #1
 sta.l W+2
 ; FS is a signed source int32. Only exact zero/one qualify.
 lda.l W+10
 beq SourceCostMove_FSLo
 jmp SourceCostMove_False
SourceCostMove_FSLo:
.a16
.i16
 lda.l W+8
 beq SourceCostMove_FSZero
 cmp #1
 beq SourceCostMove_FSOne
 jmp SourceCostMove_False
SourceCostMove_FSZero:
.a16
.i16
 lda.l W+18
 ora.l W+16
 beq SourceCostMove_Resolve
 lda.l W+18
 bne SourceCostMove_FalseNear
 lda.l W+16
 cmp #3
 beq SourceCostMove_Resolve
SourceCostMove_FalseNear:
.a16
.i16
 jmp SourceCostMove_False
SourceCostMove_FSOne:
.a16
.i16
 lda.l W+18
 bmi SourceCostMove_Resolve
 bne SourceCostMove_FalseNear
 lda.l W+16
 cmp #2
 bcs SourceCostMove_FalseNear
SourceCostMove_Resolve:
.a16
.i16
 lda.l W+4
 sta.l SourceAnimationInit4086_Slot
 lda.l W+6
 sta.l SourceAnimationInit4086_Number
 lda #0
 sta.l SourceAnimationInit4086_Reset
 jsl SourceAnimationInit4086_Resolve
 bcc SourceCostMove_Resolved
 jmp SourceCostMove_Fault
SourceCostMove_Resolved:
.a16
.i16
 lda.l SourceAnimationInit4086_Handle
 beq SourceCostMove_FalseNear
 lda.l SourceAnimationInit4086_Count
 beq SourceCostMove_FalseNear
 lda.l W+4
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l W+30 ; flags offset
 asl a
 sta.l W+50 ; relation offset
 clc
 adc.l W+30
 sta.l W+28 ; core offset
 lda.l W+4
 asl a
 asl a
 sta.l W+34
 asl a
 asl a
 clc
 adc.l W+34
 sta.l W+34 ; combat offset
 asl a
 asl a
 sta.l W+32 ; view offset, 80*slot
 lda.l W+34
 tax
 lda.l $437E10,x
 cmp #$B5FB
 beq SourceCostMove_CombatMarker
 jmp SourceCostMove_Fault
SourceCostMove_CombatMarker:
.a16
.i16
 lda.l $437E12,x
 beq SourceCostMove_CaptureSeal
 jmp SourceCostMove_Fault
SourceCostMove_CaptureSeal:
.a16
.i16
 lda.l $437E04,x
 sta.l SourceCheckEnergy4086_Seal
 lda.l $437E06,x
 sta.l SourceCheckEnergy4086_Seal+2
 lda.l W+28
 tax
 lda.l $40C048,x
 sta.l SourceCheckEnergy4086_Type
 lda.l $40C04A,x
 sta.l SourceCheckEnergy4086_Type+2
 lda.l $40C04C,x
 sta.l SourceCheckEnergy4086_MP
 lda.l $40C04E,x
 sta.l SourceCheckEnergy4086_MP+2
 lda.l W+32
 tax
 lda.l $414020,x
 cmp #1
 beq SourceCostMove_HealthReserved
 jmp SourceCostMove_Fault
SourceCostMove_HealthReserved:
.a16
.i16
 lda.l $414022,x
 beq SourceCostMove_CaptureHealth
 jmp SourceCostMove_Fault
SourceCostMove_CaptureHealth:
.a16
.i16
 lda.l $414024,x
 sta.l SourceCheckEnergy4086_Health
 lda.l $414026,x
 sta.l SourceCheckEnergy4086_Health+2
 lda.l SourceAnimationInit4086_Handle
 jsl SourceAnimationEnergy4086_Query
 bcc SourceCostMove_EnergyFields
 jmp SourceCostMove_Fault
SourceCostMove_EnergyFields:
.a16
.i16
 lda #1
 sta.l SourceCheckEnergy4086_Present
 lda #0
 sta.l SourceCheckEnergy4086_Present+2
 sta.l SourceCheckEnergy4086_Which
 sta.l SourceCheckEnergy4086_Which+2
 jsl SourceCheckEnergy4086_Execute
 bcc SourceCostMove_HPResult
 jmp SourceCostMove_Fault
SourceCostMove_HPResult:
.a16
.i16
 lda.l SourceCheckEnergy4086_Result
 ora.l SourceCheckEnergy4086_Result+2
 bne SourceCostMove_Eligible
 jsr SourceCostMove_MP
 bcc SourceCostMove_MPResult
 jmp SourceCostMove_Fault
SourceCostMove_MPResult:
.a16
.i16
 lda.l SourceCheckEnergy4086_Result
 ora.l SourceCheckEnergy4086_Result+2
 bne SourceCostMove_Eligible
 jmp SourceCostMove_False
SourceCostMove_Eligible:
.a16
.i16
 lda #2 ; no resource debit
 sta.l W+46
 lda.l W+20
 ora.l W+22
 ora.l W+24
 ora.l W+26
 bne SourceCostMove_PreflightLink
 jsr SourceCostMove_MP
 bcc SourceCostMove_DebitKind
 jmp SourceCostMove_Fault
SourceCostMove_DebitKind:
.a16
.i16
 lda.l SourceCheckEnergy4086_Result
 ora.l SourceCheckEnergy4086_Result+2
 beq SourceCostMove_DebitHP
 lda #1
 sta.l W+46
 lda.l SourceCheckEnergy4086_MP
 ldx.l SourceCheckEnergy4086_MP+2
 bra SourceCostMove_Subtract
SourceCostMove_DebitHP:
.a16
.i16
 lda #0
 sta.l W+46
 lda.l SourceCheckEnergy4086_Health
 ldx.l SourceCheckEnergy4086_Health+2
SourceCostMove_Subtract:
.a16
.i16
 sec
 sbc.l SourceCheckEnergy4086_Cost
 sta.l W+52
 txa
 sbc.l SourceCheckEnergy4086_Cost+2
 bvc SourceCostMove_Subtracted
 jmp SourceCostMove_Fault
SourceCostMove_Subtracted:
.a16
.i16
 sta.l W+54
SourceCostMove_PreflightLink:
.a16
.i16
 lda.l W+50
 tax
 lda.l $40901C,x
 sta.l SourceRetirement4086_ArgLo
 lda.l $40901E,x
 sta.l SourceRetirement4086_ArgHi
 jsl SourceRetirement4086_ResolvePointer
 bcc SourceCostMove_LinkResolved
 jmp SourceCostMove_Fault
SourceCostMove_LinkResolved:
.a16
.i16
 sta.l W+48
 lda.l W+12
 ora.l W+14
 bne SourceCostMove_Debit
 lda.l W+4
 asl a
 asl a
 asl a
 asl a
 sta.l W+56
 asl a
 asl a
 clc
 adc.l W+56
 tax ; lifecycle row, 80*slot
 lda #17
 sta.l $43900C,x
 lda #0
 sta.l $43900E,x
SourceCostMove_Debit:
.a16
.i16
 lda.l W+46
 cmp #2
 beq SourceCostMove_Flags
 cmp #1
 beq SourceCostMove_PayMP
 lda.l W+32
 tax
 lda.l W+52
 sta.l $414024,x
 lda.l W+54
 sta.l $414026,x
 bra SourceCostMove_Flags
SourceCostMove_PayMP:
.a16
.i16
 lda.l W+28
 tax
 lda.l W+52
 sta.l $40C04C,x
 lda.l W+54
 sta.l $40C04E,x
SourceCostMove_Flags:
.a16
.i16
 lda.l W+28
 tax
 lda #1
 sta.l $40C058,x
 lda #0
 sta.l $40C05A,x
 lda.l W+30
 tax
 lda #0
 sta.l $43EB00,x
 sta.l $43EB02,x
 sta.l $43EB04,x
 sta.l $43EB06,x
 lda.l W+34
 tax
 lda #0
 sta.l $437E08,x
 sta.l $437E0A,x
 lda.l W+4
 asl a
 asl a
 asl a
 asl a
 tax
 lda #0
 sta.l C,x
 sta.l C+2,x
 sta.l C+4,x
 sta.l C+6,x
 sta.l C+8,x
 sta.l C+10,x
 sta.l C+12,x
 sta.l C+14,x
 lda.l W+50
 tax ; canonical side velocity; auxiliary movex/movez are frame deltas
 lda #0
 sta.l $416824,x
 sta.l $416826,x
 sta.l $416828,x
 sta.l $41682A,x
 lda.l W+48
 cmp #$FFFF
 beq SourceCostMove_UnlinkSelf
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l W+56
 asl a
 tax
 lda #0
 sta.l $40901C,x
 sta.l $40901E,x
 txa
 clc
 adc.l W+56
 tax
 lda #0
 sta.l $40C050,x
 sta.l $40C052,x
SourceCostMove_UnlinkSelf:
.a16
.i16
 lda.l W+50
 tax
 lda #0
 sta.l $40901C,x
 sta.l $40901E,x
 lda.l W+28
 tax
 lda #0
 sta.l $40C050,x
 sta.l $40C052,x
SourceCostMove_BeforeAnimation:
.a16
.i16
 nop
 jsl SourceAnimationInit4086_Begin
 bcc SourceCostMove_AnimationState
 jmp SourceCostMove_Fault
SourceCostMove_AnimationState:
.a16
.i16
 lda.l SourceAnimationInit4086_State
 cmp #1
 beq SourceCostMove_FramePending
 cmp #2
 beq SourceCostMove_Complete
 jmp SourceCostMove_Fault
SourceCostMove_FramePending:
.a16
.i16
 lda #3
 sta.l W+2
 jmp SourceCostMove_Return
SourceCostMove_Complete:
.a16
.i16
 lda #4
 sta.l W+2
 jmp SourceCostMove_Return
SourceCostMove_False:
.a16
.i16
 lda #2
 sta.l W+2
SourceCostMove_Return:
.a16
.i16
 ply
 plx
 pla
 plp
 clc
 rtl
SourceCostMove_Fault:
.a16
.i16
 lda #5
 sta.l W+2
 ply
 plx
 pla
 plp
 sec
 rtl
SourceCostMove_MP:
.a16
.i16
 lda #1
 sta.l SourceCheckEnergy4086_Which
 lda #0
 sta.l SourceCheckEnergy4086_Which+2
 jsl SourceCheckEnergy4086_Execute
 rts
'''
    code+='''
; Complete only after the actual native frame-zero owner and animation Ack.
SourceCostMove_Finish:
.a16
.i16
 php
 rep #$39
 pha
 phx
 phy
 lda.l W
 cmp #$B670
 beq SourceCostMove_FinishState
 jmp SourceCostMove_Fault
SourceCostMove_FinishState:
.a16
.i16
 lda.l W+2
 cmp #3
 beq SourceCostMove_FinishAnimation
 jmp SourceCostMove_Fault
SourceCostMove_FinishAnimation:
.a16
.i16
 lda.l SourceAnimationInit4086_Ready
 cmp #$B4EC
 beq SourceCostMove_FinishComplete
 jmp SourceCostMove_Fault
SourceCostMove_FinishComplete:
.a16
.i16
 lda.l SourceAnimationInit4086_State
 cmp #2
 beq SourceCostMove_FinishSlot
 jmp SourceCostMove_Fault
SourceCostMove_FinishSlot:
.a16
.i16
 lda.l SourceAnimationInit4086_Slot
 cmp.l W+4
 beq SourceCostMove_FinishRole
 jmp SourceCostMove_Fault
SourceCostMove_FinishRole:
.a16
.i16
 lda.l SourceAnimationInit4086_Number
 cmp.l W+6
 bne SourceCostMove_FinishBadRole
 jmp SourceCostMove_Complete
SourceCostMove_FinishBadRole:
.a16
.i16
 jmp SourceCostMove_Fault
'''
    # 65816 has no LDX absolute-long; use the stack for high-half subtraction.
    code=code.replace(' ldx.l SourceCheckEnergy4086_MP+2',' pha\n lda.l SourceCheckEnergy4086_MP+2\n tax\n pla').replace(' ldx.l SourceCheckEnergy4086_Health+2',' pha\n lda.l SourceCheckEnergy4086_Health+2\n tax\n pla')
    values=dict(W=work,C=combo_tail)
    for name in set(re.findall(r'\bSource(?:AnimationInit4086|AnimationEnergy4086|CheckEnergy4086|Retirement4086)_[A-Za-z0-9_]+\b',code)):
        values[name]=symbols[name]
    for name,value in values.items():code=re.sub(r'\b'+name+r'\b',str(value),code)
    return code


def emit_combo_energy_query(work,symbols):
    """Pure current-entity validanim/MP-first energy query for combo selection.

    Uses the exact same canonical field reads and table validation as costmove.
    A=0 absent/ineligible, A=1 eligible, carry=1 invalid owner/entity/table.
    No actor or resource mutation; animation and numeric query controls change.
    The caller must serialize it with real animation/costmove continuations.
    """
    template=emit(work,work+64,symbols)
    # Extract the shared Resolve/canonical-field capture before any mutation.
    start=template.index('SourceCostMove_Resolve:')
    end=template.index('SourceCostMove_EnergyFields:')
    capture=template[start:end].replace('SourceCostMove_','SourceComboEnergy_')
    code='''
SourceComboEnergy_Query:
.a16
.i16
 php
 rep #$39
 phx
 phy
 lda.l WORK
 cmp #$B670
 beq SourceComboEnergy_Lease
 jmp SourceComboEnergy_Fault
SourceComboEnergy_Lease:
.a16
.i16
 lda.l WORK+2
 beq SourceComboEnergy_Resolve
 cmp #2
 beq SourceComboEnergy_Resolve
 cmp #4
 beq SourceComboEnergy_Resolve
 jmp SourceComboEnergy_Fault
'''+capture+'''
SourceComboEnergy_EnergyFields:
.a16
.i16
 lda #1
 sta.l PRESENT
 sta.l WHICH
 lda #0
 sta.l PRESENT+2
 sta.l WHICH+2
 jsl EXECUTE
 bcc SourceComboEnergy_MPResult
 jmp SourceComboEnergy_Fault
SourceComboEnergy_MPResult:
.a16
.i16
 lda.l RESULT
 ora.l RESULT+2
 bne SourceComboEnergy_True
 lda #0
 sta.l WHICH
 jsl EXECUTE
 bcc SourceComboEnergy_HPResult
 jmp SourceComboEnergy_Fault
SourceComboEnergy_HPResult:
.a16
.i16
 lda.l RESULT
 ora.l RESULT+2
 bne SourceComboEnergy_True
SourceComboEnergy_FalseNear:
.a16
.i16
 lda #0
 bra SourceComboEnergy_Return
SourceComboEnergy_True:
.a16
.i16
 lda #1
SourceComboEnergy_Return:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
SourceComboEnergy_Fault:
.a16
.i16
 lda #0
 ply
 plx
 plp
 sec
 rtl
'''
    values=dict(WORK=work,PRESENT=symbols['SourceCheckEnergy4086_Present'],
        WHICH=symbols['SourceCheckEnergy4086_Which'],RESULT=symbols['SourceCheckEnergy4086_Result'],
        EXECUTE=symbols['SourceCheckEnergy4086_Execute'])
    for n,v in values.items():code=re.sub(r'\b'+n+r'\b',str(v),code)
    # The capture's early absent-animation branch must span the energy query.
    code=re.sub(r'^ (beq|bcc) SourceComboEnergy_FalseNear$',
        lambda m:' '+dict(beq='bne',bcc='bcs')[m[1]]+' SourceComboEnergy_Absent_'+str(m.start())+'\n jmp SourceComboEnergy_FalseNear\nSourceComboEnergy_Absent_'+str(m.start())+':\n.a16\n.i16',code,flags=re.M)
    return code
