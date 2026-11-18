"""Publish DOS Kula lettering through the existing mutable and source-hit rows."""
from bor_p2_hit_budget_v1540 import correct as baseline
from bor_timer_edges_v1532 import TILES, READ_PAIR, STOCK
from bor_restart_burst_v1494 import offset
from bor_split_atlas_v1467 import far,imm
CAPTION=bytes.fromhex('0000004804480c501a602250044b0500000000002000208c6e906a90628ce600000000000000000000000038000000000000004040a050a050a050a030402000')

def upload():
    glyphs=CAPTION+TILES
    assert len(glyphs)==128 and (0x6000+912*8)==0x7c80
    code=bytearray(imm(0xa9,0x7c80)+imm(0x8d,0x2116))
    for k in range(0,len(glyphs),2):
        code+=imm(0xa9,int.from_bytes(glyphs[k:k+2],'little'))+imm(0x8d,0x2118)
    return bytes(code)+imm(0xa9,0x7400)+imm(0x8d,0x2116)+b'\x8a'

def paths(body,loop):
    # Match the accepted four-tile loader. The additional 32 word writes
    # (60 master clocks each) are paid by unrolling 24 more original reads.
    assert 32*(24+36)==24*(22+22+14+22)
    up=upload()
    ordinary=bytes.fromhex('0a0a0aaa')+imm(0xe0,96)+bytes.fromhex('f004')+far(0x5c,body+0x580)
    ordinary+=up+b'\xe2\x20'+READ_PAIR*52+b'\xc2\x31'+imm(0xa2,44)*2+far(0x5c,loop)
    other=up+bytes.fromhex('18f004')+far(0x5c,loop)+far(0x5c,loop+len(STOCK))
    assert len(ordinary)<0x580 and 0x580+len(other)<0x800
    return ordinary,other

def correct(image,symbols):
    r=bytearray(baseline(image,symbols));s=symbols[0]
    for name,prior,body in [('Bg_LoadScene__hud',0x2dd000,0x2bc000),('Bg_LoadScene_Streaming__hud_loop',0x2dd400,0x2bc800)]:
        loop=s[name];p=offset(loop)-6
        assert r[p:p+6]==far(0x5c,prior)+b'\xea\xea' and r[p+6:p+6+len(STOCK)]==STOCK
        for a,data in zip((body,body+0x580),paths(body,loop)):
            i=offset(a)
            assert not any(r[i:i+len(data)]) and not any(a<=v<a+len(data) for group in symbols for v in group.values() if type(v)is int),hex(a)
            r[i:i+len(data)]=data
        r[p:p+4]=far(0x5c,body)
    space=0x2798
    def native(c):return 0x2400|(920+ord(c)-32)
    for n in range(100):
        value=str(5*n)
        old=('    Kula - '+value).ljust(16)
        expected=b''.join(native(c).to_bytes(2,'little') for c in old)
        # The shared P1 pointer advances two cells. Leading/trailing spaces
        # keep the subsequent record and other rosters untouched.
        words=[space]*4+[0x2400|i for i in (912,913,914)]
        words.extend((0x2400|915) if c=='0' else native(c) for c in value)
        words+=[space]*(16-len(words))
        data=b''.join(w.to_bytes(2,'little') for w in words)
        for a in (0x32a000+32*n,0x27c900+64*n):
            i=offset(a);assert r[i:i+32]==expected,hex(a);r[i:i+32]=data
    r[0x7fdc:0x7fe0]=bytes.fromhex('ffff0000');c=sum(r)&65535
    r[0x7fdc:0x7fe0]=(65535-c).to_bytes(2,'little')+c.to_bytes(2,'little')
    return bytes(r)
