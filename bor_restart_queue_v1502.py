"""Single-slot specialization after the retained general queue validator is selected."""
from bor_split_atlas_v1467 import Code, imm, far
from bor_restart_burst_v1494 import offset

BASE=0x29d500
ENTRY=0x31c33a
RESUME=0x31c3e0
def program():
    q=Code(BASE);q.put('0848')
    def load(a):q.put(far(0xaf,a))
    def save(a):q.put(far(0x8f,a))
    def cmp(v):q.put(imm(0xc9,v))
    def mask(v):q.put(imm(0x29,v))
    def refuse(op):q.when(op,'stock')
    # Source-owned StreamScroll_TileBufN, one ordinary 32-byte VRAM job.
    # The two packed comparisons authenticate the type and all three source
    # bytes. Restrict the inclusive destination span to the lower BG window.
    load(0x7e0480);cmp(32);refuse(0xd0)
    load(0x7e0484);cmp(0x0040);refuse(0xd0)
    load(0x7e0486);cmp(0x7f90);refuse(0xd0)
    load(0x7e0482);cmp(0x7fe1);refuse(0xb0);q.put(imm(0x89,1));refuse(0xd0)
    load(0x7e4600);mask(255);refuse(0xd0)
    load(0x7e048c)
    for i in range(2,8):q.put(far(0x0f,0x7e0484+i*8))
    mask(0x40);refuse(0xd0)
    # The retained range JSR leaves its return address in the two released stack bytes.
    # Preserve those bytes as well as live stack/registers for the alternate path.
    q.lab('valid');q.put('68286828');q.put(imm(0xa9,65535));save(0x43a888);q.put(imm(0xa9,0));save(0x43a886);q.put(imm(0xa9,1));save(0x43a86a)
    q.put(imm(0xa9,0x40));save(0x43a86e)
    load(0x7e0480);save(0x43a86c);save(0x43a870);q.put('3a');save(0x43a872)
    q.put('18');q.put(far(0x6f,0x7e0482));save(0x43545e)
    q.put(imm(0xa9,56));q.put('18690800aae04000');q.put('6b')
    q.lab('stock');q.put('6828');q.put(far(0x5c,0x32f900))
    return q.done(),q.labels
def correct(image,symbols):
    assert symbols[0]['StreamScroll_TileBufN']==0x7f9000
    raw=bytearray(image);addr=offset(ENTRY);start=offset(BASE);code,_=program()
    assert raw[offset(0x31c3d5):offset(0x31c3d5)+3]==bytes.fromhex('20d8c4')
    assert raw[addr:addr+7]==bytes.fromhex('a900008f6aa843')
    assert raw[offset(RESUME):offset(RESUME)+9]==bytes.fromhex('e220af1242002980f0')
    assert not any(raw[start:start+len(code)]) and not any(BASE<=v<BASE+len(code) for tab in symbols for v in tab.values() if type(v)is int)
    raw[start:start+len(code)]=code;seam=offset(0x30eeb1)
    assert raw[seam:seam+4]==far(0x5c,0x32f900) and image.count(far(0x22,0x30ee00))==1
    raw[seam:seam+4]=far(0x5c,BASE)
    raw[0x7fdc:0x7fe0]=bytes.fromhex('ffff0000')
    crc=sum(raw)&65535;raw[0x7fdc:0x7fe0]=(65535-crc).to_bytes(2,'little')+crc.to_bytes(2,'little')
    result=bytes(raw)
    verify(image,result)
    return result

def verify(image,result):
    from bor_owned_cpu_v610 import Cpu
    from pathlib import Path
    import itertools
    # The standard refusal reaches the common restore before its stack pops.
    needle=bytes.fromhex('2bab7afa68286b')
    pos=image.index(needle,offset(0x31c4b0),offset(0x31c4d8))
    exits={RESUME,0x31c4b0+pos-offset(0x31c4b0)}
    paths=[Path('/tmp/bor-model-v1502-stock'),Path('/tmp/bor-model-v1502-single')]
    for p,im in zip(paths,(image,result)):
        Cpu.assets[str((p/'product').resolve())]=(im,{'enter':0x31c331})
    def run(p,job):
        length,src,bank,dst,owner,flags,other=job[:7]
        q=Cpu(p);q.write(0x7e0480,length);q.write(0x7e0482,dst)
        q.write(0x7e0484,flags,1);q.write(0x7e0485,src);q.write(0x7e0487,bank,1)
        q.write(0x7e4600,owner,1);q.write(0x7e0478,job[7] if len(job)>7 else 0)
        if other:q.write(0x7e048c,64,1)
        q.run('enter',stop=exits)
        return (q.pc,q.a,q.x,q.y,q.d,q.s,q.p, {k:v for k,v in q.m.items() if v and not 0x7e1dc0<=k<=0x7e0000+q.s})
    cases=set()
    default=(32,0x8800,2,0xc000,0,0x40,False)
    for i,values in enumerate(((0,1,2,31,32,255,256,257,65535),(0,0x7fff,0x8000,0xffdf,0xffe0,0xffe1,0xffff),(0,0x3f,0x40,0x7e,0x7f,0x80),(0,1,0x7fe0,0x7fe2,0x8000,0xbffe,0xc000,0xffe0,0xffe2),(0,1,255),(0,0x40,0x41,0x42,0x44),(False,True))):
        for value in values:cases.add(default[:i]+(value,)+default[i+1:])
    for src,bank,dst,length in itertools.product((0,0x8100,0xffe0),(0x12,0x7e,0x7f),(0,0x8000,0xc000),(2,32,256)):
        cases.add((length,src,bank,dst,0,64,False))
    for i,values in enumerate(((0,31,32,33,256),(0x8fff,0x9000,0x9001),(0x7e,0x7f,0x80),(0,1,0x3d60,0x7fe0,0x7fe1,0x7fe2,0x8000,0xc000),(0,1,255),(0,0x40,0x41,0x42),(False,True))):
        slot=(32,0x9000,0x7f,0x3d60,0,0x40,False)
        for x in values:cases.add(slot[:i]+(x,)+slot[i+1:])
    cases.update((32,0x9000,0x7f,0x3d60,0,64,False,i) for i in range(0,65,8))
    for case in cases:
        stock=run(paths[0],case);candidate=run(paths[1],case)
        if stock!=candidate:raise ValueError(('queue specialization differs',case,stock[:7],candidate[:7]))
    print('QUEUE1502_LINKED',len(cases),flush=True)
