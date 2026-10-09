"""Canonical directional RUN section; all alternate roles query as absent.

The source-derived no-DUCK capability makes the platform-duck body unreachable.
Coordinates use the explicit existing ACCEPTED_COMPAT_Q16_16 representation.
The entry player row is supplied by the outer controller, never recaptured.
"""
from source_player_run_4086 import KEYS

def emit(work,tuple_work,history,sequence,input_owner,input_magic,profile,roles,symbols):
    spans=((work,64),(tuple_work,64),(history,1024),(sequence,110),(input_owner,2))
    for i,(a,n)in enumerate(spans):
        if not 0<=a<=0x1000000-n:raise ValueError('PLAYER_DIRECTIONAL_EXTENT')
        if any(a<b+m and b<a+n for b,m in spans[i+1:]):raise ValueError('PLAYER_DIRECTIONAL_OVERLAP')
    models=profile['models'];count=len(models)
    if profile.get('capability')!='READONLY_DIRECTIONAL_RUN_ONLY' or not 1<=count<=16 or any(m['id']!=i for i,m in enumerate(models)):raise ValueError('PLAYER_DIRECTIONAL_CAPABILITY')
    if history&255 or not 1<=input_magic<=65535:raise ValueError('PLAYER_DIRECTIONAL_INPUT')
    lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('PlayerDirectional_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;skip='PlayerDirectional_Skip'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+skip+'\n jmp PlayerDirectional_'+n+'\n'+skip+':\n.a16\n.i16')
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
        resolve(role);put(f' lda.l {symbols["SourceAnimationInit4086_Handle"]}');branch('beq','Absent'+role)
        put(f' lda.l {symbols["SourceAnimationInit4086_Count"]}');branch('bne')
        label('Absent'+role)
    def match(mask,target):
        put(f' lda #2\n sta.l {sequence}\n lda #{mask}\n sta.l {sequence}+2\n sta.l {sequence}+6\n lda #0\n sta.l {sequence}+4\n sta.l {sequence}+8\n lda.l {work}+6\n jsl PlayerHistory_Match');branch('bcs');put(' cmp #0');branch('beq',target)
    def start_run(mask):
        put(f' lda.l {work}+6\n xba\n tax\n lda.l {history}+224,x\n and #{(~mask)&65535}\n sta.l {history}+224,x\n lda.l {history}+232,x');branch('bne','StepNonzero'+str(mask));put(' lda #27');label('StepNonzero'+str(mask))
        put(f' dec a\n sta.l {history}+232,x\n lda.l {work}+20\n tax\n lda #1\n sta.l $42F404,x\n lda #0\n sta.l $42F406,x')
    label('Execute');put(' php\n rep #$39\n pha\n phx\n phy')
    for address,magic in ((work,0xb68c),(input_owner,input_magic),(symbols['VmSourceWorld_Ready'],0xb4a3),(symbols['VmSourceWorld_PoolBase'],0x4000),(symbols['SourceModelEntityCopy4086_Ready'],0xb4eb)):
        put(f' lda.l {address}\n cmp #{magic}');branch('bne')
    put(f' lda.l {work}+2');branch('beq','Ready');put(' cmp #2');branch('bne')
    label('Ready');put(f' lda #1\n sta.l {work}+2\n lda.l {work}+6\n cmp #4');branch('bcs')
    put(f' lda.l {symbols["VmSourceWorld_Count"]}');branch('beq');put(' cmp #129');branch('bcs')
    put(f' cmp.l {symbols["SourceModelEntityCopy4086_Entities"]}');branch('bne')
    put(f' lda.l {symbols["SourceModelEntityCopy4086_Models"]}\n cmp #{count}');branch('bne')
    put(f' lda.l {work}+4\n cmp.l {symbols["VmSourceWorld_Count"]}');branch('bcs')
    for dest,stride in ((16,80),(18,64),(20,24)):offset(dest,stride)
    put(f' lda.l {work}+16\n tax\n clc\n adc #$4000\n cmp.l $414000,x');branch('bne')
    put(' lda.l $414002,x\n cmp #$41');branch('bne')
    put(' lda.l $414008,x\n cmp #2');branch('bne');put(' lda.l $41400A,x');branch('bne')
    put(f' lda.l $41400C,x\n sta.l {work}+28\n lda.l $41400E,x\n sta.l {work}+30\n eor #$8000\n sta.l {work}+44\n lda.l $41401C,x\n sta.l {work}+48\n lda.l $41401E,x\n sta.l {work}+50')
    put(' lda.l $414018,x\n cmp #1');branch('bne');put(' lda.l $41401A,x');branch('bne')
    put(f' lda.l {work}+18\n tax\n lda.l $416800,x\n cmp #{count}');branch('bcs')
    put(f' lda.l $416830,x\n sta.l {work}+32\n lda.l $416832,x\n sta.l {work}+34\n eor #$8000\n cmp.l {work}+44');branch('bcc','YGreater');branch('bne','BaseGreater')
    put(f' lda.l {work}+32\n cmp.l {work}+28');branch('bcc','YGreater')
    label('BaseGreater');put(f' lda.l {work}+32\n sec\n sbc.l {work}+28\n lda.l {work}+34\n sbc.l {work}+30\n sta.l {work}+36');put(' jmp PlayerDirectional_AirCompare')
    label('YGreater');put(f' lda.l {work}+28\n sec\n sbc.l {work}+32\n lda.l {work}+30\n sbc.l {work}+34\n sta.l {work}+36')
    label('AirCompare');put(f' lda #2\n sta.l {work}+40\n lda.l {work}+18\n tax\n lda.l $409014,x\n ora.l $409016,x');branch('beq','AirThreshold')
    put(f' lda #5\n sta.l {work}+40')
    label('AirThreshold');put(f' lda #0\n sta.l {work}+8\n lda.l {work}+36\n cmp.l {work}+40');branch('bcs','Tuple')
    put(f' lda #1\n sta.l {work}+8')
    label('Tuple');put(f' lda.l {work}+4\n sta.l {tuple_work}+4\n jsl SourceRunTuple_Read');branch('bcs')
    put(f' lda.l {tuple_work}+32\n sta.l {work}+12\n lda.l {tuple_work}+34\n sta.l {work}+14')
    for name,key,attack in (('Up',KEYS['moveup'],'attackup'),('Down',KEYS['movedown'],'attackdown')):
        label(name);put(f' lda.l {work}+6\n xba\n tax\n lda.l {history}+224,x\n and #{key}');branch('beq','After'+name)
        put(f' lda.l {work}+8');branch('beq','After'+name);match(key,'After'+name)
        put(f' lda.l {work}+12\n and #2');branch('beq',name+'Alternate')
        # A RUN query occurs in both vertical branches; give its observer a
        # unique source-site label while retaining one common role identity.
        put(f' lda.l {work}+4\n sta.l {symbols["SourceAnimationInit4086_Slot"]}\n lda #{roles["run"]}\n sta.l {symbols["SourceAnimationInit4086_Number"]}')
        label('Query_run_'+name);put(f' jsl {symbols["SourceAnimationInit4086_Resolve"]}');branch('bcs')
        put(f' lda.l {symbols["SourceAnimationInit4086_Handle"]}');branch('beq',name+'Alternate')
        put(f' lda.l {symbols["SourceAnimationInit4086_Count"]}');branch('beq',name+'Alternate');start_run(key);put(' jmp PlayerDirectional_After'+name)
        label(name+'Alternate');absent(attack)
        # DODGE is queried at two source sites, so emitter labels must differ.
        put(f' lda.l {work}+4\n sta.l {symbols["SourceAnimationInit4086_Slot"]}\n lda #{roles["dodge"]}\n sta.l {symbols["SourceAnimationInit4086_Number"]}')
        label('Query_dodge_'+name);put(f' jsl {symbols["SourceAnimationInit4086_Resolve"]}');branch('bcs')
        put(f' lda.l {symbols["SourceAnimationInit4086_Handle"]}');branch('beq','After'+name)
        put(f' lda.l {symbols["SourceAnimationInit4086_Count"]}');branch('bne');label('After'+name)
    label('Horizontal');put(f' lda.l {work}+6\n xba\n tax\n lda.l {history}+224,x\n and #12');branch('beq','Done')
    put(f' lda.l {work}+8');branch('beq','Done')
    put(f' lda.l {work}+50');branch('bne','Done')
    put(f' lda.l {work}+48\n cmp #1');branch('beq','Right');put(' cmp #0');branch('bne','Done');match(KEYS['moveleft'],'Done');put(' jmp PlayerDirectional_HorizontalMatched')
    label('Right');match(KEYS['moveright'],'Done')
    label('HorizontalMatched');resolve('run');put(f' lda.l {symbols["SourceAnimationInit4086_Handle"]}');branch('beq','ForwardAlternate')
    put(f' lda.l {symbols["SourceAnimationInit4086_Count"]}');branch('beq','ForwardAlternate');start_run(12);put(' jmp PlayerDirectional_Done')
    label('ForwardAlternate');absent('attackforward')
    label('Done');put(f' lda #2\n sta.l {work}+2\n ply\n plx\n pla\n plp\n clc\n rtl')
    label('Bad');put(f' lda #3\n sta.l {work}+2\n ply\n plx\n pla\n plp\n sec\n rtl')
    return '\n'.join(lines)+'\n'
