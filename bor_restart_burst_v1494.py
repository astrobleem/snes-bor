"""Join the four contiguous 512-byte atlas pieces only in an early, owned vblank."""
from bor_split_atlas_v1467 import CHUNKS, ROW, Code, far, imm
import bor_split_budget_v1473 as budget

BASE = 0x29D300
def offset(address):
    return (address >> 16) * 32768 + (address & 32767)

def program():
    old, labels = budget.program()
    part = lambda a, b: old[a-budget.BASE:b-budget.BASE]
    src, dest, size = CHUNKS[4]
    assert all(item == (src+512*i, dest+256*i, 512) for i,item in enumerate(CHUNKS[4:]))
    descriptor = part(labels['s4'], labels['s5'])
    assert descriptor.endswith(far(0x5c,labels['sample']))
    trigger = bytes.fromhex('988f162100e220a9808f1521008f0b4200eaea')
    sample = part(labels['sample'],labels['physical'])
    assert sample.count(trigger)==1 and sample.endswith(trigger)
    q=Code(BASE)
    q.put(descriptor[:-4]); q.put(sample[:-len(trigger)])
    # X is the freshly latched low scanline; the inherited code rejected high
    # bit, non-vblank and lines outside 225..253. A 2048-byte general DMA
    # needs 16384 master clocks, about 12 lines. Keep the later 512-byte path.
    q.put(imm(0xe0,245)); q.when(0xb0,'single')
    q.put(imm(0xa9,2048)+far(0x8f,0x4375)); q.put(trigger); q.lab('complete')
    q.put('c220'); q.put(far(0xaf,ROW)+bytes.fromhex('18690400')+far(0x8f,ROW))
    q.put(far(0x5c,labels['restore']))
    q.lab('single'); q.put(far(0x5c,labels['sample']))
    return q.done(),q.labels,labels

def patch(image,symbols):
    code,labels,stock=program(); old,_=budget.program(); raw=bytearray(image)
    start=offset(budget.BASE);loc=offset(BASE)
    if raw[start:start+len(old)]!=old or any(raw[loc:loc+len(code)]):
        raise ValueError('exact retained upload program and reserved ROM space required')
    if any(BASE<=val<BASE+len(code) for table in symbols for val in table.values() if type(val)is int):
        raise ValueError('occupied helper')
    at=offset(stock['s4']); raw[at:at+4]=far(0x5c,BASE); raw[loc:loc+len(code)]=code
    raw[0x7fdc:0x7fe0]=bytes.fromhex('ffff0000')
    total=sum(raw)&65535;raw[0x7fdc:0x7fe0]=(65535-total).to_bytes(2,'little')+total.to_bytes(2,'little')
    return bytes(raw)
