"""Bounded opt-in nonblank transaction; existing fused producer and DMA unchanged.

No additional RAM/VRAM/assets. $42D600..D67F is the unused scalar CHUNK in
this fused backend: 32-byte transaction header plus at most 16 restore pairs.
Pending maps at C000; committed maps C800; committed refs D000 stay protected.
Allocation uses only unreferenced tail slots >=596, monotonically reserved.
"""
STATE=0x42d600
MODE=STATE+2
PENDING_EPOCH=STATE+4
RESTORES=STATE+6
PAIRS=STATE+8
PAIR_READY=STATE+10
COLD_DISPATCH=[' lda.l $7FFB96',' cmp #$B4B8',' bne NbCold',' jmp NbBegin','NbCold:','.a16','.i16',' lda #0',*[f' sta.l ${at:06X}' for at in (STATE,MODE,PENDING_EPOCH,RESTORES,PAIRS,PAIR_READY)]]


def transform(source):
    a=list(source)
    for name in ('OnlinePreflight:','OnlineComplete:','OnlineVblank:','WarmDirectPair:','AstraOpaqueTile:','.org $C000'):
        if a.count(name)!=1:raise ValueError('NONBLANK_SOURCE_DRIFT:'+name)
    if ' jsr WarmCompare' not in a:raise ValueError('NONBLANK_CONTROL_COMPARE_DRIFT')
    # Keep cold bootstrap and every control routine. Source guards still precede
    # this dispatch. The new warm path never calls WarmCompare or OnlineBlank.
    at=a.index('OnlinePreflight:')+3
    a[at:at]=COLD_DISPATCH
    start=a.index('OnlineComplete:')+3;end=a.index('OnlineVblank:')
    finish=a[start:end]
    assert finish[-2:]==[' sep #$20','.a8']
    finish=finish[:-2]
    lines=['.org $A000','NbBegin:','.a16','.i16']
    def add(*s):lines.extend(s)
    def state(n):add(f' lda #{n}',f' sta.l ${STATE:06X}')
    def copy(src,dst,n):add(' phb',f' lda #{n-1}',f' ldx #{src&65535}',f' ldy #{dst&65535}',f' mvn ${dst>>16:02X},${src>>16:02X}',' plb')
    serial=0
    def fail(op):
        nonlocal serial
        serial+=1;tag='NbGuard'+str(serial)
        add(f' {dict(beq="bne",bne="beq",bcs="bcc",bcc="bcs")[op]} {tag}',' jmp NbAbort',tag+':','.a16','.i16')
    state(1)
    add(' lda.l $7FBA90',f' sta.l ${PENDING_EPOCH:06X}',' lda #0',f' sta.l ${RESTORES:06X}',f' sta.l ${PAIRS:06X}',f' sta.l ${PAIR_READY:06X}')
    copy(0xe18000,0x42c000,2048)
    add(' lda #596',' sta $2E',' lda #0',' sta $18','NbMark:','.a16','.i16',
        ' lda $18',' and #31',' cmp $10',' bcc NbMarkNext',' cmp $12',' bcc NbMarkY',' bne NbMarkNext',
        'NbMarkY:','.a16','.i16',' lda $18',' lsr a',' lsr a',' lsr a',' lsr a',' lsr a',' cmp $14',' bcc NbMarkNext',' cmp $16',' bcc NbMarkTest',' bne NbMarkNext',
        'NbMarkTest:','.a16','.i16',' jsr WarmSourcePresence',' cmp #0',' beq NbMarkNext',' lda $18',' asl a',' tax',' lda #$FFFF',' sta.l $42C000,x',
        'NbMarkNext:','.a16','.i16',' inc $18',' lda $18',' cmp #896',' bcs NbRestorePlanStart',' jmp NbMark',
        'NbRestorePlanStart:','.a16','.i16',' lda #0',' sta $18',
        'NbRestorePlan:','.a16','.i16',' lda $18',' asl a',' tax',' lda.l $42C000,x',' cmp #596',' bcs NbRestorePlanNext',' sta $30',' asl a',' tax',' lda.l $42D000,x',' and #$8000',' beq NbRestorePlanNext',
        f' lda.l ${RESTORES:06X}',' cmp #16')
    fail('bcs')
    add(' jsr NbFree',f' lda.l ${RESTORES:06X}',' asl a',' asl a',' tax',' lda $30',' sta.l $42D620,x',' lda $2C',' sta.l $42D622,x',f' lda.l ${RESTORES:06X}',' inc a',f' sta.l ${RESTORES:06X}',
        ' lda #0',' sta $70','NbReroute:','.a16','.i16',' ldx $70',' lda.l $42C000,x',' cmp $30',' bne NbRerouteNext',' lda $2C',' ora #$4000',' sta.l $42C000,x',
        'NbRerouteNext:','.a16','.i16',' inc $70',' inc $70',' lda $70',' cmp #2048',' bcc NbReroute',
        'NbRestorePlanNext:','.a16','.i16',' inc $18',' lda $18',' cmp #1024',' bcs NbActorPlanStart',' jmp NbRestorePlan',
        'NbActorPlanStart:','.a16','.i16',' lda #0',' sta $18',
        'NbActorPlan:','.a16','.i16',' lda $18',' asl a',' tax',' lda.l $42C000,x',' cmp #$FFFF',' bne NbActorPlanNext',' jsr NbFree',' lda $18',' asl a',' tax',' lda $2C',' ora #$8000',' sta.l $42C000,x',
        'NbActorPlanNext:','.a16','.i16',' inc $18',' lda $18',' cmp #896',' bcc NbActorPlan')
    state(2)
    add(' lda #0',' sta $60','NbRestoreProduce:','.a16','.i16',' lda $60',f' cmp.l ${RESTORES:06X}',' bcs NbActorProduceStart',' asl a',' asl a',' tax',' lda.l $42D622,x',' sta $64',' lda.l $42D620,x',' sta $2C',' jsr WarmCopyBackdrop',' lda $64',' sta $2C',' jsr NbPreloadPair',' inc $60',' jmp NbRestoreProduce',
        'NbActorProduceStart:','.a16','.i16',' lda #0',' sta $18',
        'NbActorProduce:','.a16','.i16',' lda $18',' asl a',' tax',' lda.l $42C000,x',' and #$8000',' beq NbActorProduceNext',' lda.l $42C000,x',' and #$3FFF',' sta $2C',' jsr OnlineRowPointers',' jsl AstraOpaqueTile',' jsr NbPreloadPair',' lda $18',' asl a',' tax',' lda $2C',' sta.l $42C000,x',
        'NbActorProduceNext:','.a16','.i16',' inc $18',' lda $18',' cmp #896',' bcc NbActorProduce')
    # No tag survives READY: actors cleared only after both DMA fences; restore
    # list finishes before actors. Immutable homes never need physical reads.
    add(' lda #0',' sta $70','NbValidate:','.a16','.i16',' ldx $70',' lda.l $42C000,x',' and #$8000')
    fail('bne')
    add(' lda.l $42C000,x',' and #$3FFF',' cmp #768')
    fail('bcs')
    add(' sta.l $42C000,x',' inc $70',' inc $70',' lda $70',' cmp #2048',' bcc NbValidate',f' lda.l ${PENDING_EPOCH:06X}',' cmp.l $7FBA90')
    fail('bne')
    state(3)
    add(f' lda.l ${MODE:06X}')
    fail('bne')
    # Full-map transfer, rather than running a 7ms sparse scan during VBlank.
    # Two contiguous 2048-byte descriptors; actual native budget certification
    # is mandatory. No second map allocation or map-base swap.
    add(' jsr NbFreshVblank')
    state(4)
    add('NbMapCommit:','.a16','.i16',' lda #0',' sta $72',' lda #2048',' sta $74',' lda #$7800',' sta.l $002116',' jsr WarmMapDmaHigh',' lda #$7C00',' sta.l $002116',' jsr WarmMapDmaLow','NbMapsComplete:','.a16','.i16')
    # Producer lock remains held while RAM bookkeeping follows completed map
    # DMA. Neither a new request nor allocator can run until VISIBLE; old refs
    # are retained conservatively until this point. No PPU access in this work.
    copy(0x42c000,0x42c800,2048)
    add(' ldx #0','NbClearRefs:','.a16','.i16',' lda.l $42D000,x',' and #$8000',' sta.l $42D000,x',' inx',' inx',' cpx #1536',' bcc NbClearRefs',
        ' ldy #0','NbPublishRefs:','.a16','.i16',' tya',' tax',' lda.l $42C000,x',' asl a',' tax',' lda.l $42D000,x',' inc a',' sta.l $42D000,x',' iny',' iny',' cpy #2048',' bcc NbPublishRefs',*finish)
    state(0)
    add('NbVisible:','.a16','.i16',' pld',' plb',' ply',' plx',' pla',' plp',' clc',' rtl',
        'NbAbort:','.a16','.i16')
    copy(0x42c800,0x42c000,2048)
    state(0)
    add(' jmp OnlineReject',
        'NbFree:','.a16','.i16',' lda $2E',' cmp #768')
    # NbFree is called with a return address; admission abort must discard it.
    add(' bcc NbFreeCheck',' pla',' jmp NbAbort','NbFreeCheck:','.a16','.i16',' asl a',' tax',' lda.l $42D000,x',' and #$3FFF',' beq NbFreeFound',' inc $2E',' jmp NbFree',
        'NbFreeFound:','.a16','.i16',' lda $2E',' sta $2C',' inc $2E',' rts',
        'NbFreshVblank:','.a16','.i16',' sep #$20','.a8','NbWaitEnd:',' lda.l $004212',' and #$80',' bne NbWaitEnd','NbWaitStart:',' lda.l $004212',' and #$80',' beq NbWaitStart',' rep #$20','.a16','NbWindowStart:',' rts',
        'NbPreloadPair:','.a16','.i16',' lda #0',f' sta.l ${PAIR_READY:06X}',' jsr NbFreshVblank','NbPairBegin:',' jsr WarmDirectPair',' lda #3',f' sta.l ${PAIR_READY:06X}',f' lda.l ${PAIRS:06X}',' inc a',f' sta.l ${PAIRS:06X}','NbPairComplete:',' rts','NbCodeEnd:')
    at=a.index('.org $C000');a[at:at]=lines
    return a
