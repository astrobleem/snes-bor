"""Set the active Normal 1A HUD ink in the stage palette writer, inside its existing clock budget."""
from bor_target_rows_v1519 import correct as base
from bor_restart_burst_v1494 import offset

READ=bytes.fromhex('af012000')
WRITE=bytes.fromhex('8f222100')
PAIR=READ+WRITE
NOP=b'\xea'
BRA=bytes.fromhex('8000')
def writer():
    # M=8, X=16. EOR/ORA/AND preserve carry and the accumulator high byte.
    # Other scenes consume exactly the same MSU byte and keep all its bits.
    key=bytes.fromhex('af5e277e49030f8e267e0f58277e')
    yes=READ+bytes.fromhex('29fb8008')
    no=READ+bytes.fromhex('49004900')
    select=key+bytes((0xd0,len(yes)))+yes+no+WRITE
    assert len(no)==8 and 40+16+40+40==136
    assert 16+16+22==22+16+16
    assert 136+54+34*14+5*22==46*14+6*22
    return PAIR*5+select+PAIR*18+NOP*34+BRA*5

def correct(image,symbols):
    r=bytearray(base(image,symbols));s=symbols[0];b=s['OriginalBar1292']
    assert b==0x33f800
    prefix=READ*8
    for target,v in [(0x2121,1),(0x2122,255),(0x2122,34),(0x2121,3),(0x2122,255),(0x2122,123),(0x2121,4)]:
        prefix+=bytes((0xa9,v,0x8f))+target.to_bytes(3,'little')
    old=PAIR*24+NOP*46+BRA*6
    end=bytes.fromhex('a200005c')+s['OriginalBar1292Resume'].to_bytes(3,'little')
    i=offset(b);assert r[i:i+len(prefix+old+end)]==prefix+old+end
    new=prefix+writer()+end;length=max(len(new),len(prefix+old+end))
    assert not any(r[i+len(prefix+old+end):i+length])
    assert not any(b<v<b+length for table in symbols for v in table.values() if type(v)is int)
    r[i:i+length]=new+NOP*(length-len(new))
    r[0x7fdc:0x7fe0]=bytes.fromhex('ffff0000');c=sum(r)&65535
    r[0x7fdc:0x7fe0]=(65535-c).to_bytes(2,'little')+c.to_bytes(2,'little')
    return bytes(r)
