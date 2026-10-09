"""Actual special energy, linked idle and frame services for a closed profile."""


def emit(work,special,binding,energy,role,block,symbols):
    extents=((work,32),(special,192),(binding,64),(energy,64))
    for i,(a,n)in enumerate(extents):
        if not 0<=a<=0x1000000-n:raise ValueError('SPECIAL_SERVICES_EXTENT')
        if any(a<b+m and b<a+n for b,m in extents[i+1:]):raise ValueError('SPECIAL_SERVICES_OVERLAP')
    lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('SpecialServices_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;skip='SpecialServices_Skip'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+skip+'\n jmp SpecialServices_'+n+'\n'+skip+':\n.a16\n.i16')
    for entry in ('Begin','FinishFrame'):
        label(entry);put(f' php\n rep #$39\n phx\n phy\n lda.l {work}\n cmp #$B685');branch('bne')
        if entry=='Begin':
            put(f' lda.l {work}+2');branch('beq','BeginReady')
            put(' cmp #2');branch('beq','BeginReady');put(' cmp #4');branch('bne')
            label('BeginReady');put(' jsl SpecialBinding_Capture');branch('bcs')
            put(' jsl SourceSpecial_Begin');branch('bcs');put(' jmp SpecialServices_Drive')
        else:
            put(f' lda.l {work}+2\n cmp #3');branch('bne')
            put(f' jsl {symbols["SourceAnimationInit4086_Ack"]}');branch('bcs')
            put(' jmp SpecialServices_ServiceReturned')
    label('Drive');put(f' lda #1\n sta.l {work}+2\n lda.l {special}+2\n cmp #2');branch('beq','False')
    put(' cmp #5');branch('beq','Complete');put(' cmp #3');branch('beq','Query');put(' cmp #4');branch('bne')
    put(f' lda.l {special}+6\n cmp #1');branch('beq','LinkedIdle')
    put(' cmp #3');branch('bne')  # smartbomb is a mandatory unbound service.
    put(' jsl SpecialBinding_Publish');branch('bcs')
    put(f' lda.l {binding}+4\n sta.l {symbols["SourceAnimationInit4086_Slot"]}\n lda #{role}\n sta.l {symbols["SourceAnimationInit4086_Number"]}\n lda #0\n sta.l {symbols["SourceAnimationInit4086_Reset"]}\n jsl {symbols["SourceAnimationInit4086_Begin"]}');branch('bcs')
    put(' jmp SpecialServices_AnimationResult')
    label('LinkedIdle')
    # Validate the captured peer before publishing the unlink prefix.
    put(f' lda.l {binding}+6\n cmp #65535');branch('beq')
    put(f' sta.l {symbols["SourceIdle4086_Slot"]}\n lda.l {symbols["SourceIdle4086_Ready"]}\n cmp #$B4F3');branch('bne')
    put(' jsl SpecialBinding_Publish');branch('bcs')
    put(f' jsl {symbols["SourceSetIdle4086_Begin"]}');branch('bcs')
    label('AnimationResult');put(f' lda.l {symbols["SourceAnimationInit4086_State"]}\n cmp #1');branch('beq','Pending')
    put(' cmp #2');branch('bne');put(' jmp SpecialServices_ServiceReturned')
    label('Pending');put(f' lda #3\n sta.l {work}+2\n lda #1\n ply\n plx\n plp\n clc\n rtl')
    label('ServiceReturned');put(' jsl SpecialBinding_Capture');branch('bcs');put(' jmp SpecialServices_Acknowledge')
    label('Query');put(f' lda.l {special}+12\n cmp #2');branch('beq','Block')
    put(' cmp #2');branch('bcs')
    put(f' sta.l {energy}+58\n lda.l {binding}+4\n sta.l {energy}+4\n lda #{role}\n sta.l {energy}+6\n jsl SourceSingleEnergy_Query');branch('bcs')
    put(f' sta.l {special}+16\n jmp SpecialServices_Acknowledge')
    label('Block');put(f' lda.l {binding}+4\n sta.l {symbols["SourceAnimationInit4086_Slot"]}\n lda #{block}\n sta.l {symbols["SourceAnimationInit4086_Number"]}\n jsl {symbols["SourceAnimationInit4086_Resolve"]}');branch('bcs')
    put(f' lda #0\n sta.l {special}+16\n lda.l {symbols["SourceAnimationInit4086_Handle"]}');branch('beq','Acknowledge')
    put(f' lda.l {symbols["SourceAnimationInit4086_Count"]}');branch('beq','Acknowledge');put(f' lda #1\n sta.l {special}+16')
    label('Acknowledge');put(f' lda #$B683\n sta.l {special}+8\n lda.l {special}+6\n sta.l {special}+10\n lda.l {special}+12\n sta.l {special}+14\n jsl SourceSpecial_Resume');branch('bcs');put(' jmp SpecialServices_Drive')
    label('Complete');put(' jsl SpecialBinding_Publish');branch('bcs');put(f' lda #4\n sta.l {work}+2\n jmp SpecialServices_Return')
    label('False');put(f' lda #2\n sta.l {work}+2')
    label('Return');put(' lda #0\n ply\n plx\n plp\n clc\n rtl')
    label('Bad');put(f' lda #5\n sta.l {work}+2\n ply\n plx\n plp\n sec\n rtl')
    return '\n'.join(lines)+'\n'
