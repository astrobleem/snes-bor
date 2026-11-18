"""Use the shorter channel sequence only for the qualified scroll job in direct attack publication."""
from bor_restart_queue_v1502 import correct as classified,program as classify
from bor_packed_channel_v1506 import program as channel,BASE as CHANNEL
from bor_restart_burst_v1494 import offset
from bor_split_atlas_v1467 import Code,far,imm
GATE=0x29da00
def gate():
    q=Code(GATE)
    # Called exclusively from the positively classified case of the sole JSL at 31:C331.
    # Remove that JSL frame. The enclosing saved A/X/Y/B/D/P are untouched.
    q.put('68e22068c220a94000a24000e220')
    q.put(far(0xaf,0x4212));q.put('2980');q.when(0xf0,'decline')
    q.put(far(0xaf,0x4213));q.put('480980');q.put(far(0x8f,0x4201))
    for a in (0x2137,0x213f,0x213d):q.put(far(0xaf,a))
    q.put(far(0x8f,0x43a874));q.put(far(0xaf,0x213d));q.put('2901');q.put(far(0x8f,0x43a875))
    q.put('68');q.put(far(0x8f,0x4201));q.put(far(0xaf,0x43a875))
    # All short branches below lead to the same original refusal, with no DMA/receipt.
    q.put('d010');q.put(far(0xaf,0x43a874));q.put('c9e19008c9f1b004');q.lab('admit');q.put(far(0x5c,CHANNEL))
    q.lab('decline');q.put(far(0x5c,0x31c4cf))
    assert q.labels['admit']+4==q.labels['decline']
    return q.done(),q.labels
def correct(image,symbols):
    raw=bytearray(classified(image,symbols));a=offset(classify()[1]['stock'])-12
    assert raw[a:a+12]==bytes.fromhex('a9380018690800aae040006b')
    assert raw[offset(0x31c331):offset(0x31c331)+9]==bytes.fromhex('2200ee30900382a600')
    assert raw[offset(0x31c4cf):offset(0x31c4cf)+9]==bytes.fromhex('c2302bab7afa68286b')
    for guest,code in ((GATE,gate()[0]),(CHANNEL,channel()[0])):
        start=offset(guest);assert not any(raw[start:start+len(code)]) and not any(guest<=v<guest+len(code) for t in symbols for v in t.values() if type(v)is int)
        raw[start:start+len(code)]=code
    raw[a:a+4]=far(0x5c,GATE)
    raw[0x7fdc:0x7fe0]=bytes.fromhex('ffff0000');crc=sum(raw)&65535
    raw[0x7fdc:0x7fe0]=(65535-crc).to_bytes(2,'little')+crc.to_bytes(2,'little')
    validate_gate()
    return bytes(raw)
def validate_gate():
    data,labels=gate()
    s=data.index(bytes.fromhex('d010af74a843c9e19008c9f1b004'));end=labels['decline']-GATE
    for off in (s,s+8,s+12):assert off+2+data[off+1]==end
    for line in range(512):
        old=not line>>8 and line>=225 and line<246 and line<241
        assert old==(225<=line<241)
