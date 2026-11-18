"""Use the free stage-caption row to move each live opponent eight pixels toward its DOS position."""
from bor_multiplier_rows_v1512 import correct as base
from bor_restart_burst_v1494 import offset
from bor_split_atlas_v1467 import imm

def correct(image,symbols):
    r=bytearray(base(image,symbols));s=symbols[0]
    # Old stage caption was the sole ordinary HUD text writer for row 3.
    assert r[offset(0x0587b1):offset(0x0587b1)+4]==bytes.fromhex('5cc78705')
    for player in (0,1):
        old=0xd100+32*player;new=old-64
        sites=((0x058371 if player else 0x058376,0xa9),
               (0x33ed38 if player else 0x33ed42,0xc9),
               (0x33edb2 if player else 0x33edbc,0xc9))
        for address,op in sites:
            i=offset(address);assert r[i:i+3]==imm(op,old),(hex(address),r[i:i+3].hex())
            r[i:i+3]=imm(op,new)
    # Left and right own adjacent 16-cell rectangles on rows 3 and 4. The
    # physical dispatcher still advances exactly one 64-byte map row.
    assert s['HudOpponent_Row__p1addr']==0x058376 and s['HudDma1281Enqueue']==0x33ed00
    assert len({x for p in (0,1) for y in (0,1) for x in range(0xd0c0+p*32+y*64,0xd0e0+p*32+y*64)})==128
    assert bytes.fromhex('a980d1')==r[offset(0x058072):offset(0x058072)+3]
    r[0x7fdc:0x7fe0]=bytes.fromhex('ffff0000');crc=sum(r)&65535;r[0x7fdc:0x7fe0]=(65535-crc).to_bytes(2,'little')+crc.to_bytes(2,'little')
    return bytes(r)
