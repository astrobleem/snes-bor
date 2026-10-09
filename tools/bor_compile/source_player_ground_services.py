"""Serialized ground services; caller executes requested real frame owners.

Idle and a registered common_turn action require separate owners. Every request
for either rejects explicitly; no missing service is acknowledged as a no-op.
"""
import re
from source_animation_ids import role_id


def emit(work,ground,binding,empty,configuration,symbols):
    if configuration['limits']['max_walks']!=1:
        raise ValueError('GROUND_SERVICES_WALK_SERIES_OWNER_REQUIRED')
    extents=((work,32),(ground,128),(binding,32),(empty,24))
    for i,(a,n)in enumerate(extents):
        if not 0<=a<=0x1000000-n:raise ValueError('GROUND_SERVICES_EXTENT')
        if any(a<b+m and b<a+n for b,m in extents[i+1:]):raise ValueError('GROUND_SERVICES_OVERLAP')
    lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('GroundServices_'+n+':\n.a16\n.i16')
    def branch(op,n):
        nonlocal serial
        serial+=1;skip='GroundServices_Skip'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+skip+'\n jmp GroundServices_'+n+'\n'+skip+':\n.a16\n.i16')
    for entry in ('Begin','FinishFrame'):
        label(entry);put(' php\n rep #$39\n phx\n phy')
        put(f' lda.l {work}\n cmp #$B67E');branch('bne','Bad')
        if entry=='Begin':
            put(f' lda.l {work}+2');branch('beq','BeginReady')
            put(' cmp #2');branch('bne','Bad')
            label('BeginReady');put(' jsl GroundBinding_Capture');branch('bcs','Bad')
            put(' jsl SourceGround_Begin');branch('bcs','Bad');put(' jmp GroundServices_Drive')
        else:
            put(f' lda.l {work}+2\n cmp #3');branch('bne','Bad')
            put(' jsl SourceAnimationInit4086_Ack');branch('bcs','Bad')
            put(' jmp GroundServices_ServiceReturned')
    label('Drive');put(f' lda #1\n sta.l {work}+2\n lda.l {ground}+2\n cmp #2');branch('beq','Complete')
    put(' cmp #5');branch('beq','Query')
    put(' cmp #4');branch('beq','Item')
    put(' cmp #3');branch('bne','Bad')
    put(' jsl GroundBinding_Publish');branch('bcs','Bad')
    put(f' lda.l {binding}+4\n sta.l SourceAnimationInit4086_Slot\n lda #0\n sta.l SourceAnimationInit4086_Reset')
    put(f' lda.l {ground}+90\n cmp #1');branch('beq','SetAnimation')
    for service,role in ((3,'walk'),(4,'backwalk'),(5,'up'),(6,'down')):
        put(f' cmp #{service}');branch('beq','Walk_'+role)
    put(' jmp GroundServices_Bad')  # common_idle_anim is not set_idle.
    for service,role in ((3,'walk'),(4,'backwalk'),(5,'up'),(6,'down')):
        label('Walk_'+role)
        put(f' lda #{role_id(configuration,role)}\n sta.l SourceAnimationInit4086_Number\n lda.l {binding}+4\n sta.l SourceDefaultPlayer4086_Slot\n jsl SourceWalk4086_BeginDefaultOnly')
        branch('bcs','Bad');put(' jmp GroundServices_AnimationResult')
    label('SetAnimation');put(' jsr GroundServices_SetRole');branch('bcs','Bad')
    put(' jsl SourceAnimationInit4086_Begin');branch('bcs','Bad')
    label('AnimationResult');put(' lda.l SourceAnimationInit4086_State\n cmp #1');branch('beq','Pending')
    put(' cmp #2');branch('bne','Bad');put(' jmp GroundServices_ServiceReturned')
    label('Pending');put(f' lda #3\n sta.l {work}+2\n lda #1\n ply\n plx\n plp\n clc\n rtl')
    label('Item');put(f' lda.l {ground}+90\n cmp #2');branch('bne','Bad')
    put(' jsl GroundBinding_Publish');branch('bcs','Bad')
    put(f' lda.l {binding}+4\n sta.l {empty}+4\n lda #4\n sta.l {empty}+6\n lda #0\n sta.l {empty}+8\n jsl SourceFindHereEmpty_Execute');branch('bcs','Bad')
    label('ServiceReturned');put(' jsl GroundBinding_Capture');branch('bcs','Bad');put(' jmp GroundServices_Acknowledge')
    label('Query');put(f' lda.l {ground}+90');branch('bne','Bad')
    put(f' lda.l {binding}+4\n sta.l SourceAnimationInit4086_Slot\n jsr GroundServices_SetRole');branch('bcs','Bad')
    put(' jsl SourceAnimationInit4086_Resolve');branch('bcs','Bad')
    put(f' lda #0\n sta.l {ground}+10\n lda.l SourceAnimationInit4086_Handle');branch('beq','Acknowledge')
    put(' lda.l SourceAnimationInit4086_Count');branch('beq','Acknowledge')
    put(f' lda #1\n sta.l {ground}+10')
    label('Acknowledge');put(f' lda #$B67A\n sta.l {ground}+8\n lda.l {ground}+90\n sta.l {ground}+12\n lda.l {ground}+6\n sta.l {ground}+14\n jsl SourceGround_Resume');branch('bcs','Bad');put(' jmp GroundServices_Drive')
    label('Complete');put(' jsl GroundBinding_Publish');branch('bcs','Bad')
    put(f' lda #2\n sta.l {work}+2\n lda #0\n ply\n plx\n plp\n clc\n rtl')
    label('Bad');put(f' lda #4\n sta.l {work}+2\n ply\n plx\n plp\n sec\n rtl')
    label('SetRole');put(f' lda.l {ground}+6')
    for i,role in enumerate(('up','down','duck','turn','backwalk','run')):
        put(f' cmp #{i}');branch('beq','Role_'+role)
    put(' sec\n rts')
    for i,role in enumerate(('up','down','duck','turn','backwalk','run')):
        label('Role_'+role);put(f' lda #{role_id(configuration,role)}\n sta.l SourceAnimationInit4086_Number\n clc\n rts')
    code='\n'.join(lines)+'\n'
    for name in set(re.findall(r'\bSource(?:AnimationInit4086|DefaultPlayer4086|Walk4086)_\w+\b',code)):
        if name not in symbols:raise ValueError('GROUND_SERVICES_SYMBOL:'+name)
        code=re.sub(r'\b'+name+r'\b',str(symbols[name]),code)
    return code
