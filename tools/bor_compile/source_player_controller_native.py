"""Complete the admitted player prefix with running cancellation and ground.

Uses the existing 32-byte prefix control block and existing ground owners.
Level/Z/facing context is supplied by the source world caller. Live item/grab
states still require their complete owners; their existing explicit faults are
retained. All mandatory frames, sound and targets remain external continuations.
"""


def emit(work,run_binding,ground_services,ground,binding,directional,history,input_owner,input_magic,symbols):
    spans=((work,32),(run_binding,32),(ground_services,32),(ground,128),(binding,32),(directional,64),(history,1024),(input_owner,2))
    for i,(a,n)in enumerate(spans):
        if not 0<=a<=0x1000000-n or any(a<b+m and b<a+n for b,m in spans[i+1:]):raise ValueError('PLAYER_CONTROLLER_LAYOUT')
    if history&255 or not 1<=input_magic<=65535:raise ValueError('PLAYER_CONTROLLER_INPUT')
    lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('PlayerController_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;skip='PlayerController_Skip'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+skip+'\n jmp PlayerController_'+n+'\n'+skip+':\n.a16\n.i16')
    def entry(n):label(n);put(f' php\n rep #$39\n phx\n phy\n lda.l {work}\n cmp #$B688');branch('bne')
    entry('Begin');put(' jsl PlayerEarly_Begin');branch('bcs');put(' jmp PlayerController_PrefixResult')
    entry('FinishFrame');put(f' lda.l {work}+2\n cmp #3');branch('bne')
    put(f' lda.l {work}+16\n cmp #9');branch('beq','GroundFinish')
    put(' jsl PlayerEarly_FinishFrame');branch('bcs');put(' jmp PlayerController_PrefixResult')
    for name,target in (('FinishSound','PlayerEarly_FinishSound'),('ResumeTarget','PlayerEarly_ResumeTarget')):
        entry(name);put(f' jsl {target}');branch('bcs');put(' jmp PlayerController_PrefixResult')
    label('PrefixResult');put(f' lda.l {work}+2\n cmp #2');branch('beq','Tail')
    put(f' cmp #4');branch('beq','Done');put(' cmp #3');branch('beq','FramePending');put(' cmp #7');branch('beq','SoundPending');put(' cmp #8');branch('beq','TargetPending');put(' cmp #9');branch('beq','DoJumpPending');put(' jmp PlayerController_Bad')
    label('Tail');put(f' lda.l {input_owner}\n cmp #{input_magic}');branch('bne')
    put(f' lda.l {symbols["SourceClock4086_Ready"]}\n cmp #$B4C5');branch('bne')
    put(f' lda.l {run_binding}\n cmp #$B681');branch('bne')
    put(f' lda.l {run_binding}+2');branch('beq','RunEntry');put(' cmp #2');branch('bne')
    label('RunEntry');put(f' lda.l {work}+4\n sta.l {run_binding}+4\n sta.l {binding}+4\n lda.l {work}+6\n cmp #4');branch('bcs')
    put(f' sta.l {run_binding}+6\n xba\n tax\n lda.l {history}+216,x\n sta.l {ground}+16\n lda.l {history}+218,x\n sta.l {ground}+18')
    for at in (0,2):put(f' lda.l {work}+{8+at}\n sta.l {run_binding}+{8+at}')
    put(f' lda #1\n sta.l {run_binding}+2\n jsl SourceRunBinding_Cancel');branch('bcs')
    # This is the original entry-cached air predicate, not a new measurement.
    put(f' lda.l {directional}+8\n sta.l {ground}+22\n lda.l {symbols["SourceClock4086_TimeLo"]}\n sta.l {ground}+40\n lda.l {symbols["SourceClock4086_TimeHi"]}\n sta.l {ground}+42\n lda #9\n sta.l {work}+16\n jsl GroundServices_Begin');branch('bcs')
    label('GroundResult');put(f' lda.l {ground_services}+2\n cmp #2');branch('beq','Complete');put(' cmp #3');branch('bne')
    put(f' lda.l {symbols["SourceAnimationInit4086_Number"]}\n sta.l {work}+28\n lda.l {work}+6\n sta.l {work}+30\n jmp PlayerController_FramePending')
    label('GroundFinish');put(f' lda.l {binding}+4\n cmp.l {work}+4');branch('bne')
    put(f' lda.l {ground_services}+2\n cmp #3');branch('bne')
    put(f' lda.l {symbols["SourceAnimationInit4086_Slot"]}\n cmp.l {work}+4');branch('bne')
    put(f' lda.l {symbols["SourceAnimationInit4086_Number"]}\n cmp.l {work}+28');branch('bne')
    put(f' lda.l {work}+6\n cmp.l {work}+30');branch('bne')
    put(' jsl GroundServices_FinishFrame');branch('bcs');put(' jmp PlayerController_GroundResult')
    label('Complete');put(f' lda #4\n sta.l {work}+2')
    label('Done');put(' lda #0\n jmp PlayerController_Exit')
    for name,result in (('FramePending',1),('SoundPending',0x8001),('TargetPending',0x8002),('DoJumpPending',0x8003)):
        label(name)
        if name=='FramePending':put(f' lda #3\n sta.l {work}+2')
        put(f' lda #{result}\n jmp PlayerController_Exit')
    label('Exit');put(' ply\n plx\n plp\n clc\n rtl')
    label('Bad');put(f' lda #5\n sta.l {work}+2\n ply\n plx\n plp\n sec\n rtl')
    return '\n'.join(lines)+'\n'
