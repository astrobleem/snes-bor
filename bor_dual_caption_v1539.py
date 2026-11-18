"""Apply the independent score-row formatting budget to the P2 caption."""
from bor_p1_caption_phase_v1538 import correct as base
from bor_score_rows_v1520 import TABLE,programs
from bor_split_atlas_v1467 import far,imm,Code
from bor_restart_burst_v1494 import offset

def correct(image,symbols):
    r=bytearray(base(image,symbols));s=symbols[0]
    def add(a,b):
        i=offset(a);assert not any(r[i:i+len(b)]) and not any(a<=v<a+len(b) for t in symbols for v in t.values() if type(v)is int),hex(a);r[i:i+len(b)]=b
    def patch(a,old,b):
        i=offset(a);assert len(b)<=len(old) and r[i:i+len(old)]==old,hex(a);r[i:i+len(old)]=b+bytes([0xea])*(len(old)-len(b))
    default,lookup,entry=0x32e000,0x2dfc00,0x2dfe00
    stock=bytearray()
    for n in range(100):
        p=offset(0x27c900+64*n);stock+=r[p:p+32]
    add(default,stock);add(lookup,b''.join(((TABLE+3200*(i-22) if 22<=i<=25 else default)&65535).to_bytes(2,'little') for i in range(256)))
    q=Code(entry);q.put('da');q.put(far(0xaf,0x7e0a91));q.put(imm(0x29,255));q.put('0aaaa3034a18');q.put(far(0x7f,lookup));q.put('fa');q.put(far(0x8f,0x7e0470))
    a=offset(0x27a973);old=bytes.fromhex('a920d08f73047ea920008f75047ee220a9278f72047e')
    assert r[a:a+len(old)]==old;q.put(old.replace(bytes.fromhex('a9278f'),bytes.fromhex('a9328f')));q.put(far(0x5c,0x27a989));add(entry,q.done())
    patch(0x27a96b,bytes.fromhex('186900c9'),far(0x5c,entry))
    patch(0x33e460,bytes.fromhex('a920d08f73047e'),far(0x5c,programs()[1]['dirty1']))
    n=3;stub=0x2deb40
    text=bytes(r[offset(s['Text_Str_HudP2Score']):offset(s['Text_Str_HudP2Score'])+7]);assert text==b'P2SCOR\x00'
    old=imm(0xa2,0)+imm(0xa0,0x46e)+far(0x22,0x00e986);i=r.index(old);assert r.count(old)==1 and r[i-4:i]==bytes.fromhex('a988c210')
    b=bytearray(bytes.fromhex('08c22048'))
    for k,c in enumerate(text[:n]):b+=imm(0xa9,0x2400|(920+c-32))+far(0x8f,0x7e2700+k*2)
    b+=bytes.fromhex('80006828')+far(0x5c,0x00e986);add(stub,b)
    r[i:i+len(old)]=imm(0xa2,n)+imm(0xa0,0x46e+n)+far(0x22,stub)
    r[0x7fdc:0x7fe0]=bytes.fromhex('ffff0000');c=sum(r)&65535;r[0x7fdc:0x7fe0]=(65535-c).to_bytes(2,'little')+c.to_bytes(2,'little')
    return bytes(r)
