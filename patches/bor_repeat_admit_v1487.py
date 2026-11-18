"""Let the normal poll service an unread jump before starting a fresh warm plan."""
import bor_split_physics_v1483 as parent
from bor_split_atlas_v1467 import Code,far
compose=parent.compose
evidence=parent.evidence
BASE=0x29d100
def helper():
    q=Code(BASE)
    q.put('08e220');q.put(far(0xaf,0x4212));q.put('2901c220');q.when(0xd0,'ordinary')
    for j,(pad,held) in enumerate(((0x4218,0x7e0410),(0x421a,0x7e0416))):
        key='next'+str(j)
        q.put(far(0xaf,pad));q.put('890f00');q.when(0xd0,'ordinary')
        q.put('898000');q.when(0xf0,key)
        q.put(far(0xaf,held));q.put('898000');q.when(0xf0,'defer')
        q.lab(key)
    q.lab('ordinary');q.put('28a90000');q.put(far(0x8f,0x433444));q.put(far(0x5c,0x3dab13))
    q.lab('defer');q.put('28');q.put(far(0x5c,0x3db057));return q.done(),q.labels
def fix(raw,candidate,sy):
    raw=parent.fix(raw,candidate,sy);read=candidate.connected.link.read
    sig=bytes.fromhex('af504e430f744e4329ff00f003824b05a900008f443443a308')
    a=0x3daafc
    if read(raw,a,len(sig))!=sig or read(raw,0x3db057,8).hex()!='2bab7afa6828186b':raise ValueError('fresh original warm path')
    p=a+16;b,l=helper()
    if p+7!=0x3dab13:raise ValueError('plan continuation')
    if any(BASE<=x<BASE+len(b) for x in sy[0].values() if type(x)is int) or any(BASE<=x<BASE+len(b) for x in sy[1].values() if type(x)is int):raise ValueError('occupied helper')
    return candidate.finish_bytes(raw,raw,(),[(BASE,b)],[(p,sig[16:20],far(0x5c,BASE))])[0]
observer=parent.observer
