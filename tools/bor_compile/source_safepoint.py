"""Opt-in READY source-ground safe-point. Original movement service bytes retained.
Latch uses only dead transaction-header padding D60C..D61F, never records/queue.
"""
from pathlib import Path
LATCH=0x42d60c
LATCH_EPOCH=LATCH+18
REQUEST=0x7ffb80
SOURCE_ASM=Path('out/byor-motu-online-v3/native/callback_fixture.pasm')
SOURCE_SYM=SOURCE_ASM.with_suffix('.sym')

def movement_code():
    from actor_s5_entity_fixture import symbols
    sy=symbols(SOURCE_SYM);src=SOURCE_ASM.read_text().splitlines()
    a=src.index('LiveGroundStart:');b=src.index('LiveGroundPost:');start=src[a:b]
    a=src.index('LiveGroundExecute:');b=src.index('CallbackFixture_GroundDone:')+5;execute=src[a:b]
    a=src.index('LiveGroundPost:');b=src.index(' jsl $398000',a);post=src[a:b]
    code=start+execute+post+[' clc',' rts','SpGroundBad:','.a16','.i16',' sec',' rts']
    local={s[:-1]: 'SpOwner_'+s[:-1] for s in code if s.endswith(':') and s!='SpGroundBad:'}
    result=[]
    for s in code:
        if s.endswith(':'):s=local.get(s[:-1],s[:-1])+':'
        else:
            op,_,arg=s.strip().partition(' ')
            if arg=='CallbackFixture_Bad':s=' jmp SpGroundBad'
            elif arg in local:s=' '+op+' '+local[arg]
            elif op=='jsl' and arg in sy:s=f' jsl {sy[arg]}'
        result.append(s)
    if any('CallbackFixture_Bad' in x or '$398000' in x for x in result):raise ValueError('SAFEPOINT_RECURSIVE_PUBLISH_OR_NONRETURNING_ERROR')
    return result

def transform(source):
    a=list(source)
    for n in ('NbGuard4:','NbMapCommit:','NbPublishRefs:','NbCodeEnd:','.org $C000'):
        if a.count(n)!=1:raise ValueError('SAFEPOINT_LABEL_DRIFT:'+n)
    # Keep all stale/queue/capability guards before READY, and MODE rejection
    # before permitting a world operation. Fresh VBlank for maps remains intact.
    at=a.index(' jsr NbFreshVblank',a.index('NbGuard4:'))
    a[at:at]=[' jsr SpReadyBoundary']
    # Only warm completion consumes the immutable latch; cold path unchanged.
    begin=a.index('NbPublishRefs:');end=a.index('NbVisible:',begin)
    completion=a[begin:end]
    reads=[]
    for i,s in enumerate(completion):
        if s.startswith(' lda.l ') and i+1<len(completion) and completion[i+1].startswith(' sta.l '):
            target=completion[i+1].split()[-1]
            if target in [str(0x42d6d0+2*j) for j in range(9)]:reads.append((begin+i,int(s.split()[-1])))
    if len(reads)!=9:raise ValueError('SAFEPOINT_COMPLETION_KEY_READS')
    for j,(i,addr) in enumerate(reads):a[i]=f' lda.l ${LATCH+2*j:06X}'
    epochpair=[' lda.l 8370832',' sta.l 8387480']
    pos=[i for i in range(begin,len(a)-1) if a[i:i+2]==epochpair]
    if len(pos)!=1:raise ValueError('SAFEPOINT_COMPLETION_EPOCH_READ')
    a[pos[0]]=f' lda.l ${LATCH_EPOCH:06X}'
    code=['SpReadyBoundary:','.a16','.i16']
    # Capture after READY/source equality, before releasing source owner.
    for j,(_,addr) in enumerate(reads):code +=[f' lda.l {addr}',f' sta.l ${LATCH+2*j:06X}']
    code +=[' lda.l $42D604',f' sta.l ${LATCH_EPOCH:06X}','SpLatched:','.a16','.i16',
        ' lda.l $7FFB80',' cmp #$B4E8',' beq SpHasQueuedMovement',' rts','SpHasQueuedMovement:','.a16','.i16',
        ' php',' pha',' phx',' phy',' phb',' phd',' lda #0',' tcd',' sep #$20','.a8',' lda #0',' pha',' plb',' rep #$38','.a16','.i16',
        # Actual auto-JOY sampling, NMI remains disabled. Finish wait in active
        # display before invoking world; no DMA-critical window is occupied.
        ' lda.l $7FB46A',' cmp #2',' beq SpSourceOwnerClosed',' jmp SpMovementFailed','SpSourceOwnerClosed:','.a16','.i16',
        ' sep #$20','.a8',' lda #1',' sta.l $004200',' rep #$20','.a16',' jsr NbFreshVblank','SpWaitActive:','.a16','.i16',' lda.l $004212',' and #$80',' bne SpWaitActive',
        'SpMovementStart:','.a16','.i16',' jsr SpOwner_LiveGroundStart','SpMovementComplete:','.a16','.i16',' bcc SpMovementOK',' jmp SpMovementFailed','SpMovementOK:','.a16','.i16',
        ' pld',' plb',' ply',' plx',' pla',' plp','SpRegistersRestored:','.a16','.i16',' rts',
        'SpMovementFailed:','.a16','.i16',' pld',' plb',' ply',' plx',' pla',' plp',' pla',' jmp NbAbort',
        *movement_code(),
        'SpOwnerPoll:','.a16','.i16',' lda.l $7FFB80',' cmp #$B4E9',' beq SpRenderCurrent',' cmp #$B4E8',' beq SpNormalMovement',' jml SpOwnerPoll',
        'SpNormalMovement:','.a16','.i16',' jml $279F71',
        'SpRenderCurrent:','.a16','.i16',' lda #0',' sta.l $7FFB80',' jsl $398000',' bcc SpRenderOK',' lda #1',' sta.l $7FFB84',' jml $27A0E4',
        'SpRenderOK:','.a16','.i16',' lda #0',' sta.l $7FFB84',' jml $27A0E4','SpCodeEnd:']
    # Capacity code ends before B000; dedicated new measured code lease.
    at=a.index('.org $C000');a[at:at]=['.org $B000',*code]
    from actor_s5_entity_fixture import symbols
    sy=symbols(SOURCE_SYM)
    a=[x.replace('$279F71',f'${sy["LiveGroundStart"]:06X}').replace('$27A0E4',f'${sy["LiveGroundIdle"]:06X}') for x in a]
    service=SOURCE_ASM.read_text().splitlines();i=service.index('GroundServices_Begin:');work=int(next(x.strip().split()[1] for x in service[i:] if x.strip().startswith('lda.l ')))
    a=[x.replace('$7FB46A',f'${work+2:06X}') for x in a]
    return a
