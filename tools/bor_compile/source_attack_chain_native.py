"""Native attack-chain continuation with explicit target and frame services.

The caller leases 96 control bytes and 128 signed combostyle rows. TargetPending
requires the real normal_find_target owner; no result is invented here. The
existing immutable B4BC owner validates current source chain geometry. Scripts
which mutate chain geometry remain outside that owner's admitted capability.
"""
import re


def emit(work, styles, attacks, symbols):
    for a, size in ((work, 96), (styles, 512)):
        if not 0 <= a <= 0x1000000-size:
            raise ValueError('ATTACK_CHAIN_NATIVE_EXTENT')
    if work < styles+512 and styles < work+96:
        raise ValueError('ATTACK_CHAIN_NATIVE_OVERLAP')
    if not 1 <= len(attacks) <= 7 or any(not 0 <= a <= 65535 for a in attacks):
        raise ValueError('ATTACK_CHAIN_NATIVE_ATTACK_DIRECTORY')
    code = '''
SourceAttackChain_Begin:
 php
 rep #$39
 phx
 phy
 lda.l W
 cmp #$B675
 bne SourceAttackChain_Fault
 lda.l W+2
 beq SourceAttackChain_BeginIdle
 cmp #2
 beq SourceAttackChain_BeginIdle
 cmp #5
 bne SourceAttackChain_Fault
SourceAttackChain_BeginIdle:
 lda #1
 sta.l W+2
 lda #0
 sta.l W+10
 jsl SourceAttackChain_ReadBody
 bcs SourceAttackChain_Fault
 lda.l W+46
 beq SourceAttackChain_False
 lda.l W+4
 asl a
 asl a
 sta.l W+22
 asl a
 asl a
 clc
 adc.l W+22
 sta.l W+22
 asl a
 asl a
 sta.l W+26
 lda.l W+4
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l W+24
 asl a
 sta.l W+30
 clc
 adc.l W+24
 sta.l W+20
 tax
 lda.l $40C048,x
 sta.l W+32
 lda.l $40C04A,x
 sta.l W+34
 lda.l W+26
 tax
 lda.l $43904A,x
 cmp #$B4FB
 bne SourceAttackChain_Fault
 lda.l W+22
 tax
 lda.l $437E10,x
 cmp #$B5FB
 bne SourceAttackChain_Fault
 lda.l $437E12,x
 bne SourceAttackChain_Fault
 lda.l $437E0E,x
 cmp.l SourceClock4086_TimeHi
 bcc SourceAttackChain_ResetStep
 bne SourceAttackChain_Increment
 lda.l $437E0C,x
 cmp.l SourceClock4086_TimeLo
 bcc SourceAttackChain_ResetStep
 beq SourceAttackChain_ResetStep
SourceAttackChain_Increment:
 lda.l $437E0A,x
 cmp #$7FFF
 bne SourceAttackChain_IncrementOK
 lda.l $437E08,x
 cmp #$FFFF
 beq SourceAttackChain_Fault
SourceAttackChain_IncrementOK:
 lda.l $437E0A,x
 bne SourceAttackChain_Fault
 lda.l $437E08,x
 cmp #12
 bcs SourceAttackChain_Fault
 asl a
 tax
 lda.l W+64,x
 bne SourceAttackChain_CandidateOK
 lda.l W+64
 beq SourceAttackChain_Fault
SourceAttackChain_CandidateOK:
 lda.l W+22
 tax
 lda.l $437E08,x
 clc
 adc #1
 sta.l $437E08,x
 lda.l $437E0A,x
 adc #0
 sta.l $437E0A,x
 bra SourceAttackChain_CheckEnd
SourceAttackChain_ResetStep:
 lda.l W+64
 beq SourceAttackChain_Fault
 lda #1
 sta.l $437E08,x
 lda #0
 sta.l $437E0A,x
SourceAttackChain_CheckEnd:
 jsl SourceAttackChain_Entry
 bcs SourceAttackChain_Fault
 bne SourceAttackChain_InitialValid
 lda.l W+22
 tax
 lda #1
 sta.l $437E08,x
SourceAttackChain_InitialValid:
 jsl SourceAttackChain_Valid
 bcs SourceAttackChain_Fault
 beq SourceAttackChain_NoPick
 lda.l W+36
 and #1
 bne SourceAttackChain_Ranged
 lda.l W+32
 and #1
 bne SourceAttackChain_Pick
 lda.l W+64
 jsl SourceAttackChain_Role
 bcs SourceAttackChain_Fault
 lda #0
 sta.l W+12
 bra SourceAttackChain_TargetPending
SourceAttackChain_Ranged:
 lda.l W+32
 and #1
 beq SourceAttackChain_RangeTarget
 lda.l W+22
 tax
 lda.l $437E08,x
 cmp #1
 beq SourceAttackChain_Pick
SourceAttackChain_RangeTarget:
 lda #1
 sta.l W+12
SourceAttackChain_TargetPending:
 lda.l W+6
 sta.l W+50
 lda #0
 sta.l W+14
 sta.l W+16
 sta.l W+18
 lda #3
 sta.l W+2
 lda #$8001
 bra SourceAttackChain_Return
SourceAttackChain_TargetResume:
 php
 rep #$39
 phx
 phy
 lda.l W
 cmp #$B675
 bne SourceAttackChain_Fault
 lda.l W+2
 cmp #3
 bne SourceAttackChain_Fault
 lda.l W+18
 cmp #$B676
 bne SourceAttackChain_Fault
 lda.l W+52
 cmp.l W+4
 bne SourceAttackChain_Fault
 lda.l W+54
 cmp.l W+50
 bne SourceAttackChain_Fault
 lda #0
 sta.l W+18
 lda.l W+14
 ora.l W+16
 bne SourceAttackChain_PickAfterTarget
 lda.l W+12
 beq SourceAttackChain_NoPick
 lda.l W+22
 tax
 lda.l $437E08,x
 cmp #1
 beq SourceAttackChain_NoPick
SourceAttackChain_Search:
 lda.l W+22
 tax
 lda.l $437E08,x
 inc a
 sta.l $437E08,x
 cmp.l W+46
 bcc SourceAttackChain_SearchEntry
 beq SourceAttackChain_SearchEntry
 bra SourceAttackChain_NoPick
SourceAttackChain_SearchEntry:
 jsl SourceAttackChain_Entry
 bcs SourceAttackChain_Fault
 beq SourceAttackChain_Search
 jsl SourceAttackChain_Valid
 bcs SourceAttackChain_Fault
 beq SourceAttackChain_Search
 lda.l W+22
 tax
 lda.l $437E08,x
 cmp.l W+46
 beq SourceAttackChain_Pick
 lda #1
 sta.l W+12
 bra SourceAttackChain_TargetPending
SourceAttackChain_PickAfterTarget:
 ; A normal-chain query used attack one for range, not for animation.
 jsl SourceAttackChain_Entry
 bcs SourceAttackChain_Fault
 jsl SourceAttackChain_Role
 bcs SourceAttackChain_Fault
SourceAttackChain_Pick:
 lda #1
 sta.l W+10
 lda.l W+26
 tax
 lda #17
 sta.l $43900C,x
 lda #0
 sta.l $43900E,x
 lda.l W+20
 tax
 lda #1
 sta.l $40C058,x
 lda #0
 sta.l $40C05A,x
 lda.l W+24
 tax
 lda #0
 sta.l $43EB00,x
 sta.l $43EB02,x
 lda.l W+4
 sta.l SourceAnimationInit4086_Slot
 lda.l W+6
 sta.l SourceAnimationInit4086_Number
 lda #1
 sta.l SourceAnimationInit4086_Reset
SourceAttackChain_BeforeAnimation:
 jsl SourceAnimationInit4086_Begin
 bcs SourceAttackChain_Fault
 lda #4
 sta.l W+2
 lda #$8002
 bra SourceAttackChain_Return
SourceAttackChain_NoPick:
 lda.l W+22
 tax
 lda #0
 sta.l $437E08,x
 sta.l $437E0A,x
 bra SourceAttackChain_Post
SourceAttackChain_Finish:
 php
 rep #$39
 phx
 phy
 lda.l W
 cmp #$B675
 bne SourceAttackChain_Fault
 lda.l W+2
 cmp #4
 bne SourceAttackChain_Fault
 lda.l SourceAnimationInit4086_Ready
 cmp #$B4EC
 bne SourceAttackChain_Fault
 lda.l SourceAnimationInit4086_State
 cmp #2
 bne SourceAttackChain_Fault
 lda.l SourceAnimationInit4086_Slot
 cmp.l W+4
 bne SourceAttackChain_Fault
 lda.l SourceAnimationInit4086_Number
 cmp.l W+6
 bne SourceAttackChain_Fault
 jsl SourceAttackChain_ReadBody
 bcs SourceAttackChain_Fault
 lda.l W+22
 tax
 lda.l $437E0A,x
 bmi SourceAttackChain_Post
 bne SourceAttackChain_ClearAfter
 lda.l $437E08,x
 cmp.l W+46
 bcc SourceAttackChain_Post
 beq SourceAttackChain_Post
SourceAttackChain_ClearAfter:
 lda #0
 sta.l $437E08,x
 sta.l $437E0A,x
SourceAttackChain_Post:
 lda.l W+36
 and #2
 beq SourceAttackChain_Complete
 lda.l W+22
 tax
 lda.l SourceClock4086_TimeLo
 clc
 adc.l W+58
 sta.l $437E0C,x
 lda.l SourceClock4086_TimeHi
 adc.l W+60
 sta.l $437E0E,x
SourceAttackChain_Complete:
 lda.l W+10
 beq SourceAttackChain_False
 lda #5
 sta.l W+2
 lda #1
 bra SourceAttackChain_Return
SourceAttackChain_False:
 lda #2
 sta.l W+2
 lda #0
SourceAttackChain_Return:
 ply
 plx
 plp
 clc
 rtl
SourceAttackChain_Fault:
 lda #6
 sta.l W+2
 lda #0
 ply
 plx
 plp
 sec
 rtl

SourceAttackChain_ReadBody:
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 bne SourceAttackChain_ReadBad
 lda.l VmSourceWorld_Count
 beq SourceAttackChain_ReadBad
 cmp #129
 bcs SourceAttackChain_ReadBad
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 bne SourceAttackChain_ReadBad
 lda.l W+4
 cmp.l VmSourceWorld_Count
 bcs SourceAttackChain_ReadBad
 asl a
 asl a
 tax
 lda.l STYLES,x
 sta.l W+36
 lda.l STYLES+2,x
 sta.l W+38
 lda.l SourceClock4086_Ready
 cmp #$B4C5
 bne SourceAttackChain_ReadBad
 lda.l W+4
 asl a
 asl a
 asl a
 asl a
 asl a
 asl a
 tax
 lda.l $416800,x
 tax
 lda.l W+4
 jsl SourceAttackBody4086_ReadEntity
 bcs SourceAttackChain_ReadBad
 lda.l SourceAttackBody4086_Chain
 sta.l W+40
 lda.l SourceAttackBody4086_Chain+2
 sta.l W+42
 lda.l SourceAttackBody4086_Chain+4
 sta.l W+44
 lsr a
 lsr a
 lsr a
 lsr a
 sta.l W+46
 ldx #0
SourceAttackChain_Unpack:
 lda.l W+40
 and #7
 sta.l W+64,x
 lda.l W+44
 lsr a
 sta.l W+44
 lda.l W+42
 ror a
 sta.l W+42
 lda.l W+40
 ror a
 sta.l W+40
 lda.l W+44
 lsr a
 sta.l W+44
 lda.l W+42
 ror a
 sta.l W+42
 lda.l W+40
 ror a
 sta.l W+40
 lda.l W+44
 lsr a
 sta.l W+44
 lda.l W+42
 ror a
 sta.l W+42
 lda.l W+40
 ror a
 sta.l W+40
 inx
 inx
 cpx #24
 bne SourceAttackChain_Unpack
 clc
 rtl
SourceAttackChain_ReadBad:
 sec
 rtl
SourceAttackChain_Entry:
 lda.l W+22
 tax
 lda.l $437E0A,x
 bne SourceAttackChain_EntryBad
 lda.l $437E08,x
 beq SourceAttackChain_EntryBad
 cmp #13
 bcs SourceAttackChain_EntryBad
 dec a
 asl a
 tax
 lda.l W+64,x
 clc
 rtl
SourceAttackChain_EntryBad:
 sec
 rtl
SourceAttackChain_Valid:
 jsl SourceAttackChain_Entry
 bcs SourceAttackChain_ValidBad
 jsl SourceAttackChain_Role
 bcs SourceAttackChain_ValidBad
 lda.l W+4
 sta.l SourceAnimationInit4086_Slot
 lda.l W+6
 sta.l SourceAnimationInit4086_Number
 jsl SourceAnimationInit4086_Resolve
 bcs SourceAttackChain_ValidBad
 lda.l SourceAnimationInit4086_Handle
 beq SourceAttackChain_ValidAbsent
 lda.l SourceAnimationInit4086_Count
 beq SourceAttackChain_ValidAbsent
 lda #1
 clc
 rtl
SourceAttackChain_ValidAbsent:
 lda #0
 clc
 rtl
SourceAttackChain_ValidBad:
 sec
 rtl
SourceAttackChain_Role:
 ROLE_LOOKUP
SourceAttackChain_RoleBad:
 sec
 rtl
'''
    lookup = ''
    for i, role in enumerate(attacks, 1):
        lookup += f' cmp #{i}\n beq SourceAttackChain_Role{i}\n'
    lookup += ' bra SourceAttackChain_RoleBad\n'
    for i, role in enumerate(attacks, 1):
        lookup += f'SourceAttackChain_Role{i}:\n lda #{role}\n sta.l W+6\n clc\n rtl\n'
    code = code.replace(' ROLE_LOOKUP', lookup)
    values = dict(W=work, STYLES=styles)
    for name in set(re.findall(r'\b(?:VmSourceWorld|SourceClock4086|SourceAnimationInit4086|SourceAttackBody4086)_[A-Za-z0-9_]+\b', code)):
        values[name] = symbols[name]
    for name, value in values.items():
        code = re.sub(r'\b'+name+r'\b', str(value), code)
    inverse = dict(beq='bne', bne='beq', bcc='bcs', bcs='bcc', bmi='bpl', bpl='bmi')
    # Offline relaxation avoids hand-maintained branch-distance assumptions.
    code = re.sub(r'^ (beq|bne|bcc|bcs|bmi|bpl) (SourceAttackChain_\w+)$',
                  lambda m: f' {inverse[m[1]]} SourceAttackChain_Skip{m.start()}\n jmp {m[2]}\nSourceAttackChain_Skip{m.start()}:', code, flags=re.M)
    code = re.sub(r'^ bra (SourceAttackChain_\w+)$', r' jmp \1', code, flags=re.M)
    code = re.sub(r'^(SourceAttackChain_\w+:)$', r'\1\n.a16\n.i16', code, flags=re.M)
    return code
