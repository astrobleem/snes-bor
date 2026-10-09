"""Bind ground snapshots to canonical actors under explicit caller leases.

Context (level, time, captured player keys and notinair) belongs to the enclosing
controller. Mandatory animation/item/turn services are not supplied here.
"""
import struct
from source_model_core_4086 import GROUND_FIELDS


def emit(work, ground, state, run_work, handles, models, tuples, symbols):
    extents=((work,32),(ground,128),(state,64),(run_work,64),(handles,256))
    for i,(a,n) in enumerate(extents):
        if not 0<=a<=0x1000000-n:raise ValueError('GROUND_BINDING_EXTENT')
        if any(a<b+m and b<a+n for b,m in extents[i+1:]):raise ValueError('GROUND_BINDING_OVERLAP')
    if not 1<=len(models)<=16:raise ValueError('GROUND_BINDING_MODELS')
    if [(m['id'],m['source_sha256']) for m in models]!=[(m['id'],m['source_sha256']) for m in tuples['models']]:
        raise ValueError('GROUND_BINDING_PROFILE_IDENTITY')
    speeds=[]
    for raw in tuples['tuples']:
        f=struct.unpack_from('<f',bytes.fromhex(raw))[0];q=f*65536
        if not -2147483648<=q<=2147483647 or int(q)!=q:
            raise ValueError('GROUND_BINDING_RUN_Q16_INEXACT')
        speeds.append(int(q)&0xffffffff)
    lines=[];serial=0
    def put(s):lines.extend(s.strip().splitlines())
    def label(s):put('GroundBinding_'+s+':\n.a16\n.i16')
    def test(op,target='Bad'):
        nonlocal serial
        serial+=1;skip='GroundBinding_Skip'+str(serial)
        put({'beq':'bne','bne':'beq','bcc':'bcs','bcs':'bcc'}[op]+' '+skip)
        put(' jmp GroundBinding_'+target+'\n'+skip+':\n.a16\n.i16')
    def plus2(addr):
        return addr[:-2]+'+2,x' if addr.endswith(',x') else addr+'+2'
    def copy(src,dst):put(f' lda.l {src}\n sta.l {dst}\n lda.l {plus2(src)}\n sta.l {plus2(dst)}')
    for entry,mode in (('Capture',0),('Publish',1)):
        label(entry);put(f' php\n rep #$39\n pha\n phx\n phy\n lda #{mode}\n sta.l {work}+28\n jmp GroundBinding_Check')
    label('Check')
    for addr,magic in ((work,0xb67c),(ground,0xb679),(run_work,0xb678),
                       (symbols['VmSourceWorld_Ready'],0xb4a3),(symbols['VmSourceWorld_PoolBase'],0x4000)):
        put(f' lda.l {addr}\n cmp #{magic}');test('bne')
    put(f' lda.l {symbols["VmSourceWorld_Count"]}');test('beq')
    put(' cmp #129');test('bcs')
    put(f' lda.l {work}+4\n cmp.l {symbols["VmSourceWorld_Count"]}');test('bcs')
    # SourcePlayerState_Read validates the loaded module extent and generation.
    put(f' sta.l {state}+4\n jsl SourcePlayerState_Read');test('bcs')
    for offset,stride in ((8,80),(10,64),(12,24),(14,40),(16,32)):
        # Explicit shift/add multiplication, independent of decimal state.
        put(f' lda.l {work}+4\n sta.l {work}+30\n lda #0')
        for bit in range(stride.bit_length()-1,-1,-1):
            put(' asl a')
            if stride&(1<<bit):put(f' clc\n adc.l {work}+30')
        put(f' sta.l {work}+{offset}')
    put(f' lda.l {work}+8\n tax\n lda.l $414004,x\n ora.l $414006,x');test('beq')
    put(' lda.l $414018,x\n cmp #1');test('bne')
    put(' lda.l $41401A,x');test('bne')
    put(f' lda.l {work}+10\n tax\n lda.l $416800,x\n cmp #{len(models)}');test('bcs')
    put(f' sta.l {work}+22\n lda.l {work}+28');test('bne','Publication')
    put(f' lda.l {work}+22\n sta.l {work}+20')
    for i,m in enumerate(models):
        if m['id']!=i:raise ValueError('GROUND_BINDING_MODEL_ORDER')
        put(f' lda.l {work}+22\n cmp #{i}');test('beq','Model'+str(i))
    put(' jmp GroundBinding_Bad')
    for i,m in enumerate(models):
        label('Model'+str(i))
        for field,offset in zip(GROUND_FIELDS,(72,36)):
            value=m['fields'][field]&0xffffffff
            put(f' lda #{value&65535}\n sta.l {ground}+{offset}\n lda #{value>>16}\n sta.l {ground}+{offset+2}')
        put(' jmp GroundBinding_Run')
    label('Run');put(f' lda.l {work}+4\n asl a\n tax\n lda.l {handles},x')
    for i,v in enumerate(speeds):put(f' cmp #{i+1}');test('beq','Run'+str(i))
    put(' jmp GroundBinding_Bad')
    for i,v in enumerate(speeds):
        label('Run'+str(i));put(f' lda #{v&65535}\n sta.l {ground}+48\n lda #{v>>16}\n sta.l {ground}+50\n jmp GroundBinding_CaptureFields')
    mappings=((12,0x42f404,24),(8,0x41401c,28),(14,0x42e01c,32),
              (10,0x41683c,44),(10,0x416824,52),(10,0x416828,56),
              (8,0x43900c,60),(16,0x43eb00,64))
    label('CaptureFields')
    for off,address,dest in mappings:
        put(f' lda.l {work}+{off}\n tax');copy(f'{address},x',f'{ground}+{dest}')
    copy(f'{state}+36',f'{ground}+68');put(' jmp GroundBinding_Good')
    label('Publication')
    put(f' lda.l {work}+22\n cmp.l {work}+20');test('bne')
    # Wire 42 is a continuation request; it is not a registered native action.
    put(f' lda.l {ground}+60\n cmp #42');test('bne','PublishFields')
    put(f' lda.l {ground}+62');test('beq')
    label('PublishFields')
    put(f' lda #1\n sta.l {state}+6');copy(f'{ground}+68',f'{state}+20')
    put(' jsl SourcePlayerState_Write');test('bcs')
    for off,address,src in mappings:
        if src in (24,44):continue  # These model/running values are inputs only.
        put(f' lda.l {work}+{off}\n tax');copy(f'{ground}+{src}',f'{address},x')
    for name,status,carry in (('Good',2,'clc'),('Bad',3,'sec')):
        label(name);put(f' lda #{status}\n sta.l {work}+2\n ply\n plx\n pla\n plp\n {carry}\n rtl')
    return '\n'.join(lines)+'\n'
