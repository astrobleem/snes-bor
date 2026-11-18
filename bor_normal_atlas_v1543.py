"""Install the source timer atlas in the Normal BG2 scene's unused BG3 front-panel window."""
from bor_kula_caption_v1542 import correct as baseline
from bor_resident_hud_v1513 import TILES
from bor_stage_ink_v1528 import writer,PAIR,READ,WRITE
from bor_restart_burst_v1494 import offset
from bor_split_atlas_v1467 import far,imm
BODY=0x2b8000
SITE=0x1286b7
CLEAR=bytes.fromhex('a200088f182100cad0f9')
def mark(r,sy,addr,b):
    i=offset(addr)
    assert not any(r[i:i+len(b)]) and not any(addr<=v<addr+len(b) for t in sy for v in t.values() if type(v)is int),hex(addr)
    r[i:i+len(b)]=b

def stage_body():
    # StageFp_BG2BootDispatch already selected this source mode. The active
    # frontpanel owns BG2, so the legacy BG3 FP character cache is idle.
    # VMAIN is $80, stage load has NMI stopped and forced blank asserted.
    # Preserve the exact physical blank-map word and all 2048 writes.
    seta=lambda val:imm(0xa9,val)
    staddr=far(0x8f,0x2116);stw=far(0x8f,0x2118)
    b=bytearray(b'\x48'+seta(0x7480)+staddr)
    words=[int.from_bytes(TILES[k:k+2],'little') for k in range(0,len(TILES),2)]
    loads=0;acc=0x7480
    for word in words:
        if acc!=word:
            b+=seta(word);loads+=1;acc=word
        b+=stw
    b+=seta(0x6c00)+staddr+b'\x68'
    # Replace N loop iterations with literal stores, then restore the stock
    # LDX/loop for the remaining words. The terminal DEX preserves N/Z.
    # A16 STA.l to MMIO costs 32+12, LDA imm16 costs 24. Entry/exit
    # long jumps 32 each; PHA/PLA 30/36; each avoided taken DEX/BNE 36.
    fixed=2*32+30+36+2*(24+44)+loads*24+len(words)*44
    n=next(n for n in range((fixed+35)//36,2048) if any((36*n-fixed-22*k)>=0 and (36*n-fixed-22*k)%14==0 for k in range(7)))
    pad=36*n-fixed
    br=next(k for k in range(7) if pad>=22*k and (pad-22*k)%14==0)
    b+=b'\xea'*((pad-22*br)//14)+b'\x80\x00'*br
    b+=stw*n+imm(0xa2,2048-n)+CLEAR[3:]+far(0x5c,SITE+len(CLEAR))
    assert len(b)<0x4000 and n<2048
    return bytes(b),n

def correct(image,symbols):
    r=bytearray(baseline(image,symbols));s=symbols[0]
    site=offset(SITE);assert r[site:site+len(CLEAR)]==CLEAR and s['StageFp_BG2BootLoad__map']==SITE+3
    b,n=stage_body();mark(r,symbols,BODY,b)
    r[site:site+4]=far(0x5c,BODY)
    w=writer();pos=r.find(w,offset(s['OriginalBar1292']),offset(s['OriginalBar1292'])+500);assert pos>=0
    tail=PAIR*18+bytes([234])*34+b'\x80\x00'*5;assert w.endswith(tail)
    # Subpalette 1 index 3. All 21 compiled Normal front panels reserve
    # indices 4..7. Preserve both source reads and their order.
    red=READ+b'\xa9\x9d'+WRITE+READ+b'\xa9\x0c'+WRITE
    new=w[:-len(tail)]+red+PAIR*16+bytes([234])*38+b'\x80\x00'
    assert len(new)==len(w) and 2*16+38*14+22==34*14+5*22
    r[pos:pos+len(w)]=new
    r[0x7fdc:0x7fe0]=bytes.fromhex('ffff0000');v=sum(r)&65535;r[0x7fdc:0x7fe0]=(65535-v).to_bytes(2,'little')+v.to_bytes(2,'little')
    return bytes(r)
