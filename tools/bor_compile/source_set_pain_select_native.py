"""Source zero-guard pain selection through the actual mutable animation cache.

Caller owns 24 serialized bytes. No new arena allocation, actor writes,
animation begin, flags, unfreeze, onpain or callback acknowledgement.
"""
from compiler import key
from source_profile import document, discover
from source_animation_ids import configure
from source_model_core_4086 import integer
from dialect_4086 import ENGINE_COMMIT
import hashlib, subprocess


def derive(source):
    raw=subprocess.check_output(['git','-C','E:/gh/openbor-bcec','show',ENGINE_COMMIT+':engine/openbor.c']).decode('latin1')
    default='newchar->guardpoints.current = newchar->guardpoints.max = 0;'
    if default not in raw:raise ValueError('PAIN_SELECT_GUARD_DEFAULT_AUTHORITY')
    docs={k:document(source,n)for k,(n,_)in source.index.items()if k.endswith('.txt')}
    structure=discover(source,docs);ids=configure(docs[key(structure['models_path'])]['directives'])
    models=[]
    for i,m in enumerate(structure['models']):
        doc=docs[key(m['source_path'])];guard=0
        for r in doc['directives']:
            if r['directive']=='subclass':raise ValueError('PAIN_SELECT_SUBCLASS_REQUIRED')
            if r['directive']=='guardpoints':guard=integer(r['values'])
        if guard!=0:raise ValueError('PAIN_SELECT_GUARD_STATE_REQUIRED:'+m['declaration'])
        models.append(dict(id=i,identity=m['declaration'],source_sha256=doc['sha256'],guardpoints_max=guard))
    return dict(schema='BYOR_ZERO_GUARD_PAIN_SELECTION_V1',models=models,engine_commit=ENGINE_COMMIT,guard_default_authority_sha256=hashlib.sha256(default.encode()).hexdigest(),
                pains=ids['arrays']['pains'],grabbed=ids['authority']['enum']['ANI_GRABBED'],
                idle=ids['authority']['enum']['ANI_IDLE'],maximum=ids['max_animations'],
                guardpoint_model_mutators_admitted=False,full_set_pain_bound=False)


def emit(work, requirements, sy, code_bank=39):
    if not 0<=work<=0x1000000-24 or any(m['guardpoints_max']for m in requirements['models']):
        raise ValueError('PAIN_SELECT_NATIVE_DOMAIN')
    pains=requirements['pains'];lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('SetPainSelect_'+n+':\n.a16\n.i16')
    def jump(op,n):
        nonlocal serial
        serial+=1;skip='SetPainSelect_Skip'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc',bmi='bpl',bpl='bmi')[op]+' '+skip+'\n jmp SetPainSelect_'+n+'\n'+skip+':\n.a16\n.i16')
    def require(a,v):put(f' lda.l {a}\n cmp #{v}');jump('bne','Bad')
    label('Run');put(' php\n rep #$39\n phx\n phy')
    put(f' jsl {sy["SourceForeignWork_Check"]}');jump('bcs','Bad')
    require(work,0xb6b5);put(f' lda.l {work}+2');jump('beq','Ready');put(' cmp #2');jump('bne','Bad')
    label('Ready');require(work+22,0)
    put(f' lda.l {work}+10\n cmp #2');jump('bcs','Bad')
    put(f' lda.l {work}+4\n sta.l {sy["SourceAnimationInit4086_Slot"]}\n lda #0\n sta.l {sy["SourceAnimationInit4086_Reset"]}')
    put(f' lda.l {work}+8');jump('beq','Ordinary');put(' cmp #$FFFF');jump('bne','PositiveHigh')
    require(work+6,65535);put(' jmp SetPainSelect_Grabbed')
    label('PositiveHigh');put(f' lda.l {work}+8');jump('bmi','Bad');put(' jmp SetPainSelect_Grabbed')
    label('Ordinary');put(f' lda.l {work}+6\n cmp #{len(pains)}');jump('bcs','Grabbed')
    put(f' asl a\n tax\n lda.l SetPainSelect_Pains+{code_bank<<16},x\n jmp SetPainSelect_Requested')
    label('Grabbed');put(' lda #'+str(requirements['grabbed']))
    label('Requested');put(f' sta.l {work}+12\n sta.l {work}+14\n lda #0\n sta.l {work}+20')
    label('Query');put(f' lda.l {work}+14\n sta.l {sy["SourceAnimationInit4086_Number"]}\n jsl {sy["SourceAnimationInit4086_Resolve"]}');jump('bcs','Bad')
    put(f' lda.l {sy["SourceAnimationInit4086_Count"]}');jump('bne','Found')
    put(f' lda.l {work}+20');jump('beq','Default');put(' cmp #1');jump('beq','Idle')
    put(f' lda #$FFFF\n sta.l {work}+14\n lda #0\n sta.l {work}+16\n sta.l {work}+18\n jmp SetPainSelect_Done')
    label('Default');put(f' lda #1\n sta.l {work}+20\n lda #{pains[0]}\n sta.l {work}+14\n jmp SetPainSelect_Query')
    label('Idle');put(f' lda #2\n sta.l {work}+20\n lda #{requirements["idle"]}\n sta.l {work}+14\n jmp SetPainSelect_Query')
    label('Found');put(f' sta.l {work}+18\n lda.l {sy["SourceAnimationInit4086_Handle"]}\n sta.l {work}+16')
    label('Done');put(f' lda #2\n sta.l {work}+2\n lda #0\n ply\n plx\n plp\n clc\n rtl')
    label('Bad');put(f' lda #4\n sta.l {work}+2\n lda #3\n ply\n plx\n plp\n sec\n rtl')
    label('Pains');put(' .dw '+','.join(map(str,pains)))
    return '\n'.join(lines)+'\n'


