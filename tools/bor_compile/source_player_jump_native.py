"""Real default jump attack for a derived zero-air-control source capability.

No-air-cancel must be zero in this closed lane. Other profiles/controls reject
explicitly. The caller must run the actual frame owner before FinishFrame.
"""
from source_player_run_4086 import KEYS


def emit(work,history,input_owner,input_magic,profile,roles,symbols):
    spans=((work,32),(history,1024),(input_owner,2))
    for i,(a,n)in enumerate(spans):
        if not 0<=a<=0x1000000-n:raise ValueError('PLAYER_JUMP_EXTENT')
        if any(a<b+m and b<a+n for b,m in spans[i+1:]):raise ValueError('PLAYER_JUMP_OVERLAP')
    if history&255 or not 1<=input_magic<=65535 or profile['capability']!='READONLY_ZERO_AIR_CONTROL_DEFAULT_ATTACK':raise ValueError('PLAYER_JUMP_CAPABILITY')
    if any(any(m['fields'].values())for m in profile['models']):raise ValueError('PLAYER_JUMP_CAPABILITY_FLAGS')
    count=len(profile['models'])
    if not 1<=count<=16 or any(m['id']!=i for i,m in enumerate(profile['models'])):raise ValueError('PLAYER_JUMP_MODEL_ORDER')
    lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('PlayerJump_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;skip='PlayerJump_Skip'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+skip+'\n jmp PlayerJump_'+n+'\n'+skip+':\n.a16\n.i16')
    def offset(dest,stride):
        put(' lda #0')
        for bit in range(stride.bit_length()-1,-1,-1):
            put(' asl a')
            if stride&(1<<bit):put(f' clc\n adc.l {work}+4')
        put(f' sta.l {work}+{dest}')
    def resolve(role):
        put(f' lda.l {work}+4\n sta.l {symbols["SourceAnimationInit4086_Slot"]}\n lda #{roles[role]}\n sta.l {symbols["SourceAnimationInit4086_Number"]}')
        label('Query_'+role);put(f' jsl {symbols["SourceAnimationInit4086_Resolve"]}');branch('bcs')
    def absent(role):
        resolve(role)
        put(f' lda.l {symbols["SourceAnimationInit4086_Handle"]}');branch('beq','Absent'+role)
        put(f' lda.l {symbols["SourceAnimationInit4086_Count"]}');branch('bne')
        label('Absent'+role)
    label('Begin');put(' php\n rep #$39\n phx\n phy')
    for address,magic in ((work,0xb68a),(input_owner,input_magic),(symbols['VmSourceWorld_Ready'],0xb4a3),(symbols['VmSourceWorld_PoolBase'],0x4000),(symbols['SourceModelEntityCopy4086_Ready'],0xb4eb)):
        put(f' lda.l {address}\n cmp #{magic}');branch('bne')
    put(f' lda.l {work}+2');branch('beq','Ready');put(' cmp #2');branch('bne')
    label('Ready');put(f' lda #1\n sta.l {work}+2\n lda.l {work}+8\n ora.l {work}+10');branch('bne')
    put(f' lda.l {symbols["VmSourceWorld_Count"]}');branch('beq');put(' cmp #129');branch('bcs')
    put(f' cmp.l {symbols["SourceModelEntityCopy4086_Entities"]}');branch('bne')
    put(f' lda.l {symbols["SourceModelEntityCopy4086_Models"]}\n cmp #{count}');branch('bne')
    put(f' lda.l {work}+4\n cmp.l {symbols["VmSourceWorld_Count"]}');branch('bcs')
    for dest,stride in ((20,80),(22,96),(24,64),(28,24)):offset(dest,stride)
    put(f' lda.l {work}+24\n tax\n lda.l $416800,x\n cmp #{count}');branch('bcs')
    put(f' lda.l {work}+20\n tax\n clc\n adc #$4000\n cmp.l $414000,x');branch('bne')
    put(' lda.l $414002,x\n cmp #$41');branch('bne')
    put(' lda.l $414028,x\n cmp #1');branch('bne')
    put(' lda.l $41402A,x\n ora.l $41402E,x');branch('bne')
    put(' lda.l $41402C,x\n cmp #4');branch('bcs');put(f' sta.l {work}+6')
    put(f' lda.l {work}+12\n ora.l {work}+14');branch('beq','SpecialKey')
    put(f' lda.l {work}+14');branch('bne','AttackKey')
    put(f' lda.l {work}+12\n cmp #3');branch('bne','AttackKey')
    label('SpecialKey');put(f' lda.l {work}+6\n xba\n tax\n lda.l {history}+224,x\n and #{KEYS["special"]}');branch('beq','AttackKey')
    absent('jumpspecial');put(' jmp PlayerJump_Done')
    label('AttackKey');put(f' lda.l {work}+6\n xba\n tax\n lda.l {history}+224,x\n and #{KEYS["attack"]}');branch('beq','Done')
    put(f' lda.l {history}+224,x\n and #{(~KEYS["attack"])&65535}\n sta.l {history}+224,x')
    put(f' lda.l {work}+22\n tax\n lda #1\n sta.l $40C058,x\n lda #0\n sta.l $40C05A,x')
    for name,mask in (('jumpattack2',KEYS['movedown']),('jumpattack3',KEYS['moveup'])):
        put(f' lda.l {work}+6\n xba\n tax\n lda.l {history}+216,x\n and #{mask}');branch('beq','Skip'+name)
        absent(name);label('Skip'+name)
    put(f' lda.l {work}+28\n tax\n lda.l $42F404,x\n ora.l $42F406,x');branch('beq','SkipRun')
    absent('runjumpattack');label('SkipRun')
    put(f' lda.l {work}+24\n tax\n lda.l $416824,x\n ora.l $416826,x');branch('beq','SkipForward')
    absent('jumpforward');label('SkipForward')
    resolve('jumpattack');put(f' lda.l {symbols["SourceAnimationInit4086_Handle"]}');branch('beq','Done')
    put(f' lda.l {symbols["SourceAnimationInit4086_Count"]}');branch('beq','Done')
    put(f' lda #0\n sta.l {symbols["SourceAnimationInit4086_Reset"]}\n jsl {symbols["SourceAnimationInit4086_Begin"]}');branch('bcs')
    put(f' lda.l {symbols["SourceAnimationInit4086_State"]}\n cmp #2');branch('beq','Done');put(' cmp #1');branch('bne')
    put(f' lda #3\n sta.l {work}+2\n lda #1\n ply\n plx\n plp\n clc\n rtl')
    label('FinishFrame');put(' php\n rep #$39\n phx\n phy')
    put(f' lda.l {work}\n cmp #$B68A');branch('bne')
    put(f' lda.l {work}+2\n cmp #3');branch('bne')
    put(f' lda.l {symbols["SourceAnimationInit4086_Slot"]}\n cmp.l {work}+4');branch('bne')
    put(f' lda.l {symbols["SourceAnimationInit4086_Number"]}\n cmp #{roles["jumpattack"]}');branch('bne')
    put(f' jsl {symbols["SourceAnimationInit4086_Ack"]}');branch('bcs')
    label('Done');put(f' lda #2\n sta.l {work}+2\n lda #0\n ply\n plx\n plp\n clc\n rtl')
    label('Bad');put(f' lda #4\n sta.l {work}+2\n ply\n plx\n plp\n sec\n rtl')
    return '\n'.join(lines)+'\n'
