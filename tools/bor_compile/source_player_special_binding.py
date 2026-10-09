"""Canonical special snapshot binding for profiles without model smartbombs.

Context flags belong to the enclosing controller. This is not a smartbomb,
freeze, linked-idle or frame execution service and grants no implicit RAM lease.
"""
from source_profile import document
from source_model_core_4086 import derive as model_core


def capability(source):
    report=model_core(source)
    for m in report['models']:
        rows=document(source,m['source_path'])['directives']
        if any(r['directive']=='smartbomb' for r in rows):
            raise ValueError('SPECIAL_SMARTBOMB_MODEL_STATE_OWNER_REQUIRED')
    return dict(capability='NO_MODEL_SMARTBOMB',models=[dict(id=m['id'],source_sha256=m['source_sha256'])for m in report['models']],
                smartbomb=0,dofreeze=0,authority='init_model calloc; only CMD_MODEL_SMARTBOMB installs these fields',
                direct_model_smartbomb_mutation_admitted=False,motu_gameplay_proven=False)


def emit(work,special,tail,history,input_owner,input_magic,profile,role,symbols):
    extents=((work,64),(special,192),(tail,2048),(history,1024),(input_owner,2))
    for i,(a,n)in enumerate(extents):
        if not 0<=a<=0x1000000-n:raise ValueError('SPECIAL_BINDING_EXTENT')
        if any(a<b+m and b<a+n for b,m in extents[i+1:]):raise ValueError('SPECIAL_BINDING_OVERLAP')
    count=len(profile['models'])
    if profile['capability']!='NO_MODEL_SMARTBOMB' or not 1<=count<=16 or history&255 or not 1<=input_magic<=65535:
        raise ValueError('SPECIAL_BINDING_CAPABILITY')
    lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(n):put('SpecialBinding_'+n+':\n.a16\n.i16')
    def branch(op,n='Bad'):
        nonlocal serial
        serial+=1;skip='SpecialBinding_Skip'+str(serial)
        put(' '+dict(beq='bne',bne='beq',bcs='bcc',bcc='bcs')[op]+' '+skip+'\n jmp SpecialBinding_'+n+'\n'+skip+':\n.a16\n.i16')
    def plus2(a):return a[:-2]+'+2,x'if a.endswith(',x')else a+'+2'
    def copy(src,dst):put(f' lda.l {src}\n sta.l {dst}\n lda.l {plus2(src)}\n sta.l {plus2(dst)}')
    def offset(off,stride):
        put(f' lda.l {work}+4\n sta.l {work}+60\n lda #0')
        for bit in range(stride.bit_length()-1,-1,-1):
            put(' asl a')
            if stride&(1<<bit):put(f' clc\n adc.l {work}+60')
        put(f' sta.l {work}+{off}')
    for entry,mode in (('Capture',0),('Publish',1)):
        label(entry);put(f' php\n rep #$39\n pha\n phx\n phy\n lda #{mode}\n sta.l {work}+58\n jmp SpecialBinding_Check')
    label('Check')
    for address,magic in ((work,0xb684),(special,0xb682),(input_owner,input_magic),
                          (symbols['VmSourceWorld_Ready'],0xb4a3),(symbols['VmSourceWorld_PoolBase'],0x4000),
                          (symbols['SourceRetirement4086_Ready'],0xb4f8),(symbols['SourceModelEntityCopy4086_Ready'],0xb4eb)):
        put(f' lda.l {address}\n cmp #{magic}');branch('bne')
    put(f' lda.l {symbols["VmSourceWorld_Count"]}');branch('beq')
    put(f' cmp #129');branch('bcs')
    put(f' cmp.l {symbols["SourceModelEntityCopy4086_Entities"]}');branch('bne')
    put(f' lda.l {symbols["SourceModelEntityCopy4086_Models"]}\n cmp #{count}');branch('bne')
    put(f' lda.l {work}+4\n cmp.l {symbols["VmSourceWorld_Count"]}');branch('bcs')
    for off,stride in ((8,80),(10,96),(12,64),(14,32),(16,20),(18,40),(40,24),(42,16)):offset(off,stride)
    put(f' lda.l {work}+8\n tax')
    put(' txa\n clc\n adc #$4000\n cmp.l $414000,x');branch('bne')
    put(' lda.l $414002,x\n cmp #$41');branch('bne')
    for tag in (32,40):
        put(f' lda.l {0x414000+tag},x\n cmp #1');branch('bne')
        put(f' lda.l {0x414002+tag},x');branch('bne')
    put(' lda.l $41402E,x');branch('bne');put(' lda.l $41402C,x\n cmp #4');branch('bcs')
    put(f' lda.l {work}+12\n tax\n lda.l $416800,x\n cmp #{count}');branch('bcs')
    put(f' sta.l {work}+22\n lda.l {work}+58');branch('bne','Publication')
    put(f' lda.l {work}+22\n sta.l {work}+20\n lda.l {work}+8\n tax')
    copy('$414000,x',f'{special}+184')
    put(f' lda.l {work}+12\n tax');copy('$40901C,x',f'{special}+92');copy('$409020,x',f'{special}+28')
    copy(f'{special}+92',f'{work}+32')
    # A null or dead-but-valid relation pointer follows the actual resolver.
    copy(f'{special}+92',str(symbols['SourceRetirement4086_ArgLo']))
    put(f' jsl {symbols["SourceRetirement4086_ResolvePointer"]}');branch('bcs')
    put(f' sta.l {work}+6\n cmp #65535');branch('beq','NoPeer')
    # Compute peer side/core/view with the captured slot, preserving main slot.
    put(f' lda.l {work}+4\n sta.l {work}+44\n lda.l {work}+6\n sta.l {work}+4')
    for off,stride in ((24,64),(26,96),(30,80)):offset(off,stride)
    put(f' lda.l {work}+44\n sta.l {work}+4\n lda.l {work}+30\n tax');copy('$43900C,x',f'{special}+96')
    put(f' lda.l {work}+24\n tax');copy('$40901C,x',f'{special}+100')
    put(f' lda.l {work}+26\n tax');copy('$40C050,x',f'{special}+104')
    label('NoPeer')
    mappings=((10,0x40c04c,52),(8,0x414024,56),(8,0x43900c,60),(10,0x40c058,64),(14,0x43eb00,68),
              (10,0x40c050,108),(40,0x42f404,112),(12,0x416824,116),(12,0x416828,120),(8,0x41402c,128),(18,0x42e008,132),(16,0x437e08,72))
    for off,addr,dest in mappings:
        put(f' lda.l {work}+{off}\n tax');copy(f'{addr},x',f'{special}+{dest}')
    put(f' lda.l {work}+42\n tax')
    for i in range(4):copy(f'{tail}+{4*i},x',f'{special}+{76+4*i}')
    copy('$43FD94',f'{special}+124')
    for i in range(4):
        copy(str(history+256*i+224),f'{special}+{136+4*i}')
        copy(str(history+256*i+216),f'{special}+{152+4*i}')
    for off in (44,48):put(f' lda #0\n sta.l {special}+{off}\n sta.l {special}+{off+2}')
    put(f' lda.l {work}+4\n sta.l {symbols["SourceAnimationInit4086_Slot"]}\n lda #{role}\n sta.l {symbols["SourceAnimationInit4086_Number"]}\n jsl {symbols["SourceAnimationInit4086_Resolve"]}');branch('bcs')
    put(f' lda #0\n sta.l {special}+168\n sta.l {special}+170\n lda.l {symbols["SourceAnimationInit4086_Handle"]}');branch('beq','Good')
    put(f' jsl {symbols["SourceAnimationEnergy4086_Query"]}');branch('bcs')
    put(f' lda #1\n sta.l {special}+168');copy(str(symbols['SourceCheckEnergy4086_Cost']),f'{special}+172')
    put(' jmp SpecialBinding_Good')
    label('Publication')
    put(f' lda.l {work}+22\n cmp.l {work}+20');branch('bne')
    copy(f'{work}+32',str(symbols['SourceRetirement4086_ArgLo']))
    put(f' jsl {symbols["SourceRetirement4086_ResolvePointer"]}');branch('bcs')
    put(f' cmp.l {work}+6');branch('bne')
    # All local fields and history are committed only after preflight.
    for off,addr,src in mappings:
        if src in (128,):continue
        put(f' lda.l {work}+{off}\n tax');copy(f'{special}+{src}',f'{addr},x')
    put(f' lda.l {work}+12\n tax');copy(f'{special}+92','$40901C,x')
    put(f' lda.l {work}+42\n tax')
    for i in range(4):copy(f'{special}+{76+4*i}',f'{tail}+{4*i},x')
    copy(f'{special}+124','$43FD94')
    for i in range(4):copy(f'{special}+{136+4*i}',str(history+256*i+224))
    put(f' lda.l {work}+6\n cmp #65535');branch('beq','Good')
    put(f' lda.l {work}+30\n tax');copy(f'{special}+96','$43900C,x')
    put(f' lda.l {work}+24\n tax');copy(f'{special}+100','$40901C,x')
    put(f' lda.l {work}+26\n tax');copy(f'{special}+104','$40C050,x')
    for name,status,carry in (('Good',2,'clc'),('Bad',4,'sec')):
        label(name);put(f' lda #{status}\n sta.l {work}+2\n ply\n plx\n pla\n plp\n {carry}\n rtl')
    return '\n'.join(lines)+'\n'