def emit_begin(work,sy):
    """Velocity clear once, actual animation begin, and retained frame debt.

    A=0 no animation, 1 frame child pending, 2 painflags child required.
    Status 5 is flags-required, not completed set_pain. No implicit frame Ack.
    """
    lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('SetPainBegin_'+n+':\n.a16\n.i16')
    def jump(op,n):
        nonlocal serial
        serial+=1;skip='SetPainBegin_Skip'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcc='bcs',bcs='bcc')[op]+' '+skip+'\n jmp SetPainBegin_'+n+'\n'+skip+':\n.a16\n.i16')
    label('Run');put(' php\n rep #$39\n phx\n phy')
    put(f' jsl {sy["SourceForeignWork_Check"]}');jump('bcs','Bad')
    put(f' lda.l {work}\n cmp #$B6B5');jump('bne','Bad')
    put(f' lda.l {work}+2\n cmp #3');jump('beq','Resume');put(' cmp #5');jump('beq','Resume')
    put(' jsl SetPainSelect_Run');jump('bcs','Bad')
    # The resolver has validated the canonical side pointer, source pool,
    # table, mutable cache and every initializer lease before actor writes.
    put(f' lda.l {sy["SourceAnimationInit4086_Side"]}\n tax\n lda #0')
    for off in (36,38,40,42,44,46):put(f' sta.l $410000+{off},x')
    put(f' lda.l {work}+14\n cmp #$FFFF');jump('beq','Absent')
    put(f' lda.l {work}+10\n sta.l {sy["SourceAnimationInit4086_Reset"]}\n jsl {sy["SourceAnimationInit4086_Begin"]}');jump('bcs','Bad')
    label('Resume')
    for a,b in ((sy['SourceAnimationInit4086_Slot'],work+4),(sy['SourceAnimationInit4086_Number'],work+14),(sy['SourceAnimationInit4086_Handle'],work+16),(sy['SourceAnimationInit4086_Count'],work+18)):
        put(f' lda.l {a}\n cmp.l {b}');jump('bne','Bad')
    put(f' lda.l {sy["SourceAnimationInit4086_State"]}\n cmp #1');jump('beq','Pending')
    put(' cmp #2');jump('bne','Bad');put(f' lda #5\n sta.l {work}+2\n lda #2\n jmp SetPainBegin_Good')
    label('Pending');put(f' lda #3\n sta.l {work}+2\n lda #1\n jmp SetPainBegin_Good')
    label('Absent');put(f' lda #2\n sta.l {work}+2\n lda #0')
    label('Good');put(' ply\n plx\n plp\n clc\n rtl')
    label('Bad');put(f' lda #4\n sta.l {work}+2\n lda #3\n ply\n plx\n plp\n sec\n rtl')
    return '\n'.join(lines)+'\n'
