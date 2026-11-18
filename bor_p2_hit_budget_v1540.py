"""Use the original fixed-stride hit rows for alternate Kula, with a roster-aware fallback."""
from bor_dual_caption_v1539 import correct as base
from bor_restart_burst_v1494 import offset
from bor_split_atlas_v1467 import far,imm

def correct(image,symbols):
    r=bytearray(base(image,symbols))
    def get(a,n):i=offset(a);return bytes(r[i:i+n])
    def write(a,b):i=offset(a);r[i:i+len(b)]=b
    def branch(op,at,to):
        delta=to-at-2;assert -128<=delta<=127,(hex(at),hex(to));return bytes((op,delta&255))
    p2,req,done=0x27a947,0x27a976,0x27a9c0
    mirror=0x27a9c2;slow=0x2dfee0
    stock=get(req,0x27a9b0-req)
    assert stock[:4]==far(0x8f,0x7e0473) and stock[-2:]==bytes.fromhex('8010')
    # Preserve the P1 queue-refusal and final cache paths even though the
    # matched replay scores its three hits with P2.
    p1=bytearray(stock[:-2]);p1+=branch(0x80,mirror+len(p1),done)
    for oldat,dest in ((0x27a996,done),(0x27a99c,0x27a9b0)):
        pos=oldat-req;assert p1[pos] in (0x90,0xf0)
        p1[pos:pos+2]=branch(p1[pos],mirror+pos,dest)
    assert not any(get(mirror,len(p1))) and mirror+len(p1)<=0x27aa00
    write(mirror,p1)
    assert get(0x27a945,2)==branch(0x80,0x27a945,req);write(0x27a945,branch(0x80,0x27a945,mirror))
    for origin in (0x2df400,):
        tail=far(0x5c,0x27a989);b=get(origin,80);assert b.count(tail)==1
        write(origin+b.index(tail),far(0x5c,mirror+(0x27a989-req)))
    # Keep validation and the existing general named-table selection for
    # every other model/palette word. This includes other Kula variants.
    stockentry=get(p2,0x27a96b-p2)
    assert stockentry.startswith(far(0xaf,0x7e58d7)) and stockentry.endswith(b'\x48')
    other=stockentry+far(0x5c,0x2dfe00)
    assert not any(get(slow,len(other))) and not any(slow<=v<slow+len(other) for t in symbols for v in t.values() if type(v)is int)
    write(slow,other)
    # The full checked live word contains roster 22 and the normal P2
    # alternate byte. A mismatch always goes through the general validator.
    prefix=bytes.fromhex('a50cc91601')
    parts=[(0xd0,p2),far(0xaf,0x7e58d7),(0xd0,done),far(0xaf,0x7e58d5),imm(0xc9,500),(0xb0,done),bytes.fromhex('0aaa'),far(0xbf,0x27aa00),(0x30,done),b'\x48',imm(0x69,0xc900),far(0x8f,0x7e0470),imm(0xa9,0xd020)]
    start=req-len(prefix)-sum(2 if isinstance(x,tuple) else len(x) for x in parts)
    assert start>=p2+4
    b=bytearray(prefix)
    for x in parts:b+=branch(x[0],start+len(b),x[1]) if isinstance(x,tuple) else x
    assert start+len(b)==req
    assert get(0x27a914,2)==branch(0xf0,0x27a914,p2)
    write(0x27a914,branch(0xf0,0x27a914,start));write(p2,far(0x5c,slow));write(start,b)
    # ASL on a validated low score (0..499) cleared carry. TAX, LDA,
    # BMI and PHA preserve it. The general path keeps its original arithmetic.
    assert get(0x27a998,6)==bytes.fromhex('7bc9850af012')
    cache=get(0x27a9b0,18);assert cache.endswith(bytes.fromhex('286b'))
    write(0x27a998,b'\xea'+cache)
    for n in range(100):
        src=0x27c900+64*n
        assert get(src,32)==get(0x32e000+32*n,32)
        write(src,get(0x32a000+32*n,32))
    r[0x7fdc:0x7fe0]=bytes.fromhex('ffff0000');c=sum(r)&65535;r[0x7fdc:0x7fe0]=(65535-c).to_bytes(2,'little')+c.to_bytes(2,'little')
    return bytes(r)
