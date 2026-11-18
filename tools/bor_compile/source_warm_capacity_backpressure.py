"""Opt-in capacity deferral for the private single-owner warm renderer.

Only a typed second preflight capacity rejection may return without publishing.
The existing abort must finish first. Consistency/owner/cleanup faults stay
fatal. A failed visual key is retried only after the sealed source key changes;
simulation and input retain their ordinary source owners and clock policy.
"""
from __future__ import annotations

import re

from source_warm_presentation_native import _relax

REASON = 0x7E951C
PRIOR_STATUS = 0x7E951E
DEFER_COUNT = 0x7E9508
VISUAL_OFFSETS = (0x50, 0x54, 0x56, 0x1C, 0x1E, 0x36, 0x3E, 0x0C, 0x0E)


def _replace(text, anchor, replacement):
    if text.count(anchor) != 1:
        raise ValueError('WARM_CAPACITY_SHAPE:' + anchor.splitlines()[0])
    return text.replace(anchor, replacement)


def integrate_renderer(renderer):
    # 0=admitted/unclassified caller; 1=resource shortage; 2=consistency or
    # unknown failure; 3=second typed failure at the reversible phase-1 edge.
    renderer = _replace(renderer, 'BhPrepare:\n.a16\n.i16\n',
        f'BhPrepare:\n.a16\n.i16\n lda #2\n sta.l ${REASON:06X}\n')
    renderer = _replace(renderer, 'BhPrepareOK:\n.a16\n.i16\n',
        f'BhPrepareOK:\n.a16\n.i16\n lda #0\n sta.l ${REASON:06X}\n')
    # home_borrow emits relaxed conditionals. Only its literal >64 shortage
    # edge is retargeted; BhEligible and pool-limit consistency edges keep the
    # original fatal destination. Natural exhaustion of BOTH classes falls
    # through the new JMP, while explicit fatal jumps bypass it.
    renderer, count = re.subn(
        r'( cmp #65\n bcc BhBranch\d+\n) jmp BhPrepareBad\n',
        r'\1 jmp WarmCapacity_Exhausted\n', renderer)
    if count != 1:
        raise ValueError('WARM_CAPACITY_HARD_LIMIT_SHAPE')
    renderer = _replace(renderer, 'BhPrepareBad:\n.a16\n.i16\n',
        ' jmp WarmCapacity_Exhausted\nBhPrepareBad:\n.a16\n.i16\n')
    extra = f'''WarmCapacity_Exhausted:
.a16
.i16
 lda #1
 sta.l ${REASON:06X}
 sec
 rts
WarmCapacity_Prepare:
.a16
.i16
 jsr BhPrepare
 bcc WarmCapacity_Prepared
 lda.l ${REASON:06X}
 cmp #1
 bne WarmCapacity_PrepareFailed
 jsr BhBegin
 jsr WarmContent_Plan
 jsr BhPrepare
 bcc WarmCapacity_Prepared
 lda.l ${REASON:06X}
 cmp #1
 bne WarmCapacity_PrepareFailed
 lda.l $42D600
 cmp #1
 bne WarmCapacity_PrepareFailed
 lda.l $42D660
 ora.l $42D704
 bne WarmCapacity_PrepareFailed
 lda #3
 sta.l ${REASON:06X}
WarmCapacity_PrepareFailed:
.a16
.i16
 sec
 rts
WarmCapacity_Prepared:
.a16
.i16
 clc
 rts
BhCodeEnd:
.a16
.i16
'''
    renderer = _replace(renderer, 'BhCodeEnd:\n.a16\n.i16\n', extra)
    anchor = '''NbActorPlanStart:
.a16
.i16
 jsr BhPrepare
 bcc BhActorPlanAdmitted
 ; Ordinary admission performs no color scan or VRAM reads. Only a failed
 ; exact preflight pays for sharing; clear its provisional borrow list before
 ; replanning, without changing restores, refs, maps or the allocation cursor.
 jsr BhBegin
 jsr WarmContent_Plan
 jsr BhPrepare
 bcc BhActorPlanAdmitted
 jmp NbAbort
BhActorPlanAdmitted:'''
    replacement = '''NbActorPlanStart:
.a16
.i16
 jsr WarmCapacity_Prepare
 bcc BhActorPlanAdmitted
 jmp NbAbort
BhActorPlanAdmitted:'''
    renderer = _replace(renderer, anchor, replacement)
    return _relax(renderer, 'WarmCapacity')


