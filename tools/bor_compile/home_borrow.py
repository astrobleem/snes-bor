"""Opt-in guarded backdrop-home overflow, with a private transaction journal.

Journal/meta: 42:D700-D78F, below source physics at D800. Returning worker
and character conversion must remain withdrawn in the isolated fixture.
Default invalid-first; policy 1 and capacity limit are diagnostic controls.
"""
JOURNAL=0x42d710
END=0x42d790

def _code():
    text='''
BhInitialize:
 ldx #0
 lda #0
BhInitializeLoop:
 sta.l $42D700,x
 inx
 inx
 cpx #144
 bcc BhInitializeLoop
 lda #64
 sta.l $42D70A
 sta.l $42D70E
 rts
BhBegin:
 lda #0
 sta.l $42D700
 sta.l $42D704
 sta.l $42D706
 sta.l $42D70C
 rts
BhPrepare:
 lda.l $42D674
 beq BhPrepareOK
 lda #0
 sta $72
 ldx #0
BhCountActors:
 lda.l $42C000,x
 cmp #$FFFF
 bne BhCountActorsNext
 inc $72
BhCountActorsNext:
 inx
 inx
 cpx #2048
 bcc BhCountActors
 lda #0
 sta $74
 lda $2E
 asl a
 tax
BhCountTail:
 cpx #1536
 bcs BhCountTailDone
 lda.l $42D000,x
 and #$3FFF
 bne BhCountTailNext
 inc $74
BhCountTailNext:
 inx
 inx
 bra BhCountTail
BhCountTailDone:
 lda $72
 cmp $74
 bcc BhPrepareOK
 beq BhPrepareOK
 sec
 sbc $74
 sta.l $42D706
 cmp #65
 bcs BhPrepareBad
 lda #0
 sta $7E
BhClass:
 lda $7E
 eor.l $42D702
 and #1
 bne BhClassValid
 lda #$8000
 bra BhClassSet
BhClassValid:
 lda #0
BhClassSet:
 sta $7C
 lda #0
 sta $76
BhScan:
 lda $76
 asl a
 tax
 lda.l $42D000,x
 and #$8000
 cmp $7C
 bne BhScanNext
 jsr BhEligible
 bcs BhPrepareBad
 cmp #1
 bne BhScanNext
 lda.l $42D700
 cmp.l $42D70A
 bcs BhPrepareBad
 asl a
 tax
 lda $76
 ora $7C
 sta.l $42D710,x
 lda.l $42D700
 inc a
 sta.l $42D700
 cmp.l $42D706
 beq BhPreparePoolOK
 lda.l $42D702
 and #1
 beq BhScanNext
 lda $7E
 bne BhScanNext
 lda.l $42D700
 cmp.l $42D70E
 bcs BhClassDone
BhScanNext:
 inc $76
 lda $76
 cmp #596
 bcc BhScan
BhClassDone:
 inc $7E
 lda $7E
 cmp #2
 bcc BhClass
BhPrepareBad:
 sec
 rts
BhPreparePoolOK:
 lda #1
 sta.l $42D70C
BhPrepareOK:
 clc
 rts
BhEligible:
 lda $76
 asl a
 tax
 lda.l $42D000,x
 and #$3FFF
 bne BhNotEligible
 lda.l $42D000,x
 and #$4000
 bne BhInconsistent
 ldx #0
BhCommittedScan:
 lda.l $42C800,x
 cmp $76
 beq BhInconsistent
 inx
 inx
 cpx #2048
 bcc BhCommittedScan
 ldx #0
BhPendingScan:
 lda.l $42C000,x
 and #$3FFF
 cmp $76
 beq BhNotEligible
 inx
 inx
 cpx #2048
 bcc BhPendingScan
 lda #1
 clc
 rts
BhNotEligible:
 lda #0
 clc
 rts
BhInconsistent:
 sec
 rts
BhTake:
 lda.l $42D704
 cmp.l $42D700
 bcs BhTakeBad
 asl a
 tax
 lda.l $42D710,x
 and #$3FFF
 sta $2C
 lda.l $42D704
 inc a
 sta.l $42D704
 clc
 rts
BhTakeBad:
 sec
 rts
BhInvalidate:
 lda $2C
 cmp #596
 bcs BhInvalidateOK
 lda.l $42D70C
 cmp #1
 bne BhInvalidateBad
 ldx #0
BhInvalidateFind:
 txa
 lsr a
 cmp.l $42D704
 bcs BhInvalidateBad
 lda.l $42D710,x
 and #$3FFF
 cmp $2C
 beq BhInvalidateFound
 inx
 inx
 bra BhInvalidateFind
BhInvalidateFound:
 phx
 lda $2C
 asl a
 tax
 lda.l $42D000,x
 and #$3FFF
 beq BhInvalidateUnreferenced
 plx
 sec
 rts
BhInvalidateUnreferenced:
 plx
 lda.l $42D710,x
 ora #$4000
 sta.l $42D710,x
 lda $2C
 asl a
 tax
 lda.l $42D000,x
 ora #$8000
 sta.l $42D000,x
BhInvalidateOK:
 clc
 rts
BhInvalidateBad:
 sec
 rts
BhShouldAbort:
 lda.l $42D70C
 cmp #1
 bne BhNoFault
 lda.l $42D708
 cmp #1
 bne BhNoFault
 lda $2C
 cmp #596
 bcs BhNoFault
 lda.l $42D660
 bne BhNoFault
 sec
 rts
BhNoFault:
 clc
 rts
BhVerifyReady:
 lda.l $42D70C
 beq BhReadyOK
 lda.l $42D704
 cmp.l $42D700
 bne BhReadyBad
 ldx #0
BhVerifyLoop:
 txa
 lsr a
 cmp.l $42D700
 bcs BhReadyOK
 lda.l $42D710,x
 and #$4000
 beq BhReadyBad
 inx
 inx
 bra BhVerifyLoop
BhReadyBad:
 sec
 rts
BhReadyOK:
 clc
 rts
BhRollback:
 lda.l $42D700
 beq BhRollbackEmpty
 lda #2
 sta.l $42D70C
 lda.l $42D602
 pha
 lda #0
 sta.l $42D602
 sta $60
BhRollbackLoop:
 lda $60
 cmp.l $42D700
 bcs BhRollbackFlush
 asl a
 tax
 lda.l $42D710,x
 and #$C000
 cmp #$4000
 bne BhRollbackNext
 lda.l $42D710,x
 and #$3FFF
 sta $2C
 jsr WarmCopyBackdrop
 jsr NbPreloadPair
BhRollbackNext:
 inc $60
 bra BhRollbackLoop
BhRollbackFlush:
 jsr NbFlushQueue
BhRestorationFenced:
 lda #0
 sta $60
BhClearValidity:
 lda $60
 cmp.l $42D700
 bcs BhRollbackFinished
 asl a
 tax
 lda.l $42D710,x
 and #$C000
 cmp #$4000
 bne BhClearNext
 lda.l $42D710,x
 and #$3FFF
 asl a
 tax
 lda.l $42D000,x
 and #$7FFF
 sta.l $42D000,x
BhClearNext:
 inc $60
 bra BhClearValidity
BhRollbackFinished:
 pla
 sta.l $42D602
BhRollbackEmpty:
 jsr BhBegin
 rts
BhCommit:
 jsr BhBegin
 rts
BhCodeEnd:
'''
    # Long conditional branches are deliberately explicit absolute jumps;
    # only the unconditional local backwards BRA loops remain relative.
    out=[];serial=0
    for raw in text.strip().splitlines():
        line=raw.strip()
        if line.endswith(':'):out.extend([line,'.a16','.i16']);continue
        op,_,arg=line.partition(' ')
        if op in ('bcc','bcs','beq','bne'):
            serial+=1;label=f'BhBranch{serial}'
            out.extend([f' {dict(bcc="bcs",bcs="bcc",beq="bne",bne="beq")[op]} {label}',f' jmp {arg}',label+':','.a16','.i16'])
        elif op=='bra':out.append(' jmp '+arg)
        else:out.append(' '+line)
    return out

