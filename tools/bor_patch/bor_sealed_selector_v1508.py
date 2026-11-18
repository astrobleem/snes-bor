"""Shorten the read-only direct-publish authorization for one validated scroll job."""
from bor_scroll_window_v1507 import correct as window,gate,GATE
from bor_packed_channel_v1506 import BASE as CHANNEL
from bor_restart_burst_v1494 import offset
from bor_split_atlas_v1467 import Code,far,imm
SELECT=0x29dc00
def select():
    q=Code(SELECT);jumps=[]
    q.put('08c230488be220a94348abc220')
    def read(a):
        if a>>16==0x43:q.put(imm(0xad,a&65535))
        else:q.put(far(0xaf,a))
    def test(a,b,op=0xd0):
        read(a)
        if b is not None:
            if b<=65535:q.put(imm(0xc9,b))
            elif b>>16==0x43:q.put(imm(0xcd,b&65535))
            else:q.put(far(0xcf,b))
        q.put(bytes((op,0)));jumps.append(len(q.buf)-1)
    # Any other source follows the existing selector before changing game data.
    test(0x439400,0x5049);test(0x43a580,1);test(0x43a598,1)
    test(0x43960a,None,0xf0)  # retained palette pin search already completed
    test(0x43a582,None);test(0x43a580,1);test(0x43a598,1)
    test(0x439608,1);test(0x439602,None)
    q.put('8007');q.lab('slow1');q.put('ab6828');q.put(far(0x5c,0x3089c1))
    cut=len(jumps)
    test(0x43a580,1);test(0x43a598,1);test(0x43a500,0x524c)
    test(0x439400,0x5049);test(0x412002,0x412004);test(0x41200c,None)
    test(0x412440,0x412442);test(0x43a710,0xce51)
    for a,b in ((0xa708,0xa712),(0xa70a,0xa714),(0x9402,0xa716),(0x9404,0xa718),(0x9406,0xa71a),(0x9408,0xa71c)):test(0x430000+a,0x430000+b)
    q.put('ab');q.put(far(0x22,SELECT+0x160));q.put('900768e220a990286b68286b')
    q.lab('slow2');q.put('ab6828');q.put(far(0x5c,0x3089c1))
    for i,pos in enumerate(jumps):
        d=q.labels['slow1' if i<cut else 'slow2']-SELECT-pos-1
        assert -128<=d<=127;q.buf[pos]=d&255
    assert len(q.buf)<0x160
    q.buf.extend(bytes(0x160-len(q.buf)))
    # Same original seal writes, fresh raster measurement, refusal and receipt semantics.
    q.put('08c23048');q.put(far(0x5c,0x30a868))
    return q.done()
def correct(image,symbols):
    raw=bytearray(window(image,symbols));p=offset(SELECT);data=select()
    assert not any(raw[p:p+len(data)]) and not any(SELECT<=v<SELECT+len(data) for s in symbols for v in s.values() if type(v)is int)
    orig=offset(0x31c44c);end=offset(0x31c4ca)
    copy=bytearray(raw[orig:end]);call=far(0x22,0x3089c1);assert copy.count(call)==1
    i=copy.index(call);copy[i:i+4]=far(0x22,SELECT);copy.extend(far(0x5c,0x31c4ca))
    old=raw[offset(CHANNEL):offset(CHANNEL)+len(copy)]
    from bor_packed_channel_v1506 import program
    packed=program()[0];assert old.startswith(packed) and not any(old[len(packed):])
    assert raw[offset(0x30a868):offset(0x30a868)+4]==far(0xaf,0x439402)
    raw[p:p+len(data)]=data;raw[offset(CHANNEL):offset(CHANNEL)+len(copy)]=copy
    raw[0x7fdc:0x7fe0]=bytes.fromhex('ffff0000');crc=sum(raw)&65535
    raw[0x7fdc:0x7fe0]=(65535-crc).to_bytes(2,'little')+crc.to_bytes(2,'little')
    return bytes(raw)
