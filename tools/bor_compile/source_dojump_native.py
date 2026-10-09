"""Readonly dust-absence dojump with mandatory sound and actual toss/frame.

Arguments retain binary32 bits. Execution uses the existing Q16.16 adaptation;
nonzero lift which projects to zero is rejected explicitly. Serialized owner
must retain its input descriptor throughout sound/frame continuations.
"""
from source_engine_function_ids import function_id


def emit(work, pending, profile, symbols):
    if profile.get('capability') != 'READONLY_JUMP_DUST_ABSENCE':
        raise ValueError('DOJUMP_NATIVE_CAPABILITY')
    count = len(profile['models'])
    if not 1 <= count <= 16 or any(m['id'] != i or m['dust_jump_start'] != -1 for i, m in enumerate(profile['models'])):
        raise ValueError('DOJUMP_NATIVE_MODELS')
    if not 0 <= work <= 0xffffff-79 or work < pending+64 and pending < work+80:
        raise ValueError('DOJUMP_NATIVE_LAYOUT')
    action = function_id('common_jump')
    lines = []
    serial = 0
    def put(s): lines.extend(s.strip().splitlines())
    def label(n): put('DoJump_'+n+':\n.a16\n.i16')
    def branch(op, n='Bad'):
        nonlocal serial
        serial += 1
        skip = 'DoJump_Skip'+str(serial)
        put(' '+dict(beq='bne', bne='beq', bcc='bcs', bcs='bcc')[op]+' '+skip+'\n jmp DoJump_'+n+'\n'+skip+':\n.a16\n.i16')
    def entry(n):
        label(n); put(f' php\n rep #$39\n phx\n phy\n lda.l {work}\n cmp #$B693'); branch('bne')
    def offset(dest, stride):
        put(' lda #0')
        for bit in range(stride.bit_length()-1, -1, -1):
            put(' asl a')
            if stride & (1 << bit): put(f' clc\n adc.l {work}+4')
        put(f' sta.l {work}+{dest}')
    def project(source, dest):
        for at, name in ((0,'Lo'),(2,'Hi')):
            put(f' lda.l {work}+{source+at}\n sta.l {symbols["SourceModelEntityCopy4086_"+name]}')
        put(f' jsl {symbols["SourceModelSpeed4086_ProjectQ16"]}'); branch('bcs')
        for at, name in ((0,'Lo'),(2,'Hi')):
            put(f' lda.l {symbols["SourceModelEntityCopy4086_"+name]}\n sta.l {work}+{dest+at}')
    entry('Begin'); put(f' lda.l {work}+2'); branch('beq','Ready'); put(' cmp #2'); branch('bne')
    label('Ready'); put(f' lda #1\n sta.l {work}+2\n jsl DoJump_Bind'); branch('bcs')
    # Snapshot call arguments before the sound callback. These are C by-value.
    for at in range(4,24,2): put(f' lda.l {work}+{at}\n sta.l {work}+{at+44}')
    project(8,36); project(12,40); project(16,44)
    put(f' lda.l {work}+36\n ora.l {work}+38'); branch('bne','LiftValid')
    put(f' lda.l {work}+10\n and #$7FFF\n ora.l {work}+8'); branch('bne')
    label('LiftValid'); put(f' lda.l {work}+30\n tax\n lda #{action}\n sta.l $43900C,x\n lda #0\n sta.l $43900E,x\n sta.l {work}+24\n lda.l {work}+22\n and #$8000'); branch('bne','Body')
    put(f' lda #3\n sta.l {work}+2\n lda #$8001\n jmp DoJump_Exit')
    entry('FinishSound'); put(f' lda.l {work}+2\n cmp #3'); branch('bne')
    put(f' lda.l {work}+24\n cmp #1'); branch('beq','SoundDone'); put(' cmp #2'); branch('bne')
    label('SoundDone'); put(' jsl DoJump_CheckDescriptor'); branch('bcs'); put(' jsl DoJump_Bind'); branch('bcs')
    label('Body'); put(f' lda #1\n sta.l {work}+2')
    # The actual current model was freshly validated by Bind. Every admitted
    # readonly model has source jump dust -1; no spawn acknowledgement exists.
    put(f' lda.l {work}+32\n tax\n lda #1\n sta.l $43EB08,x\n lda #0\n sta.l $43EB0A,x\n sta.l $43EB00,x\n sta.l $43EB02,x')
    put(f' lda #$B624\n sta.l {symbols["SourceEntityToss4086_Ready"]}\n lda #0\n sta.l {symbols["SourceEntityToss4086_Status"]}\n lda.l {work}+4\n sta.l {symbols["SourceEntityToss4086_Slot"]}')
    for at in (0,2): put(f' lda.l {work}+{36+at}\n sta.l {symbols["SourceEntityToss4086_Lift"]}+{at}')
    label('BeforeToss'); put(f' jsl {symbols["SourceEntityToss4086_Execute"]}'); branch('bcs')
    put(f' lda.l {symbols["SourceEntityToss4086_Status"]}\n cmp #2'); branch('bne')
    # Fresh direction after toss; exactly LEFT=0, any other int selects right.
    label('BeforeDirection'); put(f' lda.l {work}+26\n tax\n lda.l $41401C,x\n ora.l $41401E,x'); branch('bne','VelocityRight')
    put(f' lda #0\n sec\n sbc.l {work}+40\n sta.l {work}+40\n lda #0\n sbc.l {work}+42\n sta.l {work}+42')
    label('VelocityRight'); put(f' lda.l {work}+28\n tax')
    for src, dest in ((40,36),(42,38),(44,40),(46,42)): put(f' lda.l {work}+{src}\n sta.l $416800+{dest},x')
    put(f' lda.l {work}+4\n sta.l {symbols["SourceAnimationInit4086_Slot"]}\n lda.l {work}+6\n sta.l {symbols["SourceAnimationInit4086_Number"]}\n lda #0\n sta.l {symbols["SourceAnimationInit4086_Reset"]}')
    label('BeforeAnimation'); put(f' jsl {symbols["SourceAnimationInit4086_Begin"]}'); branch('bcs')
    put(f' lda.l {symbols["SourceAnimationInit4086_State"]}\n cmp #2'); branch('beq','Done'); put(' cmp #1'); branch('bne')
    put(f' lda #4\n sta.l {work}+2\n lda #$8002\n jmp DoJump_Exit')
    entry('FinishFrame'); put(f' lda.l {work}+2\n cmp #4'); branch('bne')
    put(' jsl DoJump_CheckDescriptor'); branch('bcs')
    for name, at in (('Slot',4),('Number',6)):
        put(f' lda.l {symbols["SourceAnimationInit4086_"+name]}\n cmp.l {work}+{at}'); branch('bne')
    put(f' jsl {symbols["SourceAnimationInit4086_Ack"]}'); branch('bcs')
    label('Done'); put(f' lda #2\n sta.l {work}+2\n lda #0')
    label('Exit'); put(' ply\n plx\n plp\n clc\n rtl')
    label('Bad'); put(f' lda #5\n sta.l {work}+2\n ply\n plx\n plp\n sec\n rtl')
    label('CheckDescriptor')
    for at in range(4,24,2):
        put(f' lda.l {work}+{at}\n cmp.l {work}+{at+44}'); branch('bne','BindBad')
    put(' clc\n rtl')
    label('Bind'); put(f' lda.l {work}+4\n cmp #128'); branch('bcs','BindBad')
    offset(26,80); offset(28,64); offset(30,80); offset(32,32)
    put(f' lda.l {symbols["SourceModelEntityCopy4086_Models"]}\n cmp #{count}'); branch('bne','BindBad')
    put(f' lda.l {work}+28\n tax\n lda.l $416800,x\n cmp #{count}'); branch('bcs','BindBad')
    put(f' sta.l {pending}+6\n lda.l {work}+4\n sta.l {pending}+4\n jsl PendingJump_Read'); branch('bcs','BindBad')
    put(f' lda.l {symbols["SourceLifecycle4086_Ready"]}\n cmp #$B4FB'); branch('bne','BindBad')
    put(f' lda.l {work}+30\n tax\n lda.l $43904A,x\n cmp #$B4FB'); branch('bne','BindBad')
    put(f' lda.l $439048,x\n cmp.l {pending}+6'); branch('bne','BindBad')
    put(f' lda.l {work}+26\n tax\n lda.l $414018,x\n cmp #1'); branch('bne','BindBad')
    put(' lda.l $41401A,x'); branch('bne','BindBad'); put(' clc\n rtl')
    label('BindBad'); put(' sec\n rtl')
    return '\n'.join(lines)+'\n'
