"""Validate exactly the rows an immutable slice will touch; latch at the trigger."""
import bor_split_atlas_v1467 as sp
import bor_split_tail_v1470 as tail
import bor_split_probe_v1467 as prev
BASE=0x29c000
compose=prev.compose
evidence=prev.evidence
def program():
    q=sp.Code(BASE);I=sp.imm;L=sp.far
    q.put("08c23048da5a");q.put(L(0xaf,sp.ROW)+I(0xc9,sp.BASE_MARK));q.when(0x90,"done")
    q.put(I(0xc9,sp.BASE_MARK+8));q.when(0xb0,"done")
    for a,val,mask in ((0x7e2750,0,65535),(0x7e2758,0,65535),(0x7e275e,3,255),(0x7e5005,0,128),(0x7e5006,0,128)):
        q.put(L(0xaf,a))
        if mask!=65535:q.put(I(0x29,mask))
        q.put(I(0xc9,val));q.when(0xd0,"done")
    q.put('e220af1242002980');q.when(0xf0,'done')
    q.put('c220');q.put(L(0xaf,sp.ROW)+I(0xc9,sp.BASE_MARK+4));q.when(0xb0,'last')
    # Each of the first four rows spans five 16x32 OBJ records. Each of
    # the last four rows spans eight. Check all owners of this transfer.
    for group,indices in [('first',range(5)),('last',range(5,13))]:
        q.lab(group)
        for i in indices:
            if i:q.put(L(0xaf,sp.ROW+i*8)+I(0xc9,sp.BASE_MARK+16+i));q.when(0xd0,"done")
            q.put(L(0xaf,sp.ROW+8*i+2)+I(0xc9,sp.PRIVATE));q.when(0xd0,"done")
            q.put(L(0xaf,sp.ROW+8*i+4)+I(0x29,255));q.when(0xd0,"done")
        if group=='first':q.go('setup')
    q.lab('setup');q.put('e220')
    for i in range(7):q.put(L(0xaf,0x4370+i)+b'\x48')
    q.put('a9018f704300a9188f714300a9308f744300c220')
    q.lab('dispatch');q.put(L(0xaf,sp.ROW))
    for i in range(7):q.put(I(0xc9,sp.BASE_MARK+i));q.when(0xf0,'s'+str(i))
    q.go('s7')
    for i,(src,dest,size) in enumerate(sp.CHUNKS):
        q.lab('s'+str(i));q.put(I(0xa9,src&65535)+L(0x8f,0x4372)+I(0xa9,size)+L(0x8f,0x4375)+I(0xa0,dest));q.go('sample')
    q.lab('sample');q.put('e220af1242002980');q.when(0xf0,'restore')
    q.put('af1342004809808f014200af372100af3f2100af3d2100c22029ff00aae220af3d21002901eb688f014200ebc220290100');q.when(0xd0,'restore')
    q.put(I(0xe0,225));q.when(0x90,'restore')
    q.put(I(0xe0,254));q.when(0xb0,'restore')
    q.put('988f162100e220a9808f1521008f0b4200eaea')
    q.lab('physical');q.put('c220');q.put(L(0xaf,sp.ROW)+b'\x1a'+L(0x8f,sp.ROW))
    # S-CPU WRAM cannot change between these instructions in the same NMI.
    # Each group has a common authenticated row set. Never cross a group
    # boundary without yielding, and re-latch the raster before every trigger.
    q.put(I(0x29,3));q.when(0xd0,'dispatch')
    q.lab('restore');q.put('e220')
    for i in reversed(range(7)):q.put(b'\x68'+L(0x8f,0x4370+i))
    q.lab('done');q.put('c2307afa68286b')
    return q.done(),q.labels
def fix(raw,candidate,sy):
    raw=tail.fix(raw,candidate,sy);code,labels=program();read=candidate.connected.link.read
    if any(BASE<=v<BASE+len(code) for tab in sy for v in tab.values() if type(v)is int):raise ValueError("occupied helper")
    tr=read(raw,tail.TRAMP,40);pat=sp.far(0x22,sp.NMI+4)
    if tr.count(pat)!=1:raise ValueError("committed NMI tail seam")
    return candidate.finish_bytes(raw,raw,(),[(BASE,code)],[(tail.TRAMP+tr.index(pat),pat,sp.far(0x22,BASE))])[0]
def observer(source,reset,raw,read):
    t=prev.observer(source,reset,raw,read);q=read(raw,sp.NMI,0x900);sig=bytes.fromhex("e220a9808f0b4200688f764300")
    offs=lambda a:(a>>16)*32768+(a&32767)
    old=offs(sp.NMI+q.index(sig)+8);new=offs(program()[1]["physical"])
    token=",%d,%d,"%(old,old)
    if t.count(token)!=1:raise ValueError("physical observer seam")
    return t.replace(token,",%d,%d,"%(new,new))
