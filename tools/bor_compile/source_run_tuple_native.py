"""Capture actual shared cached RUN fields into immutable entity snapshots.

Copy wraps the real native entity model-data copier, publishing the handle only
after it succeeds. Neither entry point grants a production RAM lease by itself.
"""
import re


def emit(work, handles, report, symbols,copy_entry=None):
    for a,n in ((work,64),(handles,256)):
        if not 0<=a<=0x1000000-n:raise ValueError('RUN_TUPLE_NATIVE_EXTENT')
    if work<handles+256 and handles<work+64:raise ValueError('RUN_TUPLE_NATIVE_OVERLAP')
    tuples=[bytes.fromhex(r)for r in report['tuples']]
    count=len(report['models'])
    if not 1<=count<=16 or not 1<=len(tuples)<=16 or any(len(r)!=20 for r in tuples):
        raise ValueError('RUN_TUPLE_NATIVE_PROFILE')
    if [m['id']for m in report['models']]!=list(range(count)):
        raise ValueError('RUN_TUPLE_NATIVE_MODEL_ORDER')
    code='''
SourceRunTuple_CaptureCurrent:
 php
 rep #$39
 phx
 phy
 lda #1
 sta.l W+58
 jmp SourceRunTuple_Start
SourceRunTuple_Copy:
 php
 rep #$39
 phx
 phy
 lda #0
 sta.l W+58
SourceRunTuple_Start:
 jsl SourceRunTuple_Guard
 bcs SourceRunTuple_Fault
 lda.l SourceModelEntityCopy4086_Ready
 cmp #$B4EB
 bne SourceRunTuple_Fault
 lda.l SourceModelEntityCopy4086_Models
 cmp #MODELCOUNT
 bne SourceRunTuple_Fault
 lda.l SourceModelEntityCopy4086_Entities
 cmp.l VmSourceWorld_Count
 bne SourceRunTuple_Fault
 lda.l W+6
 cmp #MODELCOUNT
 bcs SourceRunTuple_Fault
 ; Cache row is 160 bytes; RUN occupies +4..+23.
 asl a
 asl a
 asl a
 asl a
 asl a
 sta.l W+10
 asl a
 asl a
 clc
 adc.l W+10
 clc
 adc #4
 tax
 MATCH
SourceRunTuple_Matched:
 sta.l W+8
 lda.l W+58
 bne SourceRunTuple_Publish
 lda.l W+4
 sta.l SourceModelEntityCopy4086_Slot
 lda.l W+6
 sta.l SourceModelEntityCopy4086_Model
 jsl SourceModelEntityCopy4086_Apply
 bcs SourceRunTuple_Fault
SourceRunTuple_Publish:
 lda.l W+4
 asl a
 tax
 lda.l W+8
 sta.l HANDLES,x
 bra SourceRunTuple_Complete
SourceRunTuple_Read:
 php
 rep #$39
 phx
 phy
 jsl SourceRunTuple_Guard
 bcs SourceRunTuple_Fault
 lda.l W+4
 asl a
 tax
 lda.l HANDLES,x
 READ
SourceRunTuple_Complete:
 lda #2
 sta.l W+2
 lda.l W+8
 ply
 plx
 plp
 clc
 rtl
SourceRunTuple_Fault:
 lda #3
 sta.l W+2
 lda #0
 ply
 plx
 plp
 sec
 rtl
SourceRunTuple_Guard:
 lda.l W
 cmp #$B678
 bne SourceRunTuple_GuardBad
 lda.l W+2
 beq SourceRunTuple_World
 cmp #2
 bne SourceRunTuple_GuardBad
SourceRunTuple_World:
 lda.l VmSourceWorld_Ready
 cmp #$B4A3
 bne SourceRunTuple_GuardBad
 lda.l VmSourceWorld_PoolBase
 cmp #$4000
 bne SourceRunTuple_GuardBad
 lda.l VmSourceWorld_Count
 beq SourceRunTuple_GuardBad
 cmp #129
 bcs SourceRunTuple_GuardBad
 lda.l W+4
 cmp.l VmSourceWorld_Count
 bcs SourceRunTuple_GuardBad
 clc
 rtl
SourceRunTuple_GuardBad:
 sec
 rtl
'''
    match=''
    for i,row in enumerate(tuples,1):
        for at in range(0,20,2):
            word=int.from_bytes(row[at:at+2],'little')
            match+=f' lda.l $40B000+{at},x\n cmp #{word}\n bne SourceRunTuple_Try{i+1}\n'
        match+=f' lda #{i}\n jmp SourceRunTuple_Matched\nSourceRunTuple_Try{i+1}:\n'
    match+=' jmp SourceRunTuple_Fault\n'
    read=''
    for i in range(1,len(tuples)+1):read+=f' cmp #{i}\n beq SourceRunTuple_Read{i}\n'
    read+=' jmp SourceRunTuple_Fault\n'
    for i,row in enumerate(tuples,1):
        read+=f'SourceRunTuple_Read{i}:\n lda #{i}\n sta.l W+8\n'
        for at in range(0,20,2):read+=f' lda #{int.from_bytes(row[at:at+2],"little")}\n sta.l W+{20+at}\n'
        read+=' jmp SourceRunTuple_Complete\n'
    code=code.replace(' MATCH',match).replace(' READ',read)
    values=dict(W=work,HANDLES=handles,MODELCOUNT=count)
    if copy_entry is not None:
        if not isinstance(copy_entry,str)or not re.fullmatch(r'[A-Za-z_]\w*',copy_entry):raise ValueError('RUN_TUPLE_COPY_ENTRY')
        code=code.replace(' jsl SourceModelEntityCopy4086_Apply',' jsl '+copy_entry)
    for name in set(re.findall(r'\b(?:VmSourceWorld|SourceModelEntityCopy4086)_\w+\b',code)):values[name]=symbols[name]
    for name,value in values.items():code=re.sub(r'\b'+name+r'\b',str(value),code)
    inverse=dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')
    code=re.sub(r'^ (beq|bne|bcc|bcs) (SourceRunTuple_\w+)$',lambda m:f' {inverse[m[1]]} SourceRunTuple_Skip{m.start()}\n jmp {m[2]}\nSourceRunTuple_Skip{m.start()}:',code,flags=re.M)
    code=re.sub(r'^ bra (SourceRunTuple_\w+)$',r' jmp \1',code,flags=re.M)
    return re.sub(r'^(SourceRunTuple_\w+:)$',r'\1\n.a16\n.i16',code,flags=re.M)


