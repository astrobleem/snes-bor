"""Fail-closed instruction-length and branch reach audit for emitted tile routine.

Not an assembler or native runtime verifier. Intended to catch short-branch and
placement mistakes before Sol runs the real Poppy assembler.
"""
from __future__ import annotations
import re
from tile_fusion import tile_routine

class SanityError(ValueError):pass


def audit_asm(lines=None):
    lines=tile_routine() if lines is None else list(lines)
    pc=0;labels={};branches=[];ops=0;a16=True;x16=True
    for s in lines:
        line=s.strip().split(';',1)[0].strip()
        if not line:continue
        if line.startswith('.org '):pc=int(line[5:].replace('$',''),16);continue
        if line in ('.a16','.a8','.i16','.i8'):
            if line.startswith('.a'):a16=line=='.a16'
            if line.startswith('.i'):x16=line=='.i16'
            continue
        if line.endswith(':'):
            label=line[:-1]
            if label in labels:raise SanityError('DUPLICATE_LABEL:'+label)
            labels[label]=pc;continue
        tok=line.split(None,1);op=tok[0].lower();operand=tok[1].strip() if len(tok)>1 else ''
        if op in ('php','phx','phy','plp','plx','ply','xba','clc','incx','inx','iny','rtl','asl','tax'):size=1
        elif op=='asl' and operand.lower()=='a':size=1
        elif op in ('rep','sep'):size=2
        elif op in ('bcc','bcs','beq','bne','bmi','bpl','bra'):
            size=2;branches.append((pc+2,op,operand,8))
        elif op=='brl':size=3;branches.append((pc+3,op,operand,16))
        elif op in ('jmp','jsr'):size=3;branches.append((pc+3,op,operand,None))
        elif operand.startswith('#'):
            if op in ('ldy','ldx'):size=3 if x16 else 2
            else:size=3 if a16 else 2
        elif operand.startswith('['):size=2
        elif operand.startswith('$'):
            hexaddr=operand.split(',')[0][1:]
            if '.l' in op:size=4
            elif len(hexaddr)<=2:size=2
            elif len(hexaddr)<=4:size=3
            else:raise SanityError('LONG_ADDRESS_MODE_REQUIRED:'+line)
        else:raise SanityError('UNKNOWN_ASM_FORM:'+line)
        pc+=size;ops+=1
    if 'AstraOpaqueTile' not in labels or 'AstraTileDone' not in labels:
        raise SanityError('MISSING_ENTRY_OR_EXIT')
    if pc>=0xf000:raise SanityError('E200_TO_F000_OVERFLOW')
    for src,op,target,width in branches:
        if target not in labels:raise SanityError('UNRESOLVED_BRANCH:'+target)
        diff=labels[target]-src
        if width==8 and not -128<=diff<=127:raise SanityError('SHORT_BRANCH_OUT_OF_RANGE:'+str((op,target,diff)))
        if width==16 and not -32768<=diff<=32767:raise SanityError('LONG_BRANCH_OUT_OF_RANGE')
    return dict(start=labels['AstraOpaqueTile'],end=pc,bytes=pc-labels['AstraOpaqueTile'],instructions=ops,
                branches=len(branches),labels=len(labels),unused_to_f000=0xf000-pc)

if __name__=='__main__':print(audit_asm())
