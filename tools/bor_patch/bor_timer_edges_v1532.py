"""Install Joe and both fixed middle-row timer edge tiles in the stage HUD window."""
from bor_stage_ink_v1528 import correct as base
from bor_restart_burst_v1494 import offset
from bor_split_atlas_v1467 import Code,far,imm
TILES=bytes.fromhex('010201020102010201020102010201028000800080008000800080008000800000080408040b060806480c333900000000000000003044b87c80c03098000000')
READ_PAIR=bytes.fromhex('ad01208d1821ad01208d1921')
STOCK=bytes.fromhex('e220')+READ_PAIR+bytes.fromhex('c231cad0ed')

def upload():
    # Caller already set VMAIN for paired $2118/$2119 writes. This block
    # touches no DMA channel. Restore the original HUD VRAM start afterward.
    b=bytearray(imm(0xa9,0x7ca0)+imm(0x8d,0x2116))
    for i in range(0,len(TILES),2):
        b+=imm(0xa9,int.from_bytes(TILES[i:i+2],'little'))+imm(0x8d,0x2118)
    return bytes(b)+imm(0xa9,0x7400)+imm(0x8d,0x2116)+b'\x8a'

def build(body,loop):
    # Replace three ASLs, TAX and the initial count-zero branch. The
    # original loop and epilogue remain reachable with exactly the old ABI.
    q=Code(body);q.put('0a0a0aaa');q.put(imm(0xe0,96));q.put('f004');q.put(far(0x5c,body+0x280))
    q.put(upload());q.put('e220')
    for _ in range(28):q.put(READ_PAIR)
    q.put('c231');q.put(imm(0xa2,68));q.put(far(0x5c,loop))
    b=q.done()
    # 96-word taken short branch is 22 clocks (the ordinary initial BEQ
    # was 16). Balance the saved twenty-eight loop-control visits, including
    # both JMLs, using exact slow-ROM/internal/PPU-bus prices.
    saved=28*(22+22+14+22)
    extra=32+24+(22-16)+34*(24+36)+14+22+22+24+32
    assert saved-extra==24
    # LDX #68 twice is 24 clocks, clobbers no additional state.
    tail=imm(0xa2,68)+far(0x5c,loop);assert b.endswith(tail)
    b=b[:-len(tail)]+imm(0xa2,68)+tail
    assert len(b)<0x280
    # Zero and nonstandard counts have their own complete install. TXA
    # restores the original count (including B) and CLC undoes CPX carry.
    # CPX sets carry. Use TXA to set Z and avoid disturbing C after CLC.
    slow=upload()+bytes.fromhex('18f004')+far(0x5c,loop)+far(0x5c,loop+len(STOCK))
    return b,slow

def correct(image,symbols):
    r=bytearray(base(image,symbols));s=symbols[0]
    for name,body in [('Bg_LoadScene__hud',0x2dd000),('Bg_LoadScene_Streaming__hud_loop',0x2dd400)]:
        loop=s[name];i=offset(loop);assert r[i-6:i+len(STOCK)]==bytes.fromhex('0a0a0aaaf013')+STOCK
        for addr,data in zip((body,body+0x280),build(body,loop)):
            j=offset(addr);assert not any(r[j:j+len(data)]) and not any(addr<=v<addr+len(data) for t in symbols for v in t.values() if type(v)is int)
            r[j:j+len(data)]=data
        r[i-6:i]=far(0x5c,body)+bytes.fromhex('eaea')
    assert s['HudOpponent_Name2']==0x058458 and 656+256<918 and 918+2==920
    i=offset(s['HudOpponent_Row__print']-13);assert r[i:i+3]==imm(0xc9,32);r[i:i+3]=imm(0xc9,30)
    i=offset(s['HudOpponent_Name2']);assert r[i:i+4]==b'Joe\0';r[i:i+4]=bytes((30,31,32,0))
    # The live timer owns these two cells already. Its blank and TIME OVER
    # row keep their own original entries and transfer address.
    timer=s['StageTimerHost_TimerRows']
    assert timer==0x108a24 and s['StageTimerHost_TimeOverRow']==timer+1800
    for n in range(100):
        for col,tile in [(3,916),(6,917)]:
            i=offset(timer+n*18+col*2)
            assert r[i:i+2]==bytes.fromhex('9827')
            r[i:i+2]=(0x2400|tile).to_bytes(2,'little')
    r[0x7fdc:0x7fe0]=bytes.fromhex('ffff0000');c=sum(r)&65535;r[0x7fdc:0x7fe0]=(65535-c).to_bytes(2,'little')+c.to_bytes(2,'little')
    return bytes(r)