def emit_entity_copy_bridge(work,symbols):
    """Preflight and capture around the actual copier; disabled delegates exactly.

    Pair with emit(copy_entry='SourceRunTuple_EntityCopyOriginal'). The original
    prologue must be checked before installing the caller-owned private hook.
    """
    return f'''
SourceRunTuple_EntityCopyBridge:
.a16
.i16
 php
 rep #$39
 phx
 phy
 lda.l {work}
 beq SourceRunTuple_EntityCopyDisabled
 cmp #$B678
 bne SourceRunTuple_EntityCopyBad
 lda.l {work}+2
 beq SourceRunTuple_EntityCopyReady
 cmp #2
 bne SourceRunTuple_EntityCopyBad
SourceRunTuple_EntityCopyReady:
.a16
.i16
 lda.l {symbols['SourceModelEntityCopy4086_Slot']}
 sta.l {work}+4
 lda.l {symbols['SourceModelEntityCopy4086_Model']}
 sta.l {work}+6
 jsl SourceRunTuple_Copy
 bcs SourceRunTuple_EntityCopyBad
 lda #1
 jmp SourceRunTuple_EntityCopyDone
SourceRunTuple_EntityCopyDisabled:
.a16
.i16
 jsl SourceRunTuple_EntityCopyOriginal
 bcs SourceRunTuple_EntityCopyDisabledBad
SourceRunTuple_EntityCopyDone:
.a16
.i16
 ply
 plx
 plp
 clc
 rtl
SourceRunTuple_EntityCopyDisabledBad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
SourceRunTuple_EntityCopyBad:
.a16
.i16
 lda #3
 sta.l {work}+2
 ply
 plx
 plp
 sec
 rtl
SourceRunTuple_EntityCopyOriginal:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jml {symbols['SourceModelEntityCopy4086_Apply']+5}
'''


def emit_ctor_model_bridge(work, symbols):
    """Capture after the real fresh copier; AI birth happens before this copy."""
    body=symbols['SourceCtorModel4086_Apply']+5
    slot=symbols['SourceScriptClone4086_Slot'];model=symbols['SourceScriptClone4086_Model']
    return f'''
SourceRunTuple_CtorModelBridge:
.a16
.i16
 php
 rep #$39
 phx
 phy
 jsl SourceRunTuple_CtorModelOriginal
 bcs SourceRunTuple_CtorModelBad
 pha
 lda.l {work}
 beq SourceRunTuple_CtorModelDone
 cmp #$B678
 bne SourceRunTuple_CtorCaptureBad
 lda.l {slot}
 sta.l {work}+4
 lda.l {model}
 sta.l {work}+6
 jsl SourceRunTuple_CaptureCurrent
 bcs SourceRunTuple_CtorCaptureBad
SourceRunTuple_CtorModelDone:
.a16
.i16
 pla
 ply
 plx
 plp
 clc
 rtl
SourceRunTuple_CtorCaptureBad:
.a16
.i16
 pla
SourceRunTuple_CtorModelBad:
.a16
.i16
 ply
 plx
 plp
 sec
 rtl
SourceRunTuple_CtorModelOriginal:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jml {body}
'''
