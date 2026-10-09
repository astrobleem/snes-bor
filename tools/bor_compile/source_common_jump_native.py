"""Canonical source jump landing through real JUMPLAND/set_idle frame owners.

Temporally reuses the completed dojump 80-byte control block. Sound or frame
pending dojump cannot transfer its lease. Numeric movement/inair follows the
existing explicit Q16.16 compatibility policy. No dust service is faked.
"""
import struct
from source_engine_function_ids import function_id


def emit(work,pending,run_work,profile,jumpland_role,symbols,code_bank):
    if profile.get('capability')!='READONLY_JUMP_LAND_DUST_ABSENCE' or not 1<=code_bank<=0x7d:
        raise ValueError('COMMON_JUMP_CAPABILITY')
    models=profile['models'];animations=sorted(profile['animations'],key=lambda a:a['handle']);count=len(models)
    if not 1<=count<=16 or [m['id']for m in models]!=list(range(count)) or not 1<=len(animations)<=128 or not 0<=jumpland_role<=65535 or [a['handle']for a in animations]!=list(range(1,len(animations)+1)) or any(not 0<=a['model']<count or not -2147483648<=a['landframe']<=2147483647 for a in animations):
        raise ValueError('COMMON_JUMP_PROFILE_IDENTITY')
    spans=((work,80),(pending,64),(run_work,64))
    for i,(a,n)in enumerate(spans):
        if not 0<=a<=0x1000000-n or any(a<b+m and b<a+n for b,m in spans[i+1:]):raise ValueError('COMMON_JUMP_LAYOUT')
    jump_action=function_id('common_jump');land_action=function_id('common_jumpland');lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('CommonJump_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;skip='CommonJump_Skip'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+skip+'\n jmp CommonJump_'+n+'\n'+skip+':\n.a16\n.i16')
    def offset(dest,stride):
        put(' lda #0')
        for bit in range(stride.bit_length()-1,-1,-1):
            put(' asl a')
            if stride&(1<<bit):put(f' clc\n adc.l {work}+4')
        put(f' sta.l {work}+{dest}')
    for name,action in (('Begin',jump_action),('Jumpland',land_action)):
        label(name);put(f' php\n rep #$39\n phx\n phy\n lda.l {work}\n cmp #$B693');branch('bne','Own'+name)
        put(f' lda.l {work}+2\n cmp #2');branch('bne','LeaseBad');put(f' lda #$B695\n sta.l {work}\n lda #0\n sta.l {work}+2')
        label('Own'+name);put(f' lda.l {work}\n cmp #$B695');branch('bne','LeaseBad')
        put(f' lda.l {work}+2');branch('beq','Ready'+name);put(' cmp #2');branch('bne','LeaseBad')
        label('Ready'+name);put(f' lda #{action}\n sta.l {work}+10\n lda #1\n sta.l {work}+2\n jsl CommonJump_Bind');branch('bcs')
        if name=='Jumpland':
            offset(26,20);put(f' lda.l {work}+26\n tax\n lda.l $41F510,x');branch('bne','Done');put(' jmp CommonJump_Idle')
        else:
            put(f' lda.l {work}+26\n tax\n lda.l $414008,x\n cmp #2');branch('bne');put(' lda.l $41400A,x');branch('bne')
            for at,suffix in ((0,'Lo'),(2,'Hi')):
                put(f' lda.l $41400C+{at},x\n sta.l {symbols["SourceModelEntityCopy4086_"+suffix]}')
            put(f' lda.l {work}+28\n tax')
            for at,suffix in ((0,'Lo'),(2,'Hi')):
                put(f' lda.l $416830+{at},x\n sta.l {symbols["SourceDefaultPlayer4086_Inv"+suffix]}')
            put(f' jsl {symbols["SourceInAir4086_Q16Compatibility"]}\n cmp #0');branch('bne','Done')
            put(f' lda.l {work}+28\n tax\n lda.l $41682E,x')
            # Signed velocity.y <=0, including the full low word.
            put(' and #$8000');branch('bne','Land')
            put(' lda.l $41682C,x\n ora.l $41682E,x');branch('bne','Done')
            put(' jmp CommonJump_Land')
    label('Land');put(' jsl CommonJump_Metadata');branch('bcs')
    put(f' lda.l {work}+4\n sta.l {run_work}+4\n jsl SourceRunTuple_Read');branch('bcs')
    put(f' lda.l {work}+28\n tax\n lda #0\n sta.l $41682C,x\n sta.l $41682E,x')
    for at in (0,2):put(f' lda.l $416830+{at},x\n sta.l {work}+{44+at}')
    put(f' lda.l {work}+26\n tax')
    for at in (0,2):put(f' lda.l {work}+{44+at}\n sta.l $41400C+{at},x')
    put(f' lda.l {work}+32\n tax\n lda #0\n sta.l $43EB08,x\n sta.l $43EB0A,x\n lda.l {work}+34\n tax\n lda #0\n sta.l $40C058,x\n sta.l $40C05A,x\n lda.l {run_work}+36\n ora.l {run_work}+38');branch('bne','KeepRunning')
    offset(26,24);put(f' lda.l {work}+26\n tax\n lda #0\n sta.l $42F404,x\n sta.l $42F406,x')
    label('KeepRunning');put(f' lda.l {work}+28\n tax\n lda #0\n sta.l $416824,x\n sta.l $416826,x\n sta.l $416828,x\n sta.l $41682A,x\n lda.l {work}+4\n sta.l {symbols["SourceAnimationInit4086_Slot"]}\n lda #{jumpland_role}\n sta.l {symbols["SourceAnimationInit4086_Number"]}')
    label('QueryJumpland');put(f' jsl {symbols["SourceAnimationInit4086_Resolve"]}');branch('bcs')
    put(f' lda.l {symbols["SourceAnimationInit4086_Handle"]}');branch('beq','NoJumpland')
    put(f' lda.l {symbols["SourceAnimationInit4086_Count"]}');branch('beq','NoJumpland')
    put(f' lda.l {work}+36\n cmp #$FFFF');branch('bne','NoJumpland');put(f' lda.l {work}+38\n cmp #$FFFF');branch('bne','NoJumpland')
    put(f' lda.l {work}+30\n tax\n lda #{land_action}\n sta.l $43900C,x\n lda #0\n sta.l $43900E,x\n sta.l {symbols["SourceAnimationInit4086_Reset"]}\n lda #1\n sta.l {work}+6\n jsl {symbols["SourceAnimationInit4086_Begin"]}');branch('bcs');put(' jmp CommonJump_FrameResult')
    label('NoJumpland');put(f' lda.l {work}+38\n and #$8000');branch('bne','Idle');offset(26,20)
    put(f' lda.l {work}+26\n tax\n lda.l $41F510,x');branch('bne','Done')
    label('Idle');put(f' lda.l {work}+30\n tax\n lda #0\n sta.l $43900C,x\n sta.l $43900E,x\n lda.l {work}+4\n sta.l {symbols["SourceIdle4086_Slot"]}\n lda #2\n sta.l {work}+6\n jsl {symbols["SourceSetIdle4086_Begin"]}');branch('bcs')
    label('FrameResult');put(f' lda.l {symbols["SourceAnimationInit4086_State"]}\n cmp #2');branch('beq','Done');put(' cmp #1');branch('bne')
    put(f' lda.l {work}+4\n sta.l {work}+48\n lda.l {symbols["SourceAnimationInit4086_Number"]}\n sta.l {work}+50\n lda #3\n sta.l {work}+2\n lda #$8001\n jmp CommonJump_Exit')
    label('FinishFrame');put(f' php\n rep #$39\n phx\n phy\n lda.l {work}\n cmp #$B695');branch('bne')
    put(f' lda.l {work}+2\n cmp #3');branch('bne')
    put(f' lda.l {work}+4\n cmp.l {work}+48');branch('bne')
    for name,at in (('Slot',48),('Number',50)):
        put(f' lda.l {symbols["SourceAnimationInit4086_"+name]}\n cmp.l {work}+{at}');branch('bne')
    put(f' jsl {symbols["SourceAnimationInit4086_Ack"]}');branch('bcs')
    label('Done');put(f' lda #2\n sta.l {work}+2\n lda #0')
    label('Exit');put(' ply\n plx\n plp\n clc\n rtl')
    label('Bad');put(f' lda #5\n sta.l {work}+2\n ply\n plx\n plp\n sec\n rtl')
    label('LeaseBad');put(' ply\n plx\n plp\n sec\n rtl')
    label('Bind');put(f' lda.l {symbols["VmSourceWorld_Count"]}');branch('beq','BindBad');put(' cmp #129');branch('bcs','BindBad')
    put(f' lda.l {symbols["SourceModelEntityCopy4086_Ready"]}\n cmp #$B4EB');branch('bne','BindBad')
    put(f' lda.l {symbols["SourceModelEntityCopy4086_Models"]}\n cmp #{count}');branch('bne','BindBad')
    put(f' lda.l {work}+4\n cmp.l {symbols["VmSourceWorld_Count"]}');branch('bcs','BindBad')
    for dest,stride in ((26,80),(28,64),(30,80),(32,32),(34,96)):offset(dest,stride)
    put(f' lda.l {work}+28\n tax\n lda.l $416800,x\n cmp #{count}');branch('bcs','BindBad')
    put(f' sta.l {pending}+6\n sta.l {work}+40\n lda.l {work}+4\n sta.l {pending}+4\n jsl PendingJump_Read');branch('bcs','BindBad')
    put(f' lda.l {symbols["SourceLifecycle4086_Ready"]}\n cmp #$B4FB');branch('bne','BindBad')
    put(f' lda.l {work}+30\n tax\n lda.l $43904A,x\n cmp #$B4FB');branch('bne','BindBad')
    put(f' lda.l $439048,x\n cmp.l {work}+40');branch('bne','BindBad')
    put(f' lda.l $43900C,x\n cmp.l {work}+10');branch('bne','BindBad');put(' lda.l $43900E,x');branch('bne','BindBad');put(' clc\n rtl')
    label('Metadata');put(f' lda.l {work}+28\n tax\n lda.l $416804,x');branch('beq','BindBad');put(f' cmp #{len(animations)+1}');branch('bcs','BindBad')
    put(' dec a\n asl a\n sta.l '+str(work)+'+42\n asl a\n clc\n adc.l '+str(work)+'+42\n tax')
    put(f' lda.l CommonJump_MetadataTable+{code_bank<<16},x\n cmp.l {work}+40');branch('bne','BindBad')
    for at in (0,2):put(f' lda.l CommonJump_MetadataTable+{2+at}+{code_bank<<16},x\n sta.l {work}+{36+at}')
    put(' clc\n rtl');label('BindBad');put(' sec\n rtl');label('MetadataTable')
    for row in animations:
        lo,hi=struct.unpack('<2H',struct.pack('<i',row['landframe']));put(f' .word {row["model"]},{lo},{hi}')
    return '\n'.join(lines)+'\n'