def transform(source):
    a=list(source)
    required=('OnlineComplete:','NbBegin:','NbActorPlanStart:','NbActorProduce:',
              'NbAllPairsReady:','NbAbort:','NbFree:','SpCodeEnd:','NbVisible:')
    for label in required:
        if a.count(label)!=1:raise ValueError('HOME_BORROW_LABEL_DRIFT:'+label)
    if 'BhBegin:' in a:raise ValueError('HOME_BORROW_ALREADY_APPLIED')
    def insert(label,code):
        i=a.index(label)+3;a[i:i]=code
    insert('OnlineComplete:',[' jsr BhInitialize'])
    insert('NbBegin:',[' jsr BhBegin'])
    insert('NbActorPlanStart:',[' jsr BhPrepare',' bcc BhActorPlanAdmitted',' jmp NbAbort','BhActorPlanAdmitted:','.a16','.i16'])
    # Exhaustion of the original tail scanner is the only alternate allocation
    # entry. Original conservative/exact retry remains intact below this hook.
    old=[' cmp #768',' bcc NbFreeCheck',' pla',' lda.l $42D674']
    i=a.index('NbFree:');j=next(k for k in range(i,len(a)-3) if a[k:k+4]==old)
    a[j:j+4]=[' cmp #768',' bcc NbFreeCheck',' lda.l $42D70C',' cmp #1',' bne BhOriginalExhaustion',
                   ' jsr BhTake',' bcs BhOriginalExhaustion',' rts','BhOriginalExhaustion:','.a16','.i16',' pla',' lda.l $42D674']
    i=a.index('NbActorProduce:');j=a.index(' jsr NbPreloadPair',i)
    a[j:j+1]=[' jsr BhInvalidate',' bcc BhActorPairSafe',' jmp NbAbort','BhActorPairSafe:','.a16','.i16',
                ' jsr NbPreloadPair',' jsr BhShouldAbort',' bcc BhActorPairContinue',' jmp NbAbort','BhActorPairContinue:','.a16','.i16']
    insert('NbAllPairsReady:',[' jsr BhVerifyReady',' bcc BhPendingReady',' jmp NbAbort','BhPendingReady:','.a16','.i16'])
    i=a.index('NbAbort:');j=a.index(' sta.l $42D660',i)+1;a[j:j]=[' jsr BhRollback']
    insert('NbVisible:',[' jsr BhCommit'])
    i=a.index('.org $C000');a[i:i]=['.org $B300',*_code()]
    return a
