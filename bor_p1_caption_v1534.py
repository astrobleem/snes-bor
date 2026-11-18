"""Install the live P1 name/score caption, keeping P2's two score paths intact."""
from bor_timer_edges_v1532 import correct as base
from bor_score_rows_v1520 import patterns,programs,TABLE,CODE,LOOK
from bor_split_atlas_v1467 import Code,far,imm
from bor_restart_burst_v1494 import offset

def correct(image,symbols):
    r=bytearray(base(image,symbols));body,labels,ptrs=programs()
    def add(a,b):
        i=offset(a);assert not any(r[i:i+len(b)]) and not any(a<=v<a+len(b) for t in symbols for v in t.values() if type(v)is int),(hex(a),len(b));r[i:i+len(b)]=b
    def patch(a,old,new):
        i=offset(a);assert len(new)<=len(old) and r[i:i+len(old)]==old,hex(a);r[i:i+len(old)]=new+b'\xea'*(len(old)-len(new))
    # The source-hit index is already authorized and on the stack. All
    # records here have the retained 16-cell span. The original queue and
    # cache commit are shared after type/source installation.
    default=0x32d220;lookup=0x2df100;entry=0x2df400
    slots=[];stock=bytearray()
    for roster in range(256):
        slots.append((TABLE+3200*(roster-22)+4 if 22<=roster<=25 else default)&65535)
    for i in range(100):
        p=offset(0x27b000+64*i);stock+=r[p:p+32]
    assert TABLE+len(patterns())<=default and default+len(stock)<=0x330000
    for a,b in [(TABLE,patterns()),(default,stock),(LOOK,ptrs),(CODE,body),(lookup,b''.join(k.to_bytes(2,'little') for k in slots))]:add(a,b)
    q=Code(entry);q.put('da');q.put(far(0xaf,0x7e0a0c));q.put(imm(0x29,255));q.put('0aaaa3034a18')
    q.put(far(0x7f,lookup));q.put('fa');q.put(far(0x8f,0x7e0470))
    src=offset(0x27a973);seq=bytes.fromhex('a920d08f73047ea920008f75047ee220a9278f72047e')
    assert r[src:src+len(seq)]==seq
    q.put(seq.replace(bytes.fromhex('a920d0'),bytes.fromhex('a900d0')).replace(bytes.fromhex('a9278f'),bytes.fromhex('a9328f')));q.put(far(0x5c,0x27a989));add(entry,q.done())
    patch(0x27a93a,bytes.fromhex('186900b0'),far(0x5c,entry))
    patch(0x33e43a,bytes.fromhex('a900d08f73047e'),far(0x5c,labels['dirty0']))
    assert r[offset(0x27a96a):offset(0x27a976)]==bytes.fromhex('48186900c98f70047ea920d0')
    assert r[offset(0x33e460):offset(0x33e467)]==bytes.fromhex('a920d08f73047e')
    r[0x7fdc:0x7fe0]=bytes.fromhex('ffff0000');c=sum(r)&65535;r[0x7fdc:0x7fe0]=(65535-c).to_bytes(2,'little')+c.to_bytes(2,'little')
    return bytes(r)
