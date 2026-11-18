"""Preserve all six physics slots and ticks. Specialize the four fixed NPC slots."""
import bor_split_palette_v1476 as parent
from bor_split_atlas_v1467 import far,Code
compose=parent.compose
evidence=parent.evidence
observer=parent.observer
BASE=0x29ce00
def fix(raw,candidate,sy):
    raw=parent.fix(raw,candidate,sy);read=candidate.connected.link.read
    def expect(a,h):
        b=bytes.fromhex(h)
        if read(raw,a,len(b))!=b:raise ValueError("NPC physics contract "+hex(a))
    expect(0xf835c,'dabfeb80095b200f83a301aabf08597ed02622e68507b020e220a50fc907f018c2312236800fb006e220a523f00ac23122b2810f22b4800fc2316818690200aa')
    expect(0x980eb,'000a850a0a0b8f0b140c990c000085000a018f0114029902')
    expect(0xf830f,'2200800fbf67557ec90200d01c8af00ec98500d014afbd267e29ff00f00ba52329ff00f0042209800f60')
    expect(0xf8000,'c2317b38e9000aaa6b')
    expect(0x785e6,'c2317bc9000ad00bafcd267e290100f01d386bc231c9850ad014afbd267e290100f00bafce267e290100f002386b186b')
    expect(0xf8036,'2200800fbf67557ef002386b186b')
    q=Code(BASE);q.put('dabfeb80095be00400');q.when(0x90,'player')
    # Slots 2..5 can neither be reconciled as a player nor be PlayerOut.
    # Preserve pending, noncombat, owned-state and HP test order and original
    # Tick/Enter. The offset table is authenticated above for every slot.
    q.put('bf08597e');q.when(0xd0,'next')
    q.put('e220a50fc907');q.when(0xf0,'next')
    q.put('c231bff78009aabf67557e');q.when(0xd0,'owned')
    q.put('e220a523');q.when(0xf0,'next')
    q.lab('owned');q.put(far(0x5c,0xf838a));q.lab('next');q.put(far(0x5c,0xf8394))
    q.lab('player');q.put(far(0x5c,0xf8362))
    expect(0xf838a,'c23122b2810f22b4800f')
    code=q.done()
    if any(BASE<=v<BASE+len(code) for tab in sy for v in tab.values() if type(v)is int):raise ValueError("occupied NPC helper")
    return candidate.finish_bytes(raw,raw,(),[(BASE,code)],[(0xf835c,bytes.fromhex('dabfeb80'),far(0x5c,BASE))])[0]
