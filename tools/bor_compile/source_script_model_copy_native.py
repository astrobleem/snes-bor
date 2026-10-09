"""Closed method-0 model script copying; reuse checked B5SC/B4CO controls.

Only animation instances without init/clear entries are admitted by B5SC.
Named values survive. Absent source scripts preserve the old initialized bit;
actual animation execution resolves and captures immutable model programs.
"""
from pathlib import Path
import re


def emit(symbols,repository=None):
    root=Path(repository)if repository is not None else Path(__file__).resolve().parents[2]
    code=(root/'src/core/vm/vm_source_script_clone.pasm').read_text(encoding='cp1252')
    code=code[code.index('SourceScriptClone4086_Bind:'):]
    old=' lda.l $40902C,x\n ora.l $40902E,x'
    new=' lda.l $40902C,x\n cmp #2\n bcs SourceScriptClone4086_Bad\n lda.l $40902E,x'
    if code.count(old)!=1:raise ValueError('SCRIPT_MODEL_COPY_OLD_INSTANCE_AUTHORITY')
    code=code.replace(old,new)
    old=' lda.l SourceScriptClone4086_Mask\n sta.l $40902C,x'
    new=' lda.l SourceScriptClone4086_Mask\n beq SourceScriptClone4086_Good\n sta.l $40902C,x'
    if code.count(old)!=1:raise ValueError('SCRIPT_MODEL_COPY_ABSENT_AUTHORITY')
    code=code.replace(old,new)
    labels=set(re.findall(r'^(\w+):',code,re.M))
    for old in sorted(labels,key=len,reverse=True):code=re.sub(r'\b'+old+r'\b','ModelScriptCopy_'+old,code)
    prefix='''
ModelScriptCopy_Clear0:
.a16
.i16
 php
 rep #$38
 phx
 phy
 jsr ModelScriptCopy_SourceScriptClone4086_Preflight
 bcs ModelScriptCopy_SourceScriptClone4086_Bad
 lda.l SourceScriptClone4086_Relation
 tax
 lda.l $40902C,x
 cmp #2
 bcs ModelScriptCopy_SourceScriptClone4086_Bad
 lda.l $40902E,x
 ora.l $409030,x
 ora.l $409032,x
 ora.l $409034,x
 ora.l $409036,x
 bne ModelScriptCopy_SourceScriptClone4086_Bad
 lda #0
 sta.l $40902C,x
 sta.l $40902E,x
 jmp ModelScriptCopy_SourceScriptClone4086_Good
ModelScriptCopy_Copy0:
.a16
.i16
'''
    code=prefix+code
    serial=[0]
    def relax(m):
        serial[0]+=1;label='ModelScriptCopy_Branch'+str(serial[0])
        return m[1]+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[m[2]]+' '+label+'\n jmp '+m[3]+'\n'+label+':\n.a16\n.i16'
    code=re.sub(r'^(\s+)(beq|bne|bcc|bcs) (ModelScriptCopy_\w+)$',relax,code,flags=re.M)
    for name in sorted(symbols,key=len,reverse=True):
        if name.startswith(('Source','Vm','SOURCE_','BOR_')):code=re.sub(r'\b'+re.escape(name)+r'\b',str(symbols[name]),code)
    return code
