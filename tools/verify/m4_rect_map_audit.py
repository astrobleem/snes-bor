"""Whole-ROM audit of the two exact source edits and required relocations."""
import hashlib
import struct
from m4_input_controller_native import offset
from actor_s5_entity_fixture import symbols
from rect_map_opt import transform,ORIGINAL_COMMIT

BASE_SHA='00622aaba27c82f20ed1ec6546de7a0ebce94f142b8b85f3de97a88f941b349a'
BRANCHES={'bcc','bcs','beq','bne','bpl','bmi','bra','bvc','bvs'}


def statements(lines,sy):
    pc=0;bank=0;a16=True;i16=True;out={}
    singles={'php','plp','pha','pla','phx','plx','phy','ply','phb','plb','phd','pld','tcd','txa','tax','tay','tya','iny','inx','clc','sec','rtl','rts','rti','nop','xba'}
    for i,text in enumerate(lines):
        s=text.strip().split(';',1)[0].strip()
        if not s or s=='.snes':continue
        if s.startswith('.bank'):bank=int(s.split()[1]);continue
        if s.startswith('.org'):pc=(bank<<16)+int(s.split()[1].replace('$','0x'),0);continue
        if s in ('.a16','.a8','.i16','.i8'):
            if s.startswith('.a'):a16=s=='.a16'
            else:i16=s=='.i16'
            continue
        if s.endswith(':'):
            if sy[s[:-1]]!=pc:raise ValueError('RECT_ASSEMBLED_SYMBOL_SIZE:'+s)
            continue
        if s.startswith('.db'):n=len(s.split(None,1)[1].split(','))
        else:
            op,_,arg=s.partition(' ')
            if op in singles or arg=='a':n=1
            elif op in BRANCHES or op in ('rep','sep'):n=2
            elif op in ('brl','jmp','jsr','mvn','mvp','pea'):n=3
            elif op in ('jml','jsl') or op.endswith('.l'):n=4
            elif arg.startswith('#'):n=1+(2 if (i16 if op in ('ldx','ldy','cpx','cpy') else a16) else 1)
            elif arg.startswith('['):n=2
            elif arg.startswith('$'):n=2 if len(arg.split(',')[0])<=3 else 3
            else:raise ValueError('RECT_UNKNOWN_INSTRUCTION_SIZE:'+s)
        out[i]=(pc,n,s);pc+=n
    return out


def audit(rom,native,base):
    old=(base/'bor.sfc').read_bytes()
    if hashlib.sha256(old).hexdigest()!=BASE_SHA:raise ValueError('RECT_CONTROL_IDENTITY')
    before=(base/'publisher.pasm').read_text().splitlines();after=(native/'publisher.pasm').read_text().splitlines()
    if after!=transform(before):raise ValueError('RECT_UNAUTHORIZED_SOURCE_EDIT')
    oldsy=symbols(base/'publisher.sym');sy=symbols(native/'publisher.sym')
    oi=statements(before,oldsy);ni=statements(after,sy)
    if not sy['WarmCommitMapRect']<sy['WarmMapDmaHigh']<sy['WarmSourcePresence']<sy['WarmDirectPair']==0x39d400:raise ValueError('RECT_D000_COLLISION')
    if sy['WarmPresenceDone']+1>0x39d400:raise ValueError('RECT_D000_OVERFLOW')
    expected=bytearray(old)
    for start,end in ((0x398000,0x39c000),(0x39d000,0x39d400)):expected[offset(start):offset(end)]=bytes(end-start)
    oc=before.index('OnlineMapsTransfer:');nc=after.index('OnlineMapsTransfer:')
    os=before.index('WarmSparseMaps:');ns=after.index('WarmSparseMaps:')
    oe=before.index('WarmMapDmaHigh:');ne=after.index('WarmMapDmaHigh:')
    mapping=[(0,oc,0),(oc+len(ORIGINAL_COMMIT),os,nc+5),(oe,len(before),ne)]
    relocations=[];covered=set()
    for begin,end,newbegin in mapping:
        for i in range(begin,end):
            j=newbegin+i-begin
            if before[i]!=after[j]:raise ValueError('RECT_UNCHANGED_STATEMENT_DRIFT')
            if i not in oi:continue
            opc,n,s=oi[i];pc,nn,ss=ni[j]
            if n!=nn:raise ValueError('RECT_UNCHANGED_INSTRUCTION_SIZE')
            data=bytearray(old[offset(opc):offset(opc)+n]);op,_,arg=s.partition(' ')
            if arg in oldsy and op in (BRANCHES|{'brl','jsr','jmp','jsl','jml'}):
                target=sy[arg]
                if op in BRANCHES or op=='brl':
                    delta=target-pc-n;data[1:]=delta.to_bytes(n-1,'little',signed=True)
                else:data[1:]=(target&((1<<(8*(n-1)))-1)).to_bytes(n-1,'little')
                if data!=old[offset(opc):offset(opc)+n]:relocations.append(dict(instruction=s,from_pc=opc,to_pc=pc))
            if rom[offset(pc):offset(pc)+n]!=data:raise ValueError('RECT_UNCHANGED_INSTRUCTION_BYTES:'+s)
            expected[offset(pc):offset(pc)+n]=data;covered.add(j)
    compiled=(native/'publisher.bin').read_bytes()
    inserted=[]
    for j in range(len(after)):
        if j not in ni or j in covered:continue
        pc,n,s=ni[j]
        if not (nc<=j<nc+5 or ns<=j<ne):raise ValueError('RECT_UNAUTHORIZED_INSERTION')
        data=compiled[offset(pc):offset(pc)+n]
        if len(data)!=n or rom[offset(pc):offset(pc)+n]!=data:raise ValueError('RECT_INSERTED_ASSEMBLY_BYTES')
        expected[offset(pc):offset(pc)+n]=data;inserted.append(pc)
    if rom!=expected:raise ValueError('RECT_UNRELATED_ROM_CHANGE')
    # In particular the old full committed->pending preflight MVN is among
    # unchanged statements, and direct DMA/kernels/assets remain identical.
    return dict(status='PASS',exact_source_transform=True,unchanged_instruction_checks=len(covered),
                relocated_instructions=relocations,inserted_instructions=len(inserted),
                scan_start=sy['WarmSparseMaps'],commit_start=sy['WarmCommitMapRect'],map_dma_start=sy['WarmMapDmaHigh'],
                d000_end=sy['WarmPresenceDone']+1,d400_start=sy['WarmDirectPair'],
                gap_before_direct_bytes=sy['WarmDirectPair']-sy['WarmPresenceDone']-1,
                full_preflight_clone_unchanged=True,direct_dma_and_both_kernels_unchanged=True,
                all_asset_and_non_code_rom_bytes_unchanged=True)