def integrate_helper(helper, symbols):
    required = ('SourceClock4086_Ready', 'SourceClock4086_Fault', 'SourceClock4086_Due',
                'SourceWorldTick4086_Ready', 'SourceWorldTick4086_State',
                'SourceWorldTick4086_Pending', 'SourceWorldTick4086_Fault',
                'LiveWork_Check')
    if any(type(symbols.get(n)) is not int for n in required):
        raise ValueError('WARM_CAPACITY_GUARD_SYMBOLS')
    changed = f'''WarmTryPublish_Changed:
.a16
.i16
 lda.l ${REASON:06X}
 cmp #3
 bne WarmCapacity_NewKey
'''
    for off in VISUAL_OFFSETS:
        changed += (f' lda.l ${0x7E7800+off:06X}\n'
                    f' cmp.l ${0x7E9600+off:06X}\n'
                    ' bne WarmCapacity_NewKey\n')
    changed += f''' jmp WarmTryPublish_Unchanged
WarmCapacity_NewKey:
.a16
.i16
 lda.l $7E9500
 sta.l ${PRIOR_STATUS:06X}
 lda #0
 sta.l ${REASON:06X}
 ldx #0'''
    helper = _replace(helper, 'WarmTryPublish_Changed:\n.a16\n.i16\nldx #0', changed)
    failed = f'''WarmTryPublish_Failed:
.a16
.i16
 jsr WarmCapacity_Check
 bcs WarmCapacity_Fatal
 lda.l ${DEFER_COUNT:06X}
 cmp #$FFFF
 beq WarmCapacity_CountDone
 inc a
 sta.l ${DEFER_COUNT:06X}
WarmCapacity_CountDone:
.a16
.i16
 lda #2
 sta.l $7E9500
WarmCapacity_Deferred:
.a16
.i16
 nop
 pld
 plb
 ply
 plx
 pla
 plp
 clc
 rtl
WarmCapacity_Fatal:
.a16
.i16
 lda #4'''
    helper = _replace(helper, 'WarmTryPublish_Failed:\n.a16\n.i16\nlda #4', failed)
    code = 'WarmCapacity_Check:\n.a16\n.i16\n'
    def equal(address, value):
        nonlocal code
        code += (f' lda.l ${address:06X}\n cmp #{value}\n'
                 ' bne WarmCapacity_Bad\n')
    equal(REASON, 3)
    equal(PRIOR_STATUS, 2)
    equal(0x7FFB88, 0xB6D0)
    equal(0x7FFB96, 0xB4B8)
    for at in (0x7E9502, 0x7E9504, 0x7E9506, 0x42D600, 0x42D660,
               0x42D700, 0x42D704, 0x42D706, 0x42D70C):
        equal(at, 0)
    equal(0x7E7700, 0xB6D0)
    equal(0x7E7704, 1)
    equal(0x7E7706, 0)
    equal(0x7E7710, 0)
    equal(0x7E7714, 0)
    equal(symbols['SourceClock4086_Ready'], 0xB4C5)
    equal(symbols['SourceClock4086_Fault'], 0)
    equal(symbols['SourceWorldTick4086_Ready'], 0xB4D5)
    equal(symbols['SourceWorldTick4086_Fault'], 0)
    code += f''' lda.l $7E7702
 cmp #1
 beq WarmCapacity_IdleWorld
 cmp #2
 bne WarmCapacity_Bad
 lda.l ${symbols['SourceWorldTick4086_State']:06X}
 beq WarmCapacity_Bad
 cmp #5
 bcs WarmCapacity_Bad
 lda.l ${symbols['SourceClock4086_Due']:06X}
 beq WarmCapacity_Bad
 lda.l ${symbols['SourceWorldTick4086_Pending']:06X}
 cmp #2
 bcs WarmCapacity_Bad
 jmp WarmCapacity_WorldGood
WarmCapacity_IdleWorld:
.a16
.i16
'''
    equal(symbols['SourceWorldTick4086_State'], 0)
    equal(symbols['SourceWorldTick4086_Pending'], 0)
    code += f'''WarmCapacity_WorldGood:
.a16
.i16
 lda.l $7E9790
 ora.l $7E9792
 beq WarmCapacity_Bad
 ldx #1
 ldy #0
 jsl ${symbols['LiveWork_Check']:06X}
 bcs WarmCapacity_Bad
 ldx #0
WarmCapacity_MapCheck:
.a16
.i16
 lda.l $42C000,x
 cmp.l $42C800,x
 bne WarmCapacity_Bad
 cmp #768
 bcs WarmCapacity_Bad
 inx
 inx
 cpx #2048
 bcc WarmCapacity_MapCheck
 ldx #0
WarmCapacity_RefCheck:
.a16
.i16
 lda.l $42D000,x
 and #$4000
 bne WarmCapacity_Bad
 inx
 inx
 cpx #1536
 bcc WarmCapacity_RefCheck
 clc
 rts
WarmCapacity_Bad:
.a16
.i16
 sec
 rts
'''
    return _relax(_replace(helper, 'WarmHelper_CodeEnd:\n.a16\n.i16\n',
                           code + 'WarmHelper_CodeEnd:\n.a16\n.i16\n'), 'WarmCapacity')
