"""Keep the battle publisher's deadline and source selection; pair adjacent DMA register accesses."""
from bor_restart_queue_v1502 import correct as base
from bor_restart_burst_v1494 import offset
from bor_split_atlas_v1467 import Code,imm,far
BASE=0x29d800
def program():
    q=Code(BASE)
    def read(a):q.put(far(0xaf,a))
    def write(a):q.put(far(0x8f,a))
    q.put('c22048')
    for addr in (0x4370,0x4372,0x4374):
        read(addr);q.put('48')
    q.put('e220');read(0x4376);q.put('48c220')
    q.put(imm(0xa9,0));write(0x2102)
    q.put(imm(0xa9,0x0400));write(0x4370)
    # Restore the original hidden B accumulator byte across the A8 source call.
    q.put('a308e220a900');write(0x4372);q.put('a904');q.put(far(0x22,0x3089c1))
    write(0x4373);q.put('a943');write(0x4374)
    q.put('c22048');q.put(imm(0xa9,544));write(0x4375);q.put('68e220a980')
    q.put(far(0x22,0x308b21));q.lab('returned')
    q.put('68');write(0x4376);q.put('c220')
    for addr in (0x4374,0x4372,0x4370):
        q.put('68');write(addr)
    q.put('68');q.put(far(0x5c,0x31c4ca))
    return q.done(),q.labels
def correct(image,symbols):
    raw=bytearray(base(image,symbols));code,_=program()
    loc=offset(BASE);a=offset(0x31c44c)
    assert raw[a:a+7]==bytes.fromhex('af70430048af71')
    assert raw[offset(0x31c4ca):offset(0x31c4ca)+5]==bytes.fromhex('c230a90000')
    assert not any(raw[loc:loc+len(code)]) and not any(BASE<=v<BASE+len(code) for t in symbols for v in t.values() if type(v)is int)
    raw[a:a+4]=far(0x5c,BASE);raw[loc:loc+len(code)]=code;raw[0x7fdc:0x7fe0]=bytes.fromhex('ffff0000')
    crc=sum(raw)&65535;raw[0x7fdc:0x7fe0]=(65535-crc).to_bytes(2,'little')+crc.to_bytes(2,'little')
    return bytes(raw)
