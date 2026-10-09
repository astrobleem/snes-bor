"""Private native timed operator with the world owner's relative geometry.

The checked repository operator is emitted unchanged except for the world geometry
comparisons. Production assembly is not patched by this offline proof module.
"""
import re
from pathlib import Path


def emit(symbols):
    source=Path('src/core/vm/vm_source_update_animation.pasm').read_text(encoding='cp1252')
    prefix=Path('src/core/vm/vm_source_update_animation_prefix.pasm').read_text(encoding='cp1252')
    code=source[source.index('SourceUpdateAnimation4086_Begin:'):]+ '\n'+prefix[prefix.index('SourceUpdateAnimationPrefix4086_Execute:'):]
    for field,base in [('Side',0x6800),('View',0x4000)]:
        old=' cmp.l SourceWorldTick4086_'+field
        if code.count(old)!=2:raise ValueError('TIMED_WORLD_GEOMETRY_AUTHORITY_'+field)
        code=code.replace(old,' sec\n sbc #$'+format(base,'04X')+'\n'+old)
    # The stored timed side remains a bank address used by native actor reads.
    old='SourceUpdateAnimation4086_Guard10:\n.a16\n.i16\n sta.l SourceUpdateAnimation4086_Side'
    new='SourceUpdateAnimation4086_Guard10:\n.a16\n.i16\n lda.l SourceUpdateFrame4086_Side\n sta.l SourceUpdateAnimation4086_Side'
    if old not in code:raise ValueError('TIMED_WORLD_GEOMETRY_SIDE_PUBLICATION')
    code=code.replace(old,new)
    old='SourceUpdateAnimationPrefix4086_Branch25:\n.a16\n.i16\n cmp.l SourceSelf4086_GlobalLow'
    if old not in code:raise ValueError('TIMED_WORLD_GEOMETRY_SELF')
    code=code.replace(old,old.replace(' cmp.l',' lda $0C\n cmp.l'))
    labels=set(re.findall(r'^(SourceUpdateAnimation(?:Prefix)?4086_\w+):',code,re.M))
    for name in sorted(labels,key=len,reverse=True):
        code=re.sub(r'\b'+name+r'\b',name.replace('SourceUpdateAnimation4086_','TimedWorldGeometry_').replace('SourceUpdateAnimationPrefix4086_','TimedWorldGeometry_Prefix'),code)
    serial=[0]
    def relax(match):
        serial[0]+=1;label='TimedWorldGeometry_Relax'+str(serial[0])
        return ' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc',bpl='bmi',bmi='bpl')[match[1]]+' '+label+'\n jmp '+match[2]+'\n'+label+':\n.a16\n.i16'
    code=re.sub(r'^ (beq|bne|bcc|bcs|bpl|bmi) (TimedWorldGeometry_\w+)$',relax,code,flags=re.M)
    code=re.sub(r'^ bra (TimedWorldGeometry_\w+)$',r' jmp \1',code,flags=re.M)
    for name in sorted(symbols,key=len,reverse=True):
        if name.startswith(('Source','VmSourceWorld_','SOURCE_','BOR_')):code=re.sub(r'\b'+name+r'\b',str(symbols[name]),code)
    return code+'\nTimedWorldGeometry_CodeEnd:\n.a16\n.i16\n'
