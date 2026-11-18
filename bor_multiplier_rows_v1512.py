"""Use the source multiplier and player-side alignment in the existing BG3 lives rows."""
from bor_original_stage_row_v1509 import correct as base
from bor_restart_burst_v1494 import offset
from bor_split_atlas_v1467 import Code,imm,far
# This component is outside the prepared original HUD column and packet envelopes.
BASE=0x2de800
def program():
    q=Code(BASE)
    # Caller has already stored the current 16-bit lives in Text_LabelValue.
    # One digit can occupy P2's original projected position; preserve all
    # digits inside the existing owned row for larger counts.
    q.put(imm(0xc9,10));q.put('b005');q.put(imm(0xa0,0x460));q.put('8003');q.put(imm(0xa0,0x465))
    q.put('e220a989c210a20000');q.put(far(0x22,0x00e986))
    q.put(far(0x5c,0x068488))
    return q.done()
def correct(image,symbols):
    r=bytearray(base(image,symbols));s=symbols[0];p=offset(s['Text_Str_HudLives']);p2=offset(s['Text_Str_HudP2Lives'])
    assert r[p:p+14]==b'LIVES '+bytes(1)+b'STAGE '+bytes(1)
    assert r[p2:p2+7]==b'P2LIFE'+bytes(1)
    assert r[offset(0x0587b1):offset(0x0587b1)+4]==bytes.fromhex('5cc78705')
    assert s['Text_Str_HudLives']-s['Text_StringPool']==0x460
    # Reuse the retired stage label's seven bytes. The P1 short label
    # occupies the old P2 label and is shared by the larger-count fallback.
    r[p:p+14]=b'          x'+bytes(3);r[p2:p2+7]=b'     x'+bytes(1)
    a=offset(0x058797);assert r[a:a+7]==bytes.fromhex('a060042286e900');r[a:a+3]=imm(0xa0,0x475)
    b=offset(0x068479);old=bytes.fromhex('e220a989c210a20000a075042286e90060')
    # Derive the seam from the authenticated complete dirty branch.
    b=r.find(old,offset(0x06845a),offset(0x06848b));assert b>=0 and r.count(old)==1
    assert b+len(old)-1==offset(0x068488)
    data=program();loc=offset(BASE);assert not any(r[loc:loc+len(data)]) and not any(BASE<=v<BASE+len(data) for tab in symbols for v in tab.values() if type(v)is int)
    r[b:b+4]=far(0x5c,BASE);r[loc:loc+len(data)]=data
    r[0x7fdc:0x7fe0]=bytes.fromhex('ffff0000');c=sum(r)&65535;r[0x7fdc:0x7fe0]=(65535-c).to_bytes(2,'little')+c.to_bytes(2,'little')
    return bytes(r)
