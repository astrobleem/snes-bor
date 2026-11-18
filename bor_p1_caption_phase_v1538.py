"""Use the existing P1 score-formatting window for its authenticated caption copy."""
from bor_p1_caption_v1534 import correct as base
from bor_split_atlas_v1467 import far,imm
from bor_restart_burst_v1494 import offset

N=3
def correct(image,symbols):
    r=bytearray(base(image,symbols));s=symbols[0];entry=0x2dea80
    old=imm(0xa2,0)+imm(0xa0,0x459)+far(0x22,0x00e986)
    assert r.count(old)==1
    i=r.index(old);assert r[i-2:i]==bytes.fromhex('a981')
    p=offset(s['Text_Str_HudScore']);stock=bytes(r[p:p+7])
    assert stock==b'SCORE \x00' and s['Text_Str_HudScore']-s['Text_StringPool']==0x459
    b=bytearray(bytes.fromhex('08c22048'))
    for index,c in enumerate(stock[:N]):
        b+=imm(0xa9,0x2400|(920+c-32))+far(0x8f,0x7e2700+2*index)
    # The traced first admission finishes 22 master clocks earlier. One local
    # slow-ROM BRA to the next instruction restores its original window.
    b+=bytes.fromhex('80006828')+far(0x5c,0x00e986)
    j=offset(entry);assert not any(r[j:j+len(b)]) and not any(entry<=v<entry+len(b) for t in symbols for v in t.values() if type(v)is int)
    r[j:j+len(b)]=b
    # X starts at the next cell; Y starts at the next actual stock glyph.
    # The existing formatter still writes every subsequent tile and all
    # numeric digits, including unmapped scores and unknown-roster fallback.
    r[i:i+len(old)]=imm(0xa2,N)+imm(0xa0,0x459+N)+far(0x22,entry)
    r[0x7fdc:0x7fe0]=bytes.fromhex('ffff0000');c=sum(r)&65535;r[0x7fdc:0x7fe0]=(65535-c).to_bytes(2,'little')+c.to_bytes(2,'little')
    return bytes(r)
