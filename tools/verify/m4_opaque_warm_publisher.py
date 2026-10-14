"""Persistent paired residency under forced blank, without a global content scan.

Backdrop identities have immutable home slots. Refcount bit 15 says that the
physical home was overwritten; bit 14 identifies pending actor slots. Affected
old/new coverage is removed/added incrementally. Exact actor reuse compares the
80 native-produced bytes to physical VRAM, never an unchecked hash. Scratch
uses the old committed map only after sparse map DMA, then restores it at commit.
"""
import numpy as np

MAP=0x42c000
COMMITTED=0x42c800
REF=0x42d000
OLD=0x42d6e2


def apply(lines,rom,authority,sy,assets):
    baseline=np.frombuffer((assets/'0-high.map').read_bytes(),dtype='<u2')
    counts=np.bincount(baseline,minlength=768).astype('<u2').tobytes()
    if any(rom[0x343000:0x343600]):raise ValueError('WARM_REFCOUNT_ROM_LEASE')
    rom[0x343000:0x343600]=counts
    def replace(start,end,new):
        a=lines.index(start);b=lines.index(end,a);lines[a:b]=new
    def insert(label,new):
        at=lines.index(label);lines[at:at]=new
    def block(src,dest,n):
        return [' phb',f' lda #{n-1}',f' ldx #{src&65535}',f' ldy #{dest&65535}',f' mvn ${dest>>16:02X},${src>>16:02X}',' plb']
    serial=0
    def jump(op,target):
        nonlocal serial
        serial+=1;s=f'WarmSkip{serial}'
        return [f' {dict(beq="bne",bne="beq",bcc="bcs",bcs="bcc")[op]} {s}',f' jmp {target}',s+':','.a16','.i16']
    pre=['OnlinePreflight:','.a16','.i16',' lda.l $7FFB96',' cmp #$B4B8',' beq WarmHaveCommitted',
         *block(0xe18000,COMMITTED,2048),*block(0xf43000,REF,1536)]
    for i,dp in enumerate((0x10,0x12,0x14,0x16)):pre +=[f' lda ${dp:02X}',f' sta.l {OLD+i*2}']
    pre+=['WarmHaveCommitted:','.a16','.i16',*block(COMMITTED,MAP,2048)]
    # Union rectangle worklist; each reference is removed exactly once. Current
    # actor coverage is tested only within its new rectangle. Outside the union,
    # committed references and tile storage remain untouched.
    for i,(dp,dst,choose) in enumerate(((0x10,0x78,'bcc'),(0x12,0x7a,'bcs'),(0x14,0x7c,'bcc'),(0x16,0x7e,'bcs'))):
        tag=f'WarmUnion{i}'
        pre +=[f' lda ${dp:02X}',f' cmp.l {OLD+i*2}',f' {choose} {tag}',f' lda.l {OLD+i*2}',tag+':','.a16','.i16',f' sta ${dst:02X}']
    pre+=[' lda $7C',' asl a',' asl a',' asl a',' asl a',' asl a',' clc',' adc $78',' sta $18',
          ' lda #0',' sta $3A','OnlineWorklist:','.a16','.i16',' lda $18',' asl a',' tax',f' lda.l {COMMITTED},x',' asl a',' tax',
          f' lda.l {REF},x',' and #$BFFF',' dec a',f' sta.l {REF},x',
          ' lda $18',' and #31',' cmp $10',*jump('bcc','WarmBackground'),' cmp $12',*jump('bcc','WarmTestY'),*jump('bne','WarmBackground'),
          'WarmTestY:','.a16','.i16',' lda $18',' lsr a',' lsr a',' lsr a',' lsr a',' lsr a',' cmp $14',*jump('bcc','WarmBackground'),
          ' cmp $16',*jump('bcc','WarmTestCoverage'),*jump('bne','WarmBackground'),
          'WarmTestCoverage:','.a16','.i16',' jsr OnlineCoverage',' cmp #0',*jump('beq','WarmBackground'),
          ' inc $3A',' lda $18',' asl a',' tax',' lda #$FFFF',f' sta.l {MAP},x',' jmp WarmWorkNext',
          'WarmBackground:','.a16','.i16',' lda $18',' asl a',' tax',' lda.l $E18000,x',f' sta.l {MAP},x',' asl a',' tax',
          f' lda.l {REF},x',' inc a',f' sta.l {REF},x',
          'WarmWorkNext:','.a16','.i16',' jsr WarmAdvance',*jump('bcc','OnlineWorklist'),
          'OnlineAllocationStart:','.a16','.i16',' lda $7C',' asl a',' asl a',' asl a',' asl a',' asl a',' clc',' adc $78',' sta $18',
          ' lda #0',' sta $2E','OnlineAllocate:','.a16','.i16',' lda $18',' asl a',' tax',f' lda.l {MAP},x',' cmp #$FFFF',*jump('bne','WarmAllocateNext'),
          'OnlineFindFree:','.a16','.i16',' lda $2E',' cmp #768',*jump('bcs','OnlineReject'),' asl a',' tax',f' lda.l {REF},x',' and #$3FFF',*jump('beq','WarmFree'),
          ' inc $2E',' jmp OnlineFindFree','WarmFree:','.a16','.i16',f' lda.l {REF},x',' and #$8000',' ora #$4001',f' sta.l {REF},x',
          ' lda $18',' asl a',' tax',' lda $2E',f' sta.l {MAP},x',' inc $2E',
          'WarmAllocateNext:','.a16','.i16',' jsr WarmAdvance',' bcs WarmAllocationDone',' jmp OnlineAllocate',
          'WarmAllocationDone:','.a16','.i16']
    replace('OnlinePreflight:','OnlineBlank:',pre)
    # The compiler bootstrap is cold-only. Every warm field retains CGRAM and
    # unchanged physical CHR. Old references retire only at forced blank.
    blank=lines.index('OnlineBlank:');first_db=next(i for i in range(blank,len(lines))if lines[i].startswith(' .db '))
    end_db=first_db
    while lines[end_db].startswith(' .db '):end_db+=1
    lines[first_db:first_db]=[' rep #$20','.a16',' lda.l $7FFB96',' cmp #$B4B8',' bne WarmColdBootstrap',' jmp WarmBootstrapDone',
        'WarmColdBootstrap:','.a16','.i16',' sep #$20','.a8']
    end_db=next(i for i in range(first_db,len(lines)) if lines[i].startswith(' .db '))
    while lines[end_db].startswith(' .db '):end_db+=1
    lines[end_db:end_db]=['WarmBootstrapDone:','.a16','.i16',' rep #$20',' jsr WarmSparseMaps',' lda #0',' sta $60',
        ' lda $7C',' asl a',' asl a',' asl a',' asl a',' asl a',' clc',' adc $78',' sta $18','WarmRestore:','.a16','.i16',
        ' lda $18',' asl a',' tax',f' lda.l {MAP},x',' sta $2C',' asl a',' tax',f' lda.l {REF},x',' and #$C000',' cmp #$8000',' bne WarmRestoreNext',
        ' jsr WarmCopyBackdrop',' jsr WarmStage',' lda $2C',' asl a',' tax',f' lda.l {REF},x',' and #$3FFF',f' sta.l {REF},x',
        'WarmRestoreNext:','.a16','.i16',' jsr WarmAdvance',' bcc WarmRestore',' jsr WarmFlush']
    # Reuse the existing current-rectangle iteration; no duplicate coverage scan.
    a=lines.index('OnlineTile:');b=lines.index('OnlineComposeTile:',a)
    lines[a:b]=['OnlineTile:','.a16','.i16',' lda $18',' asl a',' tax',f' lda.l {MAP},x',' asl a',' tax',
        f' lda.l {REF},x',' and #$4000',' bne OnlineComposeTile',' jmp OnlineTileNext']
    # Generated pair is compared to the ACTUAL physical selected slot. Then
    # consecutive uploads are staged in groups of at most sixteen tile pairs.
    replace('OnlineTransfer:','OnlineTileNext:',['OnlineTransfer:','.a16','.i16',' jsr WarmCompare',' bcc WarmReuse',
        ' jsr WarmStage',' lda $2C',' asl a',' tax',f' lda.l {REF},x',' ora #$8000',f' sta.l {REF},x',
        'WarmReuse:','.a16','.i16'])
    replace('OnlineMapsTransfer:','OnlineComplete:',['OnlineMapsTransfer:','.a16','.i16',' jsr WarmFlush',*block(MAP,COMMITTED,2048)])
    at=lines.index('OnlineComplete:')+3
    lines[at:at]=[s for i,dp in enumerate((0x10,0x12,0x14,0x16)) for s in (f' lda ${dp:02X}',f' sta.l {OLD+i*2}')]
    at=lines.index('OnlineNoop:')+3;lines[at:at]=[' lda #0',' sta $3A']
    routines=['.org $D000',
        'WarmAdvance:','.a16','.i16',' lda $18',' and #31',' cmp $7A',' bcs WarmNextRow',' inc $18',' clc',' rts',
        'WarmNextRow:','.a16','.i16',' lda $18',' lsr a',' lsr a',' lsr a',' lsr a',' lsr a',' cmp $7E',' bcs WarmEnd',
        ' lda $18',' and #$FFE0',' clc',' adc #32',' adc $78',' sta $18',' clc',' rts','WarmEnd:','.a16','.i16',' sec',' rts',
        'WarmCopyBackdrop:','.a16','.i16',' lda $2C',' asl a',' asl a',' asl a',' asl a',' asl a',' asl a',' tax',' ldy #$D680',' phb',' lda #63',' mvn $42,$E0',' plb',
        ' lda $2C',' asl a',' asl a',' asl a',' asl a',' tax',' ldy #$D6C0',' phb',' lda #15',' mvn $42,$E1',' plb',' rts',
        'WarmStage:','.a16','.i16',' lda $60',' beq WarmStageStart',' cmp #16',' bcs WarmStageFlush',
        ' lda $64',' inc a',' cmp $2C',' beq WarmStageCopy','WarmStageFlush:','.a16','.i16',' jsr WarmFlush',
        'WarmStageStart:','.a16','.i16',' lda $2C',' sta $62',
        'WarmStageCopy:','.a16','.i16',' lda $2C',' sta $64',' lda $60',' asl a',' asl a',' asl a',' asl a',' asl a',' asl a',' clc',' adc #$C800',' tay',
        ' phb',' lda #63',' ldx #$D680',' mvn $42,$42',' plb',
        ' lda $60',' asl a',' asl a',' asl a',' asl a',' clc',' adc #$CC00',' tay',' phb',' lda #15',' ldx #$D6C0',' mvn $42,$42',' plb',
        ' inc $60',' rts','WarmFlush:','.a16','.i16',' lda $60',' bne WarmFlushRun',' rts','WarmFlushRun:','.a16','.i16',
        ' lda $62',' asl a',' asl a',' asl a',' asl a',' asl a',' sta.l $002116',
        ' lda $60',' asl a',' asl a',' asl a',' asl a',' asl a',' asl a',' sta.l $004375',' sep #$20','.a8']
    def dma_setup(addr,done):
        return [s for reg,value in ((0x4370,1),(0x4371,0x18),(0x4372,addr&255),(0x4373,addr>>8),(0x4374,0x42),(0x420b,128))for s in(f' lda #{value}',f' sta.l ${reg:06X}')]+[done+':',' rep #$20','.a16']
    routines+=dma_setup(0xc800,'OnlineDmaDone5')
    routines+=[' lda $62',' asl a',' asl a',' asl a',' clc',' adc #$6000',' sta.l $002116',' lda $60',' asl a',' asl a',' asl a',' asl a',' sta.l $004375',' sep #$20','.a8']
    routines+=dma_setup(0xcc00,'OnlineDmaDone6')
    routines+=[' lda #0',' sta $60',' rts',
        'WarmCompare:','.a16','.i16',' lda $2C',' asl a',' asl a',' asl a',' asl a',' asl a',' sta.l $002116',' lda.l $002139',' ldx #0',
        'WarmCompareHigh:','.a16','.i16',' lda.l $002139',' cmp.l $42D680,x',' bne WarmDifferent',' inx',' inx',' cpx #64',' bcc WarmCompareHigh',
        ' lda $2C',' asl a',' asl a',' asl a',' clc',' adc #$6000',' sta.l $002116',' lda.l $002139',' ldx #0',
        'WarmCompareLow:','.a16','.i16',' lda.l $002139',' cmp.l $42D6C0,x',' bne WarmDifferent',' inx',' inx',' cpx #16',' bcc WarmCompareLow',' clc',' rts',
        'WarmDifferent:','.a16','.i16',' sec',' rts',
        'WarmSparseMaps:','.a16','.i16',' lda #0',' sta $70','WarmMapFind:','.a16','.i16',' ldx $70',f' lda.l {MAP},x',f' cmp.l {COMMITTED},x',' bne WarmMapStart',
        ' inx',' inx',' stx $70',' cpx #2048',' bcc WarmMapFind',' rts',
        'WarmMapStart:','.a16','.i16',' stx $72','WarmMapExtend:','.a16','.i16',' inx',' inx',' stx $70',' cpx #2048',' bcs WarmMapSend',f' lda.l {MAP},x',f' cmp.l {COMMITTED},x',' bne WarmMapExtend',
        'WarmMapSend:','.a16','.i16',' lda $70',' sec',' sbc $72',' sta $74',' lda $72',' lsr a',' clc',' adc #$7800',' sta.l $002116',' jsr WarmMapDmaHigh',
        ' lda $72',' lsr a',' clc',' adc #$7C00',' sta.l $002116',' jsr WarmMapDmaLow',' lda $70',' cmp #2048',' bcc WarmMapFind',' rts',
        'WarmMapDmaHigh:','WarmMapDmaLow:','.a16','.i16',' lda $72',' clc',' adc #$C000',' sta.l $004372',' lda $74',' sta.l $004375',
        ' sep #$20','.a8',' lda #1',' sta.l $004370',' lda #$18',' sta.l $004371',' lda #$42',' sta.l $004374',' lda #128',' sta.l $00420B',
        'OnlineDmaDone7:',' rep #$20','.a16',' rts']
    insert('.org $E000',routines)
    return lines
